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
    r"samba\b|circo\b|circense|cenograf\w*|"
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
    r"inform[aá]tica|computador\w*|impressora\w*|serra\b|tintas?\b|"
    # infraestrutura e logística de evento (não é serviço artístico ou cultural)
    r"tendas?\b|loca[cç][aã]o de (tendas?|palco\w*|estrutura\w*|banheiro\w*|gerador\w*|"
    r"brinquedo\w*|som\b|ilumina[cç][aã]o|telão|telões|led\b|grades?\b|container\w*|"
    r"ve[ií]culo\w*|[oô]nibus|van\b)|estruturas? (met[aá]lica\w*|de palco|para evento\w*|"
    r"tempor[aá]ria\w*)|montagem e desmontagem|palcos?\b|arquibancada\w*|camarote\w*|"
    r"banheiros? qu[ií]mico\w*|gerador\w* de energia|sonoriza[cç][aã]o|servi[cç]os? de som\b|"
    r"ilumina[cç][aã]o (c[eê]nica|de palco|para evento\w*)|seguran[cç]a (privada|patrimonial|"
    r"desarmada|armada)|brigad\w*|bombeiro\w* civi\w*|fogos de artif[ií]cio|pirot[eé]cni\w*|"
    r"decora[cç][aã]o (natalina|de natal|junina)|ornamenta[cç][aã]o|buffet|bufê|coffee ?break|"
    r"alimenta[cç][aã]o|refei[cç][oõ]es|lanches?\b|frutos?\b|abacaxi|bebidas?\b|hospedagem|"
    r"passagens? a[eé]rea\w*|transporte\b|camisetas?\b|uniformes?\b|trof[eé]us?\b|medalhas?\b|"
    r"aquisi[cç][aã]o de (instrumentos|livros|figurinos|fantasias|tecidos|materiais|"
    r"equipamentos|esta[cç][aã]o de trabalho)|registro de pre[cç]os? para (futura e )?eventual "
    r"aquisi[cç][aã]o|workstation|software|licenciamento|sistema de gest[aã]o|fornecimento de "
    r"(materiais|equipamentos|produtos|g[eê]neros)|aquisi[cç][aã]o de\b|compra de\b|"
    r"estruturas?\b|grades?\b|fechamento\b|tirolesa|seguro\b|readequa\w*|instala[cç][oõ]es|mobili[aá]rio|"
    r"impress[aã]o gr[aá]fica|confec[cç][aã]o de|sinaliza[cç][aã]o|placas?\b|[oó]leo diesel)",
    re.IGNORECASE,
)
COMPRA = re.compile(
    r"\s*(\[[^\]]*\]\s*-?\s*)?(aquisi[cç][aã]o|compra|fornecimento|registro de pre[cç]os? para "
    r"(futura e )?eventual (aquisi[cç][aã]o|compra|fornecimento)|loca[cç][aã]o de (tendas?|palco|"
    r"estrutura|equipamentos|banheiro|gerador|brinquedo|som|ilumina))",
    re.IGNORECASE,
)
# exceções: credenciamento de artistas/pareceristas/oficineiros é cultural mesmo citando "evento"
SERVICO_CULTURAL = re.compile(
    r"\b(credenciamento de (artistas|m[uú]sicos|bandas|grupos|pareceristas|oficineir\w*|"
    r"agentes culturais|profissionais (de|da) (arte|cultura))|apresenta[cç][oõ]es? "
    r"(art[ií]stic\w*|musica\w*|cultura\w*)|sele[cç][aã]o de (projetos|propostas) cultura\w*|"
    r"produ[cç][aã]o (cultural|audiovisual|de espet[aá]culo\w*)|curadoria|museolog\w*|"
    r"restaur\w* (de (obras|acervo|bens)|arquitet\w*)|tombamento|educa[cç][aã]o patrimonial|"
    r"conserva[cç][aã]o de (acervo|bens|obras)|invent[aá]rio (cultural|do patrim)|"
    r"oficinas? (de arte|cultura\w*|art[ií]stic\w*|de m[uú]sica|de teatro|de dan[cç]a))\b",
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
    if not (RELEVANTE.search(texto) or SERVICO_CULTURAL.search(texto)):
        return None
    if RUIDO.search(texto) and not SERVICO_CULTURAL.search(texto):
        return None
    # compra de bens nunca é serviço cultural, mesmo que o texto cite oficinas ou artistas
    if COMPRA.match(descricao) or COMPRA.match(titulo):
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


GEMINI_KEY = __import__("os").environ.get("GEMINI_API_KEY", "").strip()


def peneira_gemini(itens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pergunta ao Gemini, em lotes, quais objetos são serviço artístico/cultural de verdade.

    Mantém o item quando a IA diz que é cultural; se a IA falhar, mantém todos (as regras
    acima já filtraram o grosso). Sem GEMINI_API_KEY, não faz nada.
    """
    if not GEMINI_KEY or not itens:
        return itens
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        f"?key={GEMINI_KEY}"
    )
    mantidos: list[dict[str, Any]] = []
    for i in range(0, len(itens), 40):
        lote = itens[i : i + 40]
        linhas = "\n".join(f"{k}. {it['titulo'][:220]}" for k, it in enumerate(lote))
        prompt = (
            "Você classifica objetos de licitações públicas brasileiras. Responda SOMENTE um JSON "
            'no formato {"culturais": [números]} com os itens que são '
            "SERVIÇO ARTÍSTICO OU CULTURAL: "
            "contratação ou credenciamento de artistas, músicos, bandas, grupos, oficineiros, "
            "pareceristas culturais, produção cultural ou audiovisual, curadoria, museologia, "
            "restauro e inventário de patrimônio, seleção de projetos culturais, "
            "livros e literatura. "
            "NÃO são culturais: tendas, palcos, som, iluminação, geradores, banheiros, segurança, "
            "brigadistas, fogos, decoração, alimentação, transporte, hospedagem, compra de bens "
            "(instrumentos, equipamentos, materiais, software), obras e reformas, "
            "camisetas, troféus.\n" + linhas
        )
        corpo = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0},
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(corpo).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": UA},
            )
            with urllib.request.urlopen(req, timeout=120) as r:
                resp = json.loads(r.read().decode("utf-8"))
            texto = "".join(p.get("text", "") for p in resp["candidates"][0]["content"]["parts"])
            m = re.search(r"\{.*\}", texto, re.S)
            escolhidos = set(int(x) for x in json.loads(m.group(0))["culturais"]) if m else None
        except (OSError, ValueError, KeyError, IndexError, TypeError) as e:
            print(f"[aviso] Gemini na peneira de licitações: {e}; mantendo o lote", file=sys.stderr)
            escolhidos = None
        if escolhidos is None:
            mantidos.extend(lote)
        else:
            mantidos.extend(it for k, it in enumerate(lote) if k in escolhidos)
        time.sleep(1.0)
    print(f"[pncp] peneira Gemini: {len(itens)} -> {len(mantidos)}", file=sys.stderr)
    return mantidos


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
        itens = peneira_gemini(list(vistos.values()))
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
