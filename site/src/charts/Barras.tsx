/* Barras empilhadas por dia ou semana: quantas licitações fecham e quantas valem a pena (bencho "Stacked bars"). */
import type { BarraPrazo } from "../lib/dash";
import { fmtDia, licit } from "../lib/format";
import { Dica } from "../ui/Tooltip";

const ALT = 112;
export function Barras({ dados, onClick }: { dados: BarraPrazo[]; onClick?: (b: BarraPrazo) => void }) {
  const max = Math.max(1, ...dados.map((b) => b.total));
  const esc = ALT / max;
  return (
    <div className="bars-wrap">
      <div className="bars stag">
        {dados.map((b) => (
          <Dica key={b.dia} texto={<><b>{fmtDia(b.dia)}</b>: {licit(b.total)}{b.total ? <><br />{b.bom} com margem boa · {b.apertado} apertada · {b.preju} prejuízo · {b.sem} sem preço</> : null}</>}>
            <button type="button" className={"bar-col" + (b.fds ? " fds" : "")} onClick={() => onClick?.(b)} aria-label={`${fmtDia(b.dia)}: ${licit(b.total)}`}>
              <span className="bar-top mono">{b.total || ""}</span>
              <span className="bar-stack rise">
                {b.sem > 0 && <span className="seg-sem" style={{ height: Math.max(2, b.sem * esc) }} />}
                {b.preju > 0 && <span className="seg-preju" style={{ height: Math.max(2, b.preju * esc) }} />}
                {b.apertado > 0 && <span className="seg-ap" style={{ height: Math.max(2, b.apertado * esc) }} />}
                {b.bom > 0 && <span className="seg-bom" style={{ height: Math.max(2, b.bom * esc) }} />}
              </span>
            </button>
          </Dica>
        ))}
      </div>
      <div className="bar-lbls mono">{dados.map((b) => <span key={b.dia} className={b.fds ? "fds" : ""}>{b.lbl}</span>)}</div>
      <div className="legend">
        <span><i className="bom" />Margem boa</span><span><i className="ap" />Apertada</span><span><i className="preju" />Prejuízo</span><span><i className="sem" />Sem preço</span>
      </div>
    </div>
  );
}
