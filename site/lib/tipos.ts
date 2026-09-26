// Espelho do modelo pipeline/models.py (formato de data/editais.json).

export type Status = "aberto" | "em_breve" | "encerrado" | "prorrogado" | "indefinido";

export interface MudancaHistorico {
  em: string;
  campo: string;
  antes: unknown;
  depois: unknown;
  motivo: string | null;
}

export interface Edital {
  id: string;
  titulo: string;
  orgao: string | null;
  tipo_apoio: string | null;
  mecanismo: string[];
  leis_estaduais: string[];
  exige_projeto_aprovado: boolean | null;
  abrangencia: string | null;
  ufs: string[];
  cidades: string[];
  areas: string[];
  publico_prioritario: string[];
  proponente: string[];
  valor_por_projeto_min: number | null;
  valor_por_projeto_max: number | null;
  valor_total: number | null;
  valor_texto: string | null;
  prazo_texto: string | null;
  data_limite: string | null;
  fluxo_continuo: boolean;
  data_abertura: string | null;
  status: Status;
  resumo: string | null;
  link_inscricao: string | null;
  link_edital: string | null;
  observacoes: string | null;
  fonte: string;
  source_url: string;
  fontes_secundarias: { fonte: string; url: string | null; captured_at: string | null }[];
  captured_at: string;
  updated_at: string;
  prioridade: number;
  curadoria: { oculto: boolean; destaque: boolean; tags: string[]; nota: string | null };
  marcadores: string[];
  historico: MudancaHistorico[];
  aliases: string[];
  revisao_pendente: boolean;
}

export interface DocumentoEditais {
  schema: number;
  gerado_em?: string;
  licenca: string;
  atribuicao: string;
  total: number;
  editais: Edital[];
}

export interface Preset {
  id: string;
  rotulo: string;
  descricao: string;
  filtros: string;
}

export interface ConfigSite {
  consultoria?: { titulo: string; texto: string; email: string };
  substack_url?: string;
  apoio?: { pix_chave?: string; pix_nome?: string; pix_cidade?: string; apoiase_url?: string };
}
