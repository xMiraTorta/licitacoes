/* Avisos empilhados no canto, descartáveis com um arrasto (React Bits "Swipe Toast", bencho "Toast stack"). */
import { AnimatePresence, motion } from "motion/react";
import { fecharToast, useStore } from "../store";
import { IX } from "./icons";

export function Toasts() {
  const toasts = useStore((s) => s.toasts);
  return (
    <div className="toasts" role="status" aria-live="polite">
      <AnimatePresence initial={false}>
        {toasts.map((t) => (
          <motion.div
            key={t.id}
            className={"toast " + (t.tipo || "info")}
            initial={{ opacity: 0, y: 16, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.96 }}
            transition={{ type: "spring", stiffness: 420, damping: 32 }}
            drag="x"
            dragConstraints={{ left: 0, right: 0 }}
            dragElastic={0.6}
            onDragEnd={(_, info) => { if (Math.abs(info.offset.x) > 80) fecharToast(t.id); }}
          >
            <span className="toast-dot" aria-hidden="true" />
            <span className="toast-msg">{t.msg}{t.n && t.n > 1 ? <span className="toast-n mono" data-n={t.n}>×{t.n}</span> : null}</span>
            {t.acao && <button type="button" className="linkbtn" onClick={() => { t.acao!.fn(); fecharToast(t.id); }}>{t.acao.rotulo}</button>}
            <button type="button" className="toast-x" aria-label="Fechar aviso" onClick={() => fecharToast(t.id)}><IX size={14} /></button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
