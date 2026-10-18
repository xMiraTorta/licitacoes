import { fmtDate } from "../lib/format";
import { follows, getW } from "../lib/filtros";
import { isOpen } from "../lib/modelo";
import { navegar, TAB_NOME } from "../router";
import { alternarTema, setPaleta, temaAtual, useStore } from "../store";
import { REPO } from "../sync/github";
import { Bandeira, IMoon, ISearch, ISettings, ISun } from "./icons";
import { Dica } from "./Tooltip";

export function TopBar() {
  const tab = useStore((s) => s.ui.tab);
  const data = useStore((s) => s.data);
  const prep = useStore((s) => s.prep);
  const wf = useStore((s) => s.wf);
  const sync = useStore((s) => s.sync);
  const meta = useStore((s) => s.meta);
  const theme = useStore((s) => s.ui.theme);
  const nAbertas = prep ? prep.compras.filter((c) => isOpen(c) && !c.dup_of).length : 0;
  const nMinhas = prep ? prep.compras.filter((c) => follows(getW(wf, c.chave))).length + Object.keys(wf).filter((k) => !prep.byk[k] && follows(wf[k])).length : 0;
  const st = !REPO ? "local" : sync.estado === "erro" ? "erro" : sync.estado === "salvando" || (meta.pendente && sync.token) ? "salvando" : sync.token ? "ok" : "local";
  const stLbl = { ok: "Anotações salvas no GitHub", salvando: "Salvando anotações…", erro: "Erro ao salvar no GitHub: " + sync.erro, local: REPO ? "Anotações só neste aparelho (conecte em Ajustes)" : "Anotações só neste navegador" }[st];
  const escuro = (theme || temaAtual()) === "dark";
  return (
    <header className="topbar">
      <div className="topbar-in">
        <a href="#/hoje" className="brand" onClick={(e) => { e.preventDefault(); navegar("hoje"); }} aria-label="Monitor de Licitações, início">
          <Bandeira size={26} /><span className="brand-t">Monitor</span>
        </a>
        <nav className="tabs" aria-label="Seções" role="tablist">
          {(["hoje", "oportunidades", "propostas", "mercado", "guia"] as const).map((t) => (
            <button key={t} type="button" role="tab" className="tab" aria-selected={tab === t} onClick={() => navegar(t)} data-tab={t}>
              {TAB_NOME[t]}{t === "oportunidades" && <i className="n mono">{nAbertas}</i>}{t === "propostas" && <i className="n mono" id="n-mine">{nMinhas}</i>}
            </button>
          ))}
        </nav>
        <div className="grow" />
        <button type="button" className="search-btn" onClick={() => setPaleta(true)} aria-label="Buscar ou fazer algo (Ctrl K)">
          <ISearch size={16} /><span className="search-t">Buscar ou fazer algo</span><kbd>Ctrl K</kbd>
        </button>
        {data && (
          <Dica texto={`Dados do PNCP de ${fmtDate(data.gerado_em.slice(0, 16))} (horário de Brasília). A coleta roda nos dias úteis às 8h07; a página confere dados novos a cada 15 min. ${stLbl}.`}>
            <span className="status-pill" id="upd" data-sync={st}>
              <span className={"sdot " + st} aria-hidden="true" />
              <span className="status-t">Dados de <b>{fmtDate(data.gerado_em.slice(0, 16))}</b></span>
            </span>
          </Dica>
        )}
        <Dica texto={escuro ? "Tema claro (T)" : "Tema escuro (T)"}>
          <button type="button" className="btn icon ghost" id="themeBtn" onClick={alternarTema} aria-label="Alternar tema claro/escuro">{escuro ? <ISun /> : <IMoon />}</button>
        </Dica>
        <Dica texto="Meus custos, pisos, sincronização e atalhos">
          <button type="button" className={"btn icon ghost" + (tab === "ajustes" ? " on" : "")} onClick={() => navegar("ajustes")} aria-label="Ajustes" data-tab="ajustes"><ISettings /></button>
        </Dica>
      </div>
    </header>
  );
}
