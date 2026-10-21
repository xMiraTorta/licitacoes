"""Preço de varejo das marcas de referência, atualizado toda semana (pedido do dono em 18/10/2026).

Fonte: a busca pública das lojas virtuais de supermercado que usam a plataforma VTEX
(`/api/io/_v/api/intelligent-search/product_search/`), as mesmas da pesquisa de 18/10/2026. Para cada marca de
`marcas_cafe.json`, busca "café <marca>" em cada loja, separa os produtos por linha da marca (Tradicional,
Extra Forte, Gourmet...) pelo nome do produto, calcula R$/kg (pacotes de 250 g a 1 kg, só disponíveis) e grava
a faixa da semana. Linha sem oferta na semana mantém o preço anterior (com a data dele). A categoria ABIC de cada
linha não muda aqui (vem da pesquisa, planilha oficial da ABIC).
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

from coletor import cafe, marcas
from coletor.arquivos import gravar_atomico

LOJAS = ("www.mambo.com.br", "www.giassi.com.br", "www.covabra.com.br", "www.savegnago.com.br", "www.bistek.com.br",
         "www.supermuffato.com.br", "www.zonasul.com.br", "www.gbarbosa.com.br", "www.prezunic.com.br",
         "www.coopsupermercado.com.br", "www.mercantilrodrigues.com.br")
NOMES_LOJAS = {"www.mambo.com.br": "Mambo", "www.giassi.com.br": "Giassi", "www.covabra.com.br": "Covabra",
               "www.savegnago.com.br": "Savegnago", "www.bistek.com.br": "Bistek", "www.supermuffato.com.br": "Super Muffato",
               "www.zonasul.com.br": "Zona Sul", "www.gbarbosa.com.br": "GBarbosa", "www.prezunic.com.br": "Prezunic",
               "www.coopsupermercado.com.br": "Coop", "www.mercantilrodrigues.com.br": "Mercantil Rodrigues"}
BUSCA = "/api/io/_v/api/intelligent-search/product_search/"
MIN_LOJAS_OK = 6  # menos lojas respondendo que isso: algo errado (bloqueio, mudança na API); não grava
_FORA = re.compile(r"capsul|soluvel|cappuccino|capuccino|sache|drip|filtro|\bkit\b|caneca|leite|descafeinad|instantaneo|"
                   r"mocaccino|latte|\bcha\b|achocolatado|garrafa|pronto")
_PESO = re.compile(r"(\d+(?:[.,]\d+)?)\s*(kg|g|gr|gramas)\b")


@dataclass
class Oferta:
    loja: str
    url: str
    produto: str
    preco: float
    peso_g: int

    @property
    def rkg(self) -> float:
        return round(self.preco / self.peso_g * 1000, 2)


_N_X_PESO = re.compile(r"\b(\d{1,2})\s*x\s*(\d+(?:[.,]\d+)?)\s*(kg|g|gr|gramas)\b")  # "10x500g", "2x1kg"
_N_PACOTES = re.compile(r"(?:\bcom|c/)\s*(\d{1,2})\s*(?:unidades|unid|und|un|pacotes|pcts?)\b|\b(?:pack|kit)\s*(?:com|c/)?\s*(\d{1,2})\s*(?:un|unid|unidades|pacotes?)\b")
_LEVE_PAGUE = re.compile(r"\bleve\s*\d+\s*pague\s*\d+")  # preço de N pacotes, peso ambíguo: fora


def _peso_g(nome: str) -> int | None:
    """Peso do pacote em gramas, só entre 250 g e 1 kg. Pacote múltiplo ("10x500g", "500g c/ 2 unidades") conta o
    total, e acima de 1 kg fica fora: o preço é dos N pacotes e inflaria o R$/kg."""
    if _LEVE_PAGUE.search(nome):
        return None
    if (mx := _N_X_PESO.search(nome)):
        n, v, u = int(mx.group(1)), float(mx.group(2).replace(",", ".")), mx.group(3)
    else:
        m = _PESO.search(nome)
        if not m:
            return None
        v, u = float(m.group(1).replace(",", ".")), m.group(2)
        mp = _N_PACOTES.search(nome)
        n = int(mp.group(1) or mp.group(2)) if mp else 1
    g = n * (int(round(v * 1000)) if u == "kg" else int(round(v)))
    return g if 250 <= g <= 1000 else None


def _palavras_linha(linha: str) -> list[str]:
    """ "Gourmet (Cerrado Mineiro, Sul de Minas)" -> ["gourmet", "cerrado mineiro", "sul de minas"]."""
    t = cafe.norm(linha).replace("extra forte", "extraforte")
    return [p.strip() for p in re.split(r"[/(),]| e ", t) if p.strip() and p.strip() not in ("grao", "graos", "moido", "etc.", "etc")]


def _eh_grao(linha: str) -> bool:
    return bool(re.search(r"\bgraos?\b", cafe.norm(linha)))


def ofertas_da_resposta(loja: str, dados: dict[str, Any]) -> list[Oferta]:
    """Produtos disponíveis de uma resposta da busca VTEX, com peso entre 250 g e 1 kg."""
    out = []
    for p in dados.get("products") or []:
        nome = p.get("productName") or ""
        n = cafe.norm(nome)
        if "cafe" not in n or _FORA.search(n) or not (peso := _peso_g(n)):
            continue
        for item in p.get("items") or []:
            ofs = [s.get("commertialOffer") or {} for s in item.get("sellers") or []]
            precos = [o["Price"] for o in ofs if o.get("Price") and (o.get("AvailableQuantity") or 0) > 0]
            if precos:
                link = p.get("link") or (f"/{p.get('linkText')}/p" if p.get("linkText") else "")
                out.append(Oferta(NOMES_LOJAS.get(loja, loja), f"https://{loja}{link}" if link.startswith("/") else link,
                                  nome, float(min(precos)), peso))
                break
    return out


def classificar(of: Oferta, marca: str, linhas: list[dict[str, Any]]) -> dict[str, Any] | None:
    """A linha da marca que o produto representa (pelo nome), ou None se não for desta marca/linha."""
    n = cafe.norm(of.produto).replace("extra forte", "extraforte").replace("extra-forte", "extraforte")
    aliases = marcas.MARCAS[marca][0]
    if not any(re.search(rf"\b{re.escape(a)}\b", n) for a in aliases):
        return None
    grao = bool(re.search(r"\bgraos?\b|\bem grao", n))
    if len(linhas) == 1 and not _palavras_linha(linhas[0]["linha"] or ""):
        return linhas[0]  # marca registrada como uma linha só (Orfeu, Baggio, Kimimo): qualquer café dela
    melhor, pontos = None, 0
    for ln in linhas:
        if _eh_grao(ln["linha"] or "") != grao:
            continue
        ps = [p for p in _palavras_linha(ln["linha"] or "") if re.search(rf"\b{re.escape(p)}\b", n)]
        pt = sum(len(p) for p in ps)
        if pt > pontos:
            melhor, pontos = ln, pt
    return melhor


def _buscar(cliente: httpx.Client, loja: str, termo: str) -> tuple[str, list[Oferta] | None]:
    try:
        r = cliente.get(f"https://{loja}{BUSCA}", params={"query": termo, "count": 50})
        r.raise_for_status()
        return loja, ofertas_da_resposta(loja, r.json())
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("Varejo: {} '{}' falhou: {}", loja, termo, e)
        return loja, None


def atualizar(base_path: Path, hoje: str, cliente: httpx.Client | None = None) -> int:
    """Atualiza preco_kg_min/max, precos_fontes, ofertas e preco_em de cada linha. Devolve o nº de linhas com
    preço novo. Levanta RuntimeError (sem gravar) se poucas lojas responderam."""
    base = json.loads(base_path.read_text(encoding="utf-8"))
    por_marca: dict[str, list[dict[str, Any]]] = {}
    for ln in base["linhas"]:
        por_marca.setdefault(ln["marca"], []).append(ln)
    cliente = cliente or httpx.Client(timeout=25, headers={"User-Agent": "Mozilla/5.0 (monitor-licitacoes; github.com/xMiraTorta)"},
                                      follow_redirects=True)
    tarefas = [(loja, m, f"cafe {marcas.MARCAS[m][0][0]}") for m in por_marca for loja in LOJAS]
    with ThreadPoolExecutor(max_workers=3) as ex:
        res = list(ex.map(lambda t: (t[1], *_buscar(cliente, t[0], t[2])), tarefas))
    lojas_ok = {loja for _, loja, ofs in res if ofs is not None}
    if len(lojas_ok) < MIN_LOJAS_OK:
        raise RuntimeError(f"só {len(lojas_ok)} lojas responderam ({sorted(lojas_ok)}); preços anteriores mantidos")
    achadas: dict[int, list[Oferta]] = {}
    for marca, _, ofs in res:
        for of in ofs or []:
            if (ln := classificar(of, marca, por_marca[marca])) is not None:
                achadas.setdefault(id(ln), []).append(of)
    novas = 0
    for ln in base["linhas"]:
        ofs = achadas.get(id(ln), [])
        if not ofs:
            continue
        ofs = list({(o.loja, o.produto): o for o in ofs}.values())  # a mesma oferta pode vir em 2 buscas
        ofs.sort(key=lambda o: o.rkg)
        por_loja = list({o.loja: o for o in reversed(ofs)}.values())[::-1]  # a mais barata de cada loja
        amostra = [por_loja[0], por_loja[-1], por_loja[len(por_loja) // 2]] + por_loja
        fontes = list({o.loja: o for o in amostra}.values())[:4]
        ln.update(preco_kg_min=ofs[0].rkg, preco_kg_max=ofs[-1].rkg, preco_em=hoje, ofertas=len(ofs),
                  lojas=len({o.loja for o in ofs}),
                  precos_fontes=[{"loja": o.loja, "url": o.url, "data": hoje, "preco": o.preco, "peso_g": o.peso_g,
                                  "produto": o.produto} for o in fontes])
        novas += 1
    base["precos_em"] = hoje
    gravar_atomico(base_path, json.dumps(base, ensure_ascii=False, indent=1) + "\n")  # nunca um JSON pela metade
    marcas.base.cache_clear()
    logger.info("Varejo: {} de {} linhas com preço desta semana ({} lojas responderam)", novas, len(base["linhas"]),
                len(lojas_ok))
    return novas
