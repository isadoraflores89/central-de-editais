"""Imagem oficial (og:image) das oportunidades abertas."""

from datetime import UTC, datetime, timedelta

from pipeline.enums import Status
from pipeline.imagens import enriquecer, extrair_imagem, precisa_verificar
from tests.conftest import fazer_edital

HTML = """<html><head>
<meta charset="utf-8"><title>Edital</title>
<meta name="twitter:image" content="/img/twitter.jpg">
<meta property='og:image' content='https://cdn.exemplo.org/capa.png?v=2'>
</head><body><img src="/outra.png"></body></html>"""


def test_prefere_og_image_e_resolve_relativa() -> None:
    assert (
        extrair_imagem(HTML, "https://exemplo.org/edital") == "https://cdn.exemplo.org/capa.png?v=2"
    )
    so_twitter = HTML.replace("<meta property='og:image'", "<meta property='x'")
    assert (
        extrair_imagem(so_twitter, "https://exemplo.org/a/b")
        == "https://exemplo.org/img/twitter.jpg"
    )
    assert extrair_imagem("<html><head></head></html>", "https://exemplo.org") is None


def test_enriquecer_so_abertos_e_respeita_limite() -> None:
    agora = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
    aberto = fazer_edital(id="a1", status=Status.aberto, link_edital="https://exemplo.org/a")
    aberto2 = fazer_edital(id="a2", status=Status.aberto, link_edital="https://exemplo.org/b")
    encerrado = fazer_edital(id="e1", status=Status.encerrado, link_edital="https://exemplo.org/c")
    chamadas: list[str] = []

    def baixar(url: str) -> str:
        chamadas.append(url)
        if url.endswith("/b"):
            raise OSError("fora do ar")
        return HTML

    n = enriquecer([aberto, encerrado, aberto2], limite=5, agora=agora, baixar=baixar)
    assert n == 2 and chamadas == ["https://exemplo.org/a", "https://exemplo.org/b"]
    assert aberto.imagem == "https://cdn.exemplo.org/capa.png?v=2"
    assert aberto2.imagem is None and aberto2.imagem_verificada_em == agora
    assert encerrado.imagem is None and encerrado.imagem_verificada_em is None

    # Verificada hoje: não consulta de novo; depois de 14 dias, consulta.
    assert not precisa_verificar(aberto, agora + timedelta(days=3), 14)
    assert precisa_verificar(aberto, agora + timedelta(days=15), 14)
    assert enriquecer([aberto], limite=1, agora=agora + timedelta(days=1), baixar=baixar) == 0
