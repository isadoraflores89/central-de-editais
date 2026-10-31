// Espelho do modelo pipeline/models.py (formato de data/editais.json).

export type Status = "aberto" | "em_breve" | "encerrado" | "prorrogado" | "indefinido";
export type Vertical = "fomento" | "open_call" | "academico" | "noticia";

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
  // Fase 5 (opcionais até o site ter as abas; registros v1 não os têm)
  // comuns
  vertical?: Vertical;
  idiomas?: string[];
  pais_organizador?: string | null;
  elegivel_brasileiros?: boolean | null;
  // Fase 5: open call
  formato?: string | null;
  taxa_inscricao?: number | null;
  taxa_moeda?: string | null;
  cobre?: string[];
  moeda?: string | null;
  valor_original?: number | null;
  valor_brl_estimado?: number | null;
  cotacao_data?: string | null;
  modalidade?: string | null;
  // Fase 5: acadêmico
  formato_academico?: string | null;
  periodico?: string | null;
  evento?: string | null;
  issn?: string | null;
  qualis?: string | null;
  indexadores?: string[];
  apc?: number | null;
  apc_moeda?: string | null;
  data_resumo?: string | null;
  data_texto_completo?: string | null;
  data_evento?: string | null;
  tema_dossie?: string | null;
  organizadores?: string[];
  link_normas?: string | null;
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
  cadastro_endpoint?: string;
  apoio?: { pix_chave?: string; pix_nome?: string; pix_cidade?: string; apoiase_url?: string };
}
