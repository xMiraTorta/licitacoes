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
    ("BEBIDA CAFÉ: litro de café líquido sem leite para consumo em eventos", cafe.BEBIDA),
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
    # casos reais do PNCP (17/10/2026) que citam café sem ser compra de café
    "Muda De Planta tipo: café, espécie 2: coffea arábica, altura: 15",
    "Construção nova ponte Graciano Bogo na comunidade de Ribeirão Café",
    "Fruta tipo: caqui café, apresentação: natural",
    "Moedor De Alimento - Peça / Componente tipo: moedor de café",
    "Pazinha mexedora de cafe pacote c 500un plastica descartavel",
    "APARADOR DE CAFÉ COM ESPAÇO DESTINADO À ACOMODAÇÃO DE FRIGOBAR",
    "Promoção de Eventos Café, Água e Biscoitos",
    "Para coar café, confeccionado em 100% fibras celulósicas",
    "CAFETEIRA ELÉTRICA INDUSTRIAL 10 LITROS com dois reservatórios café e leite",
    "JOGO DE PORTA-MANTIMENTOS, PARA GUARDAR (CAFÉ, AÇÚCAR, FEIJÃO, ARROZ, SAL)",
    "KIT COZINHA/ POTES PARA CAFÉ E ACUÇAR",
    "CESTA RETANGULAR P/ PÃO DE CAFÉ DA MANHÃ - PCESTA RETANGULAR PARA PÃO, alimentos",
    "KIT COZINHA INFANTIL COM PANELINHAS, COOKTOP E UTENSÍLIOS: café, arroz e feijão de brinquedo",
    "FORNECIMENTO DE ALIMENTAÇÃO, almoço: arroz, feijão, salada, sal, café",
    # prefixos aceitos desde VERSAO_REGRAS 2 não podem abrir passagem para utensílios
    "Aquisição de cafeteira elétrica",
    "Pacote de açúcar para café",
    "Caixa térmica para café",
    "Pacote de biscoito sabor café",
    "Descrição: filtro de papel para café",
    "Fornecimento de café da manhã",
])
def test_nao_e_cafe(desc: str) -> None:
    assert cafe.classificar(desc, "Unidade") is None


@pytest.mark.parametrize("desc", [
    "CAFÉCafé - torrado, moagem fina ou média",
    "Lote 1: LOTE 01 - Item 4 - Lote 1: CAFE",
    "[COTA RESERVADA ME/EPP] - Café torrado e moído 500g",
    "(L3) 8910.10465-Café, TIPO: Torrado e moído",
    "LOTE UNICO - GENEROS ALIMENTICIOS - CAFE, torrado e moido",
    "Aquisição de café torrado e moído 500g",
    "Fornecimento de café torrado e moído",
    "Pacote de café 500g",
    "Pct de cafe 500 g",
    "Caixa de café 10x500g",
    "Produto: Café torrado",
    "Descrição: café torrado e moído",
    "Material de copa e cozinha - café torrado",
])
def test_cafe_com_ruido_no_inicio(desc: str) -> None:
    assert cafe.classificar(desc, "Pacote") is not None


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
    ("Café torrado e moído, pacote 1.000g", "Pacote", 40.0, 1.0, "descrição do item"),  # ponto de milhar
    ("Café torrado e moído, pacote 0.500 kg", "Pacote", 20.0, 0.5, "descrição do item"),
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


@pytest.mark.parametrize("texto,nota", [
    ("com nota de qualidade global minima de 4,5 a 5,9 na escala", 4.5),
    ("qualidade global igual ou superior a 6,0 pontos", 6.0),
    ("pontuacao global minima de 70 (setenta) pontos", 7.0),  # escala 0-100
    ("intervalo de notas da qualidade global: 7,2 - 6,0", 6.0),  # faixa: vale o mínimo
    ("nota de qualidade global na faixa acima de 83 pontos na escala sensorial", 8.3),
    ("nota: validade residual minima de 90 dias", None),
    ("nota fiscal n 12345", None),
    ("intensidade 7, certificado abic", None),
])
def test_nota_qualidade_global(texto: str, nota: float | None) -> None:
    assert cafe.nota_qg(texto) == nota


@pytest.mark.parametrize("desc,nivel", [
    ("Café torrado e moído 500g", "Sem exigência"),
    ("Café torrado e moído 500g, selo de pureza ABIC", "Tradicional"),
    ("Café torrado e moído tradicional 500g", "Tradicional"),
    ("Café torrado e moído, nota de qualidade global mínima de 4,5", "Tradicional"),
    ("Café torrado e moído superior 500g", "Superior"),
    ("Café torrado e moído, qualidade global igual ou superior a 6,0", "Superior"),
    ("Café 100% arábica bebida mole 500g", "Superior"),
    ("Café gourmet 250g", "Gourmet/especial"),
    ("Café torrado, nota de qualidade sensorial igual ou superior a 7,3", "Gourmet/especial"),
    ("Café em grãos torrados superior 1kg", "Superior"),
    ("Café solúvel 200g", None),  # solúvel/cápsula/bebida não entram na comparação por qualidade
    ("Cápsula de café 100% arábica", None),
])
def test_nivel_de_exigencia(desc: str, nivel: str | None) -> None:
    item = cafe.classificar(desc, "Pacote")
    assert item is not None and item.nivel == nivel
