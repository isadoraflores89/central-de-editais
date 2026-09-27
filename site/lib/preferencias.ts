// Preferências de leitura (tamanho do texto e tema), guardadas só neste navegador.
export const CHAVE_PREFS = "central-prefs-v1";
export const ZOOMS = [0.85, 1, 1.25, 1.54, 1.85] as const;
export const ZOOM_PADRAO = 1;
export type Tema = "auto" | "light" | "dark";

export interface Prefs { zoom: number; tema: Tema }

/**
 * Script que roda no <head> antes da página aparecer, para não "piscar"
 * no tamanho ou tema errado. Mantido pequeno e sem dependências.
 */
export const SCRIPT_PREFS = `(function(){try{var p=JSON.parse(localStorage.getItem("${CHAVE_PREFS}")||"{}");var d=document.documentElement;if(p.zoom)d.style.setProperty("--zoom",String(p.zoom));if(p.tema==="light"||p.tema==="dark")d.setAttribute("data-theme",p.tema);}catch(e){}})();`;

export function lerPrefs(): Prefs {
  try {
    const p = JSON.parse(localStorage.getItem(CHAVE_PREFS) ?? "{}") as Partial<Prefs>;
    const zoom = ZOOMS.includes(p.zoom as (typeof ZOOMS)[number]) ? (p.zoom as number) : ZOOM_PADRAO;
    const tema: Tema = p.tema === "light" || p.tema === "dark" ? p.tema : "auto";
    return { zoom, tema };
  } catch {
    return { zoom: ZOOM_PADRAO, tema: "auto" };
  }
}

export function aplicarPrefs(p: Prefs): void {
  const d = document.documentElement;
  d.style.setProperty("--zoom", String(p.zoom));
  if (p.tema === "auto") d.removeAttribute("data-theme");
  else d.setAttribute("data-theme", p.tema);
  try {
    localStorage.setItem(CHAVE_PREFS, JSON.stringify(p));
  } catch {
    /* sem armazenamento: vale só nesta visita */
  }
}
