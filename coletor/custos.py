"""Custo estimado e margem de cada oportunidade (pedido do dono em 18/10/2026).

Mesma regra de `margemInfo` no index.html (mudou uma, mude a outra). Por kg de café torrado, ao preço do órgão
(R$/kg do item principal): grão do nível (mercado.json) e torra divididos por (1 - perda na torra), embalagem,
frete (fracionado ou lotação, o mais barato por entrega, mais folga), custos fixos da licitação rateados no volume
e percentuais sobre o preço (DAS do Simples, custo financeiro, perdas). Premissas em custos.json.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

BASE = Path(__file__).with_name("custos.json")


@lru_cache(maxsize=1)
def premissas() -> dict[str, Any]:
    return json.loads(BASE.read_text(encoding="utf-8"))


def frete_total(kg: float, km: float, preco: float, registro_precos: bool, p: dict[str, Any]) -> float:
    f = p["frete"]
    n = max(1, int(f["entregas_registro_precos"] if registro_precos else f["entregas"]))
    kg_e = kg / n
    fracionado = f["fixo_por_envio"] + kg_e * (f["rs_kg"] + f["rs_kg_100km"] * km / 100) + f["ad_valorem"] * preco * kg_e
    lotacao = f["lotacao_fixo"] + f["lotacao_rs_km"] * km
    return n * min(fracionado, lotacao) * (1 + f["folga"])


def margem(compra: dict[str, Any], item: dict[str, Any], mercado: dict[str, Any],
           p: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Custo por kg e margem ao preço do órgão, ou None sem preço, volume, distância ou preço do grão."""
    p = p or premissas()
    preco, kg, km = item.get("rkg"), compra.get("kg"), compra.get("dist")
    nivel = item.get("nivel") or "Sem categoria"
    grao_v = ((mercado.get("niveis") or {}).get(nivel) or {}).get("kg_medio")
    if not preco or not kg or km is None or not grao_v:
        return None
    perda = p["perda_torra"]
    grao = grao_v / (1 - perda)
    torra = p["torra_rs_kg_verde"] / (1 - perda)
    direto = grao + torra + p["embalagem_rs_kg"]
    frete = frete_total(kg, km, preco, compra.get("srp") == "Sim", p) / kg
    fixos = (p["por_licitacao"]["plataforma"] + p["por_licitacao"]["laudo"] + p["por_licitacao"]["amostra_kg"] * direto) / kg
    pct = p["pct_preco"]["das"] + p["pct_preco"]["financeiro"] + p["pct_preco"]["perdas"]  # os mesmos 3 do site (modelo.ts)
    custo = direto + frete + fixos + preco * pct
    m = preco - custo
    return {"preco": round(preco, 2), "grao": round(grao, 2), "torra": round(torra, 2), "embalagem": p["embalagem_rs_kg"],
            "frete": round(frete, 2), "fixos": round(fixos, 2), "percentuais": round(preco * pct, 2),
            "custo": round(custo, 2), "margem_kg": round(m, 2), "margem_pct": round(m / preco, 4), "lucro": round(m * kg, 2),
            "empate": round((direto + frete + fixos) / (1 - pct), 2)}
