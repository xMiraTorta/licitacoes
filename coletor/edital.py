"""Leitura dos documentos da compra no PNCP (edital, termo de referência, anexos) para completar o que a
descrição do item não diz: categoria/qualidade do café, nota mínima, exigências, marcas de referência e prazo
de entrega. O edital é a fonte principal; a descrição do item no PNCP é a secundária.

Formatos lidos: PDF com texto, DOCX, ODT, RTF, TXT e ZIP (inclusive ZIP dentro de ZIP). PDF escaneado
(só imagem) e DOC antigo (Word 97) não têm texto extraível: ficam com status explicando isso.
"""
from __future__ import annotations

import html
import io
import re
import zipfile
import zlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

from coletor import cafe, marcas, montar
from coletor.pncp import PNCP, ColetaErro

MAX_DOCS = 6  # documentos por compra (os primeiros pela ordem de prioridade)
MAX_BYTES = 60 * 1024 * 1024
MAX_PAGINAS = 400
# Ordem: onde a especificação do café costuma estar. tipoDocumentoId do PNCP: 4 Termo de Referência, 2 Edital,
# 1 Aviso de contratação direta, 5 Anexo/Planilha (varia), 7 Estudo Técnico Preliminar.
PRIORIDADE = {4: 0, 2: 1, 1: 2, 5: 3, 6: 3, 7: 5}

STATUS_LIDO = "lido"
STATUS_SEM_DOCS = "sem documentos no PNCP"
STATUS_SEM_TEXTO = "documentos sem texto legível (PDF escaneado, .rar ou formato não suportado)"
STATUS_SEM_CAFE = "documentos lidos, sem trecho sobre o café"
STATUS_FALHA = "falha ao baixar os documentos"


@dataclass
class Leitura:
    status: str
    docs: list[str] = field(default_factory=list)  # "seq:título" dos documentos lidos
    trechos: list[str] = field(default_factory=list)
    cat: str = ""
    qg: float | None = None
    tags: list[str] = field(default_factory=list)
    marcas: list[str] = field(default_factory=list)
    prazo_entrega: str = ""
    itens: dict[Any, str] = field(default_factory=dict)  # número do item -> trecho do edital sobre ele


# ---------------------------------------------------------------- texto dos arquivos
def _xml_texto(xml: str) -> str:
    xml = re.sub(r"</w:p>|</text:p>|</text:h>|<w:br/>|<w:tab/>", "\n", xml)
    xml = re.sub(r"</w:tc>|</table:table-cell>", " | ", xml)
    return html.unescape(re.sub(r"<[^>]+>", "", xml))


def _pdf_texto(dados: bytes) -> str:
    from pypdf import PdfReader

    try:
        leitor = PdfReader(io.BytesIO(dados))
        partes = []
        for k, pg in enumerate(leitor.pages):
            if k >= MAX_PAGINAS:
                break
            try:
                partes.append(pg.extract_text() or "")
            except Exception as e:  # página defeituosa: registra e segue com as outras  # noqa: BLE001
                logger.warning("PDF: página {} ilegível: {}", k + 1, e)
        return "\n".join(partes)
    except Exception as e:  # PDF corrompido/criptografado: sem texto (status explica)  # noqa: BLE001
        logger.warning("PDF ilegível: {}", e)
        return ""


def texto_de(nome: str, dados: bytes, profundidade: int = 0) -> str:
    """Texto de um arquivo pelo conteúdo (o título no PNCP nem sempre tem a extensão certa)."""
    n = nome.lower()
    if dados[:5] == b"%PDF-":
        return _pdf_texto(dados)
    if dados[:2] == b"PK":
        try:
            z = zipfile.ZipFile(io.BytesIO(dados))
        except zipfile.BadZipFile:
            return ""
        try:
            nomes = z.namelist()
            if "word/document.xml" in nomes:  # DOCX
                return _xml_texto(z.read("word/document.xml").decode("utf-8", "ignore"))
            if "content.xml" in nomes and any(x.startswith("META-INF") for x in nomes):  # ODT
                return _xml_texto(z.read("content.xml").decode("utf-8", "ignore"))
            if profundidade >= 2:
                return ""
            partes = []
            for info in z.infolist():
                if info.is_dir() or info.file_size > MAX_BYTES:
                    continue
                partes.append(texto_de(info.filename, z.read(info), profundidade + 1))
            return "\n".join(p for p in partes if p)
        except (RuntimeError, NotImplementedError, zipfile.BadZipFile, zlib.error) as e:  # protegido por senha/corrompido
            logger.warning("ZIP {} ilegível: {}", nome, e)
            return ""
    if dados[:4] == b"\xd0\xcf\x11\xe0":  # .doc antigo (Word 97-2003): o texto fica em blocos UTF-16 ou cp1252
        u16 = [b.decode("utf-16-le", "ignore") for b in re.findall(rb"(?:[\x20-\x7e\xc0-\xff\r\n]\x00){30,}", dados)]
        if sum(map(len, u16)) > 500:
            return "\n".join(u16)
        return "\n".join(b.decode("cp1252", "ignore") for b in re.findall(rb"[\x20-\x7e\xc0-\xff\r\n]{30,}", dados))
    if dados[:5] == b"{\\rtf":
        t = dados.decode("latin-1", "ignore")
        t = re.sub(r"\\'([0-9a-f]{2})", lambda m: bytes.fromhex(m.group(1)).decode("cp1252", "ignore"), t)
        return re.sub(r"\\[a-z]+-?\d* ?|[{}]", " ", t)
    if n.endswith((".txt", ".csv", ".html", ".htm")):
        return html.unescape(re.sub(r"<[^>]+>", " ", dados.decode("utf-8", "ignore")))
    return ""  # DOC antigo, imagem, planilha binária


# ---------------------------------------------------------------- trechos sobre o café
# Palavras que indicam especificação do produto café (e não "café da manhã", "coffee break", "pó de café" de limpeza).
_PISTAS = re.compile(r"torrad|moid|\bgraos?\b|abic|pureza|superior|tradicional|gourmet|extra ?forte|qualidade|sensorial|"
                     r"vacuo|almofada|embalage|arabica|conilon|robusta|\bpqc\b|bebida|torra|moagem|marca|similar|equivalente|"
                     r"validade|\b\d+ ?(g|gr|gramas|kg)\b")
_CAFE = re.compile(r"\bcafe\b")
_FORA = re.compile(r"cafe da manha|coffee ?-?break|cafe colonial|cafeteira|garrafa termica")
_LINHA_TABELA = re.compile(r"\|\s*\d{1,6}\s*\|")  # começo da próxima linha de uma tabela de itens


@dataclass
class Trecho:
    inicio: int
    texto: str
    pistas: int
    antes: str  # o que vem logo antes de "café" (para achar o número do item)


def trechos_cafe(t: str) -> list[Trecho]:
    """Trechos (texto já normalizado) em volta de cada "café" com cara de especificação. Cada trecho vai até a
    próxima linha da tabela de itens ou ~650 caracteres, para não misturar dois itens."""
    out: list[Trecho] = []
    ultimo_fim = -1
    for m in _CAFE.finditer(t):
        if m.start() < ultimo_fim:
            continue  # "café" dentro do trecho anterior
        fim = min(len(t), m.end() + 650)
        if (prox := _LINHA_TABELA.search(t, m.end() + 20, fim)):
            fim = prox.start()
        j = t[m.start():fim]
        if _FORA.search(j[:60]) and not re.search(r"torrad|moid", j[:200]):
            continue
        pistas = len(set(x.group(0) for x in _PISTAS.finditer(j)))
        if pistas >= 3 and re.search(r"torrad|moid|\bgraos?\b|\bpo\b", j):
            out.append(Trecho(m.start(), j.strip(), pistas, t[max(0, m.start() - 60):m.start()]))
            ultimo_fim = fim
    return out


def _unicos(ts: list[Trecho], maximo: int) -> list[Trecho]:
    """Sem repetição (o mesmo texto costuma vir no edital, no TR e no ETP), dos mais ricos em pistas."""
    vistos, out = set(), []
    for tr in sorted(ts, key=lambda x: (-x.pistas, x.inicio)):
        chave = re.sub(r"[^a-z]", "", tr.texto[:220])
        if chave in vistos:
            continue
        vistos.add(chave)
        out.append(tr)
        if len(out) >= maximo:
            break
    return out


def _do_item(ts: list[Trecho], item: dict[str, Any]) -> list[Trecho]:
    """Trechos de um item: pelo número na tabela; senão pelo tipo (grão x moído); senão todos."""
    n = item.get("n")
    if n is not None:
        rx = re.compile(rf"(?:\|\s*|\bitem\s*(?:n\W{{0,2}})?|\blote\s*\d+\D{{0,6}})0*{n}\s*(?:\||-|\.|\)|:)?\s*$")
        por_num = [x for x in ts if rx.search(x.antes)]
        if por_num:
            return por_num
    grao = item["tipo"] == cafe.GRAO
    por_tipo = [x for x in ts if bool(re.search(r"\bgraos?\b", x.texto[:200])) and not re.search(r"moid", x.texto[:200])] if grao \
        else [x for x in ts if re.search(r"moid|\bpo\b", x.texto[:200])]
    return por_tipo or ts


_PRAZO = re.compile(r"prazo (?:maximo )?(?:de|para) (?:a )?entrega[^.;]{0,80}?(\d{1,3})\s*(?:\([a-z ]+\)\s*)?"
                    r"(dias? (?:uteis|corridos)|dias|horas)")


def prazo_entrega(t: str) -> str:
    m = _PRAZO.search(t)
    return f"{int(m.group(1))} {m.group(2).replace('uteis', 'úteis')}" if m else ""


def analisar(texto: str, itens: list[dict[str, Any]]) -> Leitura:
    """Leitura do texto já extraído (separado do download para poder testar sem internet)."""
    t = cafe.norm(texto)
    ts = trechos_cafe(t)
    if not ts:
        return Leitura(STATUS_SEM_CAFE, prazo_entrega=prazo_entrega(t))
    r = Leitura(STATUS_LIDO, trechos=[x.texto[:900] for x in _unicos(ts, 4)], prazo_entrega=prazo_entrega(t))
    # A lista de marcas de referência costuma vir logo depois da especificação (às vezes em outro parágrafo).
    r.marcas = list(dict.fromkeys(m for x in ts for m in marcas.citadas(t[x.inicio:x.inicio + 2500])))
    junto = " ".join(r.trechos)
    r.cat, r.qg, r.tags = cafe.categoria(junto), cafe.nota_qg(junto), cafe.exigencias(junto)
    for i in itens:
        if i["tipo"] in cafe.TIPOS_TORRADOS:
            r.itens[i["n"]] = " ".join(x.texto for x in _unicos(_do_item(ts, i), 2))[:1500]
    return r


# ---------------------------------------------------------------- download e leitura de uma compra
def _baixar(p: PNCP, url: str) -> bytes:
    p._aguardar_vez()  # mesmo ritmo das outras chamadas ao PNCP (limite de rajadas)
    with p.client.stream("GET", url, follow_redirects=True, timeout=120) as r:
        if r.status_code != 200:
            raise ColetaErro(f"{url} -> HTTP {r.status_code}")
        dados = bytearray()
        for bloco in r.iter_bytes():
            dados.extend(bloco)
            if len(dados) > MAX_BYTES:
                raise ColetaErro(f"{url}: arquivo maior que {MAX_BYTES // 2**20} MB")
        return bytes(dados)


def ler(p: PNCP, chave: str, itens: list[dict[str, Any]], salvar_em: Path | None = None) -> Leitura:
    """Baixa os documentos da compra (TR primeiro), extrai o texto e analisa. `salvar_em`: grava o texto
    extraído (para revisão manual)."""
    cnpj, resto = chave.split("-", 1)
    seq, ano = resto.split("-", 1)[1].split("/")
    try:
        docs = p.get_json(f"/pncp/v1/orgaos/{cnpj}/compras/{ano}/{int(seq)}/arquivos") or []
    except ColetaErro as e:
        logger.warning("Edital {}: lista de documentos falhou: {}", chave, e)
        return Leitura(STATUS_FALHA)
    docs = [d for d in docs if d.get("statusAtivo", True) and d.get("url")]
    if not docs:
        return Leitura(STATUS_SEM_DOCS)
    docs.sort(key=lambda d: (PRIORIDADE.get(d.get("tipoDocumentoId"), 4), d.get("sequencialDocumento") or 0))
    textos, lidos, falhas = [], [], 0
    for d in docs[:MAX_DOCS]:
        nome = d.get("titulo") or ""
        try:
            t = texto_de(nome, _baixar(p, d["url"]))
        except (ColetaErro, httpx.HTTPError) as e:
            logger.warning("Edital {}: {} não baixado: {}", chave, nome, e)
            falhas += 1
            continue
        lidos.append(f"{d.get('sequencialDocumento')}:{nome}")
        if t.strip():
            textos.append(t)
    if not lidos:
        return Leitura(STATUS_FALHA)
    if not textos:
        return Leitura(STATUS_SEM_TEXTO, docs=lidos)
    if salvar_em is not None:
        salvar_em.mkdir(parents=True, exist_ok=True)
        (salvar_em / (re.sub(r"\W", "_", chave) + ".txt")).write_text("\n\n=====\n\n".join(textos), encoding="utf-8")
    r = analisar("\n".join(textos), itens)
    r.docs = lidos
    return r


# ---------------------------------------------------------------- aplicar no registro da compra
def aplicar(compra: dict[str, Any], r: Leitura, hoje: str) -> None:
    """Grava a leitura na compra. Cada item torrado recebe o trecho do edital que fala dele (`ed_trecho`);
    o nível é recalculado (o que falta na descrição do item vem do edital, marcado com *).
    Leitura sem sucesso não apaga uma leitura boa anterior: só registra o status."""
    compra["edital_status"] = r.status
    if r.status == STATUS_FALHA or (r.status != STATUS_LIDO and compra.get("edital_lido")):
        return
    compra["edital_docs"] = r.docs
    compra["edital_lido_em"] = hoje
    compra["ed_pz"] = r.prazo_entrega or compra.get("ed_pz", "")
    if r.status != STATUS_LIDO:
        compra["edital_lido"] = False
        return
    compra["edital_lido"] = True
    compra["trecho_edital"] = " || ".join(r.trechos)
    compra["ed_tags"] = r.tags
    compra["marcas"] = r.marcas
    for i in compra["itens"]:
        if (d := r.itens.get(i["n"])) is not None:
            i["ed_trecho"] = d
    montar.reclassificar_nivel(compra)
    compra.update(montar.agregar(compra["itens"]))


# ---------------------------------------------------------------- várias compras (coleta diária e comando editais)
MAX_POR_COLETA = 40  # leituras por coleta diária (novas primeiro); o resto fica para o dia seguinte


def precisa_ler(c: dict[str, Any], versao: str) -> bool:
    """Nunca lida, falhou, ainda sem documentos, ou a compra mudou no PNCP (errata, novo anexo)."""
    st = c.get("edital_status", "")
    return not st or st in (STATUS_FALHA, STATUS_SEM_DOCS) or c.get("edital_ver", "") != versao


def ler_varias(p: PNCP, compras: list[dict[str, Any]], versoes: dict[str, str], hoje: str,
               limite: int | None = MAX_POR_COLETA, todas: bool = False, salvar_em: Path | None = None) -> int:
    """Lê o edital das compras que precisam (até `limite`; `todas`: relê todas), no máximo 3 de cada vez.
    Devolve quantas leu."""
    fila = [c for c in compras if not c.get("dup_of") and (todas or precisa_ler(c, versoes.get(c["chave"], "")))]
    fila.sort(key=lambda c: (bool(c.get("edital_status")), c.get("fim") or ""))  # nunca lidas primeiro
    if limite is not None and len(fila) > limite:
        logger.info("Editais: {} para ler; {} agora, o resto na próxima coleta", len(fila), limite)
        fila = fila[:limite]

    def uma(c: dict[str, Any]) -> str:
        r = ler(p, c["chave"], c["itens"], salvar_em)
        aplicar(c, r, hoje)
        if r.status != STATUS_FALHA:
            c["edital_ver"] = versoes.get(c["chave"], "")
        return r.status

    with ThreadPoolExecutor(max_workers=3) as ex:
        status = list(ex.map(uma, fila))
    logger.info("Editais lidos: {} ({})", len(fila), ", ".join(f"{s}: {status.count(s)}" for s in sorted(set(status))))
    return len(fila)
