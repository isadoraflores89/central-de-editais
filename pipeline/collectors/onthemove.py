"""On the Move (on-the-move.org): agregador de mobilidade artística, via RSS.

O feed público lista as últimas notícias, quase todas open calls, mas sem prazo
e com título vazio ("[News] "). Por isso o coletor abre a página de cada item
(10 por rodada, com cache e intervalo) e lê de lá: título, "Deadline:", o botão
"More info & apply" (link oficial da instituição), países de destino, tipo de
mobilidade, disciplinas e o texto completo. O link do On the Move fica em
source_url e o oficial em link_inscricao (marcador `link_agregador` quando
só existe o do agregador), como pede o adendo.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import UTC, date, datetime
from email.utils import parsedate_to_datetime

from pipeline.collectors.base import RawItem, baixar, primeira_frase, sem_html
from pipeline.enums import Cobre, FormatoOpenCall, Modalidade, Vertical
from pipeline.ids import gerar_id
from pipeline.models import Edital

FEED = "https://on-the-move.org/feed"
FONTE = "onthemove"

_FORMATO = [
    (FormatoOpenCall.residencia, r"residenc"),
    (FormatoOpenCall.bolsa_mobilidade, r"fellowship|grant|bursar|scholarship|mobility"),
    (FormatoOpenCall.premio, r"\bprize|\baward|\bpremio"),
    (FormatoOpenCall.festival, r"festival|biennale|bienal"),
    (FormatoOpenCall.exposicao, r"exhibit|exposi"),
    (FormatoOpenCall.comissionamento, r"commission"),
    (FormatoOpenCall.publicacao_artistica, r"publication|anthology|magazine"),
]
_COBRE = [
    (Cobre.passagem, r"travel|flight|transport"),
    (Cobre.hospedagem, r"accommodation|housing|lodging"),
    (Cobre.honorario, r"\bfee\b.*(artist|paid)|honorari|stipend|remunerat"),
    (Cobre.ajuda_custo, r"per diem|living (costs|allowance)|allowance"),
    (Cobre.producao, r"production (budget|costs|support)"),
    (Cobre.alimentacao, r"meals|food"),
]
_PAISES = {
    "france": "FR", "germany": "DE", "spain": "ES", "portugal": "PT", "italy": "IT",
    "netherlands": "NL", "belgium": "BE", "united kingdom": "GB", "uk": "GB", "usa": "US",
    "united states": "US", "canada": "CA", "brazil": "BR", "brasil": "BR", "argentina": "AR",
    "mexico": "MX", "chile": "CL", "colombia": "CO", "uruguay": "UY", "austria": "AT",
    "switzerland": "CH", "sweden": "SE", "norway": "NO", "denmark": "DK", "finland": "FI",
    "poland": "PL", "greece": "GR", "japan": "JP", "south korea": "KR", "australia": "AU",
    "south africa": "ZA", "senegal": "SN", "nigeria": "NG", "india": "IN", "turkey": "TR",
    "online": "",
}  # fmt: skip
_GRATUITA = re.compile(r"no (application )?fee|free (to apply|of charge)|without fee", re.I)
_TAXA = re.compile(
    r"(application|entry|submission) fee[^.]{0,40}?(\d+)\s*(€|eur|\$|usd|£|gbp)", re.I
)


def ler_feed(xml: str) -> list[RawItem]:
    raiz = ET.fromstring(xml)
    canal = raiz.find("channel")
    itens: list[RawItem] = []
    for it in canal.findall("item") if canal is not None else []:
        link = (it.findtext("link") or "").strip()
        desc = it.findtext("description") or ""
        titulo = sem_html(it.findtext("title") or "").replace("[News]", "").strip()
        if not titulo:
            titulo = primeira_frase(desc)
        pub = ""
        if it.findtext("pubDate"):
            try:
                pub = parsedate_to_datetime(it.findtext("pubDate") or "").date().isoformat()
            except (TypeError, ValueError):
                pub = ""
        if link and titulo:
            itens.append(RawItem(FONTE, titulo, link, sem_html(desc), pub))
    return itens


_DEADLINE = re.compile(r"class='deadline'>Deadline:\s*<time datetime=\"(\d{4}-\d{2}-\d{2})")
_APPLY = re.compile(r"<a href='([^']+)' class='btn btn--dark btn--apply'")
_H1 = re.compile(r'<h1 class="page-title">(.*?)</h1>', re.S)
_BODY = re.compile(r"field--name-body[^>]*>(.*?)</article>", re.S)
_PAISES_BLOCO = re.compile(r"Destination countries:</b>(.*?)</div>\s*</div>\s*</div>", re.S)
_MOBILIDADE = re.compile(r"</svg>\s*([A-Za-z ]+mobility)</span>")
_DISCIPLINAS = re.compile(r'views-field-field-art-form-discipline">(.*?)</div></div>', re.S)
_SO_PRAZO = re.compile(
    r"(deadline|apply by|until|before|closing|applications close)[^.]{0,40}", re.I
)


def ler_pagina(html: str) -> dict[str, str | list[str]]:
    """Campos da página de um item do On the Move (vazio quando não encontra)."""
    dados: dict[str, str | list[str]] = {}
    if m := _DEADLINE.search(html):
        dados["prazo"] = m.group(1)
    if m := _APPLY.search(html):
        dados["link_oficial"] = m.group(1)
    if m := _H1.search(html):
        dados["titulo"] = sem_html(m.group(1))
    if m := _BODY.search(html):
        dados["texto"] = sem_html(m.group(1))
    if m := _PAISES_BLOCO.search(html):
        dados["paises"] = [p.strip() for p in sem_html(m.group(1)).split(",") if p.strip()]
    if m := _MOBILIDADE.search(html):
        dados["mobilidade"] = m.group(1).strip().lower()
    if m := _DISCIPLINAS.search(html):
        dados["disciplinas"] = [d.strip() for d in sem_html(m.group(1)).split(",") if d.strip()]
    return dados


_DISCIPLINA_AREA = {
    "performing arts": "artes_cenicas", "visual arts": "artes_visuais", "music": "musica",
    "film": "audiovisual", "audiovisual": "audiovisual", "literature": "literatura",
    "heritage": "patrimonio", "cross-disciplinary": "multi", "digital": "artes_visuais",
    "dance": "artes_cenicas", "theatre": "artes_cenicas", "research": "formacao",
    "education": "formacao", "cultural management": "gestao_cultural",
}  # fmt: skip


def _areas(disciplinas: list[str]) -> list[str]:
    saida: list[str] = []
    for d in disciplinas:
        for chave, area in _DISCIPLINA_AREA.items():
            if chave in d.lower() and area not in saida:
                saida.append(area)
    return saida


def _pais(url: str, texto: str) -> str | None:
    slug = url.rstrip("/").rsplit("/", 1)[-1].replace("-", " ")
    for nome, iso in _PAISES.items():
        if slug.endswith(nome) or re.search(rf"\b{re.escape(nome)}\b", texto.lower()):
            return iso or None
    return None


def normalizar(
    item: RawItem, agora: datetime, pagina: dict[str, str | list[str]] | None = None
) -> Edital:
    pg = pagina or {}
    titulo = str(pg.get("titulo") or item.titulo)
    corpo = str(pg.get("texto") or item.resumo)
    texto = f"{titulo} {corpo}"
    t = texto.lower()
    formato = next((f for f, rx in _FORMATO if re.search(rx, t)), FormatoOpenCall.outro)
    cobre = [c for c, rx in _COBRE if re.search(rx, t)]
    taxa: float | None = None
    taxa_moeda: str | None = None
    if _GRATUITA.search(texto):
        taxa = 0.0
    elif m := _TAXA.search(texto):
        taxa = float(m.group(2))
        taxa_moeda = {"€": "EUR", "eur": "EUR", "$": "USD", "usd": "USD", "£": "GBP", "gbp": "GBP"}[
            m.group(3).lower()
        ]
    # Prazo só vem do campo "Deadline:" da página; nunca de uma data solta no texto.
    prazo = str(pg["prazo"]) if pg.get("prazo") else None
    link_oficial = str(pg["link_oficial"]) if pg.get("link_oficial") else None
    marcadores = ["coleta:onthemove"]
    if not link_oficial:
        marcadores.append("link_agregador")
    revisao = prazo is None
    paises = [str(p) for p in (pg.get("paises") or [])]
    pais = _pais(item.url, " ".join(paises)) if paises else _pais(item.url, texto)
    mob = str(pg.get("mobilidade") or "")
    modalidade = (
        Modalidade.hibrida
        if "hybrid" in mob
        else Modalidade.online
        if "online" in mob or "virtual" in mob
        else Modalidade.presencial
        if mob
        else None
    )
    if taxa and taxa > 0:
        marcadores.append("com_taxa")
        if not cobre:
            marcadores.append("alerta_taxa")
            revisao = True
    elegivel: bool | None = None
    if re.search(r"\b(international|worldwide|all nationalit|global|latin america)", t):
        elegivel = True
    elif re.search(r"\b(european (artists|citizens|residents)|eu[- ]based|only .* residents)", t):
        elegivel = False
    return Edital(
        id=gerar_id(FONTE, item.url.rstrip("/").rsplit("/", 1)[-1]),
        titulo=titulo,
        orgao=None,
        vertical=Vertical.open_call,
        formato=formato,
        cobre=cobre,
        taxa_inscricao=taxa,
        taxa_moeda=taxa_moeda,
        idiomas=["en"],
        pais_organizador=pais,
        elegivel_brasileiros=elegivel,
        modalidade=modalidade,
        areas=_areas([str(d) for d in (pg.get("disciplinas") or [])]),
        cidades=paises,
        abrangencia=None,
        data_limite=date.fromisoformat(prazo) if prazo else None,
        data_abertura=date.fromisoformat(item.publicado_em) if item.publicado_em else None,
        prazo_texto=(m.group(0).strip() if (m := _SO_PRAZO.search(corpo)) else None),
        resumo=primeira_frase(corpo, 600) if corpo else None,
        link_inscricao=link_oficial or item.url,
        link_edital=item.url,
        fonte=FONTE,
        source_url=item.url,
        captured_at=agora,
        updated_at=agora,
        marcadores=marcadores,
        revisao_pendente=revisao,
    )


class ColetorOnTheMove:
    nome = FONTE

    def __init__(self, xml: str | None = None, paginas: dict[str, str] | None = None) -> None:
        # xml/paginas: fixtures (testes e --simular). None = baixar.
        self._xml = xml
        self._paginas = paginas

    def coletar(self) -> list[Edital]:
        agora = datetime.now(UTC).replace(microsecond=0)
        xml = self._xml if self._xml is not None else baixar(FEED, cache_horas=1)
        saida: list[Edital] = []
        for it in ler_feed(xml):
            pagina: dict[str, str | list[str]] = {}
            try:
                html = (
                    self._paginas.get(it.url, "")
                    if self._paginas is not None
                    else baixar(it.url, cache_horas=24 * 7)
                )
                if html:
                    pagina = ler_pagina(html)
            except OSError as e:
                print(f"[aviso] onthemove {it.url}: {e}")
            saida.append(normalizar(it, agora, pagina))
        return saida
