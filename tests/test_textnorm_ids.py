from pipeline.ids import gerar_id
from pipeline.textnorm import normalizar, slugify, url_canonica, url_generica


def test_normalizar_remove_acentos_e_travessoes() -> None:
    assert normalizar("  Lei do Esporte — Paraná  ") == "lei do esporte parana"


def test_slugify_limita_tamanho_sem_cortar_palavra() -> None:
    s = slugify("Maceió — Editais PNAB Ciclo 2 (Lagoa Mundaú, Praia do Sobral, Jaraguá)", 30)
    assert s == "maceio-editais-pnab-ciclo-2"


def test_url_canonica_prosas_ignora_slug_e_fragmento() -> None:
    a = url_canonica("https://prosas.com.br/editais/16452-edital-ambev-brasilidades-2026")
    b = url_canonica("https://www.prosas.com.br/editais/16452/#info")
    assert a == b == "https://prosas.com.br/editais/16452"


def test_url_generica() -> None:
    assert url_generica("https://prosas.com.br/editais?status=abertos")
    assert not url_generica("https://prosas.com.br/editais/18788")


def test_id_estavel_e_legivel() -> None:
    a = gerar_id("fonte", "Ambev Brasilidades 2026")
    assert a == gerar_id("fonte", "ambev  brasilidades 2026")
    assert a.startswith("ambev-brasilidades-2026-")
    assert a != gerar_id("outra fonte", "Ambev Brasilidades 2026")
