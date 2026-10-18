/* Formato de data.json: o contrato é coletor/modelos.py (validado antes de cada gravação). */

export type Nivel = "Sem categoria" | "Tradicional" | "Superior" | "Gourmet/especial";

export interface Item {
  n: number | null;
  tipo: string;
  cat: string;
  emb: string;
  kgu: number | null;
  kg_src: string;
  qtd: number | null;
  un: string;
  vu: number | null;
  vt: number | null;
  sig: boolean;
  kgt: number | null;
  rkg: number | null;
  conferir: boolean;
  me: string;
  sit: string;
  tags: string[];
  espec: string;
  usa_trecho: boolean;
  ed_trecho?: string;
  nivel?: Nivel | null;
  qg?: number | null;
}

export interface Compra {
  chave: string;
  fim: string | null;
  abre: string | null;
  publicado: string | null;
  first_seen: string;
  nova: boolean;
  uf: string;
  mun: string;
  dist: number | null;
  dist_min?: number | null;
  orgao: string;
  unidade: string;
  esfera: string;
  mod: string;
  num: string;
  plat: string;
  plat_src: string;
  plat_f: string;
  publicado_via: string;
  uasg: string;
  srp: string;
  objeto: string;
  link_pncp: string;
  link_plat: string;
  ed_tags: string[];
  ed_pz: string;
  edital_lido: boolean;
  trecho_edital: string;
  tipos: string[];
  cats: string[];
  cat_do_edital: boolean;
  edital_status?: string;
  edital_docs?: string[];
  edital_lido_em?: string;
  edital_ver?: string;
  marcas?: string[];
  embs: string;
  emb_f: string[];
  vcafe: number | null;
  vcesta: number | null;
  kg: number | null;
  kg_parcial: boolean;
  rkg: number | null;
  sig: string;
  me: string;
  me_f: string[];
  tags: string[];
  niveis?: string[];
  resumo: string;
  dup: string;
  dup_of: string | null;
  dup_group: string[];
  itens: Item[];
}

export interface ChecklistItem {
  etapa: string;
  item: string;
  dica: string;
  freq?: number | null;
}

export interface Coleta {
  modalidades?: number[];
  listadas?: number;
  candidatas?: number;
  itens_baixados?: number;
  falhas?: number;
  chamadas_pncp?: number;
  novas_tentativas?: number;
  segundos?: number;
}

export interface Custos {
  atualizado_em?: string;
  perda_torra: number;
  torra_rs_kg_verde: number;
  embalagem_rs_kg: number;
  frete: {
    fixo_por_envio: number;
    rs_kg: number;
    rs_kg_100km: number;
    ad_valorem: number;
    lotacao_fixo: number;
    lotacao_rs_km: number;
    folga: number;
    entregas: number;
    entregas_registro_precos: number;
  };
  pct_preco: { das: number; financeiro: number; perdas: number };
  por_licitacao: { plataforma: number; laudo: number; amostra_kg: number };
  fontes?: Record<string, string>;
}

export interface MercadoNivel {
  saca60_min: number;
  saca60_max: number;
  kg_min: number;
  kg_max: number;
  kg_medio: number;
  receita_min?: Record<string, number>;
  receita_max?: Record<string, number>;
  regra?: string;
}

export interface HistoricoMercado {
  data: string; // data da cotação (Carvalhaes)
  arabica?: number | null;
  robusta?: number | null;
  niveis: Record<string, number>; // R$/saca médio de cada nível
}

export interface Mercado {
  atualizado_em?: string;
  perda_torra?: number;
  cepea?: { arabica?: { data: string; saca60: number }; robusta?: { data: string; saca60: number } };
  carvalhaes?: { data: string; saca60: Record<string, [number, number]> };
  niveis?: Record<string, MercadoNivel>;
  historico?: HistoricoMercado[];
  fontes?: Record<string, string>;
}

export interface MarcaLinha {
  linha: string;
  cat: string;
  min: number;
  max: number;
}

export interface MarcasRef {
  pesquisa_em?: string;
  marcas?: Record<string, { linhas?: MarcaLinha[]; basica?: MarcaLinha | null }>;
}

export interface Painel {
  gerado_em: string;
  run_date: string;
  seed_date: string;
  novas_desde: string;
  origem: { nome?: string; lat?: number; lon?: number };
  status_opcoes: string[];
  fonte: string;
  editais_lidos: number;
  compras: Compra[];
  checklist: ChecklistItem[];
  coffee_break?: unknown[];
  coleta?: Coleta | null;
  custos?: Custos;
  mercado?: Mercado;
  marcas_ref?: MarcasRef | null;
}

/* Anotações do dono por licitação (localStorage monitorLicitacoes.meusDados.v1). Uma entrada só com {upd}
   é "marca de removido": impede que outro aparelho traga de volta o que foi apagado aqui. */
export interface Ref {
  mun?: string;
  uf?: string;
  orgao?: string;
  fim?: string | null;
  vcafe?: number | null;
  link?: string;
}

export interface Anotacao {
  fav?: boolean;
  status?: string;
  preco?: number;
  resp?: string;
  notas?: string;
  upd?: string;
  ref?: Ref;
}

export type MeusDados = Record<string, Anotacao>;
export type Pisos = Record<string, number>;
export type MeusCustos = Record<string, number>;
export type Checklist = Record<string, 1>;

export type Tab = "hoje" | "oportunidades" | "propostas" | "mercado" | "guia" | "ajustes";

export interface Filtros {
  q: string;
  niveis: string[];
  precos: string[];
  ufs: string[];
  tipos: string[];
  cats: string[];
  embs: string[];
  me: string[];
  mods: string[];
  plats: string[];
  marcas: string[];
  dist: number;
  valor: string;
  hideDup: boolean;
  fav: boolean;
  novas: boolean;
  urg: boolean;
  rkg: boolean;
  viavel: boolean;
  status: string;
}

export type Ordem = "prazo" | "dist" | "valor" | "folga" | "rkg_desc" | "margem" | "rkg_asc" | "kg" | "pub" | "lucro";

export interface UIState {
  sort: Ordem;
  tab: Tab;
  theme: "" | "dark" | "light";
  agendaAll: boolean;
  densidade?: "normal" | "compacta";
  F?: Partial<Filtros>;
  split?: number; // largura da lista no painel dividido (%)
}
