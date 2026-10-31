"""Publicação no LinkedIn — interface pronta e DESLIGADA.

A API de publicação do LinkedIn exige um app aprovado e uma Página vinculada,
o que fica para outra fase. Enquanto LINKEDIN_PUBLISH não for "1", `publicar()`
só devolve o que publicaria. Os rascunhos ficam em content/ para postagem manual.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class ResultadoPublicacao:
    publicado: bool
    motivo: str
    texto: str


def ligado() -> bool:
    return os.environ.get("LINKEDIN_PUBLISH", "0").strip() == "1"


def publicar(texto: str) -> ResultadoPublicacao:
    if not ligado():
        return ResultadoPublicacao(
            False, "LINKEDIN_PUBLISH desligado: rascunho fica em content/", texto
        )
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "").strip()
    autor = os.environ.get("LINKEDIN_AUTHOR_URN", "").strip()  # urn:li:organization:... ou person
    if not token or not autor:
        return ResultadoPublicacao(
            False, "faltam LINKEDIN_ACCESS_TOKEN / LINKEDIN_AUTHOR_URN", texto
        )
    # Implementação futura: POST https://api.linkedin.com/rest/posts com o token do app aprovado.
    return ResultadoPublicacao(False, "publicação pela API ainda não implementada", texto)
