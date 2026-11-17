"""Coletores automáticos (Fase 5). Registro: nome -> fábrica."""

from __future__ import annotations

from collections.abc import Callable

from pipeline.collectors.base import Coletor


def registrados() -> dict[str, Callable[[], Coletor]]:
    from pipeline.collectors.busca_web import ColetorBuscaWeb
    from pipeline.collectors.instagram import ColetorInstagram
    from pipeline.collectors.ojs import ColetorOJS
    from pipeline.collectors.onthemove import ColetorOnTheMove
    from pipeline.collectors.paginas import ColetorPaginas

    return {
        "ojs": ColetorOJS,
        "onthemove": ColetorOnTheMove,
        "instagram": ColetorInstagram,
        "paginas": ColetorPaginas,
        "busca_web": ColetorBuscaWeb,
    }
