"use client";

import { useId } from "react";

import type { Faceta, Filtros, Prazo } from "@/lib/filtros";
import { PRAZOS } from "@/lib/filtros";
import {
  ABRANGENCIAS, AREAS, MECANISMOS, PROPONENTES, PUBLICOS, STATUS, TIPOS, UFS, rotulo,
} from "@/lib/rotulos";
import { formatarReais } from "@/lib/texto";

export const ROTULOS_FACETA: Record<Faceta, { titulo: string; mapa: Record<string, string> }> = {
  tipo: { titulo: "Tipo de apoio", mapa: TIPOS },
  mec: { titulo: "Mecanismo", mapa: MECANISMOS },
  abr: { titulo: "Abrangência", mapa: ABRANGENCIAS },
  uf: { titulo: "Estado (UF)", mapa: UFS },
  area: { titulo: "Área / linguagem", mapa: AREAS },
  prop: { titulo: "Quem pode se inscrever", mapa: PROPONENTES },
  pub: { titulo: "Público prioritário", mapa: PUBLICOS },
  fonte: { titulo: "Fonte", mapa: {} },
  status: { titulo: "Situação", mapa: STATUS },
};

const ORDEM_FACETAS: Faceta[] = ["tipo", "mec", "abr", "uf", "area", "prop", "pub", "status", "fonte"];

export const ROTULOS_PRAZO: Record<Prazo, string> = {
  "7": "Próximos 7 dias",
  "15": "15 dias",
  "30": "30 dias",
  "60": "60 dias",
  continuo: "Fluxo contínuo",
};

// Degraus do controle de valor (escala não linear, mais fácil de usar).
export const DEGRAUS_VALOR = [0, 10_000, 20_000, 50_000, 100_000, 200_000, 500_000, 1_000_000, 5_000_000];

interface Props {
  filtros: Filtros;
  contagens: Record<Faceta, Map<string, number>>;
  mudar: (f: Filtros) => void;
}

function Grupo({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <fieldset className="border-t-2 border-borda-suave pt-4">
      <legend className="pr-2 text-[1.05rem] font-bold">{titulo}</legend>
      <div className="mt-2">{children}</div>
    </fieldset>
  );
}

function Caixa({
  marcado, aoMudar, children,
}: { marcado: boolean; aoMudar: (v: boolean) => void; children: React.ReactNode }) {
  return (
    <label className="alvo flex cursor-pointer items-center gap-3 rounded-md px-1 hover:bg-chip">
      <input type="checkbox" checked={marcado} onChange={(ev) => aoMudar(ev.target.checked)} />
      <span>{children}</span>
    </label>
  );
}

function FacetaLista({
  k, filtros, contagens, mudar,
}: Props & { k: Faceta }) {
  const { titulo, mapa } = ROTULOS_FACETA[k];
  const selecionados = filtros.facetas[k];
  const cont = contagens[k];
  const valores = [...new Set([...cont.keys(), ...selecionados])].sort(
    (a, b) => (cont.get(b) ?? 0) - (cont.get(a) ?? 0) || rotulo(mapa, a).localeCompare(rotulo(mapa, b), "pt-BR"),
  );
  if (!valores.length) return null;

  const alternar = (v: string, marcado: boolean) => {
    const novos = marcado ? [...selecionados, v] : selecionados.filter((s) => s !== v);
    mudar({ ...filtros, facetas: { ...filtros.facetas, [k]: novos } });
  };

  return (
    <Grupo titulo={titulo}>
      <ul>
        {valores.map((v) => (
          <li key={v}>
            <Caixa marcado={selecionados.includes(v)} aoMudar={(m) => alternar(v, m)}>
              {rotulo(mapa, v)} <span className="text-suave">({cont.get(v) ?? 0})</span>
            </Caixa>
          </li>
        ))}
      </ul>
      {k === "uf" && selecionados.length > 0 && (
        <Caixa
          marcado={filtros.nacionais}
          aoMudar={(m) => mudar({ ...filtros, nacionais: m })}
        >
          Incluir editais nacionais
        </Caixa>
      )}
    </Grupo>
  );
}

function indiceDoValor(v: number | null, padrao: number): number {
  if (v === null) return padrao;
  const i = DEGRAUS_VALOR.findIndex((d) => d >= v);
  return i === -1 ? DEGRAUS_VALOR.length - 1 : i;
}

function FaixaValor({ filtros, mudar }: Omit<Props, "contagens">) {
  const idMin = useId();
  const idMax = useId();
  const ultimo = DEGRAUS_VALOR.length - 1;
  const iMin = indiceDoValor(filtros.vmin, 0);
  const iMax = indiceDoValor(filtros.vmax, ultimo);
  const texto = (i: number, ehMax: boolean) =>
    ehMax && i === ultimo ? "sem limite" : formatarReais(DEGRAUS_VALOR[i] ?? 0);

  return (
    <Grupo titulo="Valor por projeto">
      <label htmlFor={idMin} className="block">
        Mínimo: <strong>{iMin === 0 ? "qualquer" : texto(iMin, false)}</strong>
      </label>
      <input
        id={idMin}
        type="range"
        className="w-full"
        min={0}
        max={ultimo}
        value={iMin}
        aria-valuetext={iMin === 0 ? "qualquer valor" : texto(iMin, false)}
        onChange={(ev) => {
          const i = Number(ev.target.value);
          mudar({ ...filtros, vmin: i === 0 ? null : DEGRAUS_VALOR[i] ?? null, vmax: i > iMax ? null : filtros.vmax });
        }}
      />
      <label htmlFor={idMax} className="mt-2 block">
        Máximo: <strong>{texto(iMax, true)}</strong>
      </label>
      <input
        id={idMax}
        type="range"
        className="w-full"
        min={0}
        max={ultimo}
        value={iMax}
        aria-valuetext={texto(iMax, true)}
        onChange={(ev) => {
          const i = Number(ev.target.value);
          mudar({ ...filtros, vmax: i === ultimo ? null : DEGRAUS_VALOR[i] ?? null, vmin: i < iMin ? null : filtros.vmin });
        }}
      />
      <Caixa marcado={filtros.vnull} aoMudar={(m) => mudar({ ...filtros, vnull: m })}>
        Incluir editais sem valor informado
      </Caixa>
    </Grupo>
  );
}

export function PainelFiltros({ filtros, contagens, mudar }: Props) {
  const idDe = useId();
  const idAte = useId();

  const alternarPrazo = (p: Prazo) => {
    const ativo = filtros.prazo.includes(p);
    mudar({ ...filtros, prazo: ativo ? filtros.prazo.filter((x) => x !== p) : [...filtros.prazo, p] });
  };

  return (
    <div className="flex flex-col gap-5">
      <Grupo titulo="Prazo">
        <div className="flex flex-wrap gap-2" role="group" aria-label="Prazo de inscrição">
          {PRAZOS.map((p) => {
            const ativo = filtros.prazo.includes(p);
            return (
              <button
                key={p}
                type="button"
                aria-pressed={ativo}
                onClick={() => alternarPrazo(p)}
                className={`alvo rounded-full border-2 px-4 py-1.5 font-bold ${
                  ativo ? "border-marca bg-marca text-marca-texto" : "border-borda bg-superficie text-texto hover:bg-chip"
                }`}
              >
                {ROTULOS_PRAZO[p]}
              </button>
            );
          })}
        </div>
        <div className="mt-3 grid grid-cols-2 gap-3">
          <div>
            <label htmlFor={idDe} className="block">Prazo a partir de</label>
            <input
              id={idDe}
              type="date"
              value={filtros.de ?? ""}
              onChange={(ev) => mudar({ ...filtros, de: ev.target.value || null })}
              className="alvo w-full rounded-md border-2 border-borda bg-superficie px-2"
            />
          </div>
          <div>
            <label htmlFor={idAte} className="block">Prazo até</label>
            <input
              id={idAte}
              type="date"
              value={filtros.ate ?? ""}
              onChange={(ev) => mudar({ ...filtros, ate: ev.target.value || null })}
              className="alvo w-full rounded-md border-2 border-borda bg-superficie px-2"
            />
          </div>
        </div>
      </Grupo>

      <Grupo titulo="Atalhos">
        <Caixa marcado={filtros.pf} aoMudar={(m) => mudar({ ...filtros, pf: m })}>
          Só quem aceita pessoa física
        </Caixa>
        <Caixa marcado={filtros.semAprovado} aoMudar={(m) => mudar({ ...filtros, semAprovado: m })}>
          Só quem não exige projeto já aprovado em lei
        </Caixa>
        <Caixa marcado={filtros.destaques} aoMudar={(m) => mudar({ ...filtros, destaques: m })}>
          Só destaques da curadoria
        </Caixa>
        <Caixa marcado={filtros.encerrados} aoMudar={(m) => mudar({ ...filtros, encerrados: m })}>
          Mostrar encerrados
        </Caixa>
      </Grupo>

      <FaixaValor filtros={filtros} mudar={mudar} />

      {ORDEM_FACETAS.map((k) => (
        <FacetaLista key={k} k={k} filtros={filtros} contagens={contagens} mudar={mudar} />
      ))}
    </div>
  );
}
