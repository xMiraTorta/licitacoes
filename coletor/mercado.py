"""Preço do café verde por nível de exigência, atualizado toda semana (pedido do dono em 18/10/2026).

Fontes públicas, lidas com identificação honesta de script (pesquisa de 18/10/2026):
- CEPEA/ESALQ (licença CC BY-NC 4.0): indicador do arábica tipo 6 bebida dura para melhor e do robusta,
  R$/saca de 60 kg, posto São Paulo.
- Escritório Carvalhaes (Santos): 8 classes de bebida do arábica (CD finos a consumo riada), R$/saca de 60,5 kg,
  porta de armazém.

Não existe cotação pública de "café para Superior": o preço de cada nível é uma ESTIMATIVA pela receita de blend
abaixo, derivada das Resoluções SAA-SP 28, 30 e 31/2007 (normas do PQC/ABIC). O café da própria fazenda entra pelo
preço que o dono receberia vendendo (custo de oportunidade), que é o mesmo mercado.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

from coletor.arquivos import gravar_atomico
from typing import Any

import httpx
from loguru import logger

BASE = Path(__file__).with_name("mercado.json")
CEPEA = "https://www.cepea.org.br/br/indicador/cafe.aspx"
CARVALHAES = "https://www.carvalhaes.com.br/cotacoes/cotacoes.asp"
UA = "monitor-licitacoes-cafe/1.0 (+https://xmiratorta.github.io/licitacoes/)"
SACA_CARVALHAES = 60.5  # kg

# Classe da Carvalhaes -> começo do nome na tabela
CLASSES = {"cd_finos": "CD Finos", "finos": "Finos a Extra-Finos", "boa_qualidade": "Boa Qualidade",
           "duro_fraco": "Duros com x", "riados": "Riados", "rio": "Rio", "consumo_dura": "Consumo interno: Dura",
           "consumo_riada": "Consumo interno: Riadas"}

# Receita de cada nível (frações do blend). "min" = blend mais barato que a norma aceita; "max" = café mais caro
# usual no nível. Conilon pelo indicador do robusta CEPEA (o conilon 7/8 de Vitória não tem fonte aberta a script).
RECEITAS: dict[str, dict[str, Any]] = {
    "Tradicional": {
        "min": {"rio": 0.6, "robusta": 0.4}, "max": {"consumo_dura": 1.0},
        "regra": "Res. SAA-SP 28/2007: até tipo 8, bebida mole a rio (sem rio zona), até 20% de grãos pretos/verdes/ardidos; "
                 "aceita conilon sem predominar (40% é premissa nossa, a norma não fixa)."},
    "Superior": {
        "min": {"duro_fraco": 0.85, "robusta": 0.15}, "max": {"boa_qualidade": 1.0},
        "regra": "Res. SAA-SP 30/2007: arábica tipos 2 a 6, bebida dura ou mole, até 15% de conilon, até 10% de defeitos."},
    "Gourmet/especial": {
        "min": {"finos": 1.0}, "max": {"cd_finos": 1.0},
        "regra": "Res. SAA-SP 31/2007: 100% arábica, bebida apenas mole a estritamente mole, tipos 2 a 4, sem defeitos "
                 "(pode exigir catação, que tira peso: não incluída)."},
}
RECEITAS["Sem categoria"] = {**RECEITAS["Tradicional"], "regra": "Edital sem exigência: o blend mais simples que passa "
                             "no mínimo legal (nota 4,5, Portaria MAPA 570/2022), igual ao Tradicional."}


def _texto(pagina: str) -> str:
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", pagina, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))


def _num(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


PRECO = r"\d{1,3}(?:\.\d{3})*,\d{2}"  # "963,28", "1.601,25", "12.345,67": com ou sem ponto de milhar (abaixo de R$ 1.000 acontece)


def ler_cepea(pagina: str) -> dict[str, dict[str, Any]]:
    t = _texto(pagina)
    out = {}
    for chave, titulo in (("arabica", "INDICADOR DO CAFÉ ARÁBICA"), ("robusta", "INDICADOR DO CAFÉ ROBUSTA")):
        m = re.search(re.escape(titulo) + rf".{{0,120}}?(\d{{2}}/\d{{2}}/\d{{4}}) ({PRECO})", t)
        if not m:
            raise ValueError(f"CEPEA: {titulo} não encontrado na página")
        d, mes, a = m.group(1).split("/")
        out[chave] = {"data": f"{a}-{mes}-{d}", "saca60": _num(m.group(2))}
    return out


def ler_carvalhaes(pagina: str) -> dict[str, Any]:
    t = _texto(pagina)
    classes, data = {}, ""
    for chave, nome in CLASSES.items():
        m = re.search(re.escape(nome) + rf"[^/]{{0,60}}?(\d{{2}}/\d{{2}}/\d{{2}}) ({PRECO})/({PRECO})", t)
        if not m:
            raise ValueError(f"Carvalhaes: classe '{nome}' não encontrada na página")
        d, mes, a = m.group(1).split("/")
        data = max(data, f"20{a}-{mes}-{d}")
        # saca de 60,5 kg -> 60 kg, para somar com o CEPEA
        classes[chave] = [round(_num(m.group(i)) * 60 / SACA_CARVALHAES, 2) for i in (2, 3)]
    return {"data": data, "saca60": classes}


def niveis(cepea: dict[str, Any], carv: dict[str, Any]) -> dict[str, Any]:
    """R$/saca 60 kg e R$/kg verde (min, médio, max) de cada nível pela receita."""
    def valor(fonte: str, lado: int) -> float:
        return cepea["robusta"]["saca60"] if fonte == "robusta" else carv["saca60"][fonte][lado]

    out = {}
    for nivel, r in RECEITAS.items():
        smin = round(sum(f * valor(k, 0) for k, f in r["min"].items()), 2)
        smax = round(sum(f * valor(k, 1) for k, f in r["max"].items()), 2)
        out[nivel] = {"saca60_min": smin, "saca60_max": smax, "kg_min": round(smin / 60, 2), "kg_max": round(smax / 60, 2),
                      "kg_medio": round((smin + smax) / 120, 2), "receita_min": r["min"], "receita_max": r["max"],
                      "regra": r["regra"]}
    return out


def atualizar(hoje: str, cliente: httpx.Client | None = None, destino: Path = BASE) -> dict[str, Any]:
    """Baixa CEPEA e Carvalhaes e grava mercado.json. Erro de download ou de leitura levanta exceção sem gravar
    (fica o arquivo anterior, com a data dele)."""
    cliente = cliente or httpx.Client(timeout=30, headers={"User-Agent": UA}, follow_redirects=True)
    r = cliente.get(CARVALHAES)
    r.raise_for_status()
    carv = ler_carvalhaes(r.content.decode("latin-1", "replace"))
    # CEPEA (só o robusta entra na receita) bloqueia os servidores do GitHub (403 do Cloudflare, 18/10/2026):
    # sem ele, vale o último indicador gravado, com a data dele, e o resto atualiza.
    try:
        r = cliente.get(CEPEA)
        r.raise_for_status()
        cepea = ler_cepea(r.content.decode("utf-8", "replace"))
    except (httpx.HTTPError, ValueError) as e:
        anterior = json.loads(destino.read_text(encoding="utf-8")).get("cepea") if destino.exists() else None
        if not anterior or "robusta" not in anterior:
            raise
        logger.warning("CEPEA indisponível ({}); usado o indicador anterior de {}", e, anterior["robusta"]["data"])
        cepea = anterior
    nv = niveis(cepea, carv)
    dados = {"atualizado_em": hoje, "perda_torra": 0.18, "cepea": cepea, "carvalhaes": carv, "niveis": nv,
             "historico": historico(destino, carv["data"], cepea, nv),
             "fontes": {"cepea": CEPEA + " (CC BY-NC 4.0)", "carvalhaes": CARVALHAES}}
    gravar_atomico(destino, json.dumps(dados, ensure_ascii=False, indent=1) + "\n")  # nunca um JSON pela metade
    logger.info("Mercado do café verde ({}): arábica CEPEA R$ {}, robusta R$ {}; níveis {}", hoje,
                cepea["arabica"]["saca60"], cepea["robusta"]["saca60"],
                {n: (v["saca60_min"], v["saca60_max"]) for n, v in dados["niveis"].items()})
    return dados


HISTORICO_MAX = 400  # ~1,5 ano de dias úteis


def historico(destino: Path, data: str, cepea: dict[str, Any], nv: dict[str, Any]) -> list[dict[str, Any]]:
    """Uma linha por data de cotação (R$/saca médio de cada nível e os indicadores do CEPEA), para o site
    mostrar a evolução do café verde. A cotação do dia substitui a entrada da mesma data."""
    anterior = json.loads(destino.read_text(encoding="utf-8")).get("historico", []) if destino.exists() else []
    linha = {"data": data, "arabica": (cepea.get("arabica") or {}).get("saca60"), "robusta": (cepea.get("robusta") or {}).get("saca60"),
             "niveis": {n: round((v["saca60_min"] + v["saca60_max"]) / 2, 2) for n, v in nv.items()}}
    hist = [h for h in anterior if isinstance(h, dict) and h.get("data") and h["data"] != data]
    hist.append(linha)
    hist.sort(key=lambda h: h["data"])
    return hist[-HISTORICO_MAX:]


def carregar() -> dict[str, Any]:
    return json.loads(BASE.read_text(encoding="utf-8")) if BASE.exists() else {}
