/* Faixa do café verde: R$/saca por nível (receita de blend sobre CEPEA e Carvalhaes), atualizada 2x por dia útil. */
import { fmtDia, n0 } from "../lib/format";
import { NIVEL_CURTO, NIVEIS } from "../lib/modelo";
import { navegar } from "../router";
import { useStore } from "../store";
import { Dica } from "./Tooltip";

export function Ticker() {
  const m = useStore((s) => s.data?.mercado);
  if (!m || !m.niveis) return null;
  const data = m.carvalhaes?.data || m.atualizado_em;
  return (
    <div className="ticker-wrap"><div className="ticker mono" aria-label="Café verde hoje, R$ por saca de 60 kg">
      <span className="muted">CAFÉ VERDE {data ? fmtDia(data).slice(0, 5) : ""} · R$/SACA</span>
      {NIVEIS.filter((n) => n !== "Sem categoria").map((n) => {
        const x = m.niveis![n];
        if (!x) return null;
        return (
          <Dica key={n} texto={`${n}: ${x.regra || ""} Faixa estimada pela receita de blend; o meio da faixa entra no custo.`}>
            <span className="tk">{NIVEL_CURTO[n].toUpperCase()} <b>{n0(x.saca60_min)} a {n0(x.saca60_max)}</b></span>
          </Dica>
        );
      })}
      {m.cepea?.arabica && <span className="tk">CEPEA ARÁBICA <b>{n0(m.cepea.arabica.saca60)}</b></span>}
      {m.cepea?.robusta && <span className="tk">ROBUSTA <b>{n0(m.cepea.robusta.saca60)}</b></span>}
      <span className="muted tk-upd">ATUALIZA 7:13 E 18:47</span>
      <button type="button" className="linkbtn tk-link" onClick={() => navegar("mercado")}>Mercado →</button>
    </div></div>
  );
}
