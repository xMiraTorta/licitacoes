/* Quanto o órgão paga por nível: distribuição do R$/kg (faixas de R$ 10), com o preço típico, o seu custo típico,
   o seu piso e o varejo marcados. Substitui o gráfico "preço × exigência" do site anterior. */
import { BIN_HI, BIN_LO, BIN_W, type FaixaNivel } from "../lib/dash";
import { BRL, licit } from "../lib/format";
import { MERCADO_VAREJO, NIVEL_CURTO } from "../lib/modelo";
import { Nivel } from "../ui/Pecas";
import { Dica } from "../ui/Tooltip";

const pos = (v: number): number => Math.max(0, Math.min(100, ((v - BIN_LO) / (BIN_HI - BIN_LO)) * 100));

export function Faixas({ faixas, pisos, onNivel }: { faixas: FaixaNivel[]; pisos: Record<string, number>; onNivel?: (n: string) => void }) {
  return (
    <div className="faixas">
      {faixas.map((f) => {
        const max = Math.max(1, ...f.bins);
        const vj = MERCADO_VAREJO.valores[f.nivel];
        return (
          <div key={f.nivel} className="faixa-row">
            <button type="button" className="faixa-n" onClick={() => onNivel?.(f.nivel)} title="Ver estas licitações">
              <Nivel n={f.nivel} semTexto /><span>{NIVEL_CURTO[f.nivel]}</span><i className="mono muted">{f.n}</i>
            </button>
            <div className="faixa-c">
              <div className="faixa-bins stag">
                {f.bins.map((b, i) => (
                  <Dica key={i} texto={`R$ ${BIN_LO + i * BIN_W} a ${BIN_LO + (i + 1) * BIN_W}${i === f.bins.length - 1 ? "+" : ""}: ${licit(b)}`}>
                    <span className={"bin" + (b ? " rise" : "")} style={{ height: b ? Math.max(3, (b / max) * 34) : 1 }} />
                  </Dica>
                ))}
              </div>
              {f.med != null && <Dica texto={`Preço típico ${f.nivel}: ${BRL(f.med)}/kg (faixa comum ${BRL(f.p25)} a ${BRL(f.p75)})`}><span className="mk tipico" style={{ left: pos(f.med) + "%" }} /></Dica>}
              {f.custo != null && <Dica texto={`Seu custo típico neste nível: ${BRL(f.custo)}/kg (mediana das licitações com estimativa)`}><span className="mk custo" style={{ left: pos(f.custo) + "%" }} /></Dica>}
              {pisos[f.nivel] > 0 && <Dica texto={`Seu piso ${f.nivel}: ${BRL(pisos[f.nivel])}/kg`}><span className="mk piso" style={{ left: pos(pisos[f.nivel]) + "%" }} /></Dica>}
              {vj && <Dica texto={`Varejo ${f.nivel} em supermercados (ABIC, ${MERCADO_VAREJO.data}): ${BRL(vj)}/kg`}><span className="mk varejo" style={{ left: pos(vj) + "%" }} /></Dica>}
            </div>
            <span className="faixa-v mono">{f.med != null ? "R$ " + Math.round(f.med) : "—"}</span>
          </div>
        );
      })}
      <span /><div className="faixa-axis mono muted"><span>R$ {BIN_LO}</span><span>{BIN_LO + 25}</span><span>{BIN_LO + 50}</span><span>{BIN_LO + 75}</span><span>{BIN_HI}+</span></div><span />
      <div className="legend">
        <span><i className="l-tipico" />preço típico</span><span><i className="l-custo" />seu custo típico</span><span><i className="l-varejo" />varejo (ABIC)</span>{Object.values(pisos).some((v) => v > 0) && <span><i className="l-piso" />seu piso</span>}
      </div>
    </div>
  );
}
