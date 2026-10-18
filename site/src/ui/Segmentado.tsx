/* Controle segmentado com indicador que desliza (React Bits "Rubber Segment", sem o exagero elástico). */
import { motion } from "motion/react";
import { useId } from "react";

export function Segmentado<T extends string>({ opcoes, valor, onChange, rotulo, pequeno }: { opcoes: [T, string][]; valor: T; onChange: (v: T) => void; rotulo: string; pequeno?: boolean }) {
  const id = useId();
  return (
    <div className={"seg" + (pequeno ? " sm" : "")} role="group" aria-label={rotulo}>
      {opcoes.map(([k, t]) => (
        <button key={k} type="button" aria-pressed={valor === k} onClick={() => onChange(k)}>
          {valor === k && <motion.span layoutId={"thumb-" + id} className="thumb" transition={{ type: "spring", stiffness: 500, damping: 38 }} />}
          <span style={{ position: "relative", zIndex: 1 }}>{t}</span>
        </button>
      ))}
    </div>
  );
}
