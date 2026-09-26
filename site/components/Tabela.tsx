"use client";

// Visão em tabela, como uma planilha. Mesma lista filtrada dos cartões.
import Link from "next/link";

import type { Ordem } from "@/lib/filtros";
import { diasRestantes, statusEfetivo, textoPrazo, urgencia } from "@/lib/prazo";
import { ABRANGENCIAS, MECANISMOS, STATUS, TIPOS, rotulo } from "@/lib/rotulos";
import { formatarData, formatarReais } from "@/lib/texto";
import type { Edital } from "@/lib/tipos";

import { LinkProtegido } from "./Cadastro";

const COR_PRAZO = {
  critica: "bg-critica-fundo text-critica font-bold",
  alta: "bg-alta-fundo text-alta font-bold",
  normal: "",
  nenhuma: "text-suave",
} as const;

function valor(e: Edital): string {
  const v = e.valor_por_projeto_max ?? e.valor_por_projeto_min;
  if (v !== null) return `${formatarReais(v)} por projeto`;
  if (e.valor_total !== null) return `${formatarReais(e.valor_total)} no total`;
  return "Não informado";
}

function onde(e: Edital): string {
  const abr = e.abrangencia ? rotulo(ABRANGENCIAS, e.abrangencia) : "Não informado";
  if (e.abrangencia === "nacional" || e.abrangencia === "internacional") return abr;
  const lugares = e.cidades.length ? e.cidades.join(", ") : e.ufs.join(", ");
  return lugares ? `${abr}: ${lugares}` : abr;
}

interface Props {
  editais: Edital[];
  hoje: string;
  ordem: Ordem;
  ordenar: (o: Ordem) => void;
}

function Cabecalho({ rotulo: r, ordem, alvo, ordenar }: { rotulo: string; ordem: Ordem; alvo?: Ordem; ordenar: (o: Ordem) => void }) {
  const ativo = alvo !== undefined && ordem === alvo;
  return (
    <th scope="col" aria-sort={ativo ? (alvo === "prazo" ? "ascending" : "descending") : undefined}
        className="border-b-2 border-marca bg-chip px-3 py-3 text-left align-bottom font-bold">
      {alvo ? (
        <button type="button" onClick={() => ordenar(alvo)} className="alvo inline-flex items-center gap-1 text-left underline decoration-1">
          {r}{ativo && <span aria-hidden="true"> ▾</span>}
          <span className="sr-only">{ativo ? "(ordenado)" : "(clique para ordenar)"}</span>
        </button>
      ) : r}
    </th>
  );
}

export function Tabela({ editais, hoje, ordem, ordenar }: Props) {
  return (
    <div
      role="region"
      aria-label="Tabela de editais (role para o lado para ver todas as colunas)"
      tabIndex={0}
      className="relative overflow-x-auto rounded-xl border-2 border-borda-suave bg-superficie"
    >
      <table className="w-full min-w-[68rem] border-collapse text-[1rem]">
        <caption className="sr-only">Editais filtrados, uma linha por edital</caption>
        <thead>
          <tr>
            <th scope="col" className="sticky left-0 z-10 border-b-2 border-marca bg-chip px-3 py-3 text-left align-bottom font-bold">
              Edital
            </th>
            <Cabecalho rotulo="Prazo" ordem={ordem} alvo="prazo" ordenar={ordenar} />
            <Cabecalho rotulo="Valor" ordem={ordem} alvo="valor" ordenar={ordenar} />
            <Cabecalho rotulo="Tipo" ordem={ordem} ordenar={ordenar} />
            <Cabecalho rotulo="Mecanismo" ordem={ordem} ordenar={ordenar} />
            <Cabecalho rotulo="Onde" ordem={ordem} ordenar={ordenar} />
            <Cabecalho rotulo="Situação" ordem={ordem} ordenar={ordenar} />
            <Cabecalho rotulo="Prioridade" ordem={ordem} alvo="prioridade" ordenar={ordenar} />
            <th scope="col" className="border-b-2 border-marca bg-chip px-3 py-3 text-left align-bottom font-bold">Links</th>
          </tr>
        </thead>
        <tbody>
          {editais.map((e, i) => {
            const dias = diasRestantes(e, hoje);
            const status = statusEfetivo(e, hoje);
            const nivel = status === "encerrado" ? "nenhuma" : urgencia(dias);
            const fundo = i % 2 ? "bg-fundo" : "bg-superficie";
            return (
              <tr key={e.id} className={`${fundo} align-top`}>
                <th scope="row" className={`sticky left-0 z-10 max-w-[22rem] border-b border-borda-suave px-3 py-3 text-left font-normal ${fundo}`}>
                  <Link href={`/edital/${e.id}/`} className="font-bold underline">{e.titulo}</Link>
                  {e.orgao && <span className="mt-1 block text-suave">{e.orgao}</span>}
                </th>
                <td className={`border-b border-borda-suave px-3 py-3 ${COR_PRAZO[nivel]}`}>
                  {textoPrazo(e, hoje)}
                  {e.data_limite && <span className="block font-normal">{formatarData(e.data_limite)}</span>}
                </td>
                <td className="border-b border-borda-suave px-3 py-3">{valor(e)}</td>
                <td className="border-b border-borda-suave px-3 py-3">{e.tipo_apoio ? rotulo(TIPOS, e.tipo_apoio) : "Não informado"}</td>
                <td className="border-b border-borda-suave px-3 py-3">
                  {e.mecanismo.length ? e.mecanismo.map((m) => rotulo(MECANISMOS, m)).join(", ") : "Não informado"}
                </td>
                <td className="border-b border-borda-suave px-3 py-3">{onde(e)}</td>
                <td className="border-b border-borda-suave px-3 py-3">{rotulo(STATUS, status)}</td>
                <td className="border-b border-borda-suave px-3 py-3 text-center">{e.prioridade}</td>
                <td className="border-b border-borda-suave px-3 py-3">
                  <div className="flex flex-col gap-2">
                    {e.link_inscricao && (
                      <LinkProtegido href={e.link_inscricao} edital={e.titulo} rotulo="Ir para a inscrição"
                        className="alvo inline-flex items-center justify-center rounded-lg bg-marca px-3 py-1.5 font-bold text-marca-texto">
                        Inscrever
                      </LinkProtegido>
                    )}
                    {e.link_edital && (
                      <LinkProtegido href={e.link_edital} edital={e.titulo} rotulo="Abrir o edital oficial"
                        className="alvo inline-flex items-center justify-center rounded-lg border-2 border-marca px-3 py-1.5 font-bold text-acento">
                        Edital
                      </LinkProtegido>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
