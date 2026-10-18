import { useEffect, useRef, useState } from "react";

export function useMedia(q: string): boolean {
  const [ok, setOk] = useState(() => window.matchMedia(q).matches);
  useEffect(() => {
    const m = window.matchMedia(q);
    const h = () => setOk(m.matches);
    m.addEventListener("change", h);
    return () => m.removeEventListener("change", h);
  }, [q]);
  return ok;
}

export const useCelular = (): boolean => useMedia("(max-width: 900px)");

/* Relógio de 1 s para contagens regressivas (só enquanto o componente existe). */
export function useRelogio(ativo = true): number {
  const [t, setT] = useState(Date.now());
  useEffect(() => {
    if (!ativo) return;
    const id = window.setInterval(() => setT(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [ativo]);
  return t;
}

/* Gravação com atraso: guarda o último valor e grava depois de `ms` sem digitar; `flush` grava já. */
export function useDebounce<T>(fn: (v: T) => void, ms = 350): { push: (v: T) => void; flush: () => void } {
  const timer = useRef(0), pend = useRef<{ v: T } | null>(null), fnRef = useRef(fn);
  fnRef.current = fn;
  const flush = () => { if (pend.current) { const v = pend.current.v; pend.current = null; window.clearTimeout(timer.current); fnRef.current(v); } };
  const push = (v: T) => { pend.current = { v }; window.clearTimeout(timer.current); timer.current = window.setTimeout(flush, ms); };
  useEffect(() => () => flush(), []); // eslint-disable-line react-hooks/exhaustive-deps
  return { push, flush };
}
