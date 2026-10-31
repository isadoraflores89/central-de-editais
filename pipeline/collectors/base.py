"""Base dos coletores: item bruto, download com cache, rate limit e robots.txt.

Todo coletor expõe `nome`, `vertical` e `coletar() -> list[Edital]`. O download
passa sempre por `baixar()`, que respeita robots.txt, espera entre pedidos e
guarda o conteúdo em data/cache/ (fora do git) por algumas horas. Nos testes,
`Coletor.de_fixture()` lê o arquivo salvo em tests/fixtures/ e nunca acessa a rede.
"""

from __future__ import annotations

import hashlib
import re
import time
import urllib.error
import urllib.request
import urllib.robotparser
from dataclasses import dataclass, field
from datetime import UTC, datetime
from html import unescape
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlsplit

from pipeline import config
from pipeline.models import Edital

UA = "Mozilla/5.0 (compatible; CentralDeEditais/1.0; +https://radardeeditais.isadoraflores.art.br)"
CACHE_DIR = config.DATA / "cache"
CACHE_HORAS = 6
INTERVALO_SEGUNDOS = 1.5


@dataclass
class RawItem:
    """O que um coletor extrai de uma fonte antes da normalização."""

    fonte: str
    titulo: str
    url: str
    resumo: str = ""
    publicado_em: str = ""  # AAAA-MM-DD quando a fonte informa
    extra: dict[str, Any] = field(default_factory=dict)


class Coletor(Protocol):
    nome: str

    def coletar(self) -> list[Edital]: ...


_robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
_ultimo_pedido: dict[str, float] = {}


def pode_acessar(url: str) -> bool:
    host = urlsplit(url).netloc
    if host not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            req = urllib.request.Request(
                f"{urlsplit(url).scheme}://{host}/robots.txt", headers={"User-Agent": UA}
            )
            with urllib.request.urlopen(req, timeout=20) as r:
                rp.parse(r.read().decode("utf-8", "replace").splitlines())
            _robots[host] = rp
        except (OSError, ValueError):
            _robots[host] = None  # sem robots.txt legível: segue
    rp2 = _robots[host]
    return True if rp2 is None else rp2.can_fetch(UA, url)


def _espera(host: str) -> None:
    agora = time.monotonic()
    ultimo = _ultimo_pedido.get(host)
    if ultimo is not None and agora - ultimo < INTERVALO_SEGUNDOS:
        time.sleep(INTERVALO_SEGUNDOS - (agora - ultimo))
    _ultimo_pedido[host] = time.monotonic()


def baixar(url: str, *, cache_horas: float = CACHE_HORAS) -> str:
    """Baixa uma URL (texto) com cache em disco. Levanta OSError se falhar."""
    chave = hashlib.sha1(url.encode("utf-8")).hexdigest()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    arq = CACHE_DIR / f"{chave}.txt"
    if arq.exists():
        idade = (datetime.now(UTC).timestamp() - arq.stat().st_mtime) / 3600
        if idade < cache_horas:
            return arq.read_text(encoding="utf-8")
    if not pode_acessar(url):
        raise OSError(f"robots.txt proíbe {url}")
    _espera(urlsplit(url).netloc)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    with urllib.request.urlopen(req, timeout=60) as r:
        texto = str(r.read().decode(r.headers.get_content_charset() or "utf-8", "replace"))
    arq.write_text(texto, encoding="utf-8")
    return texto


def ler_fixture(caminho: str) -> str:
    """Lê um arquivo salvo em tests/fixtures/ (usado pelos testes e por --simular)."""
    return (config.RAIZ / "tests" / "fixtures" / caminho).read_text(encoding="utf-8")


_TAGS = re.compile(r"<[^>]+>")
_ESPACOS = re.compile(r"\s+")


def sem_html(texto: str | None) -> str:
    return _ESPACOS.sub(" ", unescape(_TAGS.sub(" ", texto or ""))).strip()


def primeira_frase(texto: str, maximo: int = 140) -> str:
    t = sem_html(texto)
    m = re.match(r"(.{20,}?[.!?])(\s|$)", t)
    frase = m.group(1) if m else t
    return (frase[: maximo - 1] + "…") if len(frase) > maximo else frase


_DATA_BR = re.compile(r"\b(\d{1,2})[/.](\d{1,2})[/.](\d{4})\b")
_DATA_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_MESES = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "março": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7,
    "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}  # fmt: skip
_DATA_EXTENSO = re.compile(
    r"\b(\d{1,2})\s*(?:de\s+)?([a-zç]+)\s*(?:de\s+|,\s*)?(\d{4})\b", re.IGNORECASE
)


def datas_no_texto(texto: str) -> list[str]:
    """Todas as datas reconhecíveis no texto, em AAAA-MM-DD, na ordem em que aparecem."""
    achadas: list[tuple[int, str]] = []
    for m in _DATA_ISO.finditer(texto):
        achadas.append((m.start(), f"{m.group(1)}-{m.group(2)}-{m.group(3)}"))
    for m in _DATA_BR.finditer(texto):
        d, mes, a = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mes <= 12 and 1 <= d <= 31:
            achadas.append((m.start(), f"{a:04d}-{mes:02d}-{d:02d}"))
    for m in _DATA_EXTENSO.finditer(texto):
        num = _MESES.get(m.group(2).lower())
        if num:
            achadas.append((m.start(), f"{int(m.group(3)):04d}-{num:02d}-{int(m.group(1)):02d}"))
    return [d for _, d in sorted(achadas)]


def arquivo_fixture(coletor: str, nome: str) -> Path:
    return config.RAIZ / "tests" / "fixtures" / coletor / nome
