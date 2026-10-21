"""Preço do café verde por nível (coletor/mercado.py), com trechos das páginas reais (18/10/2026), sem internet."""
from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from coletor import mercado

CEPEA = """<div>INDICADOR DO CAFÉ ARÁBICA CEPEA/ESALQ</div><table><tr><th>Valor R$</th></tr>
<tr><td>16/10/2026</td> <td>1.601,25</td><td>1,52%</td></tr><tr><td>15/10/2026</td><td>1.577,21</td></tr></table>
<div>INDICADOR DO CAFÉ ROBUSTA CEPEA/ESALQ</div><table><tr><th>Valor R$</th></tr>
<tr><td>16/10/2026</td> <td>963,28</td><td>-0,50%</td></tr></table>"""
CARVALHAES = """<table><tr><td>CD Finos - cereja descascado</td><td>16/10/26</td><td>1.900,00/2.000,00</td></tr>
<tr><td>Finos a Extra-Finos - Mogiana e Minas</td><td>16/10/26</td><td>1.750,00/1.820,00</td></tr>
<tr><td>Boa Qualidade: duros, bem preparados</td><td>16/10/26</td><td>1.700,00/1.750,00</td></tr>
<tr><td>Duros com xícaras mais fracas</td><td>16/10/26</td><td>1.500,00/1.550,00</td></tr>
<tr><td>Riados</td><td>16/10/26</td><td>1.350,00/1.400,00</td></tr><tr><td>Rio</td><td>16/10/26</td><td>1.300,00/1.350,00</td></tr>
<tr><td>Consumo interno: Dura</td><td>16/10/26</td><td>1.300,00/1.350,00</td></tr>
<tr><td>Consumo interno: Riadas</td><td>16/10/26</td><td>1.250,00/1.300,00</td></tr></table>"""


def test_le_paginas_e_calcula_niveis() -> None:
    cepea, carv = mercado.ler_cepea(CEPEA), mercado.ler_carvalhaes(CARVALHAES)
    assert cepea == {"arabica": {"data": "2026-10-16", "saca60": 1601.25}, "robusta": {"data": "2026-10-16", "saca60": 963.28}}
    assert carv["data"] == "2026-10-16" and carv["saca60"]["cd_finos"] == [round(1900 * 60 / 60.5, 2), round(2000 * 60 / 60.5, 2)]
    n = mercado.niveis(cepea, carv)
    rio = 1300 * 60 / 60.5
    assert n["Tradicional"]["saca60_min"] == round(0.6 * rio + 0.4 * 963.28, 2)
    assert n["Superior"]["saca60_max"] == round(1750 * 60 / 60.5, 2)
    assert n["Sem categoria"]["kg_medio"] == n["Tradicional"]["kg_medio"]
    assert n["Tradicional"]["kg_min"] < n["Superior"]["kg_min"] < n["Gourmet/especial"]["kg_min"]


def test_carvalhaes_abaixo_de_mil_reais() -> None:
    """Classe cotada abaixo de R$ 1.000,00 (sem ponto de milhar) tem de ser lida, não derrubar a atualização."""
    baixa = CARVALHAES.replace("1.300,00/1.350,00</td></tr>\n<tr><td>Consumo interno: Riadas", "950,00/1.010,00</td></tr>\n<tr><td>Consumo interno: Riadas") \
        .replace("<td>1.250,00/1.300,00</td>", "<td>900,00/950,00</td>")
    carv = mercado.ler_carvalhaes(baixa)
    assert carv["saca60"]["consumo_dura"] == [round(950 * 60 / 60.5, 2), round(1010 * 60 / 60.5, 2)]
    assert carv["saca60"]["consumo_riada"] == [round(900 * 60 / 60.5, 2), round(950 * 60 / 60.5, 2)]
    assert carv["saca60"]["cd_finos"] == [round(1900 * 60 / 60.5, 2), round(2000 * 60 / 60.5, 2)]  # com milhar segue igual


def test_pagina_mudou_nao_grava(tmp_path: Path) -> None:
    destino = tmp_path / "mercado.json"
    destino.write_text('{"antigo": true}', encoding="utf-8")

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=CEPEA if "cepea" in req.url.host else "<html>página nova</html>")
    with pytest.raises(ValueError):
        mercado.atualizar("2026-10-26", httpx.Client(transport=httpx.MockTransport(handler)), destino)
    assert destino.read_text(encoding="utf-8") == '{"antigo": true}'


def test_grava_quando_tudo_ok(tmp_path: Path) -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=(CEPEA if "cepea" in req.url.host else CARVALHAES).encode("utf-8" if "cepea" in req.url.host else "latin-1"))
    d = mercado.atualizar("2026-10-26", httpx.Client(transport=httpx.MockTransport(handler)), tmp_path / "m.json")
    assert d["atualizado_em"] == "2026-10-26" and (tmp_path / "m.json").exists()


def test_cepea_bloqueado_usa_indicador_anterior(tmp_path: Path) -> None:
    destino = tmp_path / "m.json"

    def ok(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=CEPEA.encode("utf-8") if "cepea" in req.url.host else CARVALHAES.encode("latin-1"))
    mercado.atualizar("2026-10-19", httpx.Client(transport=httpx.MockTransport(ok)), destino)

    def bloqueado(req: httpx.Request) -> httpx.Response:
        return httpx.Response(403) if "cepea" in req.url.host else httpx.Response(200, content=CARVALHAES.encode("latin-1"))
    d = mercado.atualizar("2026-10-26", httpx.Client(transport=httpx.MockTransport(bloqueado)), destino)
    assert d["atualizado_em"] == "2026-10-26" and d["cepea"]["robusta"] == {"data": "2026-10-16", "saca60": 963.28}
    with pytest.raises(httpx.HTTPStatusError):  # sem indicador anterior, não inventa
        mercado.atualizar("2026-10-26", httpx.Client(transport=httpx.MockTransport(bloqueado)), tmp_path / "novo.json")
