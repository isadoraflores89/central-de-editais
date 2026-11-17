"""Leitura de UMA página de oportunidade (edital, chamada, convocatória, open call) e
transformação em Edital. Compartilhado pelo vigia de páginas (paginas.py) e pela busca na
web (busca_web.py).

Como funciona
- `texto_da_pagina(html)` tira o HTML e limita o tamanho.
- `extrair_com_gemini(ctx, chave)` pede à IA um JSON com os campos do edital a partir do texto.
  Sem chave (ou com falha), `extrair_por_regras(ctx)` monta o mínimo: título do link,
  resumo = primeiras frases, prazo = data logo depois de "até"/"prazo"/"inscrições".
- `normalizar(ctx, dados, agora)` valida tudo antes de gravar. Segurança contra invenção:
  a data-limite só é aceita se aparece escrita no texto da página (datas_no_texto); senão
  vira prazo_texto + observação e o item fica como revisão pendente (status indefinido,
  não aparece para assinantes até a curadoria confirmar em data/overrides.yaml).

Palavras-chave (PT, ES, EN, FR) em `PALAVRAS`: usadas pelos dois buscadores para decidir
se um link ou texto parece oportunidade.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from urllib.parse import urlsplit

from pipeline.collectors.base import UA, datas_no_texto, primeira_frase, sem_html
from pipeline.enums import Abrangencia, Mecanismo, Proponente, TipoApoio, Vertical
from pipeline.ids import gerar_id
from pipeline.models import Edital

MODELO = "gemini-2.5-flash"
MAX_TEXTO = 14_000

# o que, num link ou título, parece oportunidade (pt / es / en / fr)
PALAVRAS = re.compile(
    r"\b(edital|editais|chamada|chamamento|chamadas|sele[cç][aã]o p[uú]blica|credenciamento|"
    r"pr[eê]mio|premia[cç][aã]o|concurso|bolsa|resid[eê]ncia|inscri[cç][oõ]es|inscri[cç][aã]o|"
    r"convocat[oó]ria|convocatoria|fomento|patroc[ií]nio|patrocinio|cadastro de projetos|"
    r"chamada p[uú]blica|fundo|fondo|fondos|est[ií]mulos|becas|beca|ayudas|subvenci[oó]n|"
    r"subvenciones|open call|call for (proposals|applications|artists|entries|projects)|"
    r"calls?\b|grants?\b|funding|residenc(y|ies)|fellowship|mobility|bursary|"
    r"appel [àa] (projets|candidatures)|bourse|r[eé]sidence|subsidies?|apoios?|concursos?|"
    r"candidaturas?|oportunidades?|rouanet|pnab|aldir blanc)\b",
    re.I,
)
# o que, num link, NÃO interessa mesmo tendo a palavra (resultado, encerrado, notícia velha)
RUIDO = re.compile(
    r"\b(resultados?|encerrad\w*|homologa\w*|gabarito|retifica[cç][aã]o|errata|"
    r"closed|results?|archive|arquivo|fechad\w*|cerrad\w*|finalizad\w*|winners?|vencedor\w*)\b",
    re.I,
)
_UFS = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA",
    "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
}  # fmt: skip
_AREAS = {
    "audiovisual", "musica", "artes_cenicas", "artes_visuais", "literatura", "patrimonio",
    "culturas_populares", "formacao", "economia_criativa", "gestao_cultural", "multi",
}  # fmt: skip
_MECANISMOS = {m.value for m in Mecanismo}
_TIPOS = {t.value for t in TipoApoio}
_PROPONENTES = {p.value for p in Proponente}
_ABRANGENCIAS = {a.value for a in Abrangencia}
_PLATAFORMAS = (
    "prosas.com.br", "mapa.cultura.gov.br", "mapas.cultura.gov.br", "salic.cultura.gov.br",
    "gov.br", "sympla.com.br", "filmfreeway.com", "festhome.com", "docs.google.com",
    "forms.gle", "ec.europa.eu", "europa.eu",
)  # fmt: skip


@dataclass
class Contexto:
    """O que sabemos de uma página antes da IA: de onde veio e o que está escrito."""

    url: str
    texto: str
    fonte_id: str
    fonte_nome: str
    titulo_link: str = ""
    pais: str | None = "BR"
    uf: str | None = None
    abrangencia: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


Extrator = Callable[[Contexto], dict[str, Any] | None]


def texto_da_pagina(html: str, maximo: int = MAX_TEXTO) -> str:
    h = re.sub(
        r"<(script|style|nav|footer|header|noscript)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I
    )
    return sem_html(h)[:maximo]


def parece_oportunidade(texto: str) -> bool:
    return bool(texto) and bool(PALAVRAS.search(texto)) and not RUIDO.search(texto[:120])


def mesmo_dominio(a: str, b: str) -> bool:
    try:
        ha, hb = urlsplit(a).netloc.lower(), urlsplit(b).netloc.lower()
    except ValueError:
        return False
    ha, hb = ha.removeprefix("www."), hb.removeprefix("www.")
    return bool(ha) and (ha == hb or ha.endswith("." + hb) or hb.endswith("." + ha))


def link_confiavel(link: str, origem: str) -> bool:
    if mesmo_dominio(link, origem):
        return True
    host = urlsplit(link).netloc.lower()
    return any(host == p or host.endswith("." + p) for p in _PLATAFORMAS)


# ---------- extração ----------
def _prompt(ctx: Contexto) -> str:
    return (
        "Você lê páginas de instituições culturais (Brasil, América Latina e Europa) e extrai "
        "OPORTUNIDADES para artistas, produtores e organizações culturais: editais, chamadas, "
        "convocatórias, prêmios, bolsas, residências, credenciamentos, patrocínios, open calls.\n"
        "Responda SOMENTE um JSON, sem comentários, no formato:\n"
        '{"eh_oportunidade": true/false, "titulo": "título curto e claro, sem caixa alta", '
        '"orgao": "instituição responsável", "resumo": "até 1000 caracteres, em português, '
        'dizendo o que é, para quem, quanto paga e como se inscreve", '
        '"data_limite": "AAAA-MM-DD ou null", '
        '"prazo_texto": "como a página escreve o prazo, ou null", '
        '"data_abertura": "AAAA-MM-DD ou null", "fluxo_continuo": true/false, '
        '"link_inscricao": "URL para se inscrever ou do edital, ou null", '
        f'"abrangencia": "{"|".join(sorted(_ABRANGENCIAS))}|null", '
        '"ufs": ["BA"], "cidades": ["Salvador"], '
        f'"areas": ["{"|".join(sorted(_AREAS))}"], '
        f'"mecanismo": ["{"|".join(sorted(_MECANISMOS))}"], '
        f'"tipo_apoio": "{"|".join(sorted(_TIPOS))}|null", '
        f'"proponente": ["{"|".join(sorted(_PROPONENTES))}"], '
        '"valor_texto": "valores como escritos, ou null", "valor_min": número ou null, '
        '"valor_max": número ou null, "moeda": "BRL|EUR|USD|...", '
        '"elegivel_brasileiros": true/false/null, "idioma": "pt|es|en|fr", '
        '"encerrado": true/false}\n'
        "Regras: nunca invente data, valor, órgão ou link; o que não está no texto fica null. "
        "Se a página é lista de vários editais, notícia de resultado, página institucional "
        "genérica ou edital já encerrado, eh_oportunidade=false (ou encerrado=true). "
        "ufs só siglas; areas, mecanismo, tipo_apoio e proponente só entre as opções dadas.\n"
        f"Fonte: {ctx.fonte_nome} (país {ctx.pais or '?'}). Título do link: {ctx.titulo_link!r}. "
        f'URL: {ctx.url}\nTexto da página:\n"""{ctx.texto}"""'
    )


def extrair_com_gemini(ctx: Contexto, chave: str, modelo: str = MODELO) -> dict[str, Any] | None:
    corpo = {
        "contents": [{"parts": [{"text": _prompt(ctx)}]}],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={chave}"
    req = urllib.request.Request(
        url,
        data=json.dumps(corpo).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": UA},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.loads(r.read().decode("utf-8"))
        texto = "".join(p.get("text", "") for p in resp["candidates"][0]["content"]["parts"])
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError) as e:
        print(f"[aviso] oportunidade/gemini {ctx.url}: {e}")
        return None
    m = re.search(r"\{.*\}", texto, re.S)
    if not m:
        return None
    try:
        dados: dict[str, Any] = json.loads(m.group(0))
    except ValueError:
        return None
    return dados


_PRAZO = re.compile(
    r"(at[eé]|prazo|inscri[cç][oõ]es?|deadline|until|hasta|plazo|jusqu)[^.\n]{0,80}", re.I
)


def extrair_por_regras(ctx: Contexto) -> dict[str, Any]:
    """Sem IA: título = texto do link ou primeira frase; prazo = data perto de 'até/prazo'."""
    titulo = ctx.titulo_link.strip() or primeira_frase(ctx.texto, 120)
    prazo: str | None = None
    prazo_txt: str | None = None
    hoje = date.today().isoformat()
    for m in _PRAZO.finditer(ctx.texto):
        datas = [d for d in datas_no_texto(m.group(0)) if d >= hoje]
        if datas:
            # num período "de X até Y", a última data é o fim das inscrições
            prazo, prazo_txt = datas[-1], m.group(0).strip()
            break
    # sem IA, só entra o que tem prazo lido ou título que claramente anuncia uma chamada
    eh = bool(prazo) or bool(re.search(r"inscri|edital|chamada|convocat|open call", titulo, re.I))
    return {
        "eh_oportunidade": eh,
        "titulo": titulo.rstrip(".!?…"),
        "orgao": ctx.fonte_nome,
        "resumo": primeira_frase(ctx.texto, 600),
        "data_limite": prazo,
        "prazo_texto": prazo_txt,
        "link_inscricao": None,
        "ufs": [ctx.uf] if ctx.uf else [],
        "areas": [],
        "abrangencia": ctx.abrangencia,
        "mecanismo": [],
        "proponente": [],
        "valor_texto": None,
        "encerrado": False,
    }


# ---------- normalização ----------
def _data(v: Any) -> date | None:
    try:
        return date.fromisoformat(str(v)[:10]) if v else None
    except ValueError:
        return None


def _num(v: Any) -> float | None:
    try:
        return float(v) if v not in (None, "", False) else None
    except (TypeError, ValueError):
        return None


def normalizar(
    ctx: Contexto, dados: dict[str, Any], agora: datetime, marcador: str
) -> Edital | None:
    if not dados.get("eh_oportunidade") or dados.get("encerrado"):
        return None
    titulo = sem_html(str(dados.get("titulo") or "")).strip()
    if len(titulo) < 8:
        return None
    link = str(dados.get("link_inscricao") or "").strip() or None
    if link and not link.lower().startswith("http"):
        link = None
    datas_pagina = set(datas_no_texto(ctx.texto))
    prazo = _data(dados.get("data_limite"))
    prazo_txt = str(dados.get("prazo_texto") or "").strip() or None
    obs: list[str] = [f"Lido de {ctx.fonte_nome} em {agora.date().isoformat()} pelo buscador."]
    marcadores = [marcador, f"fonte:{ctx.fonte_id}"]
    revisao = False
    hoje = agora.date()
    if prazo is not None and (prazo.isoformat() not in datas_pagina or prazo < hoje):
        # a IA disse uma data que não está escrita na página (ou já passou): não confiamos
        obs.append(
            f"Prazo sugerido pela leitura automática: {prazo.isoformat()} "
            "(não confirmado no texto)."
        )
        prazo_txt = prazo_txt or prazo.isoformat()
        prazo = None
    fluxo = bool(dados.get("fluxo_continuo")) and prazo is None
    if prazo is None and not fluxo:
        revisao = True
        marcadores.append("aguardando_aprovacao")
        obs.append("Sem prazo confirmado: confira na fonte e aprove com campos.data_limite.")
    if link and not link_confiavel(link, ctx.url):
        marcadores.append("link_externo")
    ufs = [u for u in (dados.get("ufs") or []) if isinstance(u, str) and u.upper() in _UFS]
    areas = [a for a in (dados.get("areas") or []) if a in _AREAS]
    mec = [Mecanismo(m) for m in (dados.get("mecanismo") or []) if m in _MECANISMOS]
    prop = [Proponente(p) for p in (dados.get("proponente") or []) if p in _PROPONENTES]
    tipo = dados.get("tipo_apoio")
    abr = dados.get("abrangencia") or ctx.abrangencia
    internacional = (ctx.pais or "BR") != "BR" or abr == "internacional"
    if internacional and not abr:
        abr = "internacional"
    if not internacional and not abr:
        abr = "estadual" if ufs else "nacional"
    if not internacional and not ufs and ctx.uf and abr in ("estadual", "municipal"):
        ufs = [ctx.uf]
    idioma = str(dados.get("idioma") or ("pt" if not internacional else "en"))[:2]
    eleg = dados.get("elegivel_brasileiros")
    return Edital(
        id=gerar_id(ctx.fonte_id, ctx.url),
        titulo=titulo,
        orgao=(str(dados.get("orgao") or "").strip() or ctx.fonte_nome)[:200],
        vertical=Vertical.open_call if internacional else Vertical.fomento,
        tipo_apoio=TipoApoio(tipo) if tipo in _TIPOS else None,
        mecanismo=mec,
        abrangencia=Abrangencia(abr) if abr in _ABRANGENCIAS else None,
        ufs=[u.upper() for u in ufs],
        cidades=[str(c) for c in (dados.get("cidades") or []) if isinstance(c, str)][:5],
        areas=areas,
        proponente=prop,
        idiomas=[idioma],
        pais_organizador=(ctx.pais if ctx.pais and len(ctx.pais) == 2 else None),
        elegivel_brasileiros=eleg if isinstance(eleg, bool) else None,
        valor_por_projeto_min=_num(dados.get("valor_min")),
        valor_por_projeto_max=_num(dados.get("valor_max")),
        valor_texto=(str(dados.get("valor_texto") or "").strip() or None),
        moeda=(str(dados.get("moeda") or "").strip().upper()[:3] or None)
        if internacional
        else None,
        prazo_texto=prazo_txt,
        data_limite=prazo,
        fluxo_continuo=fluxo,
        data_abertura=_data(dados.get("data_abertura")),
        resumo=(sem_html(str(dados.get("resumo") or "")).strip()[:1000] or None),
        link_inscricao=link or ctx.url,
        link_edital=ctx.url,
        observacoes=" ".join(obs),
        fonte=ctx.fonte_id,
        source_url=ctx.url,
        captured_at=agora,
        updated_at=agora,
        marcadores=marcadores,
        revisao_pendente=revisao,
    )
