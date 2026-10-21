/* Mapa do Brasil (contorno oficial do IBGE em src/data/mapa-uf.json, gerado por `python -m coletor mapa`):
   estados coloridos por quantidade, anéis de distância a partir da origem e pontos das melhores oportunidades. */
import { useMemo } from "react";
import MAPA from "../data/mapa-uf.json";
import { BRLc, licit, n0 } from "../lib/format";

interface MapaJson { viewBox: string; uf: Record<string, string>; centro: Record<string, [number, number]> }
const M = MAPA as unknown as MapaJson;
const UF_PEQ = new Set(["DF", "SE", "AL", "RN", "PB", "ES", "RJ"]); // área pequena: sem rótulo dentro
/* Projeção equirretangular da malha (coletor/mapa.py): caixa da malha do IBGE. Calibrada pelo centro do DF. */
const LON0 = -73.99, LON1 = -34.79, LAT0 = -33.75, LAT1 = 5.27;
const KX = Math.cos((((LAT0 + LAT1) / 2) * Math.PI) / 180), ESC = 600 / ((LON1 - LON0) * KX);
const bru = { lat: -15.78, lon: -47.93 };
const DX = (M.centro.DF?.[0] ?? 0) - (bru.lon - LON0) * KX * ESC, DY = (M.centro.DF?.[1] ?? 0) - (LAT1 - bru.lat) * ESC;
export const projetar = (lat: number, lon: number): [number, number] => [(lon - LON0) * KX * ESC + DX, (LAT1 - lat) * ESC + DY];
export const KM_PX = ESC / 111;

export interface Ponto { chave: string; lat: number; lon: number; peso: number; rotulo: string }
interface Props {
  porUF: Record<string, { n: number; lucro?: number; vcafe?: number }>;
  sel?: string | null;
  onSel?: (uf: string) => void;
  origem?: { lat?: number; lon?: number; nome?: string } | null;
  aneis?: number[];
  pontos?: Ponto[];
  onPonto?: (chave: string) => void;
  onHover?: (uf: string | null, texto: string | null, pos?: { x: number; y: number }) => void; // só mouse: no toque o estado fica selecionado
  compacto?: boolean;
}
const cor = (n: number): string => (n >= 40 ? "var(--seq-6)" : n >= 20 ? "var(--seq-5)" : n >= 10 ? "var(--seq-4)" : n >= 6 ? "var(--seq-3)" : n >= 3 ? "var(--seq-2)" : n >= 1 ? "var(--seq-1)" : "var(--surface-2)");

export function Mapa({ porUF, sel, onSel, origem, aneis = [300, 600, 1000], pontos = [], onPonto, onHover, compacto }: Props) {
  const ufs = useMemo(() => Object.keys(M.uf).sort((a, b) => Number(a === "DF") - Number(b === "DF")), []); // DF por cima de GO
  const o = origem && origem.lat != null && origem.lon != null ? projetar(origem.lat, origem.lon) : null;
  const maxPeso = Math.max(1, ...pontos.map((p) => p.peso));
  const mouse = (e: React.PointerEvent) => (e.pointerType === "mouse" ? { x: e.clientX, y: e.clientY } : undefined);
  const hoverUF = (uf: string) => (e: React.PointerEvent) => { const x = porUF[uf]; onHover?.(uf, `${uf}: ${licit(x ? x.n : 0)}${x && x.lucro ? ` · lucro estimado ${BRLc(x.lucro)}` : ""}`, mouse(e)); };
  return (
    <svg viewBox={M.viewBox} className={"mapa" + (compacto ? " compacto" : "")} role="img" aria-label="Mapa do Brasil com licitações abertas por estado">
      {ufs.map((uf) => {
        const x = porUF[uf] || { n: 0 };
        return (
          <path key={uf} className={"uf" + (sel === uf ? " sel" : "")} d={M.uf[uf]} fill={cor(x.n)} onClick={() => onSel?.(uf)} tabIndex={onSel ? 0 : -1} role={onSel ? "button" : undefined}
            onKeyDown={(e) => { if (onSel && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); onSel(uf); } }} aria-label={`${uf}: ${licit(x.n)}`}
            onPointerEnter={hoverUF(uf)} onPointerMove={hoverUF(uf)} onPointerLeave={() => onHover?.(null, null)}>
            {!onHover && <title>{uf}: {licit(x.n)}{x.lucro ? ` · lucro estimado ${BRLc(x.lucro)}` : ""}</title>}
          </path>
        );
      })}
      {o && aneis.map((km) => (
        <g key={km}>
          <circle cx={o[0]} cy={o[1]} r={km * KM_PX} className="anel" />
          <text x={o[0] + km * KM_PX + 3} y={o[1] + 3} className="anel-t">{n0(km)}</text>
        </g>
      ))}
      {ufs.filter((uf) => !UF_PEQ.has(uf) && !compacto).map((uf) => {
        const [cx, cy] = M.centro[uf], x = porUF[uf];
        return <text key={uf} x={cx} y={cy + 4} textAnchor="middle" className={"ufl" + (x && x.n >= 20 ? " hot" : "")}>{uf}{x && x.n ? <tspan x={cx} dy="12">{x.n}</tspan> : null}</text>;
      })}
      {pontos.map((p) => {
        const [x, y] = projetar(p.lat, p.lon);
        return (
          <circle key={p.chave} cx={x} cy={y} r={4 + 9 * Math.sqrt(p.peso / maxPeso)} className="ponto" onClick={() => onPonto?.(p.chave)} tabIndex={onPonto ? 0 : -1} role={onPonto ? "button" : undefined} aria-label={p.rotulo}
            onPointerEnter={(e) => onHover?.(null, p.rotulo + " · clique para abrir", mouse(e))} onPointerMove={(e) => onHover?.(null, p.rotulo + " · clique para abrir", mouse(e))} onPointerLeave={() => onHover?.(null, null)}>
            {!onHover && <title>{p.rotulo}</title>}
          </circle>
        );
      })}
      {o && <circle cx={o[0]} cy={o[1]} r="5" className="origem"><title>{origem?.nome || "Origem"}</title></circle>}
    </svg>
  );
}
