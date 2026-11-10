#!/usr/bin/env python3
"""Radar de festivais: onde um espetáculo, show ou filme pode se inscrever ou pedir pauta.

Duas fontes, juntadas em data/festivais.json:
1. Convocatórias abertas (inscrições de festivais e mostras de teatro, dança, circo, cinema,
   música, literatura e artes visuais, no Brasil e no exterior), pesquisadas na web pelo Gemini
   toda semana. Cada item tem prazo, taxa, premiação/cachê e link oficial. Sem GEMINI_API_KEY,
   este bloco é pulado e as convocatórias anteriores ainda no prazo são mantidas.
2. Calendário do Mapa dos Festivais (mapadosfestivais.com.br): festivais de música já
   anunciados, com data, cidade e estado. Servem para prospectar pauta mesmo sem edital
   aberto (tipo "calendario"). Só biblioteca padrão; respeita o site com intervalo entre pedidos.

Uso:
  python integracoes/radar/festivais.py            # as duas fontes
  python integracoes/radar/festivais.py --so mapa  # só o calendário (sem IA)
"""

from __future__ import annotations

import argparse
import contextlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Bahia")
RAIZ = Path(__file__).resolve().parents[2]
SAIDA = RAIZ / "data" / "festivais.json"
UA = "Mozilla/5.0 (compatible; CentralDeEditais/1.0; +https://radardeeditais.isadoraflores.art.br)"
MAPA_API = "https://mapadosfestivais.com.br/wp-json/wp/v2/event"
MAPA_PAGINAS = 2  # 2 x 100 eventos mais recentes
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
MODELO = "gemini-2.5-flash"

LINGUAGENS = {
    "teatro", "danca", "circo", "musica", "cinema", "literatura", "artes_visuais",
    "artes_integradas", "cultura_popular", "infantil", "outra",
}  # fmt: skip
UFS = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA",
    "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
}  # fmt: skip
_ESTADOS = {
    "acre": "AC", "alagoas": "AL", "amazonas": "AM", "amapá": "AP", "amapa": "AP", "bahia": "BA",
    "ceará": "CE", "ceara": "CE", "distrito federal": "DF", "espírito santo": "ES",
    "espirito santo": "ES", "goiás": "GO", "goias": "GO", "maranhão": "MA", "maranhao": "MA",
    "minas gerais": "MG", "mato grosso do sul": "MS", "mato grosso": "MT", "pará": "PA",
    "para": "PA",
    "paraíba": "PB", "paraiba": "PB", "pernambuco": "PE", "piauí": "PI", "piaui": "PI",
    "paraná": "PR", "parana": "PR", "rio de janeiro": "RJ", "rio grande do norte": "RN",
    "rondônia": "RO", "rondonia": "RO", "roraima": "RR", "rio grande do sul": "RS",
    "santa catarina": "SC", "sergipe": "SE", "são paulo": "SP", "sao paulo": "SP",
    "tocantins": "TO",
}  # fmt: skip
MESES = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}  # fmt: skip


def hoje() -> date:
    return datetime.now(FUSO).date()


def baixar(url: str, timeout: int = 60) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return str(r.read().decode(r.headers.get_content_charset() or "utf-8", "replace"))


def so_texto(h: str) -> str:
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t).strip()


def data_ok(valor: Any) -> str:
    try:
        return date.fromisoformat(str(valor)[:10]).isoformat()
    except (TypeError, ValueError):
        return ""


# ---------- fonte 1: Mapa dos Festivais ----------
_DATAS = re.compile(
    r"(\d{1,2})\s+(janeiro|fevereiro|mar[cç]o|abril|maio|junho|julho|agosto|setembro|outubro|"
    r"novembro|dezembro)(?:\s+(\d{4}))?",
    re.I,
)
_CIDADE_UF = re.compile(r"([A-ZÀ-Ú][\w'À-ú.\- ]{2,60}?) - ([A-Z]{2}),\s*\d{5}-?\d{3}")
_INSTA = re.compile(r'href="(https?://(?:www\.)?instagram\.com/[^"]+)"')
_OG_IMG = re.compile(r'property="og:image" content="([^"]+)"')


def ler_evento_mapa(h: str, titulo: str) -> dict[str, Any]:
    txt = so_texto(h)
    ini = txt.find(titulo)
    trecho = txt[ini : ini + 400] if ini != -1 else txt[:1500]
    datas: list[date] = []
    ano_ref = None
    for m in _DATAS.finditer(trecho):
        if m.group(3):
            ano_ref = int(m.group(3))
    for m in _DATAS.finditer(trecho):
        ano = int(m.group(3)) if m.group(3) else ano_ref
        if not ano:
            continue
        mes = MESES.get(m.group(2).lower().replace("ç", "c"), 0) or MESES.get(m.group(2).lower(), 0)
        with contextlib.suppress(ValueError):
            datas.append(date(ano, mes, int(m.group(1))))
    cidade, uf = "", ""
    if m2 := _CIDADE_UF.search(txt):
        cidade, uf = m2.group(1).strip(), m2.group(2)
    elif m3 := re.search(r"LOCALIZA[ÇC][ÃA]O (.{3,200}?) Como Chegar", txt):
        partes = [p.strip() for p in m3.group(1).split(",") if p.strip()]
        if len(partes) >= 2:
            estado = partes[-1].lower()
            uf = _ESTADOS.get(estado, estado.upper() if len(estado) == 2 else "")
            cidade = partes[-2].split(" - ")[-1].strip()
    insta = _INSTA.search(h)
    img = _OG_IMG.search(h)
    chama = bool(re.search(r"inscri[cç]|convocat|chamada|submiss|edital", txt, re.I))
    gratuito = "EVENTO GRATUITO" in txt.upper()
    return {
        "inicio": min(datas).isoformat() if datas else "",
        "fim": max(datas).isoformat() if datas else "",
        "cidade": cidade,
        "uf": uf if uf in UFS else "",
        "instagram": insta.group(1) if insta else "",
        "imagem": html.unescape(img.group(1)) if img else "",
        "menciona_inscricao": chama,
        "gratuito": gratuito,
    }


def mapa_dos_festivais(anteriores: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    saida: list[dict[str, Any]] = []
    h = hoje()
    for pagina in range(1, MAPA_PAGINAS + 1):
        try:
            lista = json.loads(
                baixar(
                    f"{MAPA_API}?per_page=100&page={pagina}&orderby=modified"
                    "&_fields=id,link,title,modified"
                )
            )
        except (OSError, ValueError) as e:
            print(f"[aviso] mapadosfestivais página {pagina}: {e}", file=sys.stderr)
            break
        if not isinstance(lista, list) or not lista:
            break
        for ev in lista:
            link = str(ev.get("link") or "")
            titulo = html.unescape(str((ev.get("title") or {}).get("rendered") or "")).strip()
            if not link or not titulo:
                continue
            antigo = anteriores.get(link)
            # reaproveita a leitura anterior se a página não mudou
            if (
                antigo
                and antigo.get("modificado_em") == ev.get("modified")
                and antigo.get("fim")
                and antigo.get("uf")
            ):
                dados = antigo
            else:
                try:
                    dados = ler_evento_mapa(baixar(link), titulo)
                except (OSError, ValueError) as e:
                    print(f"[aviso] {link}: {e}", file=sys.stderr)
                    continue
                time.sleep(0.7)
            fim = dados.get("fim") or dados.get("inicio") or ""
            if not fim or date.fromisoformat(fim) < h:
                continue  # já aconteceu
            saida.append(
                {
                    "id": "mapa-" + link.rstrip("/").rsplit("/", 1)[-1],
                    "tipo": "calendario",
                    "titulo": titulo,
                    "linguagem": "musica",
                    "organizacao": "",
                    "cidade": dados.get("cidade", ""),
                    "uf": dados.get("uf", ""),
                    "pais": "BR",
                    "inicio": dados.get("inicio", ""),
                    "fim": fim,
                    "prazo": "",
                    "taxa": "",
                    "beneficio": "",
                    "resumo": (
                        "Festival de música já anunciado. "
                        + (
                            "A página menciona inscrições ou chamada. "
                            if dados.get("menciona_inscricao")
                            else ""
                        )
                        + "Vale procurar a produção para propor pauta ou parceria."
                    ).strip(),
                    "link": link,
                    "instagram": dados.get("instagram", ""),
                    "imagem": dados.get("imagem", ""),
                    "fonte": "Mapa dos Festivais",
                    "modificado_em": ev.get("modified"),
                    "visto_em": (antigo or {}).get("visto_em") or h.isoformat(),
                }
            )
    return saida


# ---------- fonte 2: convocatórias (Gemini com busca na web) ----------
def prompt_convocatorias() -> str:
    return f"""Você é editor de um radar de FESTIVAIS E MOSTRAS COM INSCRIÇÕES ABERTAS para
artistas, grupos e produtoras do Brasil. Hoje é {hoje().isoformat()}.

Pesquise na web convocatórias ABERTAS agora (prazo no futuro ou não informado) de festivais e
mostras de teatro, dança, circo, música, cinema e audiovisual, literatura, artes visuais e
artes integradas,
no Brasil e no exterior (quando aceitam brasileiros). Inclua chamadas de festivais que selecionam
espetáculos para programação (pauta), mostras competitivas de filmes, festivais de música com
inscrição de bandas, feiras e mercados de artes cênicas (showcases) e festivais infantis.

REGRAS OBRIGATÓRIAS:
- Só com página oficial do festival ou edital publicado (site, plataforma de inscrição como
  FilmFreeway, Festhome, Mapa Cultural, Sympla, Prosas, Diário Oficial).
- Nunca invente nomes, datas, taxas ou valores. Campo desconhecido fica "".
- "linguagem" é exatamente uma destas: {", ".join(sorted(LINGUAGENS))}.
- "uf" é a sigla do estado (ou "" se internacional/nacional); "pais" é o código ISO-2
  (BR, PT, AR...).
- "taxa": "gratuita", ou o valor como escrito, ou "" se não informado.
- "beneficio": cachê, ajuda de custo, hospedagem, premiação, como escrito, ou "".
- Sem emojis. Entre 10 e 25 itens, os prazos mais próximos primeiro.

Responda APENAS com um bloco ```json``` contendo um array de objetos com os campos exatos:
  "titulo", "organizacao", "linguagem", "cidade", "uf", "pais", "inicio" (AAAA-MM-DD ou ""),
  "fim" (AAAA-MM-DD ou ""), "prazo" (AAAA-MM-DD ou ""), "taxa", "beneficio",
  "resumo" (uma ou duas frases), "link"
Não escreva nada fora do bloco JSON."""


def gemini(prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent?key={GEMINI_KEY}"
    corpo = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.2},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(corpo).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": UA},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        resp = json.loads(r.read().decode("utf-8"))
    return "".join(p.get("text", "") for p in resp["candidates"][0]["content"]["parts"])


def extrai_json(texto: str) -> Any:
    m = re.search(r"```json\s*(.*?)\s*```", texto, re.S)
    bruto = m.group(1) if m else None
    if bruto is None:
        i, j = texto.find("["), texto.rfind("]")
        bruto = texto[i : j + 1] if i != -1 and j > i else ""
    if not bruto:
        raise ValueError("nenhum JSON na resposta")
    return json.loads(bruto)


def convocatorias(anteriores: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    h = hoje()
    novos: dict[str, dict[str, Any]] = {}
    if GEMINI_KEY:
        try:
            brutos = extrai_json(gemini(prompt_convocatorias()))
        except Exception as e:  # fail-safe: nunca quebrar o site
            print(f"[aviso] convocatórias: busca falhou ({e})", file=sys.stderr)
            brutos = []
        for it in brutos if isinstance(brutos, list) else []:
            if not isinstance(it, dict):
                continue
            link = str(it.get("link") or "").strip()
            titulo = str(it.get("titulo") or "").strip()
            if not link.lower().startswith("http") or not titulo:
                continue
            prazo = data_ok(it.get("prazo"))
            if prazo and date.fromisoformat(prazo) < h:
                continue
            uf = str(it.get("uf") or "").strip().upper()
            ling = str(it.get("linguagem") or "outra").strip().lower()
            novos[link] = {
                "id": "conv-" + re.sub(r"[^a-z0-9]+", "-", link.lower())[-60:].strip("-"),
                "tipo": "convocatoria",
                "titulo": titulo,
                "linguagem": ling if ling in LINGUAGENS else "outra",
                "organizacao": str(it.get("organizacao") or "").strip(),
                "cidade": str(it.get("cidade") or "").strip(),
                "uf": uf if uf in UFS else "",
                "pais": (str(it.get("pais") or "BR").strip().upper() or "BR")[:2],
                "inicio": data_ok(it.get("inicio")),
                "fim": data_ok(it.get("fim")),
                "prazo": prazo,
                "taxa": str(it.get("taxa") or "").strip(),
                "beneficio": str(it.get("beneficio") or "").strip(),
                "resumo": str(it.get("resumo") or "").strip()[:1000],
                "link": link,
                "instagram": "",
                "imagem": "",
                "fonte": "busca semanal na web",
                "visto_em": (anteriores.get(link) or {}).get("visto_em") or h.isoformat(),
            }
    else:
        print("[aviso] sem GEMINI_API_KEY: convocatórias não atualizadas", file=sys.stderr)
    # mantém convocatórias antigas ainda no prazo (ou sem prazo) por até 45 dias
    corte = (h - timedelta(days=45)).isoformat()
    for link, it in anteriores.items():
        if it.get("tipo") != "convocatoria" or link in novos:
            continue
        if (it.get("prazo") and it["prazo"] < h.isoformat()) or (it.get("visto_em") or "") < corte:
            continue
        novos[link] = it
    return list(novos.values())


def main() -> int:
    ap = argparse.ArgumentParser(description="Radar de festivais")
    ap.add_argument("--so", choices=["mapa", "convocatorias"])
    args = ap.parse_args()
    anteriores: dict[str, dict[str, Any]] = {}
    if SAIDA.exists():
        for it in json.loads(SAIDA.read_text(encoding="utf-8")).get("itens", []):
            anteriores[it["link"]] = it
    itens: list[dict[str, Any]] = []
    if args.so != "mapa":
        itens += convocatorias(anteriores)
    else:
        itens += [it for it in anteriores.values() if it.get("tipo") == "convocatoria"]
    if args.so != "convocatorias":
        mapa = mapa_dos_festivais(anteriores)
        if not mapa:
            mapa = [it for it in anteriores.values() if it.get("tipo") == "calendario"]
        itens += mapa
    else:
        itens += [it for it in anteriores.values() if it.get("tipo") == "calendario"]
    # convocatórias primeiro (prazo mais perto), depois calendário por data
    itens.sort(
        key=lambda it: (
            0 if it.get("tipo") == "convocatoria" else 1,
            it.get("prazo") or it.get("inicio") or "9999",
            it.get("titulo") or "",
        )
    )
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(
        json.dumps(
            {
                "atualizado_em": hoje().isoformat(),
                "fontes": ["busca semanal na web (Gemini)", "Mapa dos Festivais"],
                "licenca": "curadoria CC BY 4.0; confira sempre a página oficial",
                "total": len(itens),
                "itens": itens,
            },
            ensure_ascii=False,
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    n_conv = sum(1 for it in itens if it.get("tipo") == "convocatoria")
    print(f"[ok] festivais: {n_conv} convocatórias + {len(itens) - n_conv} no calendário")
    return 0


if __name__ == "__main__":
    sys.exit(main())
