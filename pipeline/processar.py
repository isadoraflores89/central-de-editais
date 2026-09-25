"""Etapa comum a todo run: curadoria -> status -> prioridade -> histórico."""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from pipeline import overrides
from pipeline.enums import Status
from pipeline.models import Edital, MudancaHistorico
from pipeline.priority import calcular_prioridade
from pipeline.status import calcular_status

# Campos cuja mudança entra no histórico público do edital.
CAMPOS_RASTREADOS = ("data_limite", "prazo_texto", "link_inscricao", "valor_por_projeto_max")


def registrar_mudancas(
    antigo: Edital | None, novo: Edital, agora: datetime
) -> list[MudancaHistorico]:
    if antigo is None:
        return []
    velho = antigo.model_dump(mode="json")
    atual = novo.model_dump(mode="json")
    mudancas = []
    for campo in CAMPOS_RASTREADOS:
        if velho[campo] != atual[campo]:
            motivo = None
            if (
                campo == "data_limite"
                and velho[campo] is not None
                and atual[campo] is not None
                and atual[campo] > velho[campo]
            ):
                motivo = "prorrogado"
            mudancas.append(MudancaHistorico(
                em=agora, campo=campo, antes=velho[campo], depois=atual[campo], motivo=motivo,
            ))
    return mudancas


def processar(
    editais: list[Edital],
    anteriores: dict[str, Edital],
    ovs: dict[str, dict[str, Any]],
    hoje: date,
    agora: datetime,
) -> tuple[list[Edital], list[dict[str, Any]]]:
    """Devolve os editais processados e as linhas novas do historico.jsonl."""
    saida: list[Edital] = []
    linhas_hist: list[dict[str, Any]] = []
    for e in overrides.aplicar_todos(editais, ovs):
        antigo = anteriores.get(e.id)
        mudancas = registrar_mudancas(antigo, e, agora)
        e.historico = [*e.historico, *mudancas]
        if "status" not in e.valores_coletados:  # status só não é calculado se a curadoria fixou
            e.status = calcular_status(e, hoje)
        if antigo is not None and antigo.status != e.status:
            m = MudancaHistorico(
                em=agora, campo="status", antes=antigo.status.value, depois=e.status.value,
                motivo="prazo vencido" if e.status == Status.encerrado else None,
            )
            e.historico.append(m)
            mudancas.append(m)
        e.prioridade = calcular_prioridade(e, hoje)
        if mudancas:
            e.updated_at = agora
        linhas_hist += [{"id": e.id, **m.model_dump(mode="json")} for m in mudancas]
        saida.append(e)
    return saida, linhas_hist


def anexar_historico(linhas: list[dict[str, Any]], caminho: Path) -> None:
    if not linhas:
        return
    with caminho.open("a", encoding="utf-8") as f:
        for linha in linhas:
            f.write(json.dumps(linha, ensure_ascii=False) + "\n")
