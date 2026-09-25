export function normalizar(texto: string | null | undefined): string {
  if (!texto) return "";
  return texto
    .normalize("NFD")
    .replace(/\p{Mn}/gu, "")
    .toLowerCase()
    .replace(/[—–]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

const BRL = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });

export function formatarReais(v: number): string {
  if (v >= 1_000_000) {
    const m = v / 1_000_000;
    return `R$ ${m.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} ${m === 1 ? "milhão" : "milhões"}`;
  }
  if (v >= 10_000) return `R$ ${(v / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 0 })} mil`;
  return BRL.format(v);
}

export function formatarData(iso: string): string {
  const [a, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
}
