"""Padrão editorial: título em frase e resumo com até 1000 caracteres."""

from pipeline.textnorm import resumo_padrao, titulo_padrao


def test_titulo_em_caixa_alta_vira_frase_e_mantem_siglas() -> None:
    assert titulo_padrao("CONTRATAÇÃO DE EMPRESA") == "Contratação de empresa"
    assert (
        titulo_padrao("EDITAL PNAB 2026 — FOMENTO À MÚSICA (BA)")
        == "Edital PNAB 2026 — fomento à música (BA)"
    )
    assert (
        titulo_padrao("🎨 PIRACICABA ABRE INSCRIÇÕES PARA 32 PROJETOS!")
        == "Piracicaba abre inscrições para 32 projetos"
    )
    assert titulo_padrao("CHAMADA MINC/FSA PARA AUDIOVISUAL") == "Chamada MinC/FSA para audiovisual"
    assert titulo_padrao("EDITAL DE CIRCULAÇÃO — SESC SP") == "Edital de circulação — Sesc SP"
    assert (
        titulo_padrao("R$ 915 MIL PARA A CULTURA DE ILHÉUS")
        == "R$ 915 mil para a cultura de Ilhéus"
    )


def test_titulo_em_caixa_mista_so_e_limpo() -> None:
    assert titulo_padrao("  Edital de Circulação Musical  ") == "Edital de Circulação Musical"
    assert titulo_padrao("📣 Atenção, entidades.") == "Atenção, entidades"
    assert titulo_padrao("") == ""


def test_resumo_corta_em_palavra_inteira() -> None:
    assert resumo_padrao("  a  b ") == "a b"
    longo = ("palavra " * 200).strip()
    r = resumo_padrao(longo)
    assert r is not None and len(r) <= 1000 and r.endswith("…") and not r.endswith(" …")
    assert resumo_padrao(None) is None
