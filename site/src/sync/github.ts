/* Gravação automática das anotações no GitHub.
   Arquivo dados/meus-dados.json na branch "dados" deste repositório (público por decisão do dono: as anotações
   ficam visíveis). Branch própria porque cada gravação na main reconstruiria o GitHub Pages. O próprio site cria
   a branch na primeira gravação. Grava pela API do GitHub com uma chave de acesso que fica SÓ neste navegador.
   Junta aparelhos por item: vale a alteração mais recente (campo upd); remoção vira {upd} (marca de removido).
   Checklist, pisos e meus custos: vale o conjunto alterado por último (upd em meta). */
import { K, lget, lraw, lremove, lset } from "../lib/storage";
import { aplicarJuncao, aoAlterarAnotacoes, CUSTO_KEYS, nivelValido, setMeta, setSync, store, temAnotacao, toast } from "../store";
import type { Checklist, MeusCustos, MeusDados, Pisos } from "../types";

export const SYNC_PATH = "dados/meus-dados.json";
export const SYNC_BRANCH = "dados";
const SYNC_ATRASO = 3000;
const MARCA_DIAS = 180;

export const REPO: string | null = (() => {
  const h = location.hostname.match(/^([\w-]+)\.github\.io$/i), p = location.pathname.split("/").filter(Boolean)[0];
  if (h && p) return h[1] + "/" + p;
  return new URLSearchParams(location.search).get("repo"); // só fora do GitHub Pages (testes, cópia local)
})();

const agoraISO = (): string => new Date().toISOString();
let timer = 0, rodando = false, denovo = false;

interface Doc {
  app: string; versao: number; atualizado_em: string; meus_dados: MeusDados;
  checklist: { itens: Checklist; upd: string }; pisos: { valores: Pisos; upd: string }; custos: { valores: MeusCustos; upd: string };
}
interface Juncao { md: MeusDados; cl: Checklist; clu: string; pi: Pisos; piu: string; cu: MeusCustos; cuu: string; mudouLocal: boolean }

/* Junta o que veio do GitHub com o local. Devolve o documento final e se o local mudou. */
export function juntar(rem: Partial<Doc> | null): Juncao {
  const s = store.get();
  let mudouLocal = false;
  const md: MeusDados = { ...s.wf }, rmd = (rem && rem.meus_dados) || {};
  for (const [k, v] of Object.entries(rmd)) {
    if (!/^\d{14}-\d+-\d{6}\/\d{4}$/.test(k) || !v || typeof v !== "object") continue;
    if (!md[k] || (v.upd || "") > (md[k].upd || "")) { md[k] = v; mudouLocal = true; }
  }
  const lim = new Date(Date.now() - MARCA_DIAS * 864e5).toISOString();
  for (const [k, v] of Object.entries(md)) if (!temAnotacao(v) && (v.upd || "") < lim) delete md[k]; // marcas antigas
  let cl = s.checklist, clu = s.meta.checklist_upd, pi = s.pisos, piu = s.meta.pisos_upd, cu = s.custos, cuu = s.meta.custos_upd;
  const rcl = rem?.checklist, rpi = rem?.pisos, rcu = rem?.custos;
  if (rcl && rcl.itens && (rcl.upd || "") > (clu || "")) { cl = Object.fromEntries(Object.entries(rcl.itens).filter(([k, v]) => /^\d+$/.test(k) && v === 1)) as Checklist; clu = rcl.upd; mudouLocal = true; }
  if (rpi && rpi.valores && (rpi.upd || "") > (piu || "")) { pi = Object.fromEntries(Object.entries(rpi.valores).filter(([k, v]) => nivelValido(k) && typeof v === "number" && v > 0)); piu = rpi.upd; mudouLocal = true; }
  if (rcu && rcu.valores && (rcu.upd || "") > (cuu || "")) {
    cu = Object.fromEntries(Object.entries(rcu.valores).filter(([k, v]) => (CUSTO_KEYS.has(k) || (k.startsWith("grao|") && nivelValido(k.slice(5)))) && typeof v === "number" && v >= 0));
    cuu = rcu.upd; mudouLocal = true;
  }
  return { md, cl, clu, pi, piu, cu, cuu, mudouLocal };
}

function aplicar(j: Juncao): void {
  const s = store.get();
  if (lraw(K.presync) == null) lset(K.presync, { salvo_em: agoraISO(), meus_dados: s.wf, checklist: s.checklist, pisos: s.pisos, custos: s.custos }); // cópia antes da 1ª junção
  aplicarJuncao(j);
}

const b64enc = (s: string): string => { const b = new TextEncoder().encode(s); let r = ""; for (let i = 0; i < b.length; i += 8192) r += String.fromCharCode.apply(null, Array.from(b.subarray(i, i + 8192))); return btoa(r); };
const b64dec = (s: string): string => new TextDecoder().decode(Uint8Array.from(atob(s.replace(/\s/g, "")), (c) => c.charCodeAt(0)));

async function gh(method: string, body: unknown, caminho = `contents/${SYNC_PATH}`): Promise<Response> {
  const h: Record<string, string> = { Accept: "application/vnd.github+json" };
  const tok = store.get().sync.token;
  if (tok) h.Authorization = "Bearer " + tok;
  if (body) h["Content-Type"] = "application/json";
  const q = method === "GET" && caminho.startsWith("contents/") ? `?ref=${SYNC_BRANCH}&t=${Date.now()}` : "";
  return fetch(`https://api.github.com/repos/${REPO}/${caminho}${q}`, { method, headers: h, body: body ? JSON.stringify(body) : undefined, cache: "no-store" });
}
/* 401/403 com chave: a chave foi recusada. Sem chave, o GitHub responde 403 (ou 429) quando este endereço de internet
   passou do limite de consultas sem identificação (60 por hora, comum em rede de celular ou de escritório): não é
   problema de chave, é só esperar. */
const erroDe = (status: number): Error => {
  if ((status === 401 || status === 403) && store.get().sync.token) return new Error("chave");
  if (status === 403 || status === 429) return new Error("limite");
  return new Error("HTTP " + status);
};

/* Cria a branch "dados" a partir da main, se ainda não existir (primeira gravação). */
async function garantirBranch(): Promise<void> {
  const b = await gh("GET", null, `branches/${SYNC_BRANCH}`);
  if (b.ok) return;
  if (b.status !== 404) throw erroDe(b.status);
  const m = await gh("GET", null, "git/ref/heads/main");
  if (!m.ok) throw new Error("HTTP " + m.status);
  const r = await gh("POST", { ref: "refs/heads/" + SYNC_BRANCH, sha: (await m.json()).object.sha }, "git/refs");
  if (!r.ok && r.status !== 422) throw erroDe(r.status); // 422: já existe
}

async function lerRemoto(): Promise<{ doc: Doc | null; sha: string | null }> {
  const r = await gh("GET", null);
  if (r.status === 404) return { doc: null, sha: null };
  if (!r.ok) throw erroDe(r.status);
  const j = await r.json();
  return { doc: JSON.parse(b64dec(j.content)) as Doc, sha: j.sha };
}

/* Busca, junta e (com chave) grava. Uma de cada vez; pedido durante uma gravação roda logo em seguida. */
export async function syncAgora(soLer = false): Promise<void> {
  if (!REPO) { setSync({ estado: "local" }); return; }
  if (rodando) { denovo = true; return; }
  rodando = true;
  window.clearTimeout(timer);
  try {
    for (let tentativa = 1; ; tentativa++) {
      const { doc, sha } = await lerRemoto();
      const j = juntar(doc), feitas = store.get().sync.mudancas;
      if (j.mudouLocal) aplicar(j); // veio algo mais novo de outro aparelho
      const s = store.get();
      if (soLer || !s.sync.token || (!s.meta.pendente && doc)) { setSync({ estado: s.sync.token ? "ok" : "local", quando: s.sync.token ? agoraISO() : s.sync.quando }); break; }
      setSync({ estado: "salvando" });
      const novo: Doc = { app: "monitor-licitacoes", versao: 2, atualizado_em: agoraISO(), meus_dados: j.md, checklist: { itens: j.cl, upd: j.clu }, pisos: { valores: j.pi, upd: j.piu }, custos: { valores: j.cu, upd: j.cuu } };
      if (!sha) await garantirBranch();
      const r = await gh("PUT", { message: "Minhas anotações (salvo pelo site)", content: b64enc(JSON.stringify(novo, null, 1) + "\n"), branch: SYNC_BRANCH, ...(sha ? { sha } : {}) });
      if (r.ok) {
        setSync({ quando: agoraISO(), erro: "" });
        if (store.get().sync.mudancas === feitas) { setMeta({ pendente: false }); setSync({ estado: "ok" }); } else denovo = true; // alteração durante o envio: grava de novo
        break;
      }
      if ((r.status === 409 || r.status === 422) && tentativa < 4) continue; // alguém gravou no meio: busca de novo e junta
      throw erroDe(r.status);
    }
  } catch (e) {
    const motivo = (e as Error).message, chave = motivo === "chave", limite = motivo === "limite";
    if (!store.get().sync.token) {
      // Sem chave só há leitura: nada do dono fica em risco. Continua "só neste aparelho" e lê de novo depois
      // (a cada 15 min e ao voltar para a aba); não é erro para mostrar.
      console.warn("Leitura das anotações no GitHub falhou:", e);
      setSync({ estado: "local", erro: "" });
    } else {
      console.error("Gravação no GitHub falhou:", e);
      setSync({ estado: "erro", erro: chave ? "A chave de acesso foi recusada (vencida, apagada ou sem permissão de escrita neste repositório)."
        : limite ? "O GitHub limitou as consultas por enquanto. Suas alterações estão guardadas neste aparelho e serão enviadas na próxima tentativa."
        : "Sem conexão com o GitHub agora. Suas alterações estão guardadas neste aparelho e serão enviadas na próxima tentativa." });
    }
    if (!chave && !limite) { window.clearTimeout(timer); timer = window.setTimeout(() => syncAgora(), 60000); } // limite: insistir só gasta a cota
  } finally {
    rodando = false;
    if (denovo) { denovo = false; void syncAgora(); }
  }
}

/* Chamado a cada alteração local: marca pendente e agenda a gravação. */
function alterou(o: "anotações" | "checklist" | "pisos" | "custos"): void {
  const t = agoraISO();
  setMeta({ pendente: true, ...(o === "checklist" ? { checklist_upd: t } : o === "pisos" ? { pisos_upd: t } : o === "custos" ? { custos_upd: t } : {}) });
  setSync({ mudancas: store.get().sync.mudancas + 1 });
  if (!store.get().sync.token) return;
  window.clearTimeout(timer);
  timer = window.setTimeout(() => syncAgora(), SYNC_ATRASO);
  setSync({ estado: "salvando" });
}
aoAlterarAnotacoes(alterou);

export async function conectar(tok: string): Promise<boolean> {
  const token = tok.trim();
  setSync({ token, erro: "" });
  try {
    const r = await fetch(`https://api.github.com/repos/${REPO}`, { headers: { Accept: "application/vnd.github+json", Authorization: "Bearer " + token } });
    const j = r.ok ? await r.json() : null;
    if (!j || !(j.permissions && j.permissions.push)) throw new Error("chave");
  } catch {
    setSync({ token: "", estado: "erro", erro: "Essa chave não tem permissão para gravar neste repositório. Confira os passos." });
    return false;
  }
  lset(K.github, { token });
  setMeta({ pendente: true });
  toast("Conectado. Gravando suas anotações no GitHub…", "ok");
  await syncAgora();
  return true;
}

export function desconectar(): void {
  lremove(K.github);
  setSync({ token: "", estado: "local", erro: "" });
}

export function flushSync(): void {
  const s = store.get();
  if (s.meta.pendente && s.sync.token) { window.clearTimeout(timer); void syncAgora(); }
}

export const temChaveSalva = (): boolean => !!(lget<{ token?: string }>(K.github, {}) || {}).token;
