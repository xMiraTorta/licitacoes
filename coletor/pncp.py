"""Cliente das APIs públicas do PNCP (sem autenticação).

APIs usadas (verificadas em 17/10/2026):
- Consulta: GET https://pncp.gov.br/api/consulta/v1/contratacoes/proposta
  lista compras com recebimento de propostas aberto, por modalidade. Página máx. 50.
- Itens:    GET https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens
- Busca:    GET https://pncp.gov.br/api/search/ (texto livre; paginação instável, usada só como reforço).
"""
from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

import httpx
from loguru import logger

BASE = "https://pncp.gov.br/api"
USER_AGENT = "licitacoes-cafe/1.0 (painel de licitacoes; github.com/xMiraTorta/licitacoes-cafe)"
RETRY_STATUS = {429, 500, 502, 503, 504}
# O PNCP responde 429 ("Limite de requisições excedido") sem cabeçalho Retry-After quando há
# rajadas. Intervalo mínimo entre chamadas (somando todas as threads) e espera maior no 429.
INTERVALO_MIN = 0.15
ESPERA_429 = 10.0


class ColetaErro(RuntimeError):
    """Falha definitiva numa chamada ao PNCP (após todas as tentativas)."""


@dataclass
class Estatisticas:
    chamadas: int = 0
    novas_tentativas: int = 0
    falhas: list[str] = field(default_factory=list)


class PNCP:
    def __init__(self, client: httpx.Client | None = None, tentativas: int = 5, espera_base: float = 2.0,
                 limite_chamadas: int = 20000, intervalo_min: float = INTERVALO_MIN, espera_429: float = ESPERA_429) -> None:
        self.client = client or httpx.Client(timeout=httpx.Timeout(60.0, connect=20.0),
                                             headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        self.tentativas = tentativas
        self.espera_base = espera_base
        self.limite_chamadas = limite_chamadas
        self.intervalo_min = intervalo_min
        self.espera_429 = espera_429
        self.stats = Estatisticas()
        self._lock = threading.Lock()
        self._proxima = 0.0

    def _aguardar_vez(self) -> None:
        with self._lock:
            agora = time.monotonic()
            espera = self._proxima - agora
            self._proxima = max(agora, self._proxima) + self.intervalo_min
        if espera > 0:
            time.sleep(espera)

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """GET com novas tentativas (2 s, 4 s, 8 s...) em erro de rede, 429 e 5xx. 204 vira lista vazia."""
        url = path if path.startswith("http") else BASE + path
        ultimo = ""
        for n in range(1, self.tentativas + 1):
            with self._lock:
                if self.stats.chamadas >= self.limite_chamadas:
                    raise ColetaErro(f"limite de {self.limite_chamadas} chamadas atingido")
                self.stats.chamadas += 1
            self._aguardar_vez()
            limitado = False
            try:
                r = self.client.get(url, params=params)
            except httpx.TransportError as e:
                ultimo = f"{type(e).__name__}: {e}"
            else:
                if r.status_code == 204:
                    return []
                if r.status_code == 200:
                    try:
                        return r.json()
                    except ValueError as e:
                        ultimo = f"JSON inválido ({len(r.content)} bytes): {e}"
                elif r.status_code in RETRY_STATUS:
                    limitado = r.status_code == 429
                    ultimo = f"HTTP {r.status_code}" + ("" if limitado else f": {r.text[:200]}")
                else:
                    raise ColetaErro(f"{url} {params} -> HTTP {r.status_code}: {r.text[:300]}")
            if n < self.tentativas:
                espera = (self.espera_429 if limitado else self.espera_base) * 2 ** (n - 1)
                with self._lock:
                    self.stats.novas_tentativas += 1
                logger.warning("PNCP {} {} falhou ({}); tentativa {}/{} em {:.0f}s", url, params, ultimo, n + 1,
                               self.tentativas, espera)
                time.sleep(espera)
        raise ColetaErro(f"{url} {params} -> {ultimo}")

    def listar_abertas(self, modalidade: int, data_final: str, paralelo: int = 3) -> Iterator[dict[str, Any]]:
        """Todas as compras da modalidade com propostas abertas. Erro em qualquer página -> ColetaErro."""
        path = "/consulta/v1/contratacoes/proposta"
        base = {"dataFinal": data_final, "codigoModalidadeContratacao": modalidade, "tamanhoPagina": 50}
        primeira = self.get_json(path, {**base, "pagina": 1})
        total_pag = int(primeira.get("totalPaginas") or 0)
        logger.info("Modalidade {}: {} compras abertas em {} páginas", modalidade, primeira.get("totalRegistros"), total_pag)
        yield from primeira.get("data") or []
        with ThreadPoolExecutor(max_workers=paralelo) as ex:
            futs = {ex.submit(self.get_json, path, {**base, "pagina": p}): p for p in range(2, total_pag + 1)}
            for f in as_completed(futs):
                yield from f.result().get("data") or []

    def itens(self, cnpj: str, ano: int, seq: int) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        pagina = 1
        while True:
            lote = self.get_json(f"/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens",
                                 {"pagina": pagina, "tamanhoPagina": 1000})
            out.extend(lote or [])
            if not lote or len(lote) < 1000:
                return out
            pagina += 1

    def buscar(self, termo: str, max_paginas: int = 15) -> set[str]:
        """Números de controle encontrados pela busca textual (reforço; falhas só geram aviso)."""
        achados: set[str] = set()
        for p in range(1, max_paginas + 1):
            try:
                d = self.get_json("/search/", {"q": termo, "tipos_documento": "edital", "ordenacao": "-data",
                                                "pagina": p, "tam_pagina": 100, "status": "recebendo_proposta"})
            except ColetaErro as e:
                logger.warning("Busca '{}' parou na página {}: {}", termo, p, e)
                self.stats.falhas.append(f"busca '{termo}' p{p}: {e}")
                break
            items = d.get("items") or []
            achados.update(i["numero_controle_pncp"] for i in items if i.get("numero_controle_pncp"))
            if len(items) < 100:
                break
        logger.info("Busca '{}': {} compras", termo, len(achados))
        return achados
