"""Normalização de texto: sem acento, minúsculo, espaços simples, slug."""

import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit

_ESPACOS = re.compile(r"\s+")
_NAO_SLUG = re.compile(r"[^a-z0-9]+")


def sem_acento(texto: str) -> str:
    decomposto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in decomposto if unicodedata.category(c) != "Mn")


def normalizar(texto: str | None) -> str:
    """Minúsculo, sem acento, travessões viram espaço, espaços colapsados."""
    if not texto:
        return ""
    t = sem_acento(texto).lower()
    t = t.replace("—", " ").replace("–", " ")
    return _ESPACOS.sub(" ", t).strip()


def slugify(texto: str, max_len: int = 60) -> str:
    slug = _NAO_SLUG.sub("-", normalizar(texto)).strip("-")
    if len(slug) > max_len:
        slug = slug[:max_len].rsplit("-", 1)[0]
    return slug


def url_canonica(url: str | None) -> str | None:
    """Forma comparável de uma URL, para o dedupe.

    - host minúsculo, sem "www.", sem fragmento (#info), sem barra final;
    - Prosas: /editais/16452-edital-ambev → /editais/16452 (o slug muda, o número não).
    """
    if not url:
        return None
    partes = urlsplit(url.strip())
    host = partes.netloc.lower().removeprefix("www.")
    caminho = partes.path.rstrip("/")
    if host == "prosas.com.br":
        m = re.match(r"^(/editais/\d+)", caminho)
        if m:
            caminho = m.group(1)
    return urlunsplit(("https", host, caminho, partes.query, ""))


# URLs de listagem que várias linhas compartilham sem serem o mesmo edital.
_URLS_GENERICAS = {
    "https://prosas.com.br/editais?status=abertos",
    "https://prosas.com.br/editais",
}


def url_generica(url: str | None) -> bool:
    return url_canonica(url) in _URLS_GENERICAS
