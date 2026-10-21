"""Leitor de edital/TR: extração de texto, trecho de cada item, marcas de referência e gravação na compra."""
from __future__ import annotations

import io
import zipfile
from typing import Any

import httpx
import pytest

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


def _zip_ruim(variante: str) -> bytes:
    """ZIPs corrompidos de formas que o zipfile só percebe depois de abrir (casos reais de anexo danificado no PNCP)."""
    import struct
    base = _docx("Café torrado e moído superior")
    if variante == "versao":  # versão de extração impossível no diretório central: NotImplementedError ao abrir
        d = bytearray(base)
        d[d.rfind(b"PK\x01\x02") + 6] = 99
        return bytes(d)
    if variante == "nome":  # nome com a marca UTF-8 ligada mas bytes cp1252 ("Referência" gravado como \xea): UnicodeDecodeError
        b = io.BytesIO()
        with zipfile.ZipFile(b, "w") as z:
            z.writestr("Referência.docx", base)
        return b.getvalue().replace(b"\xc3\xaa", b"\xea_")
    if variante == "offset":  # diretório central apontando para fora do arquivo: ValueError (seek negativo) ao ler
        d = bytearray(base)
        eocd = d.rfind(b"PK\x05\x06")
        struct.pack_into("<L", d, eocd + 16, struct.unpack_from("<L", d, eocd + 16)[0] + 1000)
        return bytes(d)
    if variante == "lzma":  # entrada LZMA com os dados corrompidos: lzma.LZMAError ao descompactar
        b = io.BytesIO()
        with zipfile.ZipFile(b, "w", compression=zipfile.ZIP_LZMA) as z:
            z.writestr("word/document.xml", "<w:p><w:t>Café torrado</w:t></w:p>" * 50)
        d = bytearray(b.getvalue())
        ini = d.find(b"word/document.xml") + len("word/document.xml") + 2
        for k in range(ini + 2, ini + 40):
            d[k] ^= 0xFF
        return bytes(d)
    raise ValueError(variante)


def _pncp_tr_instavel(falhas_tr: int, tentativas: int) -> tuple[PNCP, dict[str, int]]:
    """Edital sem a especificação do café baixa sempre; o TR responde 429 nas primeiras `falhas_tr` chamadas."""
    docs = [{"url": "https://pncp.gov.br/docs/1", "titulo": "Edital.docx", "tipoDocumentoId": 2, "sequencialDocumento": 1},
            {"url": "https://pncp.gov.br/docs/2", "titulo": "TR.docx", "tipoDocumentoId": 4, "sequencialDocumento": 2}]
    chamadas: dict[str, int] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        chamadas[req.url.path] = chamadas.get(req.url.path, 0) + 1
        if req.url.path.endswith("/arquivos"):
            return httpx.Response(200, json=docs)
        if req.url.path == "/docs/1":
            return httpx.Response(200, content=_docx("EDITAL. Objeto: gêneros alimentícios, conforme TR anexo."))
        if chamadas["/docs/2"] <= falhas_tr:
            return httpx.Response(429, text="Limite de requisições excedido")
        return httpx.Response(200, content=_docx(TR))
    return PNCP(httpx.Client(transport=httpx.MockTransport(handler)), tentativas=tentativas, espera_base=0, espera_429=0,
                intervalo_min=0), chamadas


@pytest.mark.parametrize("variante", ["versao", "nome", "offset", "lzma"])
def test_zip_corrompido_nao_derruba_a_leitura(variante: str) -> None:
    assert edital.texto_de("Anexos.zip", _zip_ruim(variante)) == ""


def test_anexo_corrompido_nao_bloqueia_a_coleta() -> None:
    """Um ZIP danificado vira "sem texto legível" (como PDF escaneado); nenhuma exceção sobe até a coleta do dia."""
    docs = [{"url": "https://pncp.gov.br/docs/1", "titulo": "Anexos.zip", "tipoDocumentoId": 5, "sequencialDocumento": 1}]
    c = _compra()
    assert edital.ler_varias(_pncp(docs, {"/docs/1": _zip_ruim("offset")}), [c], {CHAVE: "v1"}, "2026-10-21") == 1
    assert c["edital_status"] == edital.STATUS_SEM_TEXTO and c["edital_ver"] == "v1"


def test_excecao_inesperada_na_leitura_vira_falha_e_tenta_de_novo(monkeypatch: pytest.MonkeyPatch) -> None:
    def quebra(*a: Any, **k: Any) -> edital.Leitura:
        raise RuntimeError("formato que ninguém previu")
    monkeypatch.setattr(edital, "ler", quebra)
    c = _compra()
    assert edital.ler_varias(_pncp([], {}), [c], {CHAVE: "v1"}, "2026-10-21") == 1
    assert c["edital_status"] == edital.STATUS_FALHA and "edital_ver" not in c and edital.precisa_ler(c, "v1")


def test_releitura_sem_sucesso_nao_muda_o_status_da_leitura_boa() -> None:
    """A compra mudou no PNCP e a releitura não achou o café: a leitura boa continua valendo (status, trecho, nível),
    a tentativa fica registrada; uma releitura boa depois substitui tudo e apaga a tentativa."""
    c = _compra()
    edital.aplicar(c, edital.analisar(TR, c["itens"]), "2026-10-18")
    assert c["edital_status"] == edital.STATUS_LIDO and c["itens"][0]["nivel"] == "Superior"
    edital.aplicar(c, edital.Leitura(edital.STATUS_SEM_CAFE, docs=["1:Edital.docx"]), "2026-10-21")
    assert c["edital_status"] == edital.STATUS_LIDO and c["edital_tentativa"] == f"2026-10-21: {edital.STATUS_SEM_CAFE}"
    assert c["itens"][0]["nivel"] == "Superior" and c["itens"][0]["ed_trecho"]
    edital.aplicar(c, edital.analisar(TR, c["itens"]), "2026-10-22")
    assert c["edital_status"] == edital.STATUS_LIDO and "edital_tentativa" not in c


def test_revisao_manual_sobrevive_a_pdf_escaneado_novo() -> None:
    docs = [{"url": "https://pncp.gov.br/docs/1", "titulo": "Edital.pdf", "tipoDocumentoId": 2, "sequencialDocumento": 1}]
    c = _compra()
    c.update(edital_status="lido (revisão manual: PDF escaneado)", edital_lido=True, edital_ver="v1")
    c["itens"][0]["ed_trecho"] = "transcrição à mão: café superior"
    edital.ler_varias(_pncp(docs, {"/docs/1": b"%PDF-1.4\n"}), [c], {CHAVE: "v2"}, "2026-10-21")  # PDF sem texto
    assert c["edital_status"] == "lido (revisão manual: PDF escaneado)" and c["itens"][0]["ed_trecho"].startswith("transcrição")
    assert c["edital_ver"] == "v2" and c["edital_tentativa"].startswith("2026-10-21: ") and not edital.precisa_ler(c, "v2")


def test_status_vazio_herdado_do_painel_antigo_e_atualizado() -> None:
    c = _compra()
    c.update(edital_lido=True, edital_status="")
    edital.ler_varias(_pncp([{"url": "https://pncp.gov.br/docs/1", "titulo": "Edital.docx", "tipoDocumentoId": 2, "sequencialDocumento": 1}],
                            {"/docs/1": _docx("EDITAL. Objeto: gêneros alimentícios.")}), [c], {CHAVE: "v1"}, "2026-10-21")
    assert c["edital_status"] == edital.STATUS_SEM_CAFE and not edital.precisa_ler(c, "v1")  # não fica relendo todo dia


def test_documento_com_429_tenta_de_novo() -> None:
    p, chamadas = _pncp_tr_instavel(falhas_tr=1, tentativas=3)
    c = _compra()
    edital.ler_varias(p, [c], {CHAVE: "v1"}, "2026-10-21")
    assert chamadas["/docs/2"] == 2 and c["edital_status"] == edital.STATUS_LIDO and c["edital_ver"] == "v1"
    assert [i["nivel"] for i in c["itens"]] == ["Superior", "Gourmet/especial"]
    assert p.stats.novas_tentativas == 1 and p.intervalo_min > 0  # o 429 do documento também desacelera o coletor


def test_leitura_parcial_nao_vale_como_versao_lida() -> None:
    """TR fora do ar mesmo após as tentativas: fica o que o Edital diz, mas a compra é relida na próxima coleta."""
    p, chamadas = _pncp_tr_instavel(falhas_tr=99, tentativas=2)
    c = _compra()
    edital.ler_varias(p, [c], {CHAVE: "v1"}, "2026-10-21")
    assert chamadas["/docs/2"] == 2 and c["edital_status"] == edital.STATUS_SEM_CAFE and c["edital_docs"] == ["1:Edital.docx"]
    assert "edital_ver" not in c and edital.precisa_ler(c, "v1")
    p, chamadas = _pncp_tr_instavel(falhas_tr=0, tentativas=1)  # dia seguinte, PNCP normal
    edital.ler_varias(p, [c], {CHAVE: "v1"}, "2026-10-22")
    assert c["edital_status"] == edital.STATUS_LIDO and c["edital_ver"] == "v1" and not edital.precisa_ler(c, "v1")


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


FIXTURES = __import__("pathlib").Path(__file__).parent / "fixtures" / "editais"


def test_rar_de_verdade() -> None:
    """RAR5 (formato dos editais .rar vistos no PNCP), lido pela libarchive da máquina. Falha se ela faltar."""
    import libarchive  # noqa: F401  (sem a biblioteca do sistema, este teste quebra de propósito)
    t = edital.texto_de("edital.rar", (FIXTURES / "rar5-solid.rar").read_bytes())
    assert "000" in t and "001" in t


def test_pdf_protegido_aes() -> None:
    """PDF com proteção AES e senha de abertura vazia: precisa do pacote cryptography."""
    t = edital.texto_de("TR.pdf", (FIXTURES / "protegido-aes256.pdf").read_bytes())
    assert "categoria superior" in t
