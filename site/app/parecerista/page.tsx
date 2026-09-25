import type { Metadata } from "next";
import { Suspense } from "react";

import { Radar } from "@/components/Radar";
import { dataDoBuild, editais } from "@/lib/dados";

export const metadata: Metadata = {
  title: "Parecerista e credenciamentos",
  description: "Credenciamentos abertos para pareceristas e prestadores de serviço na área cultural.",
};

export default function Parecerista() {
  return (
    <>
      <div className="mb-6 max-w-3xl">
        <h1 className="text-[2rem] font-bold leading-tight">Parecerista e credenciamentos</h1>
        <p className="mt-2 text-[1.1rem]">
          Chamadas para quem quer atuar como parecerista, avaliador ou prestador de serviço
          para órgãos de cultura. A maioria fica aberta o ano todo (fluxo contínuo).
        </p>
      </div>
      <Suspense fallback={<p>Carregando…</p>}>
        <Radar editais={editais()} presets={[]} hojeBuild={dataDoBuild()} filtrosPadrao="tipo=credenciamento" />
      </Suspense>
    </>
  );
}
