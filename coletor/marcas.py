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
    "Itamarati": (("itamarati",), False),
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


@lru_cache(maxsize=1)
def base() -> dict[str, dict[str, Any]]:
    """Categoria e faixa de preço de varejo por marca (pesquisa em marcas_cafe.json); vazio se ainda não existir."""
    if not BASE.exists():
        return {}
    return {m["marca"]: m for m in json.loads(BASE.read_text(encoding="utf-8"))["marcas"]}
