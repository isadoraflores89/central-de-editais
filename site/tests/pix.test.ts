import { describe, expect, it } from "vitest";

import { brCode, crc16 } from "@/lib/pix";

describe("PIX", () => {
  it("reproduz o exemplo do manual do Banco Central", () => {
    const esperado =
      "00020126580014br.gov.bcb.pix0136123e4567-e12b-12d1-a456-426655440000" +
      "5204000053039865802BR5913Fulano de Tal6008BRASILIA62070503***63041D3D";
    expect(brCode("123e4567-e12b-12d1-a456-426655440000", "Fulano de Tal", "BRASILIA")).toBe(esperado);
  });
  it("remove acentos e corta nome e cidade nos limites", () => {
    const c = brCode("a@b.com", "Flores Educação e Cultura Ltda", "São Paulo de Olivença");
    expect(c).toContain("5925Flores Educacao e Cultur");
    expect(c).toContain("6015Sao Paulo de Ol");
    expect(crc16(c.slice(0, -4))).toBe(c.slice(-4));
  });
});
