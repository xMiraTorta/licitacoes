/* Número que "roda" até o valor (React Bits "Counter" / "Count Up"), respeitando quem pede menos movimento. */
import { animate, useReducedMotion } from "motion/react";
import { useEffect, useRef, useState } from "react";

export function Contador({ valor, fmt, dur = 0.9, className }: { valor: number; fmt?: (v: number) => string; dur?: number; className?: string }) {
  const reduzir = useReducedMotion();
  const [v, setV] = useState(reduzir ? valor : 0);
  const anterior = useRef(reduzir ? valor : 0);
  useEffect(() => {
    if (reduzir) { setV(valor); anterior.current = valor; return; }
    const ctrl = animate(anterior.current, valor, { duration: dur, ease: [0.2, 0.7, 0.2, 1], onUpdate: (x) => setV(x) });
    anterior.current = valor;
    return () => ctrl.stop();
  }, [valor, dur, reduzir]);
  const f = fmt || ((x: number) => String(Math.round(x)));
  return <span className={className} aria-label={f(valor)}>{f(v)}</span>;
}
