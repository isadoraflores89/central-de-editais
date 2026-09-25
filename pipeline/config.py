"""Caminhos do projeto e leitura dos arquivos de configuração."""

import os
from datetime import date
from functools import cache
from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parent.parent
CONFIG = RAIZ / "config"
DATA = RAIZ / "data"
REPORTS = RAIZ / "reports"

EDITAIS_JSON = DATA / "editais.json"
EDITAIS_DB = DATA / "editais.db"
HISTORICO_JSONL = DATA / "historico.jsonl"
OVERRIDES_YAML = DATA / "overrides.yaml"
SEED_XLSX = DATA / "seed" / "Editais_Culturais_Nacionais_set2026_v2.xlsx"
SEED_AJUSTES = DATA / "seed" / "ajustes_seed.yaml"


def ler_yaml(caminho: Path) -> Any:
    if not caminho.exists():
        return None
    with caminho.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


@cache
def priority_config() -> dict[str, Any]:
    dados = ler_yaml(CONFIG / "priority.yaml")
    if not isinstance(dados, dict):
        raise RuntimeError("config/priority.yaml ausente ou inválido")
    return dados


@cache
def mapeamentos() -> dict[str, Any]:
    dados = ler_yaml(CONFIG / "mapeamentos.yaml")
    if not isinstance(dados, dict):
        raise RuntimeError("config/mapeamentos.yaml ausente ou inválido")
    return dados


def hoje() -> date:
    """Data de referência. CENTRAL_HOJE=AAAA-MM-DD fixa a data (testes, reprocessamento)."""
    fixo = os.environ.get("CENTRAL_HOJE")
    return date.fromisoformat(fixo) if fixo else date.today()
