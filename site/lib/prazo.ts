import type { Edital, Status } from "./tipos";

const FUSO = "America/Bahia";

/** Data de hoje (AAAA-MM-DD) no fuso da Bahia. */
export function hojeISO(agora: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: FUSO }).format(agora);
}

function diaUTC(iso: string): number {
  const [a, m, d] = iso.slice(0, 10).split("-").map(Number);
  return Date.UTC(a ?? 0, (m ?? 1) - 1, d ?? 1) / 86_400_000;
}

export function diasEntre(deISO: string, ateISO: string): number {
  return Math.round(diaUTC(ateISO) - diaUTC(deISO));
}

export function diasRestantes(e: Edital, hoje: string): number | null {
  return e.data_limite ? diasEntre(hoje, e.data_limite) : null;
}

/**
 * Recalcula o status no navegador (decisão D4 do PLANO): se o robô passar um dia
 * sem rodar, um prazo vencido não continua aparecendo como aberto.
 */
export function statusEfetivo(e: Edital, hoje: string): Status {
  const dias = diasRestantes(e, hoje);
  if (dias !== null && dias < 0) return "encerrado";
  const abreDepois = e.data_abertura !== null && diasEntre(hoje, e.data_abertura) > 0;
  if (e.status !== "encerrado" && abreDepois) return "em_breve";
  if (e.status === "em_breve" && !abreDepois) {
    return e.data_limite || e.fluxo_continuo ? "aberto" : "indefinido";
  }
  return e.status;
}

export type Urgencia = "critica" | "alta" | "normal" | "nenhuma";

export function urgencia(dias: number | null): Urgencia {
  if (dias === null || dias < 0) return "nenhuma";
  if (dias <= 7) return "critica";
  if (dias <= 15) return "alta";
  return "normal";
}

export function textoPrazo(e: Edital, hoje: string): string {
  const dias = diasRestantes(e, hoje);
  if (dias === null) {
    if (e.fluxo_continuo) return "Fluxo contínuo";
    return e.prazo_texto ? `Prazo: ${e.prazo_texto}` : "Prazo a confirmar";
  }
  if (dias < 0) return "Encerrado";
  if (dias === 0) return "Fecha hoje";
  if (dias === 1) return "Fecha amanhã";
  return `Fecha em ${dias} dias`;
}

export function ehNovo(e: Edital, hoje: string): boolean {
  if (e.marcadores.includes("carga_inicial")) return false;
  return diasEntre(e.captured_at.slice(0, 10), hoje) <= 3;
}
