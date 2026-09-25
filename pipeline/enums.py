"""Vocabulários controlados do modelo Edital.

Os valores são slugs em pt-BR sem acento: aparecem na URL dos filtros do site
e nos arquivos exportados, então não mudam depois de publicados.
"""

from enum import StrEnum


class TipoApoio(StrEnum):
    fomento_direto = "fomento_direto"
    patrocinio_incentivado = "patrocinio_incentivado"
    patrocinio_direto = "patrocinio_direto"
    lei_incentivo_janela = "lei_incentivo_janela"
    premio = "premio"
    credenciamento = "credenciamento"
    cessao_espaco = "cessao_espaco"
    bolsa_mobilidade = "bolsa_mobilidade"
    banco_projetos = "banco_projetos"
    certificacao = "certificacao"


class Mecanismo(StrEnum):
    rouanet = "rouanet"
    lei_esporte = "lei_esporte"
    icms_estadual = "icms_estadual"
    pnab = "pnab"
    fsa = "fsa"
    pronon_pronas = "pronon_pronas"
    fia_idoso = "fia_idoso"
    recursos_proprios = "recursos_proprios"
    outro = "outro"


class Abrangencia(StrEnum):
    internacional = "internacional"
    nacional = "nacional"
    regional = "regional"
    estadual = "estadual"
    municipal = "municipal"


class Status(StrEnum):
    aberto = "aberto"
    em_breve = "em_breve"
    encerrado = "encerrado"
    prorrogado = "prorrogado"
    indefinido = "indefinido"


class Proponente(StrEnum):
    pf = "pf"
    pj = "pj"
    mei = "mei"
    osc = "osc"
    coletivo = "coletivo"
    cooperativa = "cooperativa"
    empresa = "empresa"


# Áreas e público prioritário são vocabulários abertos (a spec diz "enum aberto"):
# ficam como str no modelo, e estas listas servem de referência para o site e os testes.
AREAS_CONHECIDAS: tuple[str, ...] = (
    "musica",
    "artes_cenicas",
    "audiovisual",
    "artes_visuais",
    "literatura",
    "patrimonio",
    "culturas_populares",
    "formacao",
    "economia_criativa",
    "esporte",
    "multi",
)

PUBLICOS_CONHECIDOS: tuple[str, ...] = (
    "periferias",
    "pessoas_negras",
    "mulheres",
    "indigenas",
    "pcd",
    "lgbtqia",
    "juventude",
    "vulnerabilidade_social",
)

UFS: dict[str, str] = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AP": "Amapá",
    "AM": "Amazonas",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais",
    "PA": "Pará",
    "PB": "Paraíba",
    "PR": "Paraná",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul",
    "RO": "Rondônia",
    "RR": "Roraima",
    "SC": "Santa Catarina",
    "SP": "São Paulo",
    "SE": "Sergipe",
    "TO": "Tocantins",
}
