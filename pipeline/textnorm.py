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


# ---------- padrão editorial de título e resumo (10/11/2026) ----------
# Título em frase ("Contratação de empresa"), nunca em caixa alta; resumo com até 1000 caracteres.
_SIGLAS = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE",
    "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO", "PNAB", "FSA", "FAC", "FIA",
    "ICMS", "LIC", "PNCP", "SALIC", "UNESCO", "BNDES", "CNPQ", "CAPES", "FAPESP", "FAPERJ",
    "FAPESB", "UFBA", "UFRJ", "USP", "UFMG", "UFRGS", "UFPE", "UFC", "UFPA", "UNB", "UNICAMP",
    "UNESP", "IPHAN", "IBRAM", "FBN", "ANCINE", "BRDE", "MIS", "CCBB", "EUA", "UE", "ONG", "OSC",
    "MEI", "PJ", "PF", "CNPJ", "LGBTQIA+", "LGBT", "RIOFILME", "MINC",
}  # fmt: skip
_CASOS = {"MINC": "MinC", "RIOFILME": "RioFilme", "CNPQ": "CNPq", "UNB": "UnB"}
# nomes próprios frequentes em títulos de edital (caixa alta -> forma usual)
_PROPRIOS = [
    "Sesc",
    "Sesi",
    "Senac",
    "Senai",
    "Funarte",
    "Petrobras",
    "Itaú",
    "Natura",
    "Caixa",
    "Bradesco",
    "Santander",
    "Ambev",
    "Oi",
    "Vale",
    "Brasil",
    "Bahia",
    "Salvador",
    "Paulo",
    "Rio",
    "Janeiro",
    "Minas",
    "Gerais",
    "Paraná",
    "Curitiba",
    "Recife",
    "Pernambuco",
    "Fortaleza",
    "Ceará",
    "Pará",
    "Belém",
    "Goiás",
    "Goiânia",
    "Amazonas",
    "Manaus",
    "Maranhão",
    "Luís",
    "Piauí",
    "Teresina",
    "Alagoas",
    "Maceió",
    "Sergipe",
    "Aracaju",
    "Paraíba",
    "Pessoa",
    "Natal",
    "Norte",
    "Sul",
    "Grande",
    "Catarina",
    "Florianópolis",
    "Porto",
    "Alegre",
    "Espírito",
    "Santo",
    "Vitória",
    "Mato",
    "Grosso",
    "Cuiabá",
    "Campo",
    "Campinas",
    "Niterói",
    "Olinda",
    "Rondônia",
    "Roraima",
    "Amapá",
    "Acre",
    "Tocantins",
    "Palmas",
    "Distrito",
    "Federal",
    "Brasília",
    "Nordeste",
    "Sudeste",
    "Centro-Oeste",
    "Piracicaba",
    "Ilhéus",
    "Juazeiro",
    "Feira",
    "Santana",
    "Lauro",
    "Freitas",
    "Camaçari",
    "Cachoeira",
    "Petrolina",
    "Sobral",
    "Ouro",
    "Preto",
    "Diamantina",
    "Paraty",
    "Santos",
    "Sorocaba",
    "Ribeirão",
    "Londrina",
    "Maringá",
    "Joinville",
    "Blumenau",
    "Caxias",
    "Pelotas",
    "Uberlândia",
    "Ipatinga",
    "Montes",
    "Claros",
    "Rouanet",
    "Aldir",
    "Blanc",
    "Lula",
    "Dilma",
    "Marielle",
    "Carlos",
    "Gomes",
    "Villa-Lobos",
    "Oscar",
    "Niemeyer",
    "Lina",
    "Bardi",
    "Jorge",
    "Amado",
    "Machado",
    "Assis",
    "Clarice",
    "Lispector",
    "Caetano",
    "Gil",
    "Gilberto",
    "Rosa",
    "Renata",
    "Garra",
    "Cultural",
    "Culturais",
]
_CASOS.update({n.upper(): n for n in _PROPRIOS})
_SIMBOLO_INICIO = re.compile(r"^[\W_]+", re.U)
_SO_SIMBOLOS = re.compile(r"[\U0001F000-\U0001FFFF☀-➿⬀-⯿️]")


def _token_padrao(nucleo: str) -> str:
    chave = nucleo.upper()
    sem = sem_acento(nucleo).lower()
    if chave in _CASOS:
        return _CASOS[chave]
    sigla = chave in _SIGLAS or (
        nucleo.isupper() and 2 <= len(nucleo) <= 4 and not any(v in sem for v in "aeiou")
    )
    return _CASOS.get(chave, chave) if sigla else nucleo.lower()


def _palavra_padrao(p: str) -> str:
    # trata cada parte separada por "/" (MINC/FSA) e preserva a pontuação em volta
    return "/".join(
        re.sub(r"[^\W_]+(?:[+]|)", lambda m: _token_padrao(m.group(0)), parte)
        for parte in p.split("/")
    )


def titulo_padrao(titulo: str | None) -> str:
    """Tira emojis e símbolos do começo; se o título está em caixa alta, vira frase.

    Mantém siglas (PNAB, FSA, UFs, MinC). Títulos já em caixa mista não são alterados,
    só limpos. Nomes próprios dentro de títulos em caixa alta ficam em minúscula e
    podem ser corrigidos pela curadoria (overrides.yaml).
    """
    t = _SO_SIMBOLOS.sub("", titulo or "")
    t = _SIMBOLO_INICIO.sub("", t)
    t = _ESPACOS.sub(" ", t).strip().rstrip(".!")
    if not t:
        return (titulo or "").strip()
    letras = [c for c in t if c.isalpha()]
    if letras and sum(c.isupper() for c in letras) / len(letras) >= 0.7:
        t = " ".join(_palavra_padrao(p) for p in t.split(" "))
    return t[0].upper() + t[1:]


def resumo_padrao(resumo: str | None, maximo: int = 1000) -> str | None:
    """Espaços colapsados e corte em palavra inteira até `maximo` caracteres."""
    if not resumo:
        return None
    t = _ESPACOS.sub(" ", resumo).strip()
    if len(t) <= maximo:
        return t
    corte = t[: maximo - 1].rsplit(" ", 1)[0]
    return corte.rstrip(",;:—-") + "…"
