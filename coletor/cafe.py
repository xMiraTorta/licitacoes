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
# Escopo do dono (18/10/2026): só café torrado, moído ou em grão. Solúvel, cápsula, bebida pronta e cesta ficam de fora.
TIPOS_TORRADOS = (TM, TM_DESCAF, GRAO)
CRU = "Café cru (verde)"

# "Café da manhã"/"coffee break" são serviços.
_SERVICO = re.compile(r"cafe da manha|cafe colonial|coffee ?-?break|coffe ?-?break|cafe regional")
_CESTA_INICIO = re.compile(r"^(\W|\d|item|lote|aquisicao( de)?)*\s*(cestas?|kits?)\b")
_BASICOS = re.compile(r"\b(arroz|feijao|acucar|oleo|macarrao|farinha|fuba|sal|biscoito|leite em po|sardinha|extrato de tomate)\b")
_TEM_CAFE = re.compile(r"\bcafe\b")
# Começos que indicam utensílio ou serviço mesmo listando alimentos ("jogo de porta-mantimentos: café, açúcar...").
_UTENSILIO = re.compile(r"^(\W|\d)*\s*(jogo|conjunto|porta|potes?|kit (de )?cozinha|brinquedo|fornecimento de alimentacao|refeic|almoco|"
                        r"\[[^\]]*\]\s*-?\s*conjunto)")


def _tipo(t: str, un: str) -> str:
    """Tipo pelo começo da descrição (onde fica o produto); o resto costuma ser especificação."""
    t = t[:200]
    if re.search(r"\b(cru|crus|verde|verdes)\b", t[:80]) and not re.search(r"torrad", t[:120]):
        return CRU  # café verde/cru (beneficiado), não torrado
    if re.search(r"\bdescafeinado\b", t) and not re.search(r"soluvel|capsula", t):
        return TM_DESCAF
    if re.search(r"\bcapsula", t):
        return CAPSULA
    if re.search(r"\bsoluvel\b", t):
        return SOLUVEL
    if re.search(r"cafe (com leite )?pronto|pronto para (servir|consumo)|coado no momento|bebida (de )?cafe|cafe liquido|"
                 r"liquido aquecido|garrafa (termica )?(de|com) ?\d+ ?(l|litros)", t) or norm(un) in {"litro", "l", "l (l)", "litros"}:
        return BEBIDA
    if re.search(r"em graos?\b|grao inteiro|torrado em grao|graos? (inteiros|para maquina)", t) and not re.search(r"moid|moagem|\bem po\b", t):
        return GRAO
    return TM


# Versão das regras de classificação. Mude ao alterar o que conta como café: o cache de compras
# "sem café" (coletor/cache/sem_cafe.json) de outra versão é descartado e tudo é verificado de novo.
VERSAO_REGRAS = 2  # nível/nota (18/10) não muda o que é café: cache continua válido

# Ruído antes do nome do produto: "(COTA)", "[COTA RESERVADA ME/EPP] -", "Lote 1: Item 4 -", "(L3) 8910.10465-",
# "GENEROS ALIMENTICIOS -", e embalagem/verbo/rótulo: "Aquisição de", "Pacote de", "Pct de", "Produto:".
_RUIDO = re.compile(r"^(?:[\W\d_]+|lote\b|item\b|unico\b|cota\b|ampla\b|concorrencia\b|reservada\b|exclusiv\w*|"
                    r"me/epp\b|me\b|epp\b|generos?\b|alimenticios?\b|\(l\d+\)|l\d+\b|"
                    r"aquisicao\b|compra\b|fornecimento\b|pacotes?\b|pcts?\b|caixas?\b|cx\b|fardos?\b|embalage(?:m|ns)\b|"
                    r"unidades?\b|produtos?\b|descricao\b|especificacao\b|objeto\b|nome\b|"
                    r"material de (?:copa|consumo|expediente)(?: e cozinha)?\b|de\b|do\b|da\b)+")
# O produto (começo da descrição, sem o ruído) precisa ser café.
_PRODUTO_CAFE = re.compile(r"^(cafe\b|cafecafe|po (de |para )?cafe\b|capsulas?\b|bebida (de )?cafe\b)")


def eh_item_de_cafe(descricao: str) -> str | None:
    """CESTA para cesta/kit com café; "?" para item de café (tipo decidido depois); None se não for café.

    Exige que a descrição COMECE pelo produto café: "Muda de planta tipo: café", "Caqui café",
    "Ponte na comunidade Ribeirão Café" e "Moedor de café" não são compras de café."""
    t = _SERVICO.sub(" ", norm(descricao))  # "café da manhã", "coffee break": não é o produto café
    tem_cafe = bool(_TEM_CAFE.search(t)) or "cafecafe" in t[:30]
    if not tem_cafe:
        return None
    cabeca = t[:150]
    basicos = len(set(_BASICOS.findall(t)))
    if not _UTENSILIO.match(cabeca) and (
            basicos >= 3 or (_CESTA_INICIO.match(cabeca) and re.search(r"cestas? (basica|de alimento|natalin)", cabeca))):
        return CESTA
    produto = _RUIDO.sub("", cabeca)
    if not _PRODUTO_CAFE.match(produto):
        return None
    if produto.startswith("capsula") and not _TEM_CAFE.search(produto[:60]):
        return None  # cápsula de chá, achocolatado
    return "?"


# ---------------------------------------------------------------- categoria
_CATS = [
    # "especial" só quando qualifica o café ("café especial", "categoria especial", "arábica especial"):
    # "grupo especial" (termo de classificação), "Melitta especial" (marca) e "farinha especial" não contam.
    ("Gourmet/especial", re.compile(r"\bgourmet\b|\b(?:categoria|estilo|qualidade|cafes?|arabica|po|moido)\s+especia(?:l|is)\b")),
    # "superior a 6,0", "igual ou superior", "qualidade superior" (de marca equivalente) não são a categoria;
    # "categoria superior ou acima/melhor" é.
    ("Superior", re.compile(r"(?<!\bou )(?<!\be )(?<!qualidade )\bsuperior\b(?! (?:a|ao|as|aos|de)\b)(?! ou (?:igual|inferior)\b)")),
    # "preparo tradicional por filtragem" é o modo de preparo, não a categoria
    ("Tradicional", re.compile(r"(?<!preparo )(?<!preparo o )(?<!forma )(?<!modo )(?<!metodo )(?<!maneira )\btradicional\b"
                               r"(?! (?:por|de|em) (?:filtra|coa|coad|pano|papel))")),
    ("Extraforte", re.compile(r"extra ?-?forte|\bintensa\b")),
]


_NEGA_CAT = re.compile(r"(?:nao (?:sera |serao )?(?:aceit|admitid|permitid)|vedad[oa]s?|proibid[oa]s?|exceto|nao pode)[^.;]{0,25}$")


def categoria(t: str) -> str:
    """Categorias citadas; "não será aceito o sabor extraforte" não conta."""
    return "/".join(nome for nome, rx in _CATS if any(not _NEGA_CAT.search(t[max(0, m.start() - 45):m.start()])
                                                       for m in rx.finditer(t)))


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
    if not unidade.startswith(("k", "q")) and re.fullmatch(r"\d{1,3}\.\d{3}", valor):
        valor = valor.replace(".", "")  # "1.000g": ponto de milhar, não decimal
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
    ("100% arábica", r"100\s*%\s*(da especie |de cafe |de graos? |de )?(cafe )?arabica(?!\w| ?(e/ou|ou|e|/) ?(cafe )?(conilon|robusta|canephora))"),
    ("PQC", r"\bpqc\b|programa de qualidade do cafe"),
    ("Sem glúten (rótulo)", r"gluten"),
    ("Amostra", r"\bamostras?\b"),
    ("Agric. familiar", r"agricultura familiar|agricultor(es)? familia"),
    ("Sem PVA (grãos selecionados)", r"(isent[oa]s?|livres?|ausencia|sem) de (graos )?(defeitos )?(pretos|verdes|ardidos|pva|fermentados)"),
    ("Premium/1ª qualidade (termo comercial)", r"\bpremium\b|primeira qualidade|\b1[ao]? qualidade"),
    ("Grãos selecionados", r"graos? (?:de cafe )?selecionados"),
    # "não aceita conilon", "proibido robusta" e "embalagem robusta" não contam (ver exigencias).
    ("Aceita conilon/blend", r"conilon|canephora|(?:cafe|especie|coffea|graos?|arabica)\W+(?:\w+\W+){0,2}robusta|robusta\W*(?:/|ou|e)\W*conil|predominantemente arabic|arabica (?:e|/|ou) (?:o |cafe )?(?:conilon|robusta)"),
]
_VALIDADE = re.compile(
    r"validade[^.;]{0,60}?(?:minim[ao]|nao inferior a|superior a|de no minimo|minimo de|pelo menos|acima de)?\s*"
    r"(?:de\s+)?(\d{1,3})\s*(?:\([a-z ]+\)\s*)?(meses|mes|dias|anos?)\b")


_NEGA = re.compile(r"(?:nao|vedad[oa]s?|proibid[oa]s?|sem|isent[oa] de|nao sera aceit\w*|nao se aceita|nao e permitid\w*)\W+(?:\w+\W+){0,3}$")


def exigencias(t: str) -> list[str]:
    tags = []
    for nome, rx in _TAGS:
        ms = list(re.finditer(rx, t))
        if nome == "Aceita conilon/blend":  # "não aceita conilon", "vedado o uso de robusta"
            ms = [m for m in ms if not _NEGA.search(t[max(0, m.start() - 40):m.start()])]
        if ms:
            tags.append(nome)
    m = _VALIDADE.search(t)
    if m:
        n, u = int(m.group(1)), m.group(2)
        meses = n * 12 if u.startswith("ano") else round(n / 30) if u == "dias" else n
        if 1 <= meses <= 36:
            tags.append(f"Validade ≥{meses} meses")
    return tags


# ---------------------------------------------------------------- nível de exigência
# "Sem categoria": o texto não pede categoria (Tradicional/Superior/Gourmet), selo ABIC/PQC nem nota de qualidade;
# pode pedir outras coisas (vácuo, validade, "premium"), que aparecem como exigências.
# Escala do PQC/ABIC para a nota de Qualidade Global (0 a 10): Tradicional/Extraforte 4,5 a 5,9;
# Superior 6,0 a 7,2; Gourmet 7,3 a 10. Pontuação em 0-100 (ex.: "70 pontos", "80 pontos SCA") vira /10.
NIVEIS = ("Sem categoria", "Tradicional", "Superior", "Gourmet/especial")
_TIPOS_COM_NIVEL = (TM, TM_DESCAF, GRAO)
_QG = re.compile(r"(?:qualidade global|pontuacao(?: global| sensorial| final)?|nota(?: de qualidade| sensorial| global| final)?|\bqg\b|"
                 r"escala sensorial|avaliacao sensorial|analise sensorial)"
                 r"([^.;]{0,45}?)(?<![\d,.])(\d{1,3}(?:[,.]\d{1,2})?)(?![\d%])(\s*\w*)")
_QG_FAIXA = re.compile(r"\s*(?:pontos\s*)?(?:-|a|ate|e)\s*(\d{1,3}(?:[,.]\d{1,2})?)(?![\d%])")
# "nota: validade mínima de 90 dias", "nota fiscal nº 12": número que não é nota de qualidade.
_QG_NAO = re.compile(r"validade|prazo|fiscal|entrega|empenho|dias|meses|anos|horas|item|lote|provador|amostra|pacote|"
                     r"unidade|norma|\bn\.?\s*$")  # "nº 12" (o º some na normalização); "no mínimo" continua valendo
# "análise sensorial realizada por 5 provadores": nessas palavras, o número só é nota se vier com nota/mínima/pontos.
_SENSORIAL = re.compile(r"escala sensorial|avaliacao sensorial|analise sensorial")
_NOTA_PERTO = re.compile(r"nota|minim|pontos|escala|igual ou superior|acima de|maior que")


def nota_qg(t: str) -> float | None:
    """Nota mínima de qualidade exigida (0 a 10), quando o texto cita uma. "Mínima de 4,5 a 5,9" -> 4,5."""
    for m in _QG.finditer(t):
        if _QG_NAO.search(m.group(1)) or _QG_NAO.search(m.group(3)):
            continue
        if _SENSORIAL.match(m.group(0)) and not _NOTA_PERTO.search(m.group(0)[len(_SENSORIAL.match(m.group(0)).group(0)):]
                                                                    + t[m.end(): m.end() + 12]):
            continue
        v = _escala_10(float(m.group(2).replace(",", ".")))
        if not 4 <= v <= 10:
            continue
        if (faixa := _QG_FAIXA.match(t, m.end(2))):  # "7,2 - 6,0", "4,5 a 5,9": vale o mínimo
            v2 = _escala_10(float(faixa.group(1).replace(",", ".")))
            if 4 <= v2 <= 10:  # "nota 7,0 - 500g": o 500 não é parte da faixa
                v = min(v, v2)
        return round(v, 2)
    return None


def _escala_10(v: float) -> float:
    return v / 10 if 10 < v <= 100 else v


# Bebida fina da classificação oficial (IN MAPA 8/2003): "mole"/"apenas mole" = Superior ou acima.
# "Mole a dura", "mole a rio" são faixas que aceitam café comercial (padrão CEPEA: tipo 6, bebida dura).
_MOLE = re.compile(r"bebida\W+(?:\w+\W+)?(?:apenas |estritamente )?mole\b(?! (?:a|ou|ate) (?:dura|rio|riad|apenas|\w+ dura))")


def nivel(t: str, tipo: str, cat: str, tags: list[str], qg: float | None) -> str | None:
    """Nível de qualidade pedido (inferido do texto; o maior que o item indicar). None para tipos sem
    comparação de preço por qualidade (solúvel, cápsula, bebida, cesta)."""
    if tipo not in _TIPOS_COM_NIVEL:
        return None
    cats = {x.rstrip("*") for x in cat.split("/")}  # "Superior*": categoria tirada do edital
    if "Gourmet" in cats or "especial" in cats or (qg is not None and qg >= 7.3) or "estritamente mole" in t:
        return "Gourmet/especial"
    if "Superior" in cats or (qg is not None and qg >= 6.0) or _MOLE.search(t):
        return "Superior"
    if cats & {"Tradicional", "Extraforte"} or qg is not None or {"ABIC/pureza", "PQC"} & set(tags):
        return "Tradicional"
    return "Sem categoria"


# ---------------------------------------------------------------- item completo
@dataclass
class ItemCafe:
    tipo: str
    cat: str
    emb: str
    kgu: float | None
    kg_src: str
    tags: list[str] = field(default_factory=list)
    nivel: str | None = None
    qg: float | None = None


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
    cat, tags, qg = categoria(t), exigencias(t), nota_qg(t)
    return ItemCafe(tipo, cat, embalagem(t, kg_pacote), kgu, src, tags, nivel(t, tipo, cat, tags, qg), qg)


def precisa_conferir(rkg: float | None) -> bool:
    return rkg is not None and not (RKG_MIN <= rkg <= RKG_MAX)
