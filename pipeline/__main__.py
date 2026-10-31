"""Linha de comando: python -m pipeline <comando>.

Comandos da Fase 1:
  import-seed   importa a planilha-semente para data/editais.json
  run           reprocessa (curadoria, status, prioridade) e exporta
  export        só exporta data/editais.json para uma pasta (JSON/CSV/XLSX/DB)
  report        imprime um resumo dos dados atuais
Fase 5:
  collect       roda os coletores (OJS, On the Move...) e junta ao data/editais.json
  conteudo      gera post semanal, carrossel, newsletter e alertas em content/
"""

import argparse
import logging
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from pipeline import config, db, overrides
from pipeline.enums import Status
from pipeline.export import formatos
from pipeline.models import Edital
from pipeline.processar import anexar_historico, processar

log = logging.getLogger("pipeline")


def _processar_e_gravar(editais: list[Edital], anteriores: dict[str, Edital]) -> list[Edital]:
    agora = datetime.now(UTC).replace(microsecond=0)
    hoje = config.hoje()
    processados, hist = processar(editais, anteriores, overrides.carregar(), hoje, agora)
    formatos.escrever_json(processados, config.EDITAIS_JSON)
    anexar_historico(hist, config.HISTORICO_JSONL)
    db.salvar(processados)
    log.info("gravados %d editais (%d mudanças no histórico)", len(processados), len(hist))
    return processados


def cmd_import_seed(args: argparse.Namespace) -> int:
    from pipeline.importers.seed_xlsx import importar

    res = importar(Path(args.arquivo))
    anteriores = (
        {e.id: e for e in formatos.ler_json(config.EDITAIS_JSON)}
        if config.EDITAIS_JSON.exists()
        else {}
    )
    # Mantém registros que não vieram da planilha (coleta, add-manual).
    ids_seed = {e.id for e in res.editais}
    outros = [
        e
        for i, e in anteriores.items()
        if i not in ids_seed and "carga_inicial" not in e.marcadores
    ]
    editais = [anteriores.get(e.id, e) if args.preservar else e for e in res.editais] + outros
    _processar_e_gravar(editais, anteriores)

    print(f"Linhas lidas na planilha: {res.linhas_lidas}")
    print(f"Registros após juntar duplicatas: {len(res.editais)} ({len(res.fusoes)} fusões)")
    for principal, fundido in res.fusoes:
        print(f"  - {fundido}  ->  {principal}")
    print(f"Pendências de revisão: {len(res.pendencias)}")
    for id_, motivo in res.pendencias:
        print(f"  - {id_}: {motivo}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    if not config.EDITAIS_JSON.exists():
        print("data/editais.json não existe. Rode primeiro: python -m pipeline import-seed")
        return 1
    editais = formatos.ler_json(config.EDITAIS_JSON)
    if not editais:
        print("ERRO: lista vazia — nada será publicado.")
        return 1
    processados = _processar_e_gravar(editais, {e.id: e for e in editais})
    if args.destino:
        _exportar(processados, Path(args.destino))
    return 0


def _exportar(editais: list[Edital], destino: Path) -> None:
    agora = datetime.now(UTC)
    formatos.escrever_json(editais, destino / "editais.json", gerado_em=agora)
    formatos.escrever_csv(editais, destino / "editais.csv")
    formatos.escrever_xlsx(editais, destino / "editais.xlsx")
    db.salvar(editais, destino / "editais.db")
    print(f"Exportado para {destino}: editais.json, editais.csv, editais.xlsx, editais.db")


def cmd_export(args: argparse.Namespace) -> int:
    _exportar(formatos.ler_json(config.EDITAIS_JSON), Path(args.destino))
    return 0


def cmd_report(_: argparse.Namespace) -> int:
    editais = formatos.ler_json(config.EDITAIS_JSON)
    visiveis = [e for e in editais if not e.curadoria.oculto]
    por_status = Counter(e.status.value for e in visiveis)
    print(f"Editais: {len(editais)} ({len(editais) - len(visiveis)} ocultos)")
    for st in Status:
        print(f"  {st.value:<12} {por_status.get(st.value, 0)}")
    print("Por fonte:")
    for fonte, n in Counter(e.fonte for e in editais).most_common():
        print(f"  {n:>4}  {fonte}")
    pend = [e for e in editais if e.revisao_pendente]
    print(f"Aguardando revisão: {len(pend)}")
    abertos = sorted(
        (e for e in visiveis if e.status in (Status.aberto, Status.prorrogado)),
        key=lambda e: -e.prioridade,
    )
    print("Top 10 por prioridade:")
    for e in abertos[:10]:
        print(f"  {e.prioridade:>3}  {e.data_limite or 'contínuo'!s:<10}  {e.titulo[:70]}")
    return 0


def cmd_collect(args: argparse.Namespace) -> int:
    """Roda os coletores da Fase 5 e junta o resultado ao data/editais.json.

    Registros já existentes mantêm curadoria, histórico e campos que o coletor não
    preenche; registros novos entram como revisão pendente quando faltar prazo.
    """
    from pipeline.collectors import registrados
    from pipeline.collectors.base import ler_fixture
    from pipeline.collectors.cambio import em_reais
    from pipeline.dedupe import chaves

    fabricas = registrados()
    nomes = [args.fonte] if args.fonte else list(fabricas)
    desconhecidos = [n for n in nomes if n not in fabricas]
    if desconhecidos:
        print(f"Coletor desconhecido: {', '.join(desconhecidos)}. Opções: {', '.join(fabricas)}")
        return 2

    coletados: list[Edital] = []
    for nome in nomes:
        try:
            if args.simular:
                # Sem rede: usa as fixtures salvas em tests/fixtures/.
                if nome == "onthemove":
                    from pipeline.collectors.onthemove import ColetorOnTheMove

                    url_situ = (
                        "https://on-the-move.org/news/situ-online-support-and-immersive-lab-"
                        "emerging-artists-creating-public-space-3rd-call"
                    )
                    col: object = ColetorOnTheMove(
                        ler_fixture("onthemove/feed.xml"),
                        {url_situ: ler_fixture("onthemove/item_in_situ.html")},
                    )
                elif nome == "ojs":
                    from pipeline.collectors.ojs import ColetorOJS

                    col = ColetorOJS(
                        {"pculturais": ler_fixture("ojs/pculturais_announcement.html")}
                    )
                else:
                    col = fabricas[nome]()
            else:
                col = fabricas[nome]()
            itens = col.coletar()  # type: ignore[attr-defined]
        except Exception as exc:
            log.error("coletor %s falhou: %s", nome, exc)
            continue
        log.info("coletor %s: %d itens", nome, len(itens))
        coletados.extend(itens)

    hoje = config.hoje()
    for e in coletados:
        if e.valor_original is not None and e.moeda and e.valor_brl_estimado is None:
            e.valor_brl_estimado = (
                None if args.simular else em_reais(e.valor_original, e.moeda, hoje)
            )
            e.cotacao_data = None if e.valor_brl_estimado is None else hoje

    if args.simular:
        for e in coletados:
            print(f"  [{e.vertical.value:<9}] {e.data_limite or '----------'}  {e.titulo[:80]}")
        print(f"Simulação: {len(coletados)} itens (nada gravado).")
        return 0

    anteriores = (
        {e.id: e for e in formatos.ler_json(config.EDITAIS_JSON)}
        if config.EDITAIS_JSON.exists()
        else {}
    )
    novos = 0
    for e in coletados:
        existente = anteriores.get(e.id) or next(
            (a for a in anteriores.values() if a.fonte == e.fonte and chaves(a) & chaves(e)), None
        )
        if existente is None:
            anteriores[e.id] = e
            novos += 1
            continue
        # Atualiza só o que o coletor sabe; preserva curadoria/histórico/marcadores manuais.
        dados = existente.model_dump()
        for campo in (
            "data_limite",
            "data_resumo",
            "prazo_texto",
            "resumo",
            "link_inscricao",
            "link_edital",
            "taxa_inscricao",
            "taxa_moeda",
            "cobre",
            "apc",
            "valor_original",
            "moeda",
            "valor_brl_estimado",
            "cotacao_data",
            "elegivel_brasileiros",
        ):
            if getattr(e, campo) not in (None, [], ""):
                dados[campo] = getattr(e, campo)
        dados["updated_at"] = e.updated_at
        dados["marcadores"] = sorted(set(existente.marcadores) | set(e.marcadores))
        anteriores[existente.id] = Edital.model_validate(dados)
    lista = list(anteriores.values())
    if not lista:
        print("Nada coletado e nada existente — nada gravado.")
        return 1
    _processar_e_gravar(
        lista,
        {e.id: e for e in formatos.ler_json(config.EDITAIS_JSON)}
        if config.EDITAIS_JSON.exists()
        else {},
    )
    print(f"Coleta: {len(coletados)} itens lidos, {novos} novos, {len(lista)} no total.")
    return 0


def cmd_conteudo(args: argparse.Namespace) -> int:
    from datetime import date

    from pipeline.content import weekly

    hoje = date.fromisoformat(args.data) if args.data else None
    gerados = weekly.gerar(hoje)
    for g in gerados:
        print(f"gerado: {g.relative_to(config.RAIZ)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    p = argparse.ArgumentParser(prog="python -m pipeline", description="Central de Editais")
    sub = p.add_subparsers(dest="comando", required=True)

    s = sub.add_parser("import-seed", help="importa a planilha-semente")
    s.add_argument("--arquivo", default=str(config.SEED_XLSX))
    s.add_argument(
        "--preservar",
        action="store_true",
        help="mantém a versão já gravada de registros que já existem",
    )
    s.set_defaults(func=cmd_import_seed)

    s = sub.add_parser("run", help="reprocessa e exporta")
    s.add_argument("--destino", help="pasta para as exportações públicas (ex.: site/public/api)")
    s.set_defaults(func=cmd_run)

    s = sub.add_parser("export", help="exporta JSON/CSV/XLSX/DB")
    s.add_argument("--destino", required=True)
    s.set_defaults(func=cmd_export)

    s = sub.add_parser("report", help="resumo dos dados atuais")
    s.set_defaults(func=cmd_report)

    s = sub.add_parser("collect", help="roda os coletores (Fase 5) e junta ao data/editais.json")
    s.add_argument("--fonte", help="só um coletor: ojs, onthemove")
    s.add_argument(
        "--simular",
        action="store_true",
        help="usa as fixtures de tests/ (sem rede) e não grava nada",
    )
    s.set_defaults(func=cmd_collect)

    s = sub.add_parser("conteudo", help="gera post semanal, carrossel, newsletter e alertas")
    s.add_argument("--data", help="AAAA-MM-DD de referência (padrão: hoje)")
    s.set_defaults(func=cmd_conteudo)

    for nome in ("add-manual", "check-links"):
        s = sub.add_parser(nome, help="(fase 3)")
        s.set_defaults(func=lambda _a, n=nome: print(f"'{n}' chega na fase 3.") or 2)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
