import { Suspense } from "react";

import { Capa } from "@/components/Capa";
import { Consultoria, Newsletter } from "@/components/Chamadas";
import { Radar } from "@/components/Radar";
import { dataDoBuild, editais, presets } from "@/lib/dados";

export default function Inicio() {
  return (
    <>
      <Capa editais={editais()} hoje={dataDoBuild()} />
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
