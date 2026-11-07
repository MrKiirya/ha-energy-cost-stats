/** Pure helpers of the comparison section and the nested device rows. */

export interface Difference {
  /** compared − actual; positive = the compared tariff would have cost more. */
  amount: number | null;
  /** `amount` as a percentage of the actual cost. */
  percent: number | null;
}

/** Display-only difference of two decimal strings; `null` never becomes 0. */
export function difference(actual: string | null, compared: string | null): Difference {
  if (actual === null || compared === null) return { amount: null, percent: null };
  const a = Number(actual);
  const c = Number(compared);
  if (!Number.isFinite(a) || !Number.isFinite(c)) return { amount: null, percent: null };
  const amount = c - a;
  return { amount, percent: a === 0 ? null : (amount / a) * 100 };
}

export interface NestedRow {
  entity_id: string;
  depth: number;
}

/**
 * Orders devices so each one follows its upstream (depth-first, report order among
 * siblings). A device whose upstream is not in the list keeps its place as a root.
 * A malformed cycle cannot loop: its members are appended as roots.
 */
export function orderNested(
  devices: readonly { entity_id: string; upstream?: string | null }[],
): NestedRow[] {
  const ids = new Set(devices.map((d) => d.entity_id));
  const children = new Map<string, string[]>();
  const roots: string[] = [];
  for (const device of devices) {
    const up = device.upstream;
    if (up && up !== device.entity_id && ids.has(up)) {
      const list = children.get(up) ?? [];
      list.push(device.entity_id);
      children.set(up, list);
    } else {
      roots.push(device.entity_id);
    }
  }
  const out: NestedRow[] = [];
  const seen = new Set<string>();
  const visit = (id: string, depth: number): void => {
    if (seen.has(id)) return;
    seen.add(id);
    out.push({ entity_id: id, depth });
    for (const child of children.get(id) ?? []) visit(child, depth + 1);
  };
  for (const id of roots) visit(id, 0);
  for (const device of devices) visit(device.entity_id, 0);
  return out;
}
