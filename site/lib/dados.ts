// Leitura dos dados no build (só roda no servidor / na geração estática).
import "server-only";

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { parse } from "yaml";

import type { ConfigSite, DocumentoEditais, Edital, Preset } from "./tipos";

const RAIZ = join(process.cwd(), "..");

let cache: DocumentoEditais | null = null;

export function documento(): DocumentoEditais {
  if (!cache) {
    const bruto = readFileSync(join(RAIZ, "data", "editais.json"), "utf-8");
    cache = JSON.parse(bruto) as DocumentoEditais;
    if (!cache.editais?.length) {
      // Decisão D9: nunca publicar lista vazia.
      throw new Error("data/editais.json está vazio — build interrompido.");
    }
  }
  return cache;
}

export function editais(): Edital[] {
  return documento().editais;
}

export function editalPorId(id: string): Edital | undefined {
  return editais().find((e) => e.id === id);
}

export function presets(): Preset[] {
  return parse(readFileSync(join(RAIZ, "config", "presets.yaml"), "utf-8")) as Preset[];
}

/** Data de referência do build (AAAA-MM-DD, fuso da Bahia). */
export function dataDoBuild(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Bahia" }).format(new Date());
}

export function configSite(): ConfigSite {
  return parse(readFileSync(join(RAIZ, "config", "site.yaml"), "utf-8")) as ConfigSite;
}
