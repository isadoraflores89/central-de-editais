"""Banco sqlite local (data/editais.db), recriado a partir de data/editais.json.

Ver decisão D1 do PLANO: o JSON é a fonte da verdade versionada; o banco é um
artefato de trabalho para consultas e para quem quiser baixar o .db.
"""

import json
from datetime import date
from pathlib import Path

from sqlalchemy import Column, Engine
from sqlmodel import JSON, Field, Session, SQLModel, create_engine, delete, select

from pipeline.config import EDITAIS_DB
from pipeline.models import Edital


class EditalRow(SQLModel, table=True):
    __tablename__ = "editais"

    id: str = Field(primary_key=True)
    titulo: str
    orgao: str | None = None
    status: str = Field(index=True)
    data_limite: date | None = Field(default=None, index=True)
    prioridade: int = Field(default=0, index=True)
    fonte: str
    dados: dict[str, object] = Field(sa_column=Column(JSON, nullable=False))


def _engine(caminho: Path) -> Engine:
    return create_engine(f"sqlite:///{caminho}")


def salvar(editais: list[Edital], caminho: Path = EDITAIS_DB) -> None:
    engine = _engine(caminho)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        s.exec(delete(EditalRow))
        for e in editais:
            s.add(EditalRow(
                id=e.id, titulo=e.titulo, orgao=e.orgao, status=e.status.value,
                data_limite=e.data_limite, prioridade=e.prioridade, fonte=e.fonte,
                dados=json.loads(e.model_dump_json()),
            ))
        s.commit()


def carregar(caminho: Path = EDITAIS_DB) -> list[Edital]:
    engine = _engine(caminho)
    with Session(engine) as s:
        return [Edital.model_validate(r.dados) for r in s.exec(select(EditalRow))]
