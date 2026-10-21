"""Testes do site (React, site/dist) no navegador (Chromium headless), com dados de teste locais."""
from __future__ import annotations

import base64
import json
from typing import Any

from playwright.sync_api import Locator, Page

from tests.conftest import ROOT, wait_ready

WFK = "monitorLicitacoes.meusDados.v1"
UIK = "monitorLicitacoes.ui.v1"
CLK = "monitorLicitacoes.checklist.v1"
PISOK = "monitorLicitacoes.pisos.v1"
CUSTOSK = "monitorLicitacoes.custos.v1"
SYNCK = "monitorLicitacoes.github.v1"
FIRST = "18243295000192-1-000080/2026"  # torrado e moído 500 g, R$ 66,03/kg
NO_WEIGHT = "77402196000175-1-000046/2026"  # T&M sem peso
MIXED = "01612911000132-1-000128/2026"  # T&M R$ 46,94/kg (696,5 kg)
PARTIAL = "75458836000133-1-000147/2026"  # T&M 400 kg + T&M sem peso
SIGILOSO = "95440517000108-1-000295/2026"
DUP = "01612382000177-1-000090/2026"  # dup_of no conjunto de teste
GONE = "99999999000199-1-000001/2026"  # chave válida que não está nos dados de teste


def ls(page: Page, key: str) -> Any:
    raw = page.evaluate("k => localStorage.getItem(k)", key)
    return None if raw is None else json.loads(raw)


def row(page: Page, chave: str) -> Locator:
    return page.locator(f'.list .row[data-ch="{chave}"]')


def detail(page: Page) -> Locator:
    return page.locator(".detalhe")


def open_detail(page: Page, chave: str) -> Locator:
    row(page, chave).locator(".c-loc").click()
    d = page.locator(f'.detalhe[data-ch="{chave}"]')
    d.wait_for()
    return d


def goto(page: Page, url: str, tab: str = "oportunidades") -> None:
    """Abre o site na aba pedida (sem aba na URL, o site sempre começa em Hoje)."""
    page.goto(url + "/index.html#/" + tab)
    wait_ready(page)
    page.wait_for_selector(f".page.{ 'opp' if tab == 'oportunidades' else tab }")


def go_tab(page: Page, tab: str) -> None:
    page.evaluate(f"location.hash = '#/{tab}'")
    page.wait_for_selector(f".page.{ 'opp' if tab == 'oportunidades' else tab }")


def glide(page: Page, testid: str, opcao: str) -> None:
    """Escolhe uma opção no menu de status (GlideSelect)."""
    page.locator(f'[data-testid="{testid}"]').click()
    page.locator(f'.glide-menu [role="option"]:has-text("{opcao}")').first.click()


def hold(loc: Locator, page: Page) -> None:
    """Segura o botão de confirmação (HoldButton) até ele disparar."""
    loc.dispatch_event("pointerdown")
    page.wait_for_timeout(1100)  # o botão confirma aos 700 ms; folga para máquina carregada
    if loc.count():  # depois de confirmar, o botão pode ter saído da tela
        loc.dispatch_event("pointerup")


def abrir_filtros(page: Page) -> None:
    if not page.locator(".filters.show").count():
        page.click('[data-testid="btn-filtros"]')
        page.wait_for_selector(".filters.show")


# ---------------- carga e navegação
def test_real_site_loads_without_errors(page: Page, real_url: str) -> None:
    goto(page, real_url, "hoje")
    assert page.evaluate("window.__monitor.count()") > 0
    for tab in ("oportunidades", "propostas", "mercado", "guia", "ajustes", "hoje"):
        go_tab(page, tab)
    go_tab(page, "oportunidades")
    assert page.locator(".list .row").count() > 0
    assert all(k.startswith("monitorLicitacoes.") for k in page.evaluate("Object.keys(localStorage)"))


def test_opens_on_today_and_kpi_filters_list(page: Page, fixture_url: str) -> None:
    page.goto(fixture_url + "/index.html")
    wait_ready(page)
    assert page.locator(".page.hoje").is_visible() and page.locator('.tab[data-tab="hoje"]').get_attribute("aria-selected") == "true"
    assert page.locator(".faixa-row").count() == 4  # um por nível de exigência
    page.click('.kpi[data-k="urg"]')  # "Fecham em 7 dias": lista por prazo, sem o filtro de 3 dias (o cartão diz 7)
    page.wait_for_selector(".page.opp")
    assert page.evaluate("window.__monitor.F().urg") is False
    assert page.evaluate("window.__monitor.state().ui.sort") == "prazo"


def test_malformed_link_still_loads_the_site(page: Page, fixture_url: str) -> None:
    """Link colado pela metade ("%E0%A4%A") não pode travar a página no "Carregando"."""
    page.goto(fixture_url + "/index.html#c=%E0%A4%A")
    wait_ready(page)
    page.wait_for_selector(".page.opp")
    assert page.evaluate("window.__monitor.count()") > 0


def test_link_to_gone_purchase_explains_and_cleans_hash(page: Page, fixture_url: str) -> None:
    """Link do Telegram para uma licitação que já saiu dos dados: aviso e hash limpo (nada de #c= morto)."""
    page.goto(fixture_url + "/index.html#c=" + GONE.replace("/", "%2F"))
    wait_ready(page)
    page.wait_for_selector(".page.opp")
    page.wait_for_selector('.toast:has-text("não está mais no monitor")')
    assert page.evaluate("location.hash") == "#/oportunidades" and detail(page).count() == 0


def test_shortcut_g_g_opens_guide(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url, "hoje")
    page.keyboard.press("g")
    page.keyboard.press("g")
    page.wait_for_selector(".page.guia")
    page.keyboard.press("g")
    page.keyboard.press("o")
    page.wait_for_selector(".page.opp")
    page.keyboard.press("t")  # "t" sozinho continua trocando o tema
    assert page.evaluate("document.documentElement.dataset.theme") == "light"


def test_data_load_failure_shows_retry_instead_of_blank_page(browser: Any, fixture_url: str) -> None:
    pg = nova_pagina(browser)
    quebrado = {"on": True}
    pg.route("**/data.json*", lambda r: r.fulfill(status=500, body="erro") if quebrado["on"] else r.continue_())
    pg.goto(fixture_url + "/index.html#/hoje")
    pg.wait_for_selector('.note.alert:has-text("Sem dados")')
    assert pg.locator("#root").inner_html() != "" and pg.locator(".page.hoje").count() == 0
    quebrado["on"] = False
    pg.click('.note.alert button:has-text("Tentar de novo")')
    wait_ready(pg)
    pg.wait_for_selector(".page.hoje")
    fechar(pg)


def test_refresh_keeps_cursor_and_list_position(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    page.keyboard.press("j")
    page.keyboard.press("j")
    assert page.locator(".row.foco").get_attribute("data-ch") == page.evaluate("window.__monitor.lista()[1]")
    page.evaluate("""() => { const j = structuredClone(window.__monitor.data()); j.gerado_em = '2099-01-01T08:00:00-03:00'; window.__monitor.apply(j); }""")
    page.wait_for_function("document.querySelector('#upd b').textContent.includes('01/01/2099')")
    assert page.locator(".row.foco").get_attribute("data-ch") == page.evaluate("window.__monitor.lista()[1]")  # a atualização não zera o cursor


def test_newer_publicado_em_replaces_data_even_with_same_gerado_em(page: Page, fixture_url: str) -> None:
    """Preços de mercado regravam o data.json com o mesmo gerado_em: a página aberta tem de perceber pelo publicado_em."""
    goto(page, fixture_url)
    base = page.evaluate("window.__monitor.data()")
    n = page.evaluate("window.__monitor.count()")
    novo = {**base, "publicado_em": "2099-01-01T09:00:00-03:00", "compras": [c for c in base["compras"] if c["chave"] != FIRST]}
    page.route("**/data.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(novo)))
    assert page.evaluate("window.__monitor.buscar()") is True
    assert page.evaluate("window.__monitor.count()") == n - 1
    row(page, FIRST).wait_for(state="detached")  # a linha some depois da animação de saída
    assert page.evaluate("window.__monitor.buscar()") is False  # a mesma versão de novo não troca nada


def test_cost_inputs_reject_100_percent_and_read_thousands(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url, "ajustes")
    perda = page.locator('[data-testid="custo-perda_torra"]')
    perda.fill("100")
    perda.press("Enter")
    page.wait_for_selector('.toast:has-text("menor que 100")')
    assert "perda_torra" not in (ls(page, CUSTOSK) or {})  # 100% de perda dividiria por zero
    grao = page.locator('[data-testid="custo-grao-2"]')  # Superior, R$/saca; o site mostra "1.572" como sugestão
    grao.fill("1.800")
    grao.press("Enter")
    page.wait_for_function("JSON.parse(localStorage.getItem('monitorLicitacoes.custos.v1') || '{}')['grao|Superior'] === 1800")
    assert grao.input_value() == "1.800"


def test_duplicates_hidden_by_default(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    assert page.evaluate("window.__monitor.count()") == 7  # 8 compras, 1 duplicata oculta
    abrir_filtros(page)
    page.locator('[data-t="hideDup"]').uncheck()
    page.wait_for_function("window.__monitor.count() === 8")


def test_search_and_quick_filter(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    page.fill("#q", "conceicao aparecida")
    page.wait_for_function("window.__monitor.count() === 1")
    page.fill("#q", "")
    page.wait_for_function("window.__monitor.count() === 7")
    page.click('[data-q="uf:MG"]')
    mg = page.evaluate("window.__monitor.count()")
    assert 0 < mg < 7


def test_detail_opens_closes_and_back_button(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    d = open_detail(page, FIRST)
    assert "Conceição da Aparecida" in d.inner_text()
    assert page.url.endswith("#c=" + FIRST.replace("/", "%2F"))
    page.go_back()
    page.wait_for_function("!document.querySelector('.detalhe')")
    open_detail(page, FIRST)
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('.detalhe')")


def test_personal_data_persists_after_reload(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    row(page, FIRST).locator('[data-act="fav"]').click()
    d = open_detail(page, FIRST)
    d.locator('[data-w="preco"]').fill("55,50")
    glide(page, "status", "Enviada")
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
    go_tab(page, "propostas")
    grupos = page.locator("#board .stage-g")
    assert "favoritas sem status" in grupos.nth(0).inner_text().lower() and "Conceição" in grupos.nth(0).inner_text()
    enviada = page.locator('#board .stage-g:has(h3:has-text("Enviada"))')
    assert enviada.locator(f'.prop[data-ch="{MIXED}"]').count() == 1
    page.click('[data-stage="Enviada"]')  # etapa escolhida: só ela aparece
    assert page.locator("#board .prop").count() == 1
    enviada.locator("[data-open]").click()
    page.locator(".detalhe").wait_for()
    assert page.evaluate("document.querySelector('#board').scrollWidth <= document.querySelector('#board').clientWidth")


def test_agenda_lists_followed_deadlines(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    page.evaluate("([k, v]) => localStorage.setItem(k, v)", [WFK, json.dumps({FIRST: {"fav": True, "upd": "x"}})])
    page.reload()
    wait_ready(page)
    go_tab(page, "propostas")
    assert page.locator("#agenda .mini").count() == 1
    page.locator('#agenda .seg button:has-text("Todas")').click()
    while page.locator('#agenda .more button').count():
        page.locator("#agenda .more button").click()
    assert page.locator("#agenda .mini").count() == 7


def test_price_input_parsing(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    d = open_detail(page, FIRST)
    for typed, expected in (("55,5", 55.5), ("1.234,56", 1234.56), ("R$ 60", 60.0), ("1.800", 1800.0), ("1.8", 1.8)):
        d.locator('[data-w="preco"]').fill(typed)
        page.wait_for_function("([k, v]) => JSON.parse(localStorage.getItem(k) || '{}')[%s]?.preco === v" % json.dumps(FIRST), arg=[WFK, expected], timeout=5000)


def test_margin_against_estimate(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    d = open_detail(page, FIRST)
    d.locator('[data-w="preco"]').fill("59,43")
    page.wait_for_timeout(700)
    calc = d.locator("[data-calc]").inner_text()
    assert "+10%" in calc  # (66,03 - 59,43) / 66,03
    assert "R$ 359.076" in calc and "6.042 kg" in calc  # 59,43 × 6.042 kg


def test_checklist_persists_and_shows_progress(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url, "guia")
    page.locator('label:has([data-testid="cl-0"])').click()
    page.wait_for_function(f"localStorage.getItem('{CLK}') === '{{\"0\":1}}'")
    assert "1 de " in page.locator("#gside").inner_text()


def test_secret_budget_shown_as_secret_not_zero(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    r = row(page, SIGILOSO)
    assert "Sigiloso" in r.locator(".c-valor").inner_text()
    assert "R$ 0" not in r.inner_text()


def test_ui_state_saved(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    page.select_option("#sort", "valor")
    go_tab(page, "propostas")
    ui = ls(page, UIK)
    assert ui["sort"] == "valor" and ui["tab"] == "propostas"
    page.goto(fixture_url + "/index.html")
    wait_ready(page)
    assert page.locator(".page.hoje").is_visible()  # sempre abre em Hoje
    go_tab(page, "oportunidades")
    assert page.locator("#sort").input_value() == "valor"


def test_theme_toggle_saved(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"  # escuro por padrão
    page.click("#themeBtn")
    assert ls(page, UIK)["theme"] == "light"
    assert page.evaluate("document.documentElement.dataset.theme") == "light"


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
    alert = page.locator('[data-testid="bad-data"]')
    assert "ilegíveis" in alert.inner_text()
    alert.locator("button").click()
    assert alert.count() == 0


def test_only_roasted_coffee_is_shown(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    assert "R$ 46,94" in row(page, MIXED).locator(".c-rkg").inner_text()
    assert "sem preço" in row(page, NO_WEIGHT).locator(".c-rkg").inner_text()  # sem R$/kg: um aviso só, não três travessões
    d = open_detail(page, MIXED)
    assert "solúvel" not in d.inner_text().lower() and "Copiar resumo" not in d.inner_text()
    abrir_filtros(page)
    assert "Não se aplica" not in page.locator('.fsec[data-sec="niveis"]').inner_text()


def test_sort_uses_only_roast_and_ground(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    page.select_option("#sort", "rkg_desc")
    assert page.locator(".list .row").first.get_attribute("data-ch") != NO_WEIGHT
    assert page.evaluate("window.__monitor.lista()[0]") == page.locator(".list .row").first.get_attribute("data-ch")


def test_partial_volume_marked_when_item_has_no_weight(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    assert "≥ 400 kg" in row(page, PARTIAL).locator(".c-valor").inner_text()
    assert "≥" not in row(page, FIRST).locator(".c-valor").inner_text()


def test_margin_uses_type_specific_price(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    d = open_detail(page, MIXED)
    d.locator('[data-w="preco"]').fill("42,25")
    page.wait_for_timeout(700)
    calc = d.locator("[data-calc]").inner_text()
    assert "R$ 46,94/kg (torrado e moído)" in calc and "+10%" in calc
    assert "R$ 29.427" in calc and "697 kg" in calc  # 42,25 × 696,5 kg


def test_single_type_price_matches_generator(page: Page, real_url: str) -> None:
    """Onde há um só tipo com R$/kg, o valor recalculado na página bate com o do coletor."""
    goto(page, real_url, "hoje")
    assert page.evaluate("window.__monitor.rkCheck()") == []


def test_duplicate_with_my_data_is_never_hidden(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    assert row(page, DUP).count() == 0
    page.evaluate("([k, v]) => localStorage.setItem(k, v)", [WFK, json.dumps({DUP: {"fav": True, "upd": "2026-10-17T12:00:00Z"}})])
    page.reload()
    wait_ready(page)
    assert row(page, DUP).count() == 1
    assert page.evaluate("window.__monitor.count()") == 8


def nova_pagina(browser: Any, largura: int = 1280, altura: int = 900) -> Page:
    """Página num contexto próprio (localStorage limpo) que guarda os erros de JavaScript em page.erros."""
    ctx = browser.new_context(viewport={"width": largura, "height": altura})
    pg = ctx.new_page()
    erros: list[str] = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    # Respostas HTTP de erro que o próprio teste provoca (GitHub falso com 404/401/409, data.json com 500) aparecem
    # no console como "Failed to load resource": não são erro de JavaScript.
    pg.on("console", lambda m: erros.append(m.text) if m.type == "error" and "ilegíveis" not in m.text and not m.text.startswith("Failed to load resource") else None)
    pg.erros = erros  # type: ignore[attr-defined]
    return pg


def fechar(pg: Page, esperado: str | None = None) -> None:
    """Fecha o contexto e falha se houve erro de JavaScript (exceto os que contêm `esperado`, quando o teste provoca um)."""
    erros = [e for e in pg.erros if not (esperado and esperado in e)]  # type: ignore[attr-defined]
    pg.context.close()
    assert not erros, f"erros de JavaScript na página: {erros}"


def test_mobile_layout_has_no_horizontal_overflow(browser: Any, fixture_url: str) -> None:
    pg = nova_pagina(browser, 390, 844)
    goto(pg, fixture_url)
    assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    box = pg.locator(f'.list .row[data-ch="{FIRST}"] .c-valor').bounding_box()
    assert box and box["x"] + box["width"] <= 390  # valor visível, não cortado à direita
    assert pg.locator(".bottom-nav").is_visible()
    fechar(pg)


def test_mobile_detail_fits_screen(browser: Any, fixture_url: str) -> None:
    pg = nova_pagina(browser, 390, 844)
    goto(pg, fixture_url)
    ruins = pg.evaluate("""async () => { const out = []; for (const k of window.__monitor.data().compras.map(c => c.chave)) { window.__monitor.open(k);
      await new Promise(r => setTimeout(r, 80));  // o React desenha depois do clique
      const d = document.querySelector('.drawer-wrap .d-body'), v = document.querySelector('.verdict');
      if (!d || d.scrollWidth > d.clientWidth + 1 || !v || v.getBoundingClientRect().height < 40) out.push([k, !!d, d && d.scrollWidth, d && d.clientWidth, v && v.getBoundingClientRect().height]); } return out; }""")
    assert ruins == []
    fechar(pg)


# ---------------- atualização automática dos dados
def test_auto_update_closes_detail_of_removed_purchase_and_keeps_saving(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    open_detail(page, FIRST)
    page.evaluate("""() => { const j = structuredClone(window.__monitor.data()); j.gerado_em = '2099-01-01T08:00:00-03:00';
      j.compras = j.compras.filter(c => c.chave !== '%s'); window.__monitor.apply(j); }""" % FIRST)
    page.wait_for_function("!document.querySelector('.detalhe')")
    assert "01/01/2099" in page.locator("#upd").inner_text()
    other = page.evaluate("window.__monitor.data().compras[0].chave")
    d = open_detail(page, other)
    d.locator('[data-w="notas"]').fill("ainda salva")
    d.locator('[data-w="notas"]').blur()
    page.wait_for_timeout(400)
    assert ls(page, WFK)[other]["notas"] == "ainda salva"


def test_update_keeps_what_is_being_typed(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    d = open_detail(page, FIRST)
    d.locator('[data-w="notas"]').type("abc")
    page.evaluate("""() => { const j = structuredClone(window.__monitor.data()); j.gerado_em = '2099-01-01T08:00:00-03:00';
      window.__monitor.offer(j); }""")
    d.locator('[data-w="notas"]').type("d")
    page.wait_for_timeout(500)
    assert ls(page, WFK)[FIRST]["notas"] == "abcd"
    assert d.locator('[data-w="notas"]').input_value() == "abcd"
    assert "2099" in page.locator("#upd").inner_text()


def test_escape_right_after_typing_still_saves(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    d = open_detail(page, FIRST)
    d.locator('[data-w="notas"]').type("ligar pregoeiro")
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('.detalhe')")
    page.wait_for_timeout(450)
    assert ls(page, WFK)[FIRST]["notas"] == "ligar pregoeiro"


def test_direct_link_then_close_stays_on_site(page: Page, fixture_url: str) -> None:
    page.goto("about:blank")
    page.goto(fixture_url + "/index.html#c=" + FIRST.replace("/", "%2F"))
    wait_ready(page)
    page.locator(".detalhe").wait_for()
    page.click('.detalhe [data-act="close"]')
    page.wait_for_function("!document.querySelector('.detalhe')")
    assert page.url.startswith(fixture_url) and "#c=" not in page.url


def test_duplicate_link_then_close_closes_once_and_keeps_filters(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    page.click('[data-q="uf:MG"]')
    filtros = page.evaluate("JSON.stringify(window.__monitor.F())")
    dup_of = page.evaluate("window.__monitor.data().compras.find(c => c.chave === '%s').dup_of" % DUP)
    page.evaluate("k => window.__monitor.open(k)", dup_of)
    page.locator(f'.detalhe [data-goto="{DUP}"]').click()
    page.wait_for_function("location.hash.includes('000090')")
    page.click('.detalhe [data-act="close"]')
    page.wait_for_function("!document.querySelector('.detalhe')")
    page.wait_for_timeout(300)
    assert not page.evaluate("!!document.querySelector('.detalhe')")
    assert page.evaluate("JSON.stringify(window.__monitor.F())") == filtros


def test_followed_purchase_stays_on_board_after_leaving_data(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    open_detail(page, FIRST)
    glide(page, "status", "Enviada")
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('.detalhe')")
    page.evaluate("""() => { const j = structuredClone(window.__monitor.data()); j.gerado_em = '2099-01-01T08:00:00-03:00';
      j.compras = j.compras.filter(c => c.chave !== '%s'); window.__monitor.apply(j); }""" % FIRST)
    go_tab(page, "propostas")
    card = page.locator(f'#board .prop[data-ch="{FIRST}"]')
    assert "Fora dos dados" in card.inner_text() and "Conceição" in card.inner_text()
    assert page.locator("#n-mine").inner_text() == "1"
    card.locator("[data-open]").click()
    page.locator(".detalhe").wait_for()
    glide(page, "status", "Ganha")
    assert ls(page, WFK)[FIRST]["status"] == "Ganha"


# ---------------- Hoje, pisos e custos
def test_level_row_in_today_filters_list(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url, "hoje")
    page.locator('.faixa-n:has-text("Superior")').click()
    page.wait_for_function("window.__monitor.count() === 2")  # 080 e 128 pedem Superior
    assert page.locator(f'.list .row[data-ch="{FIRST}"] .lvl').inner_text().strip() == "Superior"


def test_price_floor_marks_purchases_and_filters(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url, "ajustes")
    piso = page.locator('[data-piso="Superior"]')
    piso.fill("70,00")
    piso.blur()
    page.wait_for_function(f"JSON.stringify(JSON.parse(localStorage.getItem('{PISOK}'))) === '{{\"Superior\":70}}'")
    go_tab(page, "oportunidades")
    assert "abaixo do meu piso" in row(page, FIRST).inner_text()  # R$ 66,03 < R$ 70
    abrir_filtros(page)
    page.locator('[data-t="viavel"]').check()
    page.wait_for_function("window.__monitor.count() === 0")


def test_detail_starts_with_verdict_and_specs(page: Page, fixture_url: str) -> None:
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
    assert "ainda não publicou o edital" in d.inner_text() and "ainda não foi lido" not in d.inner_text()


def test_reference_brands_show_retail_price(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    page.evaluate("""() => { const j = structuredClone(window.__monitor.data()); j.gerado_em = '2099-01-01T08:00:00-03:00';
      j.marcas_ref = {pesquisa_em: '2026-10-18', marcas: {'Pilão': {linhas: [], basica: {linha: 'Tradicional', cat: 'Tradicional', min: 39.78, max: 91.96}}}};
      j.compras.find(c => c.chave === '%s').marcas = ['Pilão', 'Toko']; window.__monitor.apply(j); }""" % FIRST)
    d = open_detail(page, FIRST)
    t = d.inner_text()
    assert "Pilão · Tradicional (Tradicional): R$ 39,78 a R$ 91,96/kg" in t and "Toko" in t and "18/10/2026" in t
    assert "R$ 39,78 a R$ 91,96/kg no varejo" in d.locator(".verdict").inner_text()
    go_tab(page, "hoje")
    card = page.locator('section[aria-label="Marcas citadas"]')
    assert "Pilão" in card.inner_text() and "no varejo" in card.inner_text()
    card.locator('button.hb-row:has-text("Pilão")').click()
    page.wait_for_function("window.__monitor.count() === 1")


def test_floor_inputs_keep_focus_and_reject_garbage(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url, "ajustes")
    page.locator('[data-piso="Tradicional"]').fill("60")
    page.keyboard.press("Tab")
    page.wait_for_timeout(100)
    assert page.evaluate("document.activeElement.dataset.piso") == "Superior"  # o Tab não se perde
    page.locator('[data-piso="Tradicional"]').fill("abc")
    page.locator('[data-piso="Tradicional"]').blur()
    page.wait_for_timeout(100)
    assert ls(page, PISOK) == {"Tradicional": 60}  # texto inválido não apaga o piso
    assert page.locator('[data-piso="Tradicional"]').input_value() == "60,00"


def test_today_click_starts_from_clean_filters(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url, "hoje")
    page.locator('.faixa-n:has-text("Superior")').click()
    page.wait_for_selector(".page.opp")
    go_tab(page, "hoje")
    page.locator('section[aria-label="Onde estão"] .chip:has-text("MG")').click()
    page.locator('section[aria-label="Onde estão"] button:has-text("Ver MG")').click()
    page.wait_for_selector(".page.opp")
    f = page.evaluate("window.__monitor.F()")
    assert f["ufs"] == ["MG"] and f["niveis"] == []


def test_floor_filter_ignored_without_floors(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url, "ajustes")
    piso = page.locator('[data-piso="Superior"]')
    piso.fill("70")
    piso.blur()
    page.wait_for_timeout(100)
    go_tab(page, "oportunidades")
    abrir_filtros(page)
    page.locator('[data-t="viavel"]').check()
    go_tab(page, "ajustes")
    page.locator('[data-piso="Superior"]').fill("")
    page.locator('[data-piso="Superior"]').blur()
    page.wait_for_timeout(100)
    assert page.evaluate("window.__monitor.F().viavel") is False
    go_tab(page, "oportunidades")
    assert page.evaluate("window.__monitor.count()") == 7


def test_unfavorite_purchase_that_left_the_data(page: Page, fixture_url: str) -> None:
    """Favorita que saiu dos dados tem de poder ser desmarcada em Minhas propostas."""
    goto(page, fixture_url)
    row(page, FIRST).locator('[data-act="fav"]').click()
    page.evaluate("""() => { const j = structuredClone(window.__monitor.data()); j.gerado_em = '2099-01-01T08:00:00-03:00';
      j.compras = j.compras.filter(c => c.chave !== '%s'); window.__monitor.apply(j); }""" % FIRST)
    go_tab(page, "propostas")
    page.locator(f'#board .prop[data-ch="{FIRST}"] [data-act="fav"]').click()
    assert page.locator(f'#board .prop[data-ch="{FIRST}"]').count() == 0 and page.locator("#n-mine").inner_text() == "0"
    assert not ls(page, WFK)[FIRST].get("fav")


def test_status_on_card_and_stop_following(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    row(page, FIRST).locator('[data-act="fav"]').click()
    d = open_detail(page, FIRST)
    d.locator('[data-w="notas"]').fill("ligar")
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('.detalhe')")
    go_tab(page, "propostas")
    glide(page, "st-" + FIRST, "Em preparação")
    assert ls(page, WFK)[FIRST]["status"] == "Em preparação"
    assert page.locator('#board .stage-g:has(h3:has-text("Em preparação")) .prop').count() == 1
    hold(page.locator(f'[data-testid="unfollow-{FIRST}"]'), page)
    w = ls(page, WFK)[FIRST]
    assert not w.get("fav") and not w.get("status") and w["notas"] == "ligar"  # notas ficam
    assert page.locator("#board .prop").count() == 0 and page.locator("#n-mine").inner_text() == "0"


# ---------------- gravação automática no GitHub (API simulada; nada sai para a internet)
class FakeGitHub:
    """Repositório falso: guarda dados/meus-dados.json e responde como a API de conteúdos do GitHub."""

    def __init__(self, conflitos: int = 0, limite_anonimo: bool = False) -> None:
        self.doc: dict[str, Any] | None = None
        self.sha = 0
        self.puts = 0
        self.conflitos = conflitos  # quantos PUTs responder 409 (alguém gravou no meio)
        self.branch = False  # a branch "dados" só existe depois que o site a cria
        self.limite_anonimo = limite_anonimo  # o endereço passou do limite de consultas sem chave: 403 em tudo sem Authorization
        self.anonimas = 0  # pedidos recebidos sem chave

    def handler(self, route: Any) -> None:
        req = route.request
        auth = req.headers.get("authorization", "")
        if not auth:
            self.anonimas += 1
            if self.limite_anonimo:
                route.fulfill(status=403, json={"message": "API rate limit exceeded for 203.0.113.9. (But here's the good news: Authenticated requests get a higher rate limit.)"})
                return
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
    page = nova_pagina(browser, 1440, 900)
    page.context.route("https://api.github.com/**", gh.handler)
    if token:
        page.add_init_script(f"localStorage.setItem('{SYNCK}', JSON.stringify({{token: '{token}'}}))")
    page.goto(url + "/index.html?repo=dono/repo#/oportunidades")
    wait_ready(page)
    page.wait_for_selector(".page.opp")
    return page


def espera_salvo(page: Page) -> None:
    page.wait_for_function("window.__monitor.syncState().estado === 'ok' && !window.__monitor.syncState().pendente", timeout=8000)


def test_sync_saves_to_github_and_second_device_sees_it(browser: Any, fixture_url: str) -> None:
    gh = FakeGitHub()
    a = aparelho(browser, fixture_url, gh)
    row(a, FIRST).locator('[data-act="fav"]').click()
    espera_salvo(a)
    assert gh.doc and gh.doc["meus_dados"][FIRST]["fav"] is True and gh.branch  # criou a branch "dados"
    assert a.locator("#upd").get_attribute("data-sync") == "ok"
    b = aparelho(browser, fixture_url, gh)  # outro aparelho, navegador vazio
    b.wait_for_function(f"document.querySelector('.list .row[data-ch=\"{FIRST}\"] .star.on')")
    go_tab(b, "propostas")
    assert b.locator(f'[data-ch="{FIRST}"]').count() >= 1
    fechar(a)
    fechar(b)


def test_sync_unfavorite_is_not_resurrected_by_other_device(browser: Any, fixture_url: str) -> None:
    gh = FakeGitHub()
    a = aparelho(browser, fixture_url, gh)
    row(a, FIRST).locator('[data-act="fav"]').click()
    espera_salvo(a)
    b = aparelho(browser, fixture_url, gh)
    b.wait_for_function(f"document.querySelector('.list .row[data-ch=\"{FIRST}\"] .star.on')")
    row(a, FIRST).locator('[data-act="fav"]').click()  # desfavorita no aparelho A
    espera_salvo(a)
    assert gh.doc["meus_dados"][FIRST].get("fav") is None  # fica só a marca de removido
    b.evaluate("window.__monitor.sync()")  # B ainda tinha o favorito antigo guardado
    b.wait_for_function(f"!document.querySelector('.list .row[data-ch=\"{FIRST}\"] .star.on')")
    espera_salvo(b)
    assert gh.doc["meus_dados"][FIRST].get("fav") is None
    fechar(a)
    fechar(b)


def test_sync_merges_when_someone_saved_in_between(browser: Any, fixture_url: str) -> None:
    gh = FakeGitHub(conflitos=1)
    a = aparelho(browser, fixture_url, gh)
    row(a, FIRST).locator('[data-act="fav"]').click()
    espera_salvo(a)
    assert gh.doc["meus_dados"][FIRST]["fav"] is True and gh.conflitos == 0  # o 409 aconteceu e foi resolvido
    fechar(a)


def test_sync_rejected_key_keeps_data_local(browser: Any, fixture_url: str) -> None:
    gh = FakeGitHub()
    a = aparelho(browser, fixture_url, gh, token="velha")
    row(a, FIRST).locator('[data-act="fav"]').click()
    a.wait_for_function("window.__monitor.syncState().estado === 'erro'", timeout=8000)
    assert gh.doc is None and ls(a, WFK)[FIRST]["fav"] is True
    assert "recusada" in a.evaluate("window.__monitor.syncState().erro")
    fechar(a, esperado="Gravação no GitHub falhou")  # o erro é o esperado neste teste


def test_sync_anonymous_rate_limit_is_not_a_key_error(browser: Any, fixture_url: str) -> None:
    """Sem chave o site só lê. Se o GitHub limitar o endereço (403 nas consultas sem chave, comum em rede de celular),
    fica "só neste aparelho" sem acusar chave recusada; com chave, o mesmo endereço lê e grava normalmente."""
    gh = FakeGitHub(limite_anonimo=True)
    a = aparelho(browser, fixture_url, gh, token=None)
    for _ in range(50):  # espera a leitura sem chave chegar e levar o 403
        if gh.anonimas:
            break
        a.wait_for_timeout(100)
    assert gh.anonimas >= 1
    a.wait_for_timeout(500)
    st = a.evaluate("window.__monitor.syncState()")
    assert st["estado"] == "local" and st["erro"] == "", st
    assert a.locator("#upd").get_attribute("data-sync") == "local"
    row(a, FIRST).locator('[data-act="fav"]').click()
    assert ls(a, WFK)[FIRST]["fav"] is True  # a anotação fica guardada no aparelho
    b = aparelho(browser, fixture_url, gh)
    row(b, FIRST).locator('[data-act="fav"]').click()
    espera_salvo(b)
    assert gh.doc["meus_dados"][FIRST]["fav"] is True
    fechar(a)
    fechar(b)


def test_sync_keeps_old_removal_marks_forever(browser: Any, fixture_url: str) -> None:
    """Marca de removido antiga (anos) continua existindo e vai para o GitHub: um aparelho que ficou meses sem abrir
    não traz o favorito de volta."""
    gh = FakeGitHub()
    a = nova_pagina(browser, 1440, 900)
    a.context.route("https://api.github.com/**", gh.handler)
    marca = {GONE: {"upd": "2023-01-01T00:00:00.000Z"}}
    a.add_init_script(f"localStorage.setItem('{SYNCK}', JSON.stringify({{token: 'boa'}})); localStorage.setItem('{WFK}', {json.dumps(json.dumps(marca))})")
    a.goto(fixture_url + "/index.html?repo=dono/repo#/oportunidades")
    wait_ready(a)
    row(a, FIRST).locator('[data-act="fav"]').click()
    espera_salvo(a)
    assert gh.doc["meus_dados"][GONE] == {"upd": "2023-01-01T00:00:00.000Z"} and ls(a, WFK)[GONE] == {"upd": "2023-01-01T00:00:00.000Z"}
    fechar(a)


def test_sync_connect_with_key_in_settings(browser: Any, fixture_url: str) -> None:
    gh = FakeGitHub()
    a = aparelho(browser, fixture_url, gh, token=None)
    row(a, FIRST).locator('[data-act="fav"]').click()
    assert a.locator("#upd").get_attribute("data-sync") == "local" and gh.doc is None
    go_tab(a, "ajustes")
    assert "Só neste aparelho" in a.locator("#syncLbl").inner_text()
    a.fill("#syncTok", "boa")
    a.click("#syncSave")
    espera_salvo(a)
    assert gh.doc["meus_dados"][FIRST]["fav"] is True and ls(a, SYNCK) == {"token": "boa"}
    assert "Salvo no GitHub" in a.locator("#syncLbl").inner_text()
    fechar(a)


def test_margin_estimate_matches_collector_and_follows_my_costs(browser: Any, fixture_url: str) -> None:
    from coletor import custos, referencia
    data = json.loads((ROOT / "tests" / "fixtures" / "data_min.json").read_text(encoding="utf-8"))
    c = next(x for x in data["compras"] if x["chave"] == FIRST)
    py = custos.margem(c, referencia.item_principal(c), data["mercado"], data["custos"])
    assert py is not None
    gh = FakeGitHub()
    page = aparelho(browser, fixture_url, gh)
    js = page.evaluate(f"(() => {{ const c = window.__monitor.state().prep.byk['{FIRST}']; return {{custo: c._mg.custo, mp: c._mg.mp, empate: c._mg.empate}}; }})()")
    assert abs(js["custo"] - py["custo"]) < 0.01 and abs(js["mp"] - py["margem_pct"]) < 0.0001  # mesma regra nos dois lados
    assert f"{'+' if py['margem_pct'] > 0 else ''}{round(py['margem_pct'] * 100)}%" in row(page, FIRST).locator(".c-mg").inner_text()
    d = open_detail(page, FIRST)
    card = d.locator('[data-testid="custo-margem"]').inner_text()
    assert "Preço para empatar" in card and "Frete até" in card
    d.locator('[data-act="custos"]').click()  # leva a Meus custos
    page.wait_for_selector(".page.ajustes")
    page.locator('[data-testid="custo-torra"]').fill("15")
    page.keyboard.press("Tab")
    page.wait_for_function(f"window.__monitor.state().prep.byk['{FIRST}']._mg.custo > {js['custo']} + 10")
    espera_salvo(page)
    assert gh.doc["custos"]["valores"]["torra"] == 15  # gravado com as anotações
    page.locator('[data-act="custos-padrao"]').click()
    page.wait_for_function(f"Math.abs(window.__monitor.state().prep.byk['{FIRST}']._mg.custo - {js['custo']}) < 0.01")
    fechar(page)


# ---------------- revisão de UI/UX (21/10/2026): erros confirmados nas fotos do site
def test_mobile_rows_keep_numbers_on_screen(browser: Any, fixture_url: str) -> None:
    """Nome de órgão longo não pode empurrar kg, valor, R$/kg e margem para fora da tela do celular."""
    pg = nova_pagina(browser, 390, 844)
    goto(pg, fixture_url)
    ruins = pg.evaluate("""() => [...document.querySelectorAll('.list .row')].filter(r => r.scrollWidth > r.clientWidth + 1
      || [...r.querySelectorAll('.c-valor,.c-rkg,.c-mg')].some(c => c.getBoundingClientRect().right > window.innerWidth)).map(r => r.dataset.ch)""")
    assert ruins == []
    assert row(pg, FIRST).locator(".c-prazo .pill").is_visible()  # prazo e margem aparecem no cartão do celular
    assert row(pg, FIRST).locator(".c-mg .mg").is_visible()
    assert "—" not in row(pg, FIRST).locator(".c-status").inner_text()  # sem travessão solto no fim do cartão
    fechar(pg)


def test_mobile_best_table_shows_profit_without_hidden_scroll(browser: Any, fixture_url: str) -> None:
    pg = nova_pagina(browser, 390, 844)
    goto(pg, fixture_url, "hoje")
    assert pg.locator(".melhores .mrow").count() > 0
    assert pg.evaluate("() => { const el = document.querySelector('.melhores .scroll-x'); return el.scrollWidth <= el.clientWidth + 1; }")
    r = pg.locator(".melhores .mrow").first
    assert r.locator(".m-lucro").is_visible() and r.locator(".m-mg-cel").is_visible() and r.locator(".m-prazo").is_visible()
    assert not r.locator(".m-kg").is_visible() and not r.locator(".m-rkg").is_visible()
    fechar(pg)


def test_palette_box_is_opaque(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    page.keyboard.press("Control+k")
    page.wait_for_selector("[cmdk-dialog] [cmdk-root]")
    bg = page.evaluate("getComputedStyle(document.querySelector('[cmdk-dialog] [cmdk-root]')).backgroundColor")
    assert bg not in ("rgba(0, 0, 0, 0)", "transparent"), bg  # antes, o texto da página aparecia atrás da lista
    page.keyboard.press("Escape")


def test_repeated_notices_collapse_into_one(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    for k in (FIRST, MIXED, PARTIAL):
        row(page, k).locator('[data-act="fav"]').click()
    toasts = page.locator(".toast")
    assert toasts.count() == 1 and "×3" in toasts.first.inner_text()
    row(page, FIRST).locator('[data-act="fav"]').click()  # mensagem diferente: segundo aviso
    assert toasts.count() == 2
    row(page, MIXED).locator('[data-act="fav"]').click()  # igual ao último: junta nele
    assert toasts.count() == 2 and "×2" in toasts.last.inner_text()
    row(page, FIRST).locator('[data-act="fav"]').click()  # terceira mensagem diferente: nunca mais que 2 na tela
    page.wait_for_function("document.querySelectorAll('.toast').length === 2")  # o mais antigo sai com animação
    assert len(page.evaluate("window.__monitor.state().toasts")) == 2


def test_today_kpi_shows_my_proposals_by_stage(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    wf = {FIRST: {"fav": True, "upd": "x"}, MIXED: {"status": "Enviada", "upd": "x"}, GONE: {"status": "Em preparação", "upd": "x"}}
    page.evaluate("([k, v]) => localStorage.setItem(k, v)", [WFK, json.dumps(wf)])
    page.reload()
    wait_ready(page)
    go_tab(page, "hoje")
    t = page.locator('[data-testid="kpi-etapas"]').inner_text()
    assert "1 sem status" in t and "1 enviada" in t and "1 em preparação" in t
    page.wait_for_function("document.querySelector('.kpi[data-k=\"mine\"] .v').textContent.trim() === '3'")  # as que saíram dos dados contam, como no quadro
    assert page.locator('.kpi[data-k="mine"] .stacked.ghost').count() == 0


def test_detail_axis_last_label_is_not_cut(page: Page, real_url: str) -> None:
    goto(page, real_url)  # dados reais: a faixa só aparece com licitações suficientes do mesmo nível (REF_MIN), e os de teste não chegam lá
    chave = page.evaluate("""async () => { for (const k of window.__monitor.lista()) { window.__monitor.open(k); await new Promise(r => setTimeout(r, 80));
      if (document.querySelector('.detalhe .strip')) return k; } return null; }""")
    assert chave, "nenhuma licitação de teste mostra a faixa de preços"
    d = page.locator(f'.detalhe[data-ch="{chave}"]')
    labels = d.locator(".strip .axl")
    assert labels.last.get_attribute("text-anchor") == "end"
    svg, last = d.locator(".strip").bounding_box(), labels.last.bounding_box()
    assert svg and last and last["x"] + last["width"] <= svg["x"] + svg["width"] + 1


# ---------------- revisão de UI/UX (21/10/2026): organização e alinhamento
def test_verdict_is_a_labeled_list_with_badge_below_headline(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    d = open_detail(page, FIRST)
    v = d.locator(".verdict")
    assert "nível Superior" in v.locator(".big").inner_text() and v.locator(".big .pc").count() == 0  # o selo de comparação não fica dentro da frase
    rotulos = v.locator(".vd-list small").all_inner_texts()
    assert rotulos[0] == "Preço típico do nível" and "Meu preço mínimo" in rotulos and any(r.startswith("Por que nível") for r in rotulos)
    assert v.locator('[data-act="pisos"]').count() == 1


def test_mobile_filter_bar_is_compact(browser: Any, fixture_url: str) -> None:
    pg = nova_pagina(browser, 390, 844)
    goto(pg, fixture_url)
    b, s = pg.locator('[data-testid="btn-filtros"]').bounding_box(), pg.locator("#sort").bounding_box()
    assert b and s and abs(b["y"] - s["y"]) < 4  # Filtros e ordenação na mesma linha
    q = pg.locator(".opp-tools .quick")
    assert pg.evaluate("el => getComputedStyle(el).flexWrap === 'nowrap' && el.scrollWidth > 0", q.element_handle())
    assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert "Buscar nesta lista" in (pg.locator("#q").get_attribute("placeholder") or "")
    fechar(pg)


def test_level_labels_never_wrap_in_price_chart(browser: Any, fixture_url: str) -> None:
    for w in (1440, 390):
        pg = nova_pagina(browser, w, 900)
        goto(pg, fixture_url, "hoje")
        alturas = [b["height"] for b in [x.bounding_box() for x in pg.locator(".faixa-n").all()] if b]
        assert alturas and max(alturas) < 30, (w, alturas)  # "Sem categoria" numa linha só
        eixo, barras = pg.locator(".faixa-axis").bounding_box(), pg.locator(".faixa-c").first.bounding_box()
        assert eixo and barras and abs(eixo["x"] - barras["x"]) < 2 and abs(eixo["width"] - barras["width"]) < 2  # eixo alinhado com as barras
        fechar(pg)


def test_brand_rows_keep_count_on_first_line(page: Page, real_url: str) -> None:
    goto(page, real_url, "hoje")
    linha = page.locator('[aria-label="Marcas citadas"] .hb-row').first
    t, v, sub = linha.locator(".hb-t").bounding_box(), linha.locator(".hb-v").bounding_box(), linha.locator(".hb-sub").bounding_box()
    assert t and v and sub and abs(t["y"] - v["y"]) < 6 and sub["y"] > t["y"]  # número ao lado do nome; preço de varejo embaixo


def test_market_merges_uncategorized_into_traditional_card(page: Page, real_url: str) -> None:
    goto(page, real_url, "mercado")
    cards = page.locator(".niv-cards .card")
    assert cards.count() == 3 and page.locator('.niv-cards .card[data-nivel="Sem categoria"]').count() == 0
    assert "Vale também para edital sem categoria" in page.locator('.niv-cards .card[data-nivel="Tradicional"]').inner_text()
    assert page.locator(".tbl-g").count() == 1 and "Carvalhaes · CD" not in page.locator(".page.mercado .tbl").first.inner_text()  # nome da corretora só no cabeçalho do grupo


def test_proposal_card_footer_is_always_the_same(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url)
    wf = {FIRST: {"fav": True, "upd": "x"}, MIXED: {"status": "Em preparação", "upd": "x"}, PARTIAL: {"status": "Enviada", "upd": "x"}}
    page.evaluate("([k, v]) => localStorage.setItem(k, v)", [WFK, json.dumps(wf)])
    page.reload()
    wait_ready(page)
    go_tab(page, "propostas")
    for k in (FIRST, MIXED, PARTIAL):
        card = page.locator(f'.prop[data-ch="{k}"]')
        st, ab, pa = card.locator(".glide-btn").bounding_box(), card.locator("[data-open]").bounding_box(), card.locator(f'[data-testid="unfollow-{k}"]').bounding_box()
        assert st and ab and pa and abs(st["y"] - ab["y"]) < 4 and pa["y"] > ab["y"] + ab["height"] - 1, k  # status e Abrir numa linha; Parar embaixo
        assert abs(pa["x"] - st["x"]) < 2 and pa["height"] < 40  # Parar alinhado à esquerda, numa linha só
    assert page.locator(".stage-g h3 .cnt").count() == 3 and page.locator(".stage-g h3 i").count() == 0
    assert page.locator('.agenda .seg button:has-text("Minhas")').count() == 1


def test_settings_sync_text_without_jargon(page: Page, fixture_url: str) -> None:
    goto(page, fixture_url, "ajustes")
    t = page.locator("#sync").inner_text()
    for jargao in ("branch", "repositório", "meus-dados.json", "React"):
        assert jargao not in t, jargao
    assert "(React)" not in page.locator(".page.ajustes").inner_text()
