import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import "../src/index";
import type { EnergyCostStatsCard } from "../src/card";
import {
  collectionPeriod,
  collectionProperties,
  findEnergyCollection,
  type EnergyCollectionLike,
} from "../src/energy-period";
import type { HassLike } from "../src/report";
import { report } from "./fixtures";

type Msg = Record<string, unknown>;

/** A stand-in for HA's energy collection. */
function fakeCollection(start: Date, end?: Date) {
  const listeners = new Set<(data: { start: Date; end?: Date }) => void>();
  const collection = {
    start,
    end,
    unsubscribed: 0,
    subscribe(cb: (data: { start: Date; end?: Date }) => void) {
      listeners.add(cb);
      return () => {
        listeners.delete(cb);
        collection.unsubscribed += 1;
      };
    },
    setPeriod(newStart: Date, newEnd?: Date) {
      collection.start = newStart;
      collection.end = newEnd;
      for (const cb of listeners) cb({ start: newStart, end: newEnd });
    },
    listeners,
  };
  return collection;
}

// Moscow (UTC+3) local midnights and ends of day, as HA's picker keeps them.
const msk = (date: string, end = false) =>
  new Date(`${date}T${end ? "23:59:59.999" : "00:00:00.000"}+03:00`);

describe("collection lookup", () => {
  it("uses the collection_key, else energy_<dashboard>", () => {
    expect(collectionProperties("energy_custom", "/cost-card/cost")).toEqual(["_energy_custom"]);
    expect(collectionProperties(undefined, "/cost-card/cost")).toEqual(["_energy_cost-card"]);
    expect(collectionProperties(undefined, "/")).toEqual([]);
  });

  it("finds only collection-like objects", () => {
    const collection = fakeCollection(msk("2026-11-01"));
    expect(findEnergyCollection({ "_energy_cost-card": collection }, undefined, "/cost-card/x")).toBe(
      collection,
    );
    expect(findEnergyCollection({ "_energy_cost-card": { start: "x" } }, undefined, "/cost-card")).toBe(
      undefined,
    );
    expect(findEnergyCollection(undefined, undefined, "/cost-card")).toBe(undefined);
  });
});

describe("collectionPeriod", () => {
  it("reads a month in the report time zone", () => {
    expect(
      collectionPeriod({ start: msk("2026-10-01"), end: msk("2026-10-31", true) }, "Europe/Moscow"),
    ).toEqual({ start: "2026-10-01", end: "2026-10-31" });
  });

  it("is independent of the zone HA used for the bounds (browser vs server)", () => {
    // Picker in UTC+5 (browser), report in Moscow (UTC+3).
    const start = new Date("2026-11-06T00:00:00+05:00");
    const end = new Date("2026-11-06T23:59:59.999+05:00");
    expect(collectionPeriod({ start, end }, "Europe/Moscow")).toEqual({
      start: "2026-11-06",
      end: "2026-11-06",
    });
    // Picker in UTC-5 (browser), report in Moscow.
    expect(
      collectionPeriod(
        {
          start: new Date("2026-11-06T00:00:00-05:00"),
          end: new Date("2026-11-06T23:59:59.999-05:00"),
        },
        "Europe/Moscow",
      ),
    ).toEqual({ start: "2026-11-06", end: "2026-11-06" });
  });

  it("an open end means until today; invalid ranges are ignored", () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-11-06T12:00:00Z"));
    try {
      expect(collectionPeriod({ start: msk("2026-11-01") }, "Europe/Moscow")).toEqual({
        start: "2026-11-01",
        end: "2026-11-06",
      });
    } finally {
      vi.useRealTimers();
    }
    expect(collectionPeriod({ start: new Date("x") }, "UTC")).toBeUndefined();
    expect(
      collectionPeriod({ start: msk("2026-11-02"), end: msk("2026-11-01", true) }, "Europe/Moscow"),
    ).toBeUndefined();
  });
});

describe("card following the energy date picker", () => {
  let collection: ReturnType<typeof fakeCollection>;

  function makeHass(connection: Record<string, unknown>): HassLike & {
    calls: Msg[];
    connection: unknown;
  } {
    const calls: Msg[] = [];
    return {
      calls,
      connection,
      language: "en",
      locale: { language: "en" },
      config: { time_zone: "Europe/Moscow", currency: "RUB" },
      callWS: <T>(msg: Msg) => {
        calls.push(msg);
        return Promise.resolve(report()) as Promise<T>;
      },
    };
  }

  async function settle(card: EnergyCostStatsCard): Promise<void> {
    for (let i = 0; i < 5; i++) {
      await card.updateComplete;
      await new Promise((r) => setTimeout(r, 0));
    }
  }

  async function mount(config: Record<string, unknown>, hass: ReturnType<typeof makeHass>) {
    const card = document.createElement("energy-cost-stats-card") as EnergyCostStatsCard;
    card.setConfig({ type: "custom:energy-cost-stats-card", ...config });
    card.hass = hass;
    document.body.appendChild(card);
    await settle(card);
    return card;
  }

  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-11-06T12:00:00Z"));
    window.history.pushState({}, "", "/cost-card/cost");
    collection = fakeCollection(msk("2026-10-01"), msk("2026-10-31", true));
  });

  afterEach(() => {
    vi.useRealTimers();
    document.body.innerHTML = "";
  });

  it("takes the period from the picker and follows its changes", async () => {
    const hass = makeHass({ "_energy_cost-card": collection });
    const card = await mount({}, hass);
    expect(card.followsEnergyPicker).toBe(true);
    expect(hass.calls[hass.calls.length - 1]).toMatchObject({
      start: "2026-10-01",
      end: "2026-11-01",
    });
    // The own picker is replaced by a period line.
    expect(card.shadowRoot!.querySelector("select.preset")).toBeNull();
    expect(card.shadowRoot!.querySelector(".picker.followed")!.textContent).toContain("2026");

    collection.setPeriod(msk("2026-11-02"), msk("2026-11-08", true));
    await settle(card);
    expect(hass.calls[hass.calls.length - 1]).toMatchObject({
      start: "2026-11-02",
      end: "2026-11-06T15:00:00+03:00",
    });
  });

  it("uses a configured collection_key", async () => {
    const hass = makeHass({ _energy_mine: collection });
    const card = await mount({ collection_key: "energy_mine" }, hass);
    expect(card.followsEnergyPicker).toBe(true);
  });

  it("keeps its own picker with period_source: card", async () => {
    const hass = makeHass({ "_energy_cost-card": collection });
    const card = await mount({ period_source: "card" }, hass);
    expect(card.followsEnergyPicker).toBe(false);
    expect(card.shadowRoot!.querySelector("select.preset")).not.toBeNull();
    expect(hass.calls[0]).toMatchObject({ start: "2026-11-01" });
  });

  it("falls back to its own picker (with a note for period_source: energy)", async () => {
    const auto = await mount({}, makeHass({}));
    expect(auto.followsEnergyPicker).toBe(false);
    expect(auto.shadowRoot!.querySelector("select.preset")).not.toBeNull();
    expect(auto.shadowRoot!.querySelector(".note.warning")).toBeNull();
    document.body.innerHTML = "";

    const energy = await mount({ period_source: "energy" }, makeHass({}));
    expect(energy.shadowRoot!.querySelector(".note.warning")!.textContent).toContain(
      "Energy date picker",
    );
    expect(energy.shadowRoot!.querySelector("select.preset")).not.toBeNull();
  });

  it("attaches when the picker's collection appears later", async () => {
    const connection: Record<string, unknown> = {};
    const hass = makeHass(connection);
    const card = await mount({}, hass);
    expect(card.followsEnergyPicker).toBe(false);
    connection["_energy_cost-card"] = collection;
    card.hass = { ...hass }; // HA sets a new hass object on every state change
    await settle(card);
    expect(card.followsEnergyPicker).toBe(true);
    expect(hass.calls[hass.calls.length - 1]).toMatchObject({ start: "2026-10-01" });
  });

  it("unsubscribes when removed", async () => {
    const card = await mount({}, makeHass({ "_energy_cost-card": collection }));
    expect(collection.listeners.size).toBe(1);
    card.remove();
    expect(collection.unsubscribed).toBe(1);
    expect(collection.listeners.size).toBe(0);
  });

  it("rejects an unknown period_source", () => {
    const card = document.createElement("energy-cost-stats-card") as EnergyCostStatsCard;
    expect(() => card.setConfig({ type: "x", period_source: "calendar" as never })).toThrow(
      /period_source/,
    );
  });

  it("satisfies the collection type", () => {
    const typed: EnergyCollectionLike = collection;
    expect(typed.start).toBeInstanceOf(Date);
  });
});
