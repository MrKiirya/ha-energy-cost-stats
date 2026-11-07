import { afterEach, describe, expect, it, vi } from "vitest";
import {
  loadSort,
  makeComparator,
  naturalDirection,
  resolveSort,
  saveSort,
  sortValue,
  storageKey,
  validateSortConfig,
} from "../src/sort";
import type { Row } from "../src/report";
import { row } from "./fixtures";

function costRow(id: string, t1: string | null, t2: string | null = null): Row {
  return row(id, ["1.000", t1], ["1.000", t2]);
}

describe("sortValue", () => {
  it("reads the total, average price or zone cost by key", () => {
    const r = costRow("a", "10.00", "5.00");
    expect(sortValue(r, "total")).toBe(15);
    expect(sortValue(r, "t2")).toBe(5);
    expect(sortValue(r, "avg_price")).toBeCloseTo(7.5);
    // Zones in another order are still found by key.
    const swapped = { ...r, zones: [...r.zones].reverse() };
    expect(sortValue(swapped, "t1")).toBe(10);
  });

  it("returns null for missing, null and non-numeric values", () => {
    const r = costRow("a", null, null);
    expect(sortValue(r, "total")).toBeNull();
    expect(sortValue(r, "t1")).toBeNull();
    expect(sortValue(r, "t9")).toBeNull();
    expect(sortValue({ ...costRow("a", "1.00"), cost: "abc" }, "total")).toBeNull();
    expect(sortValue({ ...costRow("a", "1.00"), kwh: null }, "avg_price")).toBeNull();
    expect(sortValue({ ...costRow("a", "1.00"), kwh: "0.000" }, "avg_price")).toBeNull();
  });

  it("never uses kWh for cost keys", () => {
    const big = { ...costRow("a", "1.00", "1.00"), kwh: "999.000" };
    expect(sortValue(big, "total")).toBe(2);
  });
});

describe("comparator", () => {
  const rows = new Map([
    ["a", costRow("a", "5.00")],
    ["b", costRow("b", null)],
    ["c", costRow("c", "10.00")],
  ]);
  const names = new Map([
    ["a", "Alpha"],
    ["b", "Bravo"],
    ["c", "Charlie"],
  ]);
  const order = (spec: { sort: string; direction: "asc" | "desc" }, ids = ["a", "b", "c"]) =>
    [...ids].sort(makeComparator(spec, rows, names, "en"));

  it("puts unpriced last in both directions", () => {
    expect(order({ sort: "total", direction: "desc" })).toEqual(["c", "a", "b"]);
    expect(order({ sort: "total", direction: "asc" })).toEqual(["a", "c", "b"]);
  });

  it("breaks ties by name, then entity id", () => {
    const tied = new Map([
      ["x", costRow("x", "5.00")],
      ["y", costRow("y", "5.00")],
      ["z", costRow("z", null)],
      ["w", costRow("w", null)],
    ]);
    const tiedNames = new Map([
      ["x", "Same"],
      ["y", "Same"],
      ["z", "Zed"],
      ["w", "Able"],
    ]);
    for (const direction of ["asc", "desc"] as const) {
      const out = ["z", "y", "w", "x"].sort(
        makeComparator({ sort: "total", direction }, tied, tiedNames, "en"),
      );
      expect(out).toEqual(["x", "y", "w", "z"]);
    }
  });

  it("sorts names with the collator", () => {
    const n = new Map([
      ["a", "Plug 10"],
      ["b", "Plug 2"],
    ]);
    const r = new Map<string, Row>();
    expect(["a", "b"].sort(makeComparator({ sort: "name", direction: "asc" }, r, n, "en"))).toEqual([
      "b",
      "a",
    ]);
    expect(["a", "b"].sort(makeComparator({ sort: "name", direction: "desc" }, r, n, "en"))).toEqual([
      "a",
      "b",
    ]);
    const ru = new Map([
      ["a", "Ёлка"],
      ["b", "Арка"],
      ["c", "Яма"],
    ]);
    expect(
      ["c", "a", "b"].sort(makeComparator({ sort: "name", direction: "asc" }, r, ru, "ru")),
    ).toEqual(["b", "a", "c"]);
  });

  it("sorts by average price", () => {
    const r = new Map([
      ["a", { ...costRow("a", "10.00"), kwh: "5.000" }],
      ["b", { ...costRow("b", "10.00"), kwh: "2.000" }],
      ["c", { ...costRow("c", "10.00"), kwh: null }],
    ]);
    expect(
      ["a", "b", "c"].sort(makeComparator({ sort: "avg_price", direction: "desc" }, r, names, "en")),
    ).toEqual(["b", "a", "c"]);
  });
});

describe("naturalDirection", () => {
  it("is ascending for names and descending for money", () => {
    expect(naturalDirection("name")).toBe("asc");
    expect(naturalDirection("total")).toBe("desc");
    expect(naturalDirection("avg_price")).toBe("desc");
    expect(naturalDirection("t1")).toBe("desc");
  });
});

describe("validateSortConfig", () => {
  it("accepts valid options", () => {
    for (const sort of [undefined, "name", "total", "avg_price", "t1"]) {
      expect(() => validateSortConfig(sort, undefined)).not.toThrow();
    }
    for (const direction of ["asc", "desc"]) {
      expect(() => validateSortConfig("t1", direction)).not.toThrow();
    }
  });

  it("rejects invalid options", () => {
    expect(() => validateSortConfig("", undefined)).toThrow("sort must be");
    expect(() => validateSortConfig(3, undefined)).toThrow("sort must be");
    expect(() => validateSortConfig("total", "up")).toThrow("sort_direction");
  });
});

describe("resolveSort", () => {
  it("falls back for an unknown zone", () => {
    expect(resolveSort({ sort: "t9", direction: "asc" }, ["t1", "t2"])).toEqual({
      sort: "total",
      direction: "desc",
    });
    expect(resolveSort({ sort: "t2", direction: "asc" }, ["t1", "t2"])).toEqual({
      sort: "t2",
      direction: "asc",
    });
    expect(resolveSort({ sort: "name", direction: "desc" }, [])).toEqual({
      sort: "name",
      direction: "desc",
    });
  });
});

describe("storage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it("round-trips and ignores malformed values", () => {
    const key = storageKey("/lovelace/0", { title: "T", entities: ["sensor.a"], sort: "name" });
    expect(key).toContain("/lovelace/0");
    expect(key).toContain("name");
    expect(loadSort(key)).toBeUndefined();
    saveSort(key, { sort: "t1", direction: "asc" });
    expect(loadSort(key)).toEqual({ sort: "t1", direction: "asc" });
    localStorage.setItem(key, "{oops");
    expect(loadSort(key)).toBeUndefined();
    localStorage.setItem(key, JSON.stringify({ sort: "", direction: "asc" }));
    expect(loadSort(key)).toBeUndefined();
    localStorage.setItem(key, JSON.stringify({ sort: "t1", direction: "up" }));
    expect(loadSort(key)).toBeUndefined();
  });

  it("survives a localStorage that throws", () => {
    const boom = () => {
      throw new Error("denied");
    };
    vi.stubGlobal("localStorage", { getItem: boom, setItem: boom, removeItem: boom });
    expect(() => saveSort("k", { sort: "name", direction: "asc" })).not.toThrow();
    expect(loadSort("k")).toBeUndefined();
  });
});
