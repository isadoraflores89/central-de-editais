"""Aplicação das regras de config/mapeamentos.yaml.

Todas as funções recebem texto cru (com acento) e devolvem valores do
vocabulário controlado. Se não houver evidência no texto, devolvem vazio/None.
"""

import re
from collections.abc import Iterable
from typing import Any

from pipeline.config import mapeamentos
from pipeline.enums import UFS, Abrangencia, Mecanismo, Proponente, TipoApoio
from pipeline.textnorm import normalizar

_ESTADOS_NORM = {normalizar(nome): sigla for sigla, nome in UFS.items()}
# Nomes mais longos primeiro, para "mato grosso do sul" vencer "mato grosso".
_ESTADOS_ORDEM = sorted(_ESTADOS_NORM, key=len, reverse=True)
_SIGLA = re.compile(r"\b(" + "|".join(UFS) + r")\b")
_CIDADE_UF = re.compile(r"([A-ZÀ-Ý][\wÀ-ÿ'. ]*?)\s*/\s*(" + "|".join(UFS) + r")\b")


def _juntar(*partes: str | None) -> str:
    return normalizar(" \n ".join(p for p in partes if p))


def _todas(regras: Iterable[dict[str, Any]], texto_norm: str) -> list[str]:
    achados: list[str] = []
    for r in regras:
        if re.search(r["padrao"], texto_norm) and r["valor"] not in achados:
            achados.append(r["valor"])
    return achados


def tipo_apoio(texto: str | None) -> TipoApoio | None:
    t = normalizar(texto)
    for r in mapeamentos()["tipo_apoio"]:
        if re.search(r["padrao"], t):
            return TipoApoio(r["valor"])
    return None


def mecanismos(*textos: str | None) -> list[Mecanismo]:
    return [Mecanismo(v) for v in _todas(mapeamentos()["mecanismo"], _juntar(*textos))]


def leis_estaduais(*textos: str | None) -> list[str]:
    return _todas(mapeamentos()["leis_estaduais"], _juntar(*textos))


def areas(*textos: str | None) -> list[str]:
    return _todas(mapeamentos()["areas"], _juntar(*textos))


def publico_prioritario(*textos: str | None) -> list[str]:
    return _todas(mapeamentos()["publico_prioritario"], _juntar(*textos))


def proponentes(*textos: str | None) -> list[Proponente]:
    return [Proponente(v) for v in _todas(mapeamentos()["proponente"], _juntar(*textos))]


def exige_projeto_aprovado(tipo: TipoApoio | None, *textos: str | None) -> bool | None:
    cfg = mapeamentos()["exige_projeto_aprovado"]
    if tipo is not None and tipo.value in cfg["falso_por_tipo"]:
        return False
    if re.search(cfg["verdadeiro"], _juntar(*textos)):
        return True
    if tipo is not None and tipo.value in cfg["verdadeiro_por_tipo"]:
        return True
    return None


def ufs_e_cidades(texto: str | None) -> tuple[list[str], list[str]]:
    """Extrai UFs (siglas e nomes de estado) e cidades no formato "Cidade/UF"."""
    if not texto:
        return [], []
    cidades: list[str] = []
    ufs: set[str] = set()
    leis = [r["padrao"] for r in mapeamentos()["leis_estaduais"]]
    for m in _CIDADE_UF.finditer(texto):
        candidata = m.group(1).strip()
        if any(re.search(p, normalizar(f"{candidata}/{m.group(2)}")) for p in leis):
            continue  # "Fazcultura/BA" é lei, não cidade
        cidades.append(candidata)
        ufs.add(m.group(2))
    ufs.update(_SIGLA.findall(texto))
    t = normalizar(texto)
    for nome in _ESTADOS_ORDEM:
        if re.search(rf"\b{re.escape(nome)}\b", t):
            ufs.add(_ESTADOS_NORM[nome])
            t = t.replace(nome, " ")
    return sorted(ufs), cidades


def abrangencia(texto: str | None) -> tuple[Abrangencia | None, list[str], list[str]]:
    """Devolve (abrangência, ufs, cidades) a partir da coluna "Abrangência"."""
    cfg = mapeamentos()["abrangencia"]
    t = normalizar(texto)
    if not t:
        return None, [], []
    if re.search(cfg["nacional"], t):
        return Abrangencia.nacional, [], []
    if re.search(cfg["internacional"], t):
        return Abrangencia.internacional, [], []
    ufs, cidades = ufs_e_cidades(texto)
    if cidades or re.search(r"\bmunicipio d[eo] ", t):
        return Abrangencia.municipal, ufs, cidades
    if len(ufs) == 1:
        return Abrangencia.estadual, ufs, []
    if len(ufs) > 1:
        return Abrangencia.regional, ufs, []
    return None, [], []


# --- valores -----------------------------------------------------------------

_NUM = r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:,\d+)?)"
# "milh..." antes de "mil": senão "10 milhões" vira 10 mil.
_MULT = r"(milh(?:ao|oes)|bilh(?:ao|oes)|mil\b)?"
_POR_PROJETO = re.compile(rf"ate r\$ ?{_NUM} ?{_MULT} por projeto")
_TOTAL = re.compile(
    rf"r\$ ?{_NUM} ?{_MULT} (?:no total|em recursos|ao todo)"
    rf"|(?:investimento|orcamento|valor) total de r\$ ?{_NUM} ?{_MULT}"
)
_FRASES = re.compile(r"(?<=[.;])\s+(?=[A-ZÀ-Ý0-9])")
_MOEDA = re.compile(r"R\$|€|US\$")


def _valor(num: str, mult: str | None) -> float:
    base = float(num.replace(".", "").replace(",", "."))
    fator = {"mil": 1e3}.get(mult or "", 1.0)
    if mult and mult.startswith("milh"):
        fator = 1e6
    if mult and mult.startswith("bilh"):
        fator = 1e9
    return base * fator


def valores(texto: str | None) -> dict[str, Any]:
    """Só extrai o que está escrito de forma inequívoca ("até R$ X por projeto",
    "R$ X no total"). Valores em moeda estrangeira ficam só em valor_texto."""
    out: dict[str, Any] = {
        "valor_por_projeto_max": None,
        "valor_total": None,
        "valor_texto": None,
    }
    if not texto:
        return out
    t = normalizar(texto)
    if m := _POR_PROJETO.search(t):
        out["valor_por_projeto_max"] = _valor(m.group(1), m.group(2))
    if m := _TOTAL.search(t):
        num, mult = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        out["valor_total"] = _valor(num, mult)
    trechos = [f.strip() for f in _FRASES.split(texto) if _MOEDA.search(f)]
    if trechos:
        out["valor_texto"] = "; ".join(trechos)
    return out


# --- links -------------------------------------------------------------------

_URL = re.compile(r"https?://[^\s)\]]+")


def link_edital_das_observacoes(obs: str | None) -> str | None:
    """Primeiro link de Observações precedido por um rótulo oficial
    ("Edital em PDF:", "Página MinC:"...)."""
    if not obs:
        return None
    rotulos = mapeamentos()["rotulos_link_edital"]
    for m in _URL.finditer(obs):
        antes = normalizar(obs[max(0, m.start() - 40) : m.start()])
        if any(r in antes for r in rotulos):
            return m.group(0).rstrip(".,;")
    return None


def dominio_nao_oficial(url: str | None) -> bool:
    if not url:
        return False
    return any(d in url for d in mapeamentos()["dominios_nao_oficiais"])
