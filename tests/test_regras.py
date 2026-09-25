import pytest

from pipeline.enums import Abrangencia, Mecanismo, Proponente, TipoApoio
from pipeline.normalize import regras


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Credenciamento (pessoa física ou MEI)", TipoApoio.credenciamento),
        ("Patrocínio via leis ESTADUAIS de incentivo (cultura e esporte)",
         TipoApoio.patrocinio_incentivado),
        ("Patrocínio corporativo (fluxo contínuo)", TipoApoio.patrocinio_direto),
        ("Lei estadual de incentivo (ICMS) — Bahia", TipoApoio.lei_incentivo_janela),
        ("Premiação (fomento direto)", TipoApoio.premio),
        ("Edital público (fomento direto)", TipoApoio.fomento_direto),
        ("Cessão de espaço (pauta gratuita)", TipoApoio.cessao_espaco),
        ("Vitrine de projetos incentivados (fluxo contínuo)", TipoApoio.banco_projetos),
        ("Apoio a internacionalização (reembolso)", TipoApoio.bolsa_mobilidade),
        ("algo que nenhuma regra conhece", None),
    ],
)
def test_tipo_apoio(texto: str, esperado: TipoApoio | None) -> None:
    assert regras.tipo_apoio(texto) == esperado


def test_mecanismos_multiplos() -> None:
    m = regras.mecanismos("Projetos aptos a captar via Lei Rouanet, Lei do Esporte, FMDCA e Pronon")
    assert m == [Mecanismo.rouanet, Mecanismo.lei_esporte, Mecanismo.pronon_pronas,
                 Mecanismo.fia_idoso]


def test_lei_estadual_de_esporte_nao_e_lei_federal() -> None:
    assert Mecanismo.lei_esporte not in regras.mecanismos("leis estaduais de incentivo ao esporte")


def test_abrangencia_nacional() -> None:
    assert regras.abrangencia("Nacional (áreas Sicredi)") == (Abrangencia.nacional, [], [])


def test_abrangencia_municipal_com_cidade() -> None:
    assert regras.abrangencia("São José dos Campos/SP") == (
        Abrangencia.municipal, ["SP"], ["São José dos Campos"]
    )


def test_nome_de_lei_nao_vira_cidade() -> None:
    _, cidades = regras.ufs_e_cidades("cultura em 16 estados (inclui Fazcultura/BA e Profice/PR)")
    assert cidades == []


def test_abrangencia_regional_por_siglas_e_nomes() -> None:
    abr, ufs, _ = regras.abrangencia("RJ, SP e MG")
    assert abr == Abrangencia.regional and ufs == ["MG", "RJ", "SP"]
    assert regras.abrangencia("Mato Grosso do Sul")[1] == ["MS"]


def test_abrangencia_desconhecida_fica_vazia() -> None:
    assert regras.abrangencia("em algum lugar") == (None, [], [])


def test_valores_por_projeto_e_total() -> None:
    v = regras.valores("Chamada 2026: até R$ 1,5 milhão por projeto e R$ 30 milhões no total.")
    assert v["valor_por_projeto_max"] == 1_500_000
    assert v["valor_total"] == 30_000_000


def test_valor_total_por_extenso() -> None:
    assert regras.valores("investimento total de R$ 10 milhões.")["valor_total"] == 10_000_000


def test_moeda_estrangeira_nao_e_convertida() -> None:
    v = regras.valores("com até € 175 mil por projeto minoritário.")
    assert v["valor_por_projeto_max"] is None
    assert v["valor_texto"] is not None and "€ 175 mil" in v["valor_texto"]


def test_valor_texto_nao_corta_milhar() -> None:
    v = regras.valores("Remuneração de R$ 60 a R$ 2.430 por parecer. Inscrição pelo Mapa.")
    assert v["valor_texto"] == "Remuneração de R$ 60 a R$ 2.430 por parecer."


def test_proponente_pj_sem_fins_e_so_osc() -> None:
    assert regras.proponentes("Elegíveis pessoas jurídicas sem fins lucrativos") == [
        Proponente.osc
    ]
    assert Proponente.pj in regras.proponentes("Somente pessoas jurídicas")


def test_exige_projeto_aprovado() -> None:
    assert regras.exige_projeto_aprovado(TipoApoio.premio, "já aprovados") is False
    assert regras.exige_projeto_aprovado(TipoApoio.patrocinio_direto, "já aprovados") is True
    assert regras.exige_projeto_aprovado(TipoApoio.patrocinio_incentivado) is True
    assert regras.exige_projeto_aprovado(TipoApoio.patrocinio_direto, "sem pistas") is None


def test_link_edital_so_com_rotulo_oficial() -> None:
    obs = "Link divulgado em: https://blog.com/x | Edital em PDF: https://gov.br/edital.pdf."
    assert regras.link_edital_das_observacoes(obs) == "https://gov.br/edital.pdf"
    assert regras.link_edital_das_observacoes("Link em: https://blog.com/x") is None
