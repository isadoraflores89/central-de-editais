import { diasRestantes, statusEfetivo, textoPrazo, urgencia } from "@/lib/prazo";
import { formatarData } from "@/lib/texto";
import type { Edital } from "@/lib/tipos";

import { IconeAlerta, IconeCalendario } from "./Icones";

const ESTILO = {
  critica: "bg-critica-fundo text-critica border-critica",
  alta: "bg-alta-fundo text-alta border-alta",
  normal: "bg-chip text-texto border-borda-suave",
  nenhuma: "bg-chip text-suave border-borda-suave",
} as const;

/** Contagem regressiva. A cor sempre vem acompanhada de texto (nunca só cor). */
export function SeloPrazo({ edital, hoje }: { edital: Edital; hoje: string }) {
  const dias = diasRestantes(edital, hoje);
  const nivel = statusEfetivo(edital, hoje) === "encerrado" ? "nenhuma" : urgencia(dias);
  const Icone = nivel === "critica" ? IconeAlerta : IconeCalendario;
  return (
    <p className={`inline-flex flex-wrap items-center gap-x-2 gap-y-1 rounded-md border-2 px-3 py-1.5 font-bold ${ESTILO[nivel]}`}>
      <Icone />
      <span>{textoPrazo(edital, hoje)}</span>
      {edital.data_limite && (
        <span className="font-normal">
          <span className="sr-only">, data-limite </span>
          ({formatarData(edital.data_limite)})
        </span>
      )}
    </p>
  );
}
