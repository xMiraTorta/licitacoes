"""Distância por estrada de Uberaba-MG até a sede de cada município (cálculo feito uma vez só).

Fonte: OSRM (router.project-osrm.org), roteador gratuito sobre o OpenStreetMap. Conferido em 17/10/2026:
Uberaba→Sacramento 75,9 km, →Belo Horizonte 476 km, →São Paulo 481 km (próximo do Google Maps).
Estradas mudam pouco: recalcular só se a origem mudar (`python -m coletor distancias`).
O resultado fica em `distancias_uberaba.csv` e o coletor só lê esse arquivo (custo diário zero).
"""
from __future__ import annotations

import csv
import time
from functools import lru_cache
from pathlib import Path

import httpx
from loguru import logger

ORIGEM = {"nome": "Uberaba-MG", "lat": -19.7472, "lon": -47.9381, "codigo_ibge": "3170107"}
ARQUIVO = Path(__file__).with_name("distancias_uberaba.csv")
MUNICIPIOS = Path(__file__).with_name("municipios.csv")
OSRM = "https://router.project-osrm.org/table/v1/driving/"
LOTE = 250  # a URL estoura (HTTP 414) acima de ~400 pontos


@lru_cache(maxsize=1)
def tabela() -> dict[str, tuple[int, int]]:
    """codigo_ibge -> (km por estrada, minutos de viagem)."""
    if not ARQUIVO.exists():
        raise FileNotFoundError(f"{ARQUIVO} não existe: rode `python -m coletor distancias`")
    with ARQUIVO.open(encoding="utf-8") as f:
        return {r["codigo_ibge"]: (int(r["km"]), int(r["minutos"])) for r in csv.DictReader(f) if r["km"]}


def estrada(codigo_ibge: str | None) -> tuple[int | None, int | None]:
    return tabela().get(str(codigo_ibge or ""), (None, None))


def calcular(client: httpx.Client | None = None, pausa: float = 1.0) -> int:
    """Consulta o OSRM em lotes e grava o CSV. Município sem rota (ilhas) fica em branco."""
    cli = client or httpx.Client(timeout=60, headers={"User-Agent": "licitacoes-monitor/1.0"})
    with MUNICIPIOS.open(encoding="utf-8") as f:
        muns = list(csv.DictReader(f))
    saida: list[dict[str, str]] = []
    for i in range(0, len(muns), LOTE):
        lote = muns[i:i + LOTE]
        pts = [(ORIGEM["lon"], ORIGEM["lat"])] + [(float(m["lon"]), float(m["lat"])) for m in lote]
        url = OSRM + ";".join(f"{x:.5f},{y:.5f}" for x, y in pts)
        r = cli.get(url, params={"sources": 0, "annotations": "distance,duration"})
        r.raise_for_status()
        d = r.json()
        if d.get("code") != "Ok":
            raise RuntimeError(f"OSRM recusou o lote {i}: {d.get('code')} {d.get('message')}")
        for m, dist, dur in zip(lote, d["distances"][0][1:], d["durations"][0][1:], strict=True):
            ok = dist is not None and dur is not None
            saida.append({"codigo_ibge": m["codigo_ibge"], "nome": m["nome"], "uf": m["uf"],
                          "km": str(round(dist / 1000)) if ok else "", "minutos": str(round(dur / 60)) if ok else ""})
        logger.info("Distâncias: {}/{} municípios", len(saida), len(muns))
        time.sleep(pausa)
    sem = [s for s in saida if not s["km"]]
    if len(sem) > 50:
        raise RuntimeError(f"{len(sem)} municípios sem rota: resultado suspeito, arquivo não gravado")
    tmp = ARQUIVO.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["codigo_ibge", "nome", "uf", "km", "minutos"])
        w.writeheader()
        w.writerows(saida)
    tmp.replace(ARQUIVO)
    logger.info("Gravado {} ({} municípios, {} sem rota: {})", ARQUIVO.name, len(saida), len(sem),
                [f"{s['nome']}-{s['uf']}" for s in sem])
    tabela.cache_clear()
    return len(saida)
