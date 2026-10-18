"""Mapa do Brasil por estado para o Dashboard: contorno oficial do IBGE convertido em caminhos SVG.

Fonte: API de malhas do IBGE (servicodados.ibge.gov.br, dado público), qualidade "mínima".
Roda só quando for preciso refazer o desenho (`python -m coletor mapa`); o resultado fica embutido
no index.html na linha `const MAPA_UF = ...;`.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

URL = ("https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
       "?formato=application/vnd.geo+json&intrarregiao=UF&qualidade=minima")
PREFIXO = "const MAPA_UF = "
UF_IBGE = {"11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO", "21": "MA", "22": "PI",
           "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
           "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF"}
LARGURA = 600.0
TOLERANCIA = 0.6  # simplificação em unidades do SVG (~0,05 grau): contorno leve, sem perder a forma


def _simplificar(pts: list[tuple[float, float]], tol: float) -> list[tuple[float, float]]:
    """Douglas-Peucker: remove pontos que quase não mudam o contorno."""
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    norma = math.hypot(dx, dy)
    if norma == 0:  # anel fechado (primeiro ponto = último): distância até esse ponto
        dist = [math.hypot(x - x1, y - y1) for x, y in pts[1:-1]]
    else:
        dist = [abs(dy * x - dx * y + x2 * y1 - y2 * x1) / norma for x, y in pts[1:-1]]
    k = max(range(len(dist)), key=dist.__getitem__)
    if dist[k] <= tol:
        return [pts[0], pts[-1]]
    return _simplificar(pts[:k + 2], tol)[:-1] + _simplificar(pts[k + 1:], tol)


def caminhos(geo: dict[str, Any]) -> dict[str, Any]:
    """{"viewBox": "...", "uf": {"MG": "M...Z", ...}} em projeção equirretangular corrigida pela latitude média."""
    aneis: dict[str, list[list[list[float]]]] = {}
    for f in geo["features"]:
        uf = UF_IBGE[f["properties"]["codarea"]]
        g = f["geometry"]
        polis = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        aneis[uf] = [anel for p in polis for anel in p[:1]]  # só o contorno externo de cada parte
    todos = [pt for rs in aneis.values() for r in rs for pt in r]
    lon0, lon1 = min(p[0] for p in todos), max(p[0] for p in todos)
    lat0, lat1 = min(p[1] for p in todos), max(p[1] for p in todos)
    kx = math.cos(math.radians((lat0 + lat1) / 2))
    esc = LARGURA / ((lon1 - lon0) * kx)
    altura = (lat1 - lat0) * esc

    def xy(p: list[float]) -> tuple[float, float]:
        return (p[0] - lon0) * kx * esc, (lat1 - p[1]) * esc

    out, centro = {}, {}
    for uf, rs in sorted(aneis.items()):
        partes = []
        for r in rs:
            pts = _simplificar([xy(p) for p in r], TOLERANCIA)
            if len(pts) >= 3:
                partes.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z")
        out[uf] = "".join(partes)
        maior = [xy(p) for p in max(rs, key=len)]  # rótulo no meio da maior parte (ilhas ficam de fora)
        centro[uf] = [round(sum(x for x, _ in maior) / len(maior), 1), round(sum(y for _, y in maior) / len(maior), 1)]
    return {"viewBox": f"0 0 {LARGURA:.0f} {altura:.0f}", "uf": out, "centro": centro}


def embutir(html: str, mapa: dict[str, Any]) -> str:
    inicio = html.index("\n" + PREFIXO) + 1
    fim = html.index("\n", inicio)
    return html[:inicio] + PREFIXO + json.dumps(mapa, separators=(",", ":")) + ";" + html[fim:]


def gerar(destino: Path) -> None:
    r = httpx.get(URL, timeout=60, follow_redirects=True)
    r.raise_for_status()
    mapa = caminhos(r.json())
    if set(mapa["uf"]) != set(UF_IBGE.values()):
        raise ValueError(f"malha do IBGE incompleta: {sorted(set(UF_IBGE.values()) - set(mapa['uf']))}")
    html_path = destino / "index.html"
    html_path.write_text(embutir(html_path.read_text(encoding="utf-8"), mapa), encoding="utf-8")
    logger.info("Mapa do Brasil embutido no index.html ({} KB, 27 estados)", len(json.dumps(mapa)) // 1024)
