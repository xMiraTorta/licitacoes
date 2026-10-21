/* Paleta de comandos (Ctrl K): acha licitação, troca de aba, executa ações. */
import { Command } from "cmdk";
import { useEffect, useMemo, useState } from "react";
import { BRLc, nrm } from "../lib/format";
import { isOpen, mgCls } from "../lib/modelo";
import { abrirDetalhe, navegar } from "../router";
import { alternarTema, setF, setPaleta, temaAtual, useStore } from "../store";
import { syncAgora } from "../sync/github";
import { ISearch } from "./icons";

export function Paleta() {
  const aberta = useStore((s) => s.paleta);
  const prep = useStore((s) => s.prep);
  const [q, setQ] = useState("");
  useEffect(() => { if (aberta) setQ(""); }, [aberta]);
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setPaleta(!useStoreGet().paleta); }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);
  const termos = nrm(q).split(/\s+/).filter(Boolean);
  const achadas = useMemo(() => {
    if (!prep || !termos.length) return [];
    const now = Date.now();
    return prep.compras.filter((c) => isOpen(c, now) && !c.dup_of && termos.every((t) => c._s.includes(t))).slice(0, 8);
  }, [prep, q]); // eslint-disable-line react-hooks/exhaustive-deps
  const vai = (fn: () => void) => { setPaleta(false); fn(); };
  return (
    <Command.Dialog open={aberta} onOpenChange={setPaleta} label="Busca e ações" contentClassName="paleta" shouldFilter={false} loop>
      <div className="paleta-in">
        <ISearch size={18} />
        <Command.Input value={q} onValueChange={setQ} placeholder="Buscar município, órgão, nº ou ação" autoFocus />
        <kbd>esc</kbd>
      </div>
      <Command.List>
        <Command.Empty>{termos.length ? "Nenhuma licitação aberta com esse texto." : "Digite para buscar, ou escolha abaixo."}</Command.Empty>
        {achadas.length > 0 && (
          <Command.Group heading={`Licitações · ${achadas.length}${achadas.length === 8 ? "+" : ""}`}>
            {achadas.map((c) => (
              <Command.Item key={c.chave} value={"c:" + c.chave} onSelect={() => vai(() => abrirDetalhe(c.chave))}>
                <span className="p-main">
                  <b>{c.mun} <span className="muted">{c.uf}</span> · {c._orgao}</b>
                  <span className="small muted">{c._niv || c.tipos[0]} · {c.dist != null ? c.dist + " km · " : ""}{c.kg ? Math.round(c.kg).toLocaleString("pt-BR") + " kg · " : ""}fecha {c.fim ? c.fim.slice(8, 10) + "/" + c.fim.slice(5, 7) : "sem prazo"}</span>
                </span>
                {c._mg && <span className={"mg " + mgCls(c._mg.mp)}>{Math.round(c._mg.mp * 100)}% · {c._mg.lucro < 0 ? "−" : ""}{BRLc(Math.abs(c._mg.lucro))}</span>}
              </Command.Item>
            ))}
            {termos.length > 0 && <Command.Item value="filtrar" onSelect={() => vai(() => { setF({ q }); navegar("oportunidades"); })}>Ver todas em Oportunidades com “{q}” <kbd>↵</kbd></Command.Item>}
          </Command.Group>
        )}
        <Command.Group heading="Ir para">
          <Command.Item value="hoje" onSelect={() => vai(() => navegar("hoje"))}>Hoje <kbd>G H</kbd></Command.Item>
          <Command.Item value="oportunidades" onSelect={() => vai(() => navegar("oportunidades"))}>Oportunidades <kbd>G O</kbd></Command.Item>
          <Command.Item value="propostas" onSelect={() => vai(() => navegar("propostas"))}>Minhas propostas <kbd>G P</kbd></Command.Item>
          <Command.Item value="mercado" onSelect={() => vai(() => navegar("mercado"))}>Mercado: café verde e marcas <kbd>G M</kbd></Command.Item>
          <Command.Item value="guia" onSelect={() => vai(() => navegar("guia"))}>Guia da proposta <kbd>G G</kbd></Command.Item>
          <Command.Item value="ajustes" onSelect={() => vai(() => navegar("ajustes"))}>Meus custos, pisos e ajustes <kbd>G C</kbd></Command.Item>
        </Command.Group>
        <Command.Group heading="Ações">
          <Command.Item value="urgentes" onSelect={() => vai(() => { setF({ urg: true }); navegar("oportunidades"); })}>Só as que fecham em 3 dias</Command.Item>
          <Command.Item value="perto" onSelect={() => vai(() => { setF({ dist: 600 }); navegar("oportunidades"); })}>Só até 600 km de Uberaba</Command.Item>
          <Command.Item value="tema" onSelect={() => vai(alternarTema)}>Mudar para tema {temaAtual() === "dark" ? "claro" : "escuro"} <kbd>T</kbd></Command.Item>
          <Command.Item value="sincronizar" onSelect={() => vai(() => void syncAgora())}>Sincronizar anotações agora</Command.Item>
          <Command.Item value="atalhos" onSelect={() => vai(() => navegar("ajustes"))}>Atalhos do teclado <kbd>?</kbd></Command.Item>
        </Command.Group>
      </Command.List>
      <div className="paleta-foot mono"><span>↑↓ navegar</span><span>↵ abrir</span><span>esc fechar</span></div>
    </Command.Dialog>
  );
}

import { store } from "../store";
const useStoreGet = () => store.get();
