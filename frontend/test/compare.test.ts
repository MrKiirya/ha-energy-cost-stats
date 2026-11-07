import { describe, expect, it } from "vitest";
import { difference, orderNested } from "../src/compare";
import { hassChanged } from "../src/hass";
import type { HassLike } from "../src/report";

describe("difference", () => {
  it("is compared minus actual, with the percent of actual", () => {
    expect(difference("100.00", "112.50")).toEqual({ amount: 12.5, percent: 12.5 });
    const cheaper = difference("100.00", "90.00");
    expect(cheaper.amount).toBe(-10);
    expect(cheaper.percent).toBe(-10);
  });

  it("is unknown when either cost is null, never zero", () => {
    expect(difference(null, "10.00")).toEqual({ amount: null, percent: null });
    expect(difference("10.00", null)).toEqual({ amount: null, percent: null });
    expect(difference(null, null)).toEqual({ amount: null, percent: null });
  });

  it("has no percent when the actual cost is zero", () => {
    expect(difference("0.00", "5.00")).toEqual({ amount: 5, percent: null });
  });

  it("rejects garbage instead of showing NaN", () => {
    expect(difference("abc", "1.00")).toEqual({ amount: null, percent: null });
  });
});

describe("orderNested", () => {
  const dev = (entity_id: string, upstream: string | null = null) => ({ entity_id, upstream });

  it("keeps report order without upstreams", () => {
    expect(orderNested([dev("a"), dev("b")])).toEqual([
      { entity_id: "a", depth: 0 },
      { entity_id: "b", depth: 0 },
    ]);
  });

  it("places children right after their upstream, depth first", () => {
    const out = orderNested([dev("child", "parent"), dev("other"), dev("parent")]);
    expect(out).toEqual([
      { entity_id: "other", depth: 0 },
      { entity_id: "parent", depth: 0 },
      { entity_id: "child", depth: 1 },
    ]);
  });

  it("handles chains and sibling order", () => {
    const out = orderNested([dev("c1", "p"), dev("g", "c1"), dev("p"), dev("c2", "p")]);
    expect(out).toEqual([
      { entity_id: "p", depth: 0 },
      { entity_id: "c1", depth: 1 },
      { entity_id: "g", depth: 2 },
      { entity_id: "c2", depth: 1 },
    ]);
  });

  it("keeps the position of a device whose upstream is not in the report", () => {
    const out = orderNested([dev("a"), dev("b", "missing"), dev("c")]);
    expect(out.map((r) => r.entity_id)).toEqual(["a", "b", "c"]);
    expect(out.every((r) => r.depth === 0)).toBe(true);
  });

  it("terminates on a malformed cycle and on a self reference", () => {
    const out = orderNested([dev("a", "b"), dev("b", "a"), dev("c", "c")]);
    expect(out.map((r) => r.entity_id).sort()).toEqual(["a", "b", "c"]);
  });
});

describe("hassChanged", () => {
  const hass = (language = "en", localeLanguage = "en", timeZone = "UTC"): HassLike => ({
    callWS: async <T>() => ({}) as T,
    language,
    locale: { language: localeLanguage },
    config: { time_zone: timeZone },
  });

  it("is true for the first hass", () => {
    expect(hassChanged(hass(), undefined)).toBe(true);
  });

  it("is false for another object with the same language and time zone", () => {
    expect(hassChanged({ ...hass(), states: { a: 1 } } as HassLike, hass())).toBe(false);
  });

  it("is true when the language, the locale language or the time zone changes", () => {
    expect(hassChanged(hass("ru"), hass())).toBe(true);
    expect(hassChanged(hass("en", "ru"), hass())).toBe(true);
    expect(hassChanged(hass("en", "en", "Europe/Berlin"), hass())).toBe(true);
  });

  it("is false when both are missing", () => {
    expect(hassChanged(undefined, undefined)).toBe(false);
  });
});
