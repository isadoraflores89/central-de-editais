"""Agente Instagram: filtro, extração por regras e normalização (sem rede)."""

from typing import Any

from pipeline.collectors.instagram import (
    ColetorInstagram,
    extrair_por_regras,
    normalizar,
    parece_oportunidade,
)
from pipeline.enums import Status

POST_EDITAL = {
    "caption": (
        "🎨 PIRACICABA ABRE INSCRIÇÕES PARA 32 PROJETOS CULTURAIS. "
        "Inscrições gratuitas até 7 de dezembro, às 17h. Edital em https://exemplo.gov.br/fac2026"
    ),
    "permalink": "https://www.instagram.com/p/ABC123/",
    "timestamp": "2026-11-09T12:00:00+0000",
    "media_type": "IMAGE",
    "media_url": "https://cdn.exemplo/img.jpg",
    "conta": "secultpiracicaba",
}
POST_AGENDA = {
    "caption": "Agenda da semana: shows, oficinas e exposições no centro cultural.",
    "permalink": "https://www.instagram.com/p/DEF456/",
    "timestamp": "2026-11-09T12:00:00+0000",
    "media_type": "IMAGE",
    "conta": "sescsp",
}
POST_VELHO = {
    **POST_EDITAL,
    "permalink": "https://www.instagram.com/p/OLD/",
    "timestamp": "2026-01-01T00:00:00+0000",
}


def test_filtro_de_palavras() -> None:
    assert parece_oportunidade(POST_EDITAL["caption"])
    assert not parece_oportunidade(POST_AGENDA["caption"])


def test_regras_leem_prazo_e_link() -> None:
    d = extrair_por_regras(POST_EDITAL)
    assert d["data_limite"] == "2026-12-07"
    assert d["link"] == "https://exemplo.gov.br/fac2026"
    assert d["titulo"].startswith("🎨 PIRACICABA")


def test_normalizar_nunca_publica_sem_aprovacao() -> None:
    from datetime import UTC, datetime

    agora = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)
    e = normalizar(POST_EDITAL, extrair_por_regras(POST_EDITAL), agora)
    assert e is not None
    assert e.data_limite is None and e.prazo_texto and "2026-12-07" in (e.observacoes or "")
    assert e.revisao_pendente and "aguardando_aprovacao" in e.marcadores
    assert e.status == Status.indefinido
    assert e.imagem == "https://cdn.exemplo/img.jpg" and e.orgao == "secultpiracicaba"
    assert str(e.source_url) == POST_EDITAL["permalink"]
    assert normalizar(POST_AGENDA, {"eh_oportunidade": False}, agora) is None


def test_coletor_filtra_antigos_e_agenda() -> None:
    chamados: list[str] = []

    def extrator(p: dict[str, Any]) -> dict[str, Any]:
        chamados.append(p["permalink"])
        return extrair_por_regras(p)

    col = ColetorInstagram(
        posts=[POST_EDITAL, POST_AGENDA, POST_VELHO],
        extrator=extrator,
        cfg={"dias": 400, "max_posts_ia": 10},
        guardar_vistos=False,
    )
    # dias=400 ainda corta o post de janeiro? não: 2026-01-01 está dentro de 400 dias de hoje.
    itens = col.coletar()
    assert chamados == [POST_EDITAL["permalink"], POST_VELHO["permalink"]]
    assert len(itens) == 2 and all(i.fonte == "instagram" for i in itens)
