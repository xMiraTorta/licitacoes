"""Junta a coleta nova com a anterior, valida e grava data.json + cópia embutida em index.html.

Travas de segurança (uma coleta ruim nunca substitui dados bons em silêncio):
- listagem incompleta (qualquer página com erro) -> aborta antes de chegar aqui;
- falha ao baixar itens de mais de LIMITE_FALHAS das candidatas -> aborta;
- compras abertas caem abaixo de LIMITE_QUEDA da coleta anterior -> aborta;
- compra conhecida cujos itens falharam nesta rodada -> mantém o registro anterior;
- validação de formato antes de gravar; gravação atômica (arquivo temporário + rename).
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

DATA_PREFIX = "const DATA0 = "
LIMITE_FALHAS = 0.05
LIMITE_QUEDA = 0.6


class PublicacaoBloqueada(RuntimeError):
    """A coleta parece incompleta; os arquivos publicados não foram alterados."""


def carregar(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def abertas(compras: list[dict[str, Any]], agora: str) -> list[dict[str, Any]]:
    return [c for c in compras if not c.get("fim") or c["fim"] >= agora]


def novas_desde(anterior: dict[str, Any] | None, hoje: str) -> str:
    """Data de referência para o selo "Nova": a última coleta de um dia anterior a hoje."""
    if not anterior:
        return hoje
    if anterior.get("run_date", hoje) < hoje:
        return anterior["run_date"]
    return anterior.get("novas_desde") or anterior.get("run_date", hoje)


def juntar(novas: list[dict[str, Any]], anterior: dict[str, Any] | None, falharam: set[str],
           hoje: str, agora_min: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Compras finais e lista das que apareceram pela primeira vez nesta rodada."""
    from coletor.montar import herdar_do_anterior, marcar_duplicatas

    antigos = {c["chave"]: c for c in (anterior or {}).get("compras", [])}
    seed = (anterior or {}).get("seed_date", hoje)
    ref = novas_desde(anterior, hoje)
    out: list[dict[str, Any]] = []
    primeira_vez: list[str] = []
    for c in novas:
        if c["chave"] in antigos:
            herdar_do_anterior(c, antigos[c["chave"]])
        else:
            c["first_seen"] = hoje
            primeira_vez.append(c["chave"])
        out.append(c)
    vistos = {c["chave"] for c in out}
    mantidas = [dict(antigos[k]) for k in sorted(falharam) if k in antigos and k not in vistos
                and (not antigos[k].get("fim") or antigos[k]["fim"] >= agora_min)]
    if mantidas:
        logger.warning("{} compras conhecidas mantidas da coleta anterior porque os itens falharam: {}",
                       len(mantidas), [c["chave"] for c in mantidas])
    out.extend(mantidas)
    out = [c for c in out if not c.get("fim") or c["fim"] >= agora_min]
    for c in out:
        c["nova"] = hoje != seed and (c.get("first_seen") or hoje) > ref
    out.sort(key=lambda c: (c.get("fim") or "9999", c["chave"]))
    marcar_duplicatas(out, {k for k, c in antigos.items() if not c.get("dup_of")})
    return out, primeira_vez


def verificar_travas(compras: list[dict[str, Any]], anterior: dict[str, Any] | None, candidatas: int,
                     falhas: int, agora_min: str, forcar: bool = False) -> None:
    problemas = []
    if candidatas and falhas / candidatas > LIMITE_FALHAS:
        problemas.append(f"itens falharam em {falhas} de {candidatas} candidatas (> {LIMITE_FALHAS:.0%})")
    if anterior:
        antes = len(abertas(anterior.get("compras", []), agora_min))
        if antes and len(compras) < antes * LIMITE_QUEDA:
            problemas.append(f"{len(compras)} compras abertas agora contra {antes} na coleta anterior "
                             f"(queda maior que {1 - LIMITE_QUEDA:.0%})")
    if not compras:
        problemas.append("nenhuma compra de café encontrada")
    if problemas:
        msg = "; ".join(problemas)
        if forcar:
            logger.warning("Travas ignoradas por --forcar: {}", msg)
        else:
            raise PublicacaoBloqueada(msg)


def validar(data: dict[str, Any]) -> None:
    from coletor.modelos import Painel

    Painel.model_validate(data)


def _gravar_atomico(path: Path, texto: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(texto, encoding="utf-8")
    os.replace(tmp, path)


def embutir_no_html(html: str, data_json: str) -> str:
    """Troca a linha `const DATA0 = ...;`. Textos do PNCP podem conter "</script>" ou "<!--", que
    encerrariam o <script> da página (e rodariam código de terceiros): escapados como "<\\/" e
    "<\\u0021--", que continuam JSON/JavaScript válidos e com o mesmo valor."""
    seguro = data_json.replace("</", "<\\/").replace("<!--", "<\\u0021--")
    inicio = html.index("\n" + DATA_PREFIX) + 1
    fim = html.index("\n", inicio)
    if not html[inicio:fim].endswith(";"):
        raise ValueError("linha const DATA0 em index.html não termina com ';'")
    return html[:inicio] + DATA_PREFIX + seguro + ";" + html[fim:]


def atualizar_cabecalho(html: str, gerado_em: datetime) -> str:
    """Texto estático "Atualizado em" (a página também o reescreve ao carregar)."""
    import re

    novo = f'<span id="upd">Atualizado em <b>{gerado_em:%d/%m/%Y %H:%M}</b> (horário de Brasília)</span>'
    html2, n = re.subn(r'<span id="upd">.*?</span>', novo, html, count=1)
    if n != 1:
        raise ValueError('span id="upd" não encontrado em index.html')
    return html2


def gravar(data: dict[str, Any], destino: Path, gerado_em: datetime) -> None:
    validar(data)
    texto = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    html_path = destino / "index.html"
    html = atualizar_cabecalho(embutir_no_html(html_path.read_text(encoding="utf-8"), texto), gerado_em)
    _gravar_atomico(destino / "data.json", texto)
    _gravar_atomico(html_path, html)
    logger.info("Gravados data.json ({} KB) e index.html com {} compras", len(texto) // 1024, len(data["compras"]))
