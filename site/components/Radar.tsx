"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useId, useMemo, useRef, useState } from "react";

import { baixarCsv, baixarXlsx } from "@/lib/exportar";
import {
  FACETAS, ORDENS, contarAtivos, contarFacetas, escreverFiltros, filtrar, filtrosVazios, lerFiltros,
  type Filtros, type Ordem,
} from "@/lib/filtros";
import { hojeISO } from "@/lib/prazo";
import { rotulo } from "@/lib/rotulos";
import type { Edital, Preset } from "@/lib/tipos";

import { useCadastro } from "./Cadastro";
import { Cartao } from "./Cartao";
import { IconeBusca, IconeDownload, IconeFechar, IconeFiltro } from "./Icones";
import { PainelFiltros, ROTULOS_FACETA, ROTULOS_PRAZO } from "./PainelFiltros";
import { Tabela } from "./Tabela";

const ROTULOS_ORDEM: Record<Ordem, string> = {
  prioridade: "Prioridade",
  prazo: "Prazo mais próximo",
  valor: "Maior valor",
  recentes: "Recém-adicionados",
  atualizados: "Atualizados recentemente",
};

interface Props {
  editais: Edital[];
  presets: Preset[];
  hojeBuild: string;
  /** Filtros aplicados quando a URL não tem nenhum (páginas /parecerista etc.). */
  filtrosPadrao?: string;
}

export function Radar({ editais, presets, hojeBuild, filtrosPadrao = "" }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const qs = params.toString() || filtrosPadrao;
  const filtros = useMemo(() => lerFiltros(new URLSearchParams(qs)), [qs]);

  // O HTML estático usa a data do build; no navegador, a data real (decisão D4).
  const [hoje, setHoje] = useState(hojeBuild);
  useEffect(() => setHoje(hojeISO()), []);

  const { pedir } = useCadastro();
  const [painelAberto, setPainelAberto] = useState(false);
  const [busca, setBusca] = useState(filtros.q);
  useEffect(() => setBusca(filtros.q), [filtros.q]);

  const mudar = (f: Filtros) => {
    const novo = escreverFiltros(f).toString();
    router.replace(novo ? `${pathname}?${novo}` : `${pathname}?`, { scroll: false });
  };

  // Busca com pequeno atraso para não reescrever a URL a cada tecla.
  const temporizador = useRef<ReturnType<typeof setTimeout>>(undefined);
  const aoDigitar = (valor: string) => {
    setBusca(valor);
    clearTimeout(temporizador.current);
    temporizador.current = setTimeout(() => mudar({ ...filtros, q: valor }), 300);
  };

  const resultado = useMemo(() => filtrar(editais, filtros, hoje), [editais, filtros, hoje]);
  const contagens = useMemo(() => contarFacetas(editais, filtros, hoje), [editais, filtros, hoje]);
  const ativos = contarAtivos(filtros);

  const idBusca = useId();
  const idOrdem = useId();
  const idPainel = useId();

  const chipsAtivos: { rotulo: string; remover: () => void }[] = [];
  for (const k of FACETAS) {
    for (const v of filtros.facetas[k]) {
      chipsAtivos.push({
        rotulo: `${ROTULOS_FACETA[k].titulo}: ${rotulo(ROTULOS_FACETA[k].mapa, v)}`,
        remover: () => mudar({ ...filtros, facetas: { ...filtros.facetas, [k]: filtros.facetas[k].filter((x) => x !== v) } }),
      });
    }
  }
  for (const p of filtros.prazo) {
    chipsAtivos.push({ rotulo: `Prazo: ${ROTULOS_PRAZO[p]}`, remover: () => mudar({ ...filtros, prazo: filtros.prazo.filter((x) => x !== p) }) });
  }
  if (filtros.q.trim()) chipsAtivos.push({ rotulo: `Busca: "${filtros.q}"`, remover: () => mudar({ ...filtros, q: "" }) });

  return (
    <div>
      {presets.length > 0 && (
        <nav aria-label="Buscas prontas" className="mb-6">
          <h2 className="titulo-display mb-3 text-[1.35rem] font-bold">Buscas prontas</h2>
          <ul className="flex flex-wrap gap-2">
            {presets.map((p) => {
              const ativo = params.toString() === p.filtros;
              return (
                <li key={p.id}>
                  <span id={`preset-${p.id}`} hidden>{p.descricao}</span>
                  <button
                    type="button"
                    aria-describedby={`preset-${p.id}`}
                    aria-pressed={ativo}
                    onClick={() => router.replace(`${pathname}?${p.filtros}`, { scroll: false })}
                    className={`alvo rounded-lg border-2 px-4 py-2 font-bold ${
                      ativo ? "border-marca bg-marca text-marca-texto shadow-[0_3px_0_0_var(--amarelo)]" : "border-marca bg-superficie text-acento hover:bg-chip"
                    }`}
                  >
                    {p.rotulo}
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>
      )}

      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-end">
        <div className="flex-1">
          <label htmlFor={idBusca} className="mb-1 block font-bold">
            Buscar por nome, órgão, cidade ou palavra do resumo
          </label>
          <div className="relative">
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-suave">
              <IconeBusca />
            </span>
            <input
              id={idBusca}
              type="search"
              value={busca}
              onChange={(ev) => aoDigitar(ev.target.value)}
              placeholder="ex.: audiovisual, Petrobras, Salvador"
              className="alvo w-full rounded-lg border-2 border-borda bg-superficie py-2 pl-11 pr-3 text-[1.05rem]"
            />
          </div>
        </div>
        <div>
          <label htmlFor={idOrdem} className="mb-1 block font-bold">Ordenar por</label>
          <select
            id={idOrdem}
            value={filtros.ordem}
            onChange={(ev) => mudar({ ...filtros, ordem: ev.target.value as Ordem })}
            className="alvo w-full rounded-lg border-2 border-borda bg-superficie px-3 md:w-auto"
          >
            {ORDENS.map((o) => <option key={o} value={o}>{ROTULOS_ORDEM[o]}</option>)}
          </select>
        </div>
      </div>

      <div className="lg:grid lg:grid-cols-[20rem_1fr] lg:gap-8">
        <div>
          <button
            type="button"
            className="alvo mb-4 inline-flex w-full items-center justify-center gap-2 rounded-lg border-2 border-marca bg-superficie px-4 py-2 font-bold text-acento lg:hidden"
            aria-expanded={painelAberto}
            aria-controls={idPainel}
            onClick={() => setPainelAberto((v) => !v)}
          >
            <IconeFiltro /> {painelAberto ? "Esconder filtros" : "Mostrar filtros"}
            {ativos > 0 && ` (${ativos} ativos)`}
          </button>
          <aside
            id={idPainel}
            aria-label="Filtros"
            className={`${painelAberto ? "block" : "hidden"} mb-6 rounded-2xl border-2 border-borda-suave bg-superficie p-4 lg:sticky lg:top-4 lg:block lg:max-h-[calc(100vh-2rem)] lg:overflow-y-auto`}
          >
            <PainelFiltros filtros={filtros} contagens={contagens} mudar={mudar} />
          </aside>
        </div>

        <section aria-labelledby="titulo-resultados">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <h2 id="titulo-resultados" className="titulo-display text-[1.6rem] font-extrabold">
              <span role="status" aria-live="polite" aria-atomic="true">
                {resultado.length === 1 ? "1 edital encontrado" : `${resultado.length} editais encontrados`}
              </span>
            </h2>
            <div className="flex flex-wrap gap-2">
              <div role="group" aria-label="Ver como" className="inline-flex overflow-hidden rounded-lg border-2 border-marca">
                {(["cartoes", "tabela"] as const).map((v) => (
                  <button
                    key={v}
                    type="button"
                    aria-pressed={filtros.visao === v}
                    onClick={() => mudar({ ...filtros, visao: v })}
                    className={`alvo px-3 py-1.5 font-bold ${filtros.visao === v ? "bg-marca text-marca-texto" : "bg-superficie text-acento hover:bg-chip"}`}
                  >
                    {v === "cartoes" ? "Cartões" : "Tabela"}
                  </button>
                ))}
              </div>
              <button
                type="button"
                onClick={() => pedir({ rotulo: "Baixar CSV", aoLiberar: () => baixarCsv(resultado, hoje) })}
                className="alvo inline-flex items-center gap-2 rounded-lg border-2 border-borda px-3 py-1.5 font-bold hover:bg-chip"
              >
                <IconeDownload /> CSV <span className="sr-only">da lista filtrada</span>
              </button>
              <button
                type="button"
                onClick={() => pedir({ rotulo: "Baixar planilha", aoLiberar: () => void baixarXlsx(resultado, hoje) })}
                className="alvo inline-flex items-center gap-2 rounded-lg border-2 border-borda px-3 py-1.5 font-bold hover:bg-chip"
              >
                <IconeDownload /> Planilha Excel <span className="sr-only">da lista filtrada</span>
              </button>
            </div>
          </div>

          {(chipsAtivos.length > 0 || ativos > 0) && (
            <div className="mb-4 flex flex-wrap items-center gap-2">
              {chipsAtivos.map((c) => (
                <button
                  key={c.rotulo}
                  type="button"
                  onClick={c.remover}
                  className="alvo inline-flex items-center gap-1 rounded-full border-2 border-marca bg-chip px-3 py-1"
                >
                  {c.rotulo} <IconeFechar /><span className="sr-only">remover filtro</span>
                </button>
              ))}
              <button
                type="button"
                onClick={() => mudar(filtrosVazios())}
                className="alvo px-2 font-bold text-acento underline"
              >
                Limpar todos os filtros
              </button>
            </div>
          )}

          {resultado.length === 0 ? (
            <div className="rounded-xl border-2 border-dashed border-borda p-8 text-center">
              <p className="text-[1.1rem] font-bold">Nenhum edital com esses filtros.</p>
              <p className="mt-2">Tente tirar algum filtro ou marcar &quot;Mostrar encerrados&quot;.</p>
            </div>
          ) : filtros.visao === "tabela" ? (
            <Tabela editais={resultado} hoje={hoje} ordem={filtros.ordem} ordenar={(o) => mudar({ ...filtros, ordem: o })} />
          ) : (
            <ol className="flex flex-col gap-5">
              {resultado.map((e, i) => (
                <li key={e.id} className="entrada" style={{ "--i": i } as React.CSSProperties}>
                  <Cartao edital={e} hoje={hoje} />
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>
    </div>
  );
}
