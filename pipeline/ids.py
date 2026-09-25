"""Identificador estável de um edital (decisão D2 do PLANO).

O id é calculado uma vez, na primeira captura, e depois fica congelado no
registro. Nunca recalcular o id de um edital que já existe: use as chaves do
dedupe para reconhecê-lo.
"""

import hashlib

from pipeline.textnorm import normalizar, slugify


def gerar_id(fonte: str, titulo: str) -> str:
    base = f"{normalizar(fonte)}|{normalizar(titulo)}"
    sufixo = hashlib.sha1(base.encode("utf-8")).hexdigest()[:6]
    return f"{slugify(titulo)}-{sufixo}"
