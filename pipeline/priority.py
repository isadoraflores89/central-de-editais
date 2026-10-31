"""Prioridade 0–100, com pesos em config/priority.yaml (ver docs/METODOLOGIA.md)."""

from datetime import date
from typing import Any

from pipeline.config import priority_config
from pipeline.enums import Abrangencia, Cobre, FormatoAcademico, Mecanismo, Status, Vertical
from pipeline.models import Edital
from pipeline.status import dias_restantes


def calcular_prioridade(e: Edital, hoje: date, cfg: dict[str, Any] | None = None) -> int:
    c = cfg or priority_config()
    if e.status == Status.encerrado:
        return 0

    pontos = 0
    verticais = c.get("verticais") or {}
    if e.vertical == Vertical.open_call and "open_call" in verticais:
        pontos += _pontos_open_call(e, verticais["open_call"])
    elif e.vertical == Vertical.academico and "academico" in verticais:
        pontos += _pontos_academico(e, verticais["academico"])
    else:
        pontos += _pontos_fomento(e, c)

    pz = c["prazo"]
    dias = dias_restantes(e, hoje)
    if dias is not None and 7 <= dias <= 60:
        pontos += int(pz["entre_7_e_60_dias"])
    elif dias is not None and 0 <= dias <= 6:
        pontos += int(pz["entre_1_e_6_dias"])
    elif dias is None and e.fluxo_continuo:
        pontos += int(pz["fluxo_continuo"])

    if e.curadoria.destaque:
        pontos += int(c["destaque_manual"])

    return max(0, min(int(c["teto"]), pontos))


def _pontos_open_call(e: Edital, v: dict[str, Any]) -> int:
    pontos = 0
    if e.taxa_inscricao == 0:
        pontos += int(v["gratuita"])
    if e.elegivel_brasileiros is True:
        pontos += int(v["elegivel_brasileiros"])
    if Cobre.passagem in e.cobre or Cobre.hospedagem in e.cobre:
        pontos += int(v["cobre_passagem_ou_hospedagem"])
    if Cobre.honorario in e.cobre:
        pontos += int(v["cobre_honorario"])
    va = v["valor_brl_alto"]
    if e.valor_brl_estimado is not None and e.valor_brl_estimado >= float(va["minimo"]):
        pontos += int(va["pontos"])
    if "alerta_taxa" in e.marcadores:
        pontos += int(v["com_taxa_sem_contrapartida"])
    return pontos


def _pontos_academico(e: Edital, v: dict[str, Any]) -> int:
    pontos = 0
    if e.apc == 0:
        pontos += int(v["sem_apc"])
    q = (e.qualis or "").upper()
    if q.startswith("A"):
        pontos += int(v["qualis_a"])
    elif q.startswith("B"):
        pontos += int(v["qualis_b"])
    if "pt" in e.idiomas:
        pontos += int(v["idioma_portugues"])
    ap = v["area_prioritaria"]
    if set(ap["areas"]).intersection(e.areas):
        pontos += int(ap["pontos"])
    if e.formato_academico == FormatoAcademico.congresso and e.data_evento is not None:
        pontos += int(v["congresso_com_data"])
    return pontos


def _pontos_fomento(e: Edital, c: dict[str, Any]) -> int:
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

    if e.exige_projeto_aprovado is False:
        pontos += int(c["nao_exige_projeto_aprovado"])

    up = c["uf_prioritaria"]
    if set(up["ufs"]).intersection(e.ufs):
        pontos += int(up["pontos"])
    return pontos


def _icms_em(e: Edital, ufs: set[str]) -> bool:
    if ufs.intersection(e.ufs):
        return True
    siglas = {lei.rsplit("/", 1)[-1].upper() for lei in e.leis_estaduais if "/" in lei}
    return bool(ufs.intersection(siglas))
