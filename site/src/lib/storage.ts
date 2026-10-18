/* Armazenamento local. Chaves e formatos são contrato (CLAUDE.md): mudar só com migração testada.
   Dado salvo ilegível: guarda uma cópia intacta antes de seguir com o valor padrão, para nunca apagar
   anotações em silêncio. Se nem a cópia couber, bloqueia a gravação daquela chave. */

export const PFX = "monitorLicitacoes.";
export const K = {
  meusDados: PFX + "meusDados.v1",
  ui: PFX + "ui.v1",
  checklist: PFX + "checklist.v1",
  pisos: PFX + "pisos.v1",
  custos: PFX + "custos.v1",
  github: PFX + "github.v1",
  sync: PFX + "sync.v1",
  presync: PFX + "antesDaSincronizacao.v1",
} as const;

const LS: Storage | null = (() => {
  try {
    const k = "__t";
    localStorage.setItem(k, "1");
    localStorage.removeItem(k);
    return localStorage;
  } catch {
    return null;
  }
})();
const mem: Record<string, string> = {};
export const BAD: Record<string, string | null> = {};
export const LOCKED = new Set<string>();
let avisar: ((msg: string) => void) | null = null;
export const aoFalharGravacao = (fn: (msg: string) => void): void => { avisar = fn; };

export function lget<T>(k: string, d: T): T {
  let v: string | null | undefined;
  try {
    v = LS ? LS.getItem(k) : mem[k];
  } catch (e) {
    console.error("Falha ao ler", k, e);
    return d;
  }
  if (!v) return d;
  try {
    return JSON.parse(v) as T;
  } catch (e) {
    if (!(k in BAD)) {
      const bk = k + ".ilegivel." + new Date().toISOString();
      try {
        LS!.setItem(bk, v);
        BAD[k] = bk;
      } catch {
        BAD[k] = null;
        LOCKED.add(k);
      }
      console.error("Dados salvos ilegíveis em", k, "- cópia:", BAD[k], e);
    }
    return d;
  }
}

export function lset(k: string, v: unknown): void {
  if (LOCKED.has(k)) {
    avisar?.("Não salvei: os dados antigos estão ilegíveis e não consegui guardar uma cópia.");
    return;
  }
  const s = JSON.stringify(v);
  if (LS) {
    try {
      LS.setItem(k, s);
    } catch {
      avisar?.("Não foi possível salvar no navegador.");
    }
  } else mem[k] = s;
}

export function lremove(k: string): void {
  if (LS) LS.removeItem(k); else delete mem[k];
}

export const temLocalStorage = (): boolean => !!LS;
export const lraw = (k: string): string | null => (LS ? LS.getItem(k) : mem[k] ?? null);
