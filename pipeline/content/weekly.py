"""Conteúdo semanal para LinkedIn e newsletter (rascunhos; publicação é humana).

Gera, a partir de data/*.json e de config/brand.yaml:
  content/weekly/AAAA-WW.md             post de LinkedIn (<= 2.800 caracteres)
  content/weekly/AAAA-WW.carrossel.json 6–8 slides (título + 2 linhas)
  content/newsletter/AAAA-WW.md         mesmo conteúdo em formato de e-mail
  content/alertas/AAAA-MM-DD.md         itens com prioridade >= 80 ou prazo <= 7 dias

Nenhum link aponta para a fonte: tudo leva à página do item no site, para o
tráfego ir para o site (como pede o adendo).
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from pipeline import config
from pipeline.enums import Status, Vertical
from pipeline.export import formatos
from pipeline.models import Edital

LIMITE_POST = 2800
_PROPONENTE = {
    "pf": "pessoas físicas", "pj": "pessoas jurídicas", "mei": "MEI", "osc": "OSCs",
    "coletivo": "coletivos", "cooperativa": "cooperativas", "empresa": "empresas",
}  # fmt: skip
ROTULO_VERTICAL = {
    Vertical.fomento: "fomento",
    Vertical.open_call: "open call",
    Vertical.academico: "chamada acadêmica",
    Vertical.noticia: "notícia",
}


def semana_iso(d: date) -> str:
    ano, semana, _ = d.isocalendar()
    return f"{ano}-{semana:02d}"


def _link(b: dict[str, Any], e: Edital) -> str:
    """Link oficial do edital (a Central não tem mais páginas públicas; só a API)."""
    return str(e.link_inscricao or e.link_edital or e.source_url)


def _quem(e: Edital) -> str:
    if e.vertical == Vertical.academico:
        return "pesquisadores e docentes"
    if e.vertical == Vertical.open_call:
        return "artistas e coletivos"
    if not e.proponente:
        return "proponentes em geral"
    return ", ".join(_PROPONENTE.get(p.value, p.value) for p in e.proponente)


def _prazo(e: Edital, hoje: date) -> str:
    if e.fluxo_continuo:
        return "fluxo contínuo"
    if e.data_limite is None:
        return "prazo a confirmar"
    dias = (e.data_limite - hoje).days
    if dias == 0:
        return "encerra hoje"
    if dias == 1:
        return "encerra amanhã"
    faltam = f" (faltam {dias} dias)" if dias <= 10 else ""
    return f"até {e.data_limite.strftime('%d/%m')}{faltam}"


def selecionar(editais: list[Edital], hoje: date) -> dict[str, list[Edital]]:
    """Novos da semana, abertos por vertical e os que fecham em breve."""
    inicio = hoje - timedelta(days=7)
    visiveis = [
        e
        for e in editais
        if not e.curadoria.oculto
        and "alerta_taxa" not in e.marcadores
        and e.status in (Status.aberto, Status.prorrogado, Status.em_breve)
    ]
    novos = [e for e in visiveis if e.captured_at.date() >= inicio]
    destaques = sorted(visiveis, key=lambda e: (-e.prioridade, e.data_limite or date.max))
    fecham = [
        e for e in visiveis if e.data_limite is not None and 0 <= (e.data_limite - hoje).days <= 7
    ]
    return {"visiveis": visiveis, "novos": novos, "destaques": destaques, "fecham": fecham}


def montar_post(editais: list[Edital], hoje: date, b: dict[str, Any]) -> str:
    s = selecionar(editais, hoje)
    n_novos = len(s["novos"])
    n_int = len([e for e in s["novos"] if e.vertical == Vertical.open_call])
    n_grat = len(
        [e for e in s["novos"] if e.vertical == Vertical.open_call and e.taxa_inscricao == 0]
    )
    n_acad = len([e for e in s["novos"] if e.vertical == Vertical.academico])
    pessoal = b.get("voz", "pessoal") == "pessoal"
    gratuitas = f" ({n_grat} gratuitas)" if n_grat else ""
    sujeito = "eu" if pessoal else "o " + str(b["nome"])
    if n_novos:
        verbo = "mapeei" if pessoal else "mapeou"
        abertura = (
            f"Esta semana {sujeito} {verbo} {n_novos} oportunidades novas para quem vive de cultura"
            + (f", {n_int} internacionais{gratuitas}" if n_int else "")
            + (f" e {n_acad} chamadas acadêmicas" if n_acad else "")
            + "."
        )
    else:
        verbo = "sigo" if pessoal else "segue"
        abertura = (
            f"Semana sem novidades, mas {sujeito} {verbo} de olho: "
            f"{len(s['visiveis'])} oportunidades continuam abertas e estas fecham em breve."
        )
    escolhidos: list[Edital] = []
    vistos: set[str] = set()
    # mistura: primeiro o que fecha, depois por prioridade; no máximo 7, no mínimo 5 se houver
    for e in s["fecham"] + s["destaques"]:
        if e.id in vistos:
            continue
        vistos.add(e.id)
        escolhidos.append(e)
        if len(escolhidos) == 7:
            break
    linhas = [
        f"• {e.titulo[:90]} | {_quem(e)} | {_prazo(e, hoje)} | {_link(b, e)}" for e in escolhidos
    ]
    fecho = (
        f"A lista completa, com filtros por estado, linguagem e mecanismo, está em "
        f"https://{b.get('dominio_publico', b['dominio'])}. "
        + str(b.get("chamada_newsletter") or "")
    ).strip()
    hashtags = " ".join(f"#{h.lstrip('#')}" for h in (b.get("hashtags") or [])[:3])
    texto = "\n\n".join(p for p in [abertura, "\n".join(linhas), fecho, hashtags] if p)
    while len(texto) > LIMITE_POST and len(linhas) > 5:
        linhas.pop()
        texto = "\n\n".join(p for p in [abertura, "\n".join(linhas), fecho, hashtags] if p)
    return texto[:LIMITE_POST]


def montar_carrossel(editais: list[Edital], hoje: date, b: dict[str, Any]) -> list[dict[str, str]]:
    s = selecionar(editais, hoje)
    slides = [
        {
            "titulo": f"{len(s['novos'])} oportunidades novas esta semana",
            "linha1": f"{len(s['visiveis'])} abertas no total",
            "linha2": f"Atualizado em {hoje.strftime('%d/%m/%Y')}",
        }
    ]
    for e in (s["fecham"] + s["destaques"])[:6]:
        if any(sl.get("id") == e.id for sl in slides):
            continue
        slides.append(
            {
                "id": e.id,
                "titulo": e.titulo[:70],
                "linha1": f"{ROTULO_VERTICAL[e.vertical]} · {_quem(e)}",
                "linha2": _prazo(e, hoje) + (f" · {e.orgao}" if e.orgao else ""),
            }
        )
        if len(slides) == 7:
            break
    slides.append(
        {"titulo": b["nome"], "linha1": str(b.get("slogan") or ""), "linha2": b["dominio"]}
    )
    return slides


def _linha_nl(e: Edital, hoje: date, b: dict[str, Any]) -> str:
    return f"- **{e.titulo[:90]}**, {_quem(e)}, {_prazo(e, hoje)}. [agarrar]({_link(b, e)})"


def montar_newsletter(post: str, b: dict[str, Any], hoje: date) -> str:
    """Newsletter no tom descontraído (minúsculas, frases curtas, recado direto).

    Os trechos entre {{ }} são preenchidos pela Isadora no painel de disparos:
    {{NOME}} vira o nome de quem recebe; {{BABADOS}} e {{RECADO}} são os textos dela.
    O post (argumento) é ignorado: a newsletter é montada do zero a partir dos dados.
    """
    editais = formatos.ler_json(config.EDITAIS_JSON)
    s = selecionar(editais, hoje)
    fecham = s["fecham"][:5]
    novos = [
        e
        for e in s["novos"]
        if e.id not in {x.id for x in fecham} and e.vertical != Vertical.open_call
    ][:6]
    internacionais = [e for e in s["novos"] if e.vertical == Vertical.open_call][:4]
    n_abertas = len(s["visiveis"])

    assuntos = [
        f"{{{{NOME}}}}, {n_abertas} oportunidades abertas e {len(fecham)} fechando essa semana",
        "piscou, perdeu: tem edital fechando",
        "passando pra avisar que pintou oportunidade",
    ]
    partes = [
        f"# newsletter da semana {semana_iso(hoje)} ({hoje.strftime('%d/%m/%Y')})",
        "",
        "assunto (escolha um ou escreva o seu):",
        *[f"- {a}" for a in assuntos],
        "",
        "---",
        "",
        "{{NOME}},",
        "",
        "passando pra avisar que a semana tá cheia: "
        f"{n_abertas} oportunidades abertas pra quem vive de cultura, "
        f"{len(s['novos'])} chegaram agora. dá uma olhada, que isso aqui voa.",
        "",
        "## corre que fecha",
        "",
        "piscou, perdeu. esses encerram nos próximos 7 dias:",
        "",
    ]
    partes += [_linha_nl(e, hoje, b) for e in fecham] or [
        "- nada fechando nos próximos 7 dias. respira."
    ]
    partes += ["", "## chegou agora", "", "novidade fresquinha, ninguém viu ainda:", ""]
    partes += [_linha_nl(e, hoje, b) for e in novos] or [
        "- semana parada no fomento. a gente segue de olho."
    ]
    if internacionais:
        partes += ["", "## pra quem quer atravessar o oceano", ""]
        partes += [_linha_nl(e, hoje, b) for e in internacionais]
    partes += [
        "",
        "## babados da cultura",
        "",
        "{{BABADOS}}",
        "",
        "## o recado da isa",
        "",
        "{{RECADO}}",
        "",
        "---",
        "",
        "acho que você não deveria perder essa oportunidade, {{NOME}}. "
        f"a lista inteira, com filtro por estado, linguagem e mecanismo, tá em "
        f"https://{b.get('dominio_publico', b['dominio'])}. "
        + str(b.get("chamada_newsletter") or ""),
        "",
        str(b.get("assinatura") or ""),
        "",
    ]
    return "\n".join(partes)


def montar_alertas(editais: list[Edital], hoje: date, b: dict[str, Any]) -> str:
    s = selecionar(editais, hoje)
    urgentes = [
        e
        for e in s["novos"]
        if e.prioridade >= 80 or (e.data_limite and 0 <= (e.data_limite - hoje).days <= 7)
    ]
    if not urgentes:
        return ""
    linhas = [f"# Alertas de {hoje.strftime('%d/%m/%Y')}", ""]
    for e in urgentes:
        linhas.append(
            f"- **{e.titulo}** ({ROTULO_VERTICAL[e.vertical]}) — {_prazo(e, hoje)}, "
            f"prioridade {e.prioridade}. {_link(b, e)}"
        )
    return "\n".join(linhas) + "\n"


def gerar(hoje: date | None = None, raiz: Path | None = None) -> list[Path]:
    hoje = hoje or config.hoje()
    raiz = raiz or config.RAIZ / "content"
    b = config.brand()
    editais = formatos.ler_json(config.EDITAIS_JSON)
    semana = semana_iso(hoje)
    gerados: list[Path] = []

    post = montar_post(editais, hoje, b)
    p = raiz / "weekly" / f"{semana}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(post + "\n", encoding="utf-8")
    gerados.append(p)

    c = raiz / "weekly" / f"{semana}.carrossel.json"
    c.write_text(
        json.dumps(montar_carrossel(editais, hoje, b), ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    gerados.append(c)

    n = raiz / "newsletter" / f"{semana}.md"
    n.parent.mkdir(parents=True, exist_ok=True)
    n.write_text(montar_newsletter(post, b, hoje), encoding="utf-8")
    gerados.append(n)

    alertas = montar_alertas(editais, hoje, b)
    if alertas:
        a = raiz / "alertas" / f"{hoje.isoformat()}.md"
        a.parent.mkdir(parents=True, exist_ok=True)
        a.write_text(alertas, encoding="utf-8")
        gerados.append(a)
    gerados.append(escrever_indice(raiz))
    return gerados


def escrever_indice(raiz: Path) -> Path:
    """content/index.json: lista das semanas geradas, para o painel de disparos ler."""
    semanas = []
    for md in sorted((raiz / "weekly").glob("????-??.md"), reverse=True):
        semana = md.stem
        newsletter = raiz / "newsletter" / f"{semana}.md"
        carrossel = raiz / "weekly" / f"{semana}.carrossel.json"
        semanas.append(
            {
                "semana": semana,
                "gerado_em": date.fromtimestamp(md.stat().st_mtime).isoformat(),
                "post": f"content/weekly/{md.name}",
                "newsletter": f"content/newsletter/{newsletter.name}"
                if newsletter.exists()
                else None,
                "carrossel": f"content/weekly/{carrossel.name}" if carrossel.exists() else None,
            }
        )
    alertas = (
        sorted((raiz / "alertas").glob("????-??-??.md"), reverse=True)
        if (raiz / "alertas").exists()
        else []
    )
    idx = raiz / "index.json"
    idx.write_text(
        json.dumps(
            {"semanas": semanas, "alertas": [f"content/alertas/{a.name}" for a in alertas[:12]]},
            ensure_ascii=False,
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    return idx
