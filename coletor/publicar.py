"""Junta a coleta nova com a anterior, valida e grava data.json (o site, em site/, lê esse arquivo).

Travas de segurança (uma coleta ruim nunca substitui dados bons em silêncio):
- listagem incompleta (qualquer página com erro) -> aborta antes de chegar aqui;
- falha ao baixar itens de mais de LIMITE_FALHAS das candidatas -> aborta;
- compras abertas caem abaixo de LIMITE_QUEDA da coleta anterior -> aborta;
- compra conhecida cujos itens falharam nesta rodada -> mantém o registro anterior;
- validação de formato antes de gravar; gravação atômica (arquivo temporário + rename).
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from loguru import logger

from coletor import custos, marcas, mercado
from coletor.arquivos import gravar_atomico

LIMITE_FALHAS = 0.05
LIMITE_QUEDA = 0.6


class PublicacaoBloqueada(RuntimeError):
    """A coleta parece incompleta; os arquivos publicados não foram alterados."""


def carregar(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def abertas(compras: list[dict[str, Any]], agora: str) -> list[dict[str, Any]]:
    return [c for c in compras if not c.get("fim") or c["fim"] >= agora]


def novas_desde(anterior: dict[str, Any] | None, hoje: str) -> str:
    """Data de referência para o selo "Nova": a última coleta de um dia anterior a hoje."""
    if not anterior:
        return hoje
    if anterior.get("run_date", hoje) < hoje:
        return anterior["run_date"]
    return anterior.get("novas_desde") or anterior.get("run_date", hoje)


def juntar(novas: list[dict[str, Any]], anterior: dict[str, Any] | None, falharam: set[str],
           hoje: str, agora_min: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Compras finais e lista das que apareceram pela primeira vez nesta rodada."""
    from coletor.montar import herdar_do_anterior, marcar_duplicatas

    antigos = {c["chave"]: c for c in (anterior or {}).get("compras", [])}
    seed = (anterior or {}).get("seed_date", hoje)
    ref = novas_desde(anterior, hoje)
    out: list[dict[str, Any]] = []
    primeira_vez: list[str] = []
    for c in novas:
        if c["chave"] in antigos:
            herdar_do_anterior(c, antigos[c["chave"]])
        else:
            c["first_seen"] = hoje
            primeira_vez.append(c["chave"])
        out.append(c)
    vistos = {c["chave"] for c in out}
    mantidas = [dict(antigos[k]) for k in sorted(falharam) if k in antigos and k not in vistos
                and (not antigos[k].get("fim") or antigos[k]["fim"] >= agora_min)]
    if mantidas:
        logger.warning("{} compras conhecidas mantidas da coleta anterior porque os itens falharam: {}",
                       len(mantidas), [c["chave"] for c in mantidas])
    out.extend(mantidas)
    out = [c for c in out if not c.get("fim") or c["fim"] >= agora_min]
    for c in out:
        c["nova"] = hoje != seed and (c.get("first_seen") or hoje) > ref
    out.sort(key=lambda c: (c.get("fim") or "9999", c["chave"]))
    marcar_duplicatas(out, {k for k, c in antigos.items() if not c.get("dup_of")})
    return out, primeira_vez


def verificar_travas(compras: list[dict[str, Any]], anterior: dict[str, Any] | None, candidatas: int,
                     falhas: int, agora_min: str, forcar: bool = False) -> None:
    problemas = []
    if candidatas and falhas / candidatas > LIMITE_FALHAS:
        problemas.append(f"itens falharam em {falhas} de {candidatas} candidatas (> {LIMITE_FALHAS:.0%})")
    if anterior:
        antes = len(abertas(anterior.get("compras", []), agora_min))
        if antes and len(compras) < antes * LIMITE_QUEDA:
            problemas.append(f"{len(compras)} compras abertas agora contra {antes} na coleta anterior "
                             f"(queda maior que {1 - LIMITE_QUEDA:.0%})")
    if not compras:
        problemas.append("nenhuma compra de café encontrada")
    if problemas:
        msg = "; ".join(problemas)
        if forcar:
            logger.warning("Travas ignoradas por --forcar: {}", msg)
        else:
            raise PublicacaoBloqueada(msg)


def validar(data: dict[str, Any]) -> None:
    from coletor.modelos import Painel

    Painel.model_validate(data)


def gravar(data: dict[str, Any], destino: Path, gerado_em: datetime) -> None:
    """Grava data.json validado. O site (site/, React) baixa esse arquivo ao abrir e a cada 15 min; o GitHub
    Pages republica o site a cada push na main que mude data.json (.github/workflows/pages.yml)."""
    data["marcas_ref"] = marcas.resumo()  # pesquisa de varejo das marcas citadas em editais (coletor/marcas_cafe.json)
    data["mercado"] = mercado.carregar()  # café verde por nível (coletor/mercado.json, 2x por dia útil)
    data["custos"] = custos.premissas()  # premissas padrão da margem (coletor/custos.json)
    # Toda gravação (inclusive só de preços, com o mesmo gerado_em) ganha hora nova: é por ela que a página aberta
    # percebe que há arquivo mais novo e troca os dados.
    data["publicado_em"] = datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat(timespec="seconds")
    validar(data)
    texto = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False)  # NaN/Infinity quebrariam o site
    gravar_atomico(destino / "data.json", texto)
    logger.info("Gravado data.json ({} KB, {} compras, gerado em {:%d/%m/%Y %H:%M})", len(texto) // 1024, len(data["compras"]), gerado_em)
