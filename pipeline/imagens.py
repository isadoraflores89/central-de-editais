"""Imagem oficial de cada oportunidade: lê og:image / twitter:image da página do edital.

Roda no robô diário (comando `python -m pipeline imagens`). Só consulta as oportunidades
abertas ou prorrogadas que ainda não têm imagem (ou cuja imagem foi verificada há mais de
`revalidar_dias`), com um limite de páginas por execução para a rotina não demorar.
Nunca inventa imagem: se a página não declara uma, o campo fica vazio e o site usa o
logotipo do domínio.
"""

from __future__ import annotations

import logging
import re
import urllib.error
import urllib.request
from datetime import UTC, datetime
from html import unescape
from urllib.parse import urljoin, urlsplit

from pipeline.collectors.base import UA
from pipeline.enums import Status
from pipeline.models import Edital

log = logging.getLogger("pipeline.imagens")

TIMEOUT = 20
MAX_BYTES = 400_000  # só o começo da página já traz o <head>

_META = re.compile(r"<meta\b[^>]*>", re.I)
_ATTR = re.compile(r"""([a-zA-Z:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))""")
_EXT_IMG = re.compile(r"\.(png|jpe?g|webp|gif|avif)(\?|$)", re.I)


def _atributos(tag: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in _ATTR.finditer(tag):
        nome = m.group(1).lower()
        out[nome] = unescape(m.group(2) or m.group(3) or m.group(4) or "")
    return out


def extrair_imagem(html: str, url_pagina: str) -> str | None:
    """Devolve a URL absoluta da imagem declarada na página, ou None."""
    candidatos: dict[str, str] = {}
    for m in _META.finditer(html):
        a = _atributos(m.group(0))
        chave = (a.get("property") or a.get("name") or a.get("itemprop") or "").lower()
        valor = (a.get("content") or "").strip()
        if not chave or not valor:
            continue
        if chave in ("og:image", "og:image:url", "og:image:secure_url"):
            candidatos.setdefault("og", valor)
        elif chave in ("twitter:image", "twitter:image:src"):
            candidatos.setdefault("twitter", valor)
        elif chave == "image":
            candidatos.setdefault("itemprop", valor)
    for chave in ("og", "twitter", "itemprop"):
        if chave in candidatos:
            img = urljoin(url_pagina, candidatos[chave])
            if urlsplit(img).scheme in ("http", "https"):
                return img
    return None


def _baixar_inicio(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        tipo = r.headers.get_content_type()
        if tipo and "html" not in tipo and "xml" not in tipo:
            raise OSError(f"não é HTML: {tipo}")
        bruto = r.read(MAX_BYTES)
        return str(bruto.decode(r.headers.get_content_charset() or "utf-8", "replace"))


def link_da_pagina(e: Edital) -> str | None:
    for link in (e.link_edital, e.link_inscricao, str(e.source_url)):
        if link and urlsplit(link).scheme in ("http", "https"):
            return link
    return None


def precisa_verificar(e: Edital, agora: datetime, revalidar_dias: int) -> bool:
    if e.status not in (Status.aberto, Status.prorrogado) or e.curadoria.oculto:
        return False
    if e.imagem_verificada_em is None:
        return True
    verificada = e.imagem_verificada_em
    if verificada.tzinfo is None:
        verificada = verificada.replace(tzinfo=UTC)
    return (agora - verificada).days >= revalidar_dias


def enriquecer(
    editais: list[Edital],
    *,
    limite: int = 60,
    revalidar_dias: int = 14,
    agora: datetime | None = None,
    baixar: object | None = None,
) -> int:
    """Preenche `imagem` nas oportunidades abertas. Devolve quantas páginas consultou."""
    agora = agora or datetime.now(UTC).replace(microsecond=0)
    download = baixar or _baixar_inicio
    consultadas = 0
    pendentes = [e for e in editais if precisa_verificar(e, agora, revalidar_dias)]
    # Primeiro as que nunca foram verificadas, depois as mais antigas.
    pendentes.sort(
        key=lambda e: (e.imagem_verificada_em is not None, e.imagem_verificada_em or agora)
    )
    for e in pendentes[:limite]:
        link = link_da_pagina(e)
        if not link:
            continue
        consultadas += 1
        try:
            html = download(link)  # type: ignore[operator]
            imagem = extrair_imagem(html, link)
        except (OSError, urllib.error.URLError, ValueError) as exc:
            log.info("sem imagem para %s (%s)", e.id, exc)
            imagem = None
        if imagem:
            e.imagem = imagem
        elif e.imagem and not _EXT_IMG.search(e.imagem):
            e.imagem = None
        e.imagem_verificada_em = agora
    return consultadas
