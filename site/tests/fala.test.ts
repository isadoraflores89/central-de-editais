import { describe, expect, it } from "vitest";

import { dataFalada, falaEdital, reaisFalado } from "@/lib/fala";
import type { Edital } from "@/lib/tipos";

const base = {
  id: "x", titulo: "Vale — Seleção", orgao: "MinC / Vale", tipo_apoio: "premio", mecanismo: ["rouanet"],
  leis_estaduais: [], exige_projeto_aprovado: null, abrangencia: "municipal", ufs: ["BA"], cidades: ["Salvador"],
  areas: [], publico_prioritario: [], proponente: [], valor_por_projeto_min: null, valor_por_projeto_max: 1_500_000,
  valor_total: null, valor_texto: null, prazo_texto: null, data_limite: "2026-09-30", fluxo_continuo: false,
  data_abertura: null, status: "aberto", resumo: "Até R$ 20 mil.", link_inscricao: null, link_edital: null,
  observacoes: null, fonte: "t", source_url: "https://x", fontes_secundarias: [], captured_at: "2026-09-24T00:00:00Z",
  updated_at: "2026-09-24T00:00:00Z", prioridade: 50, curadoria: { oculto: false, destaque: false, tags: [], nota: null },
  marcadores: [], historico: [], aliases: [], revisao_pendente: false,
} as Edital;

describe("fala", () => {
  it("datas e valores por extenso", () => {
    expect(dataFalada("2026-09-30")).toBe("30 de setembro de 2026");
    expect(reaisFalado(1_500_000)).toBe("1 milhão e meio de reais");
    expect(reaisFalado(20_000)).toBe("20 mil reais");
  });
  it("monta a audiodescrição sem símbolos que a voz lê mal", () => {
    const t = falaEdital(base, "2026-09-26");
    expect(t).toContain("Atenção: Fecha em 4 dias, no dia 30 de setembro de 2026.");
    expect(t).toContain("Vale, Seleção. Quem publica: MinC e Vale.");
    expect(t).toContain("até 1 milhão e meio de reais por projeto");
    expect(t).toContain("em Salvador");
    expect(t).not.toMatch(/R\$|—|\//);
  });
});
