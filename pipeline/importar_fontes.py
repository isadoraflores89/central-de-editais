"""Importa as planilhas de fontes (config/fontes/*.xlsx) para config/fontes.yaml.

As planilhas são a fonte da verdade editorial: Isadora edita lá (nome, URL de editais,
frequência, prioridade, status). Este script só traduz para o YAML que os coletores leem.

Uso:  uv run python -m pipeline.importar_fontes
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import openpyxl
import yaml

from pipeline import config
from pipeline.textnorm import slugify

PASTA = config.CONFIG / "fontes"
SAIDA = config.CONFIG / "fontes.yaml"

PAISES = {
    "união europeia": "EU", "europa": "EU", "portugal": "PT", "espanha": "ES", "frança": "FR",
    "alemanha": "DE", "itália": "IT", "reino unido": "GB", "escócia": "GB", "irlanda": "IE",
    "país de gales": "GB", "países baixos": "NL", "suíça": "CH", "áustria": "AT", "bélgica": "BE",
    "dinamarca": "DK", "suécia": "SE", "noruega": "NO", "finlândia": "FI", "polônia": "PL",
    "república tcheca": "CZ", "grécia": "GR", "islândia": "IS", "ibero-américa": "IB",
    "américas": "AM", "américa latina": "LA", "argentina": "AR", "bolívia": "BO", "chile": "CL",
    "colômbia": "CO", "costa rica": "CR", "cuba": "CU", "república dominicana": "DO",
    "equador": "EC", "el salvador": "SV", "guatemala": "GT", "honduras": "HN", "méxico": "MX",
    "nicarágua": "NI", "panamá": "PA", "paraguai": "PY", "peru": "PE", "uruguai": "UY",
    "venezuela": "VE", "brasil / regional": "BR",
}  # fmt: skip


def _metodo(texto: str) -> str:
    t = (texto or "").lower()
    if "pesquisa por palavras" in t or "busca por objeto" in t:
        return "busca"
    if "monitorar instâncias" in t or "monitorar pró-reitorias" in t:
        return "manual"
    return "pagina"


def _frequencia(texto: str) -> str:
    return "diaria" if "diár" in (texto or "").lower() else "semanal"


def _prioridade(texto: str) -> int:
    return {"crítica": 3, "critica": 3, "alta": 2}.get((texto or "").strip().lower(), 1)


def _url(*cands: Any) -> str:
    for c in cands:
        s = str(c or "").strip()
        if s.lower().startswith("http"):
            return s
    return ""


def _linhas(ws: Any) -> list[dict[str, Any]]:
    linhas = list(ws.iter_rows(values_only=True))
    if not linhas:
        return []
    cab = [str(c or "").strip() for c in linhas[0]]
    return [dict(zip(cab, r, strict=False)) for r in linhas[1:] if any(c for c in r)]


def ler_brasil(caminho: Path) -> list[dict[str, Any]]:
    wb = openpyxl.load_workbook(caminho, read_only=True)
    saida = []
    for r in _linhas(wb["Fontes"]):
        nome = str(r.get("Instituição / fonte") or "").strip()
        url = _url(r.get("URL de editais / oportunidades"), r.get("URL institucional"))
        if not nome or not url:
            continue
        uf = str(r.get("UF") or "").strip().upper() or None
        abr = str(r.get("Abrangência") or "").strip().lower()
        saida.append(
            {
                "id": slugify(nome)[:50],
                "nome": nome,
                "grupo": str(r.get("Grupo") or "").strip(),
                "pais": "BR" if "internacional" not in abr else None,
                "abrangencia": "internacional"
                if "internacional" in abr
                else "estadual"
                if "estadual" in abr
                else "municipal"
                if "municipal" in abr
                else "nacional",
                "uf": uf,
                "url": url,
                "url_institucional": _url(r.get("URL institucional")) or None,
                "temas": str(r.get("Temas / oportunidades") or "").strip(),
                "metodo": _metodo(str(r.get("Método de coleta sugerido") or "")),
                "frequencia": _frequencia(str(r.get("Frequência sugerida") or "")),
                "prioridade": _prioridade(str(r.get("Prioridade") or "")),
                "observacoes": str(r.get("Observações") or "").strip() or None,
                "ativo": True,
            }
        )
    return saida


def ler_internacional(caminho: Path) -> list[dict[str, Any]]:
    wb = openpyxl.load_workbook(caminho, read_only=True)
    saida = []
    for aba, regiao in (
        ("Europa - fontes", "europa"),
        ("América Latina - fontes", "america_latina"),
    ):
        for r in _linhas(wb[aba]):
            nome = str(r.get("Instituição / programa") or "").strip()
            url = _url(
                r.get("URL de chamadas"), r.get("URL de convocatórias"), r.get("URL institucional")
            )
            if not nome or not url:
                continue
            pais_txt = str(r.get("País / abrangência") or "").strip().lower()
            saida.append(
                {
                    "id": slugify(nome)[:50],
                    "nome": nome,
                    "grupo": f"internacional:{regiao}",
                    "pais": PAISES.get(pais_txt, pais_txt[:2].upper() if pais_txt else None),
                    "abrangencia": "internacional",
                    "uf": None,
                    "url": url,
                    "url_institucional": _url(r.get("URL institucional")) or None,
                    "temas": str(r.get("Áreas / oportunidades") or "").strip(),
                    "metodo": _metodo(str(r.get("Método de monitoramento") or "")),
                    "frequencia": _frequencia(str(r.get("Frequência sugerida") or "")),
                    "prioridade": _prioridade(str(r.get("Prioridade") or "")),
                    "elegibilidade": str(r.get("Elegibilidade internacional") or "").strip()
                    or None,
                    "observacoes": str(r.get("Observações") or "").strip() or None,
                    "ativo": True,
                }
            )
    return saida


# fontes que já têm coletor próprio (não precisam do vigia de páginas)
COLETOR_PROPRIO = {"on-the-move": "coletor onthemove (RSS)"}


def importar() -> list[dict[str, Any]]:
    fontes: list[dict[str, Any]] = []
    for arq in sorted(PASTA.glob("*.xlsx")):
        nome = arq.name.lower()
        fontes.extend(ler_internacional(arq) if "internacional" in nome else ler_brasil(arq))
    # remove duplicatas (mesma URL de editais) e garante ids únicos
    vistos_url: set[str] = set()
    ids: set[str] = set()
    saida = []
    for f in fontes:
        chave = re.sub(r"/+$", "", f["url"].lower())
        if chave in vistos_url:
            continue
        vistos_url.add(chave)
        base, i = f["id"], 2
        while f["id"] in ids:
            f["id"] = f"{base}-{i}"
            i += 1
        ids.add(f["id"])
        if f["id"] in COLETOR_PROPRIO:
            f["ativo"] = False
            obs = str(f.get("observacoes") or "")
            f["observacoes"] = f"Lida por {COLETOR_PROPRIO[f['id']]}. {obs}".strip()
        saida.append({k: v for k, v in f.items() if v not in (None, "")})
    return saida


def main() -> int:
    fontes = importar()
    cab = (
        "# Fontes vigiadas pelo buscador (pipeline/collectors/paginas.py).\n"
        "# GERADO por `uv run python -m pipeline.importar_fontes` "
        "a partir de config/fontes/*.xlsx.\n"
        "# Edite as planilhas e rode o comando de novo; ajustes manuais aqui serão perdidos.\n"
        "# metodo: pagina (robô lê a página e acha links de editais) | "
        "busca (só pela busca na web)\n"
        "#         | manual (não é uma página única). frequencia: diaria | semanal.\n"
    )
    SAIDA.write_text(
        cab + yaml.safe_dump(fontes, allow_unicode=True, sort_keys=False, width=110),
        encoding="utf-8",
    )
    por_metodo = {
        m: sum(1 for f in fontes if f["metodo"] == m) for m in ("pagina", "busca", "manual")
    }
    print(f"{len(fontes)} fontes em {SAIDA.relative_to(config.RAIZ)}: {por_metodo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
