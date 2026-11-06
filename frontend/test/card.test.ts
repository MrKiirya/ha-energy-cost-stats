import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import "../src/index";
import type { EnergyCostStatsCard } from "../src/card";
import type { HassLike, ReportDocument } from "../src/report";
import { report, row } from "./fixtures";

type Msg = Record<string, unknown>;

function makeHass(
  respond: (msg: Msg) => Promise<unknown> = async () => report(),
  language = "en",
  timeZone = "Europe/Moscow",
): HassLike & { calls: Msg[] } {
  const calls: Msg[] = [];
  return {
    calls,
    language,
    locale: { language },
    config: { time_zone: timeZone, currency: "RUB" },
    callWS: <T>(msg: Msg) => {
      calls.push(msg);
      return respond(msg) as Promise<T>;
    },
  };
}

async function mount(
  config: Record<string, unknown> = {},
  hass = makeHass(),
): Promise<{ card: EnergyCostStatsCard; hass: ReturnType<typeof makeHass> }> {
  const card = document.createElement("energy-cost-stats-card") as EnergyCostStatsCard;
  card.setConfig({ type: "custom:energy-cost-stats-card", ...config });
  card.hass = hass;
  document.body.appendChild(card);
  await settle(card);
  return { card, hass };
}

async function settle(card: EnergyCostStatsCard): Promise<void> {
  for (let i = 0; i < 5; i++) {
    await card.updateComplete;
    await Promise.resolve();
    await new Promise((r) => setTimeout(r, 0));
  }
}

function q<T extends Element = HTMLElement>(card: EnergyCostStatsCard, selector: string): T {
  const el = card.shadowRoot!.querySelector<T>(selector);
  if (!el) throw new Error(`not found: ${selector}`);
  return el;
}

function text(card: EnergyCostStatsCard, selector = "ha-card"): string {
  return (q(card, selector).textContent ?? "").replace(/\s+/g, " ").trim();
}

async function click(card: EnergyCostStatsCard, selector: string): Promise<void> {
  q<HTMLButtonElement>(card, selector).click();
  await settle(card);
}

async function choose(card: EnergyCostStatsCard, selector: string, value: string): Promise<void> {
  const select = q<HTMLSelectElement>(card, selector);
  select.value = value;
  select.dispatchEvent(new Event("change"));
  await settle(card);
}

function last(hass: { calls: Msg[] }): Msg {
  return hass.calls[hass.calls.length - 1]!;
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  // Friday 2026-11-06.
  vi.setSystemTime(new Date("2026-11-06T12:00:00Z"));
});

afterEach(() => {
  vi.useRealTimers();
  document.body.innerHTML = "";
});

describe("config", () => {
  it("rejects an unknown period or grouping", () => {
    const card = document.createElement("energy-cost-stats-card") as EnergyCostStatsCard;
    expect(() => card.setConfig({ type: "x", period: "fortnight" as never })).toThrow(/period/);
    expect(() => card.setConfig({ type: "x", grouping: "minute" as never })).toThrow(/grouping/);
    expect(() => card.setConfig({ type: "x", entities: "sensor.a" as never })).toThrow(
      /entities/,
    );
  });

  it("has a stub config", async () => {
    const { EnergyCostStatsCard } = await import("../src/card");
    expect(EnergyCostStatsCard.getStubConfig()).toEqual({
      type: "custom:energy-cost-stats-card",
      period: "this_month",
    });
  });
});

describe("request", () => {
  it("loads this month by day by default, with an exclusive end", async () => {
    const { hass } = await mount();
    expect(hass.calls).toEqual([
      {
        type: "energy_cost_stats/report",
        start: "2026-11-01",
        // A period containing today ends at the current hour (Moscow, UTC+3).
        end: "2026-11-06T15:00:00+03:00",
        grouping: "day",
      },
    ]);
  });

  it("passes configured entities and the configured period", async () => {
    const { hass } = await mount({ entities: ["sensor.plug_02"], period: "today" });
    expect(last(hass)).toEqual({
      type: "energy_cost_stats/report",
      start: "2026-11-06",
      end: "2026-11-06T15:00:00+03:00",
      grouping: "hour",
      entities: ["sensor.plug_02"],
    });
  });

  it("uses the configured grouping when allowed", async () => {
    const { hass } = await mount({ grouping: "week", period: "this_year" });
    expect(last(hass)).toMatchObject({ grouping: "week", start: "2026-01-01" });
  });

  it("falls back to auto grouping when hours are too long for the period", async () => {
    const { hass } = await mount({ grouping: "hour", period: "this_quarter" });
    expect(last(hass)).toMatchObject({ grouping: "week" });
  });
});

describe("time zone", () => {
  it("asks again in the integration's time zone when it differs from HA's", async () => {
    const { hass } = await mount({}, makeHass(undefined, "en", "UTC"));
    expect(hass.calls.map((c) => c.end)).toEqual([
      "2026-11-06T12:00:00+00:00",
      "2026-11-06T15:00:00+03:00",
    ]);
  });

  it("does not ask again for a past period", async () => {
    const { hass } = await mount({ period: "last_month" }, makeHass(undefined, "en", "UTC"));
    expect(hass.calls).toHaveLength(1);
  });
});

describe("period picker", () => {
  it("arrows move a month by months; next is disabled on the current month", async () => {
    const { card, hass } = await mount();
    expect(q<HTMLButtonElement>(card, "button.next").disabled).toBe(true);
    expect(q<HTMLButtonElement>(card, "button.now").disabled).toBe(true);
    await click(card, "button.prev");
    expect(last(hass)).toMatchObject({ start: "2026-10-01", end: "2026-11-01" });
    await click(card, "button.prev");
    expect(last(hass)).toMatchObject({ start: "2026-09-01", end: "2026-10-01" });
    expect(q<HTMLButtonElement>(card, "button.next").disabled).toBe(false);
    await click(card, "button.next");
    expect(last(hass)).toMatchObject({ start: "2026-10-01", end: "2026-11-01" });
    await click(card, "button.now");
    expect(last(hass)).toMatchObject({ start: "2026-11-01", end: "2026-11-06T15:00:00+03:00" });
  });

  it("today moves by days and yesterday stays a day", async () => {
    const { card, hass } = await mount({ period: "today" });
    await click(card, "button.prev");
    expect(last(hass)).toMatchObject({ start: "2026-11-05", end: "2026-11-06", grouping: "hour" });
    expect(q<HTMLSelectElement>(card, "select.preset").value).toBe("yesterday");
    await click(card, "button.prev");
    expect(last(hass)).toMatchObject({ start: "2026-11-04", end: "2026-11-05" });
  });

  it("keeps the preset select in sync after a custom range", async () => {
    const { card } = await mount();
    await click(card, "button.prev");
    expect(q<HTMLSelectElement>(card, "select.preset").value).toBe("last_month");
    await click(card, "button.prev");
    expect(q<HTMLSelectElement>(card, "select.preset").value).toBe("");
    await click(card, "button.now");
    expect(q<HTMLSelectElement>(card, "select.preset").value).toBe("this_month");
  });

  it("presets switch the step: week moves by weeks", async () => {
    const { card, hass } = await mount();
    await choose(card, "select.preset", "this_week");
    expect(last(hass)).toMatchObject({ start: "2026-11-02", end: "2026-11-06T15:00:00+03:00" });
    await click(card, "button.prev");
    expect(last(hass)).toMatchObject({ start: "2026-10-26", end: "2026-11-02" });
    expect(q<HTMLSelectElement>(card, "select.preset").value).toBe("last_week");
  });

  it("quarter and year move by three and twelve months", async () => {
    const { card, hass } = await mount({ period: "this_quarter" });
    await click(card, "button.prev");
    expect(last(hass)).toMatchObject({ start: "2026-07-01", end: "2026-10-01" });
    await choose(card, "select.preset", "this_year");
    await click(card, "button.prev");
    expect(last(hass)).toMatchObject({ start: "2025-01-01", end: "2026-01-01" });
  });

  it("custom range is applied and then moves by its length", async () => {
    const { card, hass } = await mount();
    await choose(card, "select.preset", "custom");
    const start = q<HTMLInputElement>(card, "input.custom-start");
    const end = q<HTMLInputElement>(card, "input.custom-end");
    start.value = "2026-10-10";
    start.dispatchEvent(new Event("change"));
    end.value = "2026-10-19";
    end.dispatchEvent(new Event("change"));
    await settle(card);
    await click(card, "button.apply");
    expect(last(hass)).toMatchObject({ start: "2026-10-10", end: "2026-10-20", grouping: "day" });
    expect(q<HTMLSelectElement>(card, "select.preset").value).toBe("");
    await click(card, "button.prev");
    expect(last(hass)).toMatchObject({ start: "2026-09-30", end: "2026-10-10" });
  });

  it("custom range with swapped dates is put in order", async () => {
    const { card, hass } = await mount();
    await click(card, "button.label");
    const start = q<HTMLInputElement>(card, "input.custom-start");
    const end = q<HTMLInputElement>(card, "input.custom-end");
    start.value = "2026-10-19";
    start.dispatchEvent(new Event("change"));
    end.value = "2026-10-10";
    end.dispatchEvent(new Event("change"));
    await settle(card);
    await click(card, "button.apply");
    expect(last(hass)).toMatchObject({ start: "2026-10-10", end: "2026-10-20" });
  });

  it("refresh re-requests the same period", async () => {
    const { card, hass } = await mount();
    await click(card, "button.refresh");
    expect(hass.calls).toHaveLength(2);
    expect(hass.calls[1]).toEqual(hass.calls[0]);
  });
});

describe("table", () => {
  it("renders devices, zones and the total row", async () => {
    const { card } = await mount();
    const header = text(card, "table.devices thead");
    expect(header).toContain("Day");
    expect(header).toContain("Night");
    const rows = card.shadowRoot!.querySelectorAll("table.devices tbody tr");
    expect(rows).toHaveLength(2);
    expect(rows[0]!.textContent).toContain("Plug 01");
    expect(rows[0]!.textContent).toContain("30.90");
    const footer = text(card, "table.devices tfoot");
    expect(footer).toContain("Total");
    expect(footer).toContain("59.64");
    // Estimated rows carry a badge.
    expect(rows[1]!.querySelector(".badge.estimated")).not.toBeNull();
  });

  it("shows null cells as a dash, never as zero", async () => {
    const doc = report();
    doc.totals.rows[1] = row("sensor.plug_02", ["1.500", "15.45"], [null, null]);
    const { card } = await mount({}, makeHass(async () => doc));
    const cells = card.shadowRoot!.querySelectorAll("table.devices tbody tr")[1]!.querySelectorAll(
      "td",
    );
    expect(cells[2]!.textContent!.trim()).toBe("—");
    expect(cells[3]!.textContent!.trim()).toBe("—");
  });

  it("speaks Russian", async () => {
    const { card } = await mount({}, makeHass(undefined, "ru"));
    expect(text(card)).toContain("Итого");
    expect(text(card)).toContain("Стоимость электроэнергии");
    expect(q<HTMLButtonElement>(card, "button.label").textContent).toContain("2026");
  });

  it("breakdown lists buckets and can show a single device", async () => {
    const { card } = await mount({ show_breakdown: true });
    const bucketRows = () => card.shadowRoot!.querySelectorAll("table.buckets tbody tr");
    expect(bucketRows()).toHaveLength(2);
    expect(bucketRows()[1]!.textContent).toContain("35.33");
    await choose(card, "select.breakdown-device", "sensor.plug_02");
    expect(bucketRows()[1]!.textContent).toContain("14.73");
  });

  it("shows auto when the chosen grouping is not allowed for the period", async () => {
    const { card, hass } = await mount({
      show_breakdown: true,
      grouping: "hour",
      period: "this_quarter",
    });
    expect(last(hass)).toMatchObject({ grouping: "week" });
    expect(q<HTMLSelectElement>(card, "select.grouping").value).toBe("auto");
  });

  it("labels week buckets with the whole calendar week", async () => {
    const doc = report({ grouping: "week" });
    doc.buckets[1]!.start = "2026-11-02T00:00:00+03:00";
    doc.buckets[1]!.end = "2026-11-06T15:00:00+03:00";
    const { card } = await mount({ show_breakdown: true }, makeHass(async () => doc));
    const label = card.shadowRoot!.querySelectorAll("table.buckets tbody tr th")[1]!.textContent;
    expect(label).toContain("2");
    expect(label).toContain("8");
  });

  it("changing the grouping re-requests", async () => {
    const { card, hass } = await mount({ show_breakdown: true });
    await choose(card, "select.grouping", "week");
    expect(last(hass)).toMatchObject({ grouping: "week" });
  });

  it("warns when no tariff plan covers the period", async () => {
    const { card } = await mount({}, makeHass(async () => report({ plans: [] })));
    expect(text(card)).toContain("No tariff plan");
  });

  it("warns about unpriced hours", async () => {
    const { card } = await mount({}, makeHass(async () => report({ unpriced_hours: 12 })));
    expect(text(card)).toContain("12 h before the first tariff plan");
  });

  it("lists data quality issues", async () => {
    const { card } = await mount();
    expect(text(card, "details.issues")).toContain("Plug 02");
    expect(text(card, "details.issues")).toContain("estimated");
  });

  it("explains an empty sensor list", async () => {
    const empty = report({ devices: [] });
    empty.totals.rows = [];
    const { card } = await mount({}, makeHass(async () => empty));
    expect(text(card)).toContain("No energy sensors selected");
  });
});

describe("errors and races", () => {
  it("shows a translated websocket error", async () => {
    const hass = makeHass(async () => {
      throw { code: "not_loaded", message: "No loaded entry" };
    });
    const { card } = await mount({}, hass);
    expect(text(card, ".error")).toContain("not set up or not loaded");
  });

  it("shows the message of an unknown error", async () => {
    const hass = makeHass(async () => {
      throw { code: "home_assistant_error", message: "boom" };
    });
    const { card } = await mount({}, hass);
    expect(text(card, ".error")).toContain("boom");
  });

  it("ignores a stale response that arrives after a newer one", async () => {
    let resolveFirst: (doc: ReportDocument) => void = () => {};
    let call = 0;
    const hass = makeHass(
      (msg) =>
        new Promise((resolve) => {
          call += 1;
          if (call === 1) {
            resolveFirst = resolve as (doc: ReportDocument) => void;
          } else {
            const doc = report();
            doc.devices[0]!.name = `Newer ${String(msg.start)}`;
            resolve(doc);
          }
        }),
    );
    const { card } = await mount({}, hass);
    await click(card, "button.prev");
    resolveFirst(report());
    await settle(card);
    expect(text(card)).toContain("Newer 2026-10-01");
  });
});
