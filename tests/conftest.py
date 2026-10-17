"""Fixtures compartilhadas: servidor HTTP local e navegador headless.

Os testes de página não acessam a internet: servem os arquivos do repositório
(ou uma cópia com dados de teste) a partir de um servidor local.
"""
from __future__ import annotations

import functools
import http.server
import json
import os
import socketserver
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Browser, Page, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
DATA_LINE_PREFIX = "const DATA0 = "


def split_index(html: str) -> tuple[str, str, str]:
    """Separa index.html em (antes, json embutido, depois) da linha `const DATA0 = ...;`."""
    start = html.index("\n" + DATA_LINE_PREFIX) + 1
    end = html.index("\n", start)
    line = html[start:end]
    if not line.endswith(";"):
        raise ValueError("linha DATA0 não termina com ';'")
    return html[:start], line[len(DATA_LINE_PREFIX):-1], html[end:]


def embedded_data(html: str) -> dict[str, Any]:
    return json.loads(split_index(html)[1])


def page_with_data(html: str, data: dict[str, Any]) -> str:
    before, _, after = split_index(html)
    return before + DATA_LINE_PREFIX + json.dumps(data, ensure_ascii=False) + ";" + after


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 (assinatura da stdlib)
        pass


@pytest.fixture(scope="session")
def site_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Diretório servido: cópia de index.html com os dados de teste em tests/fixtures/data_min.json."""
    d = tmp_path_factory.mktemp("site")
    data = json.loads((FIXTURES / "data_min.json").read_text(encoding="utf-8"))
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    (d / "index.html").write_text(page_with_data(html, data), encoding="utf-8")
    (d / "data.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return d


def _serve(directory: Path) -> Iterator[str]:
    handler = functools.partial(_QuietHandler, directory=str(directory))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as httpd:
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
        httpd.shutdown()


@pytest.fixture(scope="session")
def fixture_url(site_dir: Path) -> Iterator[str]:
    """Site com dados de teste controlados."""
    yield from _serve(site_dir)


@pytest.fixture(scope="session")
def real_url() -> Iterator[str]:
    """Site real do repositório (dados atuais)."""
    yield from _serve(ROOT)


@pytest.fixture(scope="session")
def browser() -> Iterator[Browser]:
    exe = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH")
    if not exe and Path("/opt/pw-browsers/chromium").exists():
        exe = "/opt/pw-browsers/chromium"  # ambiente de nuvem do Claude Code
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def page(browser: Browser) -> Iterator[Page]:
    """Página nova (localStorage limpo) que falha o teste se houver erro de JavaScript."""
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    errors: list[str] = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" and "ilegíveis" not in m.text else None)
    yield pg
    ctx.close()
    assert not errors, f"erros de JavaScript na página: {errors}"


def wait_ready(pg: Page) -> None:
    pg.wait_for_function("() => window.__cafe && document.querySelectorAll('.kpi').length > 0")
