// Capa da página inicial: manchete editorial + três números do dia.
import { dataFalada, falaEdital } from "@/lib/fala";
import { diasRestantes, statusEfetivo } from "@/lib/prazo";
import { formatarData } from "@/lib/texto";
import type { Edital } from "@/lib/tipos";

import { Ouvir } from "./Ouvir";

function Numero({ valor, rotulo }: { valor: number; rotulo: string }) {
  return (
    <div className="border-l-[5px] border-amarelo pl-4">
      <p className="titulo-display text-[3rem] font-extrabold leading-none sm:text-[3.6rem]">{valor}</p>
      <p className="mt-1 text-[1.05rem]">{rotulo}</p>
    </div>
  );
}

export function Capa({ editais, hoje }: { editais: Edital[]; hoje: string }) {
  const visiveis = editais.filter((e) => !e.curadoria.oculto);
  const abertos = visiveis.filter((e) => ["aberto", "prorrogado"].includes(statusEfetivo(e, hoje)));
  const semana = abertos.filter((e) => {
    const d = diasRestantes(e, hoje);
    return d !== null && d >= 0 && d <= 7;
  }).length;
  const continuo = abertos.filter((e) => e.fluxo_continuo && e.data_limite === null).length;
  const top = [...abertos].sort((a, b) => b.prioridade - a.prioridade).slice(0, 3);
  const fala = [
    `Central de Editais. Hoje, ${dataFalada(hoje)}, há ${abertos.length} editais abertos.`,
    `${semana} fecham em até 7 dias, e ${continuo} recebem inscrições o ano todo.`,
    "Os três com maior prioridade são:",
    ...top.map((e, i) => `${i + 1}. ${falaEdital(e, hoje, false)}`),
  ].join(" ");

  return (
    <section aria-labelledby="manchete" className="listras relative -mx-4 -mt-6 mb-8 overflow-hidden sm:mt-0 bg-cabecalho px-4 py-10 text-cabecalho-texto sm:mx-0 sm:rounded-2xl sm:px-10">
      <p className="text-[1.05rem] font-bold uppercase tracking-[0.12em]">
        Radar diário · atualizado em {formatarData(hoje)}
      </p>
      <h1 id="manchete" className="titulo-display mt-3 max-w-3xl text-[2.6rem] font-extrabold sm:text-[3.6rem]">
        Editais culturais <span className="grifo">abertos</span> agora
      </h1>
      <p className="mt-4 max-w-2xl text-[1.15rem]">
        Editais, patrocínios e credenciamentos do campo cultural brasileiro, em ordem de
        prioridade. Filtre por estado, mecanismo, prazo e valor.
      </p>
      <Ouvir texto={fala} rotulo="Ouvir os destaques de hoje"
             className="mt-6 border-cabecalho-texto/70 text-cabecalho-texto hover:bg-white/10" />
      <div className="mt-8 grid max-w-3xl grid-cols-1 gap-6 sm:grid-cols-3">
        <Numero valor={abertos.length} rotulo="editais abertos" />
        <Numero valor={semana} rotulo="fecham em até 7 dias" />
        <Numero valor={continuo} rotulo="abertos o ano todo" />
      </div>
    </section>
  );
}
