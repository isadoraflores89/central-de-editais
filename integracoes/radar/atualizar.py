#!/usr/bin/env python3
"""Radar de resultados e radar de vagas na cultura.

Roda toda semana no GitHub Actions (ver .github/workflows/radar-semanal.yml) e
escreve dois arquivos versionados, que a atualização diária copia para o site:

  data/resultados.json  editais da Central que já encerraram e cujo resultado
                        (lista de selecionados, habilitados, classificados) foi
                        publicado, com o link da página oficial;
  data/vagas.json       vagas de trabalho na cultura abertas no Brasil
                        (editais de contratação, chamadas, seleções, concursos).

Usa a API gratuita do Google Gemini com busca na web (Google Search grounding),
a mesma do Rolê Salvador. Secret: GEMINI_API_KEY. Só biblioteca padrão.

Se a busca falhar, mantém o arquivo anterior e só atualiza a data. Nunca quebra o site.

Uso:
  python integracoes/radar/atualizar.py            # atualiza os dois
  python integracoes/radar/atualizar.py --so vagas # ou --so resultados
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Bahia")
RAIZ = Path(__file__).resolve().parents[2]
EDITAIS = RAIZ / "data" / "editais.json"
RESULTADOS = RAIZ / "data" / "resultados.json"
VAGAS = RAIZ / "data" / "vagas.json"

MODELO = "gemini-2.5-flash"
API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent?key={API_KEY}"

AREAS = {
    "audiovisual",
    "musica",
    "artes_cenicas",
    "artes_visuais",
    "literatura",
    "patrimonio",
    "culturas_populares",
    "formacao",
    "economia_criativa",
    "gestao_cultural",
    "producao",
    "comunicacao",
    "educacao",
    "museus",
    "outra",
}
UFS = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA",
    "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
}  # fmt: skip


def hoje() -> date:
    return datetime.now(FUSO).date()


def gemini(prompt: str) -> str:
    corpo = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.2},
    }
    dados = json.dumps(corpo).encode("utf-8")
    ultimo: Exception | None = None
    for tentativa in range(2):
        try:
            req = urllib.request.Request(
                URL,
                data=dados,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "central-de-editais/1.0",
                },
            )
            with urllib.request.urlopen(req, timeout=180) as r:
                resp = json.loads(r.read().decode("utf-8"))
            partes = resp["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in partes)
        except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError) as e:
            ultimo = e
            print(f"[aviso] tentativa {tentativa + 1} falhou: {e}", file=sys.stderr)
    raise RuntimeError(f"Gemini não respondeu: {ultimo}")


def extrai_json(texto: str) -> Any:
    m = re.search(r"```json\s*(.*?)\s*```", texto, re.DOTALL)
    bruto = m.group(1) if m else None
    if bruto is None:
        i, j = texto.find("["), texto.rfind("]")
        if i != -1 and j > i:
            bruto = texto[i : j + 1]
    if not bruto:
        raise ValueError("nenhum JSON na resposta")
    return json.loads(bruto)


def ler(caminho: Path) -> dict[str, Any]:
    if caminho.exists():
        with open(caminho, encoding="utf-8") as f:
            dados: dict[str, Any] = json.load(f)
            return dados
    return {"atualizado_em": None, "itens": []}


def gravar(caminho: Path, itens: list[dict[str, Any]], fonte: str) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conteudo = {
        "atualizado_em": hoje().isoformat(),
        "fonte": fonte,
        "licenca": "CC BY 4.0",
        "total": len(itens),
        "itens": itens,
    }
    caminho.write_text(json.dumps(conteudo, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def data_ok(valor: Any) -> str:
    try:
        return date.fromisoformat(str(valor)).isoformat()
    except (TypeError, ValueError):
        return ""


# ----------------------------------------------------------------------------
# resultados
# ----------------------------------------------------------------------------
def prompt_resultados(encerrados: list[dict[str, Any]]) -> str:
    lista = "\n".join(
        f"- id={e['id']} | {e['titulo']} | {e.get('orgao') or ''} | "
        f"encerrou em {e.get('data_limite') or '?'} | "
        f"{e.get('link_edital') or e.get('source_url') or ''}"
        for e in encerrados
    )
    return f"""Você é editor de um radar de editais culturais brasileiros.
Hoje é {hoje().isoformat()}.

Para CADA edital abaixo, pesquise na web se o RESULTADO já foi publicado (lista de selecionados,
aprovados, habilitados, classificados, homologação ou resultado preliminar/final).

{lista}

REGRAS:
- Só inclua um edital se encontrou a página oficial do resultado (site do órgão, Diário Oficial,
  plataforma de inscrição). Nunca invente. Se não achou, não inclua.
- "tipo" é um destes: preliminar, final, habilitacao, homologacao.
- "data" no formato AAAA-MM-DD (da publicação do resultado), ou "" se não houver.

Responda APENAS com um bloco ```json``` contendo um array de objetos com os campos exatos:
  "id", "titulo", "orgao", "tipo", "data", "resumo" (uma frase curta, sem emojis), "link"
Não escreva nada fora do bloco JSON."""


def atualizar_resultados() -> None:
    with open(EDITAIS, encoding="utf-8") as f:
        feed = json.load(f)
    editais = feed["editais"] if isinstance(feed, dict) else feed
    limite = hoje() - timedelta(days=60)
    encerrados = [
        e
        for e in editais
        if e.get("status") == "encerrado"
        and e.get("data_limite")
        and date.fromisoformat(e["data_limite"]) >= limite
    ]
    anterior = ler(RESULTADOS)
    conhecidos = {it["id"]: it for it in anterior.get("itens", []) if it.get("id")}
    if not encerrados:
        print("[ok] resultados: nenhum edital encerrado nos últimos 60 dias")
        gravar(RESULTADOS, list(conhecidos.values()), "Central de Editais + busca semanal")
        return
    try:
        brutos = extrai_json(gemini(prompt_resultados(encerrados)))
    except Exception as e:  # fail-safe: nunca quebrar o site
        print(f"[aviso] resultados: busca falhou ({e}); mantendo os anteriores", file=sys.stderr)
        gravar(RESULTADOS, list(conhecidos.values()), "Central de Editais + busca semanal")
        return
    ids_validos = {e["id"]: e for e in encerrados}
    novos = 0
    for it in brutos if isinstance(brutos, list) else []:
        if not isinstance(it, dict) or it.get("id") not in ids_validos:
            continue
        link = str(it.get("link") or "").strip()
        if not link.lower().startswith("http"):
            continue
        base = ids_validos[it["id"]]
        item = {
            "id": it["id"],
            "titulo": base["titulo"],
            "orgao": base.get("orgao") or str(it.get("orgao") or ""),
            "areas": base.get("areas") or [],
            "ufs": base.get("ufs") or [],
            "tipo": str(it.get("tipo") or "final").strip().lower(),
            "data": data_ok(it.get("data")) or hoje().isoformat(),
            "resumo": str(it.get("resumo") or "").strip(),
            "link": link,
            "visto_em": conhecidos.get(it["id"], {}).get("visto_em") or hoje().isoformat(),
        }
        if it["id"] not in conhecidos:
            novos += 1
        conhecidos[it["id"]] = item
    # some da lista resultados com mais de 120 dias
    corte = (hoje() - timedelta(days=120)).isoformat()
    itens = [it for it in conhecidos.values() if (it.get("data") or "") >= corte]
    itens.sort(key=lambda it: it.get("data") or "", reverse=True)
    gravar(RESULTADOS, itens, "Central de Editais + busca semanal")
    print(f"[ok] resultados: {len(itens)} no radar ({novos} novos)")


# ----------------------------------------------------------------------------
# vagas
# ----------------------------------------------------------------------------
def prompt_vagas() -> str:
    return f"""Você é editor de um radar de VAGAS DE TRABALHO NA CULTURA no Brasil.
Hoje é {hoje().isoformat()}.

Pesquise na web vagas e seleções ABERTAS agora (prazo de inscrição no futuro ou não informado)
para profissionais da cultura: produção cultural, gestão cultural, curadoria, educação/mediação em
museus e centros culturais, comunicação cultural, técnicos de audiovisual/som/luz, pesquisa,
captação de recursos, pareceristas, coordenação de projetos. Inclua:
- editais e chamadas de contratação de órgãos públicos (secretarias, fundações, Funarte,
  Iphan, museus);
- processos seletivos de institutos, fundações, Sesc, Sesi, Oi Futuro, Itaú Cultural,
  Instituto Moreira Salles etc.;
- vagas publicadas por organizações culturais e produtoras (CLT, PJ, bolsa ou temporário);
- seleção de pareceristas e credenciamentos remunerados.

REGRAS OBRIGATÓRIAS:
- Só vagas com página oficial ou publicação confiável (site do empregador, plataforma de
  vagas, Diário Oficial).
- Nunca invente vagas, nomes ou prazos. Se não tiver certeza da data, deixe "prazo" vazio ("").
- "uf" é a sigla do estado, ou "" se remoto/nacional. "remoto" é true/false.
- "area" é exatamente uma destas: {", ".join(sorted(AREAS))}.
- "regime": clt, pj, bolsa, temporario, estagio, concurso, credenciamento ou outro.
- Sem emojis. Entre 8 e 20 itens, os mais relevantes primeiro.

Responda APENAS com um bloco ```json``` contendo um array de objetos com os campos exatos:
  "titulo", "organizacao", "cidade", "uf", "remoto", "area", "regime", "prazo" (AAAA-MM-DD ou ""),
  "salario" (texto curto ou ""), "resumo" (uma frase), "link"
Não escreva nada fora do bloco JSON."""


def atualizar_vagas() -> None:
    anterior = ler(VAGAS)
    antigos = {it["link"]: it for it in anterior.get("itens", []) if it.get("link")}
    try:
        brutos = extrai_json(gemini(prompt_vagas()))
    except Exception as e:  # fail-safe: nunca quebrar o site
        print(f"[aviso] vagas: busca falhou ({e}); mantendo as anteriores", file=sys.stderr)
        gravar(VAGAS, list(antigos.values()), "busca semanal na web")
        return
    h = hoje()
    itens: dict[str, dict[str, Any]] = {}
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
        area = str(it.get("area") or "outra").strip().lower()
        itens[link] = {
            "titulo": titulo,
            "organizacao": str(it.get("organizacao") or "").strip(),
            "cidade": str(it.get("cidade") or "").strip(),
            "uf": uf if uf in UFS else "",
            "remoto": bool(it.get("remoto")),
            "area": area if area in AREAS else "outra",
            "regime": str(it.get("regime") or "outro").strip().lower(),
            "prazo": prazo,
            "salario": str(it.get("salario") or "").strip(),
            "resumo": str(it.get("resumo") or "").strip(),
            "link": link,
            "visto_em": antigos.get(link, {}).get("visto_em") or h.isoformat(),
        }
    # mantém as antigas ainda dentro do prazo (ou sem prazo) por até 30 dias
    corte = (h - timedelta(days=30)).isoformat()
    for link, it in antigos.items():
        if link in itens:
            continue
        if (it.get("prazo") and it["prazo"] < h.isoformat()) or (it.get("visto_em") or "") < corte:
            continue
        itens[link] = it
    lista = sorted(
        itens.values(), key=lambda it: (it.get("prazo") or "9999", it.get("titulo") or "")
    )
    gravar(VAGAS, lista, "busca semanal na web")
    print(f"[ok] vagas: {len(lista)} no radar")


def main() -> int:
    ap = argparse.ArgumentParser(description="Radar de resultados e de vagas na cultura")
    ap.add_argument("--so", choices=["resultados", "vagas"], help="atualizar só um dos dois")
    args = ap.parse_args()
    if not API_KEY:
        print("[erro] falta GEMINI_API_KEY", file=sys.stderr)
        return 1
    if args.so != "vagas":
        atualizar_resultados()
    if args.so != "resultados":
        atualizar_vagas()
    return 0


if __name__ == "__main__":
    sys.exit(main())
