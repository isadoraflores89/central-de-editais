#!/usr/bin/env python3
"""Envio do Radar de Editais aos apoiadores (editais.isadoraflores.art.br).

Roda todo dia no GitHub Actions (ver .github/workflows/envio-apoiadores.yml):
  1. lê os cadastros do formulário "preferencias" na Netlify;
  2. lê a lista de editais da Central (API pública);
  3. decide, pessoa por pessoa, o que mandar hoje;
  4. manda e-mail (Resend) e WhatsApp (template da Meta).

Regras (as mesmas da página de apoiadores):
  - Resumo semanal: toda segunda, para todo mundo.
  - Novos: todo dia, para quem pediu "imediato", só editais captados nas últimas 24 h.
  - Aviso de prazo: todo dia, para quem marcou aviso, editais com 7 dias ou 1 dia de prazo.
  - Sem nada para dizer, não manda.

Só biblioteca padrão. Variáveis de ambiente:
  NETLIFY_TOKEN            obrigatória — token pessoal da Netlify (lê os cadastros)
  NETLIFY_SITE_ID          padrão: o site editais-isadoraflores
  RESEND_API_KEY           para mandar e-mail; sem ela, e-mails são pulados
  EMAIL_REMETENTE          padrão: "Radar de Editais <radar@isadoraflores.art.br>"
  WHATSAPP_TOKEN           para mandar WhatsApp; sem ele, WhatsApp é pulado
  WHATSAPP_PHONE_NUMBER_ID idem
  WHATSAPP_TEMPLATE        padrão: radar_editais

Uso:
  python integracoes/apoiadores/enviar.py                 # envia
  python integracoes/apoiadores/enviar.py --simular       # só mostra quem receberia o quê
  python integracoes/apoiadores/enviar.py --dia 2026-10-19 --simular   # finge que hoje é outro dia
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Bahia")
FEED_URL = "https://radardeeditais.isadoraflores.art.br/api/editais.json"
FEED_LOCAL = os.path.join(os.path.dirname(__file__), "..", "..", "data", "editais.json")
SITE_URL = "https://editais.isadoraflores.art.br"
NETLIFY_SITE_ID_PADRAO = "b74ac8a2-95f2-4601-ab51-c87bfdd3d61c"
REMETENTE_PADRAO = "Radar de Editais <radar@isadoraflores.art.br>"

AREAS = {
    "audiovisual": "Audiovisual",
    "musica": "Música",
    "artes_cenicas": "Artes cênicas",
    "artes_visuais": "Artes visuais",
    "literatura": "Literatura",
    "patrimonio": "Patrimônio",
    "culturas_populares": "Culturas populares",
    "formacao": "Formação",
    "economia_criativa": "Economia criativa",
    "esporte": "Esporte",
}
MESES = [
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
]
DIAS_SEMANA = [
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
]

Edital = dict[str, Any]

# Modelos de HTML do e-mail (letra grande, contraste alto; funciona em qualquer leitor de e-mail)
CARTAO = (
    '<div style="border:1px solid #e3ded4;border-radius:12px;padding:14px 16px;'
    'margin:0 0 10px">'
    '<div style="font-size:18px;font-weight:700;line-height:1.3">'
    '<a href="{link}" style="color:#0a2f33">{titulo}</a></div>'
    '<div style="font-size:15px;color:#555;margin-top:4px">{orgao} · '
    '<b style="color:{cor}">{prazo}</b>{valor}</div>'
    '<div style="font-size:14px;color:#555;margin-top:2px">{areas}{ufs}</div>'
    "{resumo}</div>"
)
CORPO = (
    '<div style="font-family:Inter,Arial,sans-serif;max-width:640px;margin:0 auto;'
    'padding:24px;color:#222;font-size:16px;line-height:1.5">'
    '<p style="font-size:13px;letter-spacing:.12em;text-transform:uppercase;'
    'color:#4a7f3a;margin:0 0 6px">Radar de Editais · apoiadores</p>'
    '<h1 style="font-size:26px;margin:0 0 6px;color:#0a2f33">Olá, {nome}.</h1>'
    '<p style="margin:0;color:#555">{data}.</p>'
    "{blocos}"
    '<p style="margin:28px 0 0;font-size:14px;color:#555">Confira sempre prazos e regras '
    "no edital oficial. Para mudar seus filtros, entre em "
    '<a href="{site}" style="color:#0a2f33">{site_curto}</a>. '
    'Para parar de receber, responda este e-mail com "sair".</p>'
    '<p style="font-size:13px;color:#888;margin-top:16px">'
    "Isadora Flores · Flores Educação e Cultura</p>"
    "</div>"
)


# ----------------------------------------------------------------------------
# utilidades
# ----------------------------------------------------------------------------
def norm(texto: Any) -> str:
    s = unicodedata.normalize("NFD", str(texto or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def lista(valor: Any) -> list[str]:
    return [x.strip() for x in str(valor or "").split(",") if x.strip()]


def intersecta(a: list[str], b: list[str]) -> bool:
    return not b or any(x in b for x in a)


def http_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: int = 60,
) -> Any:
    dados = json.dumps(body).encode("utf-8") if body is not None else None
    cabecalhos = {"Accept": "application/json", **(headers or {})}
    if dados is not None:
        cabecalhos["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=dados, headers=cabecalhos)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


# ----------------------------------------------------------------------------
# fontes
# ----------------------------------------------------------------------------
def carregar_cadastros(token: str, site_id: str) -> list[dict[str, Any]]:
    url = f"https://api.netlify.com/api/v1/sites/{site_id}/submissions?per_page=100"
    resposta = http_json(url, headers={"Authorization": f"Bearer {token}"})
    return [s for s in resposta if s.get("form_name") == "preferencias" and s.get("data")]


def carregar_feed() -> list[Edital]:
    try:
        feed = http_json(FEED_URL)
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        print(f"[aviso] API fora do ar ({e}); usando data/editais.json", file=sys.stderr)
        with open(FEED_LOCAL, encoding="utf-8") as f:
            feed = json.load(f)
    editais: list[Edital] = feed["editais"] if isinstance(feed, dict) else feed
    return [e for e in editais if e.get("status") in ("aberto", "prorrogado")]


def apoiadores_unicos(cadastros: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """O cadastro mais recente de cada e-mail vence. E-mails @exemplo.com são teste."""
    por_email: dict[str, dict[str, Any]] = {}
    for s in sorted(cadastros, key=lambda s: str(s.get("created_at") or "")):
        email = norm(s["data"].get("email")).strip()
        if "@" not in email or email.endswith("@exemplo.com"):
            continue
        por_email[email] = s["data"]
    return list(por_email.values())


# ----------------------------------------------------------------------------
# cruzamento
# ----------------------------------------------------------------------------
class Perfil:
    def __init__(self, d: dict[str, Any]) -> None:
        self.nome = str(d.get("nome") or "").strip() or "apoiador"
        self.email = str(d.get("email") or "").strip()
        zap = re.sub(r"\D", "", str(d.get("whatsapp") or ""))
        self.whatsapp = ("55" + zap) if zap and len(zap) <= 11 else zap
        self.canais = lista(d.get("canais"))
        self.frequencia = str(d.get("frequencia") or "semanal").strip()
        self.aviso_prazo = "sim" in lista(d.get("aviso_prazo"))
        self.areas = lista(d.get("areas"))
        self.ufs = lista(d.get("ufs"))
        self.mecanismo = lista(d.get("mecanismo"))
        self.proponente = lista(d.get("proponente"))
        self.temas = [
            norm(t).lstrip("#")
            for t in str(d.get("temas") or "").split()
            if len(norm(t).lstrip("#")) > 2
        ]

    def combina(self, e: Edital) -> bool:
        texto = norm(
            " ".join(
                [
                    str(e.get("titulo") or ""),
                    str(e.get("resumo") or ""),
                    " ".join(e.get("publico_prioritario") or []),
                    " ".join((e.get("curadoria") or {}).get("tags") or []),
                    " ".join(e.get("areas") or []),
                ]
            )
        )
        texto = re.sub(r"[^a-z0-9]", "", texto)
        tema = any(t in texto for t in self.temas)
        local = (
            e.get("abrangencia") in ("nacional", "internacional")
            or not self.ufs
            or intersecta(e.get("ufs") or [], self.ufs)
        )
        bate = (
            intersecta(e.get("areas") or [], self.areas)
            and local
            and intersecta(e.get("mecanismo") or [], self.mecanismo)
            and intersecta(e.get("proponente") or [], self.proponente)
        )
        return bate or tema


def dias_restantes(e: Edital, hoje: date) -> int | None:
    if e.get("fluxo_continuo") or not e.get("data_limite"):
        return None
    return (date.fromisoformat(str(e["data_limite"])) - hoje).days


def eh_novo(e: Edital, agora: datetime) -> bool:
    cap = e.get("captured_at")
    if not cap:
        return False
    try:
        quando = datetime.fromisoformat(str(cap).replace("Z", "+00:00"))
    except ValueError:
        return False
    if quando.tzinfo is None:
        quando = quando.replace(tzinfo=FUSO)
    return quando >= agora - timedelta(hours=24)


def prazo_txt(e: Edital, hoje: date) -> str:
    d = dias_restantes(e, hoje)
    if e.get("fluxo_continuo"):
        return "Fluxo contínuo"
    if d is None:
        return str(e.get("prazo_texto") or "Prazo a confirmar")
    data = date.fromisoformat(str(e["data_limite"])).strftime("%d/%m/%Y")
    if d == 0:
        return f"Até {data} (último dia)"
    if d == 1:
        return f"Até {data} (falta 1 dia)"
    if d <= 7:
        return f"Até {data} (faltam {d} dias)"
    return f"Até {data}"


def link(e: Edital) -> str:
    return str(
        e.get("link_inscricao")
        or e.get("link_edital")
        or e.get("source_url")
        or f"https://radardeeditais.isadoraflores.art.br/edital/{e.get('id')}"
    )


def ordenar(editais: list[Edital]) -> list[Edital]:
    return sorted(editais, key=lambda e: str(e.get("data_limite") or "9999"))


# ----------------------------------------------------------------------------
# mensagens
# ----------------------------------------------------------------------------
def bloco_html(titulo: str, itens: list[Edital], hoje: date) -> str:
    if not itens:
        return ""
    partes = [f'<h2 style="font-size:20px;margin:28px 0 10px;color:#0a2f33">{titulo}</h2>']
    for e in itens:
        d = dias_restantes(e, hoje)
        cor = "#b3261e" if d is not None and d <= 7 else "#8a5a12"
        areas = ", ".join(AREAS.get(a, a) for a in e.get("areas") or [])
        ufs = ", ".join(e.get("ufs") or [])
        valor = f" · {html.escape(str(e['valor_texto']))}" if e.get("valor_texto") else ""
        resumo = (
            (
                f'<p style="font-size:15px;color:#333;margin:8px 0 0;line-height:1.45">'
                f"{html.escape(str(e['resumo']))}</p>"
            )
            if e.get("resumo")
            else ""
        )
        partes.append(
            CARTAO.format(
                link=html.escape(link(e)),
                titulo=html.escape(str(e.get("titulo") or "")),
                orgao=html.escape(str(e.get("orgao") or "")),
                cor=cor,
                prazo=html.escape(prazo_txt(e, hoje)),
                valor=valor,
                areas=html.escape(areas),
                ufs=" · " + html.escape(ufs) if ufs else "",
                resumo=resumo,
            )
        )
    return "".join(partes)


def bloco_texto(titulo: str, itens: list[Edital], hoje: date, maximo: int) -> str:
    if not itens:
        return ""
    linhas = []
    for e in itens[:maximo]:
        prazo = prazo_txt(e, hoje).replace("Até ", "até ").replace(" (", ", ").rstrip(")")
        linhas.append(f"{e.get('titulo')} ({prazo})")
    if len(itens) > maximo:
        linhas.append(f"e mais {len(itens) - maximo}")
    return f"{titulo}: {'; '.join(linhas)}. "


def montar_mensagens(
    apoiadores: list[dict[str, Any]], abertos: list[Edital], agora: datetime
) -> list[dict[str, str]]:
    hoje = agora.date()
    segunda = agora.weekday() == 0
    saida: list[dict[str, str]] = []
    for dados in apoiadores:
        p = Perfil(dados)
        meus = ordenar([e for e in abertos if p.combina(e)])
        prazo = [e for e in meus if dias_restantes(e, hoje) in (7, 1)] if p.aviso_prazo else []
        novos = [e for e in meus if eh_novo(e, agora)] if p.frequencia == "imediato" else []
        resumo = meus if segunda else []
        if not (prazo or novos or resumo):
            continue

        novos_so = [e for e in novos if e not in prazo]
        resumo_so = [e for e in resumo if e not in prazo and e not in novos]
        if prazo and not segunda:
            assunto = f"Prazo chegando: {prazo[0].get('titulo')}"
        elif novos and not segunda:
            assunto = f"Edital novo: {novos[0].get('titulo')}"
        else:
            assunto = f"Seu Radar de Editais da semana ({len(resumo)} abertos)"

        data_txt = f"{DIAS_SEMANA[agora.weekday()]}, {hoje.day} de {MESES[hoje.month - 1]}"
        corpo = CORPO.format(
            nome=html.escape(p.nome),
            data=data_txt,
            blocos=bloco_html("Prazo chegando", prazo, hoje)
            + bloco_html("Novos desta semana", novos_so, hoje)
            + bloco_html("Resumo da semana: editais abertos para o seu perfil", resumo_so, hoje),
            site=SITE_URL,
            site_curto=SITE_URL.removeprefix("https://"),
        )
        texto = (
            bloco_texto("PRAZO CHEGANDO", prazo, hoje, 3)
            + bloco_texto("NOVOS", novos_so, hoje, 3)
            + bloco_texto("ABERTOS PARA VOCÊ", resumo_so, hoje, 6)
        )
        texto = re.sub(r"\s+", " ", texto).strip()
        if len(texto) > 900:
            texto = re.sub(r"[^.;]*$", "", texto[:880]) + " (lista completa no e-mail)"

        if "email" in p.canais and p.email:
            saida.append(
                {
                    "canal": "email",
                    "para": p.email,
                    "nome": p.nome,
                    "assunto": assunto,
                    "html": corpo,
                    "texto": texto,
                }
            )
        if "whatsapp" in p.canais and len(p.whatsapp) >= 12:
            saida.append(
                {
                    "canal": "whatsapp",
                    "para": p.whatsapp,
                    "nome": p.nome,
                    "assunto": assunto,
                    "html": corpo,
                    "texto": texto,
                }
            )
    return saida


# ----------------------------------------------------------------------------
# envio
# ----------------------------------------------------------------------------
def enviar_email(m: dict[str, str], chave: str, remetente: str) -> None:
    http_json(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {chave}"},
        body={"from": remetente, "to": [m["para"]], "subject": m["assunto"], "html": m["html"]},
    )


def enviar_whatsapp(m: dict[str, str], token: str, phone_id: str, template: str) -> None:
    http_json(
        f"https://graph.facebook.com/v21.0/{phone_id}/messages",
        headers={"Authorization": f"Bearer {token}"},
        body={
            "messaging_product": "whatsapp",
            "to": m["para"],
            "type": "template",
            "template": {
                "name": template,
                "language": {"code": "pt_BR"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": m["nome"]},
                            {"type": "text", "text": m["texto"]},
                        ],
                    }
                ],
            },
        },
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Envio do Radar de Editais aos apoiadores")
    ap.add_argument("--simular", action="store_true", help="não envia, só mostra")
    ap.add_argument("--dia", help="AAAA-MM-DD para fingir outra data (teste)")
    args = ap.parse_args()

    agora = datetime.now(FUSO)
    if args.dia:
        agora = datetime.combine(date.fromisoformat(args.dia), agora.time(), FUSO)

    token = os.environ.get("NETLIFY_TOKEN", "").strip()
    if not token:
        print("[erro] falta NETLIFY_TOKEN", file=sys.stderr)
        return 1
    site_id = os.environ.get("NETLIFY_SITE_ID", NETLIFY_SITE_ID_PADRAO).strip()
    resend = os.environ.get("RESEND_API_KEY", "").strip()
    remetente = os.environ.get("EMAIL_REMETENTE", REMETENTE_PADRAO).strip()
    zap_token = os.environ.get("WHATSAPP_TOKEN", "").strip()
    zap_phone = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "").strip()
    zap_template = os.environ.get("WHATSAPP_TEMPLATE", "radar_editais").strip()

    cadastros = carregar_cadastros(token, site_id)
    apoiadores = apoiadores_unicos(cadastros)
    abertos = carregar_feed()
    mensagens = montar_mensagens(apoiadores, abertos, agora)
    print(
        f"[ok] {len(apoiadores)} apoiadores, {len(abertos)} editais abertos, "
        f"{len(mensagens)} mensagens para {agora:%d/%m/%Y} ({DIAS_SEMANA[agora.weekday()]})"
    )

    enviadas = puladas = falhas = 0
    for m in mensagens:
        rotulo = f"{m['canal']:8} {m['para']:35} {m['assunto']}"
        if args.simular:
            print(f"[simulação] {rotulo}\n            {m['texto'][:160]}")
            continue
        try:
            if m["canal"] == "email":
                if not resend:
                    print(f"[pulado] sem RESEND_API_KEY: {rotulo}")
                    puladas += 1
                    continue
                enviar_email(m, resend, remetente)
            else:
                if not (zap_token and zap_phone):
                    print(f"[pulado] sem WHATSAPP_TOKEN/PHONE_NUMBER_ID: {rotulo}")
                    puladas += 1
                    continue
                enviar_whatsapp(m, zap_token, zap_phone, zap_template)
            enviadas += 1
            print(f"[enviado] {rotulo}")
        except urllib.error.HTTPError as e:
            falhas += 1
            detalhe = e.read().decode("utf-8", "replace")[:300]
            print(f"[falha] {rotulo}: HTTP {e.code} {detalhe}", file=sys.stderr)
        except (urllib.error.URLError, TimeoutError) as e:
            falhas += 1
            print(f"[falha] {rotulo}: {e}", file=sys.stderr)

    if not args.simular:
        print(f"[ok] enviadas {enviadas}, puladas {puladas}, falhas {falhas}")
    return 1 if falhas and not enviadas else 0


if __name__ == "__main__":
    sys.exit(main())
