"""Classificador de itens de café (coletor/cafe.py)."""
from __future__ import annotations

import json

import pytest

from coletor import cafe
from tests.conftest import ROOT


@pytest.mark.parametrize("desc,esperado", [
    ("Café torrado e moído, pacote 500g, selo ABIC", cafe.TM),
    ("PÓ PARA CAFÉ TORRADO E MOÍDO PRODUTO DE 1º QUALIDADE; EMBALAGEM 500G", cafe.TM),
    ("(COTA) PÓ DE CAFÉ- EXTRA FORTE TORRADO E MOÍDO, EMBALAGEM TIPO A VÁCUO", cafe.TM),
    ("CAFÉ SOLÚVEL GRANULADO (FRASCO 180G)", cafe.SOLUVEL),
    ("Café torrado em grãos, 100% arábica, 1 kg", cafe.GRAO),
    ("CÁPSULA DE CAFÉ (COMPATÍVEL SISTEMA DOLCE GUSTO)", cafe.CAPSULA),
    ("CAFÉ PRONTO, GARRAFA DE 5 LITROS, coado no momento da entrega", cafe.BEBIDA),
    ("Cafe em po 500 gramas para preparo de cafe coado", cafe.TM),
    ("CAFÉ DESCAFEINADO Café torrado e moído a vácuo, 250 gr", cafe.TM_DESCAF),
    ("CESTA BÁSICA: arroz 5kg; feijão 1kg; café 500g; açúcar 2kg", cafe.CESTA),
    ("Açúcar cristal 1kg 2 pct; arroz 1kg; biscoito 400g; café em pó 250g; óleo", cafe.CESTA),
])
def test_tipo(desc: str, esperado: str) -> None:
    item = cafe.classificar(desc, "Unidade")
    assert item is not None and item.tipo == esperado


@pytest.mark.parametrize("desc", [
    "Copo descartável 50 ml para café",
    "Filtro de papel para café nº 103",
    "Garrafa térmica 1 litro para café",
    "Açúcar refinado 1 kg",
    "Fornecimento de café da manhã para eventos",
    "Serviço de coffee break para 100 pessoas, com café, sucos e salgados",
    "Cafeteira elétrica 30 xícaras",
    "Máquina de café expresso automática",
    "Cápsula de chá de camomila",
])
def test_nao_e_cafe(desc: str) -> None:
    assert cafe.classificar(desc, "Unidade") is None


@pytest.mark.parametrize("desc,un,vu,kgu,src", [
    ("Café torrado e moído, pacote 500g", "Pacote", 30.0, 0.5, "descrição do item"),
    ("Café torrado e moído", "PACOTE 250.0 GRAMAS", 15.0, 0.25, "unidade de compra"),
    ("Café torrado e moído", "Pacote KG", 40.0, 1.0, 'unidade "Pacote KG"'),
    # unidade oficial vence a descrição: preço é por kg
    ("CAFÉ SUPERIOR, ENTREGA EM EMBALAGEM DE 500 GR", "KG (KG)", 60.6, 1.0, "unidade = kg"),
    ("Café pó, em embalagens a vácuo de 10x500g", "FRD", 414.72, 5.0, "descrição do item (caixa/fardo)"),
    ("CAFÉ EM PÓ VÁCUO 250G, CAIXA COM 20 UNIDADES", "CX", 400.0, 5.0, "descrição do item (caixa/fardo)"),
    ("Café torrado e moído, 250g", "Caixa G", 21.71, 0.25, "descrição do item"),  # caixa = 1 pacote pelo preço
    ("Café torrado e moído, 500g", "cx", 303.22, None, "fardo/caixa sem nº de pacotes"),  # caixa com vários
    ("Café solúvel frasco 180g, embalagem de 200g", "Frasco", 30.0, None, "vários tamanhos na descrição"),
    ("Café torrado e moído", "Unidade", 20.0, None, "tamanho não informado"),
    ("Café em pó, características químicas exigidas para cada 100g; pacote 500g", "PCT", 30.0, 0.5, "descrição do item"),
])
def test_peso_unitario(desc: str, un: str, vu: float, kgu: float | None, src: str) -> None:
    item = cafe.classificar(desc, un, vu)
    assert item is not None and (item.kgu, item.kg_src) == (kgu, src)


def test_exigencias() -> None:
    t = cafe.norm("Selo de pureza ABIC, 100% arábica, nota de qualidade global mínima 6,0, laudo, "
                  "validade mínima de 12 meses, similar ou superior a Melitta, amostra em 3 dias")
    assert cafe.exigencias(t) == ["ABIC/pureza", "Marca ref.", "Nota QG/sensorial", "Laudo", "100% arábica",
                                  "Amostra", "Validade ≥12 meses"]
    assert "Validade ≥3 meses" in cafe.exigencias(cafe.norm("validade residual mínima de 90 dias"))


def test_categoria_nao_confunde_ou_superior() -> None:
    assert cafe.categoria(cafe.norm("café tradicional, qualidade similar ou superior a Melitta")) == "Tradicional"
    assert cafe.categoria(cafe.norm("CATEGORIA SUPERIOR, extraforte")) == "Superior/Extraforte"


def test_conferir_faixa_de_preco() -> None:
    assert cafe.precisa_conferir(9.3) and cafe.precisa_conferir(500)
    assert not cafe.precisa_conferir(66.03) and not cafe.precisa_conferir(300) and not cafe.precisa_conferir(None)


def test_concordancia_com_painel_original() -> None:
    """Regressão: o classificador concorda com os rótulos do painel original (17/10/2026) em
    tipo e peso, salvo divergências conferidas uma a uma (erros do original ou regra deliberada)."""
    data = json.loads((ROOT / "tests" / "fixtures" / "itens_originais.json").read_text(encoding="utf-8"))
    tipo_ok = kgu_ok = 0
    for i in data:
        x = cafe.classificar(i["espec"], i["un"], i["vu"])
        assert x is not None, i["espec"][:80]
        tipo_ok += x.tipo == i["tipo"]
        kgu_ok += x.kgu == i["kgu"]
    assert tipo_ok >= len(data) - 1   # 1: "café pronto para servir" que o original chamou de torrado e moído
    assert kgu_ok >= len(data) - 2    # 2: unidade "KG" com texto de 500 g; "CX" com peso único e preço plausível
