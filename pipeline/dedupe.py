"""Fusão de registros que descrevem o mesmo edital.

Chaves de igualdade (qualquer uma basta):
- mesma URL canônica de inscrição ou de edital (exceto URLs genéricas de listagem;
  se a URL for só a página inicial de uma plataforma, o órgão também precisa bater);
- mesmo título normalizado + mesmo órgão normalizado.

Na fusão, o registro "principal" mantém id, título, resumo e fonte; listas são
unidas; o id do outro vira alias; a fonte do outro vai para fontes_secundarias.
"""

from urllib.parse import urlsplit

from pipeline.models import Edital, FonteSecundaria
from pipeline.textnorm import normalizar, url_canonica, url_generica


def chaves(e: Edital) -> set[str]:
    ks: set[str] = set()
    orgao = normalizar(e.orgao)
    for url in (e.link_inscricao, e.link_edital):
        canon = url_canonica(url)
        if not canon or url_generica(url):
            continue
        if urlsplit(canon).path in ("", "/"):
            # Página inicial de plataforma (salic.cultura.gov.br, editaisapaa.org.br):
            # vários editais diferentes usam o mesmo link. Só vale junto com o órgão.
            if orgao:
                ks.add(f"urlraiz:{canon}|{orgao}")
        else:
            ks.add("url:" + canon)
    if e.orgao:
        ks.add(f"titulo:{normalizar(e.titulo)}|{normalizar(e.orgao)}")
    return ks


def _uniao[T](a: list[T], b: list[T]) -> list[T]:
    return a + [x for x in b if x not in a]


def fundir(principal: Edital, outro: Edital) -> Edital:
    p = principal.model_copy(deep=True)
    p.mecanismo = _uniao(p.mecanismo, outro.mecanismo)
    p.leis_estaduais = _uniao(p.leis_estaduais, outro.leis_estaduais)
    p.ufs = _uniao(p.ufs, outro.ufs)
    p.cidades = _uniao(p.cidades, outro.cidades)
    p.areas = _uniao(p.areas, outro.areas)
    p.publico_prioritario = _uniao(p.publico_prioritario, outro.publico_prioritario)
    p.proponente = _uniao(p.proponente, outro.proponente)
    p.marcadores = _uniao(p.marcadores, outro.marcadores)

    # Se alguma das fontes diz que exige projeto aprovado, vale a mais restritiva.
    exige = {p.exige_projeto_aprovado, outro.exige_projeto_aprovado}
    p.exige_projeto_aprovado = True if True in exige else (False if False in exige else None)
    for campo in (
        "orgao", "tipo_apoio", "abrangencia", "link_edital", "data_limite", "data_abertura",
        "valor_por_projeto_min", "valor_por_projeto_max", "valor_total", "valor_texto",
    ):
        if getattr(p, campo) is None and getattr(outro, campo) is not None:
            setattr(p, campo, getattr(outro, campo))
    p.fluxo_continuo = p.fluxo_continuo or outro.fluxo_continuo

    if outro.observacoes and outro.observacoes not in (p.observacoes or ""):
        p.observacoes = " | ".join(x for x in (p.observacoes, outro.observacoes) if x)

    p.fontes_secundarias = _uniao(
        p.fontes_secundarias,
        [FonteSecundaria(fonte=outro.fonte, url=str(outro.source_url),
                         captured_at=outro.captured_at), *outro.fontes_secundarias],
    )
    p.aliases = _uniao(p.aliases, [outro.id, *outro.aliases])
    p.aliases = [a for a in p.aliases if a != p.id]
    p.historico = p.historico + outro.historico
    p.revisao_pendente = p.revisao_pendente or outro.revisao_pendente
    return p


def deduplicar(editais: list[Edital]) -> tuple[list[Edital], list[tuple[str, str]]]:
    """Funde duplicatas mantendo a ordem de chegada (o primeiro vence).

    Devolve a lista resultante e os pares (id_principal, id_fundido).
    """
    resultado: list[Edital] = []
    indice: dict[str, int] = {}
    fusoes: list[tuple[str, str]] = []
    for e in editais:
        ks = chaves(e)
        alvo = next((indice[k] for k in ks if k in indice), None)
        if alvo is None:
            resultado.append(e)
            pos = len(resultado) - 1
        else:
            fusoes.append((resultado[alvo].id, e.id))
            resultado[alvo] = fundir(resultado[alvo], e)
            pos = alvo
        for k in chaves(resultado[pos]) | ks:
            indice[k] = pos
    return resultado, fusoes
