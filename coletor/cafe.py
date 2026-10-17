"""Classificação de itens de compra: é café? que tipo, categoria, embalagem, peso e exigências.

Regras reconstruídas a partir dos rótulos do painel original (17/10/2026) e conferidas contra ele
em tests/test_cafe.py. Princípio: na dúvida, deixar em branco (None) em vez de chutar.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


def norm(s: str | None) -> str:
    """Minúsculas, sem acentos, espaços simples."""
    s = unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().lower()


TM = "Torrado e moído"
TM_DESCAF = "Torrado e moído (descafeinado)"
SOLUVEL = "Solúvel"
GRAO = "Grão"
CAPSULA = "Cápsula"
BEBIDA = "Café pronto (bebida)"
CESTA = "Cesta/kit"

# Produto citado ANTES de "café" no começo da descrição indica que o item é outra coisa
# (copo para café, filtro de café, açúcar...). "Café da manhã"/"coffee break" são serviços.
_NAO_CAFE_ANTES = re.compile(
    r"\b(copos?|copinhos?|colher(inha)?s?|garrafas?|filtros?|coador(es)?|xicaras?|bules?|maquinas?|acucar|adocante|"
    r"leite|biscoitos?|bolachas?|paes?|pao|chas?|achocolatado|mesas?|jogos?|conjuntos?|suportes?|porta|servicos?|"
    r"locacao|prestacao|toalhas?|bandejas?|chocolates?|jarras?|canecas?|potes?|capas?|refeic(ao|oes)|lanches?|"
    r"sacos?|papel|guardanapos?|mexedor(es)?|paletas?|creme|cappuccino|capuccino|bolos?|torradas?|armarios?|"
    r"descartave(l|is)|termica|aparelho|cafeteiras?)\b")
_SERVICO = re.compile(r"cafe da manha|cafe colonial|coffee ?-?break|coffe ?-?break|cafe regional")
_CESTA_INICIO = re.compile(r"^(\W|\d|item|lote|aquisicao( de)?)*\s*(cestas?|kits?)\b")
_BASICOS = re.compile(r"\b(arroz|feijao|acucar|oleo|macarrao|farinha|fuba|sal|biscoito|leite em po|sardinha|extrato de tomate)\b")
_TEM_CAFE = re.compile(r"\bcafe\b")


def _tipo(t: str, un: str) -> str:
    """Tipo pelo começo da descrição (onde fica o produto); o resto costuma ser especificação."""
    t = t[:200]
    if re.search(r"\bdescafeinado\b", t) and not re.search(r"soluvel|capsula", t):
        return TM_DESCAF
    if re.search(r"\bcapsula", t):
        return CAPSULA
    if re.search(r"\bsoluvel\b", t):
        return SOLUVEL
    if re.search(r"cafe (com leite )?pronto|pronto para (servir|consumo)|coado no momento|"
                 r"liquido aquecido|garrafa (termica )?(de|com) ?\d+ ?(l|litros)", t) or norm(un) in {"litro", "l", "l (l)", "litros"}:
        return BEBIDA
    if re.search(r"em graos?\b|grao inteiro|torrado em grao|graos? (inteiros|para maquina)", t) and not re.search(r"moid|moagem|\bem po\b", t):
        return GRAO
    return TM


def eh_item_de_cafe(descricao: str) -> str | None:
    """CESTA para cesta/kit com café; "?" para item de café (tipo decidido depois); None se não for café."""
    t = norm(descricao)
    tem_cafe = bool(_TEM_CAFE.search(t))
    if not tem_cafe and not re.search(r"\bcapsula", t):
        return None
    cabeca = t[:150]
    if tem_cafe and (_CESTA_INICIO.match(cabeca) or len(set(_BASICOS.findall(t))) >= 3):
        return CESTA
    m = re.search(r"\bcafe\b|\bcapsulas?\b", cabeca)
    if not m or _NAO_CAFE_ANTES.search(cabeca[:m.start()]) or _SERVICO.search(cabeca):
        return None
    if not tem_cafe:
        return None  # cápsula sem "café" no texto (chá, achocolatado)
    return "?"


# ---------------------------------------------------------------- categoria
_CATS = [
    ("Gourmet/especial", re.compile(r"\bgourmet\b|\bespecial\b|\bespeciais\b")),
    ("Superior", re.compile(r"(?<!ou )(?<!e )\bsuperior\b(?! (a|ao|as|aos|ou|de)\b)")),
    ("Tradicional", re.compile(r"\btradicional\b")),
    ("Extraforte", re.compile(r"extra ?-?forte|\bintensa\b")),
]


def categoria(t: str) -> str:
    return "/".join(nome for nome, rx in _CATS if rx.search(t))


# ---------------------------------------------------------------- peso e embalagem
# Faixa usual de R$/kg; fora dela, provável erro de unidade no edital (ex.: preço por pacote em "kg").
RKG_MIN, RKG_MAX = 25.0, 400.0
_PESO = re.compile(r"(\d{1,4}(?:[.,]\d{1,3})?)\s*(kg|kgs|klg|quilos?|quilogra\w*|kilos?|g|gr|grs|gramas?)\b")
_POR_100G = re.compile(r"(cada|por|em|/)\s*100\s*(g|gr|gramas?)\b")
_UN_KG = {"kg", "quilo", "quilograma", "kilo", "kgs", "quilos", "klg", "kg (kg)", "kg - quilograma", "quilogramas"}
# "caixa com 20 unidades", "fardo c/ 10 pacotes", "10x500g"
_N_PACOTES = re.compile(r"(?:com|contendo|c/)\s*(\d{1,3})\s*(?:\(\w+\)\s*)?(?:pacotes|pcts?|unidades|und|un|embalagens|saches)\b")
_N_X_PESO = re.compile(r"\b(\d{1,3})\s*x\s*(\d{1,4}(?:[.,]\d{1,3})?)\s*(kg|g|gr|gramas)\b")
_UN_FARDO = re.compile(r"\b(fardo|fardos|fd|frd|caixa|cx|cxs|caixas)\b")


def _kg(valor: str, unidade: str) -> float | None:
    try:
        v = float(valor.replace(",", "."))
    except ValueError:
        return None
    kg = v if unidade.startswith(("k", "q")) else v / 1000
    return kg if 0.01 <= kg <= 30 else None


def pesos_na_descricao(t: str) -> set[float]:
    sem = _POR_100G.sub(" ", t)
    out = set()
    for m in _PESO.finditer(sem):
        kg = _kg(m.group(1), m.group(2))
        if kg is not None:
            out.add(round(kg, 4))
    return out


def peso_unitario(t: str, un: str, tipo: str, vu: float | None = None) -> tuple[float | None, str]:
    """(kg por unidade comprada, origem da informação). None quando não é inequívoco.

    A unidade oficial do item vence a descrição: em "KG" o preço é por quilo, mesmo que o texto cite
    pacotes de 500 g. Em caixa/fardo só há peso se o texto disser quantos pacotes vêm dentro, ou se
    o preço mostrar que a "caixa" é um pacote só (R$/kg resultante na faixa usual).
    """
    if tipo in (CESTA, CAPSULA, BEBIDA):
        return None, ""
    u = norm(un)
    m = _PESO.search(u)
    if m and (kg := _kg(m.group(1), m.group(2))) is not None:
        return kg, "unidade de compra"
    if re.fullmatch(r"(pacote|pct|caixa|cx|embalagem)\s*kg", u):
        return 1.0, 'unidade "Pacote KG"'
    if u in _UN_KG:
        return 1.0, "unidade = kg"
    ps = pesos_na_descricao(t)
    if _UN_FARDO.search(u):
        mx = _N_X_PESO.search(t)
        if mx and (kg := _kg(mx.group(2), mx.group(3))) is not None:
            return round(int(mx.group(1)) * kg, 4), "descrição do item (caixa/fardo)"
        mn = _N_PACOTES.search(t)
        if mn and len(ps) == 1:
            return round(int(mn.group(1)) * next(iter(ps)), 4), "descrição do item (caixa/fardo)"
        if len(ps) == 1 and vu and RKG_MIN <= vu / next(iter(ps)) <= RKG_MAX:
            return next(iter(ps)), "descrição do item"
        return None, "fardo/caixa sem nº de pacotes"
    if len(ps) == 1:
        return ps.pop(), "descrição do item"
    if len(ps) > 1:
        return None, "vários tamanhos na descrição"
    return None, "tamanho não informado"


_EMB = [("vácuo", r"vacuo"), ("almofada", r"almofada"), ("lata", r"\blata\b"), ("sachê", r"\bsaches?\b"),
        ("vidro/frasco", r"\bvidro\b|\bfrasco\b"), ("c/ válvula", r"valvula"), ("granel", r"\bgranel\b")]


def tamanho_txt(kgu: float | None) -> str:
    if kgu is None:
        return ""
    return f"{kgu:g}kg" if kgu >= 1 else f"{round(kgu * 1000):g}g"


def embalagem(t: str, kgu: float | None) -> str:
    flags = "/".join(nome for nome, rx in _EMB if re.search(rx, t))
    return " ".join(x for x in (tamanho_txt(kgu), flags) if x)


# ---------------------------------------------------------------- exigências
_TAGS = [
    ("ABIC/pureza", r"\babic\b|selo de pureza"),
    ("Marca ref.", r"marca\s+(de\s+)?refer|referencia\s*:|ou similar|similar ou|equivalente ou superior|ou equivalente"),
    ("Nota QG/sensorial", r"qualidade global|nota (minima )?(de )?\d|analise sensorial|\bsensorial"),
    ("Laudo", r"\blaudo"),
    ("100% arábica", r"100\s*%\s*(da especie |de cafe |de graos? |de )?(cafe )?arabica"),
    ("PQC", r"\bpqc\b|programa de qualidade do cafe"),
    ("Sem glúten (rótulo)", r"gluten"),
    ("Amostra", r"\bamostras?\b"),
    ("Agric. familiar", r"agricultura familiar|agricultor(es)? familia"),
]
_VALIDADE = re.compile(
    r"validade[^.;]{0,60}?(?:minim[ao]|nao inferior a|superior a|de no minimo|minimo de|pelo menos|acima de)?\s*"
    r"(?:de\s+)?(\d{1,3})\s*(?:\([a-z ]+\)\s*)?(meses|mes|dias|anos?)\b")


def exigencias(t: str) -> list[str]:
    tags = [nome for nome, rx in _TAGS if re.search(rx, t)]
    m = _VALIDADE.search(t)
    if m:
        n, u = int(m.group(1)), m.group(2)
        meses = n * 12 if u.startswith("ano") else round(n / 30) if u == "dias" else n
        if 1 <= meses <= 36:
            tags.append(f"Validade ≥{meses} meses")
    return tags


# ---------------------------------------------------------------- item completo
@dataclass
class ItemCafe:
    tipo: str
    cat: str
    emb: str
    kgu: float | None
    kg_src: str
    tags: list[str] = field(default_factory=list)


def classificar(descricao: str, unidade: str, vu: float | None = None) -> ItemCafe | None:
    base = eh_item_de_cafe(descricao)
    if base is None:
        return None
    t = norm(descricao)
    tipo = CESTA if base == CESTA else _tipo(t, unidade)
    if tipo == CESTA:
        return ItemCafe(tipo, "", "", None, "", [])
    kgu, src = peso_unitario(t, unidade, tipo, vu)
    kg_pacote = kgu
    if src.endswith("(caixa/fardo)"):  # embalagem descreve o pacote, não o fardo
        mx = _N_X_PESO.search(t)
        kg_pacote = _kg(mx.group(2), mx.group(3)) if mx else next(iter(pesos_na_descricao(t)), None)
    return ItemCafe(tipo, categoria(t), embalagem(t, kg_pacote), kgu, src, exigencias(t))


def precisa_conferir(rkg: float | None) -> bool:
    return rkg is not None and not (RKG_MIN <= rkg <= RKG_MAX)
