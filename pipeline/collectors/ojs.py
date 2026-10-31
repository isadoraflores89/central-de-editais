"""Coletor genérico de avisos de revistas em Open Journal Systems (OJS 3).

Cada revista de config/periodicos.yaml tem uma página pública
`<url_base>/announcement` com blocos `obj_announcement_summary` (título, data,
resumo). Só viram oportunidade os avisos que parecem chamada de trabalhos.
O feed RSS de avisos existe no OJS mas quase nenhuma revista o liga, por isso
o coletor lê o HTML.

Nunca inferimos Qualis, APC ou elegibilidade: Qualis e ISSN vêm do
periodicos.yaml (preenchidos à mão); o resto só se estiver no texto.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from typing import Any

from pipeline import config
from pipeline.collectors.base import RawItem, baixar, datas_no_texto, sem_html
from pipeline.enums import FormatoAcademico, Vertical
from pipeline.ids import gerar_id
from pipeline.models import Edital

_BLOCO = re.compile(
    r'<article class="obj_announcement_summary">(.*?)</article>', re.DOTALL | re.IGNORECASE
)
_TITULO = re.compile(r'<h2>\s*<a href="([^"]+)">(.*?)</a>', re.DOTALL)
_DATA = re.compile(r'<div class="date">\s*(\d{4}-\d{2}-\d{2})', re.DOTALL)
_RESUMO = re.compile(r'<div class="summary">(.*?)</div>', re.DOTALL)
_CHAMADA = re.compile(
    r"chamada|call for papers|call for submissions|convocat|submiss|dossi|dossier|"
    r"special issue|n[uú]mero tem[aá]tico|edi[cç][aã]o tem[aá]tica|artigos",
    re.IGNORECASE,
)
_PRAZO = re.compile(
    r"(at[eé]|prazo|deadline|until|submissões até|submissoes ate)[^.]{0,60}", re.IGNORECASE
)
_APC = re.compile(r"\b(apc|taxa de publica[cç][aã]o|article processing charge)\b", re.IGNORECASE)
_SEM_TAXA = re.compile(
    r"(sem (cobran[cç]a|taxa)|n[aã]o cobra|gratuit|free of charge)", re.IGNORECASE
)


def periodicos() -> list[dict[str, Any]]:
    dados = config.ler_yaml(config.CONFIG / "periodicos.yaml")
    return [p for p in (dados or []) if p.get("ativo", True)]


def extrair_avisos(html: str, fonte: str) -> list[RawItem]:
    itens: list[RawItem] = []
    for bloco in _BLOCO.findall(html):
        t = _TITULO.search(bloco)
        if not t:
            continue
        url, titulo = t.group(1).strip(), sem_html(t.group(2))
        d = _DATA.search(bloco)
        r = _RESUMO.search(bloco)
        resumo = sem_html(r.group(1)) if r else ""
        resumo = re.sub(r"\s*Saiba mais.*$", "", resumo).strip()
        if not _CHAMADA.search(titulo + " " + resumo):
            continue
        itens.append(RawItem(fonte, titulo, url, resumo, d.group(1) if d else ""))
    return itens


def _formato(texto: str) -> FormatoAcademico:
    t = texto.lower()
    if "fluxo cont" in t or "rolling" in t:
        return FormatoAcademico.fluxo_continuo_revista
    return FormatoAcademico.dossie_revista


_MAX_DIAS = 365


def recente(item: RawItem, agora: datetime) -> bool:
    """Aviso dos últimos 12 meses e sem ano passado no título (revistas não apagam avisos)."""
    if item.publicado_em:
        try:
            pub = date.fromisoformat(item.publicado_em)
        except ValueError:
            return True
        if (agora.date() - pub).days > _MAX_DIAS:
            return False
    anos = [int(a) for a in re.findall(r"\b(20\d{2})\b", item.titulo)]
    return not anos or max(anos) >= agora.year


def normalizar(item: RawItem, revista: dict[str, Any], agora: datetime) -> Edital:
    texto = f"{item.titulo}. {item.resumo}"
    # Prazo só com contexto ("até", "prazo", "deadline"); nunca uma data solta.
    prazo: str | None = None
    if m := _PRAZO.search(texto):
        futuras = [d for d in datas_no_texto(m.group(0)) if d >= agora.date().isoformat()]
        prazo = futuras[0] if futuras else None
    tema = item.resumo.split(".")[0][:160] if item.resumo else None
    apc: float | None = None
    if _SEM_TAXA.search(texto):
        apc = 0.0
    marcadores = ["coleta:ojs"]
    if _APC.search(texto) and apc is None:
        marcadores.append("com_taxa")
    e = Edital(
        id=gerar_id(item.fonte, item.titulo),
        titulo=item.titulo,
        orgao=str(revista.get("nome") or item.fonte),
        vertical=Vertical.academico,
        formato_academico=_formato(texto),
        periodico=str(revista.get("nome") or ""),
        issn=revista.get("issn"),
        qualis=revista.get("qualis"),
        indexadores=list(revista.get("indexadores") or []),
        apc=apc,
        tema_dossie=tema,
        link_normas=revista.get("link_normas"),
        areas=list(revista.get("areas") or []),
        idiomas=list(revista.get("idiomas") or ["pt"]),
        pais_organizador=str(revista.get("pais") or "BR"),
        abrangencia=None,
        data_resumo=date.fromisoformat(prazo) if prazo else None,
        data_limite=date.fromisoformat(prazo) if prazo else None,
        prazo_texto=(m.group(0).strip() if (m := _PRAZO.search(texto)) else None),
        resumo=item.resumo or None,
        link_inscricao=item.url,
        link_edital=item.url,
        fonte=item.fonte,
        source_url=item.url,
        captured_at=agora,
        updated_at=agora,
        marcadores=marcadores,
        revisao_pendente=prazo is None,
    )
    if item.publicado_em:
        e.data_abertura = date.fromisoformat(item.publicado_em)
    return e


class ColetorOJS:
    nome = "ojs"

    def __init__(self, html_por_revista: dict[str, str] | None = None) -> None:
        # html_por_revista: id da revista -> HTML (fixtures); None = baixar
        self._fixo = html_por_revista

    def coletar(self) -> list[Edital]:
        agora = datetime.now(UTC).replace(microsecond=0)
        saida: list[Edital] = []
        for rev in periodicos():
            fonte = f"ojs:{rev['id']}"
            if self._fixo is not None and rev["id"] not in self._fixo:
                continue  # fixtures: só as revistas salvas
            try:
                html = (
                    self._fixo[rev["id"]]
                    if self._fixo is not None
                    else baixar(rev["url_base"].rstrip("/") + "/announcement")
                )
            except OSError as e:
                print(f"[aviso] {fonte}: {e}")
                continue
            for item in extrair_avisos(html, fonte):
                if recente(item, agora):
                    saida.append(normalizar(item, rev, agora))
        return saida
