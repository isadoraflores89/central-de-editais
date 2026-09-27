"use client";

// Audiodescrição automática: lê o texto em voz alta com a voz pt-BR do próprio
// navegador (Web Speech API). Grátis, sem servidor e sem enviar nada para fora.
import { useEffect, useState } from "react";

let quemFala: ((v: boolean) => void) | null = null;

function vozPtBr(): SpeechSynthesisVoice | undefined {
  const vozes = window.speechSynthesis.getVoices();
  return vozes.find((v) => v.lang === "pt-BR") ?? vozes.find((v) => v.lang.startsWith("pt"));
}

export function Ouvir({ texto, rotulo = "Ouvir", className = "" }: { texto: string; rotulo?: string; className?: string }) {
  const [suportado, setSuportado] = useState(false);
  const [falando, setFalando] = useState(false);

  useEffect(() => {
    setSuportado(typeof window !== "undefined" && "speechSynthesis" in window);
    return () => {
      if (quemFala === setFalando) window.speechSynthesis.cancel();
    };
  }, []);

  if (!suportado) return null;

  const alternar = () => {
    const s = window.speechSynthesis;
    if (falando) {
      s.cancel();
      setFalando(false);
      return;
    }
    s.cancel();
    quemFala?.(false); // só uma leitura por vez
    const u = new SpeechSynthesisUtterance(texto);
    u.lang = "pt-BR";
    const v = vozPtBr();
    if (v) u.voice = v;
    u.rate = 0.95;
    u.onend = () => setFalando(false);
    u.onerror = () => setFalando(false);
    quemFala = setFalando;
    setFalando(true);
    s.speak(u);
  };

  return (
    <button
      type="button"
      onClick={alternar}
      aria-pressed={falando}
      className={`alvo inline-flex items-center gap-2 rounded-lg border-2 border-borda px-3 py-1.5 font-bold hover:bg-chip ${className}`}
    >
      <svg viewBox="0 0 24 24" width="1.2em" height="1.2em" fill="none" stroke="currentColor" strokeWidth={2}
           strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
        <path d="M4 9v6h4l5 4V5L8 9H4Z" />
        {falando ? <path d="M17 9l4 6M21 9l-4 6" /> : <path d="M16.5 8.5a5 5 0 0 1 0 7M19 6a8.5 8.5 0 0 1 0 12" />}
      </svg>
      {falando ? "Parar leitura" : rotulo}
    </button>
  );
}
