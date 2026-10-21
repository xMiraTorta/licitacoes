/* Anel de proporção (uma parte do todo), desenhado ao entrar. */
const R = 22, C = 2 * Math.PI * R;
export function Donut({ frac, rotulo, sub, cor = "var(--accent)", onClick }: { frac: number; rotulo: string; sub: string; cor?: string; onClick?: () => void }) {
  const f = Math.max(0, Math.min(1, frac));
  const Tag = onClick ? "button" : "div";
  return (
    <Tag className="donut-item" {...(onClick ? { type: "button" as const, onClick, title: "Ver estas licitações" } : {})}>
      <svg width="52" height="52" viewBox="0 0 52 52" aria-hidden="true">
        <circle cx="26" cy="26" r={R} fill="none" stroke="var(--surface-2)" strokeWidth="6" />
        <circle className="donut" cx="26" cy="26" r={R} fill="none" stroke={cor} strokeWidth="6" strokeLinecap="round" strokeDasharray={`${f * C} ${C}`} transform="rotate(-90 26 26)" />
      </svg>
      <span className="donut-t"><b className="mono">{rotulo}</b><span className="tiny muted">{sub}</span></span>
    </Tag>
  );
}
