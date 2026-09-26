import { Suspense } from "react";

import { Consultoria, Newsletter } from "@/components/Chamadas";
import { Radar } from "@/components/Radar";
import { dataDoBuild, editais, presets } from "@/lib/dados";

export default function Inicio() {
  return (
    <>
      <div className="mb-6 max-w-3xl">
        <h1 className="text-[2rem] font-bold leading-tight">Editais culturais abertos</h1>
        <p className="mt-2 text-[1.1rem]">
          Editais, patrocínios e credenciamentos do campo cultural brasileiro, em ordem de
          prioridade e atualizados todos os dias. Use os filtros para achar o que serve para você.
        </p>
      </div>
      <Suspense fallback={<p>Carregando editais…</p>}>
        <Radar editais={editais()} presets={presets()} hojeBuild={dataDoBuild()} />
      </Suspense>
      <div className="mt-10 grid gap-5 md:grid-cols-2">
        <Newsletter />
        <Consultoria />
      </div>
    </>
  );
}
