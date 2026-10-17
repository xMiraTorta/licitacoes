"""Testes da página no navegador (Chromium headless), com dados de teste locais."""
from __future__ import annotations

import json
from typing import Any

from playwright.sync_api import Page

from tests.conftest import wait_ready

WFK = "cafeBizinotto.meusDados.v1"
UIK = "cafeBizinotto.ui.v1"
CLK = "cafeBizinotto.checklist.v1"
FIRST = "18243295000192-1-000080/2026"  # torrado e moído 500 g, R$ 66,03/kg


def ls(page: Page, key: str) -> Any:
    raw = page.evaluate("k => localStorage.getItem(k)", key)
    return None if raw is None else json.loads(raw)


def open_card(page: Page, chave: str) -> Any:
    card = page.locator(f'article.card[data-ch="{chave}"]')
    card.locator('[data-act="toggle"]').click()
    return page.locator(f'article.card[data-ch="{chave}"]')


def test_real_site_loads_without_errors(page: Page, real_url: str) -> None:
    page.goto(real_url + "/index.html")
    wait_ready(page)
    assert page.evaluate("window.__cafe.count()") > 0
    for tab in ("charts", "check", "about", "list"):
        page.click(f'[data-tab="{tab}"]')
    page.click('[data-view="table"]')
    assert page.locator("tr.r").count() > 0


def test_duplicates_hidden_by_default(page: Page, fixture_url: str) -> None:
    page.goto(fixture_url + "/index.html")
    wait_ready(page)
    assert page.evaluate("window.__cafe.count()") == 8  # 9 compras, 1 duplicata oculta
    page.click('label.toggle:has-text("Ocultar possíveis duplicatas")')
    assert page.evaluate("window.__cafe.count()") == 9


def test_search_and_quick_filter(page: Page, fixture_url: str) -> None:
    page.goto(fixture_url + "/index.html")
    wait_ready(page)
    page.fill("#q", "conceicao aparecida")
    page.wait_for_function("window.__cafe.count() === 1")
    page.fill("#q", "")
    page.wait_for_function("window.__cafe.count() === 8")
    page.click('[data-q="uf:MG"]')
    mg = page.evaluate("window.__cafe.count()")
    assert 0 < mg < 8


def test_personal_data_persists_after_reload(page: Page, fixture_url: str) -> None:
    page.goto(fixture_url + "/index.html")
    wait_ready(page)
    card = page.locator(f'article.card[data-ch="{FIRST}"]')
    card.locator('[data-act="fav"]').click()
    card = open_card(page, FIRST)
    card.locator('[data-w="preco"]').fill("55,50")
    card.locator('[data-w="status"]').select_option("Enviada")
    card.locator('[data-w="resp"]').fill("Vinicius")
    card.locator('[data-w="notas"]').fill("frete CIF")
    card.locator('[data-w="notas"]').blur()
    page.wait_for_timeout(500)
    page.reload()
    wait_ready(page)
    w = ls(page, WFK)[FIRST]
    assert w["fav"] is True and w["preco"] == 55.5 and w["status"] == "Enviada"
    assert w["resp"] == "Vinicius" and w["notas"] == "frete CIF" and "upd" in w
    assert "★ Favoritos" in page.locator('[data-q="fav"]').inner_text()


def test_price_input_parsing(page: Page, fixture_url: str) -> None:
    page.goto(fixture_url + "/index.html")
    wait_ready(page)
    card = open_card(page, FIRST)
    for typed, expected in (("55,5", 55.5), ("1.234,56", 1234.56), ("R$ 60", 60.0)):
        card.locator('[data-w="preco"]').fill(typed)
        page.wait_for_timeout(450)
        assert ls(page, WFK)[FIRST]["preco"] == expected, typed


def test_margin_against_estimate(page: Page, fixture_url: str) -> None:
    page.goto(fixture_url + "/index.html")
    wait_ready(page)
    card = open_card(page, FIRST)
    card.locator('[data-w="preco"]').fill("59,43")
    page.wait_for_timeout(450)
    calc = card.locator("[data-calc]").inner_text()
    assert "+10%" in calc  # (66,03 - 59,43) / 66,03
    assert "R$ 359.076" in calc and "6.042 kg" in calc  # 59,43 × 6.042 kg


def test_checklist_persists(page: Page, fixture_url: str) -> None:
    page.goto(fixture_url + "/index.html")
    wait_ready(page)
    page.click('[data-tab="check"]')
    page.click('[data-cl="0"]')
    assert ls(page, CLK) == {"0": 1}


def test_export_import_roundtrip(page: Page, fixture_url: str) -> None:
    page.goto(fixture_url + "/index.html")
    wait_ready(page)
    backup = {"app": "cafe-bizinotto-licitacoes", "versao": 1, "exportado_em": "2026-10-17T12:00:00Z",
              "meus_dados": {FIRST: {"fav": True, "notas": "importada", "upd": "2026-10-17T12:00:00Z"}},
              "checklist": {"3": 1}}
    n = page.evaluate("t => window.__cafe.importText(t)", json.dumps(backup))
    assert n == 1
    assert ls(page, WFK)[FIRST]["notas"] == "importada"
    assert ls(page, CLK) == {"3": 1}
    # importação de entrada mais antiga não sobrescreve a mais nova
    older = {"meus_dados": {FIRST: {"notas": "velha", "upd": "2020-01-01T00:00:00Z"}}}
    assert page.evaluate("t => window.__cafe.importText(t)", json.dumps(older)) == 0
    assert ls(page, WFK)[FIRST]["notas"] == "importada"


def test_csv_export(page: Page, fixture_url: str) -> None:
    page.goto(fixture_url + "/index.html")
    wait_ready(page)
    csv = page.evaluate("window.__cafe.csvText()")
    assert csv["n"] == 8
    lines = csv["csv"].lstrip("﻿").split("\r\n")
    assert lines[0].startswith("Chave PNCP;Prazo final;")
    assert len(lines) == 9


def test_secret_budget_shown_as_secret_not_zero(page: Page, fixture_url: str) -> None:
    page.goto(fixture_url + "/index.html")
    wait_ready(page)
    card = page.locator('article.card[data-ch="95440517000108-1-000295/2026"]')
    assert "Sigiloso" in card.locator(".nums").inner_text()
    assert "R$ 0" not in card.inner_text()


def test_ui_state_saved(page: Page, fixture_url: str) -> None:
    page.goto(fixture_url + "/index.html")
    wait_ready(page)
    page.click('[data-view="table"]')
    page.select_option("#sort", "valor")
    ui = ls(page, UIK)
    assert ui["view"] == "table" and ui["sort"] == "valor"
