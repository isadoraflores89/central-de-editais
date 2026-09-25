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
  ["novo-texto", "novo-fundo"],
];

const claro = tokens(css.split("@media")[0]!);
const escuro = { ...claro, ...tokens(css.split("@media (prefers-color-scheme: dark)")[1]!.split("}")[0]!) };

describe.each([["claro", claro], ["escuro", escuro]])("tema %s", (_, t) => {
  it.each(PARES)("%s sobre %s tem contraste AA", (frente, fundo) => {
    expect(contraste(t[frente]!, t[fundo]!)).toBeGreaterThanOrEqual(4.5);
  });
});
