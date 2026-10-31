"""Coletores automáticos (Fase 5). Registro: nome -> fábrica."""

from __future__ import annotations

from collections.abc import Callable

from pipeline.collectors.base import Coletor


def registrados() -> dict[str, Callable[[], Coletor]]:
    from pipeline.collectors.ojs import ColetorOJS
    from pipeline.collectors.onthemove import ColetorOnTheMove

    return {
        "ojs": ColetorOJS,
        "onthemove": ColetorOnTheMove,
    }
