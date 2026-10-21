import { describe, expect, it } from "vitest";
import { fmtDataHoraBR, parseNum, toMs } from "./format";

describe("parseNum (números digitados em português)", () => {
  it("vírgula é decimal e ponto é milhar", () => {
    expect(parseNum("55,5")).toBe(55.5);
    expect(parseNum("1.234,56")).toBe(1234.56);
    expect(parseNum("R$ 60")).toBe(60);
  });
  it("sem vírgula, ponto seguido de 3 dígitos é milhar (como o site mostra 1.572)", () => {
    expect(parseNum("1.800")).toBe(1800);
    expect(parseNum("12.345.678")).toBe(12345678);
    expect(parseNum("1.572")).toBe(1572);
  });
  it("sem vírgula, ponto com 1 ou 2 dígitos (ou zero à esquerda) é decimal", () => {
    expect(parseNum("1.8")).toBe(1.8);
    expect(parseNum("1.25")).toBe(1.25);
    expect(parseNum("0.500")).toBe(0.5);
  });
  it("vazio é null e lixo é NaN", () => {
    expect(parseNum("")).toBeNull();
    expect(parseNum("   ")).toBeNull();
    expect(Number.isNaN(parseNum("abc"))).toBe(true);
  });
});

describe("datas", () => {
  it("toMs lê os horários do PNCP como Brasília e devolve null para texto sem hora", () => {
    expect(toMs("2026-10-23T10:00")).toBe(Date.parse("2026-10-23T10:00:00-03:00"));
    expect(toMs("2026-10-23")).toBeNull();
    expect(toMs(null)).toBeNull();
  });
  it("fmtDataHoraBR mostra um instante UTC no horário de Brasília", () => {
    expect(fmtDataHoraBR("2026-10-21T12:10:00.000Z")).toBe("21/10/2026 09:10");
    expect(fmtDataHoraBR("")).toBe("—");
  });
});
