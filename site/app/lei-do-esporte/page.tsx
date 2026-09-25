import type { Metadata } from "next";
import { Suspense } from "react";

import { Radar } from "@/components/Radar";
import { dataDoBuild, editais } from "@/lib/dados";

export const metadata: Metadata = {
  title: "Lei do Esporte",
  description: "Chamadas de patrocínio para projetos da Lei de Incentivo ao Esporte e leis estaduais de esporte.",
};

export default function LeiDoEsporte() {
  return (
    <>
      <div className="mb-6 max-w-3xl">
        <h1 className="text-[2rem] font-bold leading-tight">Lei do Esporte</h1>
        <p className="mt-2 text-[1.1rem]">
          Empresas e programas que patrocinam projetos esportivos aprovados na Lei de Incentivo
          ao Esporte (federal) ou em leis estaduais e municipais de esporte.
        </p>
      </div>
      <Suspense fallback={<p>Carregando…</p>}>
        <Radar editais={editais()} presets={[]} hojeBuild={dataDoBuild()} filtrosPadrao="area=esporte" />
      </Suspense>
    </>
  );
}
