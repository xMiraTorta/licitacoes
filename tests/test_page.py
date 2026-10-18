"""Testes da página no navegador (Chromium headless), com dados de teste locais."""
from __future__ import annotations

import json
from typing import Any

from playwright.sync_api import Locator, Page

from tests.conftest import wait_ready

WFK = "monitorLicitacoes.meusDados.v1"
UIK = "monitorLicitacoes.ui.v1"
CLK = "monitorLicitacoes.checklist.v1"
FIRST = "18243295000192-1-000080/2026"  # torrado e moído 500 g, R$ 66,03/kg
SOLUVEL_ONLY = "77402196000175-1-000046/2026"  # T&M sem peso + solúvel 0,5 kg a R$ 300/kg
MIXED = "01612911000132-1-000128/2026"  # T&M R$ 46,94/kg (696,5 kg) + solúvel R$ 151,55/kg
CAPSULE = "75458836000133-1-000147/2026"  # T&M 400 kg + cápsulas sem peso
SIGILOSO = "95440517000108-1-000295/2026"
DUP = "01612382000177-1-000090/2026"  # dup_of no conjunto de teste


def ls(page: Page, key: str) -> Any:
    raw = page.evaluate("k => localStorage.getItem(k)", key)
    return None if raw is None else json.loads(raw)


def row(page: Page, chave: str) -> Locator:
    return page.locator(f'#list .row[data-ch="{chave}"]')


def open_detail(page: Page, chave: str) -> Locator:
    row(page, chave).locator(".c-loc").click()
    d = page.locator("#drawer.show")
    d.wait_for()
    return d


def goto(page: Page, url: str) -> None:
    page.goto(url + "/index.html")
    wait_ready(page)


def test_real_site_loads_without_errors(page: Page, real_url: str) -> None:
    goto(page, real_url)
    assert page.evaluate("window.__monitor.count()") > 0
    for tab in ("mine", "agenda", "charts", "check", "about", "list"):
        page.click(f'[data-tab="{tab}"]')
        assert page.locator(f"#tab-{tab}").is_visible()
    assert page.locator("#list .row").count() > 0
    assert all(k.startswith("monitorLicitacoes.") for k in page.evaluate("Object.keys(localStorage)"))


def test_duplicates_hidden_by_default(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    assert page.evaluate("window.__monitor.count()") == 8  # 9 compras, 1 duplicata oculta
    page.click('label.toggle:has-text("Ocultar possíveis duplicatas")')
    assert page.evaluate("window.__monitor.count()") == 9


def test_search_and_quick_filter(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    page.fill("#q", "conceicao aparecida")
    page.wait_for_function("window.__monitor.count() === 1")
    page.fill("#q", "")
    page.wait_for_function("window.__monitor.count() === 8")
    page.click('[data-q="uf:MG"]')
    mg = page.evaluate("window.__monitor.count()")
    assert 0 < mg < 8


def test_detail_drawer_opens_closes_and_back_button(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    d = open_detail(page, FIRST)
    assert "Conceição da Aparecida" in d.inner_text()
    assert page.url.endswith("#c=" + FIRST.replace("/", "%2F"))
    page.go_back()
    page.wait_for_function("!document.querySelector('#drawer').classList.contains('show')")
    open_detail(page, FIRST)
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('#drawer').classList.contains('show')")


def test_personal_data_persists_after_reload(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    row(page, FIRST).locator('[data-act="fav"]').click()
    d = open_detail(page, FIRST)
    d.locator('[data-w="preco"]').fill("55,50")
    d.locator('[data-w="status"]').select_option("Enviada")
    d.locator('[data-w="resp"]').fill("Vinicius")
    d.locator('[data-w="notas"]').fill("frete CIF")
    d.locator('[data-w="notas"]').blur()
    page.wait_for_timeout(500)
    page.reload()
    wait_ready(page)
    w = ls(page, WFK)[FIRST]
    assert w["fav"] is True and w["preco"] == 55.5 and w["status"] == "Enviada"
    assert w["resp"] == "Vinicius" and w["notas"] == "frete CIF" and "upd" in w
    assert "★ Favoritos" in page.locator('[data-q="fav"]').inner_text()


def test_my_proposals_board_groups_by_status(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    wf = {FIRST: {"fav": True, "upd": "x"}, MIXED: {"status": "Enviada", "upd": "x"}}
    page.evaluate("([k, v]) => localStorage.setItem(k, v)", [WFK, json.dumps(wf)])
    page.reload()
    wait_ready(page)
    assert page.locator("#n-mine").inner_text() == "2"
    page.click('[data-tab="mine"]')
    cols = page.locator("#board .col")
    assert "Favoritas sem status" in cols.nth(0).inner_text() and "Conceição" in cols.nth(0).inner_text()
    enviada = page.locator('#board .col:has(h3:has-text("Enviada"))')
    assert enviada.locator(f'.mini[data-ch="{MIXED}"]').count() == 1
    enviada.locator(".mini").click()
    page.locator("#drawer.show").wait_for()


def test_agenda_lists_followed_deadlines(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    page.evaluate("([k, v]) => localStorage.setItem(k, v)", [WFK, json.dumps({FIRST: {"fav": True, "upd": "x"}})])
    page.reload()
    wait_ready(page)
    page.click('[data-tab="agenda"]')
    assert page.locator("#agenda .row").count() == 1
    page.click('[data-ag="1"]')
    assert page.locator("#agenda .row").count() == 8


def test_price_input_parsing(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    d = open_detail(page, FIRST)
    for typed, expected in (("55,5", 55.5), ("1.234,56", 1234.56), ("R$ 60", 60.0)):
        d.locator('[data-w="preco"]').fill(typed)
        page.wait_for_timeout(450)
        assert ls(page, WFK)[FIRST]["preco"] == expected, typed


def test_margin_against_estimate(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    d = open_detail(page, FIRST)
    d.locator('[data-w="preco"]').fill("59,43")
    page.wait_for_timeout(450)
    calc = d.locator("[data-calc]").inner_text()
    assert "+10%" in calc  # (66,03 - 59,43) / 66,03
    assert "R$ 359.076" in calc and "6.042 kg" in calc  # 59,43 × 6.042 kg


def test_checklist_persists_and_shows_progress(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    page.click('[data-tab="check"]')
    page.click('[data-cl="0"]')
    assert ls(page, CLK) == {"0": 1}
    assert "1 de " in page.locator("#gside").inner_text()


def test_export_import_roundtrip(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    backup = {"app": "monitor-licitacoes", "versao": 1, "exportado_em": "2026-10-17T12:00:00Z",
              "meus_dados": {FIRST: {"fav": True, "notas": "importada", "upd": "2026-10-17T12:00:00Z"}},
              "checklist": {"3": 1}}
    assert page.evaluate("t => window.__monitor.importText(t)", json.dumps(backup)) == 1
    assert ls(page, WFK)[FIRST]["notas"] == "importada"
    assert ls(page, CLK) == {"3": 1}
    # importação de entrada mais antiga não sobrescreve a mais nova
    older = {"meus_dados": {FIRST: {"notas": "velha", "upd": "2020-01-01T00:00:00Z"}}}
    assert page.evaluate("t => window.__monitor.importText(t)", json.dumps(older)) == 0
    assert ls(page, WFK)[FIRST]["notas"] == "importada"


def test_csv_export(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    csv = page.evaluate("window.__monitor.csvText()")
    assert csv["n"] == 8
    lines = csv["csv"].lstrip("﻿").split("\r\n")
    assert lines[0].startswith("Chave PNCP;Prazo final;")
    assert len(lines) == 9


def test_secret_budget_shown_as_secret_not_zero(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    r = row(page, SIGILOSO)
    assert "Sigiloso" in r.locator(".c-valor").inner_text()
    assert "R$ 0" not in r.inner_text()


def test_ui_state_saved(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    page.select_option("#sort", "valor")
    page.click('[data-tab="charts"]')
    ui = ls(page, UIK)
    assert ui["sort"] == "valor" and ui["tab"] == "charts"
    page.reload()
    wait_ready(page)
    assert page.locator("#tab-charts").is_visible()


def test_theme_toggle_saved(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    page.click("#themeBtn")
    theme = ls(page, UIK)["theme"]
    assert theme in ("dark", "light")
    assert page.evaluate("document.documentElement.dataset.theme") == theme


def test_corrupted_storage_is_backed_up_not_erased(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    broken = '{"A":{"fav":true},"B":{"notas":"importante"'
    page.evaluate("([k, v]) => localStorage.setItem(k, v)", [WFK, broken])
    page.reload()
    wait_ready(page)
    row(page, FIRST).locator('[data-act="fav"]').click()
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
    goto(page, fixture_url)
    row(page, FIRST).locator('[data-act="fav"]').click()
    page.click('[data-tab="check"]')
    page.click('[data-cl="2"]')
    before_wf, before_cl = ls(page, WFK), ls(page, CLK)
    imp = {"meus_dados": {"99999999000199-1-000001/2026": {"notas": "outra", "upd": "2030-01-01T00:00:00Z"}}, "checklist": {"5": 1}}
    page.evaluate("t => window.__monitor.importText(t)", json.dumps(imp))
    assert "99999999000199-1-000001/2026" in ls(page, WFK)
    page.click("#dataBtn")
    page.click("#undoImp")
    assert ls(page, WFK) == before_wf and ls(page, CLK) == before_cl
    assert ls(page, "monitorLicitacoes.antesDaImportacao.v1") is None
    page.click("#dataBtn")
    page.click("#undoImp")
    assert "Nenhuma importação" in page.locator("#toast").inner_text()


def test_price_per_kg_separated_by_coffee_type(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    assert "R$ 46,94" in row(page, MIXED).locator(".c-rkg").inner_text()  # antes: R$ 61,10 misturado
    sol = row(page, SOLUVEL_ONLY).locator(".c-rkg").inner_text().lower()
    assert "r$ 300,00" in sol and "solúvel" in sol  # identificado como solúvel, não como T&M
    d = open_detail(page, MIXED)
    assert "solúvel R$ 151,55" in d.locator(".facts").inner_text()


def test_median_and_sort_use_only_roast_and_ground(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    kpi = page.locator('.kpi[data-k="rkg"]').inner_text()
    # T&M visíveis (sem a duplicata oculta): 66,03; 46,94; 58,42; 63,52. Com o solúvel (300) daria outra.
    assert "R$ 60,97" in kpi and "4 de torrado e moído" in kpi
    page.select_option("#sort", "rkg_desc")
    assert page.locator("#list .row").first.get_attribute("data-ch") != SOLUVEL_ONLY


def test_partial_volume_marked_when_item_has_no_weight(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    assert "≥ 400 kg" in row(page, CAPSULE).locator(".c-valor").inner_text()
    assert "≥" not in row(page, FIRST).locator(".c-valor").inner_text()


def test_margin_uses_type_specific_price(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    d = open_detail(page, MIXED)
    d.locator('[data-w="preco"]').fill("42,25")
    page.wait_for_timeout(450)
    calc = d.locator("[data-calc]").inner_text()
    assert "R$ 46,94/kg (torrado e moído)" in calc and "+10%" in calc
    assert "só torrado e moído" in calc and "R$ 29.427" in calc and "697 kg" in calc  # 42,25 × 696,5 kg


def test_single_type_price_matches_generator(page: Page, real_url: str) -> None:
    """Onde há um só tipo com R$/kg, o valor recalculado na página bate com o do coletor."""
    goto(page, real_url)
    assert page.evaluate("window.__monitor.rkCheck()") == []


def test_duplicate_with_my_data_is_never_hidden(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    assert row(page, DUP).count() == 0
    page.evaluate("([k, v]) => localStorage.setItem(k, v)",
                  [WFK, json.dumps({DUP: {"fav": True, "upd": "2026-10-17T12:00:00Z"}})])
    page.reload()
    wait_ready(page)
    assert row(page, DUP).count() == 1
    assert page.evaluate("window.__monitor.count()") == 9


def test_mobile_layout_has_no_horizontal_overflow(browser: Any, fixture_url: str) -> None:
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    pg = ctx.new_page()
    goto(pg, fixture_url)
    assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    box = pg.locator(f'#list .row[data-ch="{FIRST}"] .c-valor').bounding_box()
    assert box and box["x"] + box["width"] <= 390  # valor visível, não cortado à direita
    ctx.close()



GONE = "99999999000199-1-000001/2026"  # chave válida que não está nos dados de teste


def test_auto_update_closes_drawer_of_removed_purchase_and_keeps_saving(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    open_detail(page, FIRST)
    # dados novos sem a compra aberta (encerrou): o painel fecha sem erro e o cabeçalho atualiza
    page.evaluate("""() => { const j = structuredClone(window.__monitor.data()); j.gerado_em = '2099-01-01T08:00:00-03:00';
      j.compras = j.compras.filter(c => c.chave !== '%s'); window.__monitor.apply(j); }""" % FIRST)
    page.wait_for_function("!document.querySelector('#drawer').classList.contains('show')")
    assert "01/01/2099" in page.locator("#upd").inner_text()
    other = page.evaluate("window.__monitor.data().compras[0].chave")
    d = open_detail(page, other)
    d.locator('[data-w="notas"]').fill("ainda salva")
    d.locator('[data-w="notas"]').blur()
    page.wait_for_timeout(400)
    assert ls(page, WFK)[other]["notas"] == "ainda salva"


def test_update_waits_while_typing_in_drawer(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    d = open_detail(page, FIRST)
    d.locator('[data-w="notas"]').type("abc")
    page.evaluate("""() => { const j = structuredClone(window.__monitor.data()); j.gerado_em = '2099-01-01T08:00:00-03:00';
      window.__monitor.offer(j); }""")
    d.locator('[data-w="notas"]').type("d")
    page.wait_for_timeout(500)
    assert ls(page, WFK)[FIRST]["notas"] == "abcd"
    assert d.locator('[data-w="notas"]').input_value() == "abcd"
    d.locator('[data-w="notas"]').blur()
    page.wait_for_function("document.querySelector('#upd').innerText.includes('2099')", timeout=3000)


def test_escape_right_after_typing_still_saves(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    d = open_detail(page, FIRST)
    d.locator('[data-w="notas"]').type("ligar pregoeiro")
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('#drawer').classList.contains('show')")
    page.wait_for_timeout(450)
    assert ls(page, WFK)[FIRST]["notas"] == "ligar pregoeiro"


def test_star_in_agenda_updates_and_toggles(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    page.click('[data-tab="agenda"]')
    star = page.locator('#agenda .row').first.locator('[data-act="fav"]')
    ch = page.locator('#agenda .row').first.get_attribute("data-ch")
    star.click()
    assert page.locator(f'#agenda .row[data-ch="{ch}"] [data-act="fav"]').inner_text() == "★"
    page.locator(f'#agenda .row[data-ch="{ch}"] [data-act="fav"]').click()
    assert page.locator(f'#agenda .row[data-ch="{ch}"] [data-act="fav"]').inner_text() == "☆"
    assert ch not in (ls(page, WFK) or {})


def test_direct_link_then_close_stays_on_site(page: Page, fixture_url: str) -> None:
    page.goto("about:blank")
    page.goto(fixture_url + "/index.html#c=" + FIRST.replace("/", "%2F"))
    wait_ready(page)
    page.locator("#drawer.show").wait_for()
    page.click('#drawer [data-act="close"]')
    page.wait_for_function("!document.querySelector('#drawer').classList.contains('show')")
    assert page.url.startswith(fixture_url) and "#c=" not in page.url


def test_duplicate_link_then_close_closes_once_and_keeps_filters(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    page.click('[data-q="uf:MG"]')
    filtros = page.evaluate("JSON.stringify(window.__monitor.F())")
    dup_of = page.evaluate("window.__monitor.data().compras.find(c => c.chave === '%s').dup_of" % DUP)
    page.evaluate("k => window.__monitor.open(k)", dup_of)
    page.locator(f'#drawer.show [data-goto="{DUP}"]').click()
    page.wait_for_function("document.querySelector('#drawer h2') && location.hash.includes('000090')")
    page.click('#drawer [data-act="close"]')
    page.wait_for_function("!document.querySelector('#drawer').classList.contains('show')")
    page.wait_for_timeout(300)
    assert not page.evaluate("document.querySelector('#drawer').classList.contains('show')")
    assert page.evaluate("JSON.stringify(window.__monitor.F())") == filtros


def test_followed_purchase_stays_on_board_after_leaving_data(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    d = open_detail(page, FIRST)
    d.locator('[data-w="status"]').select_option("Enviada")
    page.keyboard.press("Escape")
    page.evaluate("""() => { const j = structuredClone(window.__monitor.data()); j.gerado_em = '2099-01-01T08:00:00-03:00';
      j.compras = j.compras.filter(c => c.chave !== '%s'); window.__monitor.apply(j); }""" % FIRST)
    page.click('[data-tab="mine"]')
    card = page.locator(f'#board .mini[data-ch="{FIRST}"]')
    assert "Fora dos dados" in card.inner_text() and "Conceição" in card.inner_text()
    assert page.locator("#n-mine").inner_text() == "1"
    card.click()
    d = page.locator("#drawer.show")
    d.wait_for()
    d.locator('[data-w="status"]').select_option("Ganha")
    assert ls(page, WFK)[FIRST]["status"] == "Ganha"


def test_import_rejects_site_data_file(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    data = page.evaluate("JSON.stringify(window.__monitor.data())")
    err = page.evaluate("t => { try { window.__monitor.importText(t); return ''; } catch (e) { return e.message; } }", data)
    assert err and ls(page, WFK) is None and ls(page, CLK) is None


def test_csv_neutralizes_formulas(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    d = open_detail(page, FIRST)
    d.locator('[data-w="notas"]').fill("=HYPERLINK(\"x\")")
    d.locator('[data-w="notas"]').blur()
    page.wait_for_timeout(400)
    csv = page.evaluate("window.__monitor.csvText().csv")
    assert "\"'=HYPERLINK(\"\"x\"\")\"" in csv
