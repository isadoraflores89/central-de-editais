"""Regras de status (aberto, encerrado, prorrogado...)."""

from datetime import date

from pipeline.enums import Status
from pipeline.models import Edital
from pipeline.textnorm import normalizar


def calcular_status(e: Edital, hoje: date) -> Status:
    if e.data_limite is not None and e.data_limite < hoje:
        return Status.encerrado
    if e.data_abertura is not None and e.data_abertura > hoje:
        return Status.em_breve
    aberto = e.data_limite is not None or e.fluxo_continuo
    if not aberto:
        return Status.indefinido
    if foi_prorrogado(e):
        return Status.prorrogado
    return Status.aberto


def foi_prorrogado(e: Edital) -> bool:
    if "prorrogad" in normalizar(e.prazo_texto):
        return True
    return any(
        h.campo == "data_limite" and h.motivo == "prorrogado" for h in e.historico
    )


def dias_restantes(e: Edital, hoje: date) -> int | None:
    if e.data_limite is None:
        return None
    return (e.data_limite - hoje).days
