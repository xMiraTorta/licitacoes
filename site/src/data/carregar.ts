/* Carga do data.json (publicado ao lado do site) e atualização automática a cada 15 min. Só troca se o arquivo
   for mais novo: `publicado_em` (toda gravação, inclusive só de preços de mercado) ou, nos arquivos antigos, `gerado_em`. */
import { aplicarDados, store, toast } from "../store";
import type { Painel } from "../types";

const INTERVALO = 15 * 60000;
let ultimaVersao = "";

function valido(j: unknown): j is Painel {
  return !!j && typeof j === "object" && typeof (j as Painel).gerado_em === "string" && Array.isArray((j as Painel).compras);
}
const versaoDe = (j: Painel): string => j.publicado_em || j.gerado_em;

/** Baixa o data.json; devolve true se trouxe dados mais novos. */
export async function buscar(inicial = false): Promise<boolean> {
  if (!/^https?:$/.test(location.protocol)) { store.set({ carregando: false, erroCarga: "Abra o site por um endereço http(s): o navegador não lê data.json de arquivo local." }); return false; }
  let j: unknown;
  try {
    const r = await fetch("./data.json?t=" + Date.now(), { cache: "no-store" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    j = await r.json();
  } catch (e) {
    console.warn("data.json indisponível:", e);
    if (inicial) store.set({ carregando: false, erroCarga: "Não consegui carregar os dados (data.json). Verifique a conexão e recarregue a página." });
    return false;
  }
  if (!valido(j)) { if (inicial) store.set({ carregando: false, erroCarga: "O arquivo de dados veio num formato inesperado." }); return false; }
  if (versaoDe(j) <= ultimaVersao) return false;
  const primeira = !ultimaVersao;
  ultimaVersao = versaoDe(j);
  aplicarDados(j);
  if (!primeira) {
    const nov = (store.get().prep?.compras || []).filter((c) => c._new && (!c._ms || c._ms >= Date.now())).length;
    toast(`Dados atualizados${nov ? `: ${nov} novas` : ""}`, "ok");
  }
  return true;
}

export function iniciarAtualizacao(): void {
  void buscar(true);
  window.setInterval(() => void buscar(), INTERVALO);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) void buscar(); });
}

/* Para testes: aplica um conjunto de dados como se tivesse vindo do servidor. */
export function aplicarExterno(j: Painel): void {
  if (!valido(j)) return;
  ultimaVersao = versaoDe(j) > ultimaVersao ? versaoDe(j) : ultimaVersao;
  aplicarDados(j);
}
