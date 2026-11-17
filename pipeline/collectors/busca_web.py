"""Busca na web: pergunta ao Google, todo dia, por oportunidades culturais abertas usando as
palavras-chave de config/buscador.yaml (português, espanhol, inglês, francês), em rodízio.

Dois motores, escolhidos pelas variáveis de ambiente:
- Google Programmable Search (GOOGLE_CSE_KEY + GOOGLE_CSE_ID): 100 consultas grátis por dia,
  resultados reais do Google (10 por consulta).
- Sem elas, Gemini com Google Search grounding (GEMINI_API_KEY): a mesma busca que o radar
  de festivais e o de vagas já usam. A IA devolve links; nunca confiamos no que ela diz sem
  abrir a página.

Cada link novo (data/busca_vistos.json) é aberto e lido pelo mesmo leitor do vigia de páginas
(pipeline/collectors/oportunidade.py), com a mesma regra: prazo só vale se está escrito na
página; senão, revisão pendente.

Uso: `uv run python -m pipeline collect --fonte busca_web`.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from pipeline import config
from pipeline.collectors.base import UA, baixar
from pipeline.collectors.oportunidade import (
    RUIDO,
    Contexto,
    Extrator,
    extrair_com_gemini,
    extrair_por_regras,
    normalizar,
    texto_da_pagina,
)
from pipeline.collectors.paginas import url_limpa
from pipeline.models import Edital

FONTE = "busca_web"
CONFIG_YAML = config.CONFIG / "buscador.yaml"
VISTOS = config.DATA / "busca_vistos.json"
MODELO = "gemini-2.5-flash"
ESTADOS = {
    "AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá", "BA": "Bahia", "CE": "Ceará",
    "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão",
    "MG": "Minas Gerais", "MS": "Mato Grosso do Sul", "MT": "Mato Grosso", "PA": "Pará",
    "PB": "Paraíba", "PE": "Pernambuco", "PI": "Piauí", "PR": "Paraná", "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte", "RO": "Rondônia", "RR": "Roraima", "RS": "Rio Grande do Sul",
    "SC": "Santa Catarina", "SE": "Sergipe", "SP": "São Paulo", "TO": "Tocantins",
}  # fmt: skip
_IGNORAR_HOSTS = (
    "instagram.com", "facebook.com", "youtube.com", "twitter.com", "x.com", "linkedin.com",
    "tiktok.com", "wikipedia.org", "google.com", "pinterest.com",
)  # fmt: skip

# um resultado de busca: link + o que o motor disse dele
Resultado = dict[str, str]
Motor = Callable[[str], list[Resultado]]


def carregar_config() -> dict[str, Any]:
    dados = config.ler_yaml(CONFIG_YAML) or {}
    return dict(dados.get("busca_web") or {}) if isinstance(dados, dict) else {}


def consultas_do_dia(cfg: dict[str, Any], dia: datetime) -> list[dict[str, Any]]:
    """Rodízio: N consultas fixas por dia + 2 estados por dia (todos a cada ~2 semanas)."""
    fixas = [c for c in (cfg.get("consultas") or []) if isinstance(c, dict) and c.get("q")]
    n = int(cfg.get("consultas_por_dia", 6))
    saida: list[dict[str, Any]] = []
    if fixas and n > 0:
        i = (dia.timetuple().tm_yday * n) % len(fixas)
        saida.extend((fixas + fixas)[i : i + min(n, len(fixas))])
    modelo_uf = str(cfg.get("consulta_por_estado") or "")
    por_dia = int(cfg.get("estados_por_dia", 2))
    if modelo_uf and por_dia > 0:
        ufs = sorted(ESTADOS)
        i = (dia.timetuple().tm_yday * por_dia) % len(ufs)
        for uf in (ufs + ufs)[i : i + por_dia]:
            saida.append({"q": modelo_uf.format(estado=ESTADOS[uf], uf=uf), "pais": "BR", "uf": uf})
    return saida


# ---------- motores ----------
def motor_google_cse(chave: str, cx: str) -> Motor:
    def buscar(q: str) -> list[Resultado]:
        params = urllib.parse.urlencode(
            {"key": chave, "cx": cx, "q": q, "num": 10, "lr": "", "safe": "off"}
        )
        req = urllib.request.Request(
            f"https://www.googleapis.com/customsearch/v1?{params}", headers={"User-Agent": UA}
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            dados = json.loads(r.read().decode("utf-8"))
        return [
            {
                "link": it.get("link", ""),
                "titulo": it.get("title", ""),
                "resumo": it.get("snippet", ""),
            }
            for it in dados.get("items", [])
        ]

    return buscar


def _prompt_busca(q: str, hoje: str) -> str:
    return (
        f"Hoje é {hoje}. Pesquise na web: {q}\n"
        "Liste oportunidades ABERTAS agora (prazo no futuro ou não informado) para artistas, "
        "produtores e organizações culturais: editais, chamadas, convocatórias, prêmios, bolsas, "
        "residências, credenciamentos, patrocínios. Só com página oficial (instituição, diário "
        "oficial ou plataforma de inscrição). Nunca invente. Sem emojis. Até 12 itens.\n"
        "Responda APENAS um bloco ```json``` com um array de objetos "
        '{"titulo": "...", "orgao": "...", "link": "URL da página oficial", '
        '"prazo": "AAAA-MM-DD ou \\"\\"", "resumo": "uma frase"}.'
    )


def motor_gemini(chave: str, modelo: str = MODELO) -> Motor:
    def buscar(q: str) -> list[Resultado]:
        corpo = {
            "contents": [
                {"parts": [{"text": _prompt_busca(q, datetime.now(UTC).date().isoformat())}]}
            ],
            "tools": [{"google_search": {}}],
            "generationConfig": {"temperature": 0.2},
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={chave}"
        req = urllib.request.Request(
            url,
            data=json.dumps(corpo).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": UA},
        )
        with urllib.request.urlopen(req, timeout=180) as r:
            resp = json.loads(r.read().decode("utf-8"))
        texto = "".join(p.get("text", "") for p in resp["candidates"][0]["content"]["parts"])
        m = re.search(r"```json\s*(.*?)\s*```", texto, re.S)
        bruto = m.group(1) if m else texto[texto.find("[") : texto.rfind("]") + 1]
        itens = json.loads(bruto) if bruto.strip() else []
        saida: list[Resultado] = []
        for it in itens if isinstance(itens, list) else []:
            if isinstance(it, dict) and str(it.get("link", "")).lower().startswith("http"):
                saida.append(
                    {
                        "link": str(it["link"]),
                        "titulo": str(it.get("titulo") or ""),
                        "resumo": str(it.get("resumo") or ""),
                        "orgao": str(it.get("orgao") or ""),
                        "prazo": str(it.get("prazo") or ""),
                    }
                )
        return saida

    return buscar


def motor_padrao() -> Motor | None:
    cse, cx = (
        os.environ.get("GOOGLE_CSE_KEY", "").strip(),
        os.environ.get("GOOGLE_CSE_ID", "").strip(),
    )
    if cse and cx:
        return motor_google_cse(cse, cx)
    gem = os.environ.get("GEMINI_API_KEY", "").strip()
    return motor_gemini(gem) if gem else None


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


class ColetorBuscaWeb:
    nome = FONTE

    def __init__(
        self,
        motor: Motor | None = None,
        paginas: dict[str, str] | None = None,
        extrator: Extrator | None = None,
        cfg: dict[str, Any] | None = None,
        guardar_vistos: bool = True,
        agora: datetime | None = None,
    ) -> None:
        self._motor = motor
        self._paginas = paginas
        self._extrator = extrator
        self._cfg = cfg
        self._guardar = guardar_vistos
        self._agora = agora

    def _baixar(self, url: str) -> str:
        if self._paginas is not None:
            return self._paginas.get(url, "")
        return baixar(url, cache_horas=24 * 7)

    def coletar(self) -> list[Edital]:
        agora = self._agora or datetime.now(UTC).replace(microsecond=0)
        cfg = self._cfg if self._cfg is not None else carregar_config()
        motor = self._motor or motor_padrao()
        if motor is None:
            raise OSError(
                "sem GOOGLE_CSE_KEY/GOOGLE_CSE_ID nem GEMINI_API_KEY; busca na web pulada"
            )
        max_ia = int(cfg.get("max_ia", 30))
        vistos = _carregar_vistos() if self._guardar else {}
        extrator = self._extrator
        chave = os.environ.get("GEMINI_API_KEY", "").strip()
        if extrator is None:
            extrator = (lambda c: extrair_com_gemini(c, chave)) if chave else extrair_por_regras
        saida: list[Edital] = []
        lidos = falhas = consultas = 0
        for c in consultas_do_dia(cfg, agora):
            if lidos >= max_ia:
                break
            try:
                resultados = motor(str(c["q"]))
                consultas += 1
            except (OSError, ValueError, KeyError, IndexError) as exc:
                print(f"[aviso] busca_web {c['q']!r}: {exc}")
                continue
            for r in resultados:
                link = url_limpa(r["link"])
                host = urllib.parse.urlsplit(link).netloc.lower()
                if link in vistos or any(
                    host == h or host.endswith("." + h) for h in _IGNORAR_HOSTS
                ):
                    continue
                if RUIDO.search(r.get("titulo", "")) or lidos >= max_ia:
                    continue
                try:
                    texto = texto_da_pagina(self._baixar(link))
                except OSError as exc:
                    print(f"[aviso] busca_web {link}: {exc}")
                    texto = ""
                ctx = Contexto(
                    url=link,
                    texto=texto,
                    fonte_id=FONTE,
                    fonte_nome="Busca na web",
                    titulo_link=r.get("titulo", ""),
                    pais=str(c.get("pais") or "BR"),
                    uf=c.get("uf"),
                    abrangencia=c.get("abrangencia"),
                )
                lidos += 1
                dados: dict[str, Any] | None
                if len(texto) < 200:
                    # página não abriu (bloqueio, PDF, fora do ar): guarda o que a busca disse
                    dados = {
                        "eh_oportunidade": True,
                        "titulo": r.get("titulo") or "",
                        "orgao": r.get("orgao") or "",
                        "resumo": r.get("resumo") or "",
                        "prazo_texto": r.get("prazo") or None,
                        "ufs": [c["uf"]] if c.get("uf") else [],
                    }
                    vistos[link] = agora.date().isoformat()
                else:
                    dados = extrator(ctx)
                    if dados is None:
                        falhas += 1
                        dados = extrair_por_regras(ctx)
                    else:
                        vistos[link] = agora.date().isoformat()
                ed = normalizar(ctx, dados or {}, agora, "coleta:busca_web")
                if ed is not None:
                    if r.get("orgao") and ed.orgao == "Busca na web":
                        ed.orgao = r["orgao"][:200]
                    saida.append(ed)
        print(
            f"[busca_web] {consultas} consultas, {lidos} páginas lidas ({falhas} falhas da IA), "
            f"{len(saida)} oportunidades"
        )
        if self._guardar:
            _salvar_vistos(vistos, agora)
        return saida
