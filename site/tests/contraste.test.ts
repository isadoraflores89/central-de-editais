// Garante contraste AA (4,5:1) dos pares de cor usados em texto (decisão D8).
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const css = readFileSync(join(__dirname, "..", "app", "globals.css"), "utf-8");

function tokens(bloco: string): Record<string, string> {
  return Object.fromEntries([...bloco.matchAll(/--([\w-]+):\s*(#[0-9a-f]{6})/gi)].map((m) => [m[1], m[2]]));
}

function luminancia(hex: string): number {
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0]! + 0.7152 * c[1]! + 0.0722 * c[2]!;
}

function contraste(a: string, b: string): number {
  const [l1, l2] = [luminancia(a), luminancia(b)].sort((x, y) => y - x);
  return (l1! + 0.05) / (l2! + 0.05);
}

const PARES: [string, string][] = [
  ["texto", "fundo"], ["texto", "superficie"], ["texto-suave", "fundo"], ["texto-suave", "superficie"],
  ["texto", "chip-fundo"], ["texto-suave", "chip-fundo"], ["marca-texto", "marca"], ["acento", "superficie"],
  ["acento", "chip-fundo"], ["critica-texto", "critica-fundo"], ["alta-texto", "alta-fundo"],
  ["novo-texto", "novo-fundo"], ["cabecalho-texto", "cabecalho-fundo"], ["rosa-texto", "rosa"], ["capa-texto", "grad-roxo"], ["capa-texto", "grad-azul"],
  ["prazo-normal-texto", "prazo-normal-fundo"],
];

// Escuro é o padrão (:root); o claro sobrescreve em :root[data-theme="light"].
const blocoRaiz = css.slice(css.indexOf(":root {"), css.indexOf("}", css.indexOf(":root {")));
const inicioClaro = css.indexOf(':root[data-theme="light"] {');
const blocoClaro = css.slice(inicioClaro, css.indexOf("}", inicioClaro));
const escuro = tokens(blocoRaiz);
const claro = { ...escuro, ...tokens(blocoClaro) };
// Pontas do degradê da capa (texto escuro sobre roxo e sobre azul).
const DEGRADE: Record<string, string> = { "grad-roxo": "#a77bff", "grad-azul": "#3b82ff" };

describe.each([["claro", { ...claro, ...DEGRADE }], ["escuro", { ...escuro, ...DEGRADE }]])("tema %s", (_, t) => {
  it.each(PARES)("%s sobre %s tem contraste AA", (frente, fundo) => {
    expect(contraste(t[frente]!, t[fundo]!)).toBeGreaterThanOrEqual(4.5);
  });
});
