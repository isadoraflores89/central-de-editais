"""Cotação PTAX do Banco Central (API aberta, sem chave) para estimar valores em R$.

Usa a série "CotacaoMoedaDia" do Olinda/BCB. Se a API falhar, devolve None e o
valor fica só na moeda original (o site mostra "valor em EUR" sem estimativa).
"""

from __future__ import annotations

import json
import urllib.request
from datetime import date, timedelta
from functools import cache

URL = (
    "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
    "CotacaoMoedaDia(moeda=@moeda,dataCotacao=@data)?@moeda='{moeda}'&@data='{data}'"
    "&$top=1&$orderby=dataHoraCotacao%20desc&$format=json"
)


@cache
def cotacao(moeda: str, dia: date) -> float | None:
    """Valor de 1 unidade da moeda em R$ (venda PTAX) no dia útil mais próximo."""
    moeda = moeda.upper()
    if moeda == "BRL":
        return 1.0
    for recuo in range(0, 6):  # feriados/fim de semana: volta até 5 dias
        d = dia - timedelta(days=recuo)
        url = URL.format(moeda=moeda, data=d.strftime("%m-%d-%Y"))
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                dados = json.loads(r.read().decode("utf-8"))
        except (OSError, ValueError):
            return None
        valores = dados.get("value") or []
        if valores:
            try:
                return float(valores[0]["cotacaoVenda"])
            except (KeyError, TypeError, ValueError):
                return None
    return None


def em_reais(valor: float | None, moeda: str | None, dia: date) -> float | None:
    if valor is None or not moeda:
        return None
    c = cotacao(moeda, dia)
    return round(valor * c, 2) if c else None
