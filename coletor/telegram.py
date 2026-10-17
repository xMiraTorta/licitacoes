"""Aviso no Telegram das licitações novas. Token e chat vêm de variáveis de ambiente (segredos do GitHub)."""
from __future__ import annotations

import html
import os
from datetime import datetime
from typing import Any

import httpx
from loguru import logger

# O workflow passa o endereço do site (muda se o repositório for renomeado).
PAINEL_URL = os.environ.get("PAINEL_URL") or "https://xmiratorta.github.io/licitacoes-cafe/"
LIMITE_MSG = 3900  # Telegram aceita 4096 caracteres por mensagem
PERTO = {"MG": 0, "SP": 1, "GO": 1}


class TelegramErro(RuntimeError):
    pass


def _valor(v: float | None, sig: str) -> str:
    if v is None:
        return "sigiloso" if sig == "Sim" else "valor não informado"
    if v >= 1e6:
        return f"R$ {v / 1e6:.1f} mi".replace(".", ",")
    if v >= 1e3:
        return f"R$ {v / 1e3:.0f} mil"
    return f"R$ {v:.0f}"


def linha(c: dict[str, Any]) -> str:
    fim = c.get("fim") or ""
    ano = f"/{fim[:4]}" if fim and fim[:4] != str(datetime.now().year) else ""
    prazo = f"{fim[8:10]}/{fim[5:7]}{ano} {fim[11:16]}" if fim else "sem prazo"
    bola = "🟢" if c["uf"] == "MG" else "🔵" if c["uf"] in ("SP", "GO") else "⚪"
    km = f" · {c['dist']} km" if c.get("dist") is not None else ""
    tipos = ", ".join(c.get("tipos", []))
    me = " · ME/EPP" if c.get("me", "").startswith(("Exclusivo", "Cota")) else ""
    return (f"{bola} <b>{html.escape(c['mun'])}-{c['uf']}</b>{km} · {html.escape(c['mod'])} {html.escape(c['num'])}\n"
            f"   {html.escape(tipos)} · {_valor(c.get('vcafe'), c.get('sig', 'Não'))}{me} · fecha {prazo}\n"
            f"   <a href=\"{html.escape(c['link_pncp'])}\">abrir no PNCP</a>")


def mensagens(novas: list[dict[str, Any]], total_abertas: int, data_br: str) -> list[str]:
    if not novas:
        return [f"☕ {data_br}: nenhuma licitação nova de café hoje. {total_abertas} abertas no painel:\n{PAINEL_URL}"]
    ordem = sorted(novas, key=lambda c: (PERTO.get(c["uf"], 2), c.get("fim") or "9999"))
    cab = f"☕ <b>{len(novas)} licitaç{'ão nova' if len(novas) == 1 else 'ões novas'} de café</b> ({data_br})\n"
    rodape = f"\nPainel completo: {PAINEL_URL}"
    out, atual = [], cab
    for c in ordem:
        bloco = "\n" + linha(c) + "\n"
        if len(atual) + len(bloco) + len(rodape) > LIMITE_MSG:
            out.append(atual)
            atual = ""
        atual += bloco
    out.append(atual + rodape)
    return out


def enviar(textos: list[str], client: httpx.Client | None = None) -> None:
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN", ""), os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat:
        raise TelegramErro("TELEGRAM_BOT_TOKEN e/ou TELEGRAM_CHAT_ID não configurados")
    cli = client or httpx.Client(timeout=30)
    for i, t in enumerate(textos, 1):
        r = cli.post(f"https://api.telegram.org/bot{token}/sendMessage",
                     json={"chat_id": chat, "text": t, "parse_mode": "HTML", "disable_web_page_preview": True})
        ok = r.status_code == 200 and r.json().get("ok")
        if not ok:
            # a URL contém o token: nunca registrar a URL, só a resposta
            raise TelegramErro(f"mensagem {i}/{len(textos)} recusada: HTTP {r.status_code} {r.text[:300]}")
        logger.info("Telegram: mensagem {}/{} enviada ({} caracteres)", i, len(textos), len(t))


def descobrir_chats(client: httpx.Client | None = None) -> list[tuple[int, str]]:
    """Chats que mandaram mensagem ao bot recentemente (para descobrir o TELEGRAM_CHAT_ID)."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise TelegramErro("TELEGRAM_BOT_TOKEN não configurado")
    cli = client or httpx.Client(timeout=30)
    r = cli.get(f"https://api.telegram.org/bot{token}/getUpdates")
    if r.status_code != 200 or not r.json().get("ok"):
        raise TelegramErro(f"getUpdates recusado: HTTP {r.status_code} {r.text[:300]}")
    chats: dict[int, str] = {}
    for u in r.json().get("result", []):
        ch = (u.get("message") or u.get("my_chat_member") or {}).get("chat") or {}
        if "id" in ch:
            chats[ch["id"]] = ch.get("first_name") or ch.get("title") or ""
    return list(chats.items())
