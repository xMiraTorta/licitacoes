"""Coletor de ponta a ponta com um PNCP simulado (sem internet)."""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from coletor import coleta, montar, publicar, telegram
from coletor.pncp import PNCP, ColetaErro
from tests.conftest import ROOT, embedded_data

AGORA = datetime(2026, 10, 19, 9, 0, tzinfo=coleta.TZ)


def compra_api(cnpj: str, seq: int, objeto: str, fim: str = "2026-10-30T10:00:00", ibge: str = "3156908",
               mun: str = "Sacramento", uf: str = "MG", link: str = "https://bllcompras.com/Process/1") -> dict[str, Any]:
    return {"numeroControlePNCP": f"{cnpj}-1-{seq:06d}/2026", "anoCompra": 2026, "sequencialCompra": seq,
            "numeroCompra": f"{seq:03d}", "objetoCompra": objeto, "informacaoComplementar": None, "srp": True,
            "orgaoEntidade": {"cnpj": cnpj, "razaoSocial": "MUNICIPIO DE TESTE", "esferaId": "M"},
            "unidadeOrgao": {"ufSigla": uf, "municipioNome": mun, "nomeUnidade": "PREFEITURA", "codigoIbge": ibge,
                             "codigoUnidade": "1"},
            "modalidadeNome": "Pregão - Eletrônico", "dataPublicacaoPncp": "2026-10-18T08:00:00",
            "dataAberturaProposta": "2026-10-19T08:00:00", "dataEncerramentoProposta": fim,
            "linkSistemaOrigem": link, "usuarioNome": "BLL Compras", "dataAtualizacaoGlobal": "2026-10-18T08:00:00"}


def item_api(n: int, desc: str, qtd: float, vu: float | None, un: str = "Pacote", sig: bool = False,
             beneficio: int = 1) -> dict[str, Any]:
    return {"numeroItem": n, "descricao": desc, "quantidade": qtd, "unidadeMedida": un, "orcamentoSigiloso": sig,
            "valorUnitarioEstimado": vu if vu is not None else 0, "valorTotal": round(qtd * vu, 4) if vu else 0,
            "tipoBeneficio": beneficio, "situacaoCompraItemNome": "Em andamento"}


CAFE = compra_api("11111111000111", 1, "Aquisição de gêneros alimentícios")
OUTRA = compra_api("22222222000122", 2, "Aquisição de gêneros alimentícios para merenda")
PNEU = compra_api("33333333000133", 3, "Aquisição de pneus")
ENCERRADA = compra_api("44444444000144", 4, "Aquisição de café", fim="2026-10-18T10:00:00")
ITENS = {
    "11111111000111/compras/2026/1": [item_api(1, "Arroz tipo 1, 5 kg", 100, 25.0),
                                      item_api(2, "Café torrado e moído, 500g, vácuo, selo ABIC", 1000, 30.0),
                                      item_api(3, "Café solúvel, frasco 200g", 10, 30.0, sig=True)],
    "22222222000122/compras/2026/2": [item_api(1, "Feijão carioca 1 kg", 100, 8.0)],
    "44444444000144/compras/2026/4": [item_api(1, "Café em pó 500g", 10, 30.0)],
}


def fake_pncp(lista: list[dict[str, Any]], itens: dict[str, Any], falhar: set[str] = frozenset()) -> PNCP:
    def handler(req: httpx.Request) -> httpx.Response:
        path = req.url.path
        if path.endswith("/contratacoes/proposta"):
            m = req.url.params["codigoModalidadeContratacao"]
            data = lista if m == "6" else []
            return httpx.Response(200, json={"data": data, "totalRegistros": len(data), "totalPaginas": 1 if data else 0})
        if path.endswith("/itens"):
            chave = path.split("/orgaos/")[1].removesuffix("/itens")
            if chave in falhar:
                return httpx.Response(503, text="indisponível")
            return httpx.Response(200, json=itens.get(chave, []))
        if path.startswith("/api/search"):
            return httpx.Response(200, json={"items": [], "total": 0})
        return httpx.Response(404)
    return PNCP(httpx.Client(transport=httpx.MockTransport(handler)), tentativas=2, espera_base=0, espera_429=0,
                intervalo_min=0)


@pytest.fixture
def destino(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    shutil.copy(ROOT / "index.html", tmp_path / "index.html")
    monkeypatch.setattr(coleta, "CACHE", tmp_path / "cache" / "sem_cafe.json")
    return tmp_path


def rodar(destino: Path, lista: list[dict[str, Any]], itens: dict[str, Any] = ITENS, agora: datetime = AGORA,
          **kw: Any) -> coleta.Resultado:
    return coleta.coletar(destino, pncp=fake_pncp(lista, itens, kw.pop("falhar", set())), agora=agora, **kw)


def test_primeira_coleta_monta_registro_completo(destino: Path) -> None:
    r = rodar(destino, [CAFE, OUTRA, PNEU, ENCERRADA])
    data = json.loads((destino / "data.json").read_text(encoding="utf-8"))
    assert embedded_data((destino / "index.html").read_text(encoding="utf-8")) == data
    assert [c["chave"] for c in data["compras"]] == [CAFE["numeroControlePNCP"]]  # só a de café aberta
    c = data["compras"][0]
    assert [i["n"] for i in c["itens"]] == [2, 3]  # arroz fica de fora
    tm, sol = c["itens"]
    assert (tm["kgu"], tm["kgt"], tm["rkg"], tm["tags"]) == (0.5, 500.0, 60.0, ["ABIC/pureza"])
    assert sol["sig"] is True and sol["vu"] is None and sol["vt"] is None  # sigiloso não vira zero
    assert c["vcafe"] == 30000.0 and c["kg"] == 502.0 and c["rkg"] == 60.0 and c["sig"] == "Sim"
    assert c["plat"] == "BLL Compras" and c["dist"] == 0 and c["me"] == "Exclusivo ME/EPP"
    assert c["first_seen"] == "2026-10-19" and c["nova"] is False  # primeira carga não marca "nova"
    assert r.novas == [CAFE["numeroControlePNCP"]]
    assert "Atualizado em <b>19/10/2026 09:00</b>" in (destino / "index.html").read_text(encoding="utf-8")


def test_segunda_coleta_marca_novas_e_preserva_edital(destino: Path) -> None:
    rodar(destino, [CAFE])
    data = json.loads((destino / "data.json").read_text(encoding="utf-8"))
    data["compras"][0].update(edital_lido=True, ed_tags=["Amostra"], ed_pz="5 dias úteis")
    (destino / "data.json").write_text(json.dumps(data), encoding="utf-8")
    nova = compra_api("55555555000155", 5, "Aquisição de café")
    itens = {**ITENS, "55555555000155/compras/2026/5": [item_api(1, "Café torrado e moído 250g", 100, 18.0)]}
    r = rodar(destino, [CAFE, nova], itens, agora=datetime(2026, 10, 20, 9, 0, tzinfo=coleta.TZ))
    data = json.loads((destino / "data.json").read_text(encoding="utf-8"))
    by = {c["chave"]: c for c in data["compras"]}
    velha, nv = by[CAFE["numeroControlePNCP"]], by[nova["numeroControlePNCP"]]
    assert velha["nova"] is False and velha["first_seen"] == "2026-10-19"
    assert velha["edital_lido"] is True and velha["ed_tags"] == ["Amostra"] and velha["ed_pz"] == "5 dias úteis"
    assert nv["nova"] is True and nv["first_seen"] == "2026-10-20"
    assert data["novas_desde"] == "2026-10-19" and r.novas == [nova["numeroControlePNCP"]]


def test_falha_na_listagem_nao_altera_arquivos(destino: Path) -> None:
    rodar(destino, [CAFE])
    antes = (destino / "data.json").read_bytes(), (destino / "index.html").read_bytes()

    def quebrado(req: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="fora do ar")
    p = PNCP(httpx.Client(transport=httpx.MockTransport(quebrado)), tentativas=2, espera_base=0, intervalo_min=0)
    with pytest.raises(ColetaErro):
        coleta.coletar(destino, pncp=p, agora=AGORA)
    assert ((destino / "data.json").read_bytes(), (destino / "index.html").read_bytes()) == antes


def test_queda_brusca_bloqueia_publicacao(destino: Path) -> None:
    lista = [compra_api(f"{i:014d}", i, "café") for i in range(1, 11)]
    itens = {f"{i:014d}/compras/2026/{i}": [item_api(1, "Café em pó 500g", 10, 30.0)] for i in range(1, 11)}
    rodar(destino, lista, itens)
    antes = (destino / "data.json").read_bytes()
    with pytest.raises(publicar.PublicacaoBloqueada, match="queda"):
        rodar(destino, lista[:3], itens)
    assert (destino / "data.json").read_bytes() == antes
    rodar(destino, lista[:3], itens, forcar=True)  # com --forcar publica
    assert len(json.loads((destino / "data.json").read_text())["compras"]) == 3


def test_itens_falharam_mantem_registro_anterior(destino: Path) -> None:
    lista = [compra_api(f"{i:014d}", i, "café") for i in range(1, 41)]
    itens = {f"{i:014d}/compras/2026/{i}": [item_api(1, "Café em pó 500g", 10, 30.0)] for i in range(1, 41)}
    rodar(destino, lista, itens)
    r = rodar(destino, lista, itens, falhar={"00000000000001/compras/2026/1"})
    data = json.loads((destino / "data.json").read_text())
    assert len(data["compras"]) == 40 and len(r.falhas) == 1  # a que falhou veio da coleta anterior


def test_muitas_falhas_bloqueiam(destino: Path) -> None:
    lista = [compra_api(f"{i:014d}", i, "café") for i in range(1, 11)]
    itens = {f"{i:014d}/compras/2026/{i}": [item_api(1, "Café em pó 500g", 10, 30.0)] for i in range(1, 11)}
    with pytest.raises(publicar.PublicacaoBloqueada, match="falharam"):
        rodar(destino, lista, itens, falhar={f"{i:014d}/compras/2026/{i}" for i in (1, 2)})


def test_cache_evita_baixar_de_novo_sem_cafe(destino: Path) -> None:
    rodar(destino, [CAFE, OUTRA])
    cache = json.loads(coleta.CACHE.read_text())
    assert OUTRA["numeroControlePNCP"] in cache and CAFE["numeroControlePNCP"] not in cache
    r = rodar(destino, [CAFE, OUTRA])
    assert r.candidatas == 1  # só a de café é baixada de novo


def test_duplicatas_mesmo_municipio_valor_e_data() -> None:
    a = montar.montar_compra(compra_api("11111111000111", 1, "café"), [item_api(1, "Café em pó 500g", 10, 30.0)])
    b = montar.montar_compra(compra_api("11111111000111", 2, "café", link=""), [item_api(1, "Café em pó 500g", 10, 30.0)])
    assert a and b
    montar.marcar_duplicatas([a, b])
    assert a["dup_of"] is None and b["dup_of"] == a["chave"]  # a tem link de plataforma: mais completa
    assert a["dup_group"] == [b["chave"]] and b["dup"].startswith("Possível duplicata de:")


@pytest.mark.parametrize("link,pub,esperado", [
    ("https://cnetmobile.estaleiro.serpro.gov.br/comprasnet-web/x", "Compras.gov.br", ("Compras.gov.br", "link de origem (PNCP)", "Compras.gov.br")),
    ("https://www.licitaoeiras.com.br/p", "X", ("Portal próprio: www.licitaoeiras.com.br", "link de origem (PNCP)", "Portal próprio do órgão")),
    ("", "Novo BBMNET Licitações", ("BBMNET", "publicado pela própria plataforma", "BBMNET")),
    (None, "IPM Sistemas", ("Ver edital (publicado via IPM Sistemas)", "não derivável", "Não identificada (ver edital)")),
])
def test_plataforma(link: str | None, pub: str, esperado: tuple[str, str, str]) -> None:
    assert montar.plataforma(link, pub) == esperado


def test_distancia_confere_com_painel_original() -> None:
    assert montar.distancia_km("3117108") == 189  # Conceição da Aparecida-MG
    assert montar.distancia_km("9999999") is None


def test_mensagens_telegram() -> None:
    c = montar.montar_compra(compra_api("11111111000111", 1, "café"), [item_api(1, "Café em pó 500g", 1000, 30.0)])
    assert c
    msgs = telegram.mensagens([c] * 60, 300, "19/10")
    assert len(msgs) > 1 and all(len(m) <= 4096 for m in msgs)
    assert msgs[0].startswith("☕ <b>60 licitações novas") and "Sacramento-MG" in msgs[0]
    assert "nenhuma licitação nova" in telegram.mensagens([], 300, "19/10")[0]


def test_enviar_telegram_sem_vazar_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:SEGREDO")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    enviados: list[dict[str, Any]] = []

    def handler(req: httpx.Request) -> httpx.Response:
        enviados.append(json.loads(req.content))
        return httpx.Response(200, json={"ok": True})
    telegram.enviar(["oi"], httpx.Client(transport=httpx.MockTransport(handler)))
    assert enviados == [{"chat_id": "42", "text": "oi", "parse_mode": "HTML", "disable_web_page_preview": True}]

    def recusa(req: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"ok": False, "description": "chat not found"})
    with pytest.raises(telegram.TelegramErro) as e:
        telegram.enviar(["oi"], httpx.Client(transport=httpx.MockTransport(recusa)))
    assert "SEGREDO" not in str(e.value)


def test_sem_segredos_telegram(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises(telegram.TelegramErro, match="não configurados"):
        telegram.enviar(["oi"])
