"""Formato de data.json (contrato com index.html). Validado antes de cada gravação."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, PositiveFloat


class _Base(BaseModel):
    model_config = ConfigDict(extra="allow")


class Item(_Base):
    n: int | None
    tipo: str
    cat: str
    emb: str
    kgu: PositiveFloat | None
    kg_src: str
    qtd: PositiveFloat | None
    un: str
    vu: PositiveFloat | None
    vt: PositiveFloat | None
    sig: bool
    kgt: PositiveFloat | None
    rkg: PositiveFloat | None
    conferir: bool
    me: str
    sit: str
    tags: list[str]
    espec: str
    usa_trecho: bool


class Compra(_Base):
    chave: str = Field(pattern=r"^\d{14}-\d-\d{6}/\d{4}$")
    fim: str | None
    abre: str | None
    publicado: str | None
    first_seen: str
    nova: bool
    uf: str
    mun: str
    dist: int | None  # km por estrada a partir de Uberaba (OSRM)
    dist_min: int | None = None  # minutos de viagem
    orgao: str
    unidade: str
    esfera: str
    mod: str
    num: str
    plat: str
    plat_src: str
    plat_f: str
    publicado_via: str
    uasg: str
    srp: str
    objeto: str
    link_pncp: str
    link_plat: str
    ed_tags: list[str]
    ed_pz: str
    edital_lido: bool
    trecho_edital: str
    tipos: list[str] = Field(min_length=1)
    cats: list[str]
    cat_do_edital: bool
    embs: str
    emb_f: list[str]
    vcafe: PositiveFloat | None
    vcesta: PositiveFloat | None
    kg: PositiveFloat | None
    kg_parcial: bool
    rkg: PositiveFloat | None
    sig: str
    me: str
    me_f: list[str]
    tags: list[str]
    resumo: str
    dup: str
    dup_of: str | None
    dup_group: list[str]
    itens: list[Item] = Field(min_length=1)


class Painel(_Base):
    gerado_em: str
    run_date: str
    seed_date: str
    novas_desde: str
    origem: dict[str, Any]
    status_opcoes: list[str]
    fonte: str
    editais_lidos: int
    compras: list[Compra]
    checklist: list[dict[str, Any]]
    coffee_break: list[dict[str, Any]]
