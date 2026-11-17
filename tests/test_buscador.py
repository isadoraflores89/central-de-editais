"""Buscador: vigia de páginas e busca na web (sem rede, sem IA)."""

from datetime import UTC, datetime
from typing import Any

from pipeline.collectors.base import ler_fixture
from pipeline.collectors.busca_web import ESTADOS, ColetorBuscaWeb, consultas_do_dia
from pipeline.collectors.oportunidade import (
    Contexto,
    extrair_por_regras,
    link_confiavel,
    normalizar,
    parece_oportunidade,
    texto_da_pagina,
)
from pipeline.collectors.paginas import ColetorPaginas, fontes_do_dia, links_candidatos
from pipeline.enums import Status, Vertical

LISTA = "https://exemplo.gov.br/cultura/editais"
EDITAL = "https://exemplo.gov.br/cultura/editais/edital-musica-2026"
AGORA = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
FONTE = {
    "id": "exemplo",
    "nome": "Secretaria exemplo",
    "url": LISTA,
    "uf": "BA",
    "abrangencia": "estadual",
}


def test_links_candidatos_filtra_ruido_pdf_e_repetidos() -> None:
    links = links_candidatos(ler_fixture("paginas/lista.html"), LISTA)
    assert links == [(EDITAL, "Edital de fomento à música 2026: inscrições abertas")]


def test_fontes_semanais_entram_em_rodizio() -> None:
    fontes = [{"id": f"f{i}", "url": "https://x", "frequencia": "semanal"} for i in range(40)]
    fontes.append({"id": "diaria", "url": "https://y", "frequencia": "diaria", "prioridade": 3})
    dia = fontes_do_dia(fontes, AGORA)
    assert dia[0]["id"] == "diaria" and 1 < len(dia) < 20
    assert not fontes_do_dia([{"id": "m", "url": "https://z", "metodo": "manual"}], AGORA)


def test_regras_leem_prazo_e_normalizar_confirma_no_texto() -> None:
    texto = texto_da_pagina(ler_fixture("paginas/edital.html"))
    assert "var x" not in texto and parece_oportunidade(texto)
    ctx = Contexto(
        EDITAL, texto, "exemplo", "Secretaria exemplo", "Edital de música", "BR", "BA", "estadual"
    )
    dados = extrair_por_regras(ctx)
    assert dados["data_limite"] == "2026-12-20"
    e = normalizar(ctx, dados, AGORA, "coleta:pagina")
    assert e is not None and e.data_limite is not None and e.data_limite.isoformat() == "2026-12-20"
    assert e.ufs == ["BA"] and e.vertical == Vertical.fomento and not e.revisao_pendente
    assert "aguardando_aprovacao" not in e.marcadores and "fonte:exemplo" in e.marcadores


def test_data_inventada_vira_revisao_pendente() -> None:
    texto = texto_da_pagina(ler_fixture("paginas/edital.html"))
    ctx = Contexto(EDITAL, texto, "exemplo", "Secretaria exemplo", "", "BR", "BA", "estadual")
    dados: dict[str, Any] = {
        "eh_oportunidade": True,
        "titulo": "Edital de fomento à música 2026",
        "data_limite": "2026-12-31",
        "link_inscricao": "https://outro-site.com/x",
        "ufs": ["BA", "XX"],
        "areas": ["musica", "inexistente"],
        "mecanismo": ["pnab"],
        "valor_min": "30000",
    }
    e = normalizar(ctx, dados, AGORA, "coleta:pagina")
    assert e is not None and e.data_limite is None and e.revisao_pendente
    assert "aguardando_aprovacao" in e.marcadores and "link_externo" in e.marcadores
    assert e.ufs == ["BA"] and e.areas == ["musica"] and e.valor_por_projeto_min == 30000
    assert e.status == Status.indefinido
    assert (
        normalizar(ctx, {"eh_oportunidade": True, "titulo": "x", "encerrado": True}, AGORA, "m")
        is None
    )


def test_link_confiavel() -> None:
    assert link_confiavel("https://inscricoes.exemplo.gov.br/m", EDITAL)
    assert link_confiavel("https://prosas.com.br/editais/1", EDITAL)
    assert not link_confiavel("https://bit.ly/x", EDITAL)


def test_coletor_paginas_le_so_links_novos() -> None:
    chamados: list[str] = []

    def extrator(c: Contexto) -> dict[str, Any]:
        chamados.append(c.url)
        return extrair_por_regras(c)

    col = ColetorPaginas(
        fontes=[FONTE],
        paginas={
            LISTA: ler_fixture("paginas/lista.html"),
            EDITAL: ler_fixture("paginas/edital.html"),
        },
        extrator=extrator,
        cfg={"max_por_fonte": 3, "max_ia": 10},
        guardar_vistos=False,
        agora=AGORA,
    )
    itens = col.coletar()
    assert chamados == [EDITAL] and len(itens) == 1
    assert itens[0].fonte == "exemplo" and itens[0].orgao == "Secretaria exemplo"


def test_busca_web_rodizio_e_coleta() -> None:
    cfg = {
        "consultas": [{"q": f"c{i}", "pais": "BR"} for i in range(10)],
        "consultas_por_dia": 3,
        "estados_por_dia": 2,
        "consulta_por_estado": "edital cultura {estado} {uf}",
    }
    hoje = consultas_do_dia(cfg, AGORA)
    assert len(hoje) == 5 and hoje[-1]["uf"] in ESTADOS
    col = ColetorBuscaWeb(
        motor=lambda q: [
            {"link": EDITAL + "?utm_source=g", "titulo": "Edital de música 2026"},
            {"link": "https://www.instagram.com/p/x", "titulo": "post"},
            {"link": "https://exemplo.gov.br/resultado", "titulo": "Resultado do edital"},
            {
                "link": "https://fora.org/pdf-sem-texto",
                "titulo": "Chamada X",
                "orgao": "Fora",
                "prazo": "2027-01-10",
            },
        ],
        paginas={EDITAL: ler_fixture("paginas/edital.html")},
        extrator=extrair_por_regras,
        cfg={
            "consultas": [{"q": "edital", "pais": "BR"}],
            "consultas_por_dia": 1,
            "estados_por_dia": 0,
        },
        guardar_vistos=False,
        agora=AGORA,
    )
    itens = col.coletar()
    assert [e.source_url.host for e in itens] == ["exemplo.gov.br", "fora.org"]
    assert itens[0].data_limite is not None and not itens[0].revisao_pendente
    assert (
        itens[1].revisao_pendente
        and itens[1].orgao == "Fora"
        and itens[1].prazo_texto == "2027-01-10"
    )


ESTADOS_OK = {
    "AC",
    "AL",
    "AM",
    "AP",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MG",
    "MS",
    "MT",
    "PA",
    "PB",
    "PE",
    "PI",
    "PR",
    "RJ",
    "RN",
    "RO",
    "RR",
    "RS",
    "SC",
    "SE",
    "SP",
    "TO",
}
