"""Coletor de ponta a ponta com um PNCP simulado (sem internet)."""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from coletor import coleta, custos, mercado, montar, publicar, telegram
from coletor.pncp import PNCP, ColetaErro
from tests.conftest import FIXTURES, ROOT  # noqa: F401 (raiz do repositório)


def test_embutir_grava_data_json_com_precos_atuais(destino: Path, tmp_path: Path) -> None:
    """O pages.yml roda `embutir` ao publicar: o data.json da coleta ganha os preços de mercado, as marcas e os
    custos atuais e a hora de publicação, sem a coleta e os preços escreverem o mesmo arquivo."""
    from coletor.__main__ import main
    rodar(destino, [CAFE])
    saida = tmp_path / "dist"
    assert main(["embutir", "--destino", str(destino), "--saida", str(saida)]) == 0
    out = json.loads((saida / "data.json").read_text(encoding="utf-8"))
    assert [c["chave"] for c in out["compras"]] == [CAFE["numeroControlePNCP"]]
    assert out["mercado"] == mercado.carregar() and out["custos"] == custos.premissas() and out["publicado_em"].endswith("-03:00")
    assert main(["embutir", "--destino", str(tmp_path / "vazio")]) == 2  # sem data.json: erro, nada gravado


def test_gravar_recusa_infinito_e_nan(tmp_path: Path) -> None:
    """Infinity/NaN não existem em JSON (o navegador não leria o arquivo): a gravação falha antes de tocar o data.json."""
    import math
    from pydantic import ValidationError
    data = json.loads((FIXTURES / "data_min.json").read_text(encoding="utf-8"))
    data["compras"][0]["vcafe"] = math.inf
    with pytest.raises(ValidationError):
        publicar.gravar(data, tmp_path, datetime.fromisoformat(data["gerado_em"]))
    data = json.loads((FIXTURES / "data_min.json").read_text(encoding="utf-8"))
    data["origem"]["lat"] = math.nan  # campo livre (dict): passa pelo modelo, cai no json.dumps
    with pytest.raises(ValueError):
        publicar.gravar(data, tmp_path, datetime.fromisoformat(data["gerado_em"]))
    assert not (tmp_path / "data.json").exists()


def test_gravar_marca_a_hora_da_publicacao(tmp_path: Path) -> None:
    """Toda gravação (coleta ou só preços, com o mesmo gerado_em) ganha publicado_em novo: é por ele que a página
    aberta percebe que há arquivo mais novo."""
    data = json.loads((FIXTURES / "data_min.json").read_text(encoding="utf-8"))
    data.pop("publicado_em", None)
    publicar.gravar(data, tmp_path, datetime.fromisoformat(data["gerado_em"]))
    out = json.loads((tmp_path / "data.json").read_text(encoding="utf-8"))
    assert out["gerado_em"] == data["gerado_em"]  # a hora da coleta não muda
    assert out["publicado_em"].endswith("-03:00") and out["publicado_em"] > out["gerado_em"]
    assert len(out["publicado_em"]) == 25  # AAAA-MM-DDTHH:MM:SS-03:00

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
                                      item_api(3, "Café torrado em grãos, pacote 1kg", 10, 30.0, sig=True),
                                      item_api(4, "Café solúvel, frasco 200g", 10, 30.0)],  # fora do escopo
    "22222222000122/compras/2026/2": [item_api(1, "Feijão carioca 1 kg", 100, 8.0)],
    "44444444000144/compras/2026/4": [item_api(1, "Café em pó 500g", 10, 30.0)],
}


def fake_pncp(lista: list[dict[str, Any]], itens: dict[str, Any], falhar: set[str] = frozenset(),
              no_pncp: dict[str, dict[str, Any]] | None = None) -> PNCP:
    """no_pncp: compras que existem no PNCP (consulta direta pela chave) mesmo fora da listagem."""
    def handler(req: httpx.Request) -> httpx.Response:
        path = req.url.path
        if "/consulta/v1/orgaos/" in path:
            cnpj, _, ano, seq = path.split("/orgaos/")[1].split("/")
            chave = f"{cnpj}-1-{int(seq):06d}/{ano}"
            if chave in falhar:
                return httpx.Response(503, text="indisponível")
            c = (no_pncp or {}).get(chave)
            return httpx.Response(200, json=c) if c else httpx.Response(404)
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
    monkeypatch.setattr(coleta, "CACHE", tmp_path / "cache" / "sem_cafe.json")
    return tmp_path


def rodar(destino: Path, lista: list[dict[str, Any]], itens: dict[str, Any] = ITENS, agora: datetime = AGORA,
          **kw: Any) -> coleta.Resultado:
    return coleta.coletar(destino, pncp=fake_pncp(lista, itens, kw.pop("falhar", set()), kw.pop("no_pncp", None)),
                          agora=agora, **kw)


def test_primeira_coleta_monta_registro_completo(destino: Path) -> None:
    r = rodar(destino, [CAFE, OUTRA, PNEU, ENCERRADA])
    data = json.loads((destino / "data.json").read_text(encoding="utf-8"))
    assert [c["chave"] for c in data["compras"]] == [CAFE["numeroControlePNCP"]]  # só a de café aberta
    c = data["compras"][0]
    assert [i["n"] for i in c["itens"]] == [2, 3]  # arroz e solúvel ficam de fora (só café torrado)
    tm, grao = c["itens"]
    assert (tm["kgu"], tm["kgt"], tm["rkg"], tm["tags"]) == (0.5, 500.0, 60.0, ["ABIC/pureza"])
    assert grao["tipo"] == "Grão" and grao["sig"] is True and grao["vu"] is None and grao["vt"] is None  # sigiloso não vira zero
    assert c["vcafe"] == 30000.0 and c["kg"] == 510.0 and c["rkg"] == 60.0 and c["sig"] == "Sim" and c["tipos"] == ["Torrado e moído", "Grão"]
    assert c["plat"] == "BLL Compras" and c["dist"] == 76 and c["dist_min"] == 72 and c["me"] == "Exclusivo ME/EPP"
    assert c["first_seen"] == "2026-10-19" and c["nova"] is False  # primeira carga não marca "nova"
    assert r.novas == [CAFE["numeroControlePNCP"]]
    assert c["lat"] == -19.8622 and c["lon"] == -47.4508  # sede de Sacramento (IBGE), para o mapa
    assert data["gerado_em"].startswith("2026-10-19T09:00")


def test_segunda_coleta_marca_novas_e_preserva_edital(destino: Path) -> None:
    rodar(destino, [CAFE])
    data = json.loads((destino / "data.json").read_text(encoding="utf-8"))
    data["compras"][0].update(edital_lido=True, ed_tags=["Amostra"], ed_pz="5 dias úteis", edital_tentativa="2026-10-19: falha ao baixar os documentos")
    (destino / "data.json").write_text(json.dumps(data), encoding="utf-8")
    nova = compra_api("55555555000155", 5, "Aquisição de café")
    itens = {**ITENS, "55555555000155/compras/2026/5": [item_api(1, "Café torrado e moído 250g", 100, 18.0)]}
    r = rodar(destino, [CAFE, nova], itens, agora=datetime(2026, 10, 20, 9, 0, tzinfo=coleta.TZ))
    data = json.loads((destino / "data.json").read_text(encoding="utf-8"))
    by = {c["chave"]: c for c in data["compras"]}
    velha, nv = by[CAFE["numeroControlePNCP"]], by[nova["numeroControlePNCP"]]
    assert velha["nova"] is False and velha["first_seen"] == "2026-10-19"
    assert velha["edital_lido"] is True and velha["ed_tags"] == ["Amostra"] and velha["ed_pz"] == "5 dias úteis"
    assert velha["edital_tentativa"] == "2026-10-19: falha ao baixar os documentos"  # herdado como os outros campos do edital
    assert nv["nova"] is True and nv["first_seen"] == "2026-10-20"
    assert data["novas_desde"] == "2026-10-19" and r.novas == [nova["numeroControlePNCP"]]


def test_itens_vazios_de_compra_conhecida_mantem_registro_e_nao_reavisa(destino: Path) -> None:
    """PNCP devolve a lista de itens vazia num dia (204 ou []): a compra conhecida fica como estava e, quando os
    itens voltam, não é avisada de novo como nova (first_seen preservado)."""
    lista = [compra_api(f"{i:014d}", i, "café") for i in range(1, 6)]
    itens = {f"{i:014d}/compras/2026/{i}": [item_api(1, "Café torrado e moído 500g", 10, 30.0)] for i in range(1, 6)}
    k = lista[0]["numeroControlePNCP"]
    rodar(destino, lista, itens)
    r2 = rodar(destino, lista, {**itens, "00000000000001/compras/2026/1": []}, agora=datetime(2026, 10, 20, 9, 0, tzinfo=coleta.TZ))
    by = {c["chave"]: c for c in json.loads((destino / "data.json").read_text(encoding="utf-8"))["compras"]}
    assert k in by and by[k]["first_seen"] == "2026-10-19" and r2.novas == [] and r2.falhas == []
    r3 = rodar(destino, lista, itens, agora=datetime(2026, 10, 21, 9, 0, tzinfo=coleta.TZ))
    by = {c["chave"]: c for c in json.loads((destino / "data.json").read_text(encoding="utf-8"))["compras"]}
    assert by[k]["first_seen"] == "2026-10-19" and by[k]["nova"] is False and r3.novas == []


def test_compra_nova_sem_itens_continua_fora(destino: Path) -> None:
    """Compra ainda desconhecida e sem itens publicados: não entra e não vai para o cache."""
    nova = compra_api("55555555000155", 5, "Aquisição de café")
    itens = {"11111111000111/compras/2026/1": [item_api(1, "Café torrado e moído 500g", 10, 30.0)]}
    r = rodar(destino, [CAFE, nova], itens)
    chaves = {c["chave"] for c in json.loads((destino / "data.json").read_text(encoding="utf-8"))["compras"]}
    assert nova["numeroControlePNCP"] not in chaves and r.falhas == []
    assert nova["numeroControlePNCP"] not in json.loads(coleta.CACHE.read_text(encoding="utf-8"))["itens"]


def test_falha_na_listagem_nao_altera_arquivos(destino: Path) -> None:
    rodar(destino, [CAFE])
    antes = (destino / "data.json").read_bytes()

    def quebrado(req: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="fora do ar")
    p = PNCP(httpx.Client(transport=httpx.MockTransport(quebrado)), tentativas=2, espera_base=0, intervalo_min=0)
    with pytest.raises(ColetaErro):
        coleta.coletar(destino, pncp=p, agora=AGORA)
    assert (destino / "data.json").read_bytes() == antes


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
    assert cache["versao"] == coleta.VERSAO_REGRAS
    assert OUTRA["numeroControlePNCP"] in cache["itens"] and CAFE["numeroControlePNCP"] not in cache["itens"]
    r = rodar(destino, [CAFE, OUTRA])
    assert r.candidatas == 1  # só a de café é baixada de novo


def test_cache_de_outra_versao_das_regras_e_descartado(destino: Path) -> None:
    coleta.CACHE.parent.mkdir()
    coleta.CACHE.write_text(json.dumps({OUTRA["numeroControlePNCP"]: OUTRA["dataAtualizacaoGlobal"]}))  # formato v1
    r = rodar(destino, [CAFE, OUTRA])
    assert r.candidatas == 2  # verifica de novo com as regras atuais


def test_compra_sem_itens_publicados_nao_vai_para_o_cache(destino: Path) -> None:
    rodar(destino, [CAFE, PNEU | {"objetoCompra": "Aquisição de café"}])
    assert PNEU["numeroControlePNCP"] not in json.loads(coleta.CACHE.read_text())["itens"]


def test_compra_que_some_da_listagem_e_conferida_pela_chave(destino: Path) -> None:
    nova = compra_api("55555555000155", 5, "Aquisição de café")
    itens = {**ITENS, "55555555000155/compras/2026/5": [item_api(1, "Café torrado e moído 250g", 100, 18.0)]}
    rodar(destino, [CAFE, nova], itens)
    # Dia seguinte: a listagem pula "nova" (paginação), mas ela continua aberta no PNCP.
    aberta = nova | {"situacaoCompraId": 1, "modalidadeId": 6}
    r = rodar(destino, [CAFE], itens, agora=datetime(2026, 10, 20, 9, 0, tzinfo=coleta.TZ),
              no_pncp={nova["numeroControlePNCP"]: aberta})
    by = {c["chave"]: c for c in json.loads((destino / "data.json").read_text())["compras"]}
    assert by[nova["numeroControlePNCP"]]["first_seen"] == "2026-10-19" and r.novas == []
    # Revogada: sai do painel.
    rodar(destino, [CAFE], itens, agora=datetime(2026, 10, 21, 9, 0, tzinfo=coleta.TZ),
          no_pncp={nova["numeroControlePNCP"]: aberta | {"situacaoCompraId": 2, "situacaoCompraNome": "Revogada"}},
          forcar=True)  # 2 -> 1 compra dispararia a trava de queda
    assert nova["numeroControlePNCP"] not in {c["chave"] for c in json.loads((destino / "data.json").read_text())["compras"]}


def test_compra_sumida_com_consulta_falhando_fica_como_antes(destino: Path) -> None:
    rodar(destino, [CAFE])
    r = rodar(destino, [], agora=datetime(2026, 10, 20, 9, 0, tzinfo=coleta.TZ), falhar={CAFE["numeroControlePNCP"]},
              forcar=True)
    c = json.loads((destino / "data.json").read_text())["compras"][0]
    assert c["chave"] == CAFE["numeroControlePNCP"] and c["first_seen"] == "2026-10-19" and r.falhas


def test_valor_que_arredonda_para_zero_vira_ausente(destino: Path) -> None:
    simbolico = compra_api("55555555000155", 5, "Aquisição de café")
    itens = {"55555555000155/compras/2026/5": [item_api(1, "Café torrado e moído 500g", 100, 0.0001, un="kg")]}
    rodar(destino, [simbolico], itens)  # antes: rkg 0.0 derrubava a validação e nada era publicado
    i = json.loads((destino / "data.json").read_text())["compras"][0]["itens"][0]
    assert i["rkg"] is None and i["vt"] is None or i["vt"] > 0


def test_texto_com_fim_de_script_fica_integro_no_data_json(destino: Path) -> None:
    """Texto do PNCP com "</script>" vai para o data.json como está (o site lê JSON, não embute em HTML)."""
    perigosa = compra_api("55555555000155", 5, "Café </script><script>window.XSS=1</script> <!-- x")
    itens = {"55555555000155/compras/2026/5": [item_api(1, "Café torrado 500g &lt;/script&gt;", 10, 30.0)]}
    rodar(destino, [perigosa], itens)
    data = json.loads((destino / "data.json").read_text(encoding="utf-8"))
    assert data["compras"][0]["objeto"] == perigosa["objetoCompra"]


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


def test_distancia_por_estrada_a_partir_de_uberaba() -> None:
    from coletor import distancias
    assert distancias.estrada("3156908") == (76, 72)  # Uberaba -> Sacramento por estrada (OSRM, 17/10/2026)
    assert distancias.estrada("3106200")[0] == 480  # Belo Horizonte
    assert distancias.estrada("9999999") == (None, None)


def _painel(compras: list[dict[str, Any]]) -> dict[str, Any]:
    for i, c in enumerate(compras):
        c["first_seen"] = "2026-10-19"
    return {"gerado_em": "2026-10-19T09:00:00-03:00", "compras": compras}


def _html_equilibrado(m: str) -> bool:
    import re
    abertas: list[str] = []
    for fecha, tag in re.findall(r"<(/?)(b|i|a|blockquote)\b[^>]*>", m):
        if fecha:
            if not abertas or abertas.pop() != tag:
                return False
        else:
            abertas.append(tag)
    return not abertas


def test_mensagens_telegram() -> None:
    def compra(seq: int, uf: str, mun: str, vu: float, desc: str = "Café torrado e moído superior 500g") -> dict[str, Any]:
        c = montar.montar_compra(compra_api(f"{seq:014d}", seq, "café", uf=uf, mun=mun),
                                 [item_api(1, desc, 1000, vu)])
        assert c
        return c
    base = [compra(i, "PR", "Curitiba", 40.0 + i) for i in range(1, 7)]  # mediana "Superior" ~R$ 87/kg
    perto = compra(50, "MG", "Sacramento", 60.0)  # R$ 120/kg: acima da mediana
    painel = _painel(base + [perto])
    msgs = telegram.mensagens([perto, base[0]], painel)
    m = msgs[0]
    assert "<b>2 licitações novas</b>" in m and "Segunda, 19/10/2026" in m
    assert m.index("Perto de você") < m.index("Sacramento · MG") < m.index("Demais estados") < m.index("Curitiba · PR")
    assert "nível Superior" in m and "▲" in m and "acima do preço típico do nível" in m
    assert "#c=00000000000050-1-000050%2F2026" in m  # abre direto a licitação no monitor
    assert "Prazo: " in m and "Abrir no monitor" in m and "PNCP" in m
    assert _html_equilibrado(m)
    # estilo pedido pelo dono (18/10/2026): sem linha decorativa, sem travessão longo, sem exclamação
    assert "━" not in m and "—" not in m and "!" not in m
    muitas = telegram.mensagens([compra(100 + i, "BA", "Salvador", 30.0) for i in range(60)], painel)
    assert len(muitas) > 1 and all(len(x) <= 4096 and _html_equilibrado(x) for x in muitas)
    assert muitas[1].startswith(f"<i>Continuação (2/{len(muitas)})</i>") and muitas[-1].rstrip().endswith("Abrir o monitor</a>")
    assert "Preço típico:" in muitas[0] and all("Preço típico:" not in x for x in muitas[1:])  # nota só na 1ª
    assert all(x.count("☕") <= 1 for x in muitas) and "☕" not in muitas[1]  # no máximo 1 emoji por mensagem
    vazio = telegram.mensagens([], painel)[0]
    assert "Nenhuma licitação nova" in vazio and "7 abertas no monitor" in vazio and _html_equilibrado(vazio)
    assert "\n" not in vazio and "Abrir o monitor" in vazio  # uma linha só, com a situação e o link


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


def test_descricao_limpa_html_e_usa_informacao_complementar() -> None:
    raw = item_api(52, "Café torrado e moído, <p>categoria&nbsp;Superior</p>  TIPO ÚNICO", 100, 30.0, un="Pct")
    raw["informacaoComplementar"] = "Pacote de 500g, vácuo"
    i = montar.montar_item(raw)
    assert i is not None
    assert i["espec"] == "Café torrado e moído, categoria Superior TIPO ÚNICO | Inf. compl.: Pacote de 500g, vácuo"
    assert i["kgu"] == 0.5  # o peso só estava na informação complementar


def test_duplicata_mantem_visivel_a_de_antes() -> None:
    a = montar.montar_compra(compra_api("11111111000111", 1, "café"), [item_api(1, "Café em pó 500g", 10, 30.0)])
    b = montar.montar_compra(compra_api("11111111000111", 2, "café"), [item_api(1, "Café em pó 500g", 10, 30.0)])
    assert a and b
    montar.marcar_duplicatas([a, b], visiveis_antes={b["chave"]})
    assert a["dup_of"] == b["chave"] and b["dup_of"] is None


def test_duplicata_sem_valor_com_itens_iguais() -> None:
    a = montar.montar_compra(compra_api("11111111000111", 1, "café"), [item_api(1, "Café em pó 500g", 10, None, sig=True)])
    b = montar.montar_compra(compra_api("22222222000122", 2, "café"), [item_api(1, "Café em pó 500g", 10, None, sig=True)])
    c = montar.montar_compra(compra_api("33333333000133", 3, "café"), [item_api(1, "Café em pó 250g", 99, None, sig=True)])
    assert a and b and c
    montar.marcar_duplicatas([a, b, c])
    assert {a["dup_of"], b["dup_of"]} == {None, a["chave"]} or {a["dup_of"], b["dup_of"]} == {None, b["chave"]}
    assert c["dup_of"] is None and c["dup"] == ""


def test_busca_pula_pagina_com_falha() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        p = int(req.url.params["pagina"])
        if p == 2:
            return httpx.Response(503)
        n = {1: "1", 3: "3"}.get(p)
        items = [{"numero_controle_pncp": f"{n}-{i}"} for i in range(100 if p == 1 else 10)] if n else []
        return httpx.Response(200, json={"total": 210, "items": items})
    p = PNCP(httpx.Client(transport=httpx.MockTransport(handler)), tentativas=2, espera_base=0, intervalo_min=0)
    achados = p.buscar("café")
    assert len(achados) == 110 and len(p.stats.falhas) == 1  # página 2 pulada, página 3 lida


def test_429_desacelera_e_insiste() -> None:
    respostas = iter([429, 429, 429, 200])

    def handler(req: httpx.Request) -> httpx.Response:
        st = next(respostas)
        return httpx.Response(200, json={"ok": 1}) if st == 200 else httpx.Response(429, text="limite")
    p = PNCP(httpx.Client(transport=httpx.MockTransport(handler)), espera_base=0, espera_429=0, intervalo_min=0.01)
    assert p.get_json("/x") == {"ok": 1}
    assert p.intervalo_min == pytest.approx(0.8 * 0.97)  # 0,1 -> 0,2 -> 0,4 -> 0,8 após três 429; -3% no sucesso
    assert p.stats.novas_tentativas == 3


def test_reclassificar_preenche_nivel_sem_pncp(destino: Path) -> None:
    from coletor.__main__ import main
    rodar(destino, [CAFE])
    data = json.loads((destino / "data.json").read_text(encoding="utf-8"))
    for c in data["compras"]:  # como os dados publicados antes do nível existir
        c.pop("niveis")
        for i in c["itens"]:
            i.pop("nivel"), i.pop("qg")
    (destino / "data.json").write_text(json.dumps(data), encoding="utf-8")
    assert main(["reclassificar", "--destino", str(destino)]) == 0
    c = json.loads((destino / "data.json").read_text(encoding="utf-8"))["compras"][0]
    assert c["niveis"] == ["Sem categoria", "Tradicional"] and c["itens"][0]["nivel"] == "Tradicional"  # selo ABIC; o grão não pede categoria


@pytest.mark.parametrize("sit,nome,entra", [
    (1, "Em andamento", True), (3, "Anulado/Revogado/Cancelado", False), (2, "Homologado", False),
    (4, "Deserto", False), (5, "Fracassado", False), (None, "Anulado/Revogado/Cancelado", False), (None, None, True),
])
def test_item_fora_de_andamento_nao_entra(sit: int | None, nome: str | None, entra: bool) -> None:
    raw = item_api(1, "Café torrado e moído 500g", 100, 30.0) | {"situacaoCompraItem": sit, "situacaoCompraItemNome": nome}
    assert (montar.montar_item(raw) is not None) is entra


def test_compra_com_cafe_cancelado_sai_do_painel(destino: Path) -> None:
    itens = {**ITENS, "11111111000111/compras/2026/1": [
        item_api(2, "Café torrado e moído, 500g", 1000, 30.0) | {"situacaoCompraItem": 3,
                                                                 "situacaoCompraItemNome": "Anulado/Revogado/Cancelado"}]}
    valida = compra_api("55555555000155", 5, "Aquisição de café")
    itens["55555555000155/compras/2026/5"] = [item_api(1, "Café torrado e moído 250g", 100, 18.0)]
    rodar(destino, [CAFE, valida], itens)
    chaves = {c["chave"] for c in json.loads((destino / "data.json").read_text())["compras"]}
    assert chaves == {valida["numeroControlePNCP"]}  # a compra segue aberta no PNCP, mas o café foi cancelado


def test_telegram_espera_quando_limitado(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "x")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    esperas: list[float] = []
    monkeypatch.setattr(telegram.time, "sleep", esperas.append)
    respostas = iter([httpx.Response(200, json={"ok": True}),
                      httpx.Response(429, json={"ok": False, "parameters": {"retry_after": 7}}),
                      httpx.Response(200, json={"ok": True})])
    telegram.enviar(["a", "b"], httpx.Client(transport=httpx.MockTransport(lambda req: next(respostas))))
    assert esperas == [telegram.PAUSA, 7.0]  # pausa entre mensagens + o tempo que o Telegram pediu


def test_telegram_429_sem_json_espera_o_padrao(monkeypatch: pytest.MonkeyPatch) -> None:
    """429 com página HTML (Cloudflare) em vez do JSON do Telegram: espera o padrão e tenta de novo, sem estourar."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "x")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    esperas: list[float] = []
    monkeypatch.setattr(telegram.time, "sleep", esperas.append)
    respostas = iter([httpx.Response(429, text="<html>Too Many Requests</html>", headers={"content-type": "text/html"}),
                      httpx.Response(200, json={"ok": True})])
    telegram.enviar(["a"], httpx.Client(transport=httpx.MockTransport(lambda req: next(respostas))))
    assert esperas == [5.0]


def test_cartao_telegram_numero_e_apostrofo() -> None:
    c = montar.montar_compra(compra_api("11111111000111", 1, "café", mun="Santa Bárbara d'Oeste", uf="SP") | {"numeroCompra": "114/2026"},
                             [item_api(1, "Café torrado e moído 500g", 10, 15.0)])
    assert c and c["num"] == "114/2026"  # o PNCP já manda o ano: não repete
    assert "d'Oeste" in telegram.cartao(c, {})


def test_cartao_telegram_mostra_marcas_e_nivel_do_edital() -> None:
    c = montar.montar_compra(compra_api("11111111000111", 1, "café"), [item_api(1, "Café torrado e moído 500g", 10, 15.0)])
    assert c
    c["itens"][0]["ed_trecho"] = "cafe torrado e moido categoria superior, marca de referencia pilao"
    montar.reclassificar_nivel(c)
    c["marcas"] = ["Pilão", "3 Corações", "Melitta", "Caboclo", "Café do Ponto"]
    t = telegram.cartao(c, {})
    assert "nível Superior (pelo edital)" in t and "Marcas de referência: Pilão, 3 Corações, Melitta, Caboclo e outras" in t


def test_compra_de_cesta_basica_fica_fora() -> None:
    c = compra_api("11111111000111", 1, "Registro de preços para aquisição de cestas básicas")
    assert montar.montar_compra(c, [item_api(1, "Café torrado e moído 500g", 10, 15.0)]) is None


@pytest.mark.parametrize("desc", ["Café solúvel 200g", "Cápsula de café espresso", "Café pronto para consumo, garrafa 1 litro",
                                  "Cesta básica com arroz, feijão, açúcar, óleo, macarrão e café", "Café cru em grãos, saca 60 kg",
                                  "café arábica cru beneficiado", "Café verde arábica, saca de 60kg"])
def test_so_cafe_torrado_entra(desc: str) -> None:
    assert montar.montar_item(item_api(1, desc, 10, 30.0)) is None


@pytest.mark.parametrize("n,esperado", [("37", "37/2026"), ("114/2026", "114/2026"), ("2809001/2026-PE", "2809001/2026-PE"),
                                         ("PMCA 044/26", "PMCA 044/26"), ("90076/PE/NATURATINS", "90076/PE/NATURATINS/2026")])
def test_numero_da_compra_sem_ano_repetido(n: str, esperado: str) -> None:
    assert montar.numero(n, 2026) == esperado


def test_margem_estimada_no_telegram_e_contas() -> None:
    from coletor import custos, mercado, referencia
    c = montar.montar_compra(compra_api("11111111000111", 1, "café"), [item_api(1, "Café torrado e moído superior 500g", 1000, 35.0)])
    assert c
    c["dist"] = 500
    i = referencia.item_principal(c)
    mk = {"niveis": {"Superior": {"kg_medio": 26.0}}}
    p = custos.premissas()
    m = custos.margem(c, i, mk, p)
    assert m is not None and i["rkg"] == 70.0
    grao = 26.0 / 0.82
    assert m["grao"] == round(grao, 2) and m["torra"] == round(5 / 0.82, 2)
    frete = custos.frete_total(500.0, 500, 70.0, c["srp"] == "Sim", p) / 500
    direto = grao + 5 / 0.82 + 5
    custo = direto + frete + (129 + 2 * direto) / 500 + 70 * (0.045 + 0.026 + 0.01)
    assert abs(m["custo"] - custo) < 0.01 and abs(m["margem_pct"] - (70 - custo) / 70) < 0.0001
    assert custos.margem({**c, "dist": None}, i, mk, p) is None  # sem distância não estima
    real = mercado.carregar()
    if real.get("niveis"):
        assert "Margem estimada ~" in telegram.cartao(c, {})
