/* Controles com micro-interações: menu que desliza (React Bits "Glide Select"), segurar para confirmar
   ("Hold Button"), caixa de marcar com mola ("Spring Check") e marca de estado ("Status Mark"). */
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { ICheck, IDown } from "./icons";

export function GlideSelect({ valor, opcoes, onChange, rotulo, vazio = "—", className, testid }: { valor: string; opcoes: string[]; onChange: (v: string) => void; rotulo: string; vazio?: string; className?: string; testid?: string }) {
  const [aberto, setAberto] = useState(false);
  const [ativo, setAtivo] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const id = useId();
  const lista = ["", ...opcoes];
  useEffect(() => {
    if (!aberto) return;
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setAberto(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, [aberto]);
  const abrir = () => { setAtivo(Math.max(0, lista.indexOf(valor))); setAberto(true); };
  const escolher = (v: string) => { onChange(v); setAberto(false); };
  const tecla = (e: React.KeyboardEvent) => {
    if (!aberto) { if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") { e.preventDefault(); abrir(); } return; }
    if (e.key === "ArrowDown") { e.preventDefault(); setAtivo((a) => Math.min(lista.length - 1, a + 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setAtivo((a) => Math.max(0, a - 1)); }
    else if (e.key === "Enter" || e.key === " ") { e.preventDefault(); escolher(lista[ativo]); }
    else if (e.key === "Escape") { e.stopPropagation(); setAberto(false); }
  };
  return (
    <div className={"glide" + (className ? " " + className : "")} ref={ref} onKeyDown={tecla}>
      <button type="button" className={"glide-btn st " + stCls(valor)} aria-haspopup="listbox" aria-expanded={aberto} aria-label={rotulo} onClick={() => (aberto ? setAberto(false) : abrir())} data-testid={testid} data-valor={valor}>
        <span>{valor || vazio}</span><IDown size={12} />
      </button>
      <AnimatePresence>
        {aberto && (
          <motion.ul className="glide-menu" role="listbox" aria-label={rotulo} aria-activedescendant={`${id}-${ativo}`} initial={{ opacity: 0, scale: 0.96, y: -4 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.96, y: -4 }} transition={{ duration: 0.14 }}>
            {lista.map((o, i) => (
              <li key={o || "__"} id={`${id}-${i}`} role="option" aria-selected={o === valor} className={i === ativo ? "ativo" : ""} onMouseEnter={() => setAtivo(i)} onClick={() => escolher(o)}>
                {i === ativo && <motion.span layoutId={"glide-hl-" + id} className="glide-hl" transition={{ type: "spring", stiffness: 600, damping: 40 }} />}
                <span className="glide-t">{o || vazio}{o === valor && <ICheck size={13} />}</span>
              </li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  );
}
export const stCls = (s: string): string => "s-" + String(s || "").split(" ")[0].normalize("NFD").replace(/[^\w]/g, "");

/* Segurar o botão (700 ms) para confirmar uma ação que não tem desfazer. Teclado: segurar Espaço. */
export function HoldButton({ onConfirm, children, className, dur = 700, testid }: { onConfirm: () => void; children: ReactNode; className?: string; dur?: number; testid?: string }) {
  const [seg, setSeg] = useState(false);
  const timer = useRef(0);
  const comeca = () => { setSeg(true); window.clearTimeout(timer.current); timer.current = window.setTimeout(() => { setSeg(false); onConfirm(); }, dur); };
  const solta = () => { setSeg(false); window.clearTimeout(timer.current); };
  useEffect(() => () => window.clearTimeout(timer.current), []);
  return (
    <button type="button" className={"hold " + (className || "")} onPointerDown={comeca} onPointerUp={solta} onPointerLeave={solta} onPointerCancel={solta}
      onKeyDown={(e) => { if ((e.key === " " || e.key === "Enter") && !e.repeat) { e.preventDefault(); comeca(); } }} onKeyUp={solta} data-testid={testid} title="Segure para confirmar">
      <motion.span className="hold-fill" initial={false} animate={{ width: seg ? "100%" : "0%" }} transition={{ duration: seg ? dur / 1000 : 0.15, ease: "linear" }} />
      <span className="hold-t">{children}</span>
    </button>
  );
}

export function SpringCheck({ marcado, onChange, rotulo, dica, extra, testid }: { marcado: boolean; onChange: (v: boolean) => void; rotulo: ReactNode; dica?: ReactNode; extra?: ReactNode; testid?: string }) {
  const id = useId();
  return (
    <label className={"chk" + (marcado ? " done" : "")} htmlFor={id}>
      <input id={id} type="checkbox" className="sr" checked={marcado} onChange={(e) => onChange(e.target.checked)} data-testid={testid} />
      <motion.span className="chk-box" aria-hidden="true" animate={{ scale: marcado ? [1, 1.18, 1] : 1, backgroundColor: marcado ? "var(--accent)" : "rgba(0,0,0,0)" }} transition={{ duration: 0.32 }}>
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
          <motion.path d="m5 12 4 4L19 6" initial={false} animate={{ pathLength: marcado ? 1 : 0, opacity: marcado ? 1 : 0 }} transition={{ duration: 0.25, delay: marcado ? 0.08 : 0 }} />
        </svg>
      </motion.span>
      <span className="chk-body">
        <span className="chk-t"><span className="chk-line">{rotulo}</span></span>
        {dica && <span className="chk-d small muted">{dica}</span>}
      </span>
      {extra}
    </label>
  );
}

/* Marca de estado da leitura do edital / da coleta. */
export function StatusMark({ estado }: { estado: "lido" | "manual" | "sem" | "ilegivel" | "sem-trecho" | "falha" | "pendente" | "ok" | "erro" | "andamento" }) {
  const ok = estado === "lido" || estado === "ok" || estado === "manual";
  const ruim = estado === "falha" || estado === "erro" || estado === "ilegivel";
  const cor = ok ? "var(--good)" : ruim ? "var(--crit)" : estado === "sem-trecho" ? "var(--warn)" : "var(--muted)";
  return (
    <svg className={"smark " + estado} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={cor} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="9" strokeDasharray={estado === "pendente" || estado === "sem" ? "4 3" : undefined} />
      {ok && <motion.path d="m8 12 3 3 5-6" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.35 }} />}
      {ruim && <path d="M12 8v4M12 16h.01" />}
      {estado === "sem-trecho" && <path d="M9 12h6" />}
      {estado === "andamento" && <motion.path d="M12 3a9 9 0 0 1 9 9" animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: "linear" }} style={{ originX: "12px", originY: "12px" }} />}
    </svg>
  );
}
