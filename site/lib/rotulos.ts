// Rótulos em pt-BR para os valores do vocabulário controlado.

export const TIPOS: Record<string, string> = {
  fomento_direto: "Fomento direto",
  patrocinio_incentivado: "Patrocínio incentivado",
  patrocinio_direto: "Patrocínio direto",
  lei_incentivo_janela: "Lei de incentivo (inscrição de projeto)",
  premio: "Prêmio",
  credenciamento: "Credenciamento",
  cessao_espaco: "Cessão de espaço",
  bolsa_mobilidade: "Bolsa e mobilidade",
  banco_projetos: "Banco de projetos",
  certificacao: "Certificação",
};

export const MECANISMOS: Record<string, string> = {
  rouanet: "Lei Rouanet",
  lei_esporte: "Lei do Esporte",
  icms_estadual: "ICMS estadual",
  pnab: "PNAB (Aldir Blanc)",
  fsa: "FSA (audiovisual)",
  pronon_pronas: "Pronon / Pronas",
  fia_idoso: "FIA / Fundo do Idoso",
  recursos_proprios: "Recursos próprios",
  outro: "Outro",
};

export const ABRANGENCIAS: Record<string, string> = {
  internacional: "Internacional",
  nacional: "Nacional",
  regional: "Regional",
  estadual: "Estadual",
  municipal: "Municipal",
};

export const AREAS: Record<string, string> = {
  musica: "Música",
  artes_cenicas: "Artes cênicas",
  audiovisual: "Audiovisual",
  artes_visuais: "Artes visuais",
  literatura: "Literatura e livro",
  patrimonio: "Patrimônio e memória",
  culturas_populares: "Culturas populares",
  formacao: "Formação",
  economia_criativa: "Economia criativa",
  esporte: "Esporte",
  multi: "Multilinguagem",
};

export const PUBLICOS: Record<string, string> = {
  periferias: "Periferias e favelas",
  pessoas_negras: "Pessoas negras",
  mulheres: "Mulheres",
  indigenas: "Povos indígenas",
  pcd: "Pessoas com deficiência",
  lgbtqia: "LGBTQIA+",
  juventude: "Juventude",
  vulnerabilidade_social: "Vulnerabilidade social",
};

export const PROPONENTES: Record<string, string> = {
  pf: "Pessoa física",
  pj: "Pessoa jurídica",
  mei: "MEI",
  osc: "OSC (sem fins lucrativos)",
  coletivo: "Coletivo",
  cooperativa: "Cooperativa",
  empresa: "Empresa",
};

export const STATUS: Record<string, string> = {
  aberto: "Aberto",
  prorrogado: "Prorrogado",
  em_breve: "Em breve",
  indefinido: "Prazo a confirmar",
  encerrado: "Encerrado",
};

export const UFS: Record<string, string> = {
  AC: "Acre", AL: "Alagoas", AP: "Amapá", AM: "Amazonas", BA: "Bahia", CE: "Ceará",
  DF: "Distrito Federal", ES: "Espírito Santo", GO: "Goiás", MA: "Maranhão",
  MT: "Mato Grosso", MS: "Mato Grosso do Sul", MG: "Minas Gerais", PA: "Pará",
  PB: "Paraíba", PR: "Paraná", PE: "Pernambuco", PI: "Piauí", RJ: "Rio de Janeiro",
  RN: "Rio Grande do Norte", RS: "Rio Grande do Sul", RO: "Rondônia", RR: "Roraima",
  SC: "Santa Catarina", SP: "São Paulo", SE: "Sergipe", TO: "Tocantins",
};

export function rotulo(mapa: Record<string, string>, valor: string): string {
  return mapa[valor] ?? valor.replaceAll("_", " ");
}
