"""Aviso no Telegram das licitações novas. Token e chat vêm de variáveis de ambiente (segredos do GitHub)."""
from __future__ import annotations

import html
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Any
from urllib.parse import quote

import httpx
from loguru import logger

from coletor import cafe, referencia

# O workflow passa o endereço do site (muda se o repositório for renomeado).
PAINEL_URL = os.environ.get("PAINEL_URL") or "https://xmiratorta.github.io/licitacoes/"
LIMITE_MSG = 3900  # Telegram aceita 4096 caracteres por mensagem
PERTO = ("MG", "SP", "GO")


class TelegramErro(RuntimeError):
    pass


DIAS = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")
LINHA = "━━━━━━━━━━━━━━━━━━"


def _num(v: float, casas: int = 0) -> str:
    """Número no padrão brasileiro: 12.345,67."""
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _valor(v: float | None, sig: str) -> str:
    if v is None:
        return "valor sigiloso" if sig != "Não" else "valor não informado"
    if v >= 1e6:
        return f"R$ {_num(v / 1e6, 1)} mi"
    if v >= 1e4:
        return f"R$ {_num(v / 1e3)} mil"
    return f"R$ {_num(v)}"


def _prazo(fim: str | None) -> str:
    if not fim:
        return "sem prazo informado"
    d = datetime.fromisoformat(fim)
    ano = f"/{d.year}" if d.year != datetime.now(ZoneInfo("America/Sao_Paulo")).year else ""
    return f"{DIAS[d.weekday()][:3]} {d:%d/%m}{ano}, {d:%H:%M}"


def _link_monitor(c: dict[str, Any]) -> str:
    return f"{PAINEL_URL}#c={quote(c['chave'], safe='')}"


def cartao(c: dict[str, Any], refs: dict[tuple[str, str], float]) -> str:
    """Bloco de uma licitação: onde, o que pedem, preço x referência do nível, prazo e links."""
    e = html.escape
    km = f" · {_num(c['dist'])} km" if c.get("dist") is not None else ""
    me = " · <i>ME/EPP</i>" if c.get("me", "").startswith(("Exclusivo", "Cota")) else ""
    principal = referencia.item_principal(c)
    pedido = principal or next((i for i in c["itens"] if i["tipo"] != cafe.CESTA), c["itens"][0])
    oque = [pedido["tipo"]]
    if pedido.get("nivel"):
        oque.append(f"nível {pedido['nivel']}")
    if pedido.get("qg"):
        oque.append(f"nota ≥ {_num(pedido['qg'], 1)}")
    outros = [t for t in c.get("tipos", []) if t != pedido["tipo"]]
    vol = f"{'≥ ' if c.get('kg_parcial') else ''}{_num(c['kg'])} kg" if c.get("kg") else "volume não informado"
    linhas = [" · ".join(e(x) for x in oque) + (f" + {e(', '.join(outros).lower())}" if outros else ""), f"{vol} · {_valor(c.get('vcafe'), c.get('sig', 'Não'))}"]
    if principal:
        cmp_ = referencia.comparar(principal, refs)
        preco = f"<b>R$ {_num(principal['rkg'], 2)}/kg</b>"
        if cmp_:
            ref, dif = cmp_
            if abs(dif) < referencia.FAIXA:
                preco += f" ≈ no preço típico do nível (R$ {_num(ref, 2)})"
            else:
                preco += f" {'▲' if dif > 0 else '▼'} {_num(abs(dif) * 100)}% {referencia.rotulo(dif)} do nível (R$ {_num(ref, 2)})"
        linhas.append(preco)
    linhas.append(f"⏰ {_prazo(c.get('fim'))} · {e(c['mod'])} {e(c['num'])} · {e(c.get('plat_f') or c.get('plat', ''))}{me}")
    corpo = "\n".join(linhas)
    return (f"<b>{e(c['mun'])} · {c['uf']}</b>{km}\n{e(_titulo(c.get('orgao', '')))}\n"
            f"<blockquote>{corpo}</blockquote>\n"
            f"<a href=\"{e(_link_monitor(c))}\">Abrir no monitor</a> · <a href=\"{e(c['link_pncp'])}\">PNCP</a>")


_MINUSC = {"de", "da", "do", "das", "dos", "e", "em"}


def _titulo(s: str) -> str:
    """ "MUNICIPIO DE SACRAMENTO" -> "Municipio de Sacramento" (os órgãos vêm em maiúsculas)."""
    if not s.isupper():
        return s
    return " ".join(w.lower() if w.lower() in _MINUSC and k else w.capitalize() for k, w in enumerate(s.split()))


def _cabecalho(data: dict[str, Any]) -> str:
    d = datetime.fromisoformat(data["gerado_em"])
    return f"☕ <b>Monitor de Licitações</b> · Café\n<i>{DIAS[d.weekday()].capitalize()}, {d:%d/%m/%Y}</i>\n"


def mensagens(novas: list[dict[str, Any]], data: dict[str, Any]) -> list[str]:
    """Textos (HTML do Telegram) do aviso diário. Divide em várias mensagens se passar do limite."""
    visiveis = [c for c in data.get("compras", []) if not c.get("dup_of")]
    agora = data["gerado_em"][:16]
    abertas = [c for c in visiveis if not c.get("fim") or c["fim"] >= agora]
    lim3 = (datetime.fromisoformat(data["gerado_em"][:19]) + timedelta(days=3)).isoformat()[:16]
    urgentes = sum(1 for c in abertas if c.get("fim") and c["fim"] <= lim3)
    situacao = f"{_num(len(abertas))} abertas no monitor · {_num(urgentes)} fecham em até 3 dias"
    rodape = f"\n{LINHA}\n<a href=\"{html.escape(PAINEL_URL)}\">Abrir o Monitor de Licitações</a>"
    if not novas:
        return [f"{_cabecalho(data)}\nNenhuma licitação nova de café hoje.\n{situacao}\n{rodape}"]
    refs = referencia.referencias(visiveis)
    valor = sum(c.get("vcafe") or 0 for c in novas)
    kg = sum(c.get("kg") or 0 for c in novas)
    resumo = (f"<b>{len(novas)} licitaç{'ão nova' if len(novas) == 1 else 'ões novas'}</b>"
              + (f" · {_valor(valor, 'Não')}" if valor else "") + (f" · {_num(kg)} kg" if kg else ""))
    cab = f"{_cabecalho(data)}\n{resumo}\n{situacao}\n"
    perto = sorted((c for c in novas if c["uf"] in PERTO), key=lambda c: (c.get("fim") or "9999", c["chave"]))
    demais = sorted((c for c in novas if c["uf"] not in PERTO), key=lambda c: (c.get("fim") or "9999", c["chave"]))
    nota = ("\n<i>Preço típico: o R$/kg do meio nas licitações abertas do mesmo tipo e nível de exigência "
            "(comparação entre licitações, não custo).</i>") if any(referencia.item_principal(c) for c in novas) else ""
    fim_txt = rodape + nota
    out: list[str] = []
    atual = cab
    for titulo, grupo in (("📍 <b>PERTO DE VOCÊ</b> · MG, SP e GO", perto), ("🗺 <b>DEMAIS ESTADOS</b>", demais)):
        secao = f"\n{LINHA}\n{titulo}\n"
        for i, c in enumerate(grupo):
            bloco = "\n" + cartao(c, refs) + "\n"
            cabeca = secao if i == 0 else ""
            if len(atual) + len(cabeca) + len(bloco) + len(fim_txt) > LIMITE_MSG:
                out.append(atual.rstrip())
                atual = "<i>(continuação)</i>\n" + secao.lstrip("\n")
                cabeca = ""
            atual += cabeca + bloco
    out.append(atual + fim_txt)
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
