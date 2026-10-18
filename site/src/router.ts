/* Navegação por hash. Contrato: `#c=<chave>` abre a licitação (links do Telegram); abas em `#/hoje`, `#/oportunidades`...
   O site sempre abre em Hoje, exceto por link direto. */
import { abrir, setTab, store } from "./store";
import type { Tab } from "./types";

export const TABS: Tab[] = ["hoje", "oportunidades", "propostas", "mercado", "guia", "ajustes"];
export const TAB_NOME: Record<Tab, string> = { hoje: "Hoje", oportunidades: "Oportunidades", propostas: "Propostas", mercado: "Mercado", guia: "Guia", ajustes: "Ajustes" };

export function parseHash(h = location.hash): { tab: Tab | null; chave: string | null } {
  const m = h.match(/^#c=(.+)$/);
  if (m) return { tab: "oportunidades", chave: decodeURIComponent(m[1]) };
  const t = h.match(/^#\/([a-z]+)/);
  return { tab: t && (TABS as string[]).includes(t[1]) ? (t[1] as Tab) : null, chave: null };
}

export const podeAbrir = (chave: string): boolean => {
  const s = store.get();
  const w = s.wf[chave];
  return !!(s.prep?.byk[chave] || (w && Object.keys(w).some((k) => k !== "upd" && k !== "ref")));
};

export function navegar(tab: Tab): void {
  const alvo = "#/" + tab;
  if (store.get().opened) { // fecha o detalhe trocando de aba: substitui a entrada do histórico
    history.replaceState(null, "", alvo);
    aplicarHash();
    return;
  }
  if (location.hash !== alvo) location.hash = alvo; else aplicarHash();
}

export function abrirDetalhe(chave: string): void {
  if (!podeAbrir(chave)) return;
  const h = "#c=" + encodeURIComponent(chave);
  const jaAberto = !!store.get().opened;
  if (location.hash !== h) {
    if (jaAberto) history.replaceState(history.state, "", h); else history.pushState({ drawer: true }, "", h);
  }
  aplicarHash();
}

export function fecharDetalhe(): void {
  if (!store.get().opened) return;
  if (location.hash.startsWith("#c=")) {
    if (history.state && history.state.drawer) { history.back(); return; } // o popstate aplica
    history.replaceState(null, "", "#/oportunidades");
  }
  aplicarHash();
}

export function aplicarHash(): void {
  const { tab, chave } = parseHash();
  const s = store.get();
  if (chave && podeAbrir(chave)) {
    if (s.opened !== chave) abrir(chave); // abre por cima da aba atual (painel dividido em Oportunidades)
    return;
  }
  if (s.opened) abrir(null);
  const t = tab || "hoje";
  if (s.ui.tab !== t) setTab(t);
  if (!tab) history.replaceState(null, "", "#/hoje");
}

export function iniciarRota(): void {
  window.addEventListener("popstate", aplicarHash);
  window.addEventListener("hashchange", aplicarHash);
  // link direto para uma licitação chega antes dos dados: reaplica quando eles carregarem
  const parar = store.subscribe(() => { if (store.get().prep) { parar(); aplicarHash(); } });
  aplicarHash();
}
