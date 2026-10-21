/* Regras de negócio da página: R$/kg por tipo, nível de exigência, preço típico, custo e margem.
   As que têm par no coletor são contrato: mudou lá, mude aqui.
   - preço típico por nível: coletor/referencia.py (refPrecos);
   - custo e margem: coletor/custos.py (margemInfo), teste de página compara os dois. */
import type { Compra, Custos, Item, MarcasRef, Mercado, MeusCustos, Nivel, Painel, Pisos } from "../types";
import { dayNum, nrm, tcase, toMs, todayYMD } from "./format";

export const TM = "Torrado e moído";
export const NIVEIS: Nivel[] = ["Sem categoria", "Tradicional", "Superior", "Gourmet/especial"];
export const NIVEL_CURTO: Record<string, string> = { "Sem categoria": "Sem categoria", Tradicional: "Tradicional", Superior: "Superior", "Gourmet/especial": "Gourmet" };
export const REF_MIN = 5;
export const REF_FAIXA = 0.1;

/* Réguas de mercado (valores datados, atualizados à mão; fontes na aba Guia > Sobre os dados).
   Varejo: preço médio em supermercados por estilo (ABIC, ago/2026). */
export const MERCADO_VAREJO: { valores: Record<string, number>; data: string } = {
  valores: { Tradicional: 49.5, Superior: 66.94, "Gourmet/especial": 102.38 },
  data: "ago/2026",
};

export const grupoTipo = (t: string): string => (t === "Torrado e moído (descafeinado)" ? TM : t);
/* "Torrado e moído, Torrado e moído (descafeinado)" vira "Torrado e moído (+ descafeinado)". */
export function tiposTexto(tipos: string[]): string {
  const L = [...new Set(tipos)], desc = "Torrado e moído (descafeinado)";
  if (L.includes(TM) && L.includes(desc)) return [TM + " (+ descafeinado)", ...L.filter((t) => t !== TM && t !== desc)].join(", ");
  return L.join(", ");
}

export interface RkInfo { main: { t: string; v: number; kg: number }; outros: { t: string; v: number; kg: number }[] }
/* R$/kg por tipo de café: misturar solúvel com torrado e moído distorce a comparação. O principal é o
   torrado e moído; sem ele, o tipo de maior volume. Itens "conferir" (provável erro de unidade) ficam fora. */
export function rkInfo(c: Compra): RkInfo | null {
  const by: Record<string, { v: number; kg: number }> = {};
  c.itens.forEach((i) => {
    if (i.rkg == null || i.conferir || i.vt == null || i.kgt == null) return;
    const t = by[i.tipo] || (by[i.tipo] = { v: 0, kg: 0 });
    t.v += i.vt;
    t.kg += i.kgt;
  });
  const L = Object.entries(by).map(([t, x]) => ({ t, v: Math.round((x.v / x.kg) * 100) / 100, kg: x.kg }))
    .sort((a, b) => Number(b.t === TM) - Number(a.t === TM) || b.kg - a.kg);
  return L.length ? { main: L[0], outros: L.slice(1) } : null;
}

/* Item que define a compra para comparação de preço: torrado e moído (senão qualquer tipo com nível) de maior
   volume, com nível e R$/kg. Mesma regra de coletor/referencia.py (item_principal). */
export function mainItem(c: Compra): Item | null {
  const L = c.itens.filter((i) => i.nivel && i.rkg != null && !i.conferir);
  const tm = L.filter((i) => grupoTipo(i.tipo) === TM);
  const P = tm.length ? tm : L;
  return P.length ? P.reduce((a, b) => ((b.kgt || 0) > (a.kgt || 0) ? b : a)) : null;
}

export function median(a: number[]): number | null {
  if (!a.length) return null;
  const s = a.slice().sort((x, y) => x - y);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}
export function quant(sorted: number[], q: number): number {
  const p = (sorted.length - 1) * q, b = Math.floor(p);
  return sorted[b + 1] != null ? sorted[b] + (p - b) * (sorted[b + 1] - sorted[b]) : sorted[b];
}

export interface Referencia { med: number; p25: number; p75: number; n: number; pts: { chave: string; v: number }[] }
export type Refs = Record<string, Referencia>;
/* Preço típico (mediana) do R$/kg por tipo e nível entre as compras visíveis (sem duplicatas). */
export function refPrecos(L: Compra[]): Refs {
  const by: Record<string, { chave: string; v: number }[]> = {};
  L.forEach((c) => {
    if (c.dup_of) return;
    c.itens.forEach((i) => {
      if (i.nivel && i.rkg != null && !i.conferir) (by[grupoTipo(i.tipo) + "|" + i.nivel] ||= []).push({ chave: c.chave, v: i.rkg });
    });
  });
  const out: Refs = {};
  for (const [k, pts] of Object.entries(by)) {
    if (pts.length < REF_MIN) continue;
    const v = pts.map((p) => p.v).sort((a, b) => a - b);
    out[k] = { med: Math.round(median(v)! * 100) / 100, p25: quant(v, 0.25), p75: quant(v, 0.75), n: v.length, pts }; // 2 casas, como referencia.py
  }
  return out;
}

export type ClsPreco = "up" | "mid" | "down" | "";
export const PF: Record<ClsPreco, string> = { up: "Acima do típico", mid: "No típico", down: "Abaixo do típico", "": "Sem comparação" };
export interface CmpInfo { i: Item; ref: number | null; dif: number | null; cls: ClsPreco; piso: number | null; ok: boolean | null }
export function cmpInfo(main: Item | null, refs: Refs, pisos: Pisos): CmpInfo | null {
  if (!main) return null;
  const r = refs[grupoTipo(main.tipo) + "|" + main.nivel];
  const dif = r ? main.rkg! / r.med - 1 : null;
  const piso = main.nivel && pisos[main.nivel] > 0 ? pisos[main.nivel] : null;
  return { i: main, ref: r ? r.med : null, dif, cls: dif == null ? "" : dif >= REF_FAIXA ? "up" : dif <= -REF_FAIXA ? "down" : "mid", piso, ok: piso ? main.rkg! >= piso : null };
}

/* ---------------- custo e margem (mesma regra de coletor/custos.py: mudou uma, mude a outra) */
export type CampoCusto = [key: string, rotulo: string, unidade: string, caminho: string[], fator: number, ajuda: string];
export const CAMPOS_CUSTO: CampoCusto[] = [
  ["perda_torra", "Perda na torra", "%", ["perda_torra"], 100, "O café perde água e peso ao torrar. 18% é o usual (13% clara a 20% escura)."],
  ["torra", "Torra (por kg de café verde)", "R$/kg", ["torra_rs_kg_verde"], 1, "Preço da torra terceirizada por kg de café verde."],
  ["embalagem", "Embalagem", "R$/kg", ["embalagem_rs_kg"], 1, "Empacotamento por kg de café torrado."],
  ["das", "Imposto (DAS do Simples)", "%", ["pct_preco", "das"], 100, "Simples Nacional, Anexo II, 1ª faixa. Confirme com o contador."],
  ["financeiro", "Custo de esperar o pagamento", "%", ["pct_preco", "financeiro"], 100, "O órgão paga depois da entrega; 1,5 mês de capital de giro."],
  ["perdas", "Perdas e devoluções", "%", ["pct_preco", "perdas"], 100, "Reserva para avarias e devoluções."],
  ["plataforma", "Plataforma do pregão (por licitação)", "R$", ["por_licitacao", "plataforma"], 1, "Taxa que algumas plataformas cobram do fornecedor por processo."],
  ["laudo", "Laudo de qualidade (por licitação)", "R$", ["por_licitacao", "laudo"], 1, "Laudo sensorial ou de microscopia quando o edital exige. Sem preço público: informe o seu."],
  ["amostra_kg", "Amostra (por licitação)", "kg", ["por_licitacao", "amostra_kg"], 1, "Café enviado como amostra, ao custo direto."],
  ["folga_frete", "Folga no frete", "%", ["frete", "folga"], 100, "Margem sobre a fórmula do frete (preço de balcão, entrega difícil)."],
  ["entregas", "Entregas (compra comum)", "nº", ["frete", "entregas"], 1, "Quantas viagens para entregar tudo."],
  ["entregas_rp", "Entregas (registro de preços)", "nº", ["frete", "entregas_registro_precos"], 1, "Registro de preços costuma ter entregas parceladas."],
];

export function custoPadrao(custos: Custos | undefined, k: string): number | undefined {
  const f = CAMPOS_CUSTO.find((x) => x[0] === k);
  if (!f) return undefined;
  let v: unknown = custos || {};
  for (const p of f[3]) v = (v as Record<string, unknown> | undefined)?.[p];
  return typeof v === "number" ? v : undefined;
}

export interface MargemInfo {
  preco: number; nivel: string; grao: number; torra: number; emb: number; frete: number; fixos: number; pctV: number; pct: number;
  custo: number; m: number; mp: number; lucro: number; kg: number; empate: number; proprio: boolean;
}

export class Calculadora {
  constructor(readonly custos: Custos | undefined, readonly mercado: Mercado | undefined, readonly meus: MeusCustos) {}
  custo(k: string): number {
    const v = k in this.meus ? this.meus[k] : custoPadrao(this.custos, k);
    return v ?? 0;
  }
  graoSaca(n: string): number {
    if (this.meus["grao|" + n] > 0) return this.meus["grao|" + n];
    const kg = this.mercado?.niveis?.[n]?.kg_medio;
    return kg ? kg * 60 : 0;
  }
  freteTotal(kg: number, km: number, preco: number, rp: boolean): number {
    const f = this.custos?.frete;
    if (!f) return 0;
    const n = Math.max(1, Math.trunc(rp ? this.custo("entregas_rp") : this.custo("entregas")) || 1), e = kg / n; // trunc = int() do custos.py
    const frac = f.fixo_por_envio + e * (f.rs_kg + (f.rs_kg_100km * km) / 100) + f.ad_valorem * preco * e;
    return n * Math.min(frac, f.lotacao_fixo + f.lotacao_rs_km * km) * (1 + this.custo("folga_frete"));
  }
  /** Custo por kg e margem da licitação ao preço p (padrão: o do órgão no item principal). */
  margem(c: Compra, main: Item | null, p?: number | null): MargemInfo | null {
    if (!main || !this.custos || !this.mercado?.niveis) return null;
    const preco = p || main.rkg, kg = c.kg, km = c.dist, nivel = main.nivel || "Sem categoria", sacas = this.graoSaca(nivel);
    if (!preco || !kg || km == null || !(sacas > 0)) return null;
    const perda = this.custo("perda_torra"), grao = sacas / 60 / (1 - perda), torra = this.custo("torra") / (1 - perda), emb = this.custo("embalagem");
    const direto = grao + torra + emb, frete = this.freteTotal(kg, km, preco, c.srp === "Sim") / kg;
    const fixos = (this.custo("plataforma") + this.custo("laudo") + this.custo("amostra_kg") * direto) / kg;
    const pct = this.custo("das") + this.custo("financeiro") + this.custo("perdas"), custoKg = direto + frete + fixos + preco * pct, m = preco - custoKg;
    return { preco, nivel, grao, torra, emb, frete, fixos, pctV: preco * pct, pct, custo: custoKg, m, mp: m / preco, lucro: m * kg, kg, empate: (direto + frete + fixos) / (1 - pct), proprio: this.meus["grao|" + nivel] > 0 };
  }
}

export type ClsMargem = "pos" | "mid" | "neg";
export const mgCls = (mp: number): ClsMargem => (mp >= 0.15 ? "pos" : mp >= 0 ? "mid" : "neg");

/* ---------------- urgência */
export interface Urg { d: number | null; cls: "nd" | "closed" | "red" | "amber" | "green"; lbl: string }
export function urg(fim: string | null, ms: number | null, now = Date.now()): Urg {
  if (!fim) return { d: null, cls: "nd", lbl: "Sem prazo" };
  const d = dayNum(fim.slice(0, 10)) - dayNum(todayYMD());
  if (ms != null && ms < now) return { d, cls: "closed", lbl: "Encerrada" };
  const cls = d <= 3 ? "red" : d <= 7 ? "amber" : "green";
  const lbl = d === 0 ? "Fecha hoje" : d === 1 ? "Amanhã" : d + " dias";
  return { d, cls, lbl };
}

/* ---------------- exigências que pesam no preço, em ordem de leitura */
export const SELOS = ["100% arábica", "PQC", "ABIC/pureza", "Nota QG/sensorial", "Sem PVA (grãos selecionados)", "Grãos selecionados", "Premium/1ª qualidade (termo comercial)", "Laudo", "Amostra", "Marca ref.", "Aceita conilon/blend", "Agric. familiar"];
/* Nome simples de cada exigência (cartão Exigências da tela Hoje e filtro "Exigências do item"). */
export const SELO_ROTULO: Record<string, string> = { "ABIC/pureza": "Selo ABIC / pureza", "Premium/1ª qualidade (termo comercial)": "“Premium” / 1ª qualidade", "Nota QG/sensorial": "Nota mínima de bebida", Laudo: "Laudo de laboratório", "Marca ref.": "Marca de referência", "Aceita conilon/blend": "Aceita conilon ou blend", "Sem PVA (grãos selecionados)": "Grãos sem defeitos (PVA)", "Agric. familiar": "Agricultura familiar" };
export const SELO_CURTO: Record<string, string> = { "Premium/1ª qualidade (termo comercial)": "premium/1ª qualidade", "Sem PVA (grãos selecionados)": "sem PVA", "Aceita conilon/blend": "aceita conilon", "ABIC/pureza": "selo ABIC", "Nota QG/sensorial": "nota mínima", "Marca ref.": "marca de referência", "Agric. familiar": "agricultura familiar" };
export function selosDe(c: PCompra, max = 4): string[] {
  const i = c._main || c.itens[0], t = (i && i.tags) || [];
  const L: (string | null)[] = [
    i && i.qg ? "nota ≥ " + String(i.qg).replace(".", ",") : null,
    ...SELOS.filter((x) => t.includes(x) && !(x === "Nota QG/sensorial" && i.qg)).map((x) => SELO_CURTO[x] || x),
    t.find((x) => x.startsWith("Validade")) || null,
    /vácuo/.test((i && i.emb) || "") ? "vácuo" : null,
  ];
  return L.filter((x): x is string => !!x).slice(0, max);
}

/* ---------------- marcas de referência (coletor/marcas_cafe.json, embutido como marcas_ref) */
export const marcaRef = (mr: MarcasRef | null | undefined, m: string) => mr?.marcas?.[m] || null;
export function varejoTxt(mr: MarcasRef | null | undefined, m: string): string {
  const b = marcaRef(mr, m)?.basica;
  if (!b) return "";
  const f = (v: number) => "R$ " + v.toFixed(2).replace(".", ",");
  return `${b.cat || "sem categoria ABIC"}${b.linha ? " (" + b.linha + ")" : ""}: ${b.min === b.max ? f(b.min) : f(b.min) + " a " + f(b.max)}/kg`;
}
export function marcasVarejo(mr: MarcasRef | null | undefined, c: Compra): { min: number; max: number; n: number } | null {
  const bs = (c.marcas || []).map((m) => marcaRef(mr, m)?.basica).filter((b): b is NonNullable<typeof b> => !!b);
  return bs.length ? { min: Math.min(...bs.map((b) => b.min)), max: Math.max(...bs.map((b) => b.max)), n: bs.length } : null;
}

/* ---------------- compra preparada: campos derivados calculados uma vez por carga de dados */
export interface PCompra extends Compra {
  _i: number;
  _ms: number | null;
  _rk: RkInfo | null;
  _parcial: boolean;
  _orgao: string;
  _near: "mg" | "near" | "uf";
  _new: boolean;
  _main: Item | null;
  _niv: Nivel | null;
  _s: string;
  _cmp: CmpInfo | null;
  _pf: string;
  _mg: MargemInfo | null;
}

export interface Preparado {
  compras: PCompra[];
  byk: Record<string, PCompra>;
  refs: Refs;
  calc: Calculadora;
  distMax: number;
  origem: string;
}

export const rkV = (c: PCompra): number | null => (c._rk ? c._rk.main.v : null);
export const rkTM = (c: PCompra): number | null => (c._rk && c._rk.main.t === TM ? c._rk.main.v : null);
export const rkLbl = (c: PCompra): string => (c._rk && c._rk.main.t !== TM ? c._rk.main.t.toLowerCase() : "");
export const rkOutrosTxt = (c: PCompra): string => (c._rk ? c._rk.outros.map((o) => `${o.t.toLowerCase()} R$ ${o.v.toFixed(2).replace(".", ",")}`).join(" · ") : "");
export const isOpen = (c: PCompra, now = Date.now()): boolean => !c._ms || c._ms >= now;

export function preparar(data: Painel, pisos: Pisos, meus: MeusCustos): Preparado {
  const calc = new Calculadora(data.custos, data.mercado, meus);
  const compras = data.compras.map((c, i) => {
    const p = { ...c } as PCompra; // cópia: os dados publicados ficam intactos e cada preparação é independente
    p._i = i;
    p._ms = toMs(c.fim);
    p._rk = rkInfo(c);
    p._parcial = c.kg != null && c.itens.some((it) => it.kgt == null);
    p._orgao = tcase(c.orgao);
    p._near = c.uf === "MG" ? "mg" : c.uf === "SP" || c.uf === "GO" ? "near" : "uf";
    p._new = "nova" in c ? !!c.nova : false;
    p._main = mainItem(c);
    p._niv = p._main ? (p._main.nivel as Nivel) : (NIVEIS.slice().reverse().find((n) => (c.niveis || []).includes(n)) as Nivel) || null;
    p._s = nrm([c.orgao, c.unidade, c.mun, c.uf, c.objeto, c.resumo, c.num, c.mod, c.plat, c.chave, c.tipos.join(" "), c.cats.join(" "), c.embs, c.tags.join(" "), c.me, (c.niveis || []).join(" "), ...c.itens.map((it) => it.espec)].join(" "));
    return p;
  });
  const byk: Record<string, PCompra> = {};
  compras.forEach((c) => (byk[c.chave] = c));
  const refs = refPrecos(compras.filter((c) => isOpen(c)));
  compras.forEach((c) => {
    c._cmp = cmpInfo(c._main, refs, pisos);
    c._pf = PF[c._cmp ? c._cmp.cls : ""];
    c._mg = calc.margem(c, c._main);
  });
  const md = Math.max(0, ...compras.map((c) => c.dist || 0));
  return { compras, byk, refs, calc, distMax: Math.ceil(md / 100) * 100 || 3000, origem: data.origem?.nome || "Uberaba-MG" };
}

/* ---------------- por que o item caiu nesse nível (mesmo critério de coletor/cafe.py: nivel) */
export function nivelPorque(i: Item): string {
  const cats = (i.cat || "").split("/").map((x) => x.replace("*", "")), r: string[] = [];
  if (cats.includes("Gourmet") || cats.includes("especial")) r.push("pede café gourmet/especial");
  if (cats.includes("Superior")) r.push("pede categoria Superior");
  if (i.qg) r.push(`nota mínima de qualidade ${String(i.qg).replace(".", ",")} (escala PQC/ABIC: Tradicional 4,5; Superior 6,0; Gourmet 7,3)`);
  if (/bebida\W+(\w+\W+)?(apenas |estritamente )?mole\b(?! (a|ou|ate) (dura|rio|riad|apenas|\w+ dura))/.test(nrm(i.espec + " " + (i.ed_trecho || "")))) r.push("pede bebida mole");
  if (cats.includes("Tradicional") || cats.includes("Extraforte")) r.push("categoria " + cats.filter((x) => x === "Tradicional" || x === "Extraforte").join("/"));
  if (i.tags.includes("ABIC/pureza")) r.push("selo de pureza ABIC");
  if (i.tags.includes("PQC")) r.push("programa de qualidade PQC");
  const ed = (i.cat || "").includes("*") ? " (segundo o edital/TR, a fonte principal; a descrição curta do item no PNCP não diz isso)" : "";
  return r.length ? r.join("; ") + ed : (i.ed_trecho ? "nem a descrição do item nem o trecho do edital sobre ele pedem" : "o texto do item não pede") + " categoria (Tradicional, Superior, Gourmet), selo ABIC/PQC ou nota de qualidade";
}

/* ---------------- pontos de atenção do edital (Lei 14.133/2021, TCU, normas do café). Não é orientação jurídica. */
export function pontosDeAtencao(i: Item): string[] {
  const t = i.tags || [], tx = nrm(i.espec || ""), at: string[] = [];
  const val = t.find((x) => x.startsWith("Validade"));
  if (t.includes("Marca ref.")) at.push("Marca citada: pela Lei 14.133 (art. 41, I), marca só como referência, com “ou equivalente”; a equivalência pode ser provada por laudo ou certificado (art. 42).");
  if (t.includes("ABIC/pureza")) at.push("Selo ABIC: o entendimento citado em editais e atribuído ao TCU é que exigir só o selo restringe a concorrência; laudo de laboratório credenciado deve ser aceito. Confira se o edital aceita alternativa.");
  if (t.includes("Amostra")) at.push("Amostra: pela Lei 14.133 (art. 41, parágrafo único), só se prevista e justificada, e no julgamento só do vencedor provisório.");
  if (i.qg && /\b(maxim[ao]|ate) (de )?\d[,.]\d|\d[,.]\d+ (pontos )?(a|-) \d[,.]\d/.test(tx) && /qualidade global|nota/.test(tx)) at.push("Nota com teto (ex.: “de 6,0 a 7,2”): o usual é “nota ≥ X”; um teto pode ser questionado (leitura técnica, não jurisprudência).");
  if (/almofada/.test(tx) && val && parseInt(val.replace(/\D+/g, "")) >= 12) at.push("Validade de 12 meses ou mais na entrega costuma exigir embalagem a vácuo ou com válvula (ITAL); almofada comum dura menos.");
  if (/\bsubgrupo\b|empeliculad|\bgrupo especial\b/.test(tx) || /\bcafe\b.{0,80}\btipo 1\b/.test(tx)) at.push("O texto usa termos de classificação que não existem para café torrado (ex.: “grupo especial”, “subgrupo empeliculado”, “tipo 1”; parecem copiados da classificação de outro grão, como o amendoim). A Portaria SDA 570/2022 só prevê “torrado em grão” ou “torrado e moído”. Vale pedir esclarecimento ao órgão sobre a qualidade exigida.");
  if (/tipo unico/.test(tx)) at.push("“Tipo Único” é só o mínimo legal da Portaria SDA 570/2022, não indica qualidade alta.");
  if (/\bin\s*(mapa\s*)?(n[o°º]\s*)?16\/2010|portaria\s*(n[o°º]\s*)?377/.test(tx)) at.push("Cita norma antiga (IN 16/2010 ou Portaria 377/1999); a norma federal atual do café torrado é a Portaria SDA 570/2022.");
  return at;
}

/* O que aconteceu com a leitura do edital (coletor/edital.py: STATUS_*). */
export type EdEstado = "lido" | "manual" | "sem" | "ilegivel" | "sem-trecho" | "falha" | "pendente";
export function edStatus(c: Compra): { estado: EdEstado; texto: string } {
  const st = c.edital_status || "", em = c.edital_lido_em ? " em " + c.edital_lido_em.split("-").reverse().join("/") : "";
  const docs = (c.edital_docs || []).map((d) => d.replace(/^\d+:/, "")).join(", ");
  // a compra mudou no PNCP e a releitura não deu certo: a leitura boa continua valendo, mas vale saber
  const tent = c.edital_tentativa ? ` A compra mudou no PNCP e a releitura de ${c.edital_tentativa.slice(0, 10).split("-").reverse().join("/")} não substituiu esta leitura (${c.edital_tentativa.slice(12)}).` : "";
  if (st.startsWith("lido (revis")) return { estado: "manual", texto: `Documentos escaneados (sem texto para o coletor), conferidos página a página${em}${docs ? ` (${docs})` : ""}. A transcrição do trecho de cada item está em “Itens de café”.${tent}` };
  if (st === "lido" || (!st && c.edital_lido)) return { estado: "lido", texto: `Edital lido pelo coletor${em}${docs ? ` (${docs})` : ""}. A especificação de cada item está em “Itens de café”.${tent}` };
  if (st.startsWith("sem documentos")) return { estado: "sem", texto: "O órgão ainda não publicou o edital no PNCP. O coletor confere de novo a cada coleta; até lá, valem só a descrição dos itens e o site da plataforma." };
  if (st.startsWith("documentos sem texto")) return { estado: "ilegivel", texto: `Os documentos estão no PNCP${docs ? ` (${docs})` : ""}, mas sem texto que o coletor consiga ler (PDF escaneado, arquivo .rar ou formato não suportado). Abra no PNCP para ler.` };
  if (st.startsWith("documentos lidos")) return { estado: "sem-trecho", texto: `Documentos lidos${em}${docs ? ` (${docs})` : ""}: nenhum traz a especificação do café; vale a descrição dos itens. Confira se há anexo no site da plataforma.` };
  if (st.startsWith("falha")) return { estado: "falha", texto: "Não consegui baixar os documentos do PNCP na última tentativa; o coletor tenta de novo na próxima coleta. Abra no PNCP para ver os anexos." };
  return { estado: "pendente", texto: "O coletor ainda não leu o edital desta compra (lê na próxima coleta). Abra no PNCP para ver os anexos." };
}

export const platShort = (c: Compra): string =>
  c.plat.startsWith("Ver edital") ? "ver edital" : c.plat.replace("BNC – Bolsa Nacional de Compras", "BNC").replace("Licitações-e (Banco do Brasil)", "Licitações-e (BB)").replace(/^Portal próprio: .*/, "portal próprio");
export const meBadge = (c: Compra): string | null =>
  c.me && (c.me.startsWith("Exclusivo") || c.me.startsWith("Cota")) ? (c.me.startsWith("Exclusivo ME/EPP") ? "ME/EPP" : c.me.startsWith("Cota") ? "Cota ME/EPP" : "ME/EPP parcial") : null;
export const pncpLink = (k: string): string => {
  const m = k.match(/^(\d{14})-\d+-(\d+)\/(\d{4})$/);
  return m ? `https://pncp.gov.br/app/editais/${m[1]}/${m[3]}/${+m[2]}` : "https://pncp.gov.br/";
};
