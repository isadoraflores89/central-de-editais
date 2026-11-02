"""Modelo canônico de um edital (pydantic).

Este é o formato que vai para data/editais.json e para o site. O banco sqlite
(pipeline/db.py) guarda este mesmo objeto serializado, com algumas colunas
indexadas para consulta.
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from pipeline.enums import (
    Abrangencia,
    Cobre,
    FormatoAcademico,
    FormatoOpenCall,
    Mecanismo,
    Modalidade,
    Proponente,
    Status,
    TipoApoio,
    Vertical,
)

# 2 = Fase 5: campos de vertical/open call/acadêmico (todos com padrão; v1 carrega sem conversão).
SCHEMA_VERSION = 2


class Curadoria(BaseModel):
    """Decisões manuais, sempre lidas de data/overrides.yaml (nunca da coleta)."""

    oculto: bool = False
    destaque: bool = False
    tags: list[str] = Field(default_factory=list)
    nota: str | None = None


class FonteSecundaria(BaseModel):
    fonte: str
    url: str | None = None
    captured_at: datetime | None = None


class MudancaHistorico(BaseModel):
    """Uma mudança observada entre duas coletas (ou aplicada pela curadoria)."""

    em: datetime
    campo: str
    antes: Any = None
    depois: Any = None
    motivo: str | None = None


class Edital(BaseModel):
    model_config = ConfigDict(use_enum_values=False, validate_assignment=True)

    id: str
    titulo: str
    orgao: str | None = None

    # --- Fase 5: comuns às verticais ---
    vertical: Vertical = Vertical.fomento
    idiomas: list[str] = Field(default_factory=list)  # pt, es, en, fr...
    pais_organizador: str | None = None  # ISO-3166 alfa-2
    elegivel_brasileiros: bool | None = None  # só quando o texto diz

    # --- Fase 5: open call ---
    formato: FormatoOpenCall | None = None
    taxa_inscricao: float | None = None  # 0 = gratuita; None = não informado
    taxa_moeda: str | None = None
    cobre: list[Cobre] = Field(default_factory=list)
    moeda: str | None = None
    valor_original: float | None = None
    valor_brl_estimado: float | None = None
    cotacao_data: date | None = None
    modalidade: Modalidade | None = None

    # --- Fase 5: acadêmico ---
    formato_academico: FormatoAcademico | None = None
    periodico: str | None = None
    evento: str | None = None
    issn: str | None = None
    qualis: str | None = None  # só de fonte explícita (periodicos.yaml); nunca inferido
    indexadores: list[str] = Field(default_factory=list)
    apc: float | None = None  # taxa de publicação; 0 = sem cobrança
    apc_moeda: str | None = None
    data_resumo: date | None = None
    data_texto_completo: date | None = None
    data_evento: date | None = None
    tema_dossie: str | None = None
    organizadores: list[str] = Field(default_factory=list)
    link_normas: str | None = None

    tipo_apoio: TipoApoio | None = None
    mecanismo: list[Mecanismo] = Field(default_factory=list)
    leis_estaduais: list[str] = Field(default_factory=list)
    exige_projeto_aprovado: bool | None = None

    abrangencia: Abrangencia | None = None
    ufs: list[str] = Field(default_factory=list)
    cidades: list[str] = Field(default_factory=list)
    areas: list[str] = Field(default_factory=list)
    publico_prioritario: list[str] = Field(default_factory=list)
    proponente: list[Proponente] = Field(default_factory=list)

    valor_por_projeto_min: float | None = None
    valor_por_projeto_max: float | None = None
    valor_total: float | None = None
    valor_texto: str | None = None  # como está na fonte; inclui moedas estrangeiras

    prazo_texto: str | None = None
    data_limite: date | None = None
    fluxo_continuo: bool = False
    data_abertura: date | None = None
    status: Status = Status.indefinido

    resumo: str | None = None
    link_inscricao: str | None = None
    link_edital: str | None = None
    observacoes: str | None = None
    # Imagem oficial da página do edital (og:image / twitter:image), buscada pelo robô.
    imagem: str | None = None
    imagem_verificada_em: datetime | None = None

    fonte: str
    source_url: HttpUrl
    fontes_secundarias: list[FonteSecundaria] = Field(default_factory=list)
    captured_at: datetime
    updated_at: datetime

    prioridade: int = 0
    curadoria: Curadoria = Field(default_factory=Curadoria)
    # Marcadores do sistema (ex.: carga_inicial, aba:parecerista, link_generico).
    marcadores: list[str] = Field(default_factory=list)
    # Valor coletado de cada campo que a curadoria sobrescreveu, para poder
    # restaurá-lo se o override for removido.
    valores_coletados: dict[str, Any] = Field(default_factory=dict)
    historico: list[MudancaHistorico] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    revisao_pendente: bool = False

    @field_validator("ufs")
    @classmethod
    def _ufs_maiusculas(cls, v: list[str]) -> list[str]:
        return sorted({u.strip().upper() for u in v if u.strip()})

    @field_validator("titulo")
    @classmethod
    def _titulo_nao_vazio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("titulo vazio")
        return v

    @field_validator("pais_organizador")
    @classmethod
    def _pais_iso(cls, v: str | None) -> str | None:
        v = (v or "").strip().upper()
        return v or None

    @property
    def com_taxa(self) -> bool:
        return bool((self.taxa_inscricao or 0) > 0 or (self.apc or 0) > 0)

    @property
    def tem_data_dupla(self) -> bool:
        return self.data_resumo is not None and self.data_texto_completo is not None

    def para_json(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


# O adendo da Fase 5 chama o registro de "Oportunidade" (fomento, open call ou
# chamada acadêmica). O nome da classe continua Edital por compatibilidade.
Oportunidade = Edital
