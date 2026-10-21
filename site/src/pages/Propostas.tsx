/* Minhas propostas: quadro por etapa + agenda de prazos. */
import { useMemo, useState } from "react";
import { follows, getW } from "../lib/filtros";
import { BRL, BRLc, dayNum, fmtDate, fmtPrazo, licit, PCT, todayYMD, WDL } from "../lib/format";
import { isOpen, rkV, urg, type PCompra } from "../lib/modelo";
import { LinhaMini } from "./Hoje";
import { abrirDetalhe, navegar } from "../router";
import { setUI, setW, toast, useStore } from "../store";
import { GlideSelect, HoldButton } from "../ui/Controles";
import { IStar } from "../ui/icons";
import { Nivel, PrecoCmp, Prazo, Selos, UFBadge } from "../ui/Pecas";
import { Segmentado } from "../ui/Segmentado";

export function Propostas() {
  const s = useStore((x) => x);
  const [etapa, setEtapa] = useState<string | null>(null);
  const prep = s.prep!, data = s.data!, wf = s.wf;
  const abertas = useMemo(() => prep.compras.filter((c) => follows(getW(wf, c.chave))).sort((a, b) => (a._ms ?? 1e15) - (b._ms ?? 1e15)).map((c) => c.chave), [prep, wf]);
  const sumidas = useMemo(() => Object.keys(wf).filter((k) => !prep.byk[k] && follows(wf[k])).sort((a, b) => ((wf[a].ref || {}).fim || "").localeCompare((wf[b].ref || {}).fim || "")), [prep, wf]);
  const todas = abertas.concat(sumidas), st = (k: string) => wf[k]?.status || "";
  const etapas: [string, string][] = [["", "Favoritas sem status"], ...data.status_opcoes.map((x) => [x, x] as [string, string])];
  const val = abertas.reduce((a, k) => a + (prep.byk[k].vcafe || 0), 0), prox = abertas.find((k) => isOpen(prep.byk[k], s.now));
  const grupos = etapas.filter(([e]) => etapa == null || etapa === e).map(([e, t]) => [t, todas.filter((k) => st(k) === e)] as [string, string[]]).filter(([, L]) => L.length);
  return (
    <div className="page propostas">
      <div className="page-h"><h1>Minhas propostas</h1><span className="small muted">Licitações que você marcou com ★ ou às quais deu um status. Mude o status direto no cartão; em “Abrir” você edita preço e notas.</span></div>
      {!todas.length ? (
        <div className="card empty" style={{ padding: 40 }}><b>Você ainda não acompanha nenhuma licitação.</b><span>Marque ★ nas oportunidades que interessam ou dê um status a elas: elas aparecem aqui, organizadas por etapa.</span><button type="button" className="btn primary" onClick={() => navegar("oportunidades")}>Ver oportunidades</button></div>
      ) : (
        <>
          <div className="board-sum card pad">
            <div><b className="mono">{todas.length}</b> acompanhada{todas.length === 1 ? "" : "s"}{todas.length > abertas.length && <span className="small muted"> ({todas.length - abertas.length} fora dos dados)</span>}</div>
            <div>Valor em café das abertas: <b>{BRLc(val)}</b></div>
            {prox && <div>Próximo prazo: <b>{prep.byk[prox].mun} · {prep.byk[prox].uf}</b> <Prazo c={prep.byk[prox]} /></div>}
          </div>
          <div className="chips-row stages" role="tablist" aria-label="Etapas">
            <button type="button" className="chip" aria-pressed={etapa == null} onClick={() => setEtapa(null)} data-stage="__all">Todas<i>{todas.length}</i></button>
            {etapas.map(([e, t]) => { const n = todas.filter((k) => st(k) === e).length; return <button key={e} type="button" className={"chip" + (n ? "" : " zero")} aria-pressed={etapa === e} onClick={() => setEtapa(etapa === e ? null : e)} data-stage={e}>{t}<i>{n}</i></button>; })}
          </div>
          <div id="board">
            {grupos.length ? grupos.map(([t, L]) => (
              <section key={t} className="stage-g"><h3>{t} <span className="cnt">{L.length}</span></h3><div className="props">{L.map((k) => <PropCard key={k} k={k} />)}</div></section>
            )) : <div className="card empty"><b>Nenhuma licitação nesta etapa.</b></div>}
          </div>
        </>
      )}
      <Agenda />
    </div>
  );
}

function PropCard({ k }: { k: string }) {
  const c = useStore((s) => s.prep!.byk[k]) as PCompra | undefined;
  const w = useStore((s) => s.wf[k]) || {};
  const data = useStore((s) => s.data)!;
  const r = w.ref || {};
  const mun = c ? c.mun : r.mun, uf = c ? c.uf : r.uf, org = c ? c._orgao : r.orgao, val = c ? c.vcafe : r.vcafe;
  const x = c && c._cmp, m = c && w.preco && rkV(c) ? (rkV(c)! - w.preco) / rkV(c)! : null;
  return (
    <article className="prop card" data-ch={k}>
      <header>
        <button type="button" className={"star" + (w.fav ? " on" : "")} data-act="fav" aria-label={w.fav ? "Remover dos favoritos" : "Marcar como favorito"} onClick={() => { const on = !w.fav; setW(k, { fav: on }); toast(on ? "★ Adicionada aos favoritos" : "Removida dos favoritos"); }}><IStar size={16} filled={!!w.fav} /></button>
        <div className="pt"><b>{mun ? `${mun} · ${uf}` : k}</b><span className="small muted ell">{org || ""}</span></div>
        {c ? <Prazo c={c} /> : <span className="pill closed"><span className="dot" />Fora dos dados</span>}
      </header>
      <div className="pf num">
        <div><small>Prazo</small>{c ? fmtPrazo(c.fim) : fmtDate(r.fim)}</div>
        <div><small>Valor (café)</small>{val != null ? BRLc(val) : "—"}</div>
        <div><small>Órgão paga</small>{x ? <>{BRL(x.i.rkg)}/kg <PrecoCmp c={c!} /></> : "—"}</div>
        <div><small>Meu preço</small>{w.preco ? <>{BRL(w.preco)}/kg{m != null && <> <span className={"mg " + (m >= 0 ? "pos" : "neg")}>{PCT(m)}</span></>}</> : "—"}</div>
      </div>
      {c && c._niv && <div className="pl"><UFBadge c={c} /><Nivel n={c._niv} /><Selos c={c} /></div>}
      {w.notas && <p className="pn small">{w.notas}</p>}
      <footer>
        <GlideSelect valor={w.status || ""} opcoes={data.status_opcoes} vazio="Sem status" onChange={(v) => { setW(k, { status: v }); toast(v ? `Status: ${v}` : "Status removido"); }} rotulo="Status" testid={"st-" + k} />
        <button type="button" className="btn sm" data-open={k} onClick={() => abrirDetalhe(k)}>Abrir</button>
        <HoldButton className="btn sm ghost" onConfirm={() => { setW(k, { fav: false, status: "" }); toast("Saiu de Minhas propostas (preço e notas continuam guardados)"); }} testid={"unfollow-" + k}>Parar de acompanhar</HoldButton>
      </footer>
    </article>
  );
}

function Agenda() {
  const s = useStore((x) => x);
  const prep = s.prep!, wf = s.wf;
  const anyMine = prep.compras.some((c) => follows(getW(wf, c.chave)) && isOpen(c, s.now));
  const all = s.ui.agendaAll || !anyMine;
  const L = prep.compras.filter((c) => c.fim && isOpen(c, s.now) && (all ? !c.dup_of : follows(getW(wf, c.chave)))).sort((a, b) => a._ms! - b._ms!);
  const t0 = dayNum(todayYMD()), byDay = new Map<string, PCompra[]>();
  L.forEach((c) => { const k = c.fim!.slice(0, 10); if (!byDay.has(k)) byDay.set(k, []); byDay.get(k)!.push(c); });
  const [maxDias, setMaxDias] = useState(all ? 5 : 45);
  const todosDias = [...byDay.entries()];
  const days = todosDias.slice(0, maxDias);
  return (
    <section className="agenda" id="agenda" aria-label="Agenda de prazos">
      <div className="card-h" style={{ padding: "8px 0" }}>
        <div><h2>Agenda de prazos</h2><div className="sub small muted">{all ? "Todas as abertas, por dia de encerramento" : "Só as que você acompanha"}</div></div>
        <Segmentado rotulo="Quais" valor={all ? "1" : "0"} onChange={(v) => { setUI({ agendaAll: v === "1" }); setMaxDias(v === "1" ? 5 : 45); }} opcoes={anyMine ? [["0", "Minhas"], ["1", "Todas"]] : [["1", "Todas"]]} pequeno />
      </div>
      {days.length ? days.map(([k, cs]) => {
        const d = dayNum(k) - t0, dt = new Date(dayNum(k) * 864e5);
        const rel = d === 0 ? "hoje" : d === 1 ? "amanhã" : `em ${d} dias`;
        return (
          <div key={k} className={"day" + (d === 0 ? " today" : "")}>
            <h3>{WDL[dt.getUTCDay()]}, {k.slice(8, 10)}/{k.slice(5, 7)} <span className="small muted">{rel} · {licit(cs.length)}</span></h3>
            <div className="minis">{cs.map((c) => <LinhaMini key={c.chave} c={c} />)}</div>
          </div>
        );
      }) : <div className="card empty"><b>Nenhum prazo pela frente.</b></div>}
      {todosDias.length > maxDias && <div className="more"><button type="button" className="btn" onClick={() => setMaxDias((d) => d + 7)}>Mostrar mais dias ({todosDias.length - maxDias} com prazo)</button></div>}
    </section>
  );
}

export const urgencia = urg;
