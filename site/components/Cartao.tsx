import Link from "next/link";

import { ehNovo, statusEfetivo } from "@/lib/prazo";
import { ABRANGENCIAS, MECANISMOS, TIPOS, rotulo } from "@/lib/rotulos";
import { formatarReais } from "@/lib/texto";
import type { Edital } from "@/lib/tipos";

import { IconeEstrela, IconeExterno, IconeLocal, IconeMoeda } from "./Icones";
import { SeloPrazo } from "./SeloPrazo";

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <li className="rounded-full border border-borda-suave bg-chip px-3 py-0.5 text-[0.9rem]">
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

export function Cartao({ edital: e, hoje, compacto = false }: { edital: Edital; hoje: string; compacto?: boolean }) {
  const status = statusEfetivo(e, hoje);
  const valor = valorResumido(e);
  const onde = local(e);
  const base = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
  return (
    <article
      className="rounded-xl border-2 border-borda-suave bg-superficie p-5 shadow-sm"
      aria-labelledby={`t-${e.id}`}
    >
      <div className="mb-2 flex flex-wrap gap-2">
        {e.curadoria.destaque && (
          <Selo classe="bg-marca text-marca-texto"><IconeEstrela /> Destaque</Selo>
        )}
        {ehNovo(e, hoje) && <Selo classe="bg-novo-fundo text-novo">Novo</Selo>}
        {status === "prorrogado" && <Selo classe="bg-alta-fundo text-alta">Prorrogado</Selo>}
        {status === "encerrado" && <Selo classe="bg-chip text-suave">Encerrado</Selo>}
        {status === "em_breve" && <Selo classe="bg-novo-fundo text-novo">Abre em breve</Selo>}
      </div>

      <h2 id={`t-${e.id}`} className="text-[1.3rem] font-bold leading-snug">
        <Link href={`/edital/${e.id}/`} className="underline decoration-2 hover:decoration-4">
          {e.titulo}
        </Link>
      </h2>
      {e.orgao && <p className="mt-1 text-suave">{e.orgao}</p>}

      <ul className="mt-3 flex flex-wrap gap-2" aria-label="Características">
        {e.tipo_apoio && <Chip>{rotulo(TIPOS, e.tipo_apoio)}</Chip>}
        {e.mecanismo.map((m) => <Chip key={m}>{rotulo(MECANISMOS, m)}</Chip>)}
        {e.abrangencia && <Chip>{rotulo(ABRANGENCIAS, e.abrangencia)}</Chip>}
      </ul>

      <div className="mt-4 flex flex-col gap-2">
        <SeloPrazo edital={e} hoje={hoje} />
        {valor && (
          <p className="flex items-center gap-2"><IconeMoeda /> <span>{valor}</span></p>
        )}
        {onde && (
          <p className="flex items-center gap-2"><IconeLocal /> <span>{onde}</span></p>
        )}
      </div>

      {!compacto && e.resumo && (
        <details className="mt-4 group">
          <summary className="alvo inline-flex cursor-pointer items-center font-bold text-acento underline">
            Ler resumo
          </summary>
          <p className="mt-2 max-w-prose">{e.resumo}</p>
        </details>
      )}

      <div className="mt-4 flex flex-wrap gap-3">
        {e.link_inscricao && (
          <a
            href={e.link_inscricao}
            target="_blank"
            rel="noopener noreferrer"
            className="alvo inline-flex items-center gap-2 rounded-lg bg-marca px-4 py-2 font-bold text-marca-texto hover:opacity-90"
          >
            Inscrever <IconeExterno /><span className="sr-only">(abre em nova aba)</span>
          </a>
        )}
        {e.link_edital && (
          <a
            href={e.link_edital}
            target="_blank"
            rel="noopener noreferrer"
            className="alvo inline-flex items-center gap-2 rounded-lg border-2 border-marca px-4 py-2 font-bold text-acento hover:bg-chip"
          >
            Edital oficial <IconeExterno /><span className="sr-only">(abre em nova aba)</span>
          </a>
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
    </article>
  );
}
