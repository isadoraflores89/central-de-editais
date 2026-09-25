"""Prioridade 0–100, com pesos em config/priority.yaml (ver docs/METODOLOGIA.md)."""

from datetime import date
from typing import Any

from pipeline.config import priority_config
from pipeline.enums import Abrangencia, Mecanismo, Status
from pipeline.models import Edital
from pipeline.status import dias_restantes


def calcular_prioridade(e: Edital, hoje: date, cfg: dict[str, Any] | None = None) -> int:
    c = cfg or priority_config()
    if e.status == Status.encerrado:
        return 0

    pontos = 0
    if e.abrangencia == Abrangencia.nacional:
        pontos += int(c["abrangencia_nacional"])

    mp = c["mecanismo_prioritario"]
    prioritarios = {Mecanismo(m) for m in mp["mecanismos"]}
    icms_ok = Mecanismo.icms_estadual in e.mecanismo and _icms_em(e, set(mp["icms_ufs"]))
    if prioritarios.intersection(e.mecanismo) or icms_ok:
        pontos += int(mp["pontos"])

    va = c["valor_alto"]
    maior_valor = e.valor_por_projeto_max or e.valor_por_projeto_min
    if maior_valor is not None and maior_valor >= float(va["minimo_por_projeto"]):
        pontos += int(va["pontos"])

    pz = c["prazo"]
    dias = dias_restantes(e, hoje)
    if dias is not None and 7 <= dias <= 60:
        pontos += int(pz["entre_7_e_60_dias"])
    elif dias is not None and 0 <= dias <= 6:
        pontos += int(pz["entre_1_e_6_dias"])
    elif dias is None and e.fluxo_continuo:
        pontos += int(pz["fluxo_continuo"])

    if e.exige_projeto_aprovado is False:
        pontos += int(c["nao_exige_projeto_aprovado"])

    up = c["uf_prioritaria"]
    if set(up["ufs"]).intersection(e.ufs):
        pontos += int(up["pontos"])

    if e.curadoria.destaque:
        pontos += int(c["destaque_manual"])

    return max(0, min(int(c["teto"]), pontos))


def _icms_em(e: Edital, ufs: set[str]) -> bool:
    if ufs.intersection(e.ufs):
        return True
    siglas = {lei.rsplit("/", 1)[-1].upper() for lei in e.leis_estaduais if "/" in lei}
    return bool(ufs.intersection(siglas))
