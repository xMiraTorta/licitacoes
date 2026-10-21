/* Filtros, ordenação e contagem das licitações (mesmo comportamento do site anterior). */
import type { Anotacao, Filtros, MeusDados, Ordem } from "../types";
import { nrm, toMs } from "./format";
import { isOpen, NIVEIS, rkTM, rkV, SELO_ROTULO, SELOS, urg, type PCompra } from "./modelo";

export interface Facet { k: keyof Filtros & ("niveis" | "precos" | "ufs" | "tipos" | "cats" | "embs" | "me" | "mods" | "plats" | "marcas" | "selos"); t: string; get: (c: PCompra) => string[]; open?: boolean; order?: string[]; ajuda?: string; rotulo?: Record<string, string> }
/* Exigências do item principal (só as da lista SELOS; validade e rótulo ficam de fora); nota mínima lida só do número, sem a etiqueta, também conta.
   A MESMA função conta o cartão Exigências da tela Hoje, para o número do cartão bater com a lista que o clique abre. */
export const selosFiltro = (c: PCompra): string[] => { const i = c._main, t = ((i && i.tags) || []).filter((x) => SELOS.includes(x)); return i && i.qg && !t.includes("Nota QG/sensorial") ? [...t, "Nota QG/sensorial"] : t; };
export const FACETS: Facet[] = [
  { k: "niveis", t: "Nível de exigência", get: (c) => c.niveis || [], open: true, order: NIVEIS, ajuda: "Lido do texto do edital: categoria, selo ABIC/PQC, nota mínima ou classificação da bebida." },
  { k: "precos", t: "Preço vs típico do nível", get: (c) => [c._pf], open: true, order: ["Acima do típico", "No típico", "Abaixo do típico", "Sem comparação"], ajuda: "Comparação com o preço do meio entre as licitações abertas do mesmo tipo e nível." },
  { k: "tipos", t: "Tipo de café", get: (c) => c.tipos, open: true },
  { k: "ufs", t: "Estado (UF)", get: (c) => [c.uf] },
  { k: "cats", t: "Categoria", get: (c) => c.cats },
  { k: "embs", t: "Embalagem", get: (c) => c.emb_f },
  { k: "me", t: "ME/EPP", get: (c) => c.me_f, open: true, ajuda: "Licitações reservadas, total ou em parte, a micro e pequenas empresas." },
  { k: "mods", t: "Modalidade", get: (c) => [c.mod] },
  { k: "plats", t: "Onde enviar proposta", get: (c) => [c.plat_f] },
  { k: "marcas", t: "Marca de referência (edital)", get: (c) => c.marcas || [] },
  { k: "selos", t: "Exigências do item", get: selosFiltro, order: SELOS, rotulo: SELO_ROTULO, ajuda: "Lidas da descrição do item principal: selo, laudo, nota mínima, marca de referência, conilon." },
];
export const VALORES: [string, string][] = [["", "Qualquer"], ["a", "Até R$ 50 mil"], ["b", "R$ 50 a 200 mil"], ["c", "R$ 200 mil a 1 mi"], ["d", "Acima de R$ 1 mi"], ["n", "Sem valor (sigiloso)"]];
export const MEX = ["Exclusiva ME/EPP (todos os itens)", "Exclusiva em parte dos itens"];
export const DEF = (): Filtros => ({ q: "", niveis: [], precos: [], ufs: [], tipos: [], cats: [], embs: [], me: [], mods: [], plats: [], marcas: [], selos: [], dist: 0, distMin: 0, valor: "", hideDup: true, fav: false, novas: false, urg: false, rkg: false, viavel: false, status: "" });

export const ORDENS: [Ordem, string][] = [
  ["prazo", "Prazo mais próximo"],
  ["lucro", "Maior lucro estimado"],
  ["margem", "Maior margem estimada"],
  ["dist", "Mais perto de Uberaba"],
  ["valor", "Maior valor"],
  ["kg", "Maior volume (kg)"],
  ["folga", "Preço mais acima do típico do nível"],
  ["rkg_desc", "Maior R$/kg (torrado e moído)"],
  ["rkg_asc", "Menor R$/kg (torrado e moído)"],
  ["pub", "Publicadas mais recentemente"],
];

export const getW = (wf: MeusDados, chave: string): Anotacao => wf[chave] || {};
export const temAnotacao = (w: Anotacao | undefined): boolean => !!w && Object.keys(w).some((k) => k !== "upd" && k !== "ref");
export const follows = (w: Anotacao): boolean => !!(w.fav || w.status);

export function valorOk(c: PCompra, v: string): boolean {
  const x = c.vcafe;
  if (!v) return true;
  if (v === "n") return x == null;
  if (x == null) return false;
  return v === "a" ? x <= 5e4 : v === "b" ? x > 5e4 && x <= 2e5 : v === "c" ? x > 2e5 && x <= 1e6 : x > 1e6;
}

export function passes(c: PCompra, F: Filtros, wf: MeusDados, temPisos: boolean, skip?: string, now = Date.now()): boolean {
  const w = getW(wf, c.chave);
  if (!isOpen(c, now)) return false; // encerrada nunca aparece (pedido do dono)
  if (F.hideDup && c.dup_of && !follows(w)) return false; // nunca esconder o que você acompanha
  if (F.fav && !w.fav) return false;
  if (F.novas && !c._new) return false;
  if (F.urg) { const u = urg(c.fim, c._ms, now); if (!(u.d != null && u.d <= 3 && u.cls !== "closed")) return false; }
  if (F.rkg && rkV(c) == null) return false;
  if (F.viavel && temPisos && !(c._cmp && c._cmp.ok)) return false;
  if (F.status && (F.status === "__none" ? !!w.status : w.status !== F.status)) return false;
  if (F.dist && (c.dist == null || c.dist > F.dist)) return false;
  if (F.distMin && (c.dist == null || c.dist <= F.distMin)) return false;
  if (!valorOk(c, F.valor)) return false;
  for (const f of FACETS) {
    if (f.k === skip || !F[f.k].length) continue;
    const vs = f.get(c);
    if (!F[f.k].some((x) => vs.includes(x))) return false;
  }
  if (F.q) for (const t of nrm(F.q).split(/\s+/).filter(Boolean)) if (!c._s.includes(t)) return false;
  return true;
}

export function sortList(L: PCompra[], sort: Ordem): PCompra[] {
  const BIG = 1e15;
  const by: Record<Ordem, (c: PCompra) => number> = {
    prazo: (c) => c._ms ?? BIG,
    valor: (c) => -(c.vcafe ?? -1),
    folga: (c) => -(c._cmp && c._cmp.dif != null ? c._cmp.dif : -9),
    rkg_desc: (c) => -(rkTM(c) ?? -1),
    margem: (c) => -(c._mg ? c._mg.mp : -9),
    lucro: (c) => -(c._mg ? c._mg.lucro : -1e12),
    rkg_asc: (c) => rkTM(c) ?? BIG,
    dist: (c) => c.dist ?? BIG,
    kg: (c) => -(c.kg ?? -1),
    pub: (c) => -(toMs(c.publicado) ?? 0),
  };
  const f = by[sort] || by.prazo;
  return L.slice().sort((a, b) => f(a) - f(b) || (a._ms ?? BIG) - (b._ms ?? BIG));
}

export function activeCount(F: Filtros): number {
  let n = FACETS.reduce((a, f) => a + F[f.k].length, 0);
  (["dist", "distMin", "valor", "fav", "novas", "urg", "rkg", "viavel", "status"] as const).forEach((k) => { if (F[k]) n++; });
  if (!F.hideDup) n++;
  return n;
}

export function toggleArr(arr: string[], v: string): string[] {
  return arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v];
}
