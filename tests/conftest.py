"""Fixtures compartilhadas: site montado (site/dist), servidor HTTP local e navegador headless.

Os testes de página não acessam a internet: servem a versão montada do site (site/dist) com um data.json
de teste (ou o real) a partir de um servidor local. Se o dist estiver ausente ou mais velho que o código,
`npm run build` roda uma vez (precisa de Node e de `npm install` em site/).
"""
from __future__ import annotations

import functools
import http.server
import json
import os
import shutil
import socketserver
import subprocess
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Browser, Page, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
SITE = ROOT / "site"
DIST = SITE / "dist"


def _dist_desatualizado() -> bool:
    idx = DIST / "index.html"
    if not idx.exists():
        return True
    t = idx.stat().st_mtime
    fontes = [*(SITE / "src").rglob("*"), *(SITE / "public").rglob("*"), SITE / "index.html", SITE / "vite.config.ts", SITE / "tsconfig.json",
              SITE / "package.json", SITE / "package-lock.json"]
    return any(p.is_file() and p.stat().st_mtime > t for p in fontes)


@pytest.fixture(scope="session")
def dist_dir() -> Path:
    """Site montado. Monta de novo se o código mudou depois do último build."""
    if _dist_desatualizado():
        if not (SITE / "node_modules").exists():
            raise RuntimeError("site/node_modules não existe: rode `npm install` em site/ (precisa de Node 22)")
        r = subprocess.run(["npm", "run", "build"], cwd=SITE, capture_output=True, text=True)
        if r.returncode != 0:  # mostra o erro do TypeScript/Vite em vez de só "exit status 1"
            raise RuntimeError(f"npm run build falhou (código {r.returncode}):\n{r.stdout}\n{r.stderr}")
    return DIST


def _montar_site(destino: Path, dist: Path, data: dict[str, Any]) -> Path:
    shutil.copytree(dist, destino, dirs_exist_ok=True)
    (destino / "data.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return destino


@pytest.fixture(scope="session")
def site_dir(tmp_path_factory: pytest.TempPathFactory, dist_dir: Path) -> Path:
    """Diretório servido: site montado com os dados de teste em tests/fixtures/data_min.json."""
    data = json.loads((FIXTURES / "data_min.json").read_text(encoding="utf-8"))
    return _montar_site(tmp_path_factory.mktemp("site"), dist_dir, data)


@pytest.fixture(scope="session")
def real_site_dir(tmp_path_factory: pytest.TempPathFactory, dist_dir: Path) -> Path:
    """Site montado com os dados reais do repositório (data.json)."""
    data = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
    return _montar_site(tmp_path_factory.mktemp("site_real"), dist_dir, data)


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 (assinatura da stdlib)
        pass


class _Servidor(socketserver.ThreadingTCPServer):
    """Uma conexão por thread: o Chromium abre várias ao mesmo tempo (e os testes de sincronização, duas páginas)."""
    daemon_threads = True
    allow_reuse_address = True


def _serve(directory: Path) -> Iterator[str]:
    handler = functools.partial(_QuietHandler, directory=str(directory))
    with _Servidor(("127.0.0.1", 0), handler) as httpd:
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
        httpd.shutdown()


@pytest.fixture(scope="session")
def fixture_url(site_dir: Path) -> Iterator[str]:
    """Site com dados de teste controlados."""
    yield from _serve(site_dir)


@pytest.fixture(scope="session")
def real_url(real_site_dir: Path) -> Iterator[str]:
    """Site com os dados atuais do repositório."""
    yield from _serve(real_site_dir)


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
    pg.wait_for_function("() => window.__monitor && window.__monitor.state().prep && document.querySelector('.page')")
