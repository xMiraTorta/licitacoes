/* Oportunidades: filtros, lista e painel de detalhe (redimensionável no computador, tela cheia no celular). */
import { AnimatePresence, LayoutGroup, motion } from "motion/react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Group, Panel, Separator } from "react-resizable-panels";
import { activeCount, FACETS, follows, getW, MEX, ORDENS, passes, sortList, toggleArr, VALORES } from "../lib/filtros";
import { BRL, BRLc, fmtMin, fmtPrazo, KG, n0 } from "../lib/format";
import { isOpen, rkLbl, rkV, tiposTexto, urg, type PCompra } from "../lib/modelo";
import { abrirDetalhe, fecharDetalhe } from "../router";
import { limparFiltros, setF, setFiltrosAbertos, setSort, setUI, setW, toast, useStore, type State } from "../store";
import { IFilter, IStar, IX } from "../ui/icons";
import { useCelular } from "../ui/hooks";
import { Margem, MeBadge, Nivel, PisoChip, PrecoCmp, Prazo, Selos, UFBadge } from "../ui/Pecas";
import { Dica } from "../ui/Tooltip";
import { Detalhe } from "./Detalhe";

const PASSO = 60;
const temPisos = (s: State): boolean => Object.values(s.pisos).some((v) => v > 0);

export function Oportunidades() {
  const s = useStore((x) => x);
  const celular = useCelular();
  const [limite, setLimite] = useState(PASSO);
  const [cursor, setCursor] = useState(-1);
  const tp = temPisos(s);
  const L = useMemo(() => (s.prep ? sortList(s.prep.compras.filter((c) => passes(c, s.F, s.wf, tp, undefined, s.now)), s.ui.sort) : []), [s.prep, s.F, s.wf, s.ui.sort, tp, s.now]);
  useEffect(() => { setLimite(PASSO); setCursor(-1); }, [s.F, s.ui.sort]);
  const listaRef = useRef<HTMLDivElement>(null);
  // j/k andam na lista, f favorita, Enter abre
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && t.closest("input,textarea,select,[contenteditable],[role=dialog],[role=listbox]")) return;
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      if (e.key === "j" || e.key === "k") {
        e.preventDefault();
        setCursor((c) => { const n = Math.max(0, Math.min(Math.min(L.length, limite) - 1, c + (e.key === "j" ? 1 : -1))); listaRef.current?.querySelectorAll<HTMLElement>(".row")[n]?.scrollIntoView({ block: "nearest" }); return n; });
      } else if (e.key === "f" && cursor >= 0 && L[cursor]) { const c = L[cursor]; const on = !getW(s.wf, c.chave).fav; setW(c.chave, { fav: on }); toast(on ? "★ Adicionada aos favoritos" : "Removida dos favoritos"); }
      else if (e.key === "Enter" && cursor >= 0 && L[cursor] && !s.opened) abrirDetalhe(L[cursor].chave);
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [L, cursor, limite, s.wf, s.opened]);
  if (!s.prep) return null;
  const tot = L.reduce((a, c) => a + (c.vcafe || 0), 0);
  const lista = (
    <div className="opp-list" ref={listaRef}>
      <div className="resbar"><span><b>{n0(L.length)}</b> licitaç{L.length === 1 ? "ão" : "ões"} · <b>{BRLc(tot)}</b> em café</span>{s.opened && !celular && <span className="small muted">Esc fecha o detalhe · j/k andam · f favorita</span>}</div>
      {!L.length ? (
        <div className="card empty"><b>Nenhuma licitação com esses filtros.</b><button type="button" className="btn" onClick={limparFiltros}>Limpar filtros</button></div>
      ) : (
        <div className="list" role="list">
          <div className="lhead lbl"><span /><span>Prazo</span><span>Local e órgão</span><span>O que pedem</span><span className="r">Volume · valor</span><span className="r">R$/kg órgão</span><span className="r">Margem · lucro</span><span>Minha proposta</span></div>
          <LayoutGroup>
            <AnimatePresence initial={false}>
              {L.slice(0, limite).map((c, i) => <Linha key={c.chave} c={c} sel={s.opened === c.chave} foco={cursor === i} compacto={!!s.opened && !celular} />)}
            </AnimatePresence>
          </LayoutGroup>
        </div>
      )}
      {L.length > limite && <div className="more"><button type="button" className="btn" onClick={() => setLimite((l) => l + PASSO)}>Mostrar mais {Math.min(PASSO, L.length - limite)} (faltam {L.length - limite})</button></div>}
    </div>
  );
  return (
    <div className={"page opp" + (s.opened ? " com-detalhe" : "")}>
      <Toolbar s={s} />
      <div className="opp-body">
        {(s.filtrosAbertos || !celular) && <Filtros s={s} celular={celular} />}
        {celular ? lista : s.opened ? (
          <Group orientation="horizontal" className="split" defaultLayout={s.ui.split ? { lista: s.ui.split, detalhe: 100 - s.ui.split } : undefined} onLayoutChanged={(l) => { const v = (l as Record<string, number>).lista; if (v) setUI({ split: Math.round(v) }); }}>
            <Panel id="lista" minSize="34" defaultSize="52">{lista}</Panel>
            <Separator className="split-sep" aria-label="Arraste para redimensionar" />
            <Panel id="detalhe" minSize="34" defaultSize="48"><Detalhe chave={s.opened} /></Panel>
          </Group>
        ) : lista}
      </div>
    </div>
  );
}

function Toolbar({ s }: { s: State }) {
  const prep = s.prep!, F = s.F;
  const n = (fn: (c: PCompra) => boolean) => prep.compras.filter((c) => isOpen(c, s.now) && !c.dup_of && fn(c)).length;
  const nov = n((c) => c._new);
  const quick: [string, string, number, boolean, () => void][] = [
    ["uf:MG", "MG", n((c) => c.uf === "MG"), F.ufs.includes("MG"), () => setF({ ufs: toggleArr(F.ufs, "MG") })],
    ["uf:SP", "SP", n((c) => c.uf === "SP"), F.ufs.includes("SP"), () => setF({ ufs: toggleArr(F.ufs, "SP") })],
    ["uf:GO", "GO", n((c) => c.uf === "GO"), F.ufs.includes("GO"), () => setF({ ufs: toggleArr(F.ufs, "GO") })],
    ["d300", "Até 300 km", n((c) => c.dist != null && c.dist <= 300), F.dist === 300, () => setF({ dist: F.dist === 300 ? 0 : 300 })],
    ["urg", "Urgentes", n((c) => { const u = urg(c.fim, c._ms, s.now); return u.d != null && u.d <= 3; }), F.urg, () => setF({ urg: !F.urg })],
    ["me", "Exclusivas ME/EPP", n((c) => c.me_f.some((x) => MEX.includes(x))), MEX.every((x) => F.me.includes(x)), () => { const on = MEX.every((x) => F.me.includes(x)); setF({ me: on ? F.me.filter((x) => !MEX.includes(x)) : [...F.me.filter((x) => !MEX.includes(x)), ...MEX] }); }],
    ["fav", "★ Favoritos", prep.compras.filter((c) => getW(s.wf, c.chave).fav).length, F.fav, () => setF({ fav: !F.fav })],
  ];
  if (nov || F.novas) quick.splice(4, 0, ["novas", "Novas", nov, F.novas, () => setF({ novas: !F.novas })]);
  const ativos: [string, string, () => void][] = [];
  if (F.q) ativos.push(["q", `“${F.q}”`, () => setF({ q: "" })]);
  FACETS.forEach((f) => F[f.k].forEach((v) => ativos.push([f.k + "|" + v, v, () => setF({ [f.k]: toggleArr(F[f.k], v) } as Partial<typeof F>)])));
  if (F.dist) ativos.push(["dist", `Até ${n0(F.dist)} km`, () => setF({ dist: 0 })]);
  if (F.distMin) ativos.push(["distMin", `Além de ${n0(F.distMin)} km`, () => setF({ distMin: 0 })]);
  if (F.valor) ativos.push(["valor", VALORES.find((x) => x[0] === F.valor)![1], () => setF({ valor: "" })]);
  if (F.fav) ativos.push(["fav", "★ Favoritos", () => setF({ fav: false })]);
  if (F.novas) ativos.push(["novas", "Novas", () => setF({ novas: false })]);
  if (F.urg) ativos.push(["urg", "Urgentes", () => setF({ urg: false })]);
  if (F.rkg) ativos.push(["rkg", "Com R$/kg", () => setF({ rkg: false })]);
  if (F.viavel) ativos.push(["viavel", "Cobrem meu piso", () => setF({ viavel: false })]);
  if (F.status) ativos.push(["status", F.status === "__none" ? "Sem status" : F.status, () => setF({ status: "" })]);
  if (!F.hideDup) ativos.push(["dup", "Mostrando duplicatas", () => setF({ hideDup: true })]);
  const ac = activeCount(F);
  return (
    <div className="opp-tools">
      <div className="opp-tools-row">
        <button type="button" className="btn" onClick={() => setFiltrosAbertos(!s.filtrosAbertos)} aria-expanded={s.filtrosAbertos} data-testid="btn-filtros"><IFilter size={15} /> Filtros{ac > 0 && <span className="badge b-near">{ac}</span>}</button>
        <div className="chips-row quick">{quick.map(([k, l, c, on, fn]) => <button key={k} type="button" className="chip" aria-pressed={on} onClick={fn} data-q={k}>{l}<i>{c}</i></button>)}</div>
        <span className="grow" />
        <label className="sr" htmlFor="sort">Ordenar</label>
        <select id="sort" className="inp sel" value={s.ui.sort} onChange={(e) => setSort(e.target.value as typeof s.ui.sort)} aria-label="Ordenar">{ORDENS.map(([k, t]) => <option key={k} value={k}>{t}</option>)}</select>
      </div>
      {(ativos.length > 0 || F.q) && (
        <div className="active-f">
          {F.q ? null : null}
          <input className="inp q" type="search" placeholder="Buscar nesta lista" value={F.q} onChange={(e) => setF({ q: e.target.value })} aria-label="Filtrar por texto" id="q" />
          {ativos.map(([k, l, fn]) => <button key={k} type="button" className="af" onClick={fn} data-rm={k}>{l}<IX size={12} /></button>)}
          {ativos.length > 1 && <button type="button" className="linkbtn" onClick={limparFiltros} data-rm="__all">Limpar tudo</button>}
        </div>
      )}
      {ativos.length === 0 && !F.q && <div className="active-f"><input className="inp q" type="search" placeholder="Buscar nesta lista (município, órgão, nº)" value={F.q} onChange={(e) => setF({ q: e.target.value })} aria-label="Filtrar por texto" id="q" /></div>}
    </div>
  );
}

function Filtros({ s, celular }: { s: State; celular: boolean }) {
  const prep = s.prep!, F = s.F, tp = temPisos(s);
  const data = s.data!;
  const secoes = FACETS.map((f) => {
    const cnt: Record<string, number> = {};
    prep.compras.filter((c) => passes(c, F, s.wf, tp, f.k, s.now)).forEach((c) => new Set(f.get(c)).forEach((v) => (cnt[v] = (cnt[v] || 0) + 1)));
    const all = new Set<string>();
    prep.compras.forEach((c) => f.get(c).forEach((v) => all.add(v)));
    const pri = (v: string) => (v === "MG" ? 2 : v === "SP" || v === "GO" ? 1 : 0);
    const vals = f.order ? f.order.filter((v) => all.has(v)) : [...all].sort((a, b) => (f.k === "ufs" ? pri(b) - pri(a) : 0) || (cnt[b] || 0) - (cnt[a] || 0) || a.localeCompare(b));
    const sel = F[f.k];
    return (
      <details key={f.k} className="fsec" data-sec={f.k} open={!!(f.open || sel.length)}>
        <summary>{f.t}{sel.length > 0 && <span className="cnt">{sel.length} selec.</span>}</summary>
        {f.ajuda && <p className="tiny muted" style={{ margin: "0 0 6px" }}>{f.ajuda}</p>}
        <div className="opts">{vals.map((v) => <button key={v} type="button" className={"opt" + (cnt[v] ? "" : " zero")} aria-pressed={sel.includes(v)} onClick={() => setF({ [f.k]: toggleArr(sel, v) } as Partial<typeof F>)} data-f={f.k} data-v={v}>{v}<i>{cnt[v] || 0}</i></button>)}</div>
      </details>
    );
  });
  const corpo = (
    <>
      <div className="f-head"><h2>Filtros</h2><button type="button" className="linkbtn" onClick={limparFiltros}>Limpar tudo</button>{celular && <button type="button" className="btn icon ghost" aria-label="Fechar filtros" onClick={() => setFiltrosAbertos(false)}><IX /></button>}</div>
      <div className="f-body">
        {secoes[0]}{secoes[1]}
        {tp && <details className="fsec" data-sec="piso" open><summary>Meu piso de preço</summary><label className="toggle">Só as que cobrem meu piso<input type="checkbox" checked={F.viavel} onChange={(e) => setF({ viavel: e.target.checked })} data-t="viavel" /></label></details>}
        {secoes[2]}{secoes[3]}
        <details className="fsec" data-sec="dist" open><summary>Distância de {prep.origem}</summary>
          <div className="range-l"><span>Por estrada</span><b>{F.dist ? "Até " + n0(F.dist) + " km" : "Qualquer distância"}</b></div>
          <input type="range" className="range" min={100} max={prep.distMax} step={50} value={F.dist || prep.distMax} onChange={(e) => { const v = +e.target.value; setF({ dist: v >= prep.distMax ? 0 : v }); }} aria-label="Distância máxima em km" id="dist" />
          <div className="range-l tiny muted"><span>100 km</span><span>{n0(prep.distMax)} km</span></div>
        </details>
        {secoes[4]}{secoes[5]}{secoes[6]}
        <details className="fsec" data-sec="valor" open><summary>Valor estimado (café)</summary><div className="opts">{VALORES.map(([k, l]) => <button key={k} type="button" className="opt" aria-pressed={F.valor === k} onClick={() => setF({ valor: F.valor === k ? "" : k })} data-valor={k}>{l}</button>)}</div></details>
        {secoes[7]}{secoes[8]}{secoes[9]}
        <details className="fsec" data-sec="meu" open><summary>Meu acompanhamento</summary>
          <label className="toggle">Só meus favoritos ★<input type="checkbox" checked={F.fav} onChange={(e) => setF({ fav: e.target.checked })} data-t="fav" /></label>
          <select className="inp" value={F.status} onChange={(e) => setF({ status: e.target.value })} aria-label="Status da proposta" id="stsel" style={{ marginTop: 6 }}><option value="">Qualquer status</option><option value="__none">Sem status</option>{data.status_opcoes.map((o) => <option key={o} value={o}>{o}</option>)}</select>
        </details>
        <details className="fsec" data-sec="opc" open><summary>Opções</summary>
          <label className="toggle">Ocultar possíveis duplicatas<input type="checkbox" checked={F.hideDup} onChange={(e) => setF({ hideDup: e.target.checked })} data-t="hideDup" /></label>
          <label className="toggle">Só novas (última coleta)<input type="checkbox" checked={F.novas} onChange={(e) => setF({ novas: e.target.checked })} data-t="novas" /></label>
          <label className="toggle">Só urgentes (até 3 dias)<input type="checkbox" checked={F.urg} onChange={(e) => setF({ urg: e.target.checked })} data-t="urg" /></label>
          <label className="toggle">Só com R$/kg calculado<input type="checkbox" checked={F.rkg} onChange={(e) => setF({ rkg: e.target.checked })} data-t="rkg" /></label>
        </details>
      </div>
      {celular && <div className="f-foot"><button type="button" className="btn" onClick={limparFiltros}>Limpar</button><button type="button" className="btn primary" onClick={() => setFiltrosAbertos(false)}>Ver resultados</button></div>}
    </>
  );
  if (celular) return <div className="filters-overlay" role="dialog" aria-label="Filtros"><div className="scrim" onClick={() => setFiltrosAbertos(false)} /><aside className="filters sheet">{corpo}</aside></div>;
  return <aside className={"filters" + (s.filtrosAbertos ? " show" : "")} aria-label="Filtros">{corpo}</aside>;
}

function Linha({ c, sel, foco, compacto }: { c: PCompra; sel: boolean; foco: boolean; compacto: boolean }) {
  const w = useStore((s) => s.wf[c.chave]) || {};
  const F = useStore((s) => s.F);
  const r = c._cmp ? c._cmp.i.rkg : rkV(c);
  const val = c.vcafe == null ? <span className="na">{c.sig !== "Não" ? "Sigiloso" : "—"}</span> : BRLc(c.vcafe);
  const fav = (e: React.MouseEvent) => { e.stopPropagation(); const on = !w.fav; setW(c.chave, { fav: on }); toast(on ? "★ Adicionada aos favoritos" : "Removida dos favoritos"); };
  return (
    <motion.div layout="position" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.18 }}
      className={"row" + (sel ? " sel-row" : "") + (foco ? " foco" : "") + (compacto ? " compacto" : "")} data-ch={c.chave} role="listitem" tabIndex={0}
      onClick={() => abrirDetalhe(c.chave)} onKeyDown={(e) => { if (e.key === "Enter") abrirDetalhe(c.chave); }}>
      <div className="c-star"><button type="button" className={"star" + (w.fav ? " on" : "")} data-act="fav" aria-label={w.fav ? "Remover dos favoritos" : "Marcar como favorito"} onClick={fav}><IStar size={16} filled={!!w.fav} /></button></div>
      <div className="c-prazo"><Prazo c={c} /><div className="small muted" style={{ marginTop: 3 }}>{fmtPrazo(c.fim)}</div></div>
      <div className="c-loc">
        <div className="l1"><UFBadge c={c} /> {c.mun} {c._new && <span className="badge b-new">Nova</span>} {c.dup && !F.hideDup && <span className="badge b-dup">duplicata?</span>}</div>
        <div className="small muted ell">{c.dist != null ? `${n0(c.dist)} km${c.dist_min != null ? " · " + fmtMin(c.dist_min) : ""} · ` : ""}{c._orgao}</div>
      </div>
      <div className="c-cafe">
        <div className="l1" style={{ fontWeight: 550 }}>{tiposTexto(c.tipos)} <MeBadge c={c} /></div>
        <div className="small muted">{c._niv ? <Nivel n={c._niv} /> : c.mod + " " + c.num}</div>
        <Selos c={c} />
      </div>
      <div className="c-valor r"><div className="v num">{c.kg == null ? <span className="na">—</span> : (c._parcial ? "≥ " : "") + KG(c.kg)}</div><div className="small muted num">{val}</div></div>
      <div className="c-rkg r">{r == null ? <div className="small na">sem preço</div> : <div className="v num">{BRL(r)}</div>}<div className="small muted"><PrecoCmp c={c} />{!c._cmp && rkLbl(c)}</div><PisoChip c={c} /></div>
      <div className="c-mg r">{c._mg ? <><Margem c={c} curto /><div className="small muted num">{c._mg.lucro >= 0 ? "+" : "−"}{BRLc(Math.abs(c._mg.lucro))}</div></> : null}</div>
      <div className="c-status">{w.status ? <span className={"st " + stCls(w.status)}>{w.status}</span> : null}{w.preco ? <div className="small muted num">meu: {BRL(w.preco)}/kg</div> : null}</div>
    </motion.div>
  );
}
import { stCls } from "../ui/Controles";

export function RowFavoritoDica() { return <Dica texto="Favorito">★</Dica>; }
export { fecharDetalhe, follows };
