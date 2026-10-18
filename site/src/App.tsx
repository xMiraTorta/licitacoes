import { useEffect, useRef } from "react";
import { buscar } from "./data/carregar";
import { aplicarExterno } from "./data/carregar";
import { passes, sortList } from "./lib/filtros";
import { Ajustes } from "./pages/Ajustes";
import { Guia } from "./pages/Guia";
import { Hoje } from "./pages/Hoje";
import { Mercado } from "./pages/Mercado";
import { Oportunidades } from "./pages/Oportunidades";
import { Propostas } from "./pages/Propostas";
import { Detalhe } from "./pages/Detalhe";
import { abrirDetalhe, fecharDetalhe, navegar } from "./router";
import { alternarTema, dismissBad, setPaleta, store, toast, useStore } from "./store";
import { syncAgora } from "./sync/github";
import { BottomNav } from "./ui/BottomNav";
import { useCelular } from "./ui/hooks";
import { Paleta } from "./ui/Paleta";
import { Ticker } from "./ui/Ticker";
import { Toasts } from "./ui/Toasts";
import { Provedor } from "./ui/Tooltip";
import { TopBar } from "./ui/TopBar";

/* Interface de teste (tests/test_page.py) e de depuração no console. */
declare global { interface Window { __monitor: Record<string, unknown> } }
window.__monitor = {
  count: () => { const s = store.get(); if (!s.prep) return 0; const tp = Object.values(s.pisos).some((v) => v > 0); return s.prep.compras.filter((c) => passes(c, s.F, s.wf, tp)).length; },
  lista: () => { const s = store.get(); if (!s.prep) return []; const tp = Object.values(s.pisos).some((v) => v > 0); return sortList(s.prep.compras.filter((c) => passes(c, s.F, s.wf, tp)), s.ui.sort).map((c) => c.chave); },
  open: (k: string) => abrirDetalhe(k),
  F: () => store.get().F,
  sync: () => syncAgora(),
  syncState: () => ({ estado: store.get().sync.estado, erro: store.get().sync.erro, pendente: store.get().meta.pendente }),
  data: () => store.get().data,
  apply: aplicarExterno,
  offer: aplicarExterno,
  state: () => store.get(),
  rkCheck: () => (store.get().prep?.compras || []).filter((c) => c._rk && !c._rk.outros.length && c.rkg != null && Math.abs(c._rk.main.v - c.rkg) > 0.011).map((c) => [c.chave, c.rkg, c._rk!.main.v]),
};

export function App() {
  const tab = useStore((s) => s.ui.tab);
  const carregando = useStore((s) => s.carregando);
  const erro = useStore((s) => s.erroCarga);
  const bad = useStore((s) => s.bad);
  const locked = useStore((s) => s.locked);
  const opened = useStore((s) => s.opened);
  const densidade = useStore((s) => s.ui.densidade || "normal");
  const celular = useCelular();
  useAtalhos();
  usePuxarParaAtualizar();
  // Fora de Oportunidades (e sempre no celular) o detalhe abre por cima da tela atual.
  const sobreposto = !!opened && !carregando && (tab !== "oportunidades" || celular);
  return (
    <Provedor>
      <div className="app" data-tab={tab} data-densidade={densidade}>
        <TopBar />
        <Ticker />
        <main className="main" id="main">
          {bad.length > 0 && (
            <div className="note alert fade" role="alert" data-testid="bad-data">
              <b>Atenção:</b> os dados salvos neste navegador estavam ilegíveis. {locked ? "Bloqueei a gravação para não apagar nada." : "Guardei uma cópia intacta e comecei do zero."} Se este aparelho estiver conectado ao GitHub, a última versão gravada lá volta sozinha.{" "}
              <button type="button" className="linkbtn" onClick={dismissBad}>Entendi</button>
            </div>
          )}
          {erro && <div className="note alert" role="alert"><b>Sem dados.</b> {erro} <button type="button" className="linkbtn" onClick={() => void buscar(true)}>Tentar de novo</button></div>}
          {carregando && !erro ? <Carregando /> : (
            <>
              {tab === "hoje" && <Hoje />}
              {tab === "oportunidades" && <Oportunidades />}
              {tab === "propostas" && <Propostas />}
              {tab === "mercado" && <Mercado />}
              {tab === "guia" && <Guia />}
              {tab === "ajustes" && <Ajustes />}
            </>
          )}
        </main>
        {sobreposto && (
          <div className={"drawer-wrap" + (celular ? "" : " desk")}>
            {!celular && <div className="scrim" onClick={fecharDetalhe} />}
            <Detalhe chave={opened!} celular={celular} />
          </div>
        )}
        <BottomNav />
        <Paleta />
        <Toasts />
      </div>
    </Provedor>
  );
}

function Carregando() {
  return (
    <div className="page" aria-busy="true" aria-label="Carregando os dados">
      <div className="sk" style={{ height: 28, width: 320, marginBottom: 18 }} />
      <div className="kpis">{[0, 1, 2, 3, 4].map((i) => <div key={i} className="sk" style={{ height: 118 }} />)}</div>
      <div className="sk" style={{ height: 320, marginTop: 16 }} />
    </div>
  );
}

/* Atalhos globais: / busca, Ctrl K paleta, T tema, Esc fecha, G+letra vai para a aba, ? ajustes. */
function useAtalhos() {
  const g = useRef(0);
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      const digitando = !!t && !!t.closest("input,textarea,select,[contenteditable]");
      if (e.key === "Escape") {
        const s = store.get();
        if (s.paleta) return; // o cmdk fecha
        if (s.opened) { fecharDetalhe(); return; }
        if (s.filtrosAbertos) { store.set({ filtrosAbertos: false }); return; }
        return;
      }
      if (digitando || e.ctrlKey || e.metaKey || e.altKey) return;
      if (e.key === "/") { e.preventDefault(); setPaleta(true); return; }
      if (e.key === "?") { navegar("ajustes"); return; }
      if (e.key.toLowerCase() === "t") { alternarTema(); return; }
      if (e.key.toLowerCase() === "g") { g.current = Date.now(); return; }
      if (Date.now() - g.current < 900) {
        const m: Record<string, Parameters<typeof navegar>[0]> = { h: "hoje", o: "oportunidades", p: "propostas", m: "mercado", g: "guia", c: "ajustes" };
        const alvo = m[e.key.toLowerCase()];
        if (alvo) { navegar(alvo); g.current = 0; }
      }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);
}

/* Celular: puxar a página para baixo, no topo, busca os dados de novo (bencho "Pull to refresh"). */
function usePuxarParaAtualizar() {
  useEffect(() => {
    let y0 = -1, puxou = false;
    const ini = (e: TouchEvent) => { y0 = window.scrollY <= 0 ? e.touches[0].clientY : -1; puxou = false; };
    const mov = (e: TouchEvent) => { if (y0 >= 0 && e.touches[0].clientY - y0 > 90) puxou = true; };
    const fim = () => { if (puxou) { puxou = false; toast("Buscando dados novos…"); void buscar(); } y0 = -1; };
    window.addEventListener("touchstart", ini, { passive: true });
    window.addEventListener("touchmove", mov, { passive: true });
    window.addEventListener("touchend", fim);
    return () => { window.removeEventListener("touchstart", ini); window.removeEventListener("touchmove", mov); window.removeEventListener("touchend", fim); };
  }, []);
}
