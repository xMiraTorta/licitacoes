/* Lista com barras horizontais (uma cor), rótulo, valor e texto auxiliar. */
import type { ReactNode } from "react";

export interface HbarRow { l: ReactNode; v: number; extra?: ReactNode; onClick?: () => void; chave?: string }
export function Hbar({ rows, max }: { rows: HbarRow[]; max?: number }) {
  const mx = Math.max(1, max ?? Math.max(...rows.map((r) => r.v)));
  return (
    <div className="hb stag">
      {rows.map((r, i) => {
        const inner = (
          <>
            <span className="hb-l"><span className="hb-t">{r.l}</span><span className="hb-tr"><span className="hb-br wide" style={{ width: (r.v / mx) * 100 + "%" }} /></span></span>
            <span className="hb-v mono">{r.v}{r.extra ? <span className="hb-x">{r.extra}</span> : null}</span>
          </>
        );
        return r.onClick
          ? <button key={r.chave ?? i} type="button" className="hb-row" onClick={r.onClick}>{inner}</button>
          : <div key={r.chave ?? i} className="hb-row">{inner}</div>;
      })}
    </div>
  );
}

export function Sparkline({ valores, destaque = 7 }: { valores: number[]; destaque?: number }) {
  const max = Math.max(1, ...valores);
  const n = valores.length;
  return (
    <div className="spark stag" aria-hidden="true">
      {valores.map((v, i) => <span key={i} className={(v ? "rise " : "") + (i >= n - destaque ? "on" : "")} style={{ height: v ? Math.max(2, (v / max) * 100) + "%" : 2 }} />)}
    </div>
  );
}

export function Stacked({ partes }: { partes: { v: number; cls: string; t: string }[] }) {
  const tot = Math.max(1, partes.reduce((a, p) => a + p.v, 0));
  return (
    <div className="stacked" role="img" aria-label={partes.map((p) => `${p.v} ${p.t}`).join(", ")}>
      {partes.filter((p) => p.v > 0).map((p) => <span key={p.t} className={"wide " + p.cls} style={{ width: (p.v / tot) * 100 + "%" }} title={`${p.v} ${p.t}`} />)}
    </div>
  );
}
