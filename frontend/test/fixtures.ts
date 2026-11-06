import type { Bucket, ComparisonDocument, ReportDocument, Row } from "../src/report";

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
      { entity_id: "sensor.plug_01", name: "Plug 01", statistics: "ok" },
      { entity_id: "sensor.plug_02", name: "Plug 02", statistics: "ok" },
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

/** A grouping-total document with the given zones and total cost. */
export function totalReport(
  zones: { key: string; name: string; kwh: string; cost: string | null }[],
  planName: string,
): ReportDocument {
  const doc = report({ grouping: "total" });
  const total: Row = {
    ...doc.totals.total,
    kwh: "7.500",
    cost: zones.some((z) => z.cost === null)
      ? null
      : zones.reduce((a, z) => a + Number(z.cost), 0).toFixed(2),
    zones: zones.map((z) => ({ key: z.key, kwh: z.kwh, cost: z.cost, price: null })),
  };
  doc.zones = zones.map((z) => ({ key: z.key, name: z.name }));
  doc.plans = [{ valid_from: "1970-01-01", name: planName }];
  doc.totals = { ...doc.totals, total, rows: [] };
  doc.buckets = [doc.totals];
  return doc;
}

export function comparison(): ComparisonDocument {
  return {
    actual: totalReport(
      [
        { key: "t1", name: "Day", kwh: "4.500", cost: "46.35" },
        { key: "t2", name: "Night", kwh: "3.000", cost: "13.29" },
      ],
      "Two-zone",
    ),
    scenarios: [
      {
        name: "Single-rate",
        preset: "single_rate",
        report: totalReport([{ key: "t0", name: "Single-rate", kwh: "7.500", cost: "56.25" }], "Single-rate"),
      },
      {
        name: "Three-zone",
        preset: "ru_three_zone",
        report: totalReport(
          [
            { key: "t1", name: "Peak", kwh: "2.000", cost: "24.00" },
            { key: "t2", name: "Night", kwh: "3.000", cost: "12.00" },
            { key: "t3", name: "Semi-peak", kwh: "2.500", cost: "22.50" },
          ],
          "Three-zone",
        ),
      },
    ],
  };
}
