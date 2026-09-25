from datetime import date, timedelta

from pipeline.enums import Abrangencia, Mecanismo, Status
from pipeline.models import Curadoria
from pipeline.priority import calcular_prioridade
from pipeline.status import calcular_status
from tests.conftest import HOJE, fazer_edital


def test_prazo_vencido_encerra() -> None:
    assert calcular_status(fazer_edital(data_limite=HOJE - timedelta(days=1)), HOJE) == (
        Status.encerrado
    )


def test_no_dia_do_prazo_continua_aberto() -> None:
    assert calcular_status(fazer_edital(data_limite=HOJE), HOJE) == Status.aberto


def test_fluxo_continuo_aberto_e_sem_data_indefinido() -> None:
    assert calcular_status(fazer_edital(fluxo_continuo=True), HOJE) == Status.aberto
    assert calcular_status(fazer_edital(), HOJE) == Status.indefinido


def test_em_breve_e_prorrogado() -> None:
    futuro = fazer_edital(data_abertura=HOJE + timedelta(days=3), data_limite=date(2026, 12, 1))
    assert calcular_status(futuro, HOJE) == Status.em_breve
    prorrog = fazer_edital(data_limite=date(2026, 12, 31), prazo_texto="31/12/2026 (prorrogado)")
    assert calcular_status(prorrog, HOJE) == Status.prorrogado


def _com_status(**kw: object) -> int:
    e = fazer_edital(**kw)
    e.status = calcular_status(e, HOJE)
    return calcular_prioridade(e, HOJE)


def test_prioridade_soma_criterios() -> None:
    p = _com_status(
        abrangencia=Abrangencia.nacional,         # 25
        mecanismo=[Mecanismo.rouanet],            # 20
        valor_por_projeto_max=200_000,            # 15
        data_limite=HOJE + timedelta(days=20),    # 20
        exige_projeto_aprovado=False,             # 10
    )
    assert p == 90


def test_prioridade_tem_teto_100() -> None:
    p = _com_status(
        abrangencia=Abrangencia.nacional, mecanismo=[Mecanismo.rouanet], ufs=["BA"],
        valor_por_projeto_max=200_000, data_limite=HOJE + timedelta(days=20),
        exige_projeto_aprovado=False, curadoria=Curadoria(destaque=True),
    )
    assert p == 100


def test_prazo_curto_e_fluxo() -> None:
    assert _com_status(data_limite=HOJE + timedelta(days=3)) == 10
    assert _com_status(data_limite=HOJE) == 10
    assert _com_status(fluxo_continuo=True) == 5


def test_icms_so_conta_na_bahia_ou_parana() -> None:
    assert _com_status(mecanismo=[Mecanismo.icms_estadual], leis_estaduais=["Fazcultura/BA"]) == 20
    assert _com_status(mecanismo=[Mecanismo.icms_estadual], leis_estaduais=["ProAC/SP"]) == 0


def test_campo_vazio_nao_pontua_e_encerrado_zera() -> None:
    assert _com_status(exige_projeto_aprovado=None) == 0
    assert _com_status(abrangencia=Abrangencia.nacional, data_limite=HOJE - timedelta(1)) == 0
