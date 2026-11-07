import type { Bucket, CompareDocument, ReportDocument, Row } from "../src/report";

export function row(
  entity_id: string | null,
  day: [string | null, string | null],
  night: [string | null, string | null],
  status: Row["status"] = "complete",
): Row {
  const kwhs = [day[0], night[0]].filter((v): v is string => v !== null);
  const costs = [day[1], night[1]].filter((v): v is string => v !== null);
  const sum = (values: string[], digits: number) =>
    values.length ? values.reduce((a, b) => a + Number(b), 0).toFixed(digits) : null;
  return {
    entity_id,
    kwh: sum(kwhs, 3),
    cost: sum(costs, 2),
    unpriced_kwh: "0.000",
    estimated_kwh: status === "estimated" ? "1.000" : "0.000",
    excluded_kwh: "0.000",
    status,
    coverage: {
      expected: 24,
      measured: status === "estimated" ? 20 : 24,
      estimated: status === "estimated" ? 4 : 0,
      excluded: 0,
      missing: 0,
    },
    zones: [
      { key: "t1", kwh: day[0], cost: day[1], price: "10.3000" },
      { key: "t2", kwh: night[0], cost: night[1], price: "4.4300" },
    ],
  };
}

function bucket(start: string, end: string, rows: Row[], total: Row): Bucket {
  return { start, end, hours: 24, rows, total };
}

/** Generic two-zone report for 2026-11-01 .. 2026-11-02 grouped by day. */
export function report(overrides: Partial<ReportDocument> = {}): ReportDocument {
  const d1 = [
    row("sensor.plug_01", ["1.000", "10.30"], ["2.000", "8.86"]),
    row("sensor.plug_02", ["0.500", "5.15"], [null, null], "estimated"),
  ];
  const d2 = [
    row("sensor.plug_01", ["2.000", "20.60"], ["0.000", "0.00"]),
    row("sensor.plug_02", ["1.000", "10.30"], ["1.000", "4.43"]),
  ];
  const totalRows = [
    row("sensor.plug_01", ["3.000", "30.90"], ["2.000", "8.86"]),
    row("sensor.plug_02", ["1.500", "15.45"], ["1.000", "4.43"], "estimated"),
  ];
  const total = row(null, ["4.500", "46.35"], ["3.000", "13.29"], "estimated");
  return {
    schema_version: 1,
    time_zone: "Europe/Moscow",
    currency: "RUB",
    start: "2026-11-01T00:00:00+03:00",
    end: "2026-11-03T00:00:00+03:00",
    grouping: "day",
    zones: [
      { key: "t1", name: "Day" },
      { key: "t2", name: "Night" },
    ],
    plans: [{ valid_from: "2026-01-01", name: "Two-zone" }],
    devices: [
      { entity_id: "sensor.plug_01", name: "Plug 01", statistics: "ok", upstream: null },
      { entity_id: "sensor.plug_02", name: "Plug 02", statistics: "ok", upstream: null },
    ],
    buckets: [
      bucket(
        "2026-11-01T00:00:00+03:00",
        "2026-11-02T00:00:00+03:00",
        d1,
        row(null, ["1.500", "15.45"], ["2.000", "8.86"], "estimated"),
      ),
      bucket(
        "2026-11-02T00:00:00+03:00",
        "2026-11-03T00:00:00+03:00",
        d2,
        row(null, ["3.000", "30.90"], ["1.000", "4.43"]),
      ),
    ],
    totals: bucket("2026-11-01T00:00:00+03:00", "2026-11-03T00:00:00+03:00", totalRows, total),
    unpriced_hours: 0,
    issues: [
      {
        kind: "estimated",
        entity_id: "sensor.plug_02",
        start: "2026-11-01T02:00:00+03:00",
        end: "2026-11-01T06:00:00+03:00",
        hours: 4,
        kwh: "1.000",
      },
    ],
    ...overrides,
  };
}

/** A `total`-grouped document with the given total cost and kWh (comparison fixtures). */
export function totalDoc(
  cost: string | null,
  kwh: string | null = "50.000",
  overrides: Partial<ReportDocument> = {},
): ReportDocument {
  const doc = report({ grouping: "total", buckets: [], ...overrides });
  doc.totals.total = { ...doc.totals.total, cost, kwh };
  return doc;
}

/** Actual 100.00 against a dearer (112.50) and a cheaper (90.00) tariff. */
export function compareDoc(overrides: Partial<CompareDocument> = {}): CompareDocument {
  return {
    actual: totalDoc("100.00"),
    tariffs: [
      { id: "three_zone", name: "Three-zone", report: totalDoc("112.50", "50.000", { plans: [] }) },
      { id: "flat", name: "Flat", report: totalDoc("90.00", "50.000", { plans: [] }) },
    ],
    ...overrides,
  };
}
