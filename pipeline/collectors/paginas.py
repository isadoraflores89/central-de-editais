"""Vigia de páginas: lê as páginas de editais das fontes cadastradas (config/fontes.yaml, gerado
das planilhas em config/fontes/) e transforma links novos que parecem oportunidade em registros.

Como funciona, a cada rodada (diária no GitHub Actions)
1. Escolhe as fontes do dia: ativas, método "pagina"; as diárias sempre, as semanais em
   rodízio (cada uma cai num dia da semana), para não baixar 180 páginas por dia.
2. Baixa a página de editais de cada fonte (com cache, robots.txt e intervalo entre pedidos)
   e lista os links cujo texto ou endereço tem palavra de oportunidade (edital, chamada,
   convocatória, open call, grant, residência...) e não tem palavra de ruído (resultado,
   encerrado, errata...).
3. Links nunca vistos (data/fontes_vistos.json) são abertos, no máximo N por fonte e M por rodada
   (config/buscador.yaml). O texto vai para a IA (pipeline/collectors/oportunidade.py), que
   devolve título, órgão, prazo, valores, áreas e estados. Sem GEMINI_API_KEY, vale a leitura
   por regras.
4. Segurança: prazo só é aceito se está escrito na página; sem prazo confirmado, o item entra
   como revisão pendente (status indefinido) e não aparece para assinantes até a curadoria
   confirmar em data/overrides.yaml.

Uso: `uv run python -m pipeline collect --fonte paginas` (ou tudo: `make collect`).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

from pipeline import config
from pipeline.collectors.base import baixar, sem_html
from pipeline.collectors.oportunidade import (
    RUIDO,
    Contexto,
    Extrator,
    extrair_com_gemini,
    extrair_por_regras,
    normalizar,
    parece_oportunidade,
    texto_da_pagina,
)
from pipeline.models import Edital

FONTE = "paginas"
FONTES_YAML = config.CONFIG / "fontes.yaml"
CONFIG_YAML = config.CONFIG / "buscador.yaml"
VISTOS = config.DATA / "fontes_vistos.json"

_A = re.compile(r"<a\b[^>]*?href\s*=\s*[\"']([^\"'#]+)[\"'][^>]*>(.*?)</a>", re.I | re.S)
_BINARIO = re.compile(r"\.(pdf|docx?|xlsx?|pptx?|zip|rar|jpe?g|png|gif|mp4|mp3)(\?|$)", re.I)
_NAO_PAGINA = re.compile(r"^(mailto:|tel:|javascript:|whatsapp:)", re.I)
# blocos de navegação (menus, rodapé, barras laterais) não entram na busca de links
_MENUS = re.compile(r"<(nav|header|footer|aside)\b[^>]*>.*?</\1>", re.I | re.S)
# caminhos administrativos que têm a palavra "edital" mas não são oportunidade cultural
_CAMINHO_RUIDO = re.compile(
    r"acesso-a-informacao|perguntas-frequentes|licitacoes-e-contratos|movimentacao|"
    r"transparencia|servidor|concursos-publicos|rh\.|/lai\b|institucional/|sobre-|"
    r"login|cadastro-de-usuario|politica-de-privacidade",
    re.I,
)


def carregar_fontes() -> list[dict[str, Any]]:
    dados = config.ler_yaml(FONTES_YAML)
    return [f for f in (dados or []) if isinstance(f, dict) and f.get("url")]


def carregar_config() -> dict[str, Any]:
    dados = config.ler_yaml(CONFIG_YAML) or {}
    return dict(dados.get("paginas") or {}) if isinstance(dados, dict) else {}


def fontes_do_dia(fontes: list[dict[str, Any]], dia: datetime) -> list[dict[str, Any]]:
    """Diárias sempre; semanais caem num dia fixo da semana (pelo id), espalhando a carga."""
    saida = []
    for f in fontes:
        if not f.get("ativo", True) or f.get("metodo", "pagina") != "pagina":
            continue
        if f.get("frequencia") == "semanal":
            dia_da_fonte = int(hashlib.sha1(str(f["id"]).encode()).hexdigest(), 16) % 7
            if dia_da_fonte != dia.weekday():
                continue
        saida.append(f)
    saida.sort(key=lambda f: -int(f.get("prioridade", 1)))
    return saida


def url_limpa(url: str) -> str:
    p = urlsplit(url)
    query = "&".join(
        q for q in p.query.split("&") if q and not q.lower().startswith(("utm_", "fbclid"))
    )
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/") or "/", query, ""))


def links_candidatos(html: str, base: str, maximo: int = 40) -> list[tuple[str, str]]:
    """(url, texto do link) dos links que parecem oportunidade, na ordem da página, sem repetir."""
    saida: list[tuple[str, str]] = []
    vistos: set[str] = set()
    base_limpa = url_limpa(base)
    corpo = _MENUS.sub(" ", html)
    for m in _A.finditer(corpo if _A.search(corpo) else html):
        href, rotulo = m.group(1).strip(), sem_html(m.group(2))
        if _NAO_PAGINA.match(href) or _BINARIO.search(href):
            continue
        url = urljoin(base, href)
        if not url.lower().startswith("http"):
            continue
        url = url_limpa(url)
        if url == base_limpa or url in vistos or _CAMINHO_RUIDO.search(url):
            continue
        caminho = urlsplit(url).path.replace("-", " ").replace("_", " ").replace("/", " ")
        if (
            len(rotulo) < 6
            or not parece_oportunidade(f"{rotulo} {caminho}")
            or RUIDO.search(rotulo)
        ):
            continue
        vistos.add(url)
        saida.append((url, rotulo[:200]))
        if len(saida) >= maximo:
            break
    return saida


def _carregar_vistos() -> dict[str, str]:
    try:
        dados = json.loads(VISTOS.read_text(encoding="utf-8")) if VISTOS.exists() else {}
        return {str(k): str(v) for k, v in dados.items()} if isinstance(dados, dict) else {}
    except ValueError:
        return {}


def _salvar_vistos(v: dict[str, str], agora: datetime, dias: int = 180) -> None:
    limite = (agora - timedelta(days=dias)).date().isoformat()
    v = {k: d for k, d in v.items() if d >= limite}
    VISTOS.parent.mkdir(parents=True, exist_ok=True)
    VISTOS.write_text(json.dumps(v, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")


class ColetorPaginas:
    nome = FONTE

    def __init__(
        self,
        fontes: list[dict[str, Any]] | None = None,
        paginas: dict[str, str] | None = None,
        extrator: Extrator | None = None,
        cfg: dict[str, Any] | None = None,
        guardar_vistos: bool = True,
        agora: datetime | None = None,
    ) -> None:
        # fontes/paginas/extrator: injeção para testes e --simular (sem rede nem IA).
        self._fontes = fontes
        self._paginas = paginas
        self._extrator = extrator
        self._cfg = cfg
        self._guardar = guardar_vistos
        self._agora = agora

    def _baixar(self, url: str, cache_horas: float) -> str:
        if self._paginas is not None:
            return self._paginas.get(url, "")
        return baixar(url, cache_horas=cache_horas)

    def coletar(self) -> list[Edital]:
        agora = self._agora or datetime.now(UTC).replace(microsecond=0)
        cfg = self._cfg if self._cfg is not None else carregar_config()
        max_por_fonte = int(cfg.get("max_por_fonte", 6))
        max_ia = int(cfg.get("max_ia", 60))
        cache_lista = float(cfg.get("cache_horas", 6))
        fontes = fontes_do_dia(
            self._fontes if self._fontes is not None else carregar_fontes(), agora
        )
        vistos = _carregar_vistos() if self._guardar else {}
        extrator = self._extrator
        chave = os.environ.get("GEMINI_API_KEY", "").strip()
        if extrator is None:
            extrator = (lambda c: extrair_com_gemini(c, chave)) if chave else extrair_por_regras
        saida: list[Edital] = []
        lidos = falhas = fontes_ok = fontes_erro = 0
        for f in fontes:
            if lidos >= max_ia:
                break
            try:
                html = self._baixar(str(f["url"]), cache_lista)
            except OSError as e:
                fontes_erro += 1
                print(f"[aviso] paginas {f['id']}: {e}")
                continue
            if not html:
                fontes_erro += 1
                continue
            fontes_ok += 1
            novos = 0
            for url, rotulo in links_candidatos(html, str(f["url"])):
                if url in vistos or novos >= max_por_fonte or lidos >= max_ia:
                    continue
                try:
                    pagina = self._baixar(url, 24 * 7)
                except OSError as exc:
                    print(f"[aviso] paginas {f['id']} {url}: {exc}")
                    vistos[url] = agora.date().isoformat()
                    continue
                texto = texto_da_pagina(pagina)
                if len(texto) < 200:
                    vistos[url] = agora.date().isoformat()
                    continue
                novos += 1
                lidos += 1
                ctx = Contexto(
                    url=url,
                    texto=texto,
                    fonte_id=str(f["id"]),
                    fonte_nome=str(f.get("nome") or f["id"]),
                    titulo_link=rotulo,
                    pais=f.get("pais")
                    or ("BR" if f.get("abrangencia") != "internacional" else None),
                    uf=f.get("uf"),
                    abrangencia=f.get("abrangencia"),
                )
                dados = extrator(ctx)
                if dados is None:
                    # IA fora do ar: regras no lugar e NÃO marca como visto (tenta de novo amanhã)
                    falhas += 1
                    dados = extrair_por_regras(ctx)
                else:
                    vistos[url] = agora.date().isoformat()
                ed = normalizar(ctx, dados, agora, "coleta:pagina")
                if ed is not None:
                    saida.append(ed)
        print(
            f"[paginas] {fontes_ok} fontes lidas ({fontes_erro} com erro), {lidos} páginas novas "
            f"lidas pela IA ({falhas} falhas), {len(saida)} oportunidades"
        )
        if self._guardar:
            _salvar_vistos(vistos, agora)
        return saida
