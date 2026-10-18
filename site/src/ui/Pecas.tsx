/* Peças pequenas repetidas em várias telas: nível, selos, preço vs típico, piso, margem, prazo. */
import { BRL, PCTi } from "../lib/format";
import { mgCls, NIVEIS, selosDe, urg, type PCompra } from "../lib/modelo";
import { useStore } from "../store";
import { Dica, Termo } from "./Tooltip";

export function Nivel({ n, semTexto }: { n: string | null; semTexto?: boolean }) {
  if (!n) return null;
  const i = NIVEIS.indexOf(n as (typeof NIVEIS)[number]);
  return (
    <Dica texto="Nível de exigência lido do texto do edital (categoria, selo, nota mínima, bebida). Confira sempre.">
      <span className="lvl"><span className="m" aria-hidden="true">{[1, 2, 3].map((k) => <b key={k} className={i >= k ? "on" : ""} />)}</span>{!semTexto && n}</span>
    </Dica>
  );
}

export function Selos({ c, max = 4 }: { c: PCompra; max?: number }) {
  const L = selosDe(c, max);
  return L.length ? <div className="sel-tags">{L.map((x) => <span key={x}>{x}</span>)}</div> : null;
}

/* ▲ 12% acima do típico · ≈ típico · ▼ 8% abaixo */
export function PrecoCmp({ c, longo }: { c: PCompra; longo?: boolean }) {
  const x = c._cmp;
  if (!x || x.dif == null) return null;
  const a = Math.abs(Math.round(x.dif * 100));
  const t = x.cls === "mid" ? (longo ? "≈ no preço típico do nível" : "≈ típico") : `${x.cls === "up" ? "▲" : "▼"} ${a}%${longo ? (x.cls === "up" ? " acima" : " abaixo") + " do preço típico do nível" : ""}`;
  return (
    <Dica texto={`Preço típico ${x.i.nivel}: ${BRL(x.ref)}/kg (o do meio: metade das licitações abertas do mesmo tipo e nível paga mais, metade paga menos).`}>
      <span className={"pc " + x.cls}>{t}</span>
    </Dica>
  );
}

export function PisoChip({ c }: { c: PCompra }) {
  const x = c._cmp;
  if (!x || x.ok == null) return null;
  return x.ok
    ? <Dica texto={`Acima do seu piso de ${BRL(x.piso)}/kg`}><span className="pv ok">✓ cobre meu piso</span></Dica>
    : <Dica texto={`Abaixo do seu piso de ${BRL(x.piso)}/kg`}><span className="pv no">✗ abaixo do meu piso</span></Dica>;
}

export function Margem({ c, curto }: { c: PCompra; curto?: boolean }) {
  if (!c._mg) return null;
  const m = c._mg;
  return (
    <Dica texto={`Margem estimada ao preço do órgão, depois de grão, torra, embalagem, frete, impostos e outros custos (Ajustes > Meus custos). ${m.m >= 0 ? "Lucro" : "Prejuízo"} de ~${BRL(Math.abs(m.lucro)).replace(",00", "")} em ${Math.round(m.kg).toLocaleString("pt-BR")} kg.`}>
      <span className={"mg " + mgCls(m.mp)}>{curto ? "" : "margem "}{PCTi(m.mp)}</span>
    </Dica>
  );
}

export function Prazo({ c, comData }: { c: PCompra; comData?: boolean }) {
  const now = useStore((s) => s.now);
  const u = urg(c.fim, c._ms, now);
  return (
    <span className={"pill " + u.cls}><span className="dot" />{u.lbl}{comData && c.fim ? " · " + c.fim.slice(8, 10) + "/" + c.fim.slice(5, 7) : ""}</span>
  );
}

export function MeBadge({ c }: { c: PCompra }) {
  if (!(c.me && (c.me.startsWith("Exclusivo") || c.me.startsWith("Cota")))) return null;
  const t = c.me.startsWith("Exclusivo ME/EPP") ? "ME/EPP" : c.me.startsWith("Cota") ? "Cota ME/EPP" : "ME/EPP parcial";
  return <Termo t="ME/EPP"><span className="badge b-me">{t}</span></Termo>;
}

export const UFBadge = ({ c }: { c: PCompra }) => <span className={"badge b-" + c._near}>{c.uf}</span>;
