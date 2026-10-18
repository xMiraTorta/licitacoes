"""Linha de comando.

    python -m coletor coletar [--destino .] [--forcar] [--sem-busca] [--novas novas.json]
    python -m coletor avisar --novas novas.json [--destino .]
    python -m coletor telegram-chat        # lista chats que falaram com o bot (para o TELEGRAM_CHAT_ID)
    python -m coletor distancias           # recalcula distâncias por estrada (só se a origem mudar)
    python -m coletor reclassificar        # recalcula nível/nota de qualidade no data.json atual (sem PNCP)
    python -m coletor editais [--todas] [--textos DIR]   # lê edital/TR das compras do data.json atual
    python -m coletor mapa                 # baixa o contorno dos estados (IBGE) e embute no index.html (raramente)

Códigos de saída: 0 ok; 2 coleta/publicação bloqueada (dados publicados intactos); 3 falha no aviso.
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from loguru import logger
from pydantic import ValidationError

from coletor import cafe, coleta, distancias, edital, mapa, montar, publicar, telegram
from coletor.pncp import PNCP, ColetaErro


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
    m = sub.add_parser("mapa", help="baixa o contorno dos estados do IBGE e embute no index.html")
    m.add_argument("--destino", type=Path, default=Path("."))
    r = sub.add_parser("reclassificar", help="recalcula nível/nota de qualidade no data.json publicado (sem PNCP)")
    r.add_argument("--destino", type=Path, default=Path("."))
    e = sub.add_parser("editais", help="lê o edital/TR das compras do data.json publicado e grava o que achou")
    e.add_argument("--destino", type=Path, default=Path("."))
    e.add_argument("--todas", action="store_true", help="relê todas (não só as nunca lidas, alteradas ou com falha)")
    e.add_argument("--textos", type=Path, help="grava aqui o texto extraído de cada compra (revisão manual)")
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
        # Itens que não valem mais: fora de andamento no PNCP ou fora do escopo (só café torrado).
        vale = lambda i: montar.item_gravado_em_andamento(i) and i["tipo"] in cafe.TIPOS_TORRADOS  # noqa: E731
        visiveis = {c["chave"] for c in data["compras"] if not c.get("dup_of")}
        sairam = []
        for c in data["compras"]:
            antes = len(c["itens"])
            c["itens"] = [i for i in c["itens"] if vale(i)]
            if not c["itens"]:
                sairam.append(c["chave"])
            elif len(c["itens"]) != antes:
                c.update(montar.agregar(c["itens"]))  # totais refeitos só com os itens que ficaram
        if sairam:
            logger.warning("{} compras saem (sem item de café torrado em andamento): {}", len(sairam), sairam)
            data["compras"] = [c for c in data["compras"] if c["chave"] not in sairam]
            montar.marcar_duplicatas(data["compras"], visiveis)  # duplicata que apontava para uma removida volta
        for c in data["compras"]:
            montar.reclassificar_nivel(c)
            c.update(montar.agregar(c["itens"]))
            n, _, ano = c["num"].rpartition("/")  # "114/2026/2026" (ano repetido em coletas antigas) -> "114/2026"
            c["num"] = montar.numero(n, ano) if n else c["num"]
        try:
            publicar.gravar(data, args.destino, datetime.fromisoformat(data["gerado_em"]))
        except ValidationError as e:
            logger.error("Reclassificação não gravada (dados publicados intactos): {}", e)
            return 2
        return 0

    if args.cmd == "editais":
        data = publicar.carregar(args.destino / "data.json")
        if not data:
            logger.error("Sem {}: nada para ler", args.destino / "data.json")
            return 2
        p = PNCP()
        versoes: dict[str, str] = {}

        def versao(k: str) -> None:  # data da última alteração no PNCP (a coleta diária relê se mudar)
            try:
                versoes[k] = ((p.compra(k) or {}).get("dataAtualizacaoGlobal")) or ""
            except ColetaErro as erro:
                logger.warning("{}: versão no PNCP não consultada ({}); a coleta diária vai reler", k, erro)
        with ThreadPoolExecutor(max_workers=3) as ex:
            list(ex.map(versao, [c["chave"] for c in data["compras"]]))
        edital.ler_varias(p, data["compras"], versoes, datetime.now(coleta.TZ).strftime("%Y-%m-%d"),
                          limite=None, todas=args.todas, salvar_em=args.textos)
        data["editais_lidos"] = sum(1 for c in data["compras"] if c.get("edital_lido"))
        try:
            publicar.gravar(data, args.destino, datetime.fromisoformat(data["gerado_em"]))
        except ValidationError as erro:
            logger.error("Leitura dos editais não gravada (dados publicados intactos): {}", erro)
            return 2
        return 0
    if args.cmd == "mapa":
        mapa.gerar(args.destino)
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
