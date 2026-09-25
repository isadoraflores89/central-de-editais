// Exportação do filtro atual, gerada no navegador (decisão D7 do PLANO).
import { rotulo, ABRANGENCIAS, MECANISMOS, TIPOS } from "./rotulos";
import type { Edital } from "./tipos";

const COLUNAS: [string, (e: Edital) => string | number | null][] = [
  ["Edital / Programa", (e) => e.titulo],
  ["Órgão", (e) => e.orgao],
  ["Status", (e) => e.status],
  ["Prioridade", (e) => e.prioridade],
  ["Tipo de apoio", (e) => (e.tipo_apoio ? rotulo(TIPOS, e.tipo_apoio) : null)],
  ["Mecanismo", (e) => e.mecanismo.map((m) => rotulo(MECANISMOS, m)).join("; ")],
  ["Abrangência", (e) => (e.abrangencia ? rotulo(ABRANGENCIAS, e.abrangencia) : null)],
  ["UFs", (e) => e.ufs.join("; ")],
  ["Cidades", (e) => e.cidades.join("; ")],
  ["Valor máx. por projeto (R$)", (e) => e.valor_por_projeto_max],
  ["Valores (texto da fonte)", (e) => e.valor_texto],
  ["Prazo", (e) => e.prazo_texto],
  ["Data-limite", (e) => e.data_limite],
  ["Fluxo contínuo", (e) => (e.fluxo_continuo ? "sim" : "não")],
  ["Resumo", (e) => e.resumo],
  ["Link de inscrição", (e) => e.link_inscricao],
  ["Edital oficial", (e) => e.link_edital],
  ["Observações", (e) => e.observacoes],
  ["Fonte", (e) => e.fonte],
  ["URL da fonte", (e) => e.source_url],
  ["ID", (e) => e.id],
];

function celulaCsv(v: string | number | null): string {
  if (v === null || v === undefined) return "";
  const s = String(v);
  return /[",\n;]/.test(s) ? `"${s.replaceAll('"', '""')}"` : s;
}

export function gerarCsv(editais: Edital[]): string {
  const linhas = [COLUNAS.map(([c]) => c), ...editais.map((e) => COLUNAS.map(([, f]) => f(e)))];
  return "﻿" + linhas.map((l) => l.map(celulaCsv).join(",")).join("\n") + "\n";
}

function baixar(blob: Blob, nome: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nome;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function nomeArquivo(ext: string, hoje: string): string {
  return `central-de-editais-${hoje}.${ext}`;
}

export function baixarCsv(editais: Edital[], hoje: string): void {
  baixar(new Blob([gerarCsv(editais)], { type: "text/csv;charset=utf-8" }), nomeArquivo("csv", hoje));
}

export async function baixarXlsx(editais: Edital[], hoje: string): Promise<void> {
  const { default: ExcelJS } = await import("exceljs");
  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet("Editais", { views: [{ state: "frozen", ySplit: 1, xSplit: 1 }] });
  ws.columns = COLUNAS.map(([header]) => ({
    header,
    width: header === "Resumo" ? 80 : header === "Edital / Programa" ? 50 : 20,
  }));
  for (const e of editais) ws.addRow(COLUNAS.map(([, f]) => f(e)));
  ws.getRow(1).font = { bold: true, color: { argb: "FFFFFFFF" } };
  ws.getRow(1).fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF1F3A2E" } };
  ws.autoFilter = { from: { row: 1, column: 1 }, to: { row: 1, column: COLUNAS.length } };
  const buf = await wb.xlsx.writeBuffer();
  baixar(
    new Blob([buf], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }),
    nomeArquivo("xlsx", hoje),
  );
}
