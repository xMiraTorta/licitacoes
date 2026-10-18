"""Atualização semanal do preço de varejo das marcas (coletor/varejo.py), sem internet."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from coletor import varejo


def _produto(nome: str, preco: float, disponivel: int = 10) -> dict[str, Any]:
    return {"productName": nome, "link": "/x/p",
            "items": [{"sellers": [{"commertialOffer": {"Price": preco, "AvailableQuantity": disponivel}}]}]}


PILAO = [_produto("Café Torrado e Moído a Vácuo Tradicional Pilão 500g", 22.0),
         _produto("Café Pilão Extra Forte Vácuo 500g", 23.0),
         _produto("Café Pilão Grãos Espresso 1kg", 100.0),
         _produto("Cápsula Café Pilão Espresso 10 unidades", 20.0),   # cápsula: fora
         _produto("Café Pilão Tradicional 3kg", 90.0),                 # fora da faixa 250 g a 1 kg
         _produto("Café Pilão Tradicional 250g", 11.0, disponivel=0)]  # indisponível


def _base(tmp_path: Path) -> Path:
    linhas = [{"marca": "Pilão", "linha": linha, "categoria": cat, "preco_kg_min": 1.0, "preco_kg_max": 2.0, "precos_fontes": []}
              for linha, cat in (("Tradicional", "Tradicional"), ("Extra Forte", "Extraforte"), ("Espresso (grão)", "Gourmet"),
                                 ("Cafeteria", "Superior"))]
    p = tmp_path / "marcas.json"
    p.write_text(json.dumps({"pesquisa_em": "2026-10-18", "linhas": linhas}), encoding="utf-8")
    return p


def _cliente(lojas_ok: int) -> httpx.Client:
    ok = set(varejo.LOJAS[:lojas_ok])

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.host not in ok:
            return httpx.Response(403)
        return httpx.Response(200, json={"products": PILAO if "pilao" in req.url.params["query"] else []})
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_separa_por_linha_e_calcula_rkg(tmp_path: Path) -> None:
    base = _base(tmp_path)
    assert varejo.atualizar(base, "2026-10-26", _cliente(len(varejo.LOJAS))) == 3
    ls = {x["linha"]: x for x in json.loads(base.read_text(encoding="utf-8"))["linhas"]}
    assert (ls["Tradicional"]["preco_kg_min"], ls["Tradicional"]["preco_kg_max"]) == (44.0, 44.0)
    assert ls["Extra Forte"]["preco_kg_min"] == 46.0 and ls["Espresso (grão)"]["preco_kg_min"] == 100.0
    assert ls["Tradicional"]["preco_em"] == "2026-10-26" and ls["Tradicional"]["lojas"] == len(varejo.LOJAS)
    assert ls["Cafeteria"]["preco_kg_min"] == 1.0 and "preco_em" not in ls["Cafeteria"]  # sem oferta: mantém o anterior


def test_poucas_lojas_nao_grava(tmp_path: Path) -> None:
    base = _base(tmp_path)
    antes = base.read_text(encoding="utf-8")
    with pytest.raises(RuntimeError):
        varejo.atualizar(base, "2026-10-26", _cliente(varejo.MIN_LOJAS_OK - 1))
    assert base.read_text(encoding="utf-8") == antes


def test_base_real_tem_preco_e_data() -> None:
    from coletor import marcas
    r = marcas.resumo()
    assert r["pesquisa_em"] and r["marcas"]["Pilão"]["basica"]["min"] > 0
