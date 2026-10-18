"""Orquestra uma coleta completa: listar compras abertas, achar as de café, montar e publicar."""
from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from loguru import logger

from coletor import edital, publicar
from coletor.cafe import VERSAO_REGRAS, norm
from coletor.distancias import ORIGEM
from coletor.montar import montar_compra
from coletor.pncp import PNCP, ColetaErro

TZ = ZoneInfo("America/Sao_Paulo")
MODALIDADES = (6, 8)  # Pregão eletrônico e Dispensa, como no painel original
TERMOS_BUSCA = ("café", "cafe")
CACHE = Path(__file__).with_name("cache") / "sem_cafe.json"

# Objeto da compra que pode conter café entre os itens. Medido em 17/10/2026: cobre 327 de 327
# compras do painel original, junto com a busca textual. Lista ampla de propósito: o custo de
# olhar itens a mais é só tempo; o de perder uma compra é uma oportunidade.
OBJETO_PODE_TER_CAFE = re.compile(
    r"caf[eé]|coffe|aliment|genero|cesta|copa|cozinha|lanche|merenda|mercad|hortifr|estiva|refei|bebida|"
    r"desjejum|mantimento|perecive|nutric|kit|consumo|cantina|rancho|subsist|abasteciment|lanchonete|padaria|"
    r"confeit|\bchas?\b|expediente|almoxarifado|bens comuns")
COFFEE_BREAK = re.compile(r"coff?ee?\s*-?\s*break")


@dataclass
class Resultado:
    compras: int = 0
    novas: list[str] = field(default_factory=list)
    candidatas: int = 0
    falhas: list[str] = field(default_factory=list)
    chamadas: int = 0
    segundos: int = 0


def _texto_objeto(c: dict[str, Any]) -> str:
    return norm(f"{c.get('objetoCompra') or ''} {c.get('informacaoComplementar') or ''}")


def _ler_cache() -> dict[str, str]:
    """Compras já verificadas sem café: {chave: dataAtualizacaoGlobal}. Cache de outra versão das regras
    de classificação é descartado (a compra pode ter café pelas regras novas)."""
    if not CACHE.exists():
        return {}
    d = json.loads(CACHE.read_text(encoding="utf-8"))
    if d.get("versao") != VERSAO_REGRAS:
        logger.info("Cache sem_cafe de outra versão das regras ({}); verificando tudo de novo", d.get("versao"))
        return {}
    return d["itens"]


def _gravar_cache(itens: dict[str, str]) -> None:
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps({"versao": VERSAO_REGRAS, "itens": itens}, ensure_ascii=False, sort_keys=True, indent=0),
                     encoding="utf-8")


def _ainda_aberta(c: dict[str, Any], agora_min: str) -> bool:
    return (c.get("situacaoCompraId") == 1 and c.get("modalidadeId") in MODALIDADES
            and (c.get("dataEncerramentoProposta") or "9999")[:16] >= agora_min)


def coletar(destino: Path, forcar: bool = False, usar_busca: bool = True, pncp: PNCP | None = None,
            agora: datetime | None = None, ler_editais: bool = True) -> Resultado:
    t0 = time.monotonic()
    agora = agora or datetime.now(TZ)
    hoje, agora_min = agora.strftime("%Y-%m-%d"), agora.strftime("%Y-%m-%dT%H:%M")
    p = pncp or PNCP()
    anterior = publicar.carregar(destino / "data.json")
    conhecidas = {c["chave"] for c in (anterior or {}).get("compras", [])}

    # 1. Listagem completa das compras abertas (erro em qualquer página aborta tudo).
    lista: dict[str, dict[str, Any]] = {}
    data_final = (agora + timedelta(days=730)).strftime("%Y%m%d")
    for m in MODALIDADES:
        for c in p.listar_abertas(m, data_final):
            if (c.get("dataEncerramentoProposta") or "9999")[:16] >= agora_min:
                lista[c["numeroControlePNCP"]] = c
    logger.info("Listagem: {} compras com propostas abertas", len(lista))
    falhas: dict[str, str] = {}

    # 1b. Compra conhecida, ainda no prazo, que não veio na listagem: a paginação do PNCP é por posição
    # e pode pular registros enquanto a lista muda. Confere uma a uma; revogada/suspensa sai do painel.
    sumidas = sorted(k for k, c in ((c["chave"], c) for c in (anterior or {}).get("compras", []))
                     if k not in lista and (not c.get("fim") or c["fim"] >= agora_min))
    for k in sumidas:
        try:
            c = p.compra(k)
        except ColetaErro as e:
            falhas[k] = str(e)  # mantida da coleta anterior (ver publicar.juntar)
            continue
        if c and _ainda_aberta(c, agora_min):
            lista[k] = c
            logger.warning("{} não veio na listagem, mas continua aberta no PNCP: incluída", k)
        else:
            logger.info("{} saiu da listagem: {}", k, (c or {}).get("situacaoCompraNome") or "não encontrada no PNCP")

    # 2. Candidatas: objeto compatível + busca textual + já conhecidas.
    cand = {k for k, c in lista.items() if OBJETO_PODE_TER_CAFE.search(_texto_objeto(c))}
    if usar_busca:
        for termo in TERMOS_BUSCA:
            cand |= p.buscar(termo) & lista.keys()
    cand |= conhecidas & lista.keys()
    cache = _ler_cache()
    pular = {k for k in cand if k not in conhecidas and cache.get(k) == lista[k].get("dataAtualizacaoGlobal")}
    olhar = sorted(cand - pular)
    logger.info("Candidatas: {} ({} já verificadas sem café e sem alteração; {} para baixar itens)",
                len(cand), len(pular), len(olhar))

    # 3. Itens de cada candidata.
    itens: dict[str, list[dict[str, Any]]] = {}

    def baixar(k: str) -> None:
        c = lista[k]
        try:
            itens[k] = p.itens(c["orgaoEntidade"]["cnpj"], c["anoCompra"], c["sequencialCompra"])
        except ColetaErro as e:
            falhas[k] = str(e)

    with ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(baixar, olhar))
    for k, e in falhas.items():
        logger.error("Compra {} não verificada nesta coleta (fica a versão anterior, se houver): {}", k, e)

    # 4. Montagem.
    compras, sem_cafe = [], {}
    for k, its in itens.items():
        reg = montar_compra(lista[k], its)
        if reg:
            compras.append(reg)
        elif its:  # sem itens publicados ainda: verifica de novo na próxima coleta
            sem_cafe[k] = lista[k].get("dataAtualizacaoGlobal") or ""
    finais, primeira_vez = publicar.juntar(compras, anterior, set(falhas), hoje, agora_min)
    publicar.verificar_travas(finais, anterior, len(olhar) + len(sumidas), len(falhas), agora_min, forcar)

    # 4b. Edital/TR de cada compra (novas, alteradas no PNCP ou sem documentos ainda): especificação de cada
    # item, marcas de referência e prazo de entrega. Não bloqueia a publicação: falha fica para a próxima.
    if ler_editais:
        edital.ler_varias(p, finais, {k: c.get("dataAtualizacaoGlobal") or "" for k, c in lista.items()}, hoje)

    # 5. Gravação.
    base = anterior or {}
    data = {
        "gerado_em": agora.isoformat(timespec="seconds"),
        "run_date": hoje,
        "seed_date": base.get("seed_date", hoje),
        "novas_desde": publicar.novas_desde(anterior, hoje),
        "origem": {k: ORIGEM[k] for k in ("nome", "lat", "lon")},
        "status_opcoes": base.get("status_opcoes", ["A analisar", "Em preparação", "Enviada", "Ganha", "Perdida", "Desistiu"]),
        "fonte": base.get("fonte", "PNCP – Portal Nacional de Contratações Públicas (pncp.gov.br)"),
        "editais_lidos": sum(1 for c in finais if c.get("edital_lido")),
        "compras": finais,
        "checklist": base.get("checklist", []),
        "coffee_break": [
            {"orgao": (c.get("orgaoEntidade") or {}).get("razaoSocial", ""), "uf": (c.get("unidadeOrgao") or {}).get("ufSigla", ""),
             "mun": (c.get("unidadeOrgao") or {}).get("municipioNome", ""), "objeto": (c.get("objetoCompra") or "")[:250],
             "fim": (c.get("dataEncerramentoProposta") or "")[:16],
             "link": f"https://pncp.gov.br/app/editais/{c['orgaoEntidade']['cnpj']}/{c['anoCompra']}/{c['sequencialCompra']}"}
            for c in lista.values() if COFFEE_BREAK.search(_texto_objeto(c))],
        "coleta": {"modalidades": list(MODALIDADES), "listadas": len(lista), "candidatas": len(cand),
                   "itens_baixados": len(itens), "falhas": len(falhas), "chamadas_pncp": p.stats.chamadas,
                   "novas_tentativas": p.stats.novas_tentativas, "segundos": round(time.monotonic() - t0)},
    }
    publicar.gravar(data, destino, agora)
    _gravar_cache({k: v for k, v in {**cache, **sem_cafe}.items() if k in lista})

    r = Resultado(len(finais), primeira_vez, len(olhar) + len(sumidas), list(falhas), p.stats.chamadas, round(time.monotonic() - t0))
    logger.info("Coleta concluída: {} compras de café abertas, {} novas, {} falhas, {} chamadas, {} s",
                r.compras, len(r.novas), len(r.falhas), r.chamadas, r.segundos)
    return r
