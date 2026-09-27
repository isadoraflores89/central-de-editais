// Textos pensados para serem ouvidos (audiodescrição automática pelo leitor de voz
// do navegador). Sem abreviações nem símbolos que a voz lê mal (R$, /, ·).
import { diasRestantes, statusEfetivo } from "./prazo";
import { ABRANGENCIAS, MECANISMOS, TIPOS, rotulo } from "./rotulos";
import type { Edital } from "./tipos";

const MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
  "setembro", "outubro", "novembro", "dezembro"];

export function dataFalada(iso: string): string {
  const [a, m, d] = iso.slice(0, 10).split("-").map(Number);
  return `${d} de ${MESES[(m ?? 1) - 1]} de ${a}`;
}

export function reaisFalado(v: number): string {
  if (v >= 1_000_000) {
    const m = v / 1_000_000;
    if (m === 1) return "1 milhão de reais";
    if (m === 1.5) return "1 milhão e meio de reais";
    return `${m.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} milhões de reais`;
  }
  if (v >= 1000) return `${Math.round(v / 1000).toLocaleString("pt-BR")} mil reais`;
  return `${Math.round(v)} reais`;
}

function prazoFalado(e: Edital, hoje: string): string {
  if (statusEfetivo(e, hoje) === "encerrado") return "Este edital está encerrado.";
  const dias = diasRestantes(e, hoje);
  if (dias === null) return e.fluxo_continuo ? "Recebe inscrições o ano todo." : "Prazo ainda a confirmar.";
  const quando = e.data_limite ? `, no dia ${dataFalada(e.data_limite)}` : "";
  if (dias === 0) return `Atenção: as inscrições fecham hoje${quando}.`;
  if (dias === 1) return `Atenção: fecha amanhã${quando}.`;
  return `${dias <= 7 ? "Atenção: " : ""}Fecha em ${dias} dias${quando}.`;
}

function valorFalado(e: Edital): string | null {
  const v = e.valor_por_projeto_max ?? e.valor_por_projeto_min;
  if (v !== null) return `Valor: até ${reaisFalado(v)} por projeto.`;
  if (e.valor_total !== null) return `Valor total: ${reaisFalado(e.valor_total)}.`;
  return null;
}

export function falaEdital(e: Edital, hoje: string, comResumo = true): string {
  const partes = [
    `${e.titulo.replace(/\s*[—–]\s*/g, ", ")}.`,
    e.orgao ? `Quem publica: ${e.orgao.replace(/\s*\/\s*/g, " e ")}.` : null,
    prazoFalado(e, hoje),
    e.tipo_apoio ? `Tipo de apoio: ${rotulo(TIPOS, e.tipo_apoio)}.` : null,
    e.mecanismo.length ? `Mecanismo: ${e.mecanismo.map((m) => rotulo(MECANISMOS, m)).join(", ")}.` : null,
    e.abrangencia ? `Abrangência: ${rotulo(ABRANGENCIAS, e.abrangencia)}${e.cidades.length ? `, em ${e.cidades.join(", ")}` : ""}.` : null,
    valorFalado(e),
    comResumo && e.resumo ? `Resumo: ${e.resumo}` : null,
  ];
  return partes.filter(Boolean).join(" ").replace(/R\$\s?/g, "").replace(/·/g, ",");
}
