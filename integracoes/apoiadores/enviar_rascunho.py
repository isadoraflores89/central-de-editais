#!/usr/bin/env python3
"""Manda para a Isadora, por e-mail, o rascunho da newsletter da semana (quarta-feira).

Lê content/newsletter/AAAA-WW.md (semana ISO de hoje) e envia pelo Resend.
Variáveis: RESEND_API_KEY (obrigatória), EMAIL_REMETENTE (opcional),
EMAIL_RASCUNHO_PARA (padrão producao@isadoraflores.art.br).
Sem RESEND_API_KEY, só imprime o rascunho (útil no Actions sem segredo).
"""

from __future__ import annotations

import html
import json
import os
import sys
import urllib.request
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
REMETENTE_PADRAO = "Radar de Editais <radar@isadoraflores.art.br>"
PAINEL = "https://editais.isadoraflores.art.br/#disparos"


def main() -> int:
    hoje = date.today()
    ano, semana, _ = hoje.isocalendar()
    chave = f"{ano}-{semana:02d}"
    arq = RAIZ / "content" / "newsletter" / f"{chave}.md"
    if not arq.exists():
        print(f"[pulado] não existe {arq.relative_to(RAIZ)}")
        return 0
    texto = arq.read_text(encoding="utf-8")
    print(f"Rascunho da semana {chave}: {len(texto)} caracteres")

    chave_api = os.environ.get("RESEND_API_KEY", "").strip()
    if not chave_api:
        print("[pulado] sem RESEND_API_KEY; rascunho:\n")
        print(texto)
        return 0
    para = os.environ.get("EMAIL_RASCUNHO_PARA", "").strip() or "producao@isadoraflores.art.br"
    remetente = os.environ.get("EMAIL_REMETENTE", "").strip() or REMETENTE_PADRAO
    corpo = (
        "<p>Oi, Isa. Chegou o rascunho da newsletter desta semana. Ele já está no painel "
        f'(<a href="{PAINEL}">menu Disparos</a>) para você escrever o seu texto por cima e '
        "marcar como publicado na segunda.</p>"
        '<pre style="white-space:pre-wrap;font-family:inherit;font-size:16px;line-height:1.5">'
        + html.escape(texto)
        + "</pre>"
    )
    dados = json.dumps(
        {
            "from": remetente,
            "to": [para],
            "subject": f"Rascunho da newsletter, semana {chave}: escreve o seu texto até segunda",
            "html": corpo,
            "text": texto,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=dados,
        method="POST",
        headers={
            "Authorization": f"Bearer {chave_api}",
            "Content-Type": "application/json",
            "User-Agent": "central-de-editais/1.0 (+https://radardeeditais.isadoraflores.art.br)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"E-mail enviado para {para} (HTTP {r.status})")
    except Exception as exc:
        print(f"[erro] não enviou o e-mail: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
