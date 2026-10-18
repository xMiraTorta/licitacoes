/* Carga do data.json (publicado ao lado do site) e atualização automática a cada 15 min. Só troca se
   `gerado_em` for mais novo. */
import { aplicarDados, store, toast } from "../store";
import type { Painel } from "../types";

const INTERVALO = 15 * 60000;
let ultimoGerado = "";

function valido(j: unknown): j is Painel {
  return !!j && typeof j === "object" && typeof (j as Painel).gerado_em === "string" && Array.isArray((j as Painel).compras);
}

export async function buscar(inicial = false): Promise<void> {
  if (!/^https?:$/.test(location.protocol)) { store.set({ carregando: false, erroCarga: "Abra o site por um endereço http(s): o navegador não lê data.json de arquivo local." }); return; }
  let j: unknown;
  try {
    const r = await fetch("./data.json?t=" + Date.now(), { cache: "no-store" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    j = await r.json();
  } catch (e) {
    console.warn("data.json indisponível:", e);
    if (inicial) store.set({ carregando: false, erroCarga: "Não consegui carregar os dados (data.json). Verifique a conexão e recarregue a página." });
    return;
  }
  if (!valido(j)) { if (inicial) store.set({ carregando: false, erroCarga: "O arquivo de dados veio num formato inesperado." }); return; }
  if (j.gerado_em > ultimoGerado) {
    const primeira = !ultimoGerado;
    ultimoGerado = j.gerado_em;
    aplicarDados(j);
    if (!primeira) {
      const nov = (store.get().prep?.compras || []).filter((c) => c._new && (!c._ms || c._ms >= Date.now())).length;
      toast(`Dados atualizados${nov ? `: ${nov} novas` : ""}`, "ok");
    }
  }
}

export function iniciarAtualizacao(): void {
  void buscar(true);
  window.setInterval(() => void buscar(), INTERVALO);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) void buscar(); });
}

/* Para testes: aplica um conjunto de dados como se tivesse vindo do servidor. */
export function aplicarExterno(j: Painel): void {
  if (!valido(j)) return;
  ultimoGerado = j.gerado_em > ultimoGerado ? j.gerado_em : ultimoGerado;
  aplicarDados(j);
}
