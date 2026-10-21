/* Estado da aplicação: dados publicados, anotações do dono e preferências, com persistência no navegador
   (chaves em lib/storage.ts) e os campos derivados recalculados a cada mudança relevante. */
import { useSyncExternalStore } from "react";
import { DEF } from "./lib/filtros";
import { aoFalharGravacao, BAD, K, lget, LOCKED, lset } from "./lib/storage";
import { CAMPOS_CUSTO, NIVEIS, preparar, type PCompra, type Preparado } from "./lib/modelo";
import type { Anotacao, Checklist, Filtros, MeusCustos, MeusDados, Ordem, Painel, Pisos, Tab, UIState } from "./types";

export interface SyncMeta { checklist_upd: string; pisos_upd: string; custos_upd: string; pendente: boolean }
export type SyncEstado = "local" | "salvando" | "ok" | "erro";
export interface SyncState { token: string; estado: SyncEstado; quando: string; erro: string; mudancas: number }
export interface Toast { id: number; msg: string; tipo?: "ok" | "erro" | "info"; acao?: { rotulo: string; fn: () => void }; n?: number }

export interface State {
  data: Painel | null;
  prep: Preparado | null;
  carregando: boolean;
  erroCarga: string;
  wf: MeusDados;
  ui: UIState;
  F: Filtros;
  checklist: Checklist;
  pisos: Pisos;
  custos: MeusCustos;
  meta: SyncMeta;
  sync: SyncState;
  toasts: Toast[];
  opened: string | null; // chave da licitação aberta no painel de detalhe
  paleta: boolean;
  filtrosAbertos: boolean;
  bad: string[];
  locked: boolean;
  now: number; // relógio (1x por minuto) para prazos e "fecha em"
}

const uiPadrao: UIState = { sort: "prazo", tab: "hoje", theme: "", agendaAll: false };

function carregarInicial(): State {
  const ui: UIState = { ...uiPadrao, ...lget<Partial<UIState>>(K.ui, {}) };
  const pisos = lget<Pisos>(K.pisos, {});
  if ("Sem exigência" in pisos) { // nível renomeado em 18/10/2026
    if (!("Sem categoria" in pisos)) pisos["Sem categoria"] = pisos["Sem exigência"];
    delete pisos["Sem exigência"];
    lset(K.pisos, pisos);
  }
  const F: Filtros = { ...DEF(), ...(ui.F || {}), q: "" };
  const meta: SyncMeta = { checklist_upd: "", pisos_upd: "", custos_upd: "", pendente: false, ...lget<Partial<SyncMeta>>(K.sync, {}) };
  const token = (lget<{ token?: string }>(K.github, {}) || {}).token || "";
  return {
    data: null, prep: null, carregando: true, erroCarga: "",
    wf: lget<MeusDados>(K.meusDados, {}), ui, F,
    checklist: lget<Checklist>(K.checklist, {}), pisos, custos: lget<MeusCustos>(K.custos, {}),
    meta, sync: { token, estado: token ? "salvando" : "local", quando: "", erro: "", mudancas: 0 },
    toasts: [], opened: null, paleta: false, filtrosAbertos: false,
    bad: Object.keys(BAD), locked: LOCKED.size > 0, now: Date.now(),
  };
}

let state: State = carregarInicial();
const listeners = new Set<() => void>();
const emit = (): void => listeners.forEach((l) => l());

export const store = {
  get: (): State => state,
  set(patch: Partial<State> | ((s: State) => Partial<State>)): void {
    const p = typeof patch === "function" ? patch(state) : patch;
    state = { ...state, ...p };
    emit();
  },
  subscribe(l: () => void): () => void {
    listeners.add(l);
    return () => listeners.delete(l);
  },
};

export function useStore<T>(sel: (s: State) => T): T {
  return useSyncExternalStore(store.subscribe, () => sel(state), () => sel(state));
}

/* ---------------- avisos (toasts) */
let toastId = 0;
const toastTimers = new Map<number, number>();
const armarToast = (id: number, ms: number): void => {
  window.clearTimeout(toastTimers.get(id));
  toastTimers.set(id, window.setTimeout(() => { toastTimers.delete(id); store.set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })); }, ms));
};
/* Aviso igual ao último ainda na tela (favoritar 3 seguidas) vira "×3" no mesmo aviso; no máximo 2 avisos de uma vez. */
export function toast(msg: string, tipo: Toast["tipo"] = "info", acao?: Toast["acao"]): void {
  const ultimo = state.toasts[state.toasts.length - 1];
  if (ultimo && !acao && !ultimo.acao && ultimo.msg === msg && ultimo.tipo === tipo) {
    store.set((s) => ({ toasts: s.toasts.map((t) => (t.id === ultimo.id ? { ...t, n: (t.n || 1) + 1 } : t)) }));
    armarToast(ultimo.id, 3200);
    return;
  }
  const id = ++toastId;
  store.set((s) => ({ toasts: [...s.toasts.slice(-1), { id, msg, tipo, acao }] }));
  armarToast(id, acao ? 7000 : 3200);
}
export const fecharToast = (id: number): void => store.set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }));
aoFalharGravacao((m) => toast(m, "erro"));

/* ---------------- dados publicados */
export function aplicarDados(data: Painel): void {
  const prep = preparar(data, state.pisos, state.custos);
  // Mantém o MESMO objeto de filtros se nada mudou: a lista usa a identidade dele para voltar ao início
  // (limite de linhas e cursor), e a atualização automática não pode fazer isso no meio da leitura.
  const F = state.F.dist && state.F.dist >= prep.distMax ? { ...state.F, dist: 0 } : state.F;
  const opened = state.opened && !(prep.byk[state.opened] || temAnotacao(state.wf[state.opened])) ? null : state.opened;
  store.set({ data, prep, carregando: false, erroCarga: "", F, opened });
}
export const temAnotacao = (w: Anotacao | undefined): boolean => !!w && Object.keys(w).some((k) => k !== "upd" && k !== "ref");

function recalcular(): void {
  if (!state.data) return;
  store.set({ prep: preparar(state.data, state.pisos, state.custos) });
}

/* ---------------- preferências */
export function setUI(patch: Partial<UIState>): void {
  const ui = { ...state.ui, ...patch };
  lset(K.ui, { ...ui, F: { ...state.F, q: "" } });
  store.set({ ui });
}
export function setSort(sort: Ordem): void { setUI({ sort }); }
export function setTab(tab: Tab): void { setUI({ tab }); }
export function setF(patch: Partial<Filtros> | ((f: Filtros) => Partial<Filtros>)): void {
  const p = typeof patch === "function" ? patch(state.F) : patch;
  const F = { ...state.F, ...p };
  store.set({ F });
  lset(K.ui, { ...state.ui, F: { ...F, q: "" } });
}
export const limparFiltros = (): void => setF(DEF());

export function temaAtual(): "dark" | "light" {
  if (state.ui.theme) return state.ui.theme;
  return "dark"; // escuro por padrão (decisão do dono, 18/10/2026)
}
export function alternarTema(): void {
  setUI({ theme: temaAtual() === "dark" ? "light" : "dark" });
}

/* ---------------- anotações por licitação */
let aoAlterar: ((o: "anotações" | "checklist" | "pisos" | "custos") => void) | null = null;
export const aoAlterarAnotacoes = (fn: typeof aoAlterar): void => { aoAlterar = fn; };
const refOf = (c: PCompra) => ({ mun: c.mun, uf: c.uf, orgao: c._orgao, fim: c.fim, vcafe: c.vcafe, link: c.link_pncp });

export function setW(chave: string, patch: Anotacao): void {
  const c = state.prep?.byk[chave];
  const w: Record<string, unknown> = { ...(state.wf[chave] || {}), ...patch, upd: new Date().toISOString() };
  if (c) w.ref = refOf(c);
  for (const k of Object.keys(w)) if (w[k] === "" || w[k] == null || w[k] === false) delete w[k];
  const novo = w as Anotacao;
  const wf = { ...state.wf, [chave]: temAnotacao(novo) ? novo : { upd: novo.upd } };
  lset(K.meusDados, wf);
  store.set({ wf });
  aoAlterar?.("anotações");
}

export function setChecklist(cl: Checklist): void {
  lset(K.checklist, cl);
  store.set({ checklist: cl });
  aoAlterar?.("checklist");
}

export function setPiso(nivel: string, v: number | null): void {
  const pisos = { ...state.pisos };
  if (v && v > 0) pisos[nivel] = v; else delete pisos[nivel];
  lset(K.pisos, pisos);
  const F = Object.values(pisos).some((x) => x > 0) ? state.F : { ...state.F, viavel: false };
  store.set({ pisos, F });
  recalcular();
  aoAlterar?.("pisos");
}

export function setCusto(k: string, v: number | null): void {
  const custos = { ...state.custos };
  if (v == null) delete custos[k]; else custos[k] = v;
  lset(K.custos, custos);
  store.set({ custos });
  recalcular();
  aoAlterar?.("custos");
}
export function custosPadrao(): void {
  lset(K.custos, {});
  store.set({ custos: {} });
  recalcular();
  aoAlterar?.("custos");
}

/* Aplicado pela sincronização: o que veio do GitHub mais novo que o local. */
export function aplicarJuncao(j: { md: MeusDados; cl: Checklist; clu: string; pi: Pisos; piu: string; cu: MeusCustos; cuu: string }): void {
  lset(K.meusDados, j.md); lset(K.checklist, j.cl); lset(K.pisos, j.pi); lset(K.custos, j.cu);
  const meta = { ...state.meta, checklist_upd: j.clu, pisos_upd: j.piu, custos_upd: j.cuu };
  lset(K.sync, meta);
  store.set({ wf: j.md, checklist: j.cl, pisos: j.pi, custos: j.cu, meta });
  recalcular();
}
export function setMeta(patch: Partial<SyncMeta>): void {
  const meta = { ...state.meta, ...patch };
  lset(K.sync, meta);
  store.set({ meta });
}
export const setSync = (patch: Partial<SyncState>): void => store.set((s) => ({ sync: { ...s.sync, ...patch } }));

export const CUSTO_KEYS = new Set(CAMPOS_CUSTO.map((x) => x[0]));
export const nivelValido = (n: string): boolean => (NIVEIS as string[]).includes(n);

/* ---------------- painel de detalhe e navegação */
export const abrir = (chave: string | null): void => store.set({ opened: chave });
export const setPaleta = (on: boolean): void => store.set({ paleta: on });
export const setFiltrosAbertos = (on: boolean): void => store.set({ filtrosAbertos: on });
export const dismissBad = (): void => store.set({ bad: [] });
window.setInterval(() => store.set({ now: Date.now() }), 60000);
