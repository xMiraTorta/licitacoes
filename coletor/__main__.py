"""Linha de comando.

    python -m coletor coletar [--destino .] [--forcar] [--sem-busca] [--novas novas.json]
    python -m coletor avisar --novas novas.json [--destino .]
    python -m coletor telegram-chat        # lista chats que falaram com o bot (para o TELEGRAM_CHAT_ID)
    python -m coletor distancias           # recalcula distâncias por estrada (só se a origem mudar)
    python -m coletor reclassificar        # recalcula nível/nota de qualidade no data.json atual (sem PNCP)

Códigos de saída: 0 ok; 2 coleta/publicação bloqueada (dados publicados intactos); 3 falha no aviso.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from loguru import logger
from pydantic import ValidationError

from coletor import coleta, distancias, montar, publicar, telegram
from coletor.pncp import ColetaErro


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="coletor")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("coletar", help="coleta no PNCP e atualiza data.json e index.html")
    c.add_argument("--destino", type=Path, default=Path("."))
    c.add_argument("--forcar", action="store_true", help="publica mesmo se as travas de segurança dispararem")
    c.add_argument("--sem-busca", action="store_true", help="não usa a busca textual (só a listagem)")
    c.add_argument("--novas", type=Path, help="grava aqui as chaves das compras que apareceram pela 1ª vez")
    a = sub.add_parser("avisar", help="envia no Telegram as compras novas da última coleta")
    a.add_argument("--destino", type=Path, default=Path("."))
    a.add_argument("--novas", type=Path, required=True)
    sub.add_parser("telegram-chat", help="mostra os chats que mandaram mensagem ao bot")
    sub.add_parser("distancias", help="recalcula as distâncias por estrada a partir da origem (OSRM)")
    r = sub.add_parser("reclassificar", help="recalcula nível/nota de qualidade no data.json publicado (sem PNCP)")
    r.add_argument("--destino", type=Path, default=Path("."))
    args = ap.parse_args(argv)

    logger.remove()
    logger.add(sys.stderr, level="INFO", backtrace=True, diagnose=False)

    if args.cmd == "coletar":
        try:
            r = coleta.coletar(args.destino, forcar=args.forcar, usar_busca=not args.sem_busca)
        except (ColetaErro, publicar.PublicacaoBloqueada, ValidationError) as e:
            logger.error("COLETA NÃO PUBLICADA (dados anteriores mantidos): {}", e)
            return 2
        if args.novas:
            args.novas.write_text(json.dumps(r.novas), encoding="utf-8")
        return 0

    if args.cmd == "avisar":
        data = publicar.carregar(args.destino / "data.json")
        if not data:
            logger.error("Sem {}: nada para avisar", args.destino / "data.json")
            return 3
        chaves = set(json.loads(args.novas.read_text(encoding="utf-8")))
        por_chave = {c["chave"]: c for c in data.get("compras", [])}
        novas = [por_chave[k] for k in chaves if k in por_chave and not por_chave[k].get("dup_of")]
        try:
            telegram.enviar(telegram.mensagens(novas, data))
        except telegram.TelegramErro as e:
            logger.error("Aviso no Telegram falhou: {}", e)
            return 3
        return 0

    if args.cmd == "reclassificar":
        data = publicar.carregar(args.destino / "data.json")
        if not data:
            logger.error("Sem {}: nada para reclassificar", args.destino / "data.json")
            return 2
        ok = montar.item_gravado_em_andamento
        sairam = [c["chave"] for c in data["compras"] if not any(ok(i) for i in c["itens"])]
        parciais = [c["chave"] for c in data["compras"] if c["chave"] not in sairam and not all(ok(i) for i in c["itens"])]
        if sairam:
            logger.warning("{} compras saem: todos os itens de café cancelados/concluídos no PNCP: {}", len(sairam), sairam)
        if parciais:
            logger.warning("{} compras com parte dos itens fora de andamento; totais só são refeitos na próxima coleta: {}",
                           len(parciais), parciais)
        visiveis = {c["chave"] for c in data["compras"] if not c.get("dup_of")}
        data["compras"] = [c for c in data["compras"] if c["chave"] not in sairam]
        if sairam:  # uma duplicata que apontava para a compra removida volta a aparecer
            montar.marcar_duplicatas(data["compras"], visiveis)
        for c in data["compras"]:
            montar.reclassificar_nivel(c)
        try:
            publicar.gravar(data, args.destino, datetime.fromisoformat(data["gerado_em"]))
        except ValidationError as e:
            logger.error("Reclassificação não gravada (dados publicados intactos): {}", e)
            return 2
        return 0

    if args.cmd == "distancias":
        distancias.calcular()
        return 0

    if args.cmd == "telegram-chat":
        try:
            chats = telegram.descobrir_chats()
        except telegram.TelegramErro as e:
            logger.error("{}", e)
            return 3
        if not chats:
            logger.warning("Nenhum chat recente. Mande um 'oi' ao bot no Telegram e rode de novo.")
        for cid, nome in chats:
            logger.info("chat_id={} ({})", cid, nome)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
