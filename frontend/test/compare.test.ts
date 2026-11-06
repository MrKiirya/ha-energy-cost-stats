import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import "../src/index";
import type { EnergyCostStatsCard } from "../src/card";
import type { HassLike, ScenarioConfig } from "../src/report";
import { comparison, report } from "./fixtures";

type Msg = Record<string, unknown>;

const COMPARE: ScenarioConfig[] = [
  { preset: "single_rate", prices: { t0: 7.5 } },
  { name: "Three-zone", preset: "ru_three_zone", prices: { t1: "12", t3: "9", t2: "4" } },
];

function makeHass(
  compare: (msg: Msg) => Promise<unknown> = async () => comparison(),
): HassLike & { calls: Msg[] } {
  const calls: Msg[] = [];
  return {
    calls,
    language: "en",
    locale: { language: "en" },
    config: { time_zone: "Europe/Moscow", currency: "RUB" },
    callWS: <T>(msg: Msg) => {
      calls.push(msg);
      return (msg.type === "energy_cost_stats/compare" ? compare(msg) : Promise.resolve(report())) as Promise<T>;
    },
  };
}

async function settle(card: EnergyCostStatsCard): Promise<void> {
  for (let i = 0; i < 6; i++) {
    await card.updateComplete;
    await new Promise((r) => setTimeout(r, 0));
  }
}

async function mount(config: Record<string, unknown>, hass = makeHass()) {
  const card = document.createElement("energy-cost-stats-card") as EnergyCostStatsCard;
  card.setConfig({ type: "custom:energy-cost-stats-card", ...config });
  card.hass = hass;
  document.body.appendChild(card);
  await settle(card);
  return { card, hass };
}

const compareCalls = (hass: { calls: Msg[] }) =>
  hass.calls.filter((c) => c.type === "energy_cost_stats/compare");

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-11-06T12:00:00Z"));
});

afterEach(() => {
  vi.useRealTimers();
  document.body.innerHTML = "";
});

describe("tariff comparison", () => {
  it("is not requested without a compare config", async () => {
    const { card, hass } = await mount({});
    expect(compareCalls(hass)).toEqual([]);
    expect(card.shadowRoot!.querySelector("details.comparison")).toBeNull();
  });

  it("requests the same period with prices as decimal strings", async () => {
    const { hass } = await mount({ compare: COMPARE, entities: ["sensor.plug_01"] });
    const [reportCall] = hass.calls;
    expect(compareCalls(hass)).toEqual([
      {
        type: "energy_cost_stats/compare",
        start: "2026-11-01",
        end: reportCall!.end,
        entities: ["sensor.plug_01"],
        scenarios: [
          { preset: "single_rate", prices: { t0: "7.5" } },
          { name: "Three-zone", preset: "ru_three_zone", prices: { t1: "12", t3: "9", t2: "4" } },
        ],
      },
    ]);
  });

  it("renders current tariff and scenarios, marks the cheapest and the differences", async () => {
    const { card } = await mount({ compare: COMPARE });
    const rows = [...card.shadowRoot!.querySelectorAll("table.compare tbody tr")];
    expect(rows).toHaveLength(3);
    const text = rows.map((r) => (r.textContent ?? "").replace(/\s+/g, " "));
    expect(text[0]).toContain("Current tariff");
    expect(text[0]).toContain("Two-zone");
    expect(text[0]).toContain("59.64");
    // Single-rate: 56.25 - 59.64 = -3.39 → cheapest.
    expect(text[1]).toContain("Single-rate");
    expect(text[1]).toContain("−");
    expect(text[1]).toContain("3.39");
    expect(text[1]).toContain("5.7 %");
    expect(rows[1]!.classList.contains("best")).toBe(true);
    expect(rows[1]!.querySelector(".diff.cheaper")).not.toBeNull();
    // Three-zone: 58.50 → also cheaper, not the cheapest; zone names by key.
    expect(text[2]).toContain("Peak 2.0");
    expect(text[2]).toContain("Semi-peak 2.5");
    expect(rows[2]!.classList.contains("best")).toBe(false);
  });

  it("marks nothing on a tie and hides zones without hours", async () => {
    const doc = comparison();
    const single = doc.scenarios[0]!.report.totals.total;
    single.cost = "59.64"; // same as the current tariff
    const three = doc.scenarios[1]!.report.totals.total;
    three.cost = "59.64";
    three.zones[0]!.kwh = null;
    three.zones[0]!.cost = null;
    const { card } = await mount({ compare: COMPARE }, makeHass(async () => doc));
    expect(card.shadowRoot!.querySelectorAll("table.compare .badge.best")).toHaveLength(0);
    const zones = card.shadowRoot!.querySelectorAll("table.compare td.zones")[2]!.textContent;
    expect(zones).not.toContain("Peak");
    expect(zones).toContain("Night 3.0");
  });

  it("does not re-request the comparison when only the grouping changes", async () => {
    const { card, hass } = await mount({ compare: COMPARE, show_breakdown: true });
    const select = card.shadowRoot!.querySelector<HTMLSelectElement>("select.grouping")!;
    select.value = "week";
    select.dispatchEvent(new Event("change"));
    await settle(card);
    expect(compareCalls(hass)).toHaveLength(1);
    card.shadowRoot!.querySelector<HTMLButtonElement>("button.prev")!.click();
    await settle(card);
    expect(compareCalls(hass)).toHaveLength(2);
  });

  it("shows a scenario error from the backend", async () => {
    const hass = makeHass(async () => {
      throw { code: "invalid_scenario", message: "scenario 2: hours not covered: 7" };
    });
    const { card } = await mount({ compare: COMPARE }, hass);
    const error = card.shadowRoot!.querySelector("details.comparison .error")!.textContent;
    expect(error).toContain("scenario 2: hours not covered: 7");
  });

  it("warns when the current tariff does not cover the period", async () => {
    const doc = comparison();
    doc.actual.unpriced_hours = 5;
    const { card } = await mount({ compare: COMPARE }, makeHass(async () => doc));
    expect(card.shadowRoot!.querySelector("details.comparison")!.textContent).toContain(
      "does not cover the whole period",
    );
  });

  it("does not compare against an incomplete current tariff", async () => {
    const doc = comparison();
    doc.actual.unpriced_hours = 5;
    doc.actual.totals.total.cost = "10.00"; // only the priced hours: looks cheapest
    const { card } = await mount({ compare: COMPARE }, makeHass(async () => doc));
    const rows = [...card.shadowRoot!.querySelectorAll("table.compare tbody tr")];
    expect(rows[0]!.classList.contains("best")).toBe(false);
    // The cheapest scenario (single-rate 56.25 < three-zone 58.50) is still marked.
    expect(rows[1]!.classList.contains("best")).toBe(true);
    for (const row of rows.slice(1)) {
      expect(row.querySelector("td.diff")!.textContent!.trim()).toBe("—");
    }
  });

  it("names unnamed scenarios by their preset in the card's language", async () => {
    const hass = makeHass();
    hass.language = "ru";
    hass.locale = { language: "ru" };
    const { card } = await mount({ compare: [{ preset: "single_rate", prices: { t0: 7.5 } }] }, hass);
    const name = card.shadowRoot!.querySelectorAll("table.compare tbody th.name")[1]!.textContent;
    expect(name).toContain("Однозонный");
  });

  it("requests the new period's comparison even if the grouping changed meanwhile", async () => {
    // Reports resolve only when released; comparisons immediately.
    const pending: (() => void)[] = [];
    const calls: Msg[] = [];
    const hass: HassLike & { calls: Msg[] } = {
      calls,
      language: "en",
      locale: { language: "en" },
      config: { time_zone: "Europe/Moscow", currency: "RUB" },
      callWS: <T>(msg: Msg) => {
        calls.push(msg);
        if (msg.type === "energy_cost_stats/compare") return Promise.resolve(comparison()) as Promise<T>;
        return new Promise<T>((resolve) => pending.push(() => resolve(report() as T)));
      },
    };
    const card = document.createElement("energy-cost-stats-card") as EnergyCostStatsCard;
    card.setConfig({ type: "custom:energy-cost-stats-card", compare: COMPARE, show_breakdown: true });
    card.hass = hass;
    document.body.appendChild(card);
    await settle(card);
    pending.shift()!();
    await settle(card);
    expect(compareCalls(hass)).toHaveLength(1);
    expect(card.shadowRoot!.querySelectorAll("table.compare tbody tr")).toHaveLength(3);

    // New period, then a grouping change before its report arrives.
    card.shadowRoot!.querySelector<HTMLButtonElement>("button.prev")!.click();
    await settle(card);
    const select = card.shadowRoot!.querySelector<HTMLSelectElement>("select.grouping")!;
    select.value = "week";
    select.dispatchEvent(new Event("change"));
    await settle(card);
    while (pending.length) pending.shift()!();
    await settle(card);

    expect(compareCalls(hass)).toHaveLength(2);
    expect(compareCalls(hass)[1]).toMatchObject({ start: "2026-10-01", end: "2026-11-01" });
  });

  it("clears the previous period's comparison until the new one arrives", async () => {
    let releaseCompare: () => void = () => {};
    let compareCount = 0;
    const hass = makeHass(
      () =>
        new Promise((resolve) => {
          compareCount += 1;
          if (compareCount === 1) resolve(comparison());
          else releaseCompare = () => resolve(comparison());
        }),
    );
    const { card } = await mount({ compare: COMPARE }, hass);
    expect(card.shadowRoot!.querySelectorAll("table.compare tbody tr")).toHaveLength(3);
    card.shadowRoot!.querySelector<HTMLButtonElement>("button.prev")!.click();
    await settle(card);
    expect(card.shadowRoot!.querySelector("table.compare")).toBeNull();
    expect(card.shadowRoot!.querySelector("details.comparison")!.textContent).toContain("Loading");
    releaseCompare();
    await settle(card);
    expect(card.shadowRoot!.querySelectorAll("table.compare tbody tr")).toHaveLength(3);
  });

  it("uses the report request's end for the comparison", async () => {
    const { hass } = await mount({ compare: COMPARE });
    const reportCall = hass.calls.find((c) => c.type === "energy_cost_stats/report")!;
    expect(compareCalls(hass)[0]!.end).toBe(reportCall.end);
  });

  it("refresh re-requests the comparison", async () => {
    const { card, hass } = await mount({ compare: COMPARE });
    card.shadowRoot!.querySelector<HTMLButtonElement>("button.refresh")!.click();
    await settle(card);
    expect(compareCalls(hass)).toHaveLength(2);
  });

  it.each([
    [[], /1 to 5/],
    [[{ preset: "four_zone", prices: {} }], /preset/],
    [[{ preset: "single_rate" }], /prices/],
    ["single_rate", /1 to 5/],
  ])("rejects compare config %j", (compare, message) => {
    const card = document.createElement("energy-cost-stats-card") as EnergyCostStatsCard;
    expect(() => card.setConfig({ type: "x", compare: compare as never })).toThrow(message);
  });
});
