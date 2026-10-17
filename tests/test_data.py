"""Integridade de data.json e da cópia embutida em index.html (dados reais do repositório)."""
from __future__ import annotations

import json
from typing import Any

import pytest

from tests.conftest import ROOT, embedded_data

DATA: dict[str, Any] = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
COMPRAS: list[dict[str, Any]] = DATA["compras"]
ITENS = [(c["chave"], i) for c in COMPRAS for i in c["itens"]]


def test_embedded_copy_matches_data_json() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert embedded_data(html) == DATA


def test_required_top_level_fields() -> None:
    for k in ("gerado_em", "run_date", "origem", "status_opcoes", "fonte", "compras", "checklist"):
        assert k in DATA, k
    assert DATA["compras"], "lista de compras vazia"


def test_chave_unique_and_well_formed() -> None:
    chaves = [c["chave"] for c in COMPRAS]
    assert len(chaves) == len(set(chaves))
    for k in chaves:
        cnpj, _, rest = k.split("-", 2)
        assert len(cnpj) == 14 and cnpj.isdigit(), k
        assert "/" in rest, k


@pytest.mark.parametrize("campo", ["vcafe", "kg", "rkg"])
def test_missing_values_are_null_not_zero(campo: str) -> None:
    assert not [c["chave"] for c in COMPRAS if c[campo] == 0]


def test_item_kg_total_is_qty_times_unit_weight() -> None:
    bad = [(k, i["n"]) for k, i in ITENS
           if None not in (i["kgu"], i["qtd"], i["kgt"]) and abs(i["kgu"] * i["qtd"] - i["kgt"]) > 0.01]
    assert not bad


def test_item_price_per_kg_is_total_over_kg() -> None:
    # O gerador original às vezes calculou por vu/kgu (valor unitário já arredondado): aceita 0,1%.
    bad = [(k, i["n"]) for k, i in ITENS
           if i["rkg"] is not None and abs(i["vt"] / i["kgt"] - i["rkg"]) > max(0.011, i["rkg"] * 0.001)]
    assert not bad


def test_secret_budget_items_have_no_value() -> None:
    assert not [(k, i["n"]) for k, i in ITENS if i["sig"] and i["vt"] is not None]


def test_compra_kg_is_sum_of_items() -> None:
    bad = []
    for c in COMPRAS:
        ks = [i["kgt"] for i in c["itens"] if i["kgt"] is not None]
        if c["kg"] is None:
            assert not ks, c["chave"]
        elif abs(sum(ks) - c["kg"]) > 0.1:
            bad.append(c["chave"])
    assert not bad


def test_compra_value_excludes_baskets() -> None:
    """vcafe soma itens de café; cestas/kits vão em vcesta."""
    bad = []
    for c in COMPRAS:
        cafe = [i["vt"] for i in c["itens"] if i["tipo"] != "Cesta/kit" and i["vt"] is not None]
        if c["vcafe"] is None:
            assert not cafe, c["chave"]
        elif abs(sum(cafe) - c["vcafe"]) > 0.05:
            bad.append(c["chave"])
    assert not bad


def test_duplicates_point_to_existing_compras() -> None:
    chaves = {c["chave"] for c in COMPRAS}
    for c in COMPRAS:
        if c["dup_of"]:
            assert c["dup_of"] in chaves, c["chave"]
