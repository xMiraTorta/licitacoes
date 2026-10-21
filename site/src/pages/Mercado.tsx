/* Mercado: café verde por nível (CEPEA + Carvalhaes), histórico, varejo das marcas e réguas. */
import { useMemo } from "react";
import { Faixas } from "../charts/Faixas";
import { abertas, faixasPorNivel } from "../lib/dash";
import { BRL, BRL0, fmtDia, n0, n2 } from "../lib/format";
import { MERCADO_VAREJO, NIVEIS, NIVEL_CURTO } from "../lib/modelo";
import { navegar } from "../router";
import { setF, useStore } from "../store";
import { DEF } from "../lib/filtros";
import { IArrow } from "../ui/icons";
import { Nivel } from "../ui/Pecas";
import { Dica, Termo } from "../ui/Tooltip";
import type { HistoricoMercado } from "../types";

const CLASSES: Record<string, string> = { cd_finos: "CD finos", finos: "Finos a extra-finos", boa_qualidade: "Boa qualidade", duro_fraco: "Duros com x", riados: "Riados", rio: "Rio", consumo_dura: "Consumo interno: dura", consumo_riada: "Consumo interno: riada" };

export function Mercado() {
  const data = useStore((s) => s.data)!;
  const prep = useStore((s) => s.prep)!;
  const pisos = useStore((s) => s.pisos);
  const custos = useStore((s) => s.custos);
  const now = useStore((s) => s.now);
  const m = data.mercado || {};
  const perda = m.perda_torra ?? 0.18;
  const O = useMemo(() => abertas(prep, now), [prep, now]);
  const faixas = useMemo(() => faixasPorNivel(O), [O]);
  const cot = m.carvalhaes?.data || m.atualizado_em;
  const hist = (m.historico || []).slice(-60);
  // "Sem categoria" tem o mesmo café verde do Tradicional: um cartão só, a não ser que o dono fixe preços diferentes em Ajustes
  const sc = m.niveis?.["Sem categoria"], tr = m.niveis?.Tradicional;
  const juntos = !!sc && !!tr && sc.saca60_min === tr.saca60_min && sc.saca60_max === tr.saca60_max && (custos["grao|Sem categoria"] ?? null) === (custos["grao|Tradicional"] ?? null);
  return (
    <div className="page mercado">
      <div className="page-h"><h1>Mercado</h1><span className="small muted">Café verde por nível de exigência, preços de varejo das marcas e o que os órgãos pagam.</span></div>

      <section className="niv-cards stag" aria-label="Café verde por nível">
        {NIVEIS.filter((n) => m.niveis?.[n] && !(juntos && n === "Sem categoria")).map((n) => {
          const x = m.niveis![n];
          const meu = custos["grao|" + n];
          const torrado = (meu ? meu / 60 : x.kg_medio) / (1 - perda);
          return (
            <article key={n} className="card pad fade" data-nivel={n}>
              <div className="row-flex" style={{ justifyContent: "space-between" }}><Nivel n={n} /><span className="tiny muted">cotação {cot ? fmtDia(cot) : ""}</span></div>
              <div className="big-n mono">{BRL0(meu || x.saca60_min)}{!meu && <span className="v-sub"> a {BRL0(x.saca60_max)}</span>}</div>
              <div className="small muted">{meu ? "seu preço por saca (Ajustes)" : "R$ por saca de 60 kg, faixa estimada"}</div>
              <hr className="hr" style={{ margin: "10px 0" }} />
              <div className="small">≈ <b>{BRL(torrado)}</b>/kg torrado, só a matéria-prima ({Math.round(perda * 100)}% de perda na torra)</div>
              <p className="tiny muted" style={{ marginTop: 8 }}>{x.regra}</p>
              {juntos && n === "Tradicional" && <p className="tiny muted" style={{ marginTop: 6 }}>Vale também para edital sem categoria (nível “Sem categoria”): o mínimo legal é o mesmo blend, ao mesmo preço.</p>}
            </article>
          );
        })}
      </section>

      <div className="dash-row d">
        <section className="card pad" aria-label="Indicadores">
          <h2>Indicadores de hoje</h2>
          <div className="sub small muted">R$ por saca de 60 kg · fontes públicas lidas 2x por dia útil (7:13 e 18:47)</div>
          <table className="tbl" style={{ marginTop: 10 }}><tbody>
            {m.cepea?.arabica && <tr><td><Dica texto="CEPEA/ESALQ: arábica tipo 6 bebida dura para melhor, posto São Paulo (CC BY-NC 4.0)"><span className="tt-term">CEPEA arábica</span></Dica></td><td className="mono r">{n2(m.cepea.arabica.saca60)}</td><td className="muted small">{fmtDia(m.cepea.arabica.data)}</td></tr>}
            {m.cepea?.robusta && <tr><td><Dica texto="CEPEA/ESALQ: robusta (conilon), entra na receita do Tradicional e do Superior"><span className="tt-term">CEPEA robusta</span></Dica></td><td className="mono r">{n2(m.cepea.robusta.saca60)}</td><td className="muted small">{fmtDia(m.cepea.robusta.data)}</td></tr>}
            {m.carvalhaes && <tr className="tbl-g"><td colSpan={3}>Carvalhaes <span className="muted small">· corretora de café, por qualidade da bebida</span></td></tr>}
            {m.carvalhaes && Object.entries(m.carvalhaes.saca60).map(([k, [a, b]]) => <tr key={k}><td>{CLASSES[k] || k}</td><td className="mono r">{n2(a)} a {n2(b)}</td><td className="muted small">{fmtDia(m.carvalhaes!.data)}</td></tr>)}
          </tbody></table>
          <p className="tiny muted" style={{ marginTop: 8 }}>Não existe cotação pública de “café para Superior”: o preço de cada nível é estimado pela receita de blend das Resoluções SAA-SP 28, 30 e 31/2007 (PQC/ABIC), com o meio da faixa no custo. Café da sua fazenda entra pelo preço que você receberia vendendo; fixe o seu R$/saca em <button type="button" className="linkbtn" onClick={() => navegar("ajustes")}>Ajustes</button>.</p>
        </section>

        <figure className="card m0 chart">
          <figcaption className="card-h"><div><h2>Café verde nos últimos dias</h2><div className="sub">{hist.length > 1 ? `R$/saca médio por nível · ${hist.length} cotações` : "O histórico começa a ser guardado a partir de agora, a cada atualização de preço"}</div></div></figcaption>
          <div className="card-b">{hist.length > 1 ? <Historico hist={hist} /> : <div className="empty"><span className="small">Em alguns dias aparece aqui a linha do preço do café verde por nível.</span></div>}</div>
        </figure>
      </div>

      <figure className="card m0 chart">
        <figcaption className="card-h"><div><h2>Quanto o órgão paga, por nível</h2><div className="sub">R$/kg de referência nas licitações abertas (item principal, torrado e moído) · <Termo t="Preço típico">preço típico</Termo> e seu custo marcados</div></div><button type="button" className="linkbtn" onClick={() => { setF(DEF()); navegar("oportunidades"); }}>Ver a lista <IArrow size={12} /></button></figcaption>
        <div className="card-b"><Faixas faixas={faixas} pisos={pisos} onNivel={(n) => { setF({ ...DEF(), niveis: [n] }); navegar("oportunidades"); }} /></div>
      </figure>

      <section className="card pad" aria-label="Varejo das marcas">
        <div className="card-h" style={{ padding: 0 }}><div><h2>Marcas de referência no varejo</h2><div className="sub small muted">Preço por kg em supermercados online (11 lojas, pesquisa semanal de segunda) e categoria oficial da ABIC{data.marcas_ref?.pesquisa_em ? ` · última pesquisa ${fmtDia(data.marcas_ref.pesquisa_em)}` : ""}. Réguas ABIC {MERCADO_VAREJO.data}: {NIVEIS.filter((n) => MERCADO_VAREJO.valores[n]).map((n) => `${NIVEL_CURTO[n]} ${BRL(MERCADO_VAREJO.valores[n])}`).join(" · ")}.</div></div></div>
        <div className="scroll-x" style={{ marginTop: 10 }}>
          <table className="tbl marcas-t">
            <thead><tr><th>Marca</th><th>Linha básica</th><th>Categoria ABIC</th><th className="r">R$/kg no varejo</th><th className="r">Citada em</th></tr></thead>
            <tbody>
              {Object.entries(data.marcas_ref?.marcas || {}).filter(([, v]) => v.basica).sort((a, b) => a[0].localeCompare(b[0])).map(([mk, v]) => {
                const b = v.basica!, n = O.filter((c) => (c.marcas || []).includes(mk)).length;
                return <tr key={mk}><td><b>{mk}</b></td><td>{b.linha}</td><td>{b.cat}</td><td className="mono r">{n0(b.min) === n0(b.max) ? n0(b.min) : `${n0(b.min)} a ${n0(b.max)}`}</td><td className="r">{n ? <button type="button" className="linkbtn" onClick={() => { setF({ ...DEF(), marcas: [mk] }); navegar("oportunidades"); }}>{n} edita{n === 1 ? "l" : "is"}</button> : <span className="muted">—</span>}</td></tr>;
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function Historico({ hist }: { hist: HistoricoMercado[] }) {
  const niveis = NIVEIS.filter((n) => n !== "Sem categoria" && hist.some((h) => h.niveis[n]));
  const vals = hist.flatMap((h) => niveis.map((n) => h.niveis[n]).filter((v): v is number => !!v));
  const lo = Math.min(...vals) * 0.97, hi = Math.max(...vals) * 1.03;
  const W = 640, H = 200, pl = 48, pr = 30, pb = 24, pt = 10; // pr: o último rótulo do eixo ("20/10") precisa de espaço à direita
  const x = (i: number) => pl + (i / Math.max(1, hist.length - 1)) * (W - pl - pr);
  const y = (v: number) => pt + (1 - (v - lo) / (hi - lo)) * (H - pt - pb);
  const cores: Record<string, string> = { Tradicional: "var(--seq-3)", Superior: "var(--accent)", "Gourmet/especial": "var(--violet)" };
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="linechart" role="img" aria-label="Preço do café verde por nível ao longo dos dias">
        {[0, 0.5, 1].map((f) => { const v = lo + (hi - lo) * f; return <g key={f}><line className="grid" x1={pl} x2={W - pr} y1={y(v)} y2={y(v)} /><text className="axl" x={pl - 6} y={y(v) + 4} textAnchor="end">{n0(v)}</text></g>; })}
        {niveis.map((n) => <polyline key={n} fill="none" stroke={cores[n]} strokeWidth="2" strokeLinejoin="round" points={hist.map((h, i) => (h.niveis[n] ? `${x(i)},${y(h.niveis[n])}` : "")).filter(Boolean).join(" ")} />)}
        {hist.map((h, i) => (i === 0 || i === hist.length - 1 || i % Math.ceil(hist.length / 6) === 0) && <text key={h.data} className="axl" x={x(i)} y={H - 6} textAnchor="middle">{fmtDia(h.data).slice(0, 5)}</text>)}
      </svg>
      <div className="legend">{niveis.map((n) => <span key={n}><i style={{ background: cores[n] }} />{NIVEL_CURTO[n]}</span>)}</div>
    </div>
  );
}
