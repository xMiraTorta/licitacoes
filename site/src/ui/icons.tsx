import type { SVGProps } from "react";

const base = (p: SVGProps<SVGSVGElement>, size = 16) => ({
  width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.9, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true, ...p,
});
type P = SVGProps<SVGSVGElement> & { size?: number };

export const ISearch = ({ size, ...p }: P) => <svg {...base(p, size)}><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>;
export const ISettings = ({ size, ...p }: P) => <svg {...base(p, size)}><path d="M4 7h10M18 7h2M4 17h4M12 17h8" /><circle cx="16" cy="7" r="2" /><circle cx="10" cy="17" r="2" /></svg>;
export const ISun = ({ size, ...p }: P) => <svg {...base(p, size)}><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></svg>;
export const IMoon = ({ size, ...p }: P) => <svg {...base(p, size)}><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" /></svg>;
export const IX = ({ size, ...p }: P) => <svg {...base(p, size)}><path d="M18 6 6 18M6 6l12 12" /></svg>;
export const ICheck = ({ size, ...p }: P) => <svg {...base(p, size)}><path d="m5 12 4 4L19 6" /></svg>;
export const IChevron = ({ size, ...p }: P) => <svg {...base(p, size)}><path d="m9 6 6 6-6 6" /></svg>;
export const IDown = ({ size, ...p }: P) => <svg {...base(p, size)}><path d="m6 9 6 6 6-6" /></svg>;
export const IExt = ({ size, ...p }: P) => <svg {...base(p, size)}><path d="M14 4h6v6M20 4l-9 9M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5" /></svg>;
export const IRefresh = ({ size, ...p }: P) => <svg {...base(p, size)}><path d="M20 12a8 8 0 1 1-2.3-5.7M20 4v5h-5" /></svg>;
export const IFilter = ({ size, ...p }: P) => <svg {...base(p, size)}><path d="M3 5h18l-7 8v6l-4 2v-8z" /></svg>;
export const IStar = ({ size, filled, ...p }: P & { filled?: boolean }) => <svg {...base(p, size)} fill={filled ? "currentColor" : "none"}><path d="m12 3 2.8 5.9 6.4.8-4.7 4.4 1.2 6.4L12 17.4l-5.7 3.1 1.2-6.4L2.8 9.7l6.4-.8z" /></svg>;
export const IMap = ({ size, ...p }: P) => <svg {...base(p, size)}><path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2z" /><path d="M9 4v14M15 6v14" /></svg>;
export const ICoffee = ({ size, ...p }: P) => <svg {...base(p, size)}><path d="M4 10h12a4 4 0 0 1 0 8H4z" /><path d="M4 10V5h12v5" /><path d="M8 2v2M12 2v2" /></svg>;
export const IArrow = ({ size, ...p }: P) => <svg {...base(p, size)}><path d="M5 12h14M13 6l6 6-6 6" /></svg>;
export const IBack = ({ size, ...p }: P) => <svg {...base(p, size)}><path d="M19 12H5M11 18l-6-6 6-6" /></svg>;
export const IInfo = ({ size, ...p }: P) => <svg {...base(p, size)}><circle cx="12" cy="12" r="9" /><path d="M12 8h.01M11 12h1v4h1" /></svg>;
export const ICopy = ({ size, ...p }: P) => <svg {...base(p, size)}><rect x="9" y="9" width="11" height="11" rx="2" /><path d="M5 15V5a1 1 0 0 1 1-1h10" /></svg>;
export const IClock = ({ size, ...p }: P) => <svg {...base(p, size)}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>;
export const IHome = ({ size, ...p }: P) => <svg {...base(p, size)}><path d="m3 11 9-7 9 7v9a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z" /></svg>;
export const IList = ({ size, ...p }: P) => <svg {...base(p, size)}><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" /></svg>;
export const IBoard = ({ size, ...p }: P) => <svg {...base(p, size)}><rect x="3" y="4" width="5" height="16" rx="1" /><rect x="10" y="4" width="5" height="10" rx="1" /><rect x="17" y="4" width="4" height="13" rx="1" /></svg>;
export const IChart = ({ size, ...p }: P) => <svg {...base(p, size)}><path d="M4 20V10M10 20V4M16 20v-8M22 20H2" /></svg>;
export const IBook = ({ size, ...p }: P) => <svg {...base(p, size)}><path d="M4 5a2 2 0 0 1 2-2h14v16H6a2 2 0 0 0-2 2z" /><path d="M4 19a2 2 0 0 1 2-2h14" /></svg>;
export const IDoc = ({ size, ...p }: P) => <svg {...base(p, size)}><path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z" /><path d="M14 3v5h5M9 13h6M9 17h6" /></svg>;
export const IWarn = ({ size, ...p }: P) => <svg {...base(p, size)}><path d="M12 3 2 20h20z" /><path d="M12 9v5M12 17h.01" /></svg>;
export const IPlus = ({ size, ...p }: P) => <svg {...base(p, size)}><path d="M12 5v14M5 12h14" /></svg>;
export const IMinus = ({ size, ...p }: P) => <svg {...base(p, size)}><path d="M5 12h14" /></svg>;
export const ITruck = ({ size, ...p }: P) => <svg {...base(p, size)}><path d="M3 7h11v9H3zM14 10h4l3 3v3h-7z" /><circle cx="7" cy="18" r="2" /><circle cx="17" cy="18" r="2" /></svg>;
export const IPin = ({ size, ...p }: P) => <svg {...base(p, size)}><path d="M12 21s-7-6.5-7-11a7 7 0 0 1 14 0c0 4.5-7 11-7 11z" /><circle cx="12" cy="10" r="2.5" /></svg>;
export const ISpark = ({ size, ...p }: P) => <svg {...base(p, size)}><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1" /></svg>;

/* Bandeira do Brasil (ícone do app, igual ao avatar do bot no Telegram). */
export const Bandeira = ({ size = 26 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
    <defs><clipPath id="bd-e"><circle cx="16" cy="16" r="5.6" /></clipPath></defs>
    <circle cx="16" cy="16" r="16" fill="#50b050" /><path d="M1.6 16 16 6.4 30.4 16 16 25.6z" fill="#fdea3d" /><circle cx="16" cy="16" r="5.6" fill="#3f51b5" />
    <path clipPath="url(#bd-e)" d="M9.8 13.4C14 12.5 18.4 13.2 22.4 15.9L22.1 17.9C18.4 15.4 14.2 14.6 9.6 15.2Z" fill="#fff" />
  </svg>
);
