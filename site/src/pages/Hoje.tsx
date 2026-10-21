/* Tela Hoje: o painel do dia, todo calculado dos dados publicados. */
import { useMemo, useState } from "react";
import { Barras } from "../charts/Barras";
import { Donut } from "../charts/Donut";
import { Faixas } from "../charts/Faixas";
import { Hbar, Sparkline, Stacked } from "../charts/Hbar";
import { Mapa, type Ponto } from "../charts/Mapa";
import { abertas, embalagem, exigencias, faixasPorNivel, funil, insights, kpis, marcasCitadas, porUF, prazosPorDia, prazosPorSemana, simulador } from "../lib/dash";
import { DEF, follows, MEX } from "../lib/filtros";
import { BRL, BRLc, dayNum, fmtPrazo, KGc, licit, MESES_L, n0, n2, PCTi, todayYMD, WDL } from "../lib/format";
import { mgCls, NIVEIS, NIVEL_CURTO, urg, varejoTxt, type PCompra } from "../lib/modelo";
import { abrirDetalhe, navegar } from "../router";
import { setF, setSort, useStore } from "../store";
import { Contador } from "../ui/Contador";
import { IArrow, IMinus, IPlus } from "../ui/icons";
import { Margem, MeBadge, Nivel, Prazo, UFBadge } from "../ui/Pecas";
import { Segmentado } from "../ui/Segmentado";
import { Dica, Termo } from "../ui/Tooltip";

const CUMPRIMENTO = (): string => { const h = new Date().getHours(); return h < 12 ? "Bom dia" : h < 18 ? "Boa tarde" : "Boa noite"; };

export function Hoje() {
  const prep = useStore((s) => s.prep)!;
  const data = useStore((s) => s.data)!;
  const wf = useStore((s) => s.wf);
  const pisos = useStore((s) => s.pisos);
  const now = useStore((s) => s.now);
  const O = useMemo(() => abertas(prep, now), [prep, now]);
  const k = useMemo(() => kpis(O, wf, prep.compras, now), [O, wf, prep, now]);
  const uf = useMemo(() => porUF(O), [O]);
  const hoje = todayYMD(), d = new Date(dayNum(hoje) * 864e5);
  const irLista = (f: Partial<ReturnType<typeof DEF>>, sort?: Parameters<typeof setSort>[0]) => { setF({ ...DEF(), ...f }); if (sort) setSort(sort); navegar("oportunidades"); };
  const etapas = useMemo(() => etapasMinhas(wf, data.status_opcoes), [wf, data.status_opcoes]);
  return (
    <div className="page hoje">
      <div className="page-h">
        <h1>{CUMPRIMENTO()} <span className="muted" style={{ fontWeight: 400 }}>· {WDL[d.getUTCDay()]}, {d.getUTCDate()} de {MESES_L[d.getUTCMonth()]}</span></h1>
        <span className="small muted">{licit(k.n)} de café abertas · {k.fecham7} fecham em 7 dias · {k.amanha} amanhã{k.novas ? ` · ${k.novas} novas` : ""}</span>
      </div>

      <section className="kpis stag" aria-label="Resumo">
        <button type="button" className="kpi card fade" data-k="all" onClick={() => irLista({})}>
          <span className="lbl">Abertas</span>
          <span className="v"><Contador valor={k.n} fmt={(x) => n0(Math.round(x))} /></span>
          <span className="s">{KGc(k.kg)} de café · {BRLc(k.vcafe)}</span>
          <Sparkline valores={k.publicadas.map((p) => p.n)} />
          <span className="tiny muted">publicadas por dia · {k.semana} nos últimos 7 dias</span>
        </button>
        <button type="button" className="kpi card fade" data-k="lucro" onClick={() => irLista({}, "lucro")}>
          <span className="lbl">Dão lucro</span>
          <span className="v"><Contador valor={k.lucro} fmt={(x) => n0(Math.round(x))} /> <span className="v-sub">de {k.comCusto} com custo</span></span>
          <span className="s">margem típica <b>{k.mpTipica != null ? PCTi(k.mpTipica) : "—"}</b>{k.mp25 != null ? ` · faixa comum ${PCTi(k.mp25!)} a ${PCTi(k.mp75!)}` : ""}</span>
          <Stacked partes={[{ v: k.boas, cls: "bom", t: "com margem boa" }, { v: k.apertadas, cls: "ap", t: "apertadas" }, { v: k.preju, cls: "preju", t: "prejuízo" }, { v: k.sem, cls: "sem", t: "sem preço" }]} />
          <span className="tiny muted">{k.boas} boas · {k.apertadas} apertadas · {k.preju} prejuízo · {k.sem} sem preço</span>
        </button>
        <button type="button" className="kpi card fade" data-k="urg" onClick={() => irLista({}, "prazo")}>
          <span className="lbl">Fecham em 7 dias</span>
          <span className="v"><Contador valor={k.fecham7} fmt={(x) => n0(Math.round(x))} /></span>
          <span className="s serious" style={{ fontWeight: 600 }}>{k.fecham3} em até 3 dias · {k.amanha} amanhã</span>
          <Stacked partes={k.fechamSemana.map((x, i) => ({ v: x.n, cls: "ser o" + Math.min(i, 5), t: "em " + fmtPrazo(x.dia).slice(0, 3) }))} />
          <span className="tiny muted">{k.fechamSemana.slice(0, 5).map((x) => fmtPrazo(x.dia).slice(0, 3).replace(".", "") + " " + x.n).join(" · ")}</span>
        </button>
        <button type="button" className="kpi card fade" data-k="lucroTotal" onClick={() => irLista({}, "lucro")}>
          <span className="lbl">Lucro potencial</span>
          <span className="v">{k.lucroTotal >= 1e6 ? <><Contador valor={k.lucroTotal / 1e6} fmt={(x) => "R$ " + x.toFixed(1).replace(".", ",")} /> <span className="v-sub">mi</span></> : BRLc(k.lucroTotal)}</span>
          <span className="s">somando as {k.lucro} que dão lucro ao preço do órgão</span>
          <Stacked partes={k.lucroDist.map(([t, v], i) => ({ v, cls: "acc o" + i, t }))} />
          <span className="tiny muted">{k.lucroDist.map(([t, v]) => `${t.replace("acima de ", "além de ")} ${k.lucroTotal ? Math.round((v / k.lucroTotal) * 100) : 0}%`).join(" · ")}</span>
        </button>
        <button type="button" className="kpi card fade" data-k="mine" onClick={() => navegar("propostas")}>
          <span className="lbl">Minhas propostas</span>
          <span className="v"><Contador valor={etapas.total} fmt={(x) => n0(Math.round(x))} /></span>
          <span className="s">{etapas.total ? "em acompanhamento" : "nenhuma em andamento"}</span>
          {etapas.total ? <Stacked partes={etapas.partes.map((e) => ({ v: e.n, cls: e.cls, t: e.t.toLowerCase() }))} /> : <span className="stacked ghost" aria-hidden="true"><span /><span /><span /></span>}
          <span className="tiny muted" data-testid="kpi-etapas">{etapas.total ? etapas.partes.filter((e) => e.n).map((e) => `${e.n} ${e.t.toLowerCase()}`).join(" · ") : "marque uma estrela na lista para começar"}</span>
        </button>
      </section>

      <div className="dash-row a">
        <Melhores O={O} />
        <OndeEstao O={O} uf={uf} />
      </div>

      <div className="dash-row b">
        <Prazos O={O} />
        <figure className="card m0 chart">
          <figcaption className="card-h"><div><h2>Quanto o órgão paga, por nível</h2><div className="sub">R$/kg de referência do item principal (torrado e moído)</div></div></figcaption>
          <div className="card-b"><Faixas faixas={faixasPorNivel(O)} pisos={pisos} onNivel={(n) => irLista({ niveis: [n] })} /></div>
        </figure>
        <Simulador O={O} />
      </div>

      <section className="insights stag" aria-label="O que os dados dizem">
        {insights(O, k, uf).map((x) => (
          <article key={x.tag} className="card fade pad insight">
            <span className="lbl accent">{x.tag}</span>
            <h3>{x.titulo}</h3>
            <p className="small ink2">{x.texto}</p>
            <button type="button" className="linkbtn" onClick={() => {
              if (x.filtro === "longe") irLista({ distMin: 1000 }, "lucro");
              else if (x.filtro === "perto") irLista({ dist: 300 }, "lucro");
              else if (x.filtro === "me") irLista({ me: MEX });
              else if (x.filtro === "guia") navegar("guia");
              else irLista({ urg: true });
            }}>{x.acao} <IArrow size={12} /></button>
          </article>
        ))}
      </section>

      <div className="dash-row c">
        <figure className="card m0 chart">
          <figcaption className="card-h"><div><h2>De {n0(data.coleta?.listadas || O.length)} compras a {k.boas} boas</h2><div className="sub">O que a última coleta filtrou · largura em escala de raiz quadrada, para as pequenas aparecerem</div></div></figcaption>
          <div className="card-b funil stag">
            {(() => { const F = funil(data, O, k); const mx = Math.sqrt(Math.max(1, F[0].n)); return F.map((f, i) => (
              <div key={f.l} className="funil-row"><span className={"funil-bar wide f" + i} style={{ width: Math.max(2, (Math.sqrt(f.n) / mx) * 100) + "%" }} /><span className="small ink2"><b className="mono">{n0(f.n)}</b> {f.l}</span></div>
            )); })()}
            <p className="tiny muted" style={{ marginTop: 6 }}>Cestas básicas, solúvel, cápsula e compras encerradas ficam de fora por regra sua.{data.coleta?.chamadas_pncp ? ` ${n0(data.coleta.chamadas_pncp)} consultas ao PNCP, ${data.coleta.falhas ?? 0} falhas, ${Math.round((data.coleta.segundos || 0) / 60)} min.` : ""}</p>
          </div>
        </figure>
        <div className="trio">
          <section className="card pad" aria-label="Exigências mais comuns">
            <h2>Exigências</h2><div className="sub small muted">em quantas compras aparece · preço típico de quem pede</div>
            <Hbar rows={exigencias(O).slice(0, 7).map((e) => ({ l: e.l, v: e.n, extra: e.med ? BRL(e.med).replace(",00", "") + "/kg" : undefined }))} />
          </section>
          <section className="card pad" aria-label="Embalagem e tipo de compra">
            <h2>Embalagem</h2>
            <div className="donuts">{embalagem(O).map((e) => <Donut key={e.l} frac={e.n / Math.max(1, O.length)} rotulo={Math.round((e.n / Math.max(1, O.length)) * 100) + "%"} sub={e.l} />)}</div>
            <h2 style={{ marginTop: 12 }}>Tipo de compra</h2>
            <TipoCompra O={O} />
          </section>
          <section className="card pad" aria-label="Marcas citadas">
            <h2>Marcas citadas</h2><div className="sub small muted">como referência nos editais (“ou equivalente”)</div>
            <Hbar rows={marcasCitadas(O).slice(0, 6).map((m) => ({ l: <>{m.m}{varejoTxt(data.marcas_ref, m.m) ? <span className="hb-sub">{varejoTxt(data.marcas_ref, m.m).replace(/^[^:]*: /, "")} no varejo</span> : null}</>, v: m.n, onClick: () => irLista({ marcas: [m.m] }) }))} />
            {data.marcas_ref?.pesquisa_em && <p className="tiny muted" style={{ marginTop: 8 }}>Preço de varejo: 11 lojas online, pesquisa semanal (segunda, 7:13). Última: {data.marcas_ref.pesquisa_em.split("-").reverse().join("/")}.</p>}
          </section>
        </div>
      </div>
    </div>
  );
}

/* Quantas licitações acompanhadas há em cada etapa (as que saíram dos dados continuam contando, como no quadro). */
const COR_ETAPA: Record<string, string> = { "": "sem", "A analisar": "muted", "Em preparação": "ap", Enviada: "acc", Ganha: "bom", Perdida: "preju", Desistiu: "preju" };
export function etapasMinhas(wf: Record<string, { fav?: boolean; status?: string }>, opcoes: string[]): { total: number; partes: { t: string; n: number; cls: string }[] } {
  const L = Object.values(wf).filter((w) => follows(w));
  const partes = ["", ...opcoes].map((e) => ({ t: e || "Sem status", n: L.filter((w) => (w.status || "") === e).length, cls: COR_ETAPA[e] || "acc" }));
  return { total: L.length, partes };
}

/* ---------------- melhores para você */
type ChipMelhor = "todas" | "perto" | "semana" | "m30";
type OrdMelhor = "lucro" | "margem" | "prazo";
function Melhores({ O }: { O: PCompra[] }) {
  const [chip, setChip] = useState<ChipMelhor>("todas");
  const [ord, setOrd] = useState<OrdMelhor>("lucro");
  const now = useStore((s) => s.now);
  const base = O.filter((c) => c._mg && c._mg.lucro > 0 && (c.kg || 0) >= 200);
  const rows = base.filter((c) => chip === "perto" ? (c.dist ?? 1e9) <= 600 : chip === "semana" ? (urg(c.fim, c._ms, now).d ?? 99) <= 7 : chip === "m30" ? c._mg!.mp >= 0.3 : true)
    .sort((a, b) => ord === "lucro" ? b._mg!.lucro - a._mg!.lucro : ord === "margem" ? b._mg!.mp - a._mg!.mp : (a._ms ?? 1e15) - (b._ms ?? 1e15)).slice(0, 6);
  const chips: [ChipMelhor, string][] = [["todas", "Todas"], ["perto", "Até 600 km"], ["semana", "Fecha esta semana"], ["m30", "Margem de 30% ou mais"]];
  return (
    <section className="card melhores" aria-label="Melhores oportunidades">
      <div className="card-h">
        <div><h2>Melhores para você</h2><div className="sub">Lucro estimado com os seus custos · só compras de 200 kg ou mais</div></div>
        <Segmentado rotulo="Ordenar por" valor={ord} onChange={setOrd} opcoes={[["lucro", "Lucro"], ["margem", "Margem"], ["prazo", "Prazo"]]} />
      </div>
      <div className="chips-row">
        {chips.map(([k, t]) => <button key={k} type="button" className="chip" aria-pressed={chip === k} onClick={() => setChip(k)}>{t}</button>)}
        <span className="grow" /><span className="small muted">{rows.length} de {base.length} com lucro</span>
      </div>
      <div className="scroll-x">
        <div className="mlist">
          <div className="mhead lbl"><span>Licitação</span><span className="r m-kg">kg</span><span className="r m-rkg">R$/kg</span><span className="r m-mg">Margem</span><span className="r m-lucro">Lucro</span><span className="r m-prazo">Prazo</span></div>
          {rows.map((c) => {
            const u = urg(c.fim, c._ms, now);
            return (
              <button key={c.chave} type="button" className="mrow" onClick={() => abrirDetalhe(c.chave)} data-ch={c.chave}>
                <span className="mloc"><b>{c.mun} <span className="muted">{c.uf}</span></b><span className="small muted ell">{c._orgao} · {c._niv ? NIVEL_CURTO[c._niv] : c.tipos[0]}{c.dist != null ? ` · ${n0(c.dist)} km` : ""}{c.marcas?.length ? ` · ${c.marcas[0]} como referência` : ""}</span></span>
                <span className="r mono m-kg">{n0(c.kg!)}</span>
                <span className="r mono ink2 m-rkg">{n2(c._mg!.preco)}</span>
                <span className={"r mg m-mg " + mgCls(c._mg!.mp)}>{PCTi(c._mg!.mp)}</span>
                <span className="r mono m-lucro" style={{ fontWeight: 600 }}>{BRLc(c._mg!.lucro).replace("R$ ", "")}<small className={"m-mg-cel mg " + mgCls(c._mg!.mp)}>{PCTi(c._mg!.mp)}</small></span>
                <span className={"r mono small m-prazo" + (u.d != null && u.d <= 3 ? " serious" : " ink2")}>{fmtPrazo(c.fim)}</span>
              </button>
            );
          })}
          {!rows.length && <div className="empty"><b>Nenhuma com esse filtro.</b></div>}
        </div>
      </div>
      <div className="card-f"><span className="small muted">Margem é estimativa com os seus custos; o edital manda.</span><button type="button" className="linkbtn" onClick={() => { setF(DEF()); setSort("lucro"); navegar("oportunidades"); }}>Ver as {O.length} <IArrow size={12} /></button></div>
    </section>
  );
}

/* ---------------- onde estão */
function OndeEstao({ O, uf }: { O: PCompra[]; uf: ReturnType<typeof porUF> }) {
  const [sel, setSel] = useState<string | null>(null);
  const origem = useStore((s) => s.data?.origem);
  const top = Object.entries(uf).sort((a, b) => b[1].n - a[1].n).slice(0, 6);
  const pontos: Ponto[] = O.filter((c) => c._mg && c._mg.lucro > 0 && (c as PCompra & { lat?: number; lon?: number }).lat != null)
    .sort((a, b) => b._mg!.lucro - a._mg!.lucro).slice(0, 6)
    .map((c) => { const x = c as PCompra & { lat: number; lon: number }; return { chave: c.chave, lat: x.lat, lon: x.lon, peso: c._mg!.lucro, rotulo: `${c.mun}, ${c.uf}: lucro estimado ${BRLc(c._mg!.lucro)}` }; });
  const x = sel ? uf[sel] : null;
  return (
    <section className="card onde" aria-label="Onde estão">
      <div className="card-h">
        <div><h2>Onde estão</h2><div className="sub">{sel && x ? `${sel}: ${licit(x.n)} · lucro potencial ${BRLc(x.lucro)} · ${KGc(x.kg)}` : `${licit(O.length)} em ${Object.keys(uf).length} estados · toque num estado`}</div></div>
        <button type="button" className="linkbtn" onClick={() => { setF({ ...DEF(), ufs: sel ? [sel] : [] }); navegar("oportunidades"); }}>{sel ? `Ver ${sel}` : "Ver no mapa"} <IArrow size={12} /></button>
      </div>
      <div className="card-b">
        <Mapa porUF={uf} sel={sel} onSel={(u) => setSel(sel === u ? null : u)} origem={origem} pontos={pontos} onPonto={abrirDetalhe} />
        <div className="map-legend tiny muted"><span>1</span><span className="grad" /><span>{Math.max(...Object.values(uf).map((v) => v.n), 1)} abertas</span>{pontos.length > 0 && <span className="lg"><i className="pt" />as melhores</span>}<span className="lg"><i className="or" />{origem?.nome || "origem"}</span></div>
        <div className="chips-row" style={{ padding: "8px 0 0" }}>
          {top.map(([u, v]) => <button key={u} type="button" className="chip mono" aria-pressed={sel === u} onClick={() => setSel(sel === u ? null : u)}>{u} {v.n}</button>)}
        </div>
        <p className="tiny muted" style={{ marginTop: 8 }}>Anéis: 300, 600 e 1.000 km em linha reta a partir de {origem?.nome || "Uberaba"}. A distância das licitações é por estrada.</p>
      </div>
    </section>
  );
}

/* ---------------- prazos */
function Prazos({ O }: { O: PCompra[] }) {
  const [vista, setVista] = useState<"dia" | "semana">("dia");
  const dados = vista === "dia" ? prazosPorDia(O, 12) : prazosPorSemana(O, 5);
  const pico = dados.reduce((a, b) => (b.total > a.total ? b : a), dados[0]);
  return (
    <figure className="card m0 chart">
      <figcaption className="card-h">
        <div><h2>Prazos</h2><div className="sub">{vista === "dia" ? `Quantas fecham por dia · pico ${pico && pico.total ? fmtPrazo(pico.dia) : "—"}` : `Quantas fecham por semana · ${dados[0]?.total ?? 0} já na próxima`}</div></div>
        <Segmentado rotulo="Agrupar por" valor={vista} onChange={setVista} opcoes={[["dia", "Dia"], ["semana", "Semana"]]} pequeno />
      </figcaption>
      <div className="card-b"><Barras dados={dados} onClick={() => { setF(DEF()); setSort("prazo"); navegar("oportunidades"); }} /></div>
    </figure>
  );
}

/* ---------------- a quanto você venderia? */
function Simulador({ O }: { O: PCompra[] }) {
  const prep = useStore((s) => s.prep)!;
  const S = useMemo(() => simulador(O, prep), [O, prep]);
  const disponiveis = S.filter((s) => s.precos.length >= 3 && s.fixo != null);
  const [niv, setNiv] = useState(disponiveis[0]?.nivel || "Tradicional");
  const [p, setP] = useState(60);
  const s = S.find((x) => x.nivel === niv) || S[0];
  if (!disponiveis.length) return <section className="card pad"><h2>A quanto você venderia?</h2><p className="small muted">Sem licitações com preço e custo para simular.</p></section>;
  const custo = (s.fixo || 0) + p * s.pct, mp = (p - custo) / p, n = s.precos.filter((x) => x >= p).length;
  return (
    <section className="card pad sim" aria-label="Simulador de preço">
      <h2>A quanto você venderia?</h2><div className="sub small muted">Teste um preço e veja quantas pagam isso ou mais</div>
      <div className="chips-row" style={{ padding: "10px 0 6px" }}>
        {disponiveis.map((x) => <button key={x.nivel} type="button" className="chip" aria-pressed={niv === x.nivel} onClick={() => setNiv(x.nivel)}>{NIVEL_CURTO[x.nivel]}</button>)}
      </div>
      <div className="sim-ctl">
        <button type="button" className="btn icon" aria-label="Menos R$ 1" onClick={() => setP((v) => Math.max(30, v - 1))}><IMinus /></button>
        <div className="sim-v"><span className="mono big">R$ {n2(p)}</span><span className="tiny muted">por kg, entregue</span></div>
        <button type="button" className="btn icon" aria-label="Mais R$ 1" onClick={() => setP((v) => Math.min(150, v + 1))}><IPlus /></button>
      </div>
      <label className="sr" htmlFor="sim-range">Preço por kg</label>
      <input id="sim-range" type="range" min={30} max={150} step={0.5} value={p} onChange={(e) => setP(+e.target.value)} className="range" style={{ accentColor: mp >= 0.15 ? "var(--good)" : mp >= 0 ? "var(--warn)" : "var(--crit)" }} />
      <div className="sim-out">
        <div><span className="lbl">Sua margem</span><span className={"mg big " + mgCls(mp)}>{PCTi(mp)}</span><span className="tiny muted">custo típico {BRL(custo)}/kg</span></div>
        <div><span className="lbl">Pagam isso ou mais</span><span className="mono big">{n} <span className="v-sub">de {s.precos.length}</span></span><span className="tiny muted">licitações {NIVEL_CURTO[s.nivel].toLowerCase()} com preço</span></div>
      </div>
      <p className="tiny muted" style={{ marginTop: 8 }}><Termo t="Preço para empatar">Empate</Termo> em {s.empate != null ? BRL(s.empate) : "—"}/kg. A {BRL(p).replace(",00", "")} você disputa {Math.round((n / Math.max(1, s.precos.length)) * 100)}% das licitações {NIVEL_CURTO[s.nivel].toLowerCase()} abertas.</p>
    </section>
  );
}

function TipoCompra({ O }: { O: PCompra[] }) {
  const conta = (f: (c: PCompra) => boolean) => O.filter(f).length;
  const preg = conta((c) => c.mod.startsWith("Pregão")), disp = conta((c) => c.mod.startsWith("Dispensa")), srp = conta((c) => c.srp === "Sim");
  const esf = ["Municipal", "Estadual", "Federal"].map((e) => conta((c) => c.esfera === e));
  const Linha = ({ t, v }: { t: React.ReactNode; v: React.ReactNode }) => <div className="tc-row"><span className="ink2">{t}</span><span className="mono">{v}</span></div>;
  return (
    <div className="tc">
      <Linha t={<Termo t="Pregão Eletrônico">Pregão eletrônico</Termo>} v={preg} />
      <Linha t={<Termo t="Dispensa">Dispensa (compra direta)</Termo>} v={disp} />
      <Linha t={<Termo t="Registro de preços" />} v={<>{srp} <span className="muted">{Math.round((srp / Math.max(1, O.length)) * 100)}%</span></>} />
      <Linha t="Prefeituras · estados · federal" v={esf.join(" · ")} />
    </div>
  );
}

/* usado por outras telas */
export function LinhaMini({ c }: { c: PCompra }) {
  return (
    <button type="button" className="mini" onClick={() => abrirDetalhe(c.chave)} data-ch={c.chave}>
      <span><UFBadge c={c} /> <b>{c.mun}</b> <span className="small muted">· {c._orgao}</span></span>
      <span className="row-flex small"><Nivel n={c._niv} /><MeBadge c={c} /><Margem c={c} curto /><Prazo c={c} /></span>
    </button>
  );
}

export const DicaMargem = Dica;
export const NIVEIS_SIM = NIVEIS;
