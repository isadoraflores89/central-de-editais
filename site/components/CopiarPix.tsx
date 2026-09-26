"use client";

import { useState } from "react";

export function CopiarPix({ codigo, rotulo }: { codigo: string; rotulo: string }) {
  const [copiado, setCopiado] = useState(false);
  return (
    <div>
      <button
        type="button"
        onClick={async () => {
          await navigator.clipboard.writeText(codigo);
          setCopiado(true);
          setTimeout(() => setCopiado(false), 4000);
        }}
        className="alvo inline-flex items-center rounded-lg bg-marca px-4 py-2 font-bold text-marca-texto"
      >
        {rotulo}
      </button>
      <span role="status" aria-live="polite" className="ml-3 font-bold">
        {copiado ? "Copiado!" : ""}
      </span>
    </div>
  );
}
