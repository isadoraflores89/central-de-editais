// Filtros do radar. O estado vive na URL (?uf=BA&mec=rouanet...) para que
// qualquer busca possa ser compartilhada por link.

import { diasRestantes, statusEfetivo } from "./prazo";
import { normalizar } from "./texto";
import type { Edital } from "./tipos";

export const FACETAS = ["tipo", "mec", "abr", "uf", "area", "prop", "pub", "fonte", "status"] as const;
export type Faceta = (typeof FACETAS)[number];

export const PRAZOS = ["7", "15", "30", "60", "continuo"] as const;
export type Prazo = (typeof PRAZOS)[number];

export const ORDENS = ["prioridade", "prazo", "valor", "recentes", "atualizados"] as const;
export type Ordem = (typeof ORDENS)[number];

export interface Filtros {
  q: string;
  facetas: Record<Faceta, string[]>;
  prazo: Prazo[];
  de: string | null;
  ate: string | null;
  pf: boolean;
  semAprovado: boolean;
  encerrados: boolean;
  destaques: boolean;
  nacionais: boolean; // com filtro de UF, incluir editais nacionais (padrão: sim)
  vmin: number | null;
  vmax: number | null;
  vnull: boolean; // incluir valor não informado (padrão: sim)
  ordem: Ordem;
}

export function filtrosVazios(): Filtros {
  return {
    q: "",
    facetas: { tipo: [], mec: [], abr: [], uf: [], area: [], prop: [], pub: [], fonte: [], status: [] },
    prazo: [],
    de: null,
    ate: null,
    pf: false,
    semAprovado: false,
    encerrados: false,
    destaques: false,
    nacionais: true,
    vmin: null,
    vmax: null,
    vnull: true,
    ordem: "prioridade",
  };
}

const DATA = /^\d{4}-\d{2}-\d{2}$/;

function lista(v: string | null): string[] {
  return v ? v.split(",").map((s) => s.trim()).filter(Boolean) : [];
}

function numero(v: string | null): number | null {
  if (!v) return null;
  const n = Number(v);
  return Number.isFinite(n) && n >= 0 ? n : null;
}

export function lerFiltros(params: URLSearchParams): Filtros {
  const f = filtrosVazios();
  f.q = params.get("q")?.slice(0, 200) ?? "";
  for (const k of FACETAS) f.facetas[k] = lista(params.get(k));
  f.prazo = lista(params.get("prazo")).filter((p): p is Prazo => (PRAZOS as readonly string[]).includes(p));
  const de = params.get("de");
  const ate = params.get("ate");
  f.de = de && DATA.test(de) ? de : null;
  f.ate = ate && DATA.test(ate) ? ate : null;
  f.pf = params.get("pf") === "1";
  f.semAprovado = params.get("sem_aprovado") === "1";
  f.encerrados = params.get("encerrados") === "1";
  f.destaques = params.get("destaques") === "1";
  f.nacionais = params.get("nacionais") !== "0";
  f.vmin = numero(params.get("vmin"));
  f.vmax = numero(params.get("vmax"));
  f.vnull = params.get("vnull") !== "0";
  const ordem = params.get("ordem");
  f.ordem = (ORDENS as readonly string[]).includes(ordem ?? "") ? (ordem as Ordem) : "prioridade";
  return f;
}

export function escreverFiltros(f: Filtros): URLSearchParams {
  const p = new URLSearchParams();
  if (f.q.trim()) p.set("q", f.q.trim());
  for (const k of FACETAS) if (f.facetas[k].length) p.set(k, f.facetas[k].join(","));
  if (f.prazo.length) p.set("prazo", f.prazo.join(","));
  if (f.de) p.set("de", f.de);
  if (f.ate) p.set("ate", f.ate);
  if (f.pf) p.set("pf", "1");
  if (f.semAprovado) p.set("sem_aprovado", "1");
  if (f.encerrados) p.set("encerrados", "1");
  if (f.destaques) p.set("destaques", "1");
  if (!f.nacionais) p.set("nacionais", "0");
  if (f.vmin !== null) p.set("vmin", String(f.vmin));
  if (f.vmax !== null) p.set("vmax", String(f.vmax));
  if (!f.vnull) p.set("vnull", "0");
  if (f.ordem !== "prioridade") p.set("ordem", f.ordem);
  return p;
}

/** Quantos filtros estão ativos (para o botão "Filtros (3)" no celular). */
export function contarAtivos(f: Filtros): number {
  let n = FACETAS.reduce((s, k) => s + f.facetas[k].length, 0) + f.prazo.length;
  n += [f.q.trim(), f.de, f.ate, f.pf, f.semAprovado, f.encerrados, f.destaques, !f.nacionais,
    f.vmin !== null, f.vmax !== null, !f.vnull].filter(Boolean).length;
  return n;
}

/** Valores de cada faceta para um edital. */
export function valoresFaceta(e: Edital, k: Faceta, hoje: string): string[] {
  switch (k) {
    case "tipo": return e.tipo_apoio ? [e.tipo_apoio] : [];
    case "mec": return e.mecanismo;
    case "abr": return e.abrangencia ? [e.abrangencia] : [];
    case "uf": return e.ufs;
    case "area": return e.areas;
    case "prop": return e.proponente;
    case "pub": return e.publico_prioritario;
    case "fonte": return [e.fonte];
    case "status": return [statusEfetivo(e, hoje)];
  }
}

function passaFaceta(e: Edital, k: Faceta, sel: string[], f: Filtros, hoje: string): boolean {
  if (!sel.length) return true;
  if (k === "uf" && f.nacionais && e.abrangencia === "nacional") return true;
  const vals = valoresFaceta(e, k, hoje);
  return sel.some((s) => vals.includes(s));
}

function valorReferencia(e: Edital): number | null {
  return e.valor_por_projeto_max ?? e.valor_por_projeto_min;
}

function textoBusca(e: Edital): string {
  return normalizar([e.titulo, e.orgao, e.resumo, e.cidades.join(" "), e.observacoes].join(" "));
}

/**
 * Aplica todos os filtros, exceto a faceta `ignorar` (usado na contagem das
 * facetas: cada faceta mostra quantos resultados teria se fosse marcada).
 */
export function passa(e: Edital, f: Filtros, hoje: string, ignorar?: Faceta): boolean {
  if (e.curadoria.oculto) return false;
  const status = statusEfetivo(e, hoje);

  if (ignorar !== "status") {
    if (f.facetas.status.length) {
      if (!f.facetas.status.includes(status)) return false;
    } else if (status === "encerrado" && !f.encerrados) {
      return false;
    }
  }
  for (const k of FACETAS) {
    if (k === "status" || k === ignorar) continue;
    if (!passaFaceta(e, k, f.facetas[k], f, hoje)) return false;
  }

  if (f.q.trim()) {
    const termos = normalizar(f.q).split(" ");
    const alvo = textoBusca(e);
    if (!termos.every((t) => alvo.includes(t))) return false;
  }

  if (f.prazo.length) {
    const dias = diasRestantes(e, hoje);
    const ok = f.prazo.some((p) =>
      p === "continuo" ? e.fluxo_continuo : dias !== null && dias >= 0 && dias <= Number(p),
    );
    if (!ok) return false;
  }
  if (f.de && (!e.data_limite || e.data_limite < f.de)) return false;
  if (f.ate && (!e.data_limite || e.data_limite > f.ate)) return false;

  if (f.pf && !e.proponente.includes("pf")) return false;
  if (f.semAprovado && e.exige_projeto_aprovado !== false) return false;
  if (f.destaques && !e.curadoria.destaque) return false;

  if (f.vmin !== null || f.vmax !== null) {
    const v = valorReferencia(e);
    if (v === null) {
      if (!f.vnull) return false;
    } else {
      if (f.vmin !== null && v < f.vmin) return false;
      if (f.vmax !== null && v > f.vmax) return false;
    }
  } else if (!f.vnull && valorReferencia(e) === null) {
    return false;
  }
  return true;
}

export function filtrar(editais: Edital[], f: Filtros, hoje: string): Edital[] {
  return ordenar(editais.filter((e) => passa(e, f, hoje)), f.ordem, hoje);
}

export function contarFacetas(
  editais: Edital[], f: Filtros, hoje: string,
): Record<Faceta, Map<string, number>> {
  const out = {} as Record<Faceta, Map<string, number>>;
  for (const k of FACETAS) {
    const m = new Map<string, number>();
    for (const e of editais) {
      if (!passa(e, f, hoje, k)) continue;
      for (const v of new Set(valoresFaceta(e, k, hoje))) m.set(v, (m.get(v) ?? 0) + 1);
    }
    out[k] = m;
  }
  return out;
}

const DIA_LONGE = 99_999;

export function ordenar(lista: Edital[], ordem: Ordem, hoje: string): Edital[] {
  const prazo = (e: Edital) => {
    const d = diasRestantes(e, hoje);
    if (d !== null && d >= 0) return d;
    return e.fluxo_continuo ? DIA_LONGE - 1 : DIA_LONGE;
  };
  const cmp: Record<Ordem, (a: Edital, b: Edital) => number> = {
    prioridade: (a, b) => b.prioridade - a.prioridade || prazo(a) - prazo(b),
    prazo: (a, b) => prazo(a) - prazo(b) || b.prioridade - a.prioridade,
    valor: (a, b) => (valorReferencia(b) ?? -1) - (valorReferencia(a) ?? -1),
    recentes: (a, b) => b.captured_at.localeCompare(a.captured_at),
    atualizados: (a, b) => b.updated_at.localeCompare(a.updated_at),
  };
  return [...lista].sort((a, b) => cmp[ordem](a, b) || a.titulo.localeCompare(b.titulo, "pt-BR"));
}
