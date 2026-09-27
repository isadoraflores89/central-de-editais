"use client";

import { useEffect, useId, useRef, useState } from "react";

/** Resumo visível em 2 linhas, com "Ver mais" quando o texto passa disso. */
export function Resumo({ texto }: { texto: string }) {
  const ref = useRef<HTMLParagraphElement>(null);
  const id = useId();
  const [aberto, setAberto] = useState(false);
  const [cabe, setCabe] = useState(true);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const medir = () => { if (!aberto) setCabe(el.scrollHeight <= el.clientHeight + 1); };
    medir();
    const ro = new ResizeObserver(medir);
    ro.observe(el);
    return () => ro.disconnect();
  }, [aberto]);

  return (
    <div className="mt-3">
      <p id={id} ref={ref} className={`max-w-prose ${aberto ? "" : "line-clamp-2"}`}>{texto}</p>
      {(!cabe || aberto) && (
        <button
          type="button"
          aria-expanded={aberto}
          aria-controls={id}
          onClick={() => setAberto((v) => !v)}
          className="alvo inline-flex items-center font-bold text-acento underline"
        >
          {aberto ? "Ver menos" : "Ver mais"}
        </button>
      )}
    </div>
  );
}
