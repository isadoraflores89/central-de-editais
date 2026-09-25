// Garante que public/api/editais.json exista antes do build/dev.
// O pipeline Python (python -m pipeline run --destino site/public/api) gera
// JSON, CSV, XLSX e DB; se só houver o data/editais.json, copiamos ele.
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const raiz = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const origem = join(raiz, "data", "editais.json");
const destinoDir = join(raiz, "site", "public", "api");
const destino = join(destinoDir, "editais.json");

if (!existsSync(origem)) {
  console.error("data/editais.json não encontrado. Rode: python -m pipeline import-seed");
  process.exit(1);
}
mkdirSync(destinoDir, { recursive: true });
if (!existsSync(destino)) {
  copyFileSync(origem, destino);
  console.log("copiado data/editais.json -> site/public/api/editais.json");
}
