"""Curadoria manual: data/overrides.yaml sempre vence a coleta.

Formato (por id do edital):

    ambev-brasilidades-2026-3f9a1c:
      oculto: false
      destaque: true
      tags: [bahia, captacao]
      nota: "Texto interno da curadoria"
      campos:
        data_limite: 2026-10-15
        orgao: Ambev

Os campos sobrescritos guardam o valor coletado em `valores_coletados`; se o
override for apagado, o valor coletado volta no próximo processamento.
"""

from pathlib import Path
from typing import Any

from pipeline.config import OVERRIDES_YAML, ler_yaml
from pipeline.models import Curadoria, Edital

_PROTEGIDOS = {"id", "curadoria", "valores_coletados", "historico", "aliases", "captured_at"}


def carregar(caminho: Path = OVERRIDES_YAML) -> dict[str, dict[str, Any]]:
    dados = ler_yaml(caminho) or {}
    if not isinstance(dados, dict):
        raise ValueError(f"{caminho}: esperado um mapa id -> override")
    return {str(k): (v or {}) for k, v in dados.items()}


def aplicar(e: Edital, ov: dict[str, Any] | None) -> Edital:
    novo = e.model_copy(deep=True)
    ov = ov or {}
    campos: dict[str, Any] = dict(ov.get("campos") or {})
    invalidos = set(campos) & _PROTEGIDOS
    if invalidos:
        raise ValueError(f"{e.id}: override não pode alterar {sorted(invalidos)}")

    # 1. Restaura o que deixou de ser sobrescrito.
    for campo in list(novo.valores_coletados):
        if campo not in campos:
            setattr(novo, campo, novo.valores_coletados.pop(campo))

    # 2. Aplica os campos atuais do override.
    for campo, valor in campos.items():
        if campo not in Edital.model_fields:
            raise ValueError(f"{e.id}: campo inexistente no override: {campo}")
        if campo not in novo.valores_coletados:
            novo.valores_coletados[campo] = novo.model_dump(mode="json")[campo]
        setattr(novo, campo, valor)

    novo.curadoria = Curadoria(
        oculto=bool(ov.get("oculto", False)),
        destaque=bool(ov.get("destaque", False)),
        tags=[str(t) for t in ov.get("tags") or []],
        nota=ov.get("nota"),
    )
    return novo


def aplicar_todos(editais: list[Edital], ovs: dict[str, dict[str, Any]]) -> list[Edital]:
    por_alias = {a: e.id for e in editais for a in e.aliases}
    resolvidos: dict[str, dict[str, Any]] = {}
    for chave, ov in ovs.items():
        resolvidos[por_alias.get(chave, chave)] = ov
    return [aplicar(e, resolvidos.get(e.id)) for e in editais]
