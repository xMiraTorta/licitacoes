/* Formatação em português do Brasil e datas no horário de Brasília (os horários do PNCP são -03:00). */

export const TZ = "America/Sao_Paulo";

const NF0 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const NF1 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });
const NF2 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const NF3 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 });

export const n0 = (v: number): string => NF0.format(v);
export const n1 = (v: number): string => NF1.format(v);
export const n2 = (v: number): string => NF2.format(v);
export const n3 = (v: number): string => NF3.format(v);

export const BRL = (v: number | null | undefined): string => (v == null ? "—" : "R$ " + NF2.format(v));
export const BRL0 = (v: number | null | undefined): string => (v == null ? "—" : "R$ " + NF0.format(v));
/** Valor compacto: R$ 2,9 mi · R$ 217 mil · R$ 850 */
export const BRLc = (v: number | null | undefined): string =>
  v == null ? "—"
    : v >= 1e6 ? "R$ " + NF1.format(v / 1e6) + " mi"
      : v >= 1e4 ? "R$ " + NF0.format(v / 1e3) + " mil"
        : v >= 1e3 ? "R$ " + NF1.format(v / 1e3) + " mil"
          : "R$ " + NF0.format(v);
export const KG = (v: number | null | undefined): string => (v == null ? "—" : NF0.format(v) + " kg");
export const KGc = (v: number | null | undefined): string =>
  v == null ? "—" : v >= 1000 ? NF1.format(v / 1000).replace(/,0$/, "") + " t" : NF0.format(v) + " kg";
/** Percentual com sinal, a partir de uma fração (0.21 → +21,0%). */
export const PCT = (v: number): string => (v > 0 ? "+" : "") + NF1.format(v * 100) + "%";
/** Percentual inteiro com sinal (0.21 → +21%). */
export const PCTi = (v: number): string => (v > 0 ? "+" : "") + Math.round(v * 100) + "%";
/** Percentual sem sinal, sem casas inúteis (0.045 → 4,5%). */
export const PP = (v: number): string => NF1.format(v * 100).replace(/,0$/, "") + "%";

export const WD = ["dom.", "seg.", "ter.", "qua.", "qui.", "sex.", "sáb."];
export const WDL = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"];
export const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
export const MESES_L = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];

export const toMs = (iso: string | null | undefined): number | null => {
  if (!iso) return null;
  const ms = Date.parse(iso.length === 16 ? iso + ":00-03:00" : iso.slice(0, 19) + "-03:00");
  return Number.isNaN(ms) ? null : ms; // texto que não é data (ex.: só "2026-10-21") conta como "sem prazo", não como NaN
};
/** Data e hora de um instante ISO (qualquer fuso) no horário de Brasília: "21/10/2026 09:10". */
const dhFmt = new Intl.DateTimeFormat("pt-BR", { timeZone: TZ, day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
export const fmtDataHoraBR = (iso: string | null | undefined): string => {
  const ms = iso ? Date.parse(iso) : NaN;
  return Number.isNaN(ms) ? "—" : dhFmt.format(new Date(ms)).replace(",", "");
};
export const dayNum = (ymd: string): number => Date.UTC(+ymd.slice(0, 4), +ymd.slice(5, 7) - 1, +ymd.slice(8, 10)) / 864e5;
const dFmt = new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" });
export const todayYMD = (): string => dFmt.format(new Date());
export const ymdFromDay = (d: number): string => new Date(d * 864e5).toISOString().slice(0, 10);

export function fmtPrazo(iso: string | null | undefined, withWd = true): string {
  if (!iso) return "—";
  const d = new Date(Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10)));
  return (withWd ? WD[d.getUTCDay()] + " " : "") + iso.slice(8, 10) + "/" + iso.slice(5, 7) + (iso.length > 10 ? " " + iso.slice(11, 16) : "");
}
export const fmtDate = (iso: string | null | undefined): string =>
  iso ? iso.slice(8, 10) + "/" + iso.slice(5, 7) + "/" + iso.slice(0, 4) + (iso.length > 10 ? " " + iso.slice(11, 16) : "") : "—";
export const fmtDia = (ymd: string | null | undefined): string => (ymd ? ymd.slice(8, 10) + "/" + ymd.slice(5, 7) + "/" + ymd.slice(0, 4) : "—");
export const fmtMin = (m: number | null | undefined): string =>
  m == null ? "" : m < 60 ? m + " min" : Math.floor(m / 60) + "h" + String(m % 60).padStart(2, "0");

export function countdown(ms: number, now = Date.now()): string {
  let s = Math.floor((ms - now) / 1000);
  if (s < 0) return "prazo encerrado";
  const d = Math.floor(s / 86400); s -= d * 86400;
  const h = Math.floor(s / 3600); s -= h * 3600;
  const m = Math.floor(s / 60); s -= m * 60;
  if (d >= 1) return `fecha em ${d}d ${h}h`;
  if (h >= 1) return `fecha em ${h}h ${String(m).padStart(2, "0")}min`;
  return `fecha em ${m}min ${String(s).padStart(2, "0")}s`;
}

export const nrm = (s: string | null | undefined): string =>
  String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

const SMALL = new Set(["de", "da", "do", "das", "dos", "e", "em", "a", "o", "na", "no", "nas", "nos", "para", "por", "com"]);
const KEEP = /^(MG|SP|GO|RJ|BA|PR|SC|RS|ES|MT|MS|DF|PE|CE|PI|PA|AM|AP|RR|RO|AC|TO|MA|RN|PB|AL|SE|II|III|IV|VI|VII|VIII|IX|XI|XII|XIII|UFMG|UFU|UFTM|IFTM|SAAE|DMAE|CRAS|SESC|SENAI|SEBRAE|UASG|ME|EPP|PMMG|CBMMG|TRT|TRE|TJ|MPF|INSS|IBGE|UF|UFV|UFLA|CEFET|COPASA|SUS|SAMU|CIS|CISA|UPA|APAE|CEMIG|IF|HC|EBSERH|FUNASA|IFMG|IFSP|IFGO|USP|UNESP|UNICAMP|UFG|UFBA|UFPE|UFRJ|UFF|UNB)$/;
/** "MUNICIPIO DE SACRAMENTO" → "Municipio de Sacramento" (os órgãos vêm em maiúsculas no PNCP). */
export function tcase(s: string | null | undefined): string {
  if (!s) return "";
  if (s !== s.toUpperCase()) return s;
  return s.toLowerCase().split(/(\s+|-|\/|\(|\))/).map((w, i) => {
    const U = w.toUpperCase();
    if (KEEP.test(U)) return U;
    if (i > 0 && SMALL.has(w)) return w;
    return w.charAt(0).toUpperCase() + w.slice(1);
  }).join("");
}

/** "55,5" · "1.234,56" · "R$ 60" · "1.800" (ponto de milhar, como o site mostra) → número; null para vazio; NaN para lixo. */
export function parseNum(raw: string): number | null {
  const t = raw.trim().replace(/[^\d,.]/g, "");
  if (!t) return raw.trim() ? NaN : null;
  if (t.includes(",")) return parseFloat(t.replace(/\./g, "").replace(",", "."));
  // Sem vírgula: "1.800" ou "12.345.678" é milhar em português (grupos de 3 dígitos); "1.8" ou "0.500" é decimal.
  if (/^[1-9]\d{0,2}(\.\d{3})+$/.test(t)) return parseFloat(t.replace(/\./g, ""));
  return parseFloat(t);
}

export const plural = (n: number, um: string, varios: string): string => (n === 1 ? um : varios);
export const licit = (n: number): string => `${n0(n)} licitaç${n === 1 ? "ão" : "ões"}`;
