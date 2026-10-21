"""Testes do envio aos apoiadores (integracoes/apoiadores/enviar.py)."""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "enviar", RAIZ / "integracoes" / "apoiadores" / "enviar.py"
)
assert _spec is not None and _spec.loader is not None
enviar = importlib.util.module_from_spec(_spec)
sys.modules["enviar"] = enviar
_spec.loader.exec_module(enviar)

FUSO = ZoneInfo("America/Bahia")
SEGUNDA = datetime(2026, 10, 19, 9, 0, tzinfo=FUSO)
QUARTA = datetime(2026, 10, 21, 9, 0, tzinfo=FUSO)


def edital(**kw: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "x",
        "titulo": "Edital X",
        "orgao": "Org",
        "status": "aberto",
        "abrangencia": "nacional",
        "ufs": [],
        "areas": ["musica"],
        "mecanismo": [],
        "proponente": [],
        "publico_prioritario": [],
        "curadoria": {"tags": []},
        "data_limite": "2026-10-31",
        "fluxo_continuo": False,
        "captured_at": "2026-09-24T12:00:00-03:00",
        "resumo": "Um edital de música.",
        "link_inscricao": "https://exemplo.org",
    }
    base.update(kw)
    return base


def cadastro(**data: object) -> dict[str, object]:
    d: dict[str, object] = {
        "nome": "Maria",
        "email": "maria@teste.org",
        "canais": "email",
        "frequencia": "semanal",
        "aviso_prazo": "sim",
    }
    d.update(data)
    return {"form_name": "preferencias", "created_at": "2026-10-20T10:00:00Z", "data": d}


def test_ultimo_cadastro_por_email_vence_e_teste_e_ignorado() -> None:
    cads = [
        cadastro(nome="Antiga"),
        {**cadastro(nome="Nova", email="MARIA@teste.org"), "created_at": "2026-10-21T10:00:00Z"},
        cadastro(nome="Teste", email="teste@exemplo.com"),
    ]
    unicos = enviar.apoiadores_unicos(cads)
    assert [u["nome"] for u in unicos] == ["Nova"]


def test_segunda_manda_resumo_filtrado() -> None:
    abertos = [
        edital(id="a", areas=["musica"]),
        edital(id="b", areas=["esporte"], titulo="Esporte"),
    ]
    msgs = enviar.montar_mensagens([cadastro(areas="musica")["data"]], abertos, SEGUNDA)
    assert len(msgs) == 1
    assert msgs[0]["canal"] == "email"
    assert "1 abertos" in msgs[0]["assunto"]
    assert "Esporte" not in msgs[0]["html"]


def test_quarta_sem_prazo_nao_manda_nada() -> None:
    msgs = enviar.montar_mensagens([cadastro()["data"]], [edital()], QUARTA)
    assert msgs == []


def test_aviso_de_prazo_em_7_dias_e_whatsapp_normalizado() -> None:
    abertos = [edital(data_limite="2026-10-28")]
    dados = cadastro(canais="email,whatsapp", whatsapp="71 9 8888-7777")["data"]
    msgs = enviar.montar_mensagens([dados], abertos, QUARTA)
    assert [m["canal"] for m in msgs] == ["email", "whatsapp"]
    assert msgs[1]["para"] == "5571988887777"
    assert msgs[0]["assunto"].startswith("Prazo chegando")
    assert "faltam 7 dias" in msgs[0]["texto"]


def test_tema_traz_edital_fora_dos_filtros() -> None:
    abertos = [edital(areas=["esporte"], titulo="Circuito de Hip Hop", resumo="Batalha de MCs")]
    dados = cadastro(areas="musica", temas="#hiphop")["data"]
    msgs = enviar.montar_mensagens([dados], abertos, SEGUNDA)
    assert len(msgs) == 1 and "Hip Hop" in msgs[0]["html"]


def test_estado_filtra_so_os_locais() -> None:
    abertos = [
        edital(id="n", abrangencia="nacional", titulo="Nacional"),
        edital(id="ba", abrangencia="estadual", ufs=["BA"], titulo="Bahia"),
        edital(id="sp", abrangencia="estadual", ufs=["SP"], titulo="Paulista"),
    ]
    msgs = enviar.montar_mensagens([cadastro(ufs="BA")["data"]], abertos, SEGUNDA)
    h = msgs[0]["html"]
    assert "Nacional" in h and "Bahia" in h and "Paulista" not in h
