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
NO_WEIGHT = "77402196000175-1-000046/2026"  # T&M sem peso (o solúvel saiu: só café torrado)
MIXED = "01612911000132-1-000128/2026"  # T&M R$ 46,94/kg (696,5 kg); o solúvel saiu
PARTIAL = "75458836000133-1-000147/2026"  # T&M 400 kg + T&M sem peso
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


def goto(page: Page, url: str, tab: str = "list") -> None:
    """Abre o site (que sempre começa no Dashboard) e vai para a aba pedida."""
    page.goto(url + "/index.html")
    wait_ready(page)
    if tab != "dash":
        page.click(f'[data-tab="{tab}"]')


def test_real_site_loads_without_errors(page: Page, real_url: str) -> None:
    goto(page, real_url)
    assert page.evaluate("window.__monitor.count()") > 0
    for tab in ("mine", "agenda", "check", "about", "list", "dash"):
        page.click(f'[data-tab="{tab}"]')
        assert page.locator(f"#tab-{tab}").is_visible()
    assert page.locator("#list .row").count() > 0
    assert all(k.startswith("monitorLicitacoes.") for k in page.evaluate("Object.keys(localStorage)"))


def test_duplicates_hidden_by_default(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    assert page.evaluate("window.__monitor.count()") == 7  # 8 compras, 1 duplicata oculta
    page.click('label.toggle:has-text("Ocultar possíveis duplicatas")')
    assert page.evaluate("window.__monitor.count()") == 8


def test_search_and_quick_filter(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    page.fill("#q", "conceicao aparecida")
    page.wait_for_function("window.__monitor.count() === 1")
    page.fill("#q", "")
    page.wait_for_function("window.__monitor.count() === 7")
    page.click('[data-q="uf:MG"]')
    mg = page.evaluate("window.__monitor.count()")
    assert 0 < mg < 7


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
    grupos = page.locator("#board .stage-g")
    assert "favoritas sem status" in grupos.nth(0).inner_text().lower() and "Conceição" in grupos.nth(0).inner_text()
    enviada = page.locator('#board .stage-g:has(h3:has-text("Enviada"))')
    assert enviada.locator(f'.prop[data-ch="{MIXED}"]').count() == 1
    page.click('#board [data-stage="Enviada"]')  # etapa escolhida: só ela aparece
    assert page.locator("#board .prop").count() == 1
    enviada.locator("[data-open]").click()
    page.locator("#drawer.show").wait_for()
    sem_rolagem = page.evaluate("document.querySelector('#board').scrollWidth <= document.querySelector('#board').clientWidth")
    assert sem_rolagem


def test_agenda_lists_followed_deadlines(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    page.evaluate("([k, v]) => localStorage.setItem(k, v)", [WFK, json.dumps({FIRST: {"fav": True, "upd": "x"}})])
    page.reload()
    wait_ready(page)
    page.click('[data-tab="agenda"]')
    assert page.locator("#agenda .row").count() == 1
    page.click('[data-ag="1"]')
    assert page.locator("#agenda .row").count() == 7


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




def test_secret_budget_shown_as_secret_not_zero(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    r = row(page, SIGILOSO)
    assert "Sigiloso" in r.locator(".c-valor").inner_text()
    assert "R$ 0" not in r.inner_text()


def test_ui_state_saved(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    page.select_option("#sort", "valor")
    page.click('[data-tab="agenda"]')
    ui = ls(page, UIK)
    assert ui["sort"] == "valor" and ui["tab"] == "agenda"
    page.reload()
    wait_ready(page)
    assert page.locator("#tab-dash").is_visible()  # sempre abre no Dashboard
    page.click('[data-tab="list"]')
    assert page.locator("#sort").input_value() == "valor"


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
    page.click('[data-tab="list"]')
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



def test_only_roasted_coffee_is_shown(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    assert "R$ 46,94" in row(page, MIXED).locator(".c-rkg").inner_text()
    assert "—" in row(page, NO_WEIGHT).locator(".c-rkg").inner_text()
    d = open_detail(page, MIXED)
    assert "solúvel" not in d.inner_text().lower() and "Copiar resumo" not in d.inner_text()
    niveis = page.locator('.fsec[data-sec="niveis"]').inner_text()
    assert "Não se aplica" not in niveis


def test_median_and_sort_use_only_roast_and_ground(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    kpi = page.locator('.kpi[data-k="rkg"]').inner_text()
    # T&M visíveis (sem a duplicata oculta): 66,03; 46,94; 58,42; 63,52.
    assert "R$ 60,97" in kpi and "4 de torrado e moído" in kpi
    page.select_option("#sort", "rkg_desc")
    assert page.locator("#list .row").first.get_attribute("data-ch") != NO_WEIGHT


def test_partial_volume_marked_when_item_has_no_weight(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    assert "≥ 400 kg" in row(page, PARTIAL).locator(".c-valor").inner_text()
    assert "≥" not in row(page, FIRST).locator(".c-valor").inner_text()


def test_margin_uses_type_specific_price(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    d = open_detail(page, MIXED)
    d.locator('[data-w="preco"]').fill("42,25")
    page.wait_for_timeout(450)
    calc = d.locator("[data-calc]").inner_text()
    assert "R$ 46,94/kg (torrado e moído)" in calc and "+10%" in calc
    assert "R$ 29.427" in calc and "697 kg" in calc  # 42,25 × 696,5 kg


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
    assert page.evaluate("window.__monitor.count()") == 8


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
    assert not (ls(page, WFK) or {}).get(ch, {}).get("fav")  # fica só a marca de removido ({upd})


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
    card = page.locator(f'#board .prop[data-ch="{FIRST}"]')
    assert "Fora dos dados" in card.inner_text() and "Conceição" in card.inner_text()
    assert page.locator("#n-mine").inner_text() == "1"
    card.locator("[data-open]").click()
    d = page.locator("#drawer.show")
    d.wait_for()
    d.locator('[data-w="status"]').select_option("Ganha")
    assert ls(page, WFK)[FIRST]["status"] == "Ganha"




PISOK = "monitorLicitacoes.pisos.v1"


def test_opens_on_dashboard_and_kpi_filters_list(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url, tab="dash")
    assert page.locator("#tab-dash").is_visible() and page.locator('[data-tab="dash"]').get_attribute("aria-selected") == "true"
    assert page.locator("#dash .lv-row").count() == 4  # um por nível de exigência
    page.click('.kpi[data-k="urg"]')
    assert page.locator("#tab-list").is_visible() and page.evaluate("window.__monitor.F().urg") is True


def test_level_facet_and_dashboard_row_filter(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url, tab="dash")
    page.click('#dash [data-cf="niveis|Superior"]')
    page.wait_for_function("window.__monitor.count() === 2")  # 080 e 128 pedem Superior
    assert page.locator(f'#list .row[data-ch="{FIRST}"] .lvl').inner_text().strip() == "Superior"


def test_price_floor_marks_purchases_and_goes_to_backup(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url, tab="dash")
    piso = page.locator('[data-piso="Superior"]')
    piso.fill("70,00")
    piso.blur()
    assert ls(page, PISOK) == {"Superior": 70}
    page.click('[data-tab="list"]')
    assert "abaixo do meu piso" in row(page, FIRST).inner_text()  # R$ 66,03 < R$ 70
    page.locator('[data-t="viavel"]').check()
    page.wait_for_function("window.__monitor.count() === 0")


def test_drawer_starts_with_verdict_and_specs(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    d = open_detail(page, FIRST)
    cards = d.locator(".d-body > .card h3").all_inner_texts()
    assert cards[0].lower() == "vale a pena?"
    assert "nível Superior" in d.locator(".verdict").inner_text() and "R$ 66,03/kg" in d.locator(".verdict").inner_text()
    assert "Nível de exigência" in d.locator(".spec-grid").inner_text()
    d.locator('[data-act="pisos"]').click()
    page.wait_for_function("document.activeElement && document.activeElement.dataset.piso === 'Superior'")  # vai para o nível da compra


def test_copied_classification_text_gets_attention_point(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    page.evaluate("""() => { const j = structuredClone(window.__monitor.data()); j.gerado_em = '2099-01-01T08:00:00-03:00';
      const i = j.compras.find(c => c.chave === '%s').itens[0];
      i.espec = 'CAFÉ INSOLUVEL - Café torrado e moído, grupo especial, subgrupo empeliculado, tipo 1'; window.__monitor.apply(j); }""" % FIRST)
    d = open_detail(page, FIRST)
    assert "subgrupo empeliculado" in d.locator(".warn-list").inner_text()


def test_edital_reading_shown_per_item(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    page.evaluate("""() => { const j = structuredClone(window.__monitor.data()); j.gerado_em = '2099-01-01T08:00:00-03:00';
      const c = j.compras.find(c => c.chave === '%s');
      Object.assign(c, {edital_status: 'lido', edital_lido: true, edital_lido_em: '2026-10-18', edital_docs: ['2:TR.docx'],
        marcas: ['3 Corações', 'Pilão'], ed_pz: '5 dias corridos'});
      c.itens[0].ed_trecho = 'cafe torrado e moido, bebida classificada no minimo como superior';
      const s = j.compras.find(c => c.chave === '%s'); Object.assign(s, {edital_status: 'sem documentos no PNCP', edital_lido: false});
      window.__monitor.apply(j); }""" % (FIRST, MIXED))
    d = open_detail(page, FIRST)
    t = d.inner_text()
    assert "Edital lido pelo coletor em 18/10/2026 (TR.docx)" in t and "5 dias corridos" in t
    assert "3 Corações" in t and "No edital/TR, sobre este item:" in t and "como superior" in t
    d.locator('[data-act="close"]').click()
    d = open_detail(page, MIXED)
    assert "ainda não publicou o edital" in d.inner_text() and "ainda não foi lido automaticamente" not in d.inner_text()


def test_floor_inputs_keep_focus_and_reject_garbage(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url, tab="dash")
    page.locator('[data-piso="Tradicional"]').fill("60")
    page.keyboard.press("Tab")
    page.wait_for_timeout(100)
    assert page.evaluate("document.activeElement.dataset.piso") == "Superior"  # o Tab não se perde
    page.locator('[data-piso="Tradicional"]').fill("abc")
    page.locator('[data-piso="Tradicional"]').blur()
    assert ls(page, PISOK) == {"Tradicional": 60}  # texto inválido não apaga o piso
    assert page.locator('[data-piso="Tradicional"]').input_value() == "60,00"


def test_dashboard_click_starts_from_clean_filters(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url, tab="dash")
    page.click('#dash [data-cf="niveis|Superior"]')
    page.click('[data-tab="dash"]')
    page.locator('#dash .maptop [data-cf="ufs|MG"]').click()
    f = page.evaluate("window.__monitor.F()")
    assert f["ufs"] == ["MG"] and f["niveis"] == []


def test_floor_filter_ignored_without_floors(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url, tab="dash")
    piso = page.locator('[data-piso="Superior"]')
    piso.fill("70")
    piso.blur()
    page.click('[data-tab="list"]')
    page.locator('[data-t="viavel"]').check()
    page.click('[data-tab="dash"]')
    page.locator('[data-piso="Superior"]').fill("")
    page.locator('[data-piso="Superior"]').blur()
    page.wait_for_timeout(100)
    assert page.evaluate("window.__monitor.F().viavel") is False
    page.click('[data-tab="list"]')
    assert page.evaluate("window.__monitor.count()") == 7


def test_mobile_drawers_fit_screen(browser: Any, fixture_url: str) -> None:
    page = browser.new_page(viewport={"width": 390, "height": 844})
    goto(page, fixture_url, tab="dash")
    ruins = page.evaluate("""() => window.__monitor.data().compras.map(c => c.chave).filter(k => { window.__monitor.open(k);
      const d = document.querySelector('.d-body'), v = document.querySelector('.verdict');
      return d.scrollWidth > d.clientWidth + 1 || !v || v.getBoundingClientRect().height < 60; })""")
    assert ruins == []
    page.close()


# ---------------- gravação automática no GitHub (API simulada; nada sai para a internet)
import base64  # noqa: E402

SYNCK = "monitorLicitacoes.github.v1"


class FakeGitHub:
    """Repositório falso: guarda dados/meus-dados.json e responde como a API de conteúdos do GitHub."""

    def __init__(self, conflitos: int = 0) -> None:
        self.doc: dict[str, Any] | None = None
        self.sha = 0
        self.puts = 0
        self.conflitos = conflitos  # quantos PUTs responder 409 (alguém gravou no meio)
        self.branch = False  # a branch "dados" só existe depois que o site a cria

    def handler(self, route: Any) -> None:
        req = route.request
        auth = req.headers.get("authorization", "")
        if "/branches/dados" in req.url:
            route.fulfill(status=200 if self.branch else 404, json={"name": "dados"} if self.branch else {"message": "Branch not found"})
            return
        if "/git/ref/heads/main" in req.url:
            route.fulfill(status=200, json={"object": {"sha": "abc"}})
            return
        if req.url.endswith("/git/refs"):
            assert json.loads(req.post_data or "{}")["ref"] == "refs/heads/dados"
            self.branch = True
            route.fulfill(status=201, json={"ref": "refs/heads/dados"})
            return
        if "/contents/" not in req.url:  # GET /repos/dono/repo (teste da chave)
            ok = auth == "Bearer boa"
            route.fulfill(status=200 if ok else 401, json={"permissions": {"push": True}} if ok else {"message": "Bad credentials"})
            return
        if req.method == "GET":
            if self.doc is None:
                route.fulfill(status=404, json={"message": "Not Found"})
            else:
                raw = base64.b64encode(json.dumps(self.doc).encode()).decode()
                route.fulfill(status=200, json={"content": raw, "sha": str(self.sha)})
            return
        body = json.loads(req.post_data or "{}")
        if auth != "Bearer boa":
            route.fulfill(status=401, json={"message": "Bad credentials"})
        elif self.conflitos or (self.doc is not None and body.get("sha") != str(self.sha)):
            self.conflitos = max(0, self.conflitos - 1)
            route.fulfill(status=409, json={"message": "conflict"})
        elif body.get("branch") != "dados" or not self.branch:
            route.fulfill(status=404, json={"message": "Branch not found"})
        else:
            self.doc = json.loads(base64.b64decode(body["content"]).decode())
            self.sha += 1
            self.puts += 1
            route.fulfill(status=200, json={"content": {"sha": str(self.sha)}})


def aparelho(browser: Any, url: str, gh: FakeGitHub, token: str | None = "boa") -> Page:
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.route("https://api.github.com/**", gh.handler)
    page = ctx.new_page()
    if token:
        page.add_init_script(f"localStorage.setItem('{SYNCK}', JSON.stringify({{token: '{token}'}}))")
    page.goto(url + "/index.html?repo=dono/repo")
    wait_ready(page)
    page.click('[data-tab="list"]')
    return page


def espera_salvo(page: Page) -> None:
    page.wait_for_function("window.__monitor.syncState().estado === 'ok' && !window.__monitor.syncState().pendente", timeout=8000)


def test_sync_saves_to_github_and_second_device_sees_it(browser: Any, fixture_url: str) -> None:
    gh = FakeGitHub()
    a = aparelho(browser, fixture_url, gh)
    row(a, FIRST).locator('[data-act="fav"]').click()
    espera_salvo(a)
    assert gh.doc and gh.doc["meus_dados"][FIRST]["fav"] is True and gh.branch  # criou a branch "dados"
    assert "Salvo no GitHub" in a.locator("#syncLbl").inner_text()
    b = aparelho(browser, fixture_url, gh)  # outro aparelho, navegador vazio
    b.wait_for_function(f"document.querySelector('#list .row[data-ch=\"{FIRST}\"] .star.on')")
    b.click('[data-tab="mine"]')
    assert b.locator(f'[data-ch="{FIRST}"]').count() >= 1


def test_sync_unfavorite_is_not_resurrected_by_other_device(browser: Any, fixture_url: str) -> None:
    gh = FakeGitHub()
    a = aparelho(browser, fixture_url, gh)
    row(a, FIRST).locator('[data-act="fav"]').click()
    espera_salvo(a)
    b = aparelho(browser, fixture_url, gh)
    b.wait_for_function(f"document.querySelector('#list .row[data-ch=\"{FIRST}\"] .star.on')")
    row(a, FIRST).locator('[data-act="fav"]').click()  # desfavorita no aparelho A
    espera_salvo(a)
    assert gh.doc["meus_dados"][FIRST].get("fav") is None  # fica só a marca de removido
    b.evaluate("window.__monitor.sync()")  # B ainda tinha o favorito antigo guardado
    b.wait_for_function(f"!document.querySelector('#list .row[data-ch=\"{FIRST}\"] .star.on')")
    espera_salvo(b)
    assert gh.doc["meus_dados"][FIRST].get("fav") is None


def test_sync_merges_when_someone_saved_in_between(browser: Any, fixture_url: str) -> None:
    gh = FakeGitHub(conflitos=1)
    a = aparelho(browser, fixture_url, gh)
    row(a, FIRST).locator('[data-act="fav"]').click()
    espera_salvo(a)
    assert gh.doc["meus_dados"][FIRST]["fav"] is True and gh.conflitos == 0  # o 409 aconteceu e foi resolvido


def test_sync_rejected_key_keeps_data_local(browser: Any, fixture_url: str) -> None:
    gh = FakeGitHub()
    a = aparelho(browser, fixture_url, gh, token="velha")
    row(a, FIRST).locator('[data-act="fav"]').click()
    a.wait_for_function("window.__monitor.syncState().estado === 'erro'", timeout=8000)
    assert gh.doc is None and ls(a, WFK)[FIRST]["fav"] is True
    assert "recusada" in a.evaluate("window.__monitor.syncState().erro")


def test_sync_connect_with_key_from_header(browser: Any, fixture_url: str) -> None:
    gh = FakeGitHub()
    a = aparelho(browser, fixture_url, gh, token=None)
    row(a, FIRST).locator('[data-act="fav"]').click()
    assert "Só neste aparelho" in a.locator("#syncLbl").inner_text() and gh.doc is None
    a.click("#syncBtn")
    a.fill("#syncTok", "boa")
    a.click("#syncSave")
    espera_salvo(a)
    assert gh.doc["meus_dados"][FIRST]["fav"] is True and ls(a, SYNCK) == {"token": "boa"}


def test_unfavorite_purchase_that_left_the_data(page: Page, fixture_url: str) -> None:
    """Bug relatado: favorita que saiu dos dados ficava fixa em Minhas propostas (não havia ★ para tirar)."""
    goto(page, fixture_url)
    row(page, FIRST).locator('[data-act="fav"]').click()
    page.evaluate("""() => { const j = structuredClone(window.__monitor.data()); j.gerado_em = '2099-01-01T08:00:00-03:00';
      j.compras = j.compras.filter(c => c.chave !== '%s'); window.__monitor.apply(j); }""" % FIRST)
    page.click('[data-tab="mine"]')
    page.locator(f'#board .prop[data-ch="{FIRST}"] [data-act="fav"]').click()
    assert page.locator(f'#board .prop[data-ch="{FIRST}"]').count() == 0 and page.locator("#n-mine").inner_text() == "0"
    assert not ls(page, WFK)[FIRST].get("fav")


def test_status_on_card_and_stop_following(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    row(page, FIRST).locator('[data-act="fav"]').click()
    d = open_detail(page, FIRST)
    d.locator('[data-w="notas"]').fill("ligar")
    page.keyboard.press("Escape")
    page.click('[data-tab="mine"]')
    page.locator(f'#board .prop[data-ch="{FIRST}"] select').select_option("Em preparação")
    assert ls(page, WFK)[FIRST]["status"] == "Em preparação"
    assert page.locator('#board .stage-g:has(h3:has-text("Em preparação")) .prop').count() == 1
    page.locator(f'#board .prop[data-ch="{FIRST}"] [data-act="unfollow"]').click()
    w = ls(page, WFK)[FIRST]
    assert not w.get("fav") and not w.get("status") and w["notas"] == "ligar"  # notas ficam
    assert page.locator("#board .prop").count() == 0 and page.locator("#n-mine").inner_text() == "0"
