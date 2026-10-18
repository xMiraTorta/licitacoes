"""Monta os registros de compra no formato de data.json a partir das respostas do PNCP."""
from __future__ import annotations

import html
import re
from typing import Any
from urllib.parse import urlparse

from coletor import cafe, distancias


ESFERAS = {"F": "Federal", "E": "Estadual", "M": "Municipal", "D": "Distrital", "N": "Não se aplica"}
MODALIDADES = {"Pregão - Eletrônico": "Pregão Eletrônico", "Pregão - Presencial": "Pregão Presencial"}

# Domínio do link de origem -> plataforma onde a proposta é enviada (tabela do painel original).
PLATAFORMAS_DOMINIO = {
    "cnetmobile.estaleiro.serpro.gov.br": "Compras.gov.br",
    "compras.gov.br": "Compras.gov.br",
    "portaldecompraspublicas.com.br": "Portal de Compras Públicas",
    "licitanet.com.br": "Licitanet",
    "bllcompras.com": "BLL Compras",
    "bllcompras.com.br": "BLL Compras",
    "bnccompras.com": "BNC – Bolsa Nacional de Compras",
    "app2.licitardigital.com.br": "Licitar Digital",
    "licitardigital.com.br": "Licitar Digital",
    "app2.ammlicita.org.br": "AMM Licita (Licitar Digital)",
    "comprasbr.com.br": "ComprasBR",
    "precodereferencia.m2atecnologia.com.br": "M2A",
    "licitacoes-e2.bb.com.br": "Licitações-e (Banco do Brasil)",
    "licitacoes-e.com.br": "Licitações-e (Banco do Brasil)",
    "www1.compras.mg.gov.br": "Portal de Compras MG",
    "licitamaisbrasil.com.br": "Licita Mais Brasil",
    "bbmnet.com.br": "BBMNET",
    "novobbmnet.com.br": "BBMNET",
}
# Sistema que publicou no PNCP (usuarioNome) que é, ele próprio, a plataforma de disputa.
PLATAFORMAS_PUBLICADOR = {
    "Compras.gov.br": "Compras.gov.br",
    "BLL Compras": "BLL Compras",
    "Licitanet Licitações Eletrônicas LTDA": "Licitanet",
    "ECustomize Consultoria em Software S.A": "Portal de Compras Públicas",
    "Bolsa Nacional De Compras - BNC": "BNC – Bolsa Nacional de Compras",
    "Licitar Digital - Plataforma de Licitações Online": "Licitar Digital",
    "M2A tecnologia": "M2A",
    "Licitações-E BB": "Licitações-e (Banco do Brasil)",
    "Novo BBMNET Licitações": "BBMNET",
    "Portal de Compras do Estado de Minas Gerais": "Portal de Compras MG",
    "Licita + Brasil": "Licita Mais Brasil",
    "Compras Pará": "Compras Pará",
}

ORDEM_TIPOS = {t: n for n, t in enumerate((cafe.TM, cafe.TM_DESCAF, cafe.SOLUVEL, cafe.GRAO, cafe.CAPSULA,
                                           cafe.BEBIDA, cafe.CESTA))}
ABREV = {cafe.TM: "T&M", cafe.TM_DESCAF: "T&M descaf.", cafe.SOLUVEL: "Solúvel", cafe.GRAO: "Grão",
         cafe.CAPSULA: "Cápsula", cafe.BEBIDA: "Café pronto", cafe.CESTA: "Cesta/kit"}
ME_ITEM = {1: "Exclusivo", 2: "Não", 3: "Cota reservada", 4: "Não", 5: "Não se aplica"}
SIZES_F = {"500g": "500 g", "250g": "250 g", "1kg": "1 kg"}
EMB_F = {"vácuo": "Vácuo", "almofada": "Almofada", "lata": "Lata", "sachê": "Sachê", "vidro/frasco": "Vidro/frasco",
         "c/ válvula": "C/ válvula", "granel": "Granel"}


def plataforma(link: str | None, publicador: str | None) -> tuple[str, str, str]:
    """(plat, plat_src, plat_f)."""
    pub = (publicador or "").strip()
    if link:
        host = urlparse(link).netloc.lower()
        dom = host.removeprefix("www.")
        if dom in PLATAFORMAS_DOMINIO:
            p = PLATAFORMAS_DOMINIO[dom]
            return p, "link de origem (PNCP)", p
        if host:
            return f"Portal próprio: {host}", "link de origem (PNCP)", "Portal próprio do órgão"
    if pub in PLATAFORMAS_PUBLICADOR:
        p = PLATAFORMAS_PUBLICADOR[pub]
        return p, "publicado pela própria plataforma", p
    return f"Ver edital (publicado via {pub or 'sistema não informado'})", "não derivável", "Não identificada (ver edital)"


def limpar_texto(s: str | None) -> str:
    """Remove HTML que alguns sistemas mandam na descrição (<p>, &nbsp;) e espaços repetidos."""
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s or "")).split())


def _num(v: Any) -> float | None:
    """Valor numérico do PNCP; 0 e ausente viram None (valor sigiloso ou não informado nunca é zero)."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f > 0 else None


def montar_item(raw: dict[str, Any]) -> dict[str, Any] | None:
    sig = bool(raw.get("orcamentoSigiloso"))
    vu = None if sig else _num(raw.get("valorUnitarioEstimado"))
    vt = None if sig else _num(raw.get("valorTotal"))
    un = str(raw.get("unidadeMedida") or "")
    espec = limpar_texto(raw.get("descricao"))
    if (compl := limpar_texto(raw.get("informacaoComplementar"))) and compl not in espec:
        espec += f" | Inf. compl.: {compl}"  # mesmo formato do painel original; às vezes o peso só está aqui
    c = cafe.classificar(espec, un, vu)
    if c is None:
        return None
    qtd = _num(raw.get("quantidade"))
    kgt = round(c.kgu * qtd, 4) if c.kgu is not None and qtd is not None else None
    rkg = round(vt / kgt, 2) if vt is not None and kgt else None
    return {
        "n": raw.get("numeroItem"), "tipo": c.tipo, "cat": c.cat, "emb": c.emb, "kgu": c.kgu, "kg_src": c.kg_src,
        "qtd": qtd, "un": un, "vu": vu, "vt": vt, "sig": sig, "kgt": kgt, "rkg": rkg,
        "conferir": cafe.precisa_conferir(rkg), "me": ME_ITEM.get(raw.get("tipoBeneficio"), "Não se aplica"),
        "sit": raw.get("situacaoCompraItemNome") or "", "tags": c.tags, "espec": espec,
        "usa_trecho": False,
    }


def _me(itens: list[dict[str, Any]]) -> tuple[str, list[str]]:
    n = len(itens)
    exc = sum(i["me"] == "Exclusivo" for i in itens)
    cota = any(i["me"] == "Cota reservada" for i in itens)
    if exc == n:
        return "Exclusivo ME/EPP", ["Exclusiva ME/EPP (todos os itens)"]
    if exc:
        txt = f"Exclusivo em {exc} de {n} itens" + (" + Cota reservada ME/EPP" if cota else "")
        return txt, ["Exclusiva em parte dos itens"] + (["Cota reservada ME/EPP"] if cota else [])
    if cota:
        return "Cota reservada ME/EPP", ["Cota reservada ME/EPP"]
    if all(i["me"] == "Não se aplica" for i in itens):
        return "Não se aplica", ["Não se aplica / não informado"]
    return "Ampla (sem exclusividade)", ["Ampla concorrência"]


def _uniq(xs: list[str]) -> list[str]:
    return list(dict.fromkeys(x for x in xs if x))


def _emb_f(embs: list[str]) -> list[str]:
    out: list[str] = []
    for e in embs:
        partes = e.split(" ")
        tam = partes[0] if partes and re.fullmatch(r"[\d.]+k?g", partes[0]) else ""
        if tam:
            out.append(SIZES_F.get(tam, "Outro tamanho"))
        for flag in (partes[-1] if not tam or len(partes) > 1 else "").split("/"):
            if flag in EMB_F:
                out.append(EMB_F[flag])
    return _uniq(out) or ["Não informada"]


def _resumo(i: dict[str, Any]) -> str:
    tam = i["emb"].split(" ")[0] if re.match(r"[\d.]+k?g\b", i["emb"]) else i["emb"]
    qtd = f"{i['qtd']:g}" if i["qtd"] is not None else "?"
    return f"{ABREV.get(i['tipo'], i['tipo'])}{' ' + tam if tam else ''} ×{qtd} {i['un']}".strip()


def montar_compra(c: dict[str, Any], itens_raw: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Registro completo da compra, ou None se não houver item de café."""
    itens = [x for x in (montar_item(r) for r in itens_raw) if x]
    if not itens:
        return None
    org, uni = c.get("orgaoEntidade") or {}, c.get("unidadeOrgao") or {}
    cnpj, ano, seq = org.get("cnpj", ""), c.get("anoCompra"), c.get("sequencialCompra")
    km, minutos = distancias.estrada(uni.get("codigoIbge"))  # por estrada, a partir de Uberaba
    cafe_it = [i for i in itens if i["tipo"] != cafe.CESTA]
    cesta_it = [i for i in itens if i["tipo"] == cafe.CESTA]
    vts = [i["vt"] for i in cafe_it if i["vt"] is not None]
    kgs = [i["kgt"] for i in itens if i["kgt"] is not None]
    rk = [i for i in itens if i["rkg"] is not None and not i["conferir"]]
    kg = round(sum(kgs), 4) if kgs else None
    plat, plat_src, plat_f = plataforma(c.get("linkSistemaOrigem"), c.get("usuarioNome"))
    me, me_f = _me(itens)
    embs = _uniq([i["emb"] for i in itens])
    # Como no painel original, "Gourmet/especial" vira duas opções de filtro: "Gourmet" e "especial".
    cats = _uniq([p for i in itens for p in i["cat"].split("/")])
    return {
        "chave": c["numeroControlePNCP"],
        "fim": (c.get("dataEncerramentoProposta") or "")[:16] or None,
        "abre": (c.get("dataAberturaProposta") or "")[:16] or None,
        "publicado": (c.get("dataPublicacaoPncp") or "")[:16] or None,
        "first_seen": None, "nova": False,
        "uf": uni.get("ufSigla", ""), "mun": uni.get("municipioNome", ""), "dist": km, "dist_min": minutos,
        "orgao": org.get("razaoSocial", ""), "unidade": uni.get("nomeUnidade", ""),
        "esfera": ESFERAS.get(org.get("esferaId", "N"), "Não se aplica"),
        "mod": MODALIDADES.get(c.get("modalidadeNome", ""), c.get("modalidadeNome", "")),
        "num": f"{c.get('numeroCompra', '')}/{ano}", "plat": plat, "plat_src": plat_src, "plat_f": plat_f,
        "publicado_via": c.get("usuarioNome") or "",
        "uasg": str(uni.get("codigoUnidade") or "") if plat == "Compras.gov.br" else "",
        "srp": "Sim" if c.get("srp") else "Não", "objeto": (c.get("objetoCompra") or "").strip(),
        "link_pncp": f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{seq}", "link_plat": c.get("linkSistemaOrigem") or "",
        "ed_tags": [], "ed_pz": "", "edital_lido": False, "trecho_edital": "",
        "tipos": sorted(_uniq([i["tipo"] for i in itens]), key=lambda t: ORDEM_TIPOS.get(t, 99)), "cats": cats or ["Não informada"], "cat_do_edital": False,
        "embs": "; ".join(embs), "emb_f": _emb_f(embs),
        "vcafe": round(sum(vts), 2) if vts else None,
        "vcesta": round(sum(i["vt"] for i in cesta_it if i["vt"] is not None), 2) if any(i["vt"] for i in cesta_it) else None,
        "kg": kg,
        "kg_parcial": kg is not None and any(i["kgt"] is None and i["tipo"] != cafe.CESTA for i in itens),
        "rkg": round(sum(i["vt"] for i in rk) / sum(i["kgt"] for i in rk), 2) if rk else None,
        "sig": "Sim" if any(i["sig"] for i in itens) else "Não",
        "me": me, "me_f": me_f, "tags": _uniq([t for i in itens for t in i["tags"]]),
        "resumo": "; ".join(_resumo(i) for i in itens),
        "dup": "", "dup_of": None, "dup_group": [],
        "itens": itens,
    }


def _completude(c: dict[str, Any]) -> tuple[int, ...]:
    return (int(c["edital_lido"]), int(bool(c["link_plat"])), int(c["kg"] is not None), len(c["itens"]), len(c["tags"]))


def marcar_duplicatas(compras: list[dict[str, Any]], visiveis_antes: set[str] = frozenset()) -> None:
    """Mesmo município/UF, mesmo valor de café (ou, sem valor, mesmos itens) e mesmo dia de prazo final:
    provável mesma compra publicada duas vezes. Fica visível a que já era visível na coleta anterior
    (não esconder favoritas); senão a mais completa, depois a mais recente. As outras recebem dup_of.
    Sem valor e com itens diferentes, não agrupa: melhor mostrar as duas do que esconder uma compra real."""
    grupos: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for c in compras:
        c["dup"], c["dup_of"], c["dup_group"] = "", None, []
        if not c["fim"]:
            continue
        valor = round(c["vcafe"]) if c["vcafe"] is not None else ("sem valor", c["resumo"])
        grupos.setdefault((c["uf"], c["mun"], valor, c["fim"][:10]), []).append(c)
    for g in grupos.values():
        if len(g) < 2:
            continue
        g.sort(key=lambda c: (c["chave"] in visiveis_antes, _completude(c), c.get("publicado") or ""), reverse=True)
        for c in g:
            outros = [x["chave"] for x in g if x is not c]
            c["dup"] = "Possível duplicata de: " + ", ".join(outros)
            c["dup_group"] = outros
            if c is not g[0]:
                c["dup_of"] = g[0]["chave"]


# Campos que vieram da leitura de editais pelo painel original e que este coletor ainda não refaz.
CAMPOS_EDITAL = ("ed_tags", "ed_pz", "edital_lido", "trecho_edital", "cat_do_edital")


def herdar_do_anterior(novo: dict[str, Any], antigo: dict[str, Any]) -> None:
    """Preserva o que não dá para recalcular sem o edital: leitura do edital, plataforma citada no
    edital e categoria/exigências tiradas do trecho do edital. first_seen também é preservado."""
    novo["first_seen"] = antigo.get("first_seen") or novo["first_seen"]
    for k in CAMPOS_EDITAL:
        if k in antigo:
            novo[k] = antigo[k]
    if antigo.get("plat_src") in ("citado no edital", "edital cita mais de uma") and novo["plat_src"] != "link de origem (PNCP)":
        novo["plat"], novo["plat_src"], novo["plat_f"] = antigo["plat"], antigo["plat_src"], antigo["plat_f"]
        novo["uasg"] = antigo.get("uasg", novo["uasg"])
    velhos = {i.get("n"): i for i in antigo.get("itens", [])}
    for i in novo["itens"]:
        v = velhos.get(i["n"])
        if v and v.get("usa_trecho"):
            i["usa_trecho"] = True
            i["cat"] = v.get("cat", i["cat"])
            i["tags"] = _uniq(i["tags"] + list(v.get("tags", [])))
    if any(i["usa_trecho"] for i in novo["itens"]):
        novo["tags"] = _uniq([t for i in novo["itens"] for t in i["tags"]])
        novo["cats"] = _uniq([p.rstrip("*") for i in novo["itens"] for p in i["cat"].split("/")]) or ["Não informada"]
