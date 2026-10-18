"""Referência de preço por nível de exigência ("preço típico" para o dono): mediana do R$/kg estimado pelos órgãos entre as
licitações abertas do mesmo tipo e nível. É comparação entre licitações (inferência), não custo real.

A página (index.html, função refPrecos) usa a mesma regra; mudou aqui, mude lá.
"""
from __future__ import annotations

import statistics
from typing import Any

from coletor import cafe

MIN_AMOSTRA = 5  # menos que isso, a mediana não diz muito: sem referência
FAIXA = 0.10  # até 10% de diferença da mediana conta como "no preço típico"


def grupo(tipo: str) -> str:
    """Descafeinado entra com o torrado e moído; grão fica separado (preço por kg diferente)."""
    return cafe.TM if tipo == cafe.TM_DESCAF else tipo


def referencias(compras: list[dict[str, Any]]) -> dict[tuple[str, str], float]:
    """{(grupo do tipo, nível): mediana do R$/kg} das compras visíveis (sem duplicatas)."""
    por: dict[tuple[str, str], list[float]] = {}
    for c in compras:
        if c.get("dup_of"):
            continue
        for i in c["itens"]:
            if i.get("nivel") and i.get("rkg") and not i.get("conferir"):
                por.setdefault((grupo(i["tipo"]), i["nivel"]), []).append(i["rkg"])
    return {k: round(statistics.median(v), 2) for k, v in por.items() if len(v) >= MIN_AMOSTRA}


def item_principal(c: dict[str, Any]) -> dict[str, Any] | None:
    """Item que define a compra para comparação de preço: o de maior volume com nível e R$/kg."""
    its = [i for i in c["itens"] if i.get("nivel") and i.get("rkg") and not i.get("conferir")]
    return max(its, key=lambda i: i.get("kgt") or 0) if its else None


def comparar(i: dict[str, Any], refs: dict[tuple[str, str], float]) -> tuple[float, float] | None:
    """(mediana do nível, diferença relativa do item). None sem referência suficiente."""
    ref = refs.get((grupo(i["tipo"]), i["nivel"]))
    if not ref or not i.get("rkg"):
        return None
    return ref, i["rkg"] / ref - 1


def rotulo(dif: float) -> str:
    if dif >= FAIXA:
        return "acima do preço típico"
    if dif <= -FAIXA:
        return "abaixo do preço típico"
    return "no preço típico"
