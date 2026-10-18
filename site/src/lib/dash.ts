/* Contas da tela Hoje e do Mercado: tudo a partir das licitações abertas (sem duplicatas). */
import type { MeusDados, Painel } from "../types";
import { dayNum, todayYMD } from "./format";
import { follows, getW } from "./filtros";
import { grupoTipo, isOpen, median, mgCls, NIVEIS, quant, SELOS, TM, type PCompra, type Preparado } from "./modelo";

export type StatusMargem = "bom" | "apertado" | "preju" | "sem";
export const statusMargem = (c: PCompra): StatusMargem => (!c._mg ? "sem" : mgCls(c._mg.mp) === "pos" ? "bom" : mgCls(c._mg.mp) === "mid" ? "apertado" : "preju");

export const abertas = (prep: Preparado, now = Date.now()): PCompra[] => prep.compras.filter((c) => isOpen(c, now) && !c.dup_of);

export interface Kpis {
  n: number; kg: number; vcafe: number; comCusto: number; lucro: number; boas: number; apertadas: number; preju: number; sem: number;
  mpTipica: number | null; mp25: number | null; mp75: number | null; fecham7: number; fecham3: number; amanha: number; hoje: number;
  lucroTotal: number; lucroDist: [string, number][]; publicadas: { dia: string; n: number }[]; semana: number; fechamSemana: { dia: string; n: number }[];
  minhas: number; novas: number;
}
export function kpis(O: PCompra[], wf: MeusDados, todas: PCompra[], now = Date.now()): Kpis {
  const t0 = dayNum(todayYMD());
  const d = (c: PCompra) => (c.fim ? dayNum(c.fim.slice(0, 10)) - t0 : null);
  const mps = O.filter((c) => c._mg).map((c) => c._mg!.mp).sort((a, b) => a - b);
  const bands: [string, number, number][] = [["até 300 km", 0, 300], ["300 a 600", 300, 600], ["600 a 1.000", 600, 1000], ["acima de 1.000", 1000, 1e9]];
  const lucroDist = bands.map(([l, a, b]) => [l, O.filter((c) => c.dist != null && c.dist > (a === 0 ? -1 : a) && c.dist <= b && c._mg && c._mg.lucro > 0).reduce((s, c) => s + c._mg!.lucro, 0)] as [string, number]);
  const pub: Record<string, number> = {};
  for (let i = 13; i >= 0; i--) pub[new Date((t0 - i) * 864e5).toISOString().slice(0, 10)] = 0;
  todas.forEach((c) => { const k = (c.publicado || "").slice(0, 10); if (k in pub) pub[k]++; });
  const fechamSemana: { dia: string; n: number }[] = [];
  for (let i = 1; i <= 7; i++) { const dia = new Date((t0 + i) * 864e5).toISOString().slice(0, 10); fechamSemana.push({ dia, n: O.filter((c) => (c.fim || "").slice(0, 10) === dia).length }); }
  return {
    n: O.length,
    kg: O.reduce((a, c) => a + (c.kg || 0), 0),
    vcafe: O.reduce((a, c) => a + (c.vcafe || 0), 0),
    comCusto: O.filter((c) => c._mg).length,
    lucro: O.filter((c) => c._mg && c._mg.lucro > 0).length,
    boas: O.filter((c) => statusMargem(c) === "bom").length,
    apertadas: O.filter((c) => statusMargem(c) === "apertado").length,
    preju: O.filter((c) => statusMargem(c) === "preju").length,
    sem: O.filter((c) => !c._mg).length,
    mpTipica: median(mps), mp25: mps.length ? quant(mps, 0.25) : null, mp75: mps.length ? quant(mps, 0.75) : null,
    fecham7: O.filter((c) => { const x = d(c); return x != null && x >= 0 && x <= 7; }).length,
    fecham3: O.filter((c) => { const x = d(c); return x != null && x >= 0 && x <= 3; }).length,
    amanha: O.filter((c) => d(c) === 1).length,
    hoje: O.filter((c) => d(c) === 0 && isOpen(c, now)).length,
    lucroTotal: O.filter((c) => c._mg && c._mg.lucro > 0).reduce((s, c) => s + c._mg!.lucro, 0),
    lucroDist,
    publicadas: Object.entries(pub).map(([dia, n]) => ({ dia, n })),
    semana: Object.entries(pub).slice(-7).reduce((a, [, n]) => a + n, 0),
    fechamSemana,
    minhas: todas.filter((c) => follows(getW(wf, c.chave))).length,
    novas: O.filter((c) => c._new).length,
  };
}

export interface BarraPrazo { lbl: string; dia: string; fds: boolean; bom: number; apertado: number; preju: number; sem: number; total: number }
export function prazosPorDia(O: PCompra[], dias = 12): BarraPrazo[] {
  const t0 = dayNum(todayYMD()), out: BarraPrazo[] = [];
  for (let i = 1; i <= dias; i++) {
    const dt = new Date((t0 + i) * 864e5), dia = dt.toISOString().slice(0, 10), wd = dt.getUTCDay();
    const b: BarraPrazo = { lbl: wd === 0 ? "D" : wd === 6 ? "S" : String(dt.getUTCDate()), dia, fds: wd === 0 || wd === 6, bom: 0, apertado: 0, preju: 0, sem: 0, total: 0 };
    O.forEach((c) => { if ((c.fim || "").slice(0, 10) === dia) { b[statusMargem(c)]++; b.total++; } });
    out.push(b);
  }
  return out;
}
export function prazosPorSemana(O: PCompra[], semanas = 5): BarraPrazo[] {
  const t0 = dayNum(todayYMD()), out: BarraPrazo[] = [];
  for (let w = 0; w < semanas; w++) {
    const a = t0 + 1 + 7 * w, b = a + 6, da = new Date(a * 864e5).toISOString().slice(0, 10), db = new Date(b * 864e5).toISOString().slice(0, 10);
    const bar: BarraPrazo = { lbl: da.slice(8, 10) + "/" + da.slice(5, 7), dia: da, fds: false, bom: 0, apertado: 0, preju: 0, sem: 0, total: 0 };
    O.forEach((c) => { const k = (c.fim || "").slice(0, 10); if (k && k >= da && k <= db) { bar[statusMargem(c)]++; bar.total++; } });
    out.push(bar);
  }
  return out;
}

export interface UFInfo { n: number; lucro: number; kg: number; vcafe: number }
export function porUF(O: PCompra[]): Record<string, UFInfo> {
  const out: Record<string, UFInfo> = {};
  O.forEach((c) => { const u = (out[c.uf] ||= { n: 0, lucro: 0, kg: 0, vcafe: 0 }); u.n++; u.kg += c.kg || 0; u.vcafe += c.vcafe || 0; if (c._mg && c._mg.lucro > 0) u.lucro += c._mg.lucro; });
  return out;
}

/* Distribuição do R$/kg do órgão por nível (item principal, torrado e moído), faixas de R$ 10. */
export interface FaixaNivel { nivel: string; n: number; bins: number[]; med: number | null; p25: number | null; p75: number | null; custo: number | null; precos: number[] }
export const BIN_LO = 30, BIN_HI = 130, BIN_W = 10;
export function faixasPorNivel(O: PCompra[]): FaixaNivel[] {
  return NIVEIS.map((n) => {
    const L = O.filter((c) => c._main && c._main.nivel === n && grupoTipo(c._main.tipo) === TM && c._main.rkg != null);
    const ps = L.map((c) => c._main!.rkg!).sort((a, b) => a - b);
    const bins = new Array((BIN_HI - BIN_LO) / BIN_W).fill(0) as number[];
    ps.forEach((p) => { const i = Math.min(bins.length - 1, Math.max(0, Math.floor((p - BIN_LO) / BIN_W))); bins[i]++; });
    const custos = L.filter((c) => c._mg).map((c) => c._mg!.custo);
    return { nivel: n, n: ps.length, bins, med: median(ps), p25: ps.length ? quant(ps, 0.25) : null, p75: ps.length ? quant(ps, 0.75) : null, custo: median(custos), precos: ps };
  });
}

/* Simulador: custo "fixo" típico por nível (custo sem a parte proporcional ao preço) e os preços pagos. */
export interface SimNivel { nivel: string; fixo: number | null; pct: number; precos: number[]; empate: number | null }
export function simulador(O: PCompra[], prep: Preparado): SimNivel[] {
  const pct = prep.calc.custo("das") + prep.calc.custo("financeiro") + prep.calc.custo("perdas");
  return NIVEIS.map((n) => {
    const L = O.filter((c) => c._mg && c._main && c._main.nivel === n);
    const fixo = median(L.map((c) => c._mg!.custo - c._mg!.pctV));
    const precos = O.filter((c) => c._main && c._main.nivel === n && c._main.rkg != null).map((c) => c._main!.rkg!).sort((a, b) => a - b);
    return { nivel: n, fixo, pct, precos, empate: fixo != null ? fixo / (1 - pct) : null };
  });
}

export interface Exigencia { l: string; n: number; med: number | null }
export function exigencias(O: PCompra[]): Exigencia[] {
  const tor = O.filter((c) => c._main && grupoTipo(c._main.tipo) === TM);
  const rot: Record<string, string> = { "ABIC/pureza": "Selo ABIC / pureza", "Premium/1ª qualidade (termo comercial)": "“Premium” / 1ª qualidade", "Nota QG/sensorial": "Nota mínima de bebida", Laudo: "Laudo de laboratório", "Marca ref.": "Marca de referência", "Aceita conilon/blend": "Aceita conilon ou blend", "Sem PVA (grãos selecionados)": "Grãos sem defeitos (PVA)", "Agric. familiar": "Agricultura familiar" };
  const L = SELOS.map((t) => { const X = tor.filter((c) => c._main!.tags.includes(t)); return { l: rot[t] || t, n: X.length, med: median(X.map((c) => c._main!.rkg!)) }; });
  const nota = tor.filter((c) => c._main!.qg);
  L.push({ l: "Nota mínima de bebida", n: nota.length, med: median(nota.map((c) => c._main!.rkg!)) });
  const seen = new Set<string>();
  return L.filter((x) => x.n && !seen.has(x.l) && seen.add(x.l)).sort((a, b) => b.n - a.n);
}

export function embalagem(O: PCompra[]): { l: string; n: number }[] {
  const conta = (f: (c: PCompra) => boolean) => O.filter(f).length;
  return [
    { l: "a vácuo", n: conta((c) => c.emb_f.includes("Vácuo")) },
    { l: "pacote 500 g", n: conta((c) => c.emb_f.includes("500 g")) },
    { l: "pacote 250 g", n: conta((c) => c.emb_f.includes("250 g")) },
    { l: "pacote 1 kg", n: conta((c) => c.emb_f.includes("1 kg")) },
  ];
}

export function marcasCitadas(O: PCompra[]): { m: string; n: number; med: number | null }[] {
  const mc: Record<string, PCompra[]> = {};
  O.forEach((c) => (c.marcas || []).forEach((m) => (mc[m] ||= []).push(c)));
  return Object.entries(mc).sort((a, b) => b[1].length - a[1].length).map(([m, L]) => ({ m, n: L.length, med: median(L.filter((c) => c._main && c._main.rkg).map((c) => c._main!.rkg!)) }));
}

export interface Funil { l: string; n: number }
export function funil(data: Painel, O: PCompra[], k: Kpis): Funil[] {
  const co = data.coleta || {};
  const out: Funil[] = [];
  if (co.listadas) out.push({ l: "lidas no PNCP", n: co.listadas });
  if (co.candidatas) out.push({ l: "o objeto cita café ou alimentos", n: co.candidatas });
  if (co.itens_baixados) out.push({ l: "itens baixados e classificados", n: co.itens_baixados });
  out.push({ l: "abertas com café torrado", n: O.length }, { l: "com preço, volume e custo", n: k.comCusto }, { l: "dão lucro ao preço do órgão", n: k.lucro }, { l: "margem boa (15% ou mais)", n: k.boas });
  return out;
}

export interface Insight { tag: string; titulo: string; texto: string; acao: string; filtro: "longe" | "perto" | "me" | "guia" | "urgentes" | "lucro" }
export function insights(O: PCompra[], k: Kpis, uf: Record<string, UFInfo>): Insight[] {
  const out: Insight[] = [];
  const f = (v: number) => "R$ " + (v / 1e6).toFixed(1).replace(".", ",") + " mi";
  const longe = O.filter((c) => c.dist != null && c.dist > 1000), longeL = longe.filter((c) => c._mg && c._mg.lucro > 0);
  const lucroLonge = k.lucroDist[3][1];
  if (k.lucroTotal > 0 && lucroLonge / k.lucroTotal >= 0.4) {
    const top = Object.entries(uf).sort((a, b) => b[1].lucro - a[1].lucro).slice(0, 2);
    out.push({ tag: "Longe, mas vale", titulo: `${Math.round((lucroLonge / k.lucroTotal) * 100)}% do lucro está a mais de 1.000 km`, texto: `${f(lucroLonge)} dos ${f(k.lucroTotal)} ficam em ${longe.length} licitações distantes (${longeL.length} dão lucro). O frete pesa, mas o preço do órgão compensa: ${top.map(([u, x]) => u + " " + f(x.lucro)).join(" e ")}.`, acao: "Ver as distantes que dão lucro", filtro: "longe" });
  }
  const perto = O.filter((c) => c.dist != null && c.dist <= 300), pertoL = perto.filter((c) => c._mg && c._mg.lucro > 0).sort((a, b) => b._mg!.lucro - a._mg!.lucro);
  const melhor = pertoL[0];
  out.push({ tag: "Perto de casa", titulo: `${perto.length} licitaç${perto.length === 1 ? "ão" : "ões"} a até 300 km`, texto: pertoL.length ? `${pertoL.length} ${pertoL.length === 1 ? "dá" : "dão"} lucro, ${f(pertoL.reduce((s, c) => s + c._mg!.lucro, 0))} somados. A melhor é ${melhor.mun}, ${melhor.uf} (${melhor.dist} km): ${melhor._mg!.lucro >= 1e5 ? f(melhor._mg!.lucro) : "R$ " + Math.round(melhor._mg!.lucro / 1e3) + " mil"} de lucro estimado.` : "Nenhuma delas dá lucro ao preço do órgão com os seus custos.", acao: "Ver as mais próximas", filtro: "perto" });
  const excl = O.filter((c) => c.me.startsWith("Exclusivo ME/EPP")).length, cota = O.filter((c) => c.me.startsWith("Cota")).length, parcial = O.filter((c) => /^Exclusivo em/.test(c.me)).length;
  out.push({ tag: "Você tem vantagem", titulo: `${excl + cota + parcial} compras dão preferência a empresa pequena`, texto: `${excl} são exclusivas para ME/EPP, ${cota} têm cota reservada e ${parcial} reservam parte dos itens. No Simples Nacional você entra em todas elas.`, acao: "Ver as exclusivas", filtro: "me" });
  const abic = O.filter((c) => c._main && c._main.tags.includes("ABIC/pureza")).length, laudo = O.filter((c) => c._main && c._main.tags.includes("Laudo")).length;
  const vac = O.filter((c) => c.emb_f.includes("Vácuo")).length, g500 = O.filter((c) => c.emb_f.includes("500 g")).length;
  out.push({ tag: "O que os editais pedem", titulo: `Selo ABIC em ${abic} editais, laudo em ${laudo}`, texto: `Vácuo em ${vac} compras e pacote de 500 g em ${g500}. Ter o selo de pureza e embalagem a vácuo de 500 g abre a maior parte do mercado.`, acao: "Guia: documentos e selos", filtro: "guia" });
  return out.slice(0, 4);
}
