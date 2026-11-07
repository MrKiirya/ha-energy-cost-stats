/**
 * Sorting of the device table: pure helpers plus the remembered choice. Every key sorts
 * by a money value (name, a zone's cost, total cost, average price), never by kWh alone.
 */

import type { Row } from "./report";

/** `name`, `total`, `avg_price` or a zone key. */
export type SortKey = string;
export type SortDirection = "asc" | "desc";

export interface SortSpec {
  sort: SortKey;
  direction: SortDirection;
}

export const RESERVED_KEYS = ["name", "total", "avg_price"];
export const DEFAULT_SORT: SortSpec = { sort: "total", direction: "desc" };

export function naturalDirection(key: SortKey): SortDirection {
  return key === "name" ? "asc" : "desc";
}

/** The `setConfig` checks of the `sort` / `sort_direction` options. */
export function validateSortConfig(sort: unknown, direction: unknown): void {
  if (sort !== undefined && (typeof sort !== "string" || sort === "")) {
    throw new Error("sort must be name, total, avg_price or a zone key");
  }
  if (direction !== undefined && direction !== "asc" && direction !== "desc") {
    throw new Error(`sort_direction must be asc or desc, not ${String(direction)}`);
  }
}

/** A sort naming a zone that is not in the report falls back to the default. */
export function resolveSort(spec: SortSpec, zoneKeys: readonly string[]): SortSpec {
  if (RESERVED_KEYS.includes(spec.sort) || zoneKeys.includes(spec.sort)) return spec;
  return DEFAULT_SORT;
}

function finite(value: string | null | undefined): number | null {
  if (value === null || value === undefined) return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

/** The money value a row is sorted by, or `null` when it is unpriced. */
export function sortValue(row: Row, key: SortKey): number | null {
  if (key === "total") return finite(row.cost);
  if (key === "avg_price") {
    const cost = finite(row.cost);
    const amount = finite(row.kwh);
    if (cost === null || amount === null || amount <= 0) return null;
    const price = cost / amount;
    return Number.isFinite(price) ? price : null;
  }
  const cell = row.zones.find((z) => z.key === key);
  return cell ? finite(cell.cost) : null;
}

/**
 * Compares two entity ids. Unpriced values sort last in both directions; ties are broken
 * by name ascending, then by entity id, independent of the direction.
 */
export function makeComparator(
  spec: SortSpec,
  rows: ReadonlyMap<string, Row>,
  names: ReadonlyMap<string, string>,
  language: string,
): (a: string, b: string) => number {
  const collator = new Intl.Collator(language, { sensitivity: "base", numeric: true });
  const sign = spec.direction === "asc" ? 1 : -1;
  const nameOf = (id: string) => names.get(id) ?? id;
  const byName = (a: string, b: string) =>
    collator.compare(nameOf(a), nameOf(b)) || (a < b ? -1 : a > b ? 1 : 0);
  if (spec.sort === "name") {
    return (a, b) => {
      const result = collator.compare(nameOf(a), nameOf(b));
      if (result !== 0) return sign * result;
      return a < b ? -1 : a > b ? 1 : 0;
    };
  }
  const value = (id: string) => {
    const row = rows.get(id);
    return row ? sortValue(row, spec.sort) : null;
  };
  return (a, b) => {
    const va = value(a);
    const vb = value(b);
    if (va !== null && vb !== null && va !== vb) return sign * (va < vb ? -1 : 1);
    if (va === null && vb !== null) return 1;
    if (va !== null && vb === null) return -1;
    return byName(a, b);
  };
}

export function storageKey(
  pathname: string,
  config: { title?: string; entities?: string[]; sort?: string; sort_direction?: string },
): string {
  const identity = JSON.stringify([
    config.title ?? null,
    config.entities ?? null,
    config.sort ?? null,
    config.sort_direction ?? null,
  ]);
  return `energy-cost-stats-card.sort.v1|${pathname}|${identity}`;
}

export function loadSort(key: string): SortSpec | undefined {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return undefined;
    const data = JSON.parse(raw) as Partial<SortSpec> | null;
    if (
      data &&
      typeof data.sort === "string" &&
      data.sort !== "" &&
      (data.direction === "asc" || data.direction === "desc")
    ) {
      return { sort: data.sort, direction: data.direction };
    }
  } catch {
    // Storage disabled or malformed: use the default.
  }
  return undefined;
}

export function saveSort(key: string, spec: SortSpec): void {
  try {
    localStorage.setItem(key, JSON.stringify(spec));
  } catch {
    // Storage disabled or full: the choice just is not remembered.
  }
}
