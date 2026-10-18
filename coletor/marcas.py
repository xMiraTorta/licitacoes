"""Marcas de café citadas nos editais como referência ("marca de referência", "padrão", "similar a").

A marca citada indica a qualidade e a faixa de preço que o órgão espera. A base de categorias e preços de varejo
fica em `marcas_cafe.json` (pesquisa datada, com fontes). Nomes que também são palavras comuns ou cidades
("Bom Jesus", "União", "Brasileiro") só contam perto de "marca", "referência", "similar", "padrão" ou "equivalente".
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from coletor import cafe

BASE = Path(__file__).with_name("marcas_cafe.json")
# Marca: (grafias sem acento/minúsculas, precisa de contexto de "marca/referência"?)
MARCAS: dict[str, tuple[tuple[str, ...], bool]] = {
    "3 Corações": (("3 coracoes", "tres coracoes", "3coracoes"), False),
    "Melitta": (("melitta", "mellita", "melita"), False),
    "Pilão": (("pilao",), False),
    "Caboclo": (("caboclo",), False),
    "Café do Ponto": (("cafe do ponto",), False),
    "Santa Clara": (("santa clara",), True),
    "Pelé": (("cafe pele", "pele"), True),
    "União": (("uniao",), True),
    "Café Brasileiro": (("cafe brasileiro", "brasileiro"), True),
    "Mel Café": (("mel cafe",), False),
    "Moinho Fino": (("moinho fino",), False),
    "Cajubá": (("cajuba",), False),
    "Flor da Serra": (("flor da serra",), True),
    "Damasco": (("damasco",), False),
    "Bom Jesus": (("bom jesus",), True),
    "Alvorada": (("alvorada",), True),
    "Itamarati": (("itamarati", "itamaraty"), False),
    "Veneza": (("veneza",), True),
    "Dom Pedro": (("dom pedro",), True),
    "Produtor": (("cafe produtor", "produtor"), True),
    "Vasconcelos": (("vasconcelos",), True),
    "Seleto": (("seleto",), True),
    "Maratá": (("marata",), False),
    "Fazendão": (("fazendao",), True),
    "Odebrecht": (("odebrecht",), False),
    "Pimpinela": (("pimpinela",), False),
    "Toko": (("toko",), False),
    "Rancheiro": (("rancheiro",), True),
    "Fiorella": (("fiorella",), False),
    "Utam": (("utam",), False),
    "Kimimo": (("kimimo",), False),
    "Serrano": (("serrano",), True),
    "Baggio": (("baggio",), False),
    "Orfeu": (("orfeu",), False),
    "Pacaembu": (("pacaembu",), True),
    "Jaguari": (("jaguari",), True),
    "Pinguim": (("pinguim",), True),
    "Morro Grande": (("morro grande",), True),
    "L'or": (("l'or", "l or", "lor espresso"), True),
    "3 Fazendas": (("3 fazendas", "tres fazendas"), False),
    "Evolutto": (("evolutto", "evoluto"), False),
    "Nescafé": (("nescafe",), False),
}
_CONTEXTO = re.compile(r"marcas?|referencia|referencial|similar|padrao|equivalente|\bex\b|exemplo|tipo")


@lru_cache(maxsize=1)
def _regex() -> list[tuple[str, re.Pattern[str], bool]]:
    return [(nome, re.compile(r"\b(?:" + "|".join(re.escape(a) for a in aliases) + r")\b"), ctx)
            for nome, (aliases, ctx) in MARCAS.items()]


def citadas(texto: str) -> list[str]:
    """Marcas citadas no texto (normalizado por cafe.norm), na ordem em que aparecem."""
    t = cafe.norm(texto)
    achadas: list[tuple[int, str]] = []
    for nome, rx, precisa_ctx in _regex():
        for m in rx.finditer(t):
            if precisa_ctx and not _CONTEXTO.search(t[max(0, m.start() - 120):m.start()]):
                continue
            achadas.append((m.start(), nome))
            break
    return [n for _, n in sorted(achadas)]


ORDEM_CAT = {"Tradicional": 0, "Extraforte": 0, "Superior": 1, "Gourmet": 2, "Especial": 3}


@lru_cache(maxsize=1)
def base() -> dict[str, Any]:
    """Pesquisa de varejo e categorias ABIC (marcas_cafe.json): {pesquisa_em, como, fonte_categorias, linhas}."""
    return json.loads(BASE.read_text(encoding="utf-8"))


def resumo() -> dict[str, Any]:
    """O que o site e o Telegram usam: por marca, as linhas com categoria e faixa de R$/kg no varejo, e a "básica"
    (a linha de categoria mais baixa com preço: o mínimo que "equivalente à marca X" costuma significar)."""
    b = base()
    por: dict[str, list[dict[str, Any]]] = {}
    for x in b["linhas"]:
        por.setdefault(x["marca"], []).append({"linha": x["linha"] or "", "cat": x["categoria"], "min": x["preco_kg_min"],
                                               "max": x["preco_kg_max"]})
    out: dict[str, Any] = {}
    for m, ls in por.items():
        com_preco = [x for x in ls if x["min"] is not None]
        basica = min(com_preco, key=lambda x: (ORDEM_CAT.get(x["cat"] or "", 0), x["min"])) if com_preco else None
        out[m] = {"linhas": ls, "basica": basica}
    return {"pesquisa_em": b["pesquisa_em"], "marcas": out}
