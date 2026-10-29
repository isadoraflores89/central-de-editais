#!/usr/bin/env python3
"""Radar de licitações da cultura no PNCP (Portal Nacional de Contratações Públicas).

Consulta a busca pública do PNCP (sem chave), pega os editais que estão recebendo
propostas e guarda só os que falam de cultura: contratação de artistas e shows,
oficinas, festivais, produção cultural, museus, patrimônio, audiovisual, livros,
credenciamentos culturais, inexigibilidades para apresentações etc.

Escreve data/licitacoes.json (versionado). A atualização diária copia para o site.
Só biblioteca padrão. Se o PNCP não responder, mantém o arquivo anterior.

Uso:
  python integracoes/radar/pncp.py
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Bahia")
RAIZ = Path(__file__).resolve().parents[2]
SAIDA = RAIZ / "data" / "licitacoes.json"
BUSCA = "https://pncp.gov.br/api/search/"
# o PNCP recusa identificadores de programa (python-urllib, curl); só aceita os de navegador
UA = "Mozilla/5.0 (compatible; CentralDeEditais/1.0; +https://radardeeditais.isadoraflores.art.br)"

# o que perguntar ao PNCP (a busca dele é ampla; o filtro de verdade é o regex abaixo)
CONSULTAS = [
    "cultura",
    "cultural",
    "artistas",
    "show artístico",
    "festival",
    "oficinas culturais",
    "museu",
    "patrimônio histórico",
    "audiovisual",
    "teatro",
    "banda de música",
    "biblioteca",
    "carnaval",
    "evento cultural",
]
PAGINAS_POR_CONSULTA = 3
TAMANHO_PAGINA = 50

# precisa bater um destes termos no objeto (atividade cultural, não só a palavra "cultura")
RELEVANTE = re.compile(
    r"\b(art[ií]st\w*|show[s]?\b|espet[aá]cul\w*|teatr\w*|dan[cç]a\b|m[uú]sic\w*|banda[s]?\b|"
    r"orquestra|coral\b|oficina[s]? (cultura\w*|de arte\w*|art[ií]stic\w*)|museu\w*|"
    r"patrim[oô]nio (hist[oó]rico|cultural|imaterial)|audiovisu\w*|cinema|filme[s]?\b|"
    r"document[aá]rio|festival|festa[s]? (popular\w*|junina[s]?|de s[aã]o jo[aã]o)|"
    r"exposi[cç][aã]o|bibliotec\w*|liter[aá]ri\w*|literatura|capoeira|carnaval|forr[oó]\b|"
    r"samba\b|circo\b|circense|cenograf\w*|sonoriza[cç][aã]o|ilumina[cç][aã]o c[eê]nica|"
    r"curadoria|produ[cç][aã]o cultural|produtor[a]? cultural|agentes? cultura\w*|"
    r"a[cç][oõ]es culturais|atividades culturais|evento[s]? cultura\w*|projeto[s]? cultura\w*|"
    r"apresenta[cç][oõ]es (cultura\w*|art[ií]stic\w*|musica\w*)|fomento [àa] cultura|"
    r"folcl[oó]r\w*|quadrilha[s]? junina|trio el[eé]trico|hip ?hop|grafite|artesanato|"
    r"economia criativa|ponto[s]? de cultura|lei (aldir blanc|paulo gustavo|rouanet)|pnab\b|"
    r"secretaria (municipal |estadual )?de cultura)",
    re.IGNORECASE,
)
# objetos que não são contratação cultural, mesmo citando cultura (compras de material, obras)
RUIDO = re.compile(
    r"\b(odontol\w*|dent[aá]ri\w*|m[eé]dic\w*|hospital\w*|medicament\w*|"
    r"cultura de (c[eé]lulas|tecidos)|agr[ií]col\w*|agricultur\w*|sementes|fertiliz\w*|"
    r"pavimenta\w*|asf[aá]lt\w*|esgoto|combust[ií]ve\w*|pneus?\b|ve[ií]culos?\b|ambul[aâ]ncia|"
    r"merenda|g[eê]neros aliment\w*|ar[- ]condicionad\w*|aquisi[cç][aã]o de (pe[cç]as|materia\w*|"
    r"mobili[aá]rio|m[oó]veis|equipamentos|eletrodom\w*|brinquedos|uniformes|solu[cç][oõ]es)|"
    r"material de expediente|obra[s]? de|engenharia|constru[cç][aã]o|reforma|amplia[cç][aã]o|"
    r"manuten[cç][aã]o (predial|de aparelhos|de equipamentos)|limpeza|vigil[aâ]ncia|"
    r"inform[aá]tica|computador\w*|impressora\w*|serra\b|tintas?\b)",
    re.IGNORECASE,
)


def hoje() -> date:
    return datetime.now(FUSO).date()


def buscar(consulta: str, pagina: int) -> list[dict[str, Any]]:
    params = {
        "q": consulta,
        "tipos_documento": "edital",
        "status": "recebendo_proposta",
        "ordenacao": "-data",
        "pagina": str(pagina),
        "tam_pagina": str(TAMANHO_PAGINA),
    }
    url = BUSCA + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    ultimo: Exception | None = None
    for tentativa in range(4):  # o portal derruba conexões de vez em quando
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                dados = json.loads(r.read().decode("utf-8"))
            itens: list[dict[str, Any]] = dados.get("items") or []
            return itens
        except (OSError, ValueError) as e:
            ultimo = e
            time.sleep(1.5 * (tentativa + 1))
    raise OSError(f"PNCP não respondeu: {ultimo}")


def so_data(valor: Any) -> str:
    s = str(valor or "")[:10]
    try:
        return date.fromisoformat(s).isoformat()
    except ValueError:
        return ""


def normalizar(it: dict[str, Any]) -> dict[str, Any] | None:
    descricao = " ".join(str(it.get("description") or "").split())
    titulo = str(it.get("title") or "").strip()
    texto = f"{titulo} {descricao}"
    if not RELEVANTE.search(texto) or RUIDO.search(texto):
        return None
    if it.get("cancelado"):
        return None
    cnpj = str(it.get("orgao_cnpj") or "")
    ano = str(it.get("ano") or "")
    seq = str(it.get("numero_sequencial") or "")
    if not (cnpj and ano and seq):
        return None
    prazo = so_data(it.get("data_fim_vigencia"))
    if prazo and date.fromisoformat(prazo) < hoje():
        return None
    valor = it.get("valor_global")
    try:
        valor_num = float(valor) if valor not in (None, "") else None
    except (TypeError, ValueError):
        valor_num = None
    return {
        "id": str(it.get("numero_controle_pncp") or f"{cnpj}-{ano}-{seq}"),
        "titulo": descricao[:180].rstrip(" ,;:-") + ("…" if len(descricao) > 180 else ""),
        "edital": titulo,
        "orgao": str(it.get("orgao_nome") or "").strip(),
        "unidade": str(it.get("unidade_nome") or "").strip(),
        "municipio": str(it.get("municipio_nome") or "").strip(),
        "uf": str(it.get("uf") or "").strip().upper(),
        "esfera": str(it.get("esfera_nome") or "").strip(),
        "modalidade": str(it.get("modalidade_licitacao_nome") or "").strip(),
        "publicado_em": so_data(it.get("data_publicacao_pncp")),
        "prazo": prazo,
        "valor": valor_num,
        "link": f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{seq}",
    }


def main() -> int:
    anterior: list[dict[str, Any]] = []
    if SAIDA.exists():
        with open(SAIDA, encoding="utf-8") as f:
            anterior = json.load(f).get("itens", [])

    vistos: dict[str, dict[str, Any]] = {}
    falhas = 0
    for consulta in CONSULTAS:
        for pagina in range(1, PAGINAS_POR_CONSULTA + 1):
            try:
                brutos = buscar(consulta, pagina)
            except (OSError, ValueError) as e:  # URLError, conexão fechada, JSON ruim
                falhas += 1
                print(f"[aviso] PNCP '{consulta}' p{pagina}: {e}", file=sys.stderr)
                break
            if not brutos:
                break
            for it in brutos:
                item = normalizar(it)
                if item and item["id"] not in vistos:
                    vistos[item["id"]] = item
            time.sleep(1.0)  # educado com o portal

    if not vistos and anterior:
        print("[aviso] nada veio do PNCP; mantendo a lista anterior", file=sys.stderr)
        itens = [it for it in anterior if not it.get("prazo") or it["prazo"] >= hoje().isoformat()]
    else:
        itens = list(vistos.values())
    itens.sort(key=lambda it: (it.get("prazo") or "9999", it.get("publicado_em") or ""))

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    conteudo = {
        "atualizado_em": hoje().isoformat(),
        "fonte": "PNCP — Portal Nacional de Contratações Públicas (busca pública)",
        "licenca": "dados públicos; curadoria CC BY 4.0",
        "total": len(itens),
        "itens": itens,
    }
    SAIDA.write_text(json.dumps(conteudo, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"[ok] licitações da cultura no PNCP: {len(itens)} abertas ({falhas} consultas falharam)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
