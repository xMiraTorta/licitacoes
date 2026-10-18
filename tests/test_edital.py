"""Leitor de edital/TR: extração de texto, trecho de cada item, marcas de referência e gravação na compra."""
from __future__ import annotations

import io
import zipfile
from typing import Any

import httpx

from coletor import edital, montar
from coletor.pncp import PNCP

CHAVE = "18940098000122-1-000149/2026"
TR = """TERMO DE REFERÊNCIA
O prazo de entrega será de 05 (cinco) dias corridos após o pedido.
| 1709 | kg | 1 | Arroz agulhinha tipo 1, pacote 5 kg |
| 1710 | un | 2 | Café torrado e moído, de primeira qualidade, com as características mínimas: composto por no mínimo 80%
de grãos de Coffea arabica; torra média; bebida classificada, no mínimo, como superior, conforme os critérios do
Programa de Qualidade do Café (PQC) da ABIC; embalagem almofada 500 g. |
| 10774 | pt | 3 | Café em grãos para máquinas de café expresso, torrado em grãos, 100% arábica, produto classificado
como café gourmet, pontuação mínima de 80 pontos na metodologia SCA, embalagem 1 kg com válvula. |
Marcas de referência: Três Corações, Melitta, Caboclo, Pilão ou outras de qualidade equivalente ou superior.
"""
def _item(n: int, desc: str) -> dict[str, Any]:
    i = montar.montar_item({"numeroItem": n, "descricao": desc, "quantidade": 10, "unidadeMedida": "Pacote",
                            "orcamentoSigiloso": False, "valorUnitarioEstimado": 20, "valorTotal": 200,
                            "tipoBeneficio": 1, "situacaoCompraItemNome": "Em andamento"})
    assert i is not None
    return i


ITENS = [_item(2, "CAFÉ TORRADO E MOÍDO."), _item(3, "CAFÉ EM GRÃOS PARA MÁQUINAS .")]


def _docx(texto: str) -> bytes:
    corpo = "".join(f"<w:p><w:r><w:t>{linha}</w:t></w:r></w:p>" for linha in texto.splitlines())
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("word/document.xml", f"<w:document><w:body>{corpo}</w:body></w:document>")
    return b.getvalue()


def _pncp(docs: list[dict[str, Any]] | None, arquivos: dict[str, bytes]) -> PNCP:
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/arquivos"):
            return httpx.Response(200, json=docs) if docs is not None else httpx.Response(503, text="fora")
        if req.url.path in arquivos:
            return httpx.Response(200, content=arquivos[req.url.path])
        return httpx.Response(404)
    return PNCP(httpx.Client(transport=httpx.MockTransport(handler)), tentativas=1, espera_base=0, espera_429=0,
                intervalo_min=0)


def _compra() -> dict[str, Any]:
    c = {"chave": CHAVE, "itens": [dict(i) for i in ITENS], "edital_lido": False, "ed_pz": ""}
    c.update(montar.agregar(c["itens"]))
    return c


def test_cada_item_recebe_a_propria_especificacao() -> None:
    r = edital.analisar(TR, ITENS)
    assert r.status == edital.STATUS_LIDO
    assert "80%" in r.itens[2] and "gourmet" not in r.itens[2]
    assert "gourmet" in r.itens[3] and "como superior" not in r.itens[3]
    assert r.marcas == ["3 Corações", "Melitta", "Caboclo", "Pilão"]
    assert r.prazo_entrega == "5 dias corridos"
    assert len(r.trechos) == len(set(r.trechos))


def test_ler_e_aplicar_do_pncp() -> None:
    docs = [{"url": "https://pncp.gov.br/docs/1", "titulo": "Edital.pdf", "tipoDocumentoId": 2, "sequencialDocumento": 1},
            {"url": "https://pncp.gov.br/docs/2", "titulo": "TR", "tipoDocumentoId": 4, "sequencialDocumento": 2}]
    p = _pncp(docs, {"/docs/1": b"%PDF-quebrado", "/docs/2": _docx(TR)})
    c = _compra()
    edital.aplicar(c, edital.ler(p, CHAVE, c["itens"]), "2026-10-18")
    tm, grao = c["itens"]
    assert c["edital_status"] == edital.STATUS_LIDO and c["edital_lido"] is True and c["edital_lido_em"] == "2026-10-18"
    assert (tm["cat"], tm["nivel"]) == ("Superior*", "Superior")  # * = veio do edital, não da descrição do item
    assert (grao["cat"], grao["nivel"], grao["qg"]) == ("Gourmet*/especial*", "Gourmet/especial", 8.0)
    assert c["niveis"] == ["Superior", "Gourmet/especial"] and c["cat_do_edital"] is True
    assert c["ed_pz"] == "5 dias corridos" and "Pilão" in c["marcas"]
    montar.reclassificar_nivel(c)  # reclassificar (sem PNCP) mantém o que veio do edital
    assert [i["nivel"] for i in c["itens"]] == ["Superior", "Gourmet/especial"]


def test_falha_nao_apaga_leitura_anterior() -> None:
    c = _compra()
    c.update(edital_lido=True, trecho_edital="café superior", ed_pz="3 dias")
    edital.aplicar(c, edital.ler(_pncp(None, {}), CHAVE, c["itens"]), "2026-10-18")
    assert c["edital_status"] == edital.STATUS_FALHA
    assert (c["edital_lido"], c["trecho_edital"], c["ed_pz"]) == (True, "café superior", "3 dias")


def test_sem_documentos() -> None:
    c = _compra()
    edital.aplicar(c, edital.ler(_pncp([], {}), CHAVE, c["itens"]), "2026-10-18")
    assert c["edital_status"] == edital.STATUS_SEM_DOCS and c["edital_lido"] is False
    assert edital.precisa_ler(c, "v1")  # sem documentos: tenta de novo na próxima coleta


def test_precisa_ler() -> None:
    assert edital.precisa_ler({}, "v1")
    lida = {"edital_status": edital.STATUS_LIDO, "edital_ver": "v1"}
    assert not edital.precisa_ler(lida, "v1") and edital.precisa_ler(lida, "v2")  # errata/anexo novo: lê de novo


def test_cafe_da_manha_nao_e_especificacao() -> None:
    assert edital.analisar("Serviço de café da manhã e coffee break para eventos, com garrafas térmicas.", ITENS).status \
        == edital.STATUS_SEM_CAFE


def test_doc_antigo_e_zip() -> None:
    doc = b"\xd0\xcf\x11\xe0" + b"\x00" * 50 + "Café torrado e moído tipo superior, embalagem 500 g. ".encode("utf-16-le") * 30
    assert "torrado e moído" in edital.texto_de("tr.doc", doc)
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("anexos/TR.docx", _docx("Café torrado superior"))
    assert "Café torrado superior" in edital.texto_de("anexos.zip", b.getvalue())


def test_linha_do_cafe_nao_vaza_para_o_produto_seguinte() -> None:
    t = ("16 café 500gr torrado e moído embalado a vácuo, embalagem aluminizada. pct 276 R$ 28,63 R$ 7.901,88 "
         "17 molho de tomate tradicional, 340 g, embalagem sachê. pct 72 R$ 3,59 R$ 258,48")
    r = edital.analisar(t, [_item(16, "Café 500gr torrado e moído")])
    assert "molho" not in r.itens[16] and edital.cafe.categoria(r.itens[16]) == ""


def test_itens_parecidos_recebem_o_trecho_proprio() -> None:
    t = ("01 café torrado e moído comum, embalado a vácuo, em pacote de 500 g, 100% café. R$ 31,21 R$ 118.910,10 "
         "02 café torrado e moído extra forte, embalado a vácuo, em pacote de 500 g, 100% café. R$ 37,73 R$ 754,60 "
         "03 café torrado e moído premium, embalado a vácuo, em pacote de 250 g, 100% café. R$ 17,64 R$ 882,00")
    itens = [_item(1, "Café torrado e moído comum, embalado a vácuo, 500 g"), _item(2, "Café torrado e moído extra forte, 500 g"),
             _item(3, "Café torrado e moído premium, embalado a vácuo, pacote de 250 g")]
    r = edital.analisar(t, itens)
    assert "comum" in r.itens[1] and "extra forte" in r.itens[2] and "premium" in r.itens[3]


def test_pesquisa_de_precos_e_grao_sem_trecho_proprio() -> None:
    t = ("Café torrado e moído categoria tradicional, torra média, pacote 500 g, selo ABIC. "
         "Café apresentação: torrado moído, tipo único, pacote 500 grama, consolidação dos preços cotados, menor preço, mediana.")
    r = edital.analisar(t, [_item(1, "Café apresentação: torrado moído, tipo: único"), _item(2, "Café em grãos para máquina, 1 kg")])
    assert "categoria tradicional" in r.itens[1] and 2 not in r.itens  # sem trecho de café em grão: nada


def test_categoria_negada_ou_modo_de_preparo() -> None:
    cat = lambda t: edital.cafe.categoria(edital.cafe.norm(t))  # noqa: E731
    assert cat("não será aceito o sabor extraforte") == ""
    assert cat("moagem adequada ao preparo tradicional por filtragem") == ""
    assert cat("café tradicional, torra média") == "Tradicional"
