import Link from "next/link";

import { diasRestantes, ehNovo, statusEfetivo, textoPrazo, urgencia } from "@/lib/prazo";
import { ABRANGENCIAS, MECANISMOS, TIPOS, rotulo } from "@/lib/rotulos";
import { formatarData, formatarReais } from "@/lib/texto";
import type { Edital } from "@/lib/tipos";

import { LinkProtegido } from "./Cadastro";
import { IconeEstrela, IconeExterno, IconeLocal, IconeMoeda } from "./Icones";

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <li className="rounded-md border border-borda-suave bg-chip px-2.5 py-0.5 text-[0.95rem]">
      {children}
    </li>
  );
}

function Selo({ children, classe }: { children: React.ReactNode; classe: string }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[0.9rem] font-bold ${classe}`}>
      {children}
    </span>
  );
}

export function valorResumido(e: Edital): string | null {
  const { valor_por_projeto_min: min, valor_por_projeto_max: max } = e;
  if (min !== null && max !== null && min !== max) return `${formatarReais(min)} a ${formatarReais(max)} por projeto`;
  if (max !== null) return `Até ${formatarReais(max)} por projeto`;
  if (min !== null) return `A partir de ${formatarReais(min)} por projeto`;
  if (e.valor_total !== null) return `${formatarReais(e.valor_total)} no total`;
  return null;
}

function local(e: Edital): string | null {
  if (e.abrangencia === "nacional" || e.abrangencia === "internacional") return null;
  if (e.cidades.length) return e.cidades.join(", ");
  return e.ufs.length ? e.ufs.join(", ") : null;
}

/** Bloco de calendário com o prazo: o elemento mais forte do cartão. */
function BlocoPrazo({ e, hoje }: { e: Edital; hoje: string }) {
  const status = statusEfetivo(e, hoje);
  const dias = diasRestantes(e, hoje);
  const nivel = status === "encerrado" ? "nenhuma" : urgencia(dias);
  const cor = {
    critica: "bg-critica-fundo text-critica border-critica",
    alta: "bg-alta-fundo text-alta border-alta",
    normal: "bg-prazo-fundo text-prazo border-prazo",
    nenhuma: "bg-chip text-suave border-borda-suave",
  }[nivel];
  const base = `flex flex-row items-center gap-3 rounded-xl border-2 px-4 py-3 sm:flex-col sm:items-center sm:justify-center sm:gap-0 sm:self-start sm:px-2 sm:py-5 sm:text-center ${cor}`;

  let grande: string;
  let pequeno: string;
  if (status === "encerrado") { grande = "Fim"; pequeno = "encerrado"; }
  else if (dias === null) { grande = e.fluxo_continuo ? "Ano" : "?"; pequeno = e.fluxo_continuo ? "todo aberto" : "prazo a confirmar"; }
  else if (dias === 0) { grande = "Hoje"; pequeno = "último dia"; }
  else { grande = String(dias); pequeno = dias === 1 ? "dia" : "dias"; }

  return (
    <div className={base}>
      <p aria-hidden="true" className="titulo-display text-[2.4rem] font-extrabold leading-none sm:text-[2.8rem]">{grande}</p>
      <p aria-hidden="true" className="font-bold leading-tight">{pequeno}</p>
      {e.data_limite && <p aria-hidden="true" className="ml-auto text-[0.95rem] sm:ml-0 sm:mt-1">{formatarData(e.data_limite)}</p>}
      <p className="sr-only">{textoPrazo(e, hoje)}{e.data_limite ? `, data-limite ${formatarData(e.data_limite)}` : ""}</p>
    </div>
  );
}

export function Cartao({ edital: e, hoje, compacto = false }: { edital: Edital; hoje: string; compacto?: boolean }) {
  const status = statusEfetivo(e, hoje);
  const valor = valorResumido(e);
  const onde = local(e);
  const base = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
  return (
    <article
      className={`group grid gap-4 rounded-2xl border-2 bg-superficie p-4 shadow-[0_2px_0_0_var(--borda-suave)] transition-transform sm:grid-cols-[7.5rem_1fr] sm:gap-6 sm:p-5 ${
        e.curadoria.destaque ? "border-marca" : "border-borda-suave"
      } hover:-translate-y-0.5`}
      aria-labelledby={`t-${e.id}`}
    >
      <BlocoPrazo e={e} hoje={hoje} />

      <div className="min-w-0">
        <div className="mb-2 flex flex-wrap gap-2 empty:hidden">
          {e.curadoria.destaque && (
            <Selo classe="bg-amarelo text-amarelo-texto"><IconeEstrela /> Destaque</Selo>
          )}
          {ehNovo(e, hoje) && <Selo classe="bg-novo-fundo text-novo">Novo</Selo>}
          {status === "prorrogado" && <Selo classe="bg-alta-fundo text-alta">Prorrogado</Selo>}
          {status === "em_breve" && <Selo classe="bg-novo-fundo text-novo">Abre em breve</Selo>}
        </div>

        <h2 id={`t-${e.id}`} className="titulo-display text-[1.45rem] font-bold">
          <Link href={`/edital/${e.id}/`} className="underline decoration-2 underline-offset-4 hover:decoration-amarelo hover:decoration-[5px]">
            {e.titulo}
          </Link>
        </h2>
        {e.orgao && <p className="mt-1 font-bold text-suave">{e.orgao}</p>}

        <ul className="mt-3 flex flex-wrap gap-2" aria-label="Características">
          {e.tipo_apoio && <Chip>{rotulo(TIPOS, e.tipo_apoio)}</Chip>}
          {e.mecanismo.map((m) => <Chip key={m}>{rotulo(MECANISMOS, m)}</Chip>)}
          {e.abrangencia && <Chip>{rotulo(ABRANGENCIAS, e.abrangencia)}</Chip>}
        </ul>

        {(valor || onde) && (
          <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1">
            {valor && <p className="flex items-center gap-2"><IconeMoeda /> <span>{valor}</span></p>}
            {onde && <p className="flex items-center gap-2"><IconeLocal /> <span>{onde}</span></p>}
          </div>
        )}

        {!compacto && e.resumo && (
          <details className="mt-3">
            <summary className="alvo inline-flex cursor-pointer items-center font-bold text-acento underline">
              Ler resumo
            </summary>
            <p className="mt-2 max-w-prose">{e.resumo}</p>
          </details>
        )}

        <div className="mt-4 flex flex-wrap gap-3">
          {e.link_inscricao && (
            <LinkProtegido
              href={e.link_inscricao}
              edital={e.titulo}
              rotulo="Ir para a inscrição"
              className="alvo inline-flex items-center gap-2 rounded-lg bg-marca px-4 py-2 font-bold text-marca-texto shadow-[0_3px_0_0_var(--amarelo)] hover:shadow-[0_5px_0_0_var(--amarelo)]"
            >
              Inscrever <IconeExterno />
            </LinkProtegido>
          )}
          {e.link_edital && (
            <LinkProtegido
              href={e.link_edital}
              edital={e.titulo}
              rotulo="Abrir o edital oficial"
              className="alvo inline-flex items-center gap-2 rounded-lg border-2 border-marca px-4 py-2 font-bold text-acento hover:bg-chip"
            >
              Edital oficial <IconeExterno />
            </LinkProtegido>
          )}
          {compacto && (
            <a
              href={`${process.env.NEXT_PUBLIC_SITE_URL}${base}/edital/${e.id}/`}
              target="_blank"
              rel="noopener"
              className="alvo inline-flex items-center font-bold text-acento underline"
            >
              Ver detalhes
            </a>
          )}
        </div>
      </div>
    </article>
  );
}
