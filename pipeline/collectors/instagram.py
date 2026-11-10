"""Agente Instagram: lê posts de contas institucionais e de hashtags pela API oficial da Meta
(Instagram Graph API com login do Facebook) e transforma os que parecem oportunidade em
registros de revisão pendente.

Como funciona
- Contas e hashtags vêm de config/instagram.yaml. Só contas profissionais são legíveis
  (business_discovery). Hashtags: no máximo 30 diferentes por semana, por isso o rodízio.
- Um filtro de palavras-chave descarta posts que claramente não são oportunidade
  (agenda, bastidores). O que sobra vai para a IA (Gemini), que lê a legenda e, quando é
  imagem, o próprio card, e devolve título, órgão, prazo, link, área e estado.
- Segurança: NADA entra como "aberto" sem revisão. O prazo lido fica em `prazo_texto` e em
  `observacoes`; `data_limite` só é preenchido pela curadoria (data/overrides.yaml, campo
  `campos.data_limite`). Até lá o status é "indefinido" e o item não aparece para assinantes.
- Posts já vistos ficam em data/instagram_vistos.json para não gastar IA duas vezes.

Variáveis de ambiente: META_IG_TOKEN (token de usuário de longa duração), META_IG_USER_ID
(conta profissional que faz as consultas; padrão @isadoraprojetos) e GEMINI_API_KEY (opcional;
sem ela, a extração é só por regras e tudo vai para revisão).
"""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any

from pipeline import config
from pipeline.collectors.base import UA, primeira_frase, sem_html
from pipeline.enums import Vertical
from pipeline.ids import gerar_id
from pipeline.models import Edital

FONTE = "instagram"
GRAPH = "https://graph.facebook.com/v27.0"
USER_ID_PADRAO = "17841404465954093"  # @isadoraprojetos
VISTOS = config.DATA / "instagram_vistos.json"
CONFIG = config.CONFIG / "instagram.yaml"

_PALAVRAS = re.compile(
    r"\b(edital|editais|inscri[cç][aã]o|inscri[cç][oõ]es|chamada|chamamento|credenciamento|"
    r"sele[cç][aã]o|pr[eê]mio|premia[cç][aã]o|bolsa|resid[eê]ncia|fomento|patroc[ií]nio|"
    r"rouanet|pnab|aldir blanc|convocat[oó]ria|open call|concurso|cadastro de projetos|"
    r"lei de incentivo|fundo de cultura)\b",
    re.I,
)
_URL = re.compile(r"https?://[^\s)\]]+", re.I)
_DATA_BR = re.compile(
    r"\b(\d{1,2})\s*(?:/|de)\s*(\d{1,2}|janeiro|fevereiro|mar[cç]o|abril|maio|junho|julho|agosto"
    r"|setembro|outubro|novembro|dezembro)\b(?:\s*(?:/|de)\s*(\d{4}))?",
    re.I,
)
_MESES = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "março": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}  # fmt: skip
_UFS = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA",
    "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
}  # fmt: skip
_AREAS = {
    "audiovisual", "musica", "artes_cenicas", "artes_visuais", "literatura", "patrimonio",
    "culturas_populares", "formacao", "economia_criativa", "gestao_cultural", "multi",
}  # fmt: skip

Extrator = Callable[[dict[str, Any]], dict[str, Any] | None]


# ---------- leitura da API ----------
def _get(caminho: str, params: dict[str, str], token: str) -> dict[str, Any]:
    q = urllib.parse.urlencode({**params, "access_token": token}, safe="(){},")
    req = urllib.request.Request(f"{GRAPH}/{caminho}?{q}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        dados: dict[str, Any] = json.loads(r.read().decode("utf-8"))
    if "error" in dados:
        raise OSError(dados["error"].get("message", "erro da Graph API"))
    return dados


def posts_da_conta(usuario: str, user_id: str, token: str, limite: int) -> list[dict[str, Any]]:
    campos = (
        f"business_discovery.username({usuario}){{username,media.limit({limite})"
        "{caption,permalink,timestamp,media_type,media_url,thumbnail_url}}"
    )
    d = _get(user_id, {"fields": campos}, token)
    bd = d.get("business_discovery") or {}
    saida = []
    for m in (bd.get("media") or {}).get("data", []):
        m["conta"] = bd.get("username") or usuario
        saida.append(m)
    return saida


def posts_da_hashtag(tag: str, user_id: str, token: str, limite: int) -> list[dict[str, Any]]:
    d = _get("ig_hashtag_search", {"user_id": user_id, "q": tag}, token)
    ids = [x["id"] for x in d.get("data", [])]
    if not ids:
        return []
    d2 = _get(
        f"{ids[0]}/recent_media",
        {
            "user_id": user_id,
            "fields": "caption,permalink,timestamp,media_type",
            "limit": str(limite),
        },
        token,
    )
    saida = []
    for m in d2.get("data", []):
        m["conta"] = f"#{tag}"
        saida.append(m)
    return saida


# ---------- filtro e extração ----------
def parece_oportunidade(legenda: str) -> bool:
    return bool(legenda) and bool(_PALAVRAS.search(legenda))


def _data(texto: str, ano_base: int) -> str | None:
    m = _DATA_BR.search(texto)
    if not m:
        return None
    dia, mes, ano = m.group(1), m.group(2).lower(), m.group(3)
    mes_n = (
        int(mes) if mes.isdigit() else _MESES.get(mes.replace("ç", "c"), 0) or _MESES.get(mes, 0)
    )
    if not mes_n:
        return None
    try:
        return date(int(ano) if ano else ano_base, mes_n, int(dia)).isoformat()
    except ValueError:
        return None


def extrair_por_regras(post: dict[str, Any]) -> dict[str, Any]:
    """Sem IA: título = primeira frase; prazo = data perto de 'até/prazo'; link = primeira URL."""
    legenda = sem_html(post.get("caption") or "")
    ano = int((post.get("timestamp") or "2026")[:4])
    prazo: str | None = None
    m: re.Match[str] | None = None
    for cand in re.finditer(r"(até|prazo|inscri[cç][oõ]es?)[^.\n]{0,60}", legenda, re.I):
        prazo = _data(cand.group(0), ano)
        if prazo:
            m = cand
            break
    link = next((u for u in _URL.findall(legenda) if "instagram.com" not in u), None)
    return {
        "eh_oportunidade": True,
        "titulo": primeira_frase(legenda, 120).rstrip(".!?…"),
        "orgao": None,
        "resumo": primeira_frase(legenda, 600),
        "data_limite": prazo,
        "prazo_texto": m.group(0).strip() if m else None,
        "link": link,
        "ufs": [],
        "areas": [],
        "abrangencia": None,
        "valor_texto": None,
    }


def _prompt(conta: str, data_post: str, legenda: str) -> str:
    areas = ", ".join(sorted(_AREAS))
    return (
        "Você lê posts do Instagram de instituições culturais brasileiras e identifica "
        "OPORTUNIDADES (editais, chamadas, prêmios, bolsas, residências, credenciamentos, "
        "patrocínios, inscrições abertas).\n"
        "Responda SOMENTE um JSON, sem comentários, no formato:\n"
        '{"eh_oportunidade": true/false, "titulo": "...", "orgao": "...", '
        '"resumo": "até 2 frases", "data_limite": "AAAA-MM-DD ou null", '
        '"prazo_texto": "como o post escreve o prazo, ou null", '
        '"link": "URL do edital/inscrição citada, ou null", "ufs": ["BA"], '
        '"areas": ["musica"], "abrangencia": "nacional|estadual|municipal|internacional|null", '
        '"valor_texto": "..."}\n'
        "Regras: nunca invente data, valor ou link; se o post só divulga resultado, evento ou "
        f"agenda, eh_oportunidade=false. areas só entre: {areas}. ufs só siglas.\n"
        f'Conta: @{conta}. Data do post: {data_post}. Legenda:\n"""{legenda}"""\n'
    )


def _baixar_imagem(url: str, max_bytes: int = 4_000_000) -> tuple[str, str] | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            tipo = r.headers.get_content_type() or "image/jpeg"
            dados = r.read(max_bytes + 1)
        if len(dados) > max_bytes or not tipo.startswith("image/"):
            return None
        return tipo, base64.b64encode(dados).decode("ascii")
    except (OSError, ValueError):
        return None


def extrair_com_gemini(
    post: dict[str, Any], chave: str, modelo: str = "gemini-2.5-flash"
) -> dict[str, Any] | None:
    legenda = sem_html(post.get("caption") or "")[:3000]
    prompt = _prompt(str(post.get("conta", "")), (post.get("timestamp") or "")[:10], legenda)
    partes: list[dict[str, Any]] = [{"text": prompt}]
    if post.get("media_type") == "IMAGE" and post.get("media_url"):
        img = _baixar_imagem(str(post["media_url"]))
        if img:
            partes.append({"inline_data": {"mime_type": img[0], "data": img[1]}})
            partes.append({"text": "A imagem acima é o card do post; use o texto dela também."})
    corpo = {"contents": [{"parts": partes}], "generationConfig": {"temperature": 0.1}}
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
        print(f"[aviso] instagram/gemini: {e}")
        return None
    m = re.search(r"\{.*\}", texto, re.S)
    if not m:
        return None
    try:
        dados: dict[str, Any] = json.loads(m.group(0))
    except ValueError:
        return None
    return dados


# ---------- normalização ----------
def normalizar(post: dict[str, Any], dados: dict[str, Any], agora: datetime) -> Edital | None:
    if not dados.get("eh_oportunidade"):
        return None
    titulo = sem_html(str(dados.get("titulo") or "")).strip()
    if len(titulo) < 8:
        return None
    permalink = str(post.get("permalink") or "")
    link = str(dados.get("link") or "").strip() or None
    if link and "instagram.com" in link:
        link = None
    prazo = dados.get("data_limite")
    prazo_txt = dados.get("prazo_texto")
    obs = [f"Lido do Instagram (@{post.get('conta', '')}) em {(post.get('timestamp') or '')[:10]}."]
    if prazo:
        obs.append(
            f"Prazo lido no post: {prazo}. Confirme na fonte e aprove com campos.data_limite."
        )
    if not link:
        obs.append("Sem link oficial no post: procure o edital no site da instituição.")
    marcadores = ["coleta:instagram", "aguardando_aprovacao"]
    if not link:
        marcadores.append("link_instagram")
    ufs = [u for u in (dados.get("ufs") or []) if u in _UFS]
    areas = [a for a in (dados.get("areas") or []) if a in _AREAS]
    conta = str(post.get("conta") or "")
    orgao = (dados.get("orgao") or (None if conta.startswith("#") else conta)) or None
    return Edital(
        id=gerar_id(FONTE, permalink.rstrip("/").rsplit("/", 1)[-1] or titulo),
        titulo=titulo[:160],
        orgao=orgao,
        vertical=Vertical.fomento,
        idiomas=["pt"],
        pais_organizador="BR",
        ufs=ufs,
        areas=areas,
        abrangencia=dados.get("abrangencia")
        if dados.get("abrangencia")
        in ("nacional", "estadual", "municipal", "internacional", "regional")
        else None,
        valor_texto=(dados.get("valor_texto") or None),
        prazo_texto=(str(prazo_txt) if prazo_txt else (f"até {prazo}" if prazo else None)),
        data_limite=None,  # só pela curadoria (overrides.yaml); ver docstring
        resumo=sem_html(str(dados.get("resumo") or ""))[:600] or None,
        link_inscricao=link,
        link_edital=link or permalink,
        observacoes=" ".join(obs),
        imagem=str(post.get("media_url") or post.get("thumbnail_url") or "") or None,
        imagem_verificada_em=agora,
        fonte=FONTE,
        source_url=permalink or f"https://www.instagram.com/{conta.lstrip('#')}/",
        captured_at=agora,
        updated_at=agora,
        marcadores=marcadores,
        revisao_pendente=True,
    )


# ---------- coletor ----------
def _carregar_vistos() -> dict[str, str]:
    try:
        d = json.loads(VISTOS.read_text(encoding="utf-8"))
        return {str(k): str(v) for k, v in d.items()} if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _salvar_vistos(v: dict[str, str], agora: datetime) -> None:
    limite = (agora - timedelta(days=60)).date().isoformat()
    v = {k: d for k, d in v.items() if d >= limite}
    VISTOS.parent.mkdir(parents=True, exist_ok=True)
    VISTOS.write_text(json.dumps(v, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")


class ColetorInstagram:
    nome = FONTE

    def __init__(
        self,
        posts: list[dict[str, Any]] | None = None,
        extrator: Extrator | None = None,
        cfg: dict[str, Any] | None = None,
        guardar_vistos: bool = True,
    ) -> None:
        # posts/extrator: injeção para testes e --simular (sem rede).
        self._posts = posts
        self._extrator = extrator
        self._cfg = cfg
        self._guardar = guardar_vistos

    def _config(self) -> dict[str, Any]:
        if self._cfg is not None:
            return self._cfg
        return config.ler_yaml(CONFIG) or {}

    def _buscar(self, cfg: dict[str, Any], agora: datetime) -> list[dict[str, Any]]:
        if self._posts is not None:
            return list(self._posts)
        token = os.environ.get("META_IG_TOKEN", "").strip()
        if not token:
            raise OSError("META_IG_TOKEN não definido; agente Instagram pulado")
        user_id = os.environ.get("META_IG_USER_ID", USER_ID_PADRAO).strip()
        por_conta = int(cfg.get("posts_por_conta", 8))
        saida: list[dict[str, Any]] = []
        for conta in cfg.get("contas") or []:
            try:
                saida.extend(posts_da_conta(str(conta), user_id, token, por_conta))
            except (OSError, ValueError) as e:
                print(f"[aviso] instagram @{conta}: {e}")
        tags = [str(t).lstrip("#") for t in (cfg.get("hashtags") or [])]
        n = int(cfg.get("hashtags_por_rodada", 4))
        if tags and n > 0:
            # rodízio diário: dia do ano escolhe a janela
            i = (agora.timetuple().tm_yday * n) % len(tags)
            escolhidas = (tags + tags)[i : i + n]
            for tag in escolhidas:
                try:
                    saida.extend(posts_da_hashtag(tag, user_id, token, 25))
                except (OSError, ValueError) as e:
                    print(f"[aviso] instagram #{tag}: {e}")
        return saida

    def coletar(self) -> list[Edital]:
        agora = datetime.now(UTC).replace(microsecond=0)
        cfg = self._config()
        dias = int(cfg.get("dias", 4))
        corte = (agora - timedelta(days=dias)).isoformat()
        vistos = _carregar_vistos() if self._guardar else {}
        extrator = self._extrator
        if extrator is None:
            chave = os.environ.get("GEMINI_API_KEY", "").strip()
            extrator = (lambda p: extrair_com_gemini(p, chave)) if chave else extrair_por_regras
        max_ia = int(cfg.get("max_posts_ia", 25))
        saida: list[Edital] = []
        usados = 0
        falhas = 0
        candidatos = 0
        for post in self._buscar(cfg, agora):
            link = str(post.get("permalink") or "")
            ts = str(post.get("timestamp") or "")
            if not link or (ts and ts < corte) or link in vistos:
                continue
            if not parece_oportunidade(post.get("caption") or ""):
                vistos[link] = agora.date().isoformat()
                continue
            if usados >= max_ia:
                break
            usados += 1
            candidatos += 1
            dados = extrator(post)
            if dados is None:
                # IA fora do ar ou resposta inválida: cai para as regras e NÃO marca como visto,
                # para a IA tentar de novo na próxima rodada.
                falhas += 1
                dados = extrair_por_regras(post)
            else:
                vistos[link] = agora.date().isoformat()
            e = normalizar(post, dados, agora)
            if e is not None:
                saida.append(e)
        print(
            f"[instagram] {candidatos} candidatos lidos pela IA, {falhas} falhas da IA "
            f"(regras no lugar), {len(saida)} oportunidades para revisão"
        )
        if self._guardar:
            _salvar_vistos(vistos, agora)
        return saida
