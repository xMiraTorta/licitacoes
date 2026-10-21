"""Aviso diário no Telegram: licitações novas de café, em HTML do Telegram, curto e direto para ler no celular.

Token e chat vêm de variáveis de ambiente (segredos do GitHub). Regras de texto (pedido do dono em 18/10/2026):
frases curtas, sem linhas decorativas, sem exclamação, no máximo um emoji por mensagem, só o que ajuda a decidir
se vale entrar na licitação. Preço típico e margem seguem `referencia` e `custos` (mesma regra do site).
"""
from __future__ import annotations

import html
import os
import time
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx
from loguru import logger

from coletor import cafe, custos, mercado, referencia

# O workflow passa o endereço do site (muda se o repositório for renomeado).
PAINEL_URL = os.environ.get("PAINEL_URL") or "https://xmiratorta.github.io/monitor-licitacoes/"  # os workflows passam a URL certa pelo nome do repositório
LIMITE_MSG = 3900  # Telegram aceita 4096 caracteres por mensagem
PERTO = ("MG", "SP", "GO")
DIAS = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")
_FUSO = ZoneInfo("America/Sao_Paulo")
_CONT = "<i>Continuação (§/§)</i>\n"  # "§" vira o número da mensagem quando se sabe quantas são
_RESERVA_CONT = 4  # folga para os números que substituem "§" em "(2/3)"
_NOTA_TIPICO = "<i>Preço típico: o R$/kg do meio entre as licitações abertas do mesmo tipo e nível.</i>"


class TelegramErro(RuntimeError):
    pass


def _num(v: float, casas: int = 0) -> str:
    """Número no padrão brasileiro: 12.345,67."""
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _plural(n: int, um: str, varios: str) -> str:
    return f"{_num(n)} {um if n == 1 else varios}"


def _e(x: str) -> str:
    """Escape para texto do Telegram (fora de atributo): aspas e apóstrofo ficam como estão."""
    return html.escape(x, quote=False)


def _valor(v: float | None, sig: str) -> str:
    if v is None:
        return "valor sigiloso" if sig != "Não" else "valor não informado"
    if v >= 999_500:  # 999.700 vira "R$ 1,0 mi", não "R$ 1.000 mil"
        return f"R$ {_num(v / 1e6, 1)} mi"
    if v >= 1e4:
        return f"R$ {_num(v / 1e3)} mil"
    return f"R$ {_num(v)}"


def _prazo(fim: str | None) -> str:
    """"seg 19/10, 08:00" (com o ano só se não for o atual) ou "não informado"."""
    if not fim:
        return "não informado"
    d = datetime.fromisoformat(fim)
    ano = f"/{d.year}" if d.year != datetime.now(_FUSO).year else ""
    return f"{DIAS[d.weekday()][:3]} {d:%d/%m}{ano}, {d:%H:%M}"


def _link_monitor(c: dict[str, Any]) -> str:
    return f"{PAINEL_URL}#c={quote(c['chave'], safe='')}"


_MINUSC = {"de", "da", "do", "das", "dos", "e", "em"}


def _titulo(s: str) -> str:
    """ "MUNICIPIO DE SACRAMENTO" -> "Municipio de Sacramento" (os órgãos vêm em maiúsculas)."""
    if not s.isupper():
        return s
    return " ".join(w.lower() if w.lower() in _MINUSC and k else w.capitalize() for k, w in enumerate(s.split()))


def _linha_preco(i: dict[str, Any], refs: dict[tuple[str, str], float]) -> str:
    """R$/kg do órgão e, havendo referência, a diferença para o preço típico do nível (▲ acima, ▼ abaixo, ≈ no típico)."""
    preco = f"<b>R$ {_num(i['rkg'], 2)}/kg</b>"
    cmp_ = referencia.comparar(i, refs)
    if not cmp_:
        return preco
    ref, dif = cmp_
    if abs(dif) < referencia.FAIXA:
        return f"{preco} ≈ no preço típico do nível (R$ {_num(ref, 2)})"
    return f"{preco} {'▲' if dif > 0 else '▼'} {_num(abs(dif) * 100)}% {referencia.rotulo(dif)} do nível (R$ {_num(ref, 2)})"


def _linha_margem(mg: dict[str, Any]) -> str:
    pct = mg["margem_pct"] * 100
    custo = f"custo ~R$ {_num(mg['custo'], 2)}/kg com frete e impostos"
    if pct < 0:
        return f"Margem estimada ~{_num(pct)}%: prejuízo ao preço do órgão ({custo})"
    return f"Margem estimada ~{_num(pct)}% ({custo})"


def cartao(c: dict[str, Any], refs: dict[tuple[str, str], float]) -> str:
    """Bloco de uma licitação: onde e órgão, o que pedem, volume e valor, R$/kg x preço típico, margem, marcas,
    prazo, modalidade e plataforma, links. Só o que decide; nada de enfeite."""
    km = f" · {_num(c['dist'])} km" if c.get("dist") is not None else ""
    principal = referencia.item_principal(c)
    pedido = principal or next((i for i in c["itens"] if i["tipo"] != cafe.CESTA), c["itens"][0])
    # sem item com R$/kg: o maior nível pedido na compra (mesma regra do site)
    nivel = pedido.get("nivel") if principal else next((n for n in reversed(cafe.NIVEIS) if n in (c.get("niveis") or [])), None)
    oque = [pedido["tipo"]]
    if nivel:
        oque.append(f"nível {nivel}" + (" (pelo edital)" if "*" in (pedido.get("cat") or "") else ""))
    if pedido.get("qg"):
        oque.append(f"nota ≥ {_num(pedido['qg'], 1)}")
    outros = [t.lower() for t in c.get("tipos", []) if t != pedido["tipo"]]
    linhas = [_e(" · ".join(oque)) + (f" + {_e(', '.join(outros))}" if outros else "")]
    vol = f"{'≥ ' if c.get('kg_parcial') else ''}{_num(c['kg'])} kg" if c.get("kg") else "volume não informado"
    linhas.append(f"{vol} · {_valor(c.get('vcafe'), c.get('sig', 'Não'))}")
    if principal:
        linhas.append(_linha_preco(principal, refs))
        if (mg := custos.margem(c, principal, mercado.carregar())) is not None:
            linhas.append(_linha_margem(mg))
    if c.get("marcas"):
        linhas.append("Marcas de referência: " + _e(", ".join(c["marcas"][:4])) + (" e outras" if len(c["marcas"]) > 4 else ""))
    me = " · ME/EPP" if (c.get("me") or "").startswith(("Exclusivo", "Cota")) else ""
    linhas.append(f"Prazo: {_prazo(c.get('fim'))} · {_e(c['mod'])} {_e(c['num'])} · {_e(c.get('plat_f') or c.get('plat') or '')}{me}")
    corpo = "\n".join(linhas)
    return (f"<b>{_e(c['mun'])} · {_e(c['uf'])}</b>{km}\n{_e(_titulo(c.get('orgao') or ''))}\n"
            f"<blockquote>{corpo}</blockquote>\n"
            f"<a href=\"{html.escape(_link_monitor(c))}\">Abrir no monitor</a> · <a href=\"{html.escape(c['link_pncp'])}\">PNCP</a>")


def _situacao(visiveis: list[dict[str, Any]], gerado_em: str) -> str:
    """"244 abertas no monitor · 12 fecham em até 3 dias"."""
    agora = gerado_em[:16]
    abertas = [c for c in visiveis if not c.get("fim") or c["fim"] >= agora]
    lim3 = (datetime.fromisoformat(gerado_em[:19]) + timedelta(days=3)).isoformat()[:16]
    urgentes = sum(1 for c in abertas if c.get("fim") and c["fim"] <= lim3)
    fecham = "nenhuma fecha" if not urgentes else _plural(urgentes, "fecha", "fecham")
    return f"{_plural(len(abertas), 'aberta', 'abertas')} no monitor · {fecham} em até 3 dias"


def _cabecalho(data: dict[str, Any]) -> str:
    d = datetime.fromisoformat(data["gerado_em"])
    return f"☕ <b>Monitor de Licitações</b> · {DIAS[d.weekday()].capitalize()}, {d:%d/%m/%Y}"


def mensagens(novas: list[dict[str, Any]], data: dict[str, Any]) -> list[str]:
    """Textos (HTML do Telegram) do aviso diário. Sem novas: uma linha. Com novas: cabeçalho, resumo, licitações
    perto (MG, SP e GO) e depois as demais, cada grupo por prazo. Divide em várias mensagens se passar do limite;
    a nota do preço típico vai só na primeira e o link do monitor fecha a última."""
    visiveis = [c for c in data.get("compras", []) if not c.get("dup_of")]
    situacao = _situacao(visiveis, data["gerado_em"])
    link = f"<a href=\"{html.escape(PAINEL_URL)}\">Abrir o monitor</a>"
    if not novas:
        return [f"Nenhuma licitação nova de café hoje · {situacao} · {link}"]
    refs = referencia.referencias(visiveis)
    valor = sum(c.get("vcafe") or 0 for c in novas)
    kg = sum(c.get("kg") or 0 for c in novas)
    resumo = (f"<b>{_plural(len(novas), 'licitação nova', 'licitações novas')}</b>"
              + (f" · {_valor(valor, 'Não')}" if valor else "") + (f" · {_num(kg)} kg" if kg else ""))
    cab = f"{_cabecalho(data)}\n{resumo}\n{situacao}\n"
    por_prazo = lambda c: (c.get("fim") or "9999", c["chave"])  # noqa: E731
    perto = sorted((c for c in novas if c["uf"] in PERTO), key=por_prazo)
    demais = sorted((c for c in novas if c["uf"] not in PERTO), key=por_prazo)
    compara = any((p := referencia.item_principal(c)) and referencia.comparar(p, refs) for c in novas)
    nota = f"\n{_NOTA_TIPICO}" if compara else ""
    fim = f"\n{link}"
    out: list[str] = []
    atual = cab
    for titulo, grupo in (("<b>Perto de você</b> · MG, SP e GO", perto), ("<b>Demais estados</b>", demais)):
        for i, c in enumerate(grupo):
            bloco = "\n" + cartao(c, refs) + "\n"
            cabeca = f"\n{titulo}\n" if i == 0 else ""
            rodape = (nota if not out else "") + fim
            if len(atual) + len(cabeca) + len(bloco) + len(rodape) + _RESERVA_CONT > LIMITE_MSG:
                out.append(atual.rstrip() + (nota if not out else ""))
                atual, cabeca = _CONT, f"\n{titulo}\n"  # repete o grupo ao continuar no meio dele
            atual += cabeca + bloco
    out.append(atual + (nota if not out else "") + fim)
    total = len(out)
    return [m.replace("(§/§)", f"({k}/{total})") for k, m in enumerate(out, 1)]


# O Telegram aceita ~1 mensagem por segundo no mesmo chat; acima disso responde 429 com retry_after.
PAUSA = 1.1
TENTATIVAS_429 = 3
ESPERA_MAX = 60.0


def enviar(textos: list[str], client: httpx.Client | None = None, pausa: float = PAUSA) -> None:
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN", ""), os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat:
        raise TelegramErro("TELEGRAM_BOT_TOKEN e/ou TELEGRAM_CHAT_ID não configurados")
    cli = client or httpx.Client(timeout=30)
    for i, t in enumerate(textos, 1):
        if i > 1:
            time.sleep(pausa)
        for tentativa in range(1, TENTATIVAS_429 + 1):
            r = cli.post(f"https://api.telegram.org/bot{token}/sendMessage",
                         json={"chat_id": chat, "text": t, "parse_mode": "HTML", "disable_web_page_preview": True})
            if r.status_code != 429 or tentativa == TENTATIVAS_429:
                break
            try:
                espera = min(ESPERA_MAX, float(((r.json() or {}).get("parameters") or {}).get("retry_after") or 5))
            except ValueError:  # 429 com página HTML (Cloudflare) em vez de JSON: espera padrão
                espera = 5.0
            logger.warning("Telegram pediu para esperar {:.0f}s (mensagem {}/{}, tentativa {})", espera, i, len(textos), tentativa)
            time.sleep(espera)
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
