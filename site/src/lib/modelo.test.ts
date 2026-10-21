import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { DEF, passes, sortList } from "./filtros";
import { parseNum } from "./format";
import { preparar, tiposTexto } from "./modelo";
import type { Painel } from "../types";

// Mesmos dados de teste do pytest (tests/fixtures/data_min.json), para o site e o coletor concordarem.
const data = JSON.parse(readFileSync(new URL("../../../tests/fixtures/data_min.json", import.meta.url), "utf-8")) as Painel;

describe("parseNum", () => {
  it("lê números no formato brasileiro", () => {
    expect(parseNum("55,5")).toBe(55.5);
    expect(parseNum("1.234,56")).toBe(1234.56);
    expect(parseNum("R$ 60")).toBe(60);
    expect(parseNum("")).toBeNull();
    expect(Number.isNaN(parseNum("abc"))).toBe(true);
  });
});

describe("filtros de distância", () => {
  const prep = preparar(data, {}, {});
  it("dist mostra só as até N km e distMin só as além de N km; juntos cobrem todas", () => {
    const todas = prep.compras.filter((c) => passes(c, DEF(), {}, false));
    const perto = prep.compras.filter((c) => passes(c, { ...DEF(), dist: 600 }, {}, false)); // dados de teste: 189 a 1.917 km
    const longe = prep.compras.filter((c) => passes(c, { ...DEF(), distMin: 600 }, {}, false));
    expect(perto.length).toBeGreaterThan(0);
    expect(longe.length).toBeGreaterThan(0);
    expect(perto.every((c) => c.dist != null && c.dist <= 600)).toBe(true);
    expect(longe.every((c) => c.dist != null && c.dist > 600)).toBe(true);
    expect(perto.length + longe.length).toBe(todas.filter((c) => c.dist != null).length);
  });
});

describe("preparar", () => {
  const prep = preparar(data, {}, {});
  it("calcula item principal, nível e margem com a mesma regra do coletor", () => {
    const c = prep.byk["18243295000192-1-000080/2026"];
    expect(c._main?.rkg).toBe(66.03);
    expect(c._niv).toBe("Superior");
    expect(c._mg).not.toBeNull();
    expect(c._mg!.mp).toBeGreaterThan(-1);
    expect(c._mg!.custo).toBeGreaterThan(30);
  });
  it("esconde duplicatas por padrão e as mostra quando pedido", () => {
    const F = DEF(), now = Date.parse("2026-10-18T12:00:00-03:00");
    expect(prep.compras.filter((c) => passes(c, F, {}, false, undefined, now)).length).toBe(7);
    expect(prep.compras.filter((c) => passes(c, { ...F, hideDup: false }, {}, false, undefined, now)).length).toBe(8);
  });
  it("ordena por prazo com encerradas nunca aparecendo", () => {
    const now = Date.parse("2026-10-18T12:00:00-03:00");
    const L = sortList(prep.compras.filter((c) => passes(c, DEF(), {}, false, undefined, now)), "prazo");
    for (let i = 1; i < L.length; i++) expect((L[i]._ms ?? 1e15) >= (L[i - 1]._ms ?? 1e15)).toBe(true);
  });
  it("piso muda a comparação sem mudar a margem", () => {
    const comPiso = preparar(data, { Superior: 70 }, {});
    const c = comPiso.byk["18243295000192-1-000080/2026"];
    expect(c._cmp?.ok).toBe(false); // 66,03 < 70
    expect(c._mg!.custo).toBeCloseTo(prep.byk[c.chave]._mg!.custo, 6);
  });
  it("custo próprio de torra sobe o custo por kg", () => {
    const caro = preparar(data, {}, { torra: 15 });
    const c = caro.byk["18243295000192-1-000080/2026"];
    expect(c._mg!.custo).toBeGreaterThan(prep.byk[c.chave]._mg!.custo + 10);
  });
});

describe("tiposTexto", () => {
  it("não repete o tipo quando há a versão descafeinada", () => {
    expect(tiposTexto(["Torrado e moído", "Torrado e moído (descafeinado)"])).toBe("Torrado e moído (+ descafeinado)");
    expect(tiposTexto(["Torrado e moído (descafeinado)"])).toBe("Torrado e moído (descafeinado)");
    expect(tiposTexto(["Grão", "Torrado e moído"])).toBe("Grão, Torrado e moído");
  });
});
