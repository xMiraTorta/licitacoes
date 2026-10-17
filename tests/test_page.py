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


def test_corrupted_storage_is_backed_up_not_erased(page: Page, fixture_url: str) -> None:
    page.goto(fixture_url + "/index.html")
    wait_ready(page)
    broken = '{"A":{"fav":true},"B":{"notas":"importante"'
    page.evaluate("([k, v]) => localStorage.setItem(k, v)", [WFK, broken])
    page.reload()
    wait_ready(page)
    page.locator(f'article.card[data-ch="{FIRST}"] [data-act="fav"]').click()
    keys = page.evaluate("Object.keys(localStorage)")
    copies = [k for k in keys if k.startswith(WFK + ".ilegivel.")]
    assert len(copies) == 1
    assert page.evaluate("k => localStorage.getItem(k)", copies[0]) == broken
    assert ls(page, WFK)[FIRST]["fav"] is True
    alert = page.locator("#badData")
    assert "ilegíveis" in alert.inner_text()
    page.click("#badDataOk")
    assert alert.count() == 0


def test_undo_import_restores_previous_data(page: Page, fixture_url: str) -> None:
    page.goto(fixture_url + "/index.html")
    wait_ready(page)
    page.locator(f'article.card[data-ch="{FIRST}"] [data-act="fav"]').click()
    page.click('[data-tab="check"]')
    page.click('[data-cl="2"]')
    before_wf, before_cl = ls(page, WFK), ls(page, CLK)
    imp = {"meus_dados": {"X-1-000001/2026": {"notas": "outra", "upd": "2030-01-01T00:00:00Z"}}, "checklist": {"5": 1}}
    page.evaluate("t => window.__cafe.importText(t)", json.dumps(imp))
    assert "X-1-000001/2026" in ls(page, WFK)
    page.click("#dataBtn")
    page.click("#undoImp")
    assert ls(page, WFK) == before_wf and ls(page, CLK) == before_cl
    assert ls(page, "cafeBizinotto.antesDaImportacao.v1") is None
    page.click("#dataBtn")
    page.click("#undoImp")
    assert "Nenhuma importação" in page.locator("#toast").inner_text()


SOLUVEL_ONLY = "77402196000175-1-000046/2026"  # T&M sem peso + solúvel 0,5 kg a R$ 300/kg
MIXED = "01612911000132-1-000128/2026"  # T&M R$ 46,94/kg (696,5 kg) + solúvel R$ 151,55/kg
CAPSULE = "75458836000133-1-000147/2026"  # T&M 400 kg + cápsulas sem peso


def card_nums(page: Page, chave: str) -> str:
    return page.locator(f'article.card[data-ch="{chave}"] .nums').inner_text()


def test_price_per_kg_separated_by_coffee_type(page: Page, fixture_url: str) -> None:
    page.goto(fixture_url + "/index.html")
    wait_ready(page)
    mixed = card_nums(page, MIXED)
    assert "R$ 46,94" in mixed and "solúvel R$ 151,55" in mixed  # antes: R$ 61,10 misturado
    sol = card_nums(page, SOLUVEL_ONLY).lower()
    assert "r$ 300,00" in sol and "solúvel" in sol  # identificado como solúvel, não como T&M
    assert "R$ 66,03" in card_nums(page, FIRST)


def test_median_and_sort_use_only_roast_and_ground(page: Page, fixture_url: str) -> None:
    page.goto(fixture_url + "/index.html")
    wait_ready(page)
    kpi = page.locator('.kpi[data-k="rkg"]').inner_text()
    # T&M visíveis (sem a duplicata oculta): 66,03; 46,94; 58,42; 63,52. Com o solúvel (300) daria outra.
    assert "R$ 60,97" in kpi and "4 de torrado e moído" in kpi
    page.select_option("#sort", "rkg_desc")
    first = page.locator("article.card").first.get_attribute("data-ch")
    assert first != SOLUVEL_ONLY  # R$ 300/kg de solúvel não lidera a ordenação de T&M


def test_partial_volume_marked_when_item_has_no_weight(page: Page, fixture_url: str) -> None:
    page.goto(fixture_url + "/index.html")
    wait_ready(page)
    assert "≥ 400 kg" in card_nums(page, CAPSULE)
    assert "≥" not in card_nums(page, FIRST)


def test_margin_uses_type_specific_price(page: Page, fixture_url: str) -> None:
    page.goto(fixture_url + "/index.html")
    wait_ready(page)
    card = open_card(page, MIXED)
    card.locator('[data-w="preco"]').fill("42,25")
    page.wait_for_timeout(450)
    calc = card.locator("[data-calc]").inner_text()
    assert "R$ 46,94/kg (torrado e moído)" in calc and "+10%" in calc
    assert "só torrado e moído" in calc and "R$ 29.427" in calc and "697 kg" in calc  # 42,25 × 696,5 kg


def test_single_type_price_matches_generator(page: Page, real_url: str) -> None:
    """Onde há um só tipo com R$/kg, o valor recalculado na página bate com o do gerador."""
    page.goto(real_url + "/index.html")
    wait_ready(page)
    bad = page.evaluate("""() => window.__cafe.rkCheck()""")
    assert bad == [], bad
