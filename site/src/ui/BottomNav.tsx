/* Barra de abas do celular (aparece só em telas estreitas; ver app.css). */
import { navegar, TAB_NOME } from "../router";
import { useStore } from "../store";
import { IBoard, IBook, IChart, IHome, IList } from "./icons";

const ICONES = { hoje: IHome, oportunidades: IList, propostas: IBoard, mercado: IChart, guia: IBook } as const;

export function BottomNav() {
  const tab = useStore((s) => s.ui.tab);
  const opened = useStore((s) => s.opened);
  if (opened) return null;
  return (
    <nav className="bottom-nav" aria-label="Seções">
      {(Object.keys(ICONES) as (keyof typeof ICONES)[]).map((t) => {
        const I = ICONES[t];
        return <button key={t} type="button" aria-current={tab === t ? "page" : undefined} onClick={() => navegar(t)}><I size={20} /><span>{TAB_NOME[t]}</span></button>;
      })}
    </nav>
  );
}
