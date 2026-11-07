import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import "../src/index";
import { EnergyCostStatsCard } from "../src/card";
import type { CompareDocument, HassLike, ReportDocument } from "../src/report";
import { compareDoc, report, row, totalDoc } from "./fixtures";

type Msg = Record<string, unknown>;

const REPORT = "energy_cost_stats/report";
const COMPARE = "energy_cost_stats/compare";

/** `respond` answers report calls, `respondCompare` the compare calls. */
function makeHass(
  respond: (msg: Msg) => Promise<unknown> = async () => report(),
  language = "en",
  timeZone = "Europe/Moscow",
  respondCompare: (msg: Msg) => Promise<unknown> = async () => compareDoc(),
): HassLike & { calls: Msg[] } {
  const calls: Msg[] = [];
  return {
    calls,
    language,
    locale: { language },
    config: { time_zone: timeZone, currency: "RUB" },
    callWS: <T>(msg: Msg) => {
      calls.push(msg);
      return (msg.type === COMPARE ? respondCompare(msg) : respond(msg)) as Promise<T>;
    },
  };
}

function callsOf(hass: { calls: Msg[] }, type: string): Msg[] {
  return hass.calls.filter((c) => c.type === type);
}

function lastOf(hass: { calls: Msg[] }, type: string): Msg {
  const found = callsOf(hass, type);
  return found[found.length - 1]!;
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
  return lastOf(hass, REPORT);
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  // Friday 2026-11-06.
  vi.setSystemTime(new Date("2026-11-06T12:00:00Z"));
  localStorage.clear();
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
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

describe("title", () => {
  it("an empty title hides the title text", async () => {
    const { card } = await mount({ title: "" });
    expect(card.shadowRoot!.querySelector(".title")).toBeNull();
    expect(card.shadowRoot!.querySelector(".picker")).not.toBeNull();
    const { card: plain } = await mount();
    expect(text(plain, ".title")).toBe("Energy cost");
  });
});

describe("request", () => {
  it("loads this month by day by default, with an exclusive end", async () => {
    const { hass } = await mount();
    expect(callsOf(hass, REPORT)).toEqual([
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
    expect(callsOf(hass, REPORT).map((c) => c.end)).toEqual([
      "2026-11-06T12:00:00+00:00",
      "2026-11-06T15:00:00+03:00",
    ]);
  });

  it("does not ask again for a past period", async () => {
    const { hass } = await mount({ period: "last_month" }, makeHass(undefined, "en", "UTC"));
    expect(callsOf(hass, REPORT)).toHaveLength(1);
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
    const reports = callsOf(hass, REPORT);
    expect(reports).toHaveLength(2);
    expect(reports[1]).toEqual(reports[0]);
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

function bodyRows(card: EnergyCostStatsCard, table = "table.devices"): HTMLTableRowElement[] {
  return [...card.shadowRoot!.querySelectorAll<HTMLTableRowElement>(`${table} tbody tr`)];
}

function compareRows(card: EnergyCostStatsCard): string[][] {
  return [...card.shadowRoot!.querySelectorAll("table.comparison tbody tr")].map((tr) =>
    [...tr.querySelectorAll("th, td")].map((c) => (c.textContent ?? "").replace(/\s+/g, " ").trim()),
  );
}

describe("comparison", () => {
  it("requests compare with the same period and entities", async () => {
    const { hass } = await mount({ entities: ["sensor.plug_01", "sensor.plug_02"] });
    const compare = lastOf(hass, COMPARE);
    const rep = lastOf(hass, REPORT);
    expect(compare.start).toBe(rep.start);
    expect(compare.end).toBe(rep.end);
    expect(compare.entities).toEqual(["sensor.plug_01", "sensor.plug_02"]);
    expect(compare).not.toHaveProperty("tariffs");
    expect(compare).not.toHaveProperty("grouping");
  });

  it("grouping change does not re-request compare", async () => {
    const { card, hass } = await mount({ show_breakdown: true });
    expect(callsOf(hass, COMPARE)).toHaveLength(1);
    await choose(card, "select.grouping", "week");
    expect(callsOf(hass, REPORT)).toHaveLength(2);
    expect(callsOf(hass, COMPARE)).toHaveLength(1);
    await click(card, "button.refresh");
    expect(callsOf(hass, REPORT)).toHaveLength(3);
    expect(callsOf(hass, COMPARE)).toHaveLength(2);
    await click(card, "button.prev");
    expect(callsOf(hass, REPORT)).toHaveLength(4);
    expect(callsOf(hass, COMPARE)).toHaveLength(3);
    expect(lastOf(hass, COMPARE).start).toBe("2026-10-01");
  });

  it("shows actual and each compared tariff with the difference", async () => {
    const { card } = await mount();
    const rows = compareRows(card);
    expect(rows).toHaveLength(3);
    expect(rows[0]![0]).toContain("Actual");
    expect(rows[0]![0]).toContain("Two-zone");
    expect(rows[0]![1]).toContain("100.00");
    expect(rows[1]![0]).toContain("Three-zone");
    expect(rows[1]![1]).toContain("112.50");
    expect(rows[1]![2]).toContain("+");
    expect(rows[1]![2]).toContain("12.50");
    expect(rows[1]![3]).toBe("+12.5 %");
    expect(rows[2]![0]).toContain("Flat");
    expect(rows[2]![2]).toMatch(/^[-−]\D*10\.00$/);
    expect(rows[2]![3]).toMatch(/^[-−]10\.0 %$/);
    // Average price = cost / kWh.
    expect(rows[1]![4]).toContain("2.25");
  });

  it("joins several plan names of the actual schedule", async () => {
    const actual = totalDoc("100.00", "50.000", {
      plans: [
        { valid_from: "2026-01-01", name: "Old" },
        { valid_from: "2026-06-01", name: "New" },
      ],
    });
    const { card } = await mount({}, makeHass(undefined, "en", "Europe/Moscow", async () => compareDoc({ actual })));
    expect(compareRows(card)[0]![0]).toContain("Old → New");
  });

  it("null cost gives a dash difference", async () => {
    const doc = compareDoc({
      actual: totalDoc("0.00"),
      tariffs: [
        { id: "a", name: "Unknown", report: totalDoc(null) },
        { id: "b", name: "Dearer", report: totalDoc("5.00") },
      ],
    });
    const { card } = await mount({}, makeHass(undefined, "en", "Europe/Moscow", async () => doc));
    const rows = compareRows(card);
    expect(rows[1]![1]).toBe("—");
    expect(rows[1]![2]).toBe("—");
    expect(rows[1]![3]).toBe("—");
    expect(rows[2]![2]).toContain("5.00");
    expect(rows[2]![3]).toBe("—");
  });

  it("shows a dash for a missing actual cost (no plan)", async () => {
    const doc = compareDoc({ actual: totalDoc(null, "50.000", { plans: [] }) });
    const { card } = await mount({}, makeHass(undefined, "en", "Europe/Moscow", async () => doc));
    const rows = compareRows(card);
    expect(rows[0]![1]).toBe("—");
    expect(rows[1]![1]).toContain("112.50");
    expect(rows[1]![2]).toBe("—");
  });

  it("warns when a tariff leaves hours unpriced", async () => {
    const doc = compareDoc();
    doc.tariffs[0]!.report.unpriced_hours = 36;
    const { card } = await mount({}, makeHass(undefined, "en", "Europe/Moscow", async () => doc));
    const badges = card.shadowRoot!.querySelectorAll("table.comparison .badge");
    expect(badges).toHaveLength(1);
    expect(badges[0]!.getAttribute("title")).toBe(
      "36 h not priced by this tariff — the difference covers only the priced hours",
    );
  });

  it("empty list shows the hint", async () => {
    const { card } = await mount(
      {},
      makeHass(undefined, "en", "Europe/Moscow", async () => compareDoc({ tariffs: [] })),
    );
    expect(text(card, ".comparison")).toContain("No tariffs to compare");
    expect(card.shadowRoot!.querySelector("table.comparison")).toBeNull();
  });

  it("older integration hides the section", async () => {
    const hass = makeHass(undefined, "en", "Europe/Moscow", async () => {
      throw { code: "unknown_command", message: "Unknown command." };
    });
    const { card } = await mount({}, hass);
    expect(card.shadowRoot!.querySelector(".comparison")).toBeNull();
    expect(card.shadowRoot!.querySelector(".error")).toBeNull();
    expect(bodyRows(card)).toHaveLength(2);
  });

  it("a compare error does not hide the table", async () => {
    const hass = makeHass(undefined, "en", "Europe/Moscow", async () => {
      throw { code: "home_assistant_error", message: "boom" };
    });
    const { card } = await mount({}, hass);
    expect(text(card, ".comparison .error")).toContain("boom");
    expect(bodyRows(card)).toHaveLength(2);
  });

  it("stale compare response is dropped", async () => {
    let resolveFirst: (doc: CompareDocument) => void = () => {};
    let call = 0;
    const hass = makeHass(undefined, "en", "Europe/Moscow", () =>
      new Promise((resolve) => {
        call += 1;
        if (call === 1) resolveFirst = resolve as (doc: CompareDocument) => void;
        else resolve(compareDoc({ tariffs: [{ id: "n", name: "Newer", report: totalDoc("1.00") }] }));
      }),
    );
    const { card } = await mount({}, hass);
    await click(card, "button.prev");
    resolveFirst(compareDoc());
    await settle(card);
    expect(text(card, ".comparison")).toContain("Newer");
    expect(text(card, ".comparison")).not.toContain("Three-zone");
  });

  it("marks the comparison as loading while a slower compare is pending", async () => {
    let resolveSecond: (doc: CompareDocument) => void = () => {};
    let call = 0;
    const hass = makeHass(undefined, "en", "Europe/Moscow", () =>
      call++ === 0
        ? Promise.resolve(compareDoc())
        : new Promise((resolve) => {
            resolveSecond = resolve as (doc: CompareDocument) => void;
          }),
    );
    const { card } = await mount({}, hass);
    expect(card.shadowRoot!.querySelector("section.comparison.loading")).toBeNull();
    await click(card, "button.prev");
    // The report is done, the comparison is still the previous period's.
    expect(card.shadowRoot!.querySelector(".header .loading")).toBeNull();
    const section = q(card, "section.comparison");
    expect(section.classList.contains("loading")).toBe(true);
    expect(section.getAttribute("aria-busy")).toBe("true");
    expect(text(card, "section.comparison .loading")).toContain("Loading");
    resolveSecond(
      compareDoc({ tariffs: [{ id: "n", name: "Newer", report: totalDoc("1.00") }] }),
    );
    await settle(card);
    expect(card.shadowRoot!.querySelector("section.comparison.loading")).toBeNull();
    expect(text(card, "section.comparison")).toContain("Newer");
  });

  it("re-sends compare on the time zone retry", async () => {
    const { hass } = await mount({}, makeHass(undefined, "en", "UTC"));
    expect(callsOf(hass, COMPARE).map((c) => c.end)).toEqual([
      "2026-11-06T12:00:00+00:00",
      "2026-11-06T15:00:00+03:00",
    ]);
  });

  it("re-sends report and compare on the running-period timer", async () => {
    vi.useFakeTimers({ toFake: ["Date", "setInterval", "clearInterval"] });
    vi.setSystemTime(new Date("2026-11-06T12:00:00Z"));
    const { hass } = await mount();
    expect(callsOf(hass, COMPARE)).toHaveLength(1);
    await vi.advanceTimersByTimeAsync(10 * 60 * 1000);
    await settle(hass as never);
    expect(callsOf(hass, REPORT)).toHaveLength(2);
    expect(callsOf(hass, COMPARE)).toHaveLength(2);
  });

  it("translates an unknown tariff error", async () => {
    const hass = makeHass(undefined, "en", "Europe/Moscow", async () => {
      throw { code: "unknown_tariff", message: "raw" };
    });
    const { card } = await mount({}, hass);
    expect(text(card, ".comparison .error")).toContain("not defined");
    expect(text(card, ".comparison .error")).not.toContain("raw");
  });

  it("labels the first column with a short heading", async () => {
    const { card } = await mount();
    expect(text(card, "table.comparison thead th.name")).toBe("Tariff");
  });

  it("explains actual-side unpriced hours separately", async () => {
    const doc = compareDoc({ actual: totalDoc("100.00", "50.000", { unpriced_hours: 5 }) });
    const { card } = await mount({}, makeHass(undefined, "en", "Europe/Moscow", async () => doc));
    const titles = [...card.shadowRoot!.querySelectorAll("table.comparison .badge")].map((b) =>
      b.getAttribute("title"),
    );
    // Every compared row inherits the actual schedule's gap.
    expect(titles).toHaveLength(2);
    for (const title of titles) {
      expect(title).toContain("5 h");
      expect(title).toContain("actual");
    }
  });

  it("speaks Russian", async () => {
    const { card } = await mount({}, makeHass(undefined, "ru"));
    expect(text(card, ".comparison")).toContain("Сравнение тарифов");
    expect(text(card, ".comparison")).toContain("Фактически");
  });

  it("does not add a compare option to the config", async () => {
    const card = document.createElement("energy-cost-stats-card") as EnergyCostStatsCard;
    // Unknown keys are ignored, not interpreted.
    expect(() => card.setConfig({ type: "x", compare: ["a"] } as never)).not.toThrow();
  });
});

describe("layout", () => {
  it("asks for the full width in sections views", async () => {
    const { card } = await mount();
    expect(card.getGridOptions()).toEqual({ columns: "full", min_columns: 6 });
    expect(card.getGridOptions()).not.toHaveProperty("rows");
  });

  it("zone groups start with a separator cell", async () => {
    const { card } = await mount();
    const head = card.shadowRoot!.querySelectorAll("table.devices thead tr");
    const zones = head[0]!.querySelectorAll("th.zone");
    expect(zones).toHaveLength(3);
    for (const th of zones) expect(th.classList.contains("group-start")).toBe(true);
    expect(zones[0]!.getAttribute("colspan")).toBe("2");
    expect(zones[1]!.getAttribute("colspan")).toBe("2");
    expect(head[1]!.querySelectorAll("th.group-start")).toHaveLength(3);
    expect(zones[2]!.getAttribute("colspan")).toBe("2");
    const avg = head[0]!.querySelector("th.avg")!;
    expect(avg.getAttribute("rowspan")).toBe("2");
    expect(avg.classList.contains("group-start")).toBe(true);
    expect(avg.previousElementSibling).toBe(zones[2]);
    for (const tr of [...bodyRows(card), card.shadowRoot!.querySelector("table.devices tfoot tr")!]) {
      const cells = [...tr.querySelectorAll("td")];
      // kWh, cost | kWh, cost | kWh, cost | avg. price
      expect(cells.map((c) => c.classList.contains("group-start"))).toEqual([
        true, false, true, false, true, false, true,
      ]);
    }
  });

  it("name cells carry the full name as title", async () => {
    const { card } = await mount();
    const titles = bodyRows(card).map((tr) => tr.querySelector("th.name")!.getAttribute("title"));
    expect(titles).toEqual(["Plug 01", "Plug 02"]);
  });
});

describe("nested devices", () => {
  function nestedReport(): ReportDocument {
    const doc = report();
    doc.devices = [
      { entity_id: "sensor.child", name: "Child", statistics: "ok", upstream: "sensor.parent" },
      { entity_id: "sensor.other", name: "Other", statistics: "ok", upstream: null },
      { entity_id: "sensor.parent", name: "Parent", statistics: "ok", upstream: null },
    ];
    doc.totals.rows = [
      row("sensor.child", ["1.000", "10.30"], ["0.000", "0.00"]),
      row("sensor.other", ["1.000", "10.30"], ["0.000", "0.00"]),
      row("sensor.parent", ["2.000", "20.60"], ["0.000", "0.00"]),
    ];
    return doc;
  }

  it("nested rows follow their upstream, indented, with a note", async () => {
    // Name order: roots A→Z, the child directly under its upstream.
    const { card } = await mount({ sort: "name" }, makeHass(async () => nestedReport()));
    const rows = bodyRows(card);
    const names = rows.map((tr) => tr.querySelector("th.name")!.textContent!.replace(/\s+/g, " ").trim());
    expect(names[0]).toBe("Other");
    expect(names[1]).toBe("Parent");
    expect(names[2]).toContain("Child");
    expect(names[2]).toContain("↳");
    expect(rows[2]!.classList.contains("nested")).toBe(true);
    expect(rows[1]!.classList.contains("nested")).toBe(false);
    const th = rows[2]!.querySelector("th.name")!;
    expect(th.getAttribute("style")).toContain("--depth: 1");
    expect(th.getAttribute("title")).toBe(
      "Child — Measured inside Parent; not counted again in the total",
    );
    expect(text(card, ".nested-note")).toContain("Indented rows are measured inside");
  });

  it("breakdown device list keeps the report order", async () => {
    const { card } = await mount({ show_breakdown: true }, makeHass(async () => nestedReport()));
    const options = [...card.shadowRoot!.querySelectorAll<HTMLOptionElement>("select.breakdown-device option")];
    expect(options.map((o) => o.value)).toEqual(["", "sensor.child", "sensor.other", "sensor.parent"]);
  });

  it("has no note without any upstream", async () => {
    const { card } = await mount();
    expect(card.shadowRoot!.querySelector(".nested-note")).toBeNull();
    expect(card.shadowRoot!.querySelector("tr.nested")).toBeNull();
  });
});

describe("hass updates", () => {
  function entityOnly(hass: ReturnType<typeof makeHass>, n: number): ReturnType<typeof makeHass> {
    return { ...hass, states: { "sensor.clock": { state: String(n) } } } as never;
  }

  it("an entity-state-only hass update does not re-render", async () => {
    const { card, hass } = await mount();
    const before = hass.calls.length;
    const spy = vi.spyOn(card as never, "render");
    const next = entityOnly(hass, 1);
    card.hass = next;
    await settle(card);
    expect(spy).not.toHaveBeenCalled();
    expect(hass.calls).toHaveLength(before);
    expect(card.hass).toBe(next);
  });

  it("an entity-state-only hass update leaves the DOM untouched", async () => {
    const { card, hass } = await mount({ show_breakdown: true });
    const mutations: MutationRecord[] = [];
    const observer = new MutationObserver((m) => mutations.push(...m));
    observer.observe(card.shadowRoot!, { subtree: true, childList: true, attributes: true, characterData: true });
    const cardSize = card.getCardSize();
    const same = card.shadowRoot!.querySelector("ha-card");
    card.hass = entityOnly(hass, 1);
    await settle(card);
    observer.disconnect();
    expect(mutations).toEqual([]);
    expect(card.shadowRoot!.querySelector("ha-card")).toBe(same);
    expect(card.getCardSize()).toBe(cardSize);
  });

  it("the card element is not re-attached by hass updates", async () => {
    const { card, hass } = await mount();
    const connected = vi.spyOn(card, "connectedCallback");
    const disconnected = vi.spyOn(card, "disconnectedCallback");
    for (let i = 0; i < 3; i++) card.hass = entityOnly(hass, i);
    await settle(card);
    expect(connected).not.toHaveBeenCalled();
    expect(disconnected).not.toHaveBeenCalled();
  });

  it("the card size does not change while loading", async () => {
    const { card } = await mount();
    const size = card.getCardSize();
    const pending = new Promise<never>(() => {});
    card.hass = { ...makeHass(() => pending), language: "ru", locale: { language: "ru" } };
    await click(card, "button.refresh");
    expect(card.shadowRoot!.querySelector(".loading")).not.toBeNull();
    expect(card.getCardSize()).toBe(size);
  });

  it("a language change re-renders", async () => {
    const { card, hass } = await mount();
    card.hass = { ...hass, language: "ru", locale: { language: "ru" } };
    await settle(card);
    expect(text(card)).toContain("Итого");
  });

  it("a time zone change triggers an update", async () => {
    const { card, hass } = await mount();
    const spy = vi.spyOn(card as never, "render");
    card.hass = { ...hass, config: { time_zone: "Europe/Berlin" } };
    await settle(card);
    expect(spy).toHaveBeenCalled();
  });

  it("an open select keeps its node and value across hass updates", async () => {
    const { card, hass } = await mount({ show_breakdown: true });
    await choose(card, "select.grouping", "week");
    const select = q<HTMLSelectElement>(card, "select.grouping");
    for (let i = 0; i < 3; i++) {
      card.hass = entityOnly(hass, i);
      await settle(card);
    }
    expect(q<HTMLSelectElement>(card, "select.grouping")).toBe(select);
    expect(select.value).toBe("week");
  });
});

describe("sorting", () => {
  function sortReport(): ReportDocument {
    const doc = report();
    doc.devices = [
      { entity_id: "sensor.p1", name: "Delta", statistics: "ok", upstream: null },
      { entity_id: "sensor.p2", name: "Alpha", statistics: "ok", upstream: null },
      { entity_id: "sensor.p3", name: "Charlie", statistics: "ok", upstream: null },
      { entity_id: "sensor.p4", name: "Bravo", statistics: "ok", upstream: null },
    ];
    doc.totals.rows = [
      row("sensor.p1", ["10.000", "10.00"], ["1.000", "1.00"]),
      row("sensor.p2", ["1.000", "1.00"], ["1.000", "20.00"]),
      row("sensor.p3", ["1.000", null], ["1.000", null]),
      row("sensor.p4", ["4.000", "5.00"], ["1.000", "5.00"]),
    ];
    return doc;
  }
  const mountSorted = (config: Record<string, unknown> = {}, doc = sortReport()) =>
    mount(config, makeHass(async () => doc));
  const names = (card: EnergyCostStatsCard) =>
    bodyRows(card).map((tr) => tr.querySelector("th.name span")!.textContent!.replace(/[↳\s]+/g, " ").trim());
  const btn = (key: string) => `table.devices thead button.sort[data-sort="${key}"]`;
  const th = (card: EnergyCostStatsCard, key: string) => q(card, btn(key)).closest("th")!;
  const ariaSorted = (card: EnergyCostStatsCard) =>
    [...card.shadowRoot!.querySelectorAll("table.devices thead th[aria-sort]")].map(
      (el) => el.getAttribute("aria-sort"),
    );

  it("defaults to total cost descending, unpriced last", async () => {
    const { card } = await mountSorted();
    expect(names(card)).toEqual(["Alpha", "Delta", "Bravo", "Charlie"]);
    expect(th(card, "total").getAttribute("aria-sort")).toBe("descending");
    expect(th(card, "total").textContent).toContain("▼");
    expect(ariaSorted(card)).toEqual(["descending"]);
    expect(card.shadowRoot!.querySelectorAll(".sort-indicator")).toHaveLength(1);
    const last = card.shadowRoot!.querySelector("table.devices tfoot tr")!;
    expect(last.textContent).toContain("Total");
  });

  it("has all sort buttons in the top row and none in the second", async () => {
    const { card } = await mountSorted();
    const rows = card.shadowRoot!.querySelectorAll("table.devices thead tr");
    expect([...rows[0]!.querySelectorAll("button.sort")].map((b) => b.getAttribute("data-sort"))).toEqual(
      ["name", "t1", "t2", "total", "avg_price"],
    );
    expect(rows[1]!.querySelectorAll("button")).toHaveLength(0);
    expect(th(card, "name").getAttribute("rowspan")).toBe("2");
    expect(th(card, "avg_price").getAttribute("rowspan")).toBe("2");
    expect(th(card, "total").getAttribute("colspan")).toBe("2");
    expect(th(card, "avg_price").previousElementSibling).toBe(th(card, "total"));
    const css = EnergyCostStatsCard.styles.toString();
    expect(css).toMatch(/thead tr:first-child th\s*{[^}]*vertical-align: top/);
  });

  it("sorts by a zone and toggles, without a new request", async () => {
    const { card, hass } = await mountSorted();
    const before = hass.calls.length;
    await click(card, btn("t2"));
    expect(names(card)).toEqual(["Alpha", "Bravo", "Delta", "Charlie"]);
    expect(th(card, "t2").getAttribute("aria-sort")).toBe("descending");
    expect(th(card, "t2").textContent).toContain("▼");
    await click(card, btn("t2"));
    expect(names(card)).toEqual(["Delta", "Bravo", "Alpha", "Charlie"]);
    expect(th(card, "t2").getAttribute("aria-sort")).toBe("ascending");
    expect(th(card, "t2").textContent).toContain("▲");
    expect(ariaSorted(card)).toEqual(["ascending"]);
    expect(hass.calls.length).toBe(before);
  });

  it("sorts by average price", async () => {
    const { card } = await mountSorted();
    await click(card, btn("avg_price"));
    expect(names(card)).toEqual(["Alpha", "Bravo", "Delta", "Charlie"]);
    await click(card, btn("avg_price"));
    expect(names(card)).toEqual(["Delta", "Bravo", "Alpha", "Charlie"]);
    expect(th(card, "avg_price").getAttribute("aria-sort")).toBe("ascending");
  });

  it("sorts names ascending first, then descending", async () => {
    const { card } = await mountSorted();
    await click(card, btn("name"));
    expect(names(card)).toEqual(["Alpha", "Bravo", "Charlie", "Delta"]);
    expect(th(card, "name").getAttribute("aria-sort")).toBe("ascending");
    await click(card, btn("name"));
    expect(names(card)).toEqual(["Delta", "Charlie", "Bravo", "Alpha"]);
  });

  it("keeps nested devices under their upstream", async () => {
    const doc = report();
    doc.devices = [
      { entity_id: "sensor.parent", name: "Parent", statistics: "ok", upstream: null },
      { entity_id: "sensor.child", name: "Child", statistics: "ok", upstream: "sensor.parent" },
      { entity_id: "sensor.other", name: "Other", statistics: "ok", upstream: null },
    ];
    doc.totals.rows = [
      row("sensor.parent", ["1.000", "5.00"], ["0.000", "0.00"]),
      row("sensor.child", ["1.000", "50.00"], ["0.000", "0.00"]),
      row("sensor.other", ["1.000", "10.00"], ["0.000", "0.00"]),
    ];
    const { card } = await mountSorted({}, doc);
    expect(names(card)).toEqual(["Other", "Parent", "Child"]);
    expect(bodyRows(card)[2]!.classList.contains("nested")).toBe(true);
    await click(card, btn("total"));
    expect(names(card)).toEqual(["Parent", "Child", "Other"]);
  });

  it("applies the YAML default", async () => {
    let { card } = await mountSorted({ sort: "name" });
    expect(names(card)).toEqual(["Alpha", "Bravo", "Charlie", "Delta"]);
    document.body.innerHTML = "";
    ({ card } = await mountSorted({ sort: "t1", sort_direction: "asc" }));
    expect(names(card)).toEqual(["Alpha", "Bravo", "Delta", "Charlie"]);
    document.body.innerHTML = "";
    ({ card } = await mountSorted({ sort: "t9" }));
    expect(names(card)).toEqual(["Alpha", "Delta", "Bravo", "Charlie"]);
    expect(card.shadowRoot!.querySelector(".error")).toBeNull();
  });

  it("rejects invalid sort options", () => {
    const card = document.createElement("energy-cost-stats-card") as EnergyCostStatsCard;
    expect(() => card.setConfig({ type: "x", sort: "" })).toThrow();
    expect(() => card.setConfig({ type: "x", sort: 3 } as never)).toThrow();
    expect(() => card.setConfig({ type: "x", sort_direction: "down" } as never)).toThrow();
  });

  it("remembers the click per card configuration", async () => {
    const { card } = await mountSorted();
    await click(card, btn("name"));
    document.body.innerHTML = "";
    const again = await mountSorted();
    expect(names(again.card)).toEqual(["Alpha", "Bravo", "Charlie", "Delta"]);
    document.body.innerHTML = "";
    const other = await mountSorted({ sort: "t1" });
    expect(names(other.card)).toEqual(["Delta", "Bravo", "Alpha", "Charlie"]);
  });

  it("works without localStorage", async () => {
    const boom = () => {
      throw new Error("denied");
    };
    vi.stubGlobal("localStorage", { getItem: boom, setItem: boom, removeItem: boom });
    const { card } = await mountSorted();
    await click(card, btn("name"));
    expect(names(card)).toEqual(["Alpha", "Bravo", "Charlie", "Delta"]);
    expect(card.shadowRoot!.querySelector(".error")).toBeNull();
  });

  it("only the device table is sortable", async () => {
    const { card } = await mountSorted({ show_breakdown: true });
    expect(card.shadowRoot!.querySelector("table.buckets")).not.toBeNull();
    expect(card.shadowRoot!.querySelector("table.comparison")).not.toBeNull();
    expect(card.shadowRoot!.querySelectorAll("table.devices button.sort").length).toBeGreaterThan(0);
    expect(card.shadowRoot!.querySelectorAll("table.buckets button.sort")).toHaveLength(0);
    expect(card.shadowRoot!.querySelectorAll("table.comparison button.sort")).toHaveLength(0);
    expect(card.shadowRoot!.querySelectorAll("table.buckets thead [aria-sort]")).toHaveLength(0);
  });

  it("speaks Russian", async () => {
    const { card } = await mount({}, makeHass(async () => sortReport(), "ru"));
    expect(q(card, btn("t1")).getAttribute("title")).toBe(
      "Сортировать по: стоимость Day, по убыванию",
    );
    expect(q(card, btn("name")).getAttribute("title")).toContain("по возрастанию");
  });

  it("describes what a click does in English", async () => {
    const { card } = await mountSorted();
    expect(q(card, btn("t1")).getAttribute("title")).toBe("Sort by Day cost, descending");
    expect(q(card, btn("total")).getAttribute("title")).toBe("Sort by total cost, ascending");
  });
});

describe("sticky", () => {
  it("wraps the period controls, not the title", async () => {
    const { card } = await mount();
    const controls = q(card, ".controls");
    expect(controls.querySelector(".picker")).not.toBeNull();
    expect(controls.querySelector(".header")).toBeNull();
    expect(q(card, ".header").closest(".controls")).toBeNull();
    await click(card, "button.label");
    expect(q(card, ".controls").querySelector(".custom")).not.toBeNull();
    const css = EnergyCostStatsCard.styles.toString();
    expect(css).toMatch(/\.controls\s*{[^}]*position: sticky/);
    expect(css).toMatch(/\.controls\s*{[^}]*z-index: 3/);
    expect(css).toContain("--energy-cost-stats-sticky-top");
    expect(css).toMatch(/thead\s*{[^}]*position: sticky/);
    expect(css).toMatch(/\.table-wrap\s*{[^}]*max-height/);
  });

  it("renders without ResizeObserver", async () => {
    vi.stubGlobal("ResizeObserver", undefined);
    const { card } = await mount();
    expect(card.shadowRoot!.querySelector("table.devices")).not.toBeNull();
  });
});
