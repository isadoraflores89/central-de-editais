"""Fase 5: modelo, prioridade por vertical, coletores com fixtures, conteúdo semanal."""

from datetime import UTC, date, datetime
from pathlib import Path

from pipeline import config
from pipeline.collectors import ojs, onthemove
from pipeline.collectors.base import datas_no_texto, ler_fixture, primeira_frase, sem_html
from pipeline.content import weekly
from pipeline.enums import Cobre, FormatoOpenCall, Modalidade, Status, Vertical
from pipeline.export import formatos
from pipeline.models import SCHEMA_VERSION, Edital, Oportunidade
from pipeline.priority import calcular_prioridade
from tests.conftest import AGORA, HOJE, fazer_edital

AGORA_F5 = datetime(2026, 10, 31, 9, 0, tzinfo=UTC)
HOJE_F5 = date(2026, 10, 31)


def test_registro_v1_carrega_como_fomento() -> None:
    assert SCHEMA_VERSION == 2
    e = fazer_edital()
    assert e.vertical == Vertical.fomento
    assert e.idiomas == [] and e.cobre == [] and e.qualis is None
    assert Oportunidade is Edital


def test_com_taxa_e_pais_iso() -> None:
    e = fazer_edital(taxa_inscricao=25.0, taxa_moeda="EUR", pais_organizador="fr")
    assert e.com_taxa and e.pais_organizador == "FR"
    assert not fazer_edital(taxa_inscricao=0).com_taxa


def test_prioridade_open_call_gratuita_e_elegivel() -> None:
    e = fazer_edital(
        vertical=Vertical.open_call,
        taxa_inscricao=0,
        elegivel_brasileiros=True,
        cobre=[Cobre.passagem, Cobre.honorario],
        status=Status.aberto,
        data_limite=date(2026, 10, 20),
    )
    # gratuita 25 + elegível 20 + passagem 15 + honorário 10 + prazo 7–60 dias 20 = 90
    assert calcular_prioridade(e, HOJE) == 90


def test_prioridade_open_call_pay_to_play_desconta() -> None:
    e = fazer_edital(
        vertical=Vertical.open_call,
        taxa_inscricao=40,
        taxa_moeda="USD",
        marcadores=["alerta_taxa"],
        status=Status.aberto,
    )
    assert calcular_prioridade(e, HOJE) == 0


def test_prioridade_academico() -> None:
    e = fazer_edital(
        vertical=Vertical.academico,
        apc=0,
        qualis="A2",
        idiomas=["pt"],
        areas=["politicas_culturais"],
        status=Status.aberto,
    )
    # sem APC 20 + Qualis A 20 + português 10 + área 15 = 65
    assert calcular_prioridade(e, HOJE) == 65


def test_fomento_continua_igual() -> None:
    e = fazer_edital(abrangencia="nacional", ufs=["BA"], status=Status.aberto)
    assert calcular_prioridade(e, HOJE) == 35


def test_utilitarios_de_texto() -> None:
    assert sem_html("<p>Ol&aacute; <b>mundo</b></p>") == "Olá mundo"
    assert primeira_frase("<p>Residency in Lisbon for artists. More text here.</p>") == (
        "Residency in Lisbon for artists."
    )
    assert datas_no_texto("até 15/12/2026 ou 2027-01-10 ou 3 de março de 2027") == [
        "2026-12-15",
        "2027-01-10",
        "2027-03-03",
    ]


def test_onthemove_fixture() -> None:
    itens = onthemove.ler_feed(ler_fixture("onthemove/feed.xml"))
    assert len(itens) >= 5
    for it in itens:
        assert it.titulo and it.url.startswith("https://on-the-move.org/")
    editais = [onthemove.normalizar(it, AGORA_F5) for it in itens]
    assert all(e.vertical == Vertical.open_call for e in editais)
    assert all("link_agregador" in e.marcadores for e in editais)
    assert all(e.fonte == "onthemove" and e.idiomas == ["en"] for e in editais)
    # Nunca inventa taxa nem elegibilidade: ou vem do texto ou fica None.
    assert all(e.taxa_inscricao in (None, 0.0) or e.taxa_moeda for e in editais)
    assert len({e.id for e in editais}) == len(editais)


def test_onthemove_detecta_formato_e_contrapartidas() -> None:
    from pipeline.collectors.base import RawItem

    it = RawItem(
        "onthemove",
        "Residency for Latin American artists in Berlin, Germany",
        "https://on-the-move.org/news/x",
        "Open call: residency in Berlin. Travel and accommodation covered, no application fee. "
        "Deadline 15 January 2027.",
        "2026-10-20",
    )
    e = onthemove.normalizar(it, AGORA_F5)
    assert e.formato == FormatoOpenCall.residencia
    assert Cobre.passagem in e.cobre and Cobre.hospedagem in e.cobre
    assert e.taxa_inscricao == 0 and e.elegivel_brasileiros is True
    # Sem a página do item não há prazo confiável: fica pendente de revisão.
    assert e.data_limite is None and e.revisao_pendente and "link_agregador" in e.marcadores
    assert e.pais_organizador == "DE"


def test_onthemove_pagina_do_item() -> None:
    pg = onthemove.ler_pagina(ler_fixture("onthemove/item_in_situ.html"))
    assert pg["prazo"] == "2026-12-09"
    assert str(pg["link_oficial"]).startswith("https://drive.google.com/")
    assert str(pg["titulo"]).startswith("IN SITU: Online Support")
    assert pg["paises"] == ["Austria", "Europe"] and pg["mobilidade"] == "hybrid mobility"
    assert "Performing Arts" in pg["disciplinas"]

    itens = onthemove.ler_feed(ler_fixture("onthemove/feed.xml"))
    it = next(i for i in itens if "situ" in i.url)
    e = onthemove.normalizar(it, AGORA_F5, pg)
    assert e.data_limite == date(2026, 12, 9) and not e.revisao_pendente
    assert e.link_inscricao == pg["link_oficial"] and e.link_edital == it.url
    assert "link_agregador" not in e.marcadores
    assert e.pais_organizador == "AT" and e.modalidade == Modalidade.hibrida
    assert "artes_cenicas" in e.areas and "artes_visuais" in e.areas
    assert Cobre.passagem in e.cobre and Cobre.hospedagem in e.cobre
    assert e.taxa_inscricao is None  # a página não fala em taxa: não inventa


def test_ojs_fixture_so_pega_chamadas() -> None:
    html = ler_fixture("ojs/pculturais_announcement.html")
    avisos = ojs.extrair_avisos(html, "ojs:pculturais")
    assert len(avisos) >= 10  # a revista mantém avisos antigos no ar
    avisos = [a for a in avisos if ojs.recente(a, AGORA_F5)]
    assert len(avisos) == 2  # só os de 2026
    for a in avisos:
        assert a.url.startswith("http") and a.titulo
    rev = next(r for r in ojs.periodicos() if r["id"] == "pculturais")
    editais = [ojs.normalizar(a, rev, AGORA_F5) for a in avisos]
    for e in editais:
        assert e.vertical == Vertical.academico
        assert e.periodico == rev["nome"] and e.issn == rev["issn"]
        assert e.qualis is None  # não declarado no yaml: não inventa
        assert "politicas_culturais" in e.areas


def test_collector_ojs_com_fixtures_e_sem_rede() -> None:
    col = ojs.ColetorOJS({"pculturais": ler_fixture("ojs/pculturais_announcement.html")})
    saida = col.coletar()
    assert saida and all(e.fonte == "ojs:pculturais" for e in saida)


def test_exportacao_tem_colunas_novas(tmp_path: Path) -> None:
    e = fazer_edital(vertical=Vertical.academico, periodico="Revista X", qualis="B1")
    formatos.escrever_csv([e], tmp_path / "e.csv")
    cab = (tmp_path / "e.csv").read_text(encoding="utf-8").splitlines()[0]
    assert "Vertical" in cab and "Qualis" in cab and "Prazo do resumo" in cab
    doc = formatos.documento_json([e])
    assert doc["schema"] == 2 and doc["atribuicao"] == config.brand()["atribuicao"].strip()


def test_conteudo_semanal(tmp_path: Path, monkeypatch: object) -> None:
    b = config.brand()
    editais = [
        fazer_edital(
            id="a1",
            titulo="Edital Nacional de Música",
            status=Status.aberto,
            data_limite=HOJE_F5.replace(day=5, month=11),
            captured_at=AGORA_F5,
            updated_at=AGORA_F5,
            prioridade=70,
        ),
        fazer_edital(
            id="b2",
            titulo="Residency in Lisbon",
            vertical=Vertical.open_call,
            taxa_inscricao=0,
            status=Status.aberto,
            captured_at=AGORA_F5,
            updated_at=AGORA_F5,
            prioridade=85,
        ),
        fazer_edital(
            id="c3",
            titulo="Dossiê Políticas Culturais",
            vertical=Vertical.academico,
            status=Status.aberto,
            captured_at=AGORA,
            updated_at=AGORA,
            prioridade=40,
        ),
        fazer_edital(
            id="d4",
            titulo="Pay to play",
            vertical=Vertical.open_call,
            marcadores=["alerta_taxa"],
            status=Status.aberto,
            captured_at=AGORA_F5,
            updated_at=AGORA_F5,
        ),
    ]
    post = weekly.montar_post(editais, HOJE_F5, b)
    assert len(post) <= weekly.LIMITE_POST
    assert "2 oportunidades novas" in post and "1 internacionais (1 gratuitas)" in post
    assert "Pay to play" not in post  # alerta_taxa fica fora até a curadoria liberar
    assert f"https://{b['dominio']}/edital/b2" in post
    assert post.count("#") <= 3
    slides = weekly.montar_carrossel(editais, HOJE_F5, b)
    assert 3 <= len(slides) <= 8 and slides[-1]["titulo"] == b["nome"]
    alertas = weekly.montar_alertas(editais, HOJE_F5, b)
    assert "Residency in Lisbon" in alertas and "Edital Nacional" in alertas
