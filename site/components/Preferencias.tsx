"use client";

import { useEffect, useState } from "react";

import { ZOOMS, ZOOM_PADRAO, aplicarPrefs, lerPrefs, type Prefs, type Tema } from "@/lib/preferencias";

const botao = "alvo inline-flex min-w-[2.75rem] items-center justify-center px-3 font-bold";

function IconeSol() {
  return (
    <svg viewBox="0 0 24 24" width="1.1em" height="1.1em" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" aria-hidden="true" focusable="false">
      <circle cx="12" cy="12" r="4.5" />
      <path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8" />
    </svg>
  );
}
function IconeLua() {
  return (
    <svg viewBox="0 0 24 24" width="1.1em" height="1.1em" fill="none" stroke="currentColor" strokeWidth={2} strokeLinejoin="round" aria-hidden="true" focusable="false">
      <path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5Z" />
    </svg>
  );
}

/** Barra de leitura: tamanho do texto (A− A A+) e tema (claro / escuro). */
export function Preferencias() {
  const [prefs, setPrefs] = useState<Prefs>({ zoom: ZOOM_PADRAO, tema: "auto" });
  useEffect(() => {
    setPrefs(lerPrefs());
  }, []);

  // Cada clique parte do valor mais recente (cliques rápidos não se anulam).
  const mudar = (f: (p: Prefs) => Prefs) =>
    setPrefs((atual) => {
      const novo = f(atual);
      aplicarPrefs(novo);
      return novo;
    });
  const passo = (p: Prefs, d: number): number => {
    const i = Math.max(0, ZOOMS.indexOf(p.zoom as (typeof ZOOMS)[number]));
    return ZOOMS[Math.min(ZOOMS.length - 1, Math.max(0, i + d))] ?? ZOOM_PADRAO;
  };
  const i = ZOOMS.indexOf(prefs.zoom as (typeof ZOOMS)[number]);
  // Escuro é o padrão do site (como isadoraflores.art.br); só fica claro se a pessoa escolher.
  const escuro = prefs.tema !== "light";
  const porcento = Math.round(prefs.zoom * 100);

  return (
    <div className="flex flex-wrap items-center gap-3">
      <div role="group" aria-label={`Tamanho do texto, agora em ${porcento}%`} className="inline-flex overflow-hidden rounded-lg border-2 border-cabecalho-texto/70">
        <button type="button" className={botao} disabled={i <= 0}
                onClick={() => mudar((p) => ({ ...p, zoom: passo(p, -1) }))}
                aria-label="Diminuir o texto">
          A<span aria-hidden="true">−</span>
        </button>
        <button type="button" className={`${botao} border-x-2 border-cabecalho-texto/70 text-[0.95rem]`}
                onClick={() => mudar((p) => ({ ...p, zoom: ZOOM_PADRAO }))}
                aria-label="Tamanho normal do texto" title="Voltar ao tamanho normal">
          {porcento}%
        </button>
        <button type="button" className={`${botao} text-[1.2rem]`} disabled={i >= ZOOMS.length - 1}
                onClick={() => mudar((p) => ({ ...p, zoom: passo(p, +1) }))}
                aria-label="Aumentar o texto">
          A<span aria-hidden="true">+</span>
        </button>
      </div>

      <button
        type="button"
        onClick={() => mudar((p) => ({ ...p, tema: (escuro ? "light" : "dark") as Tema }))}
        aria-pressed={escuro}
        className="alvo inline-flex items-center gap-2 rounded-lg border-2 border-cabecalho-texto/70 px-3 font-bold"
      >
        {escuro ? <IconeSol /> : <IconeLua />}
        {escuro ? "Modo claro" : "Modo escuro"}
      </button>
    </div>
  );
}
