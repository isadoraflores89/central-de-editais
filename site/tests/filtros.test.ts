import { describe, expect, it } from "vitest";

import { contarFacetas, escreverFiltros, filtrar, filtrosVazios, lerFiltros } from "@/lib/filtros";
import { statusEfetivo, textoPrazo } from "@/lib/prazo";
import type { Edital } from "@/lib/tipos";

const HOJE = "2026-09-25";

function ed(p: Partial<Edital> & { id: string }): Edital {
  return {
    titulo: p.id, orgao: null, tipo_apoio: null, mecanismo: [], leis_estaduais: [],
    exige_projeto_aprovado: null, abrangencia: null, ufs: [], cidades: [], areas: [],
    publico_prioritario: [], proponente: [], valor_por_projeto_min: null,
    valor_por_projeto_max: null, valor_total: null, valor_texto: null, prazo_texto: null,
    data_limite: null, fluxo_continuo: false, data_abertura: null, status: "aberto",
    resumo: null, link_inscricao: null, link_edital: null, observacoes: null, fonte: "teste",
    source_url: "https://x.gov.br", fontes_secundarias: [], captured_at: "2026-09-24T12:00:00Z",
    updated_at: "2026-09-24T12:00:00Z", prioridade: 0,
    curadoria: { oculto: false, destaque: false, tags: [], nota: null },
    marcadores: [], historico: [], aliases: [], revisao_pendente: false,
    ...p,
  };
}

const BA = ed({ id: "ba", titulo: "Fomento à Música na Bahia", abrangencia: "estadual", ufs: ["BA"], data_limite: "2026-09-30", prioridade: 50, proponente: ["pf"], valor_por_projeto_max: 50_000 });
const NAC = ed({ id: "nac", titulo: "Prêmio Nacional", abrangencia: "nacional", fluxo_continuo: true, prioridade: 70, mecanismo: ["rouanet"], exige_projeto_aprovado: false });
const SP = ed({ id: "sp", titulo: "Edital São Paulo", abrangencia: "estadual", ufs: ["SP"], data_limite: "2026-12-01", prioridade: 90, valor_por_projeto_max: 300_000 });
const VELHO = ed({ id: "velho", titulo: "Encerrado", data_limite: "2026-09-01", status: "aberto", prioridade: 99 });
const OCULTO = ed({ id: "oculto", curadoria: { oculto: true, destaque: false, tags: [], nota: null } });
const TODOS = [BA, NAC, SP, VELHO, OCULTO];

const ids = (qs: string) => filtrar(TODOS, lerFiltros(new URLSearchParams(qs)), HOJE).map((e) => e.id);

describe("URL", () => {
  it("ida e volta preserva os filtros", () => {
    const qs = "q=musica&uf=BA,PR&prazo=7,continuo&pf=1&nacionais=0&vmin=100000&vnull=0&ordem=prazo";
    expect(escreverFiltros(lerFiltros(new URLSearchParams(qs))).toString()).toBe(
      new URLSearchParams(qs).toString(),
    );
  });
  it("ignora valores inválidos", () => {
    const f = lerFiltros(new URLSearchParams("prazo=999&de=ontem&ordem=xyz&vmin=-5"));
    expect(f.prazo).toEqual([]);
    expect(f.de).toBeNull();
    expect(f.ordem).toBe("prioridade");
    expect(f.vmin).toBeNull();
  });
});

describe("filtrar", () => {
  it("padrão: esconde encerrados e ocultos, ordena por prioridade", () => {
    expect(ids("")).toEqual(["sp", "nac", "ba"]);
  });
  it("encerrado é recalculado no navegador mesmo com status antigo", () => {
    expect(statusEfetivo(VELHO, HOJE)).toBe("encerrado");
    expect(ids("encerrados=1")).toContain("velho");
  });
  it("UF inclui nacionais por padrão", () => {
    expect(ids("uf=BA")).toEqual(["nac", "ba"]);
    expect(ids("uf=BA&nacionais=0")).toEqual(["ba"]);
  });
  it("busca sem acento", () => {
    expect(ids("q=musica bahia")).toEqual(["ba"]);
    expect(ids("q=PRÊMIO")).toEqual(["nac"]);
  });
  it("prazo em dias e fluxo contínuo", () => {
    expect(ids("prazo=7")).toEqual(["ba"]);
    expect(ids("prazo=7,continuo")).toEqual(["nac", "ba"]);
  });
  it("valor trata não informado", () => {
    expect(ids("vmin=100000")).toEqual(["sp", "nac"]);
    expect(ids("vmin=100000&vnull=0")).toEqual(["sp"]);
  });
  it("atalhos PF e sem projeto aprovado", () => {
    expect(ids("pf=1")).toEqual(["ba"]);
    expect(ids("sem_aprovado=1")).toEqual(["nac"]);
  });
  it("ordenar por prazo coloca fluxo contínuo depois das datas", () => {
    expect(ids("ordem=prazo")).toEqual(["ba", "sp", "nac"]);
  });
});

describe("facetas", () => {
  it("cada faceta conta ignorando a própria seleção", () => {
    const f = { ...filtrosVazios(), facetas: { ...filtrosVazios().facetas, abr: ["estadual"] } };
    const c = contarFacetas(TODOS, f, HOJE);
    expect(c.abr.get("estadual")).toBe(2);
    expect(c.abr.get("nacional")).toBe(1);
    expect(c.uf.get("SP")).toBe(1);
  });
});

describe("texto do prazo", () => {
  it("fala o prazo por extenso", () => {
    expect(textoPrazo(BA, HOJE)).toBe("Fecha em 5 dias");
    expect(textoPrazo(ed({ id: "h", data_limite: HOJE }), HOJE)).toBe("Fecha hoje");
    expect(textoPrazo(NAC, HOJE)).toBe("Fluxo contínuo");
  });
});
