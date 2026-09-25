"""Modelo canônico de um edital (pydantic).

Este é o formato que vai para data/editais.json e para o site. O banco sqlite
(pipeline/db.py) guarda este mesmo objeto serializado, com algumas colunas
indexadas para consulta.
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from pipeline.enums import Abrangencia, Mecanismo, Proponente, Status, TipoApoio

SCHEMA_VERSION = 1


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

    def para_json(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
