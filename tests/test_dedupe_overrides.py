from datetime import date

import pytest

from pipeline import overrides
from pipeline.dedupe import deduplicar
from pipeline.enums import Mecanismo, Status
from pipeline.processar import processar
from tests.conftest import AGORA, HOJE, fazer_edital


def test_mesma_url_funde_e_une_listas() -> None:
    a = fazer_edital(id="a", link_inscricao="https://prosas.com.br/editais/1-x",
                     mecanismo=[Mecanismo.rouanet])
    b = fazer_edital(id="b", titulo="Outro título", link_inscricao="https://prosas.com.br/editais/1",
                     mecanismo=[Mecanismo.lei_esporte], exige_projeto_aprovado=True)
    res, fusoes = deduplicar([a, b])
    assert len(res) == 1 and fusoes == [("a", "b")]
    assert res[0].mecanismo == [Mecanismo.rouanet, Mecanismo.lei_esporte]
    assert res[0].aliases == ["b"] and res[0].exige_projeto_aprovado is True
    assert res[0].fontes_secundarias[0].fonte == "teste"


def test_url_de_pagina_inicial_exige_mesmo_orgao() -> None:
    a = fazer_edital(id="a", titulo="Rouanet nas Favelas", orgao="MinC + Vale",
                     link_inscricao="https://salic.cultura.gov.br")
    b = fazer_edital(id="b", titulo="Rouanet 2026", orgao="MinC",
                     link_inscricao="https://salic.cultura.gov.br/")
    assert len(deduplicar([a, b])[0]) == 2
    c = fazer_edital(id="c", titulo="Rouanet 2026 (esporte)", orgao="MinC",
                     link_inscricao="https://salic.cultura.gov.br")
    assert len(deduplicar([b, c])[0]) == 1


def test_link_generico_nunca_funde() -> None:
    url = "https://prosas.com.br/editais?status=abertos"
    a = fazer_edital(id="a", titulo="Credenciamento A", link_inscricao=url)
    b = fazer_edital(id="b", titulo="Credenciamento B", link_inscricao=url)
    assert len(deduplicar([a, b])[0]) == 2


def test_override_aplica_e_restaura() -> None:
    e = fazer_edital(orgao="Coletado")
    com = overrides.aplicar(e, {"destaque": True, "tags": ["ba"], "campos": {"orgao": "Manual"}})
    assert com.orgao == "Manual" and com.curadoria.destaque and com.curadoria.tags == ["ba"]
    assert com.valores_coletados == {"orgao": "Coletado"}
    # Aplicar de novo é idempotente; remover o override devolve o valor coletado.
    assert overrides.aplicar(com, {"campos": {"orgao": "Manual"}}).valores_coletados == {
        "orgao": "Coletado"
    }
    sem = overrides.aplicar(com, None)
    assert sem.orgao == "Coletado" and not sem.curadoria.destaque and sem.valores_coletados == {}


def test_override_nao_mexe_em_campos_protegidos() -> None:
    with pytest.raises(ValueError):
        overrides.aplicar(fazer_edital(), {"campos": {"id": "outro"}})
    with pytest.raises(ValueError):
        overrides.aplicar(fazer_edital(), {"campos": {"inexistente": 1}})


def test_override_por_alias() -> None:
    e = fazer_edital(id="novo", aliases=["velho"])
    assert overrides.aplicar_todos([e], {"velho": {"oculto": True}})[0].curadoria.oculto


def test_processar_detecta_prorrogacao_e_encerramento() -> None:
    antes = fazer_edital(data_limite=date(2026, 9, 30))
    antes.status = Status.aberto
    depois = fazer_edital(data_limite=date(2026, 10, 30))
    depois.status = Status.aberto
    [e], hist = processar([depois], {antes.id: antes}, {}, HOJE, AGORA)
    assert e.status == Status.prorrogado
    assert hist[0]["campo"] == "data_limite" and hist[0]["motivo"] == "prorrogado"
    assert e.updated_at == AGORA

    [e2], hist2 = processar([e], {e.id: e}, {}, date(2026, 11, 1), AGORA)
    assert e2.status == Status.encerrado and e2.prioridade == 0
    assert hist2[-1]["campo"] == "status" and hist2[-1]["depois"] == "encerrado"


def test_curadoria_pode_fixar_status() -> None:
    e = fazer_edital(data_limite=date(2026, 1, 1))
    [p], _ = processar([e], {}, {e.id: {"campos": {"status": "aberto"}}}, HOJE, AGORA)
    assert p.status == Status.aberto
