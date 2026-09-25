import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { valorResumido } from "@/components/Cartao";
import { IconeAlerta, IconeExterno } from "@/components/Icones";
import { SeloPrazo } from "@/components/SeloPrazo";
import { dataDoBuild, editais, editalPorId } from "@/lib/dados";
import {
  ABRANGENCIAS, AREAS, MECANISMOS, PROPONENTES, PUBLICOS, STATUS, TIPOS, rotulo,
} from "@/lib/rotulos";
import { formatarData, formatarReais } from "@/lib/texto";
import type { Edital } from "@/lib/tipos";

export const dynamicParams = false;

export function generateStaticParams() {
  // Ids fundidos (aliases) também ganham página, para links antigos não quebrarem.
  return editais().flatMap((e) => [{ id: e.id }, ...e.aliases.map((a) => ({ id: a }))]);
}

function achar(id: string): Edital | undefined {
  return editalPorId(id) ?? editais().find((e) => e.aliases.includes(id));
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const e = achar((await params).id);
  if (!e) return {};
  return {
    title: e.titulo,
    description: e.resumo ?? undefined,
    alternates: { canonical: `/edital/${e.id}/` },
  };
}

function Linha({ termo, children }: { termo: string; children: React.ReactNode }) {
  if (children === null || children === undefined || children === "" ||
      (Array.isArray(children) && children.length === 0)) {
    return null;
  }
  return (
    <div className="grid gap-1 border-b border-borda-suave py-3 sm:grid-cols-[14rem_1fr] sm:gap-4">
      <dt className="font-bold">{termo}</dt>
      <dd>{children}</dd>
    </div>
  );
}

const lista = (vals: string[], mapa: Record<string, string>) =>
  vals.length ? vals.map((v) => rotulo(mapa, v)).join(", ") : null;

function linkIssue(e: Edital): string {
  const repo = process.env.NEXT_PUBLIC_REPO;
  const titulo = `Erro no edital: ${e.titulo}`.slice(0, 200);
  const corpo = [
    `**Edital:** ${e.titulo}`,
    `**ID:** \`${e.id}\``,
    `**Página:** ${process.env.NEXT_PUBLIC_SITE_URL}/edital/${e.id}/`,
    "",
    "**O que está errado?**",
    "",
    "**Qual é a informação correta e onde ela aparece (link oficial)?**",
    "",
  ].join("\n");
  const q = new URLSearchParams({ title: titulo, body: corpo, labels: "erro-nos-dados" });
  return `https://github.com/${repo}/issues/new?${q.toString()}`;
}

export default async function PaginaEdital({ params }: { params: Promise<{ id: string }> }) {
  const e = achar((await params).id);
  if (!e) notFound();
  const hoje = dataDoBuild();
  const historico = [...e.historico].reverse();

  return (
    <article className="max-w-4xl">
      <p className="mb-4">
        <Link href="/" className="alvo inline-flex items-center font-bold text-acento underline">
          Voltar para a lista
        </Link>
      </p>
      <h1 className="text-[2rem] font-bold leading-tight">{e.titulo}</h1>
      {e.orgao && <p className="mt-2 text-[1.15rem] text-suave">{e.orgao}</p>}

      <div className="mt-4"><SeloPrazo edital={e} hoje={hoje} /></div>

      <div className="mt-5 flex flex-wrap gap-3">
        {e.link_inscricao && (
          <a href={e.link_inscricao} target="_blank" rel="noopener noreferrer"
             className="alvo inline-flex items-center gap-2 rounded-lg bg-marca px-5 py-2.5 font-bold text-marca-texto">
            Inscrever <IconeExterno /><span className="sr-only">(abre em nova aba)</span>
          </a>
        )}
        {e.link_edital && (
          <a href={e.link_edital} target="_blank" rel="noopener noreferrer"
             className="alvo inline-flex items-center gap-2 rounded-lg border-2 border-marca px-5 py-2.5 font-bold text-acento">
            Edital oficial <IconeExterno /><span className="sr-only">(abre em nova aba)</span>
          </a>
        )}
      </div>

      {e.resumo && <p className="mt-6 max-w-prose text-[1.1rem]">{e.resumo}</p>}

      {e.revisao_pendente && (
        <p className="mt-6 flex gap-2 rounded-lg border-2 border-alta bg-alta-fundo p-4 text-alta">
          <IconeAlerta className="mt-1 shrink-0" />
          <span>
            Este registro ainda está em revisão pela curadoria. Confira as informações no link oficial.
          </span>
        </p>
      )}

      <h2 className="mt-8 text-[1.4rem] font-bold">Detalhes</h2>
      <dl className="mt-2">
        <Linha termo="Situação">{rotulo(STATUS, e.status)}</Linha>
        <Linha termo="Prazo (como na fonte)">{e.prazo_texto}</Linha>
        <Linha termo="Data-limite">{e.data_limite && formatarData(e.data_limite)}</Linha>
        <Linha termo="Abertura">{e.data_abertura && formatarData(e.data_abertura)}</Linha>
        <Linha termo="Tipo de apoio">{e.tipo_apoio && rotulo(TIPOS, e.tipo_apoio)}</Linha>
        <Linha termo="Mecanismo">{lista(e.mecanismo, MECANISMOS)}</Linha>
        <Linha termo="Leis estaduais">{e.leis_estaduais.join(", ")}</Linha>
        <Linha termo="Exige projeto já aprovado em lei">
          {e.exige_projeto_aprovado === null ? "Não informado" : e.exige_projeto_aprovado ? "Sim" : "Não"}
        </Linha>
        <Linha termo="Abrangência">{e.abrangencia && rotulo(ABRANGENCIAS, e.abrangencia)}</Linha>
        <Linha termo="Estados">{e.ufs.join(", ")}</Linha>
        <Linha termo="Cidades">{e.cidades.join(", ")}</Linha>
        <Linha termo="Áreas">{lista(e.areas, AREAS)}</Linha>
        <Linha termo="Quem pode se inscrever">{lista(e.proponente, PROPONENTES)}</Linha>
        <Linha termo="Público prioritário">{lista(e.publico_prioritario, PUBLICOS)}</Linha>
        <Linha termo="Valor">{valorResumido(e)}</Linha>
        <Linha termo="Valor total">{e.valor_total !== null && formatarReais(e.valor_total)}</Linha>
        <Linha termo="Valores (texto da fonte)">{e.valor_texto}</Linha>
        <Linha termo="Observações">{e.observacoes}</Linha>
        <Linha termo="Prioridade na Central">{`${e.prioridade} de 100`}</Linha>
      </dl>

      <h2 className="mt-8 text-[1.4rem] font-bold">Fontes</h2>
      <ul className="mt-2 list-disc pl-6">
        <li>
          {e.fonte}:{" "}
          <a href={e.source_url} className="break-all text-acento underline" rel="noopener noreferrer">{e.source_url}</a>
          {" "}(capturado em {formatarData(e.captured_at)})
        </li>
        {e.fontes_secundarias.map((f) => (
          <li key={f.fonte}>
            {f.fonte}
            {f.url && <> : <a href={f.url} className="break-all text-acento underline" rel="noopener noreferrer">{f.url}</a></>}
          </li>
        ))}
      </ul>

      <h2 className="mt-8 text-[1.4rem] font-bold">Histórico de mudanças</h2>
      {historico.length === 0 ? (
        <p className="mt-2">Nenhuma mudança registrada desde a primeira captura ({formatarData(e.captured_at)}).</p>
      ) : (
        <ol className="mt-2 flex flex-col gap-2">
          {historico.map((h, i) => (
            <li key={i} className="rounded-lg border border-borda-suave p-3">
              <strong>{formatarData(h.em)}</strong>: {h.campo.replaceAll("_", " ")} mudou de{" "}
              <em>{String(h.antes ?? "vazio")}</em> para <em>{String(h.depois ?? "vazio")}</em>
              {h.motivo && ` (${h.motivo})`}
            </li>
          ))}
        </ol>
      )}

      <p className="mt-8">
        <a href={linkIssue(e)} target="_blank" rel="noopener noreferrer"
           className="alvo inline-flex items-center gap-2 font-bold text-acento underline">
          Encontrou um erro neste edital? Avise a curadoria <IconeExterno />
          <span className="sr-only">(abre o GitHub em nova aba)</span>
        </a>
      </p>
    </article>
  );
}
