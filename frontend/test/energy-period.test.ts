import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import "../src/index";
import type { EnergyCostStatsCard } from "../src/card";
import {
  collectionPeriod,
  collectionProperties,
  dashboardPath,
  findEnergyCollection,
  isValidCollectionKey,
  pickerTimeZone,
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
    expect(collectionProperties("energy_custom", "cost-card")).toEqual(["_energy_custom"]);
    expect(collectionProperties(undefined, "cost-card")).toEqual(["_energy_cost-card"]);
    expect(collectionProperties(undefined, undefined)).toEqual([]);
    expect(dashboardPath("cost-card", "/other/view")).toBe("cost-card");
    expect(dashboardPath(undefined, "/cost-card/cost")).toBe("cost-card");
    expect(dashboardPath(undefined, "/")).toBeUndefined();
    expect(isValidCollectionKey("energy_mine")).toBe(true);
    expect(isValidCollectionKey("mine")).toBe(false);
  });

  it("finds only collection-like objects", () => {
    const collection = fakeCollection(msk("2026-11-01"));
    expect(findEnergyCollection({ "_energy_cost-card": collection }, undefined, "cost-card")).toBe(
      collection,
    );
    expect(findEnergyCollection({ "_energy_cost-card": { start: "x" } }, undefined, "cost-card")).toBe(
      undefined,
    );
    expect(findEnergyCollection(undefined, undefined, "cost-card")).toBe(undefined);
  });
});

describe("collectionPeriod", () => {
  it("reads a month in the report time zone", () => {
    expect(
      collectionPeriod({ start: msk("2026-10-01"), end: msk("2026-10-31", true) }, "Europe/Moscow"),
    ).toEqual({ start: "2026-10-01", end: "2026-10-31" });
  });

  it("reads the dates in the zone HA used for the bounds, even 12 h or more away", () => {
    // Profile "local" in Honolulu (UTC-10), integration in Moscow (UTC+3).
    const hnl = (date: string, end = false) =>
      new Date(`${date}T${end ? "23:59:59.999" : "00:00:00.000"}-10:00`);
    expect(
      collectionPeriod({ start: hnl("2026-11-05"), end: hnl("2026-11-05", true) }, "Pacific/Honolulu"),
    ).toEqual({ start: "2026-11-05", end: "2026-11-05" });
    // Profile "local" in Tokyo (UTC+9) picking a week.
    const tyo = (date: string, end = false) =>
      new Date(`${date}T${end ? "23:59:59.999" : "00:00:00.000"}+09:00`);
    expect(
      collectionPeriod({ start: tyo("2026-11-02"), end: tyo("2026-11-08", true) }, "Asia/Tokyo"),
    ).toEqual({ start: "2026-11-02", end: "2026-11-08" });
  });

  it("picks the zone from the profile setting", () => {
    expect(pickerTimeZone({ time_zone: "server" }, "Europe/Moscow")).toBe("Europe/Moscow");
    expect(pickerTimeZone({ time_zone: "local" }, "Europe/Moscow")).toBeUndefined();
    expect(pickerTimeZone(undefined, "Europe/Moscow")).toBeUndefined();
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
    panelUrl: string;
  } {
    const calls: Msg[] = [];
    return {
      calls,
      connection,
      panelUrl: "cost-card",
      language: "en",
      // Bounds below are Moscow midnights: like a profile set to the server zone.
      locale: { language: "en", time_zone: "server" },
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
    const card = await mount({ period_source: "energy" }, hass);
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
    const card = await mount({ period_source: "energy", collection_key: "energy_mine" }, hass);
    expect(card.followsEnergyPicker).toBe(true);
  });

  it("keeps its own picker by default, even when an energy collection exists", async () => {
    // Every HA energy card creates the collection; that alone is no picker.
    const hass = makeHass({ "_energy_cost-card": collection });
    const card = await mount({}, hass);
    expect(card.followsEnergyPicker).toBe(false);
    expect(card.shadowRoot!.querySelector("select.preset")).not.toBeNull();
    expect(hass.calls[0]).toMatchObject({ start: "2026-11-01" });
  });

  it("falls back to its own picker with a note when the picker is missing", async () => {
    const energy = await mount({ period_source: "energy" }, makeHass({}));
    expect(energy.shadowRoot!.querySelector(".note.warning")!.textContent).toContain(
      "Energy date picker",
    );
    expect(energy.shadowRoot!.querySelector("select.preset")).not.toBeNull();
  });

  it("attaches when the picker's collection appears later", async () => {
    const connection: Record<string, unknown> = {};
    const hass = makeHass(connection);
    const card = await mount({ period_source: "energy" }, hass);
    expect(card.followsEnergyPicker).toBe(false);
    connection["_energy_cost-card"] = collection;
    card.hass = { ...hass }; // HA sets a new hass object on every state change
    await settle(card);
    expect(card.followsEnergyPicker).toBe(true);
    expect(hass.calls[hass.calls.length - 1]).toMatchObject({ start: "2026-10-01" });
  });

  it("unsubscribes when removed", async () => {
    const card = await mount({ period_source: "energy" }, makeHass({ "_energy_cost-card": collection }));
    expect(collection.listeners.size).toBe(1);
    card.remove();
    expect(collection.unsubscribed).toBe(1);
    expect(collection.listeners.size).toBe(0);
  });

  it("rejects an unknown period_source or a collection_key HA would reject", () => {
    const card = document.createElement("energy-cost-stats-card") as EnergyCostStatsCard;
    expect(() => card.setConfig({ type: "x", period_source: "auto" as never })).toThrow(
      /period_source/,
    );
    expect(() => card.setConfig({ type: "x", collection_key: "mine" })).toThrow(/energy_/);
  });

  it("re-attaches after config edits", async () => {
    const other = fakeCollection(msk("2026-09-01"), msk("2026-09-30", true));
    const hass = makeHass({ "_energy_cost-card": collection, _energy_other: other });
    const card = await mount({ period_source: "energy" }, hass);
    expect(collection.listeners.size).toBe(1);

    // A title edit keeps following (fresh subscription, same collection).
    card.setConfig({ type: "custom:energy-cost-stats-card", period_source: "energy", title: "X" });
    await settle(card);
    expect(card.followsEnergyPicker).toBe(true);
    expect(collection.listeners.size).toBe(1);
    expect(hass.calls[hass.calls.length - 1]).toMatchObject({ start: "2026-10-01" });

    // Another collection_key: follows the other picker only.
    card.setConfig({
      type: "custom:energy-cost-stats-card",
      period_source: "energy",
      collection_key: "energy_other",
    });
    await settle(card);
    expect(collection.listeners.size).toBe(0);
    expect(other.listeners.size).toBe(1);
    expect(hass.calls[hass.calls.length - 1]).toMatchObject({ start: "2026-09-01" });

    // Back to the own picker: no subscription, configured preset.
    card.setConfig({ type: "custom:energy-cost-stats-card", period_source: "card" });
    await settle(card);
    expect(card.followsEnergyPicker).toBe(false);
    expect(other.listeners.size).toBe(0);
    expect(card.shadowRoot!.querySelector("select.preset")).not.toBeNull();
    expect(hass.calls[hass.calls.length - 1]).toMatchObject({ start: "2026-11-01" });
  });

  it("does not retry a collection whose subscribe() throws", async () => {
    let attempts = 0;
    const broken = {
      start: msk("2026-10-01"),
      end: msk("2026-10-31", true),
      subscribe: () => {
        attempts += 1;
        throw new Error("changed API");
      },
    };
    const hass = makeHass({ "_energy_cost-card": broken });
    const card = await mount({ period_source: "energy" }, hass);
    card.hass = { ...hass };
    await settle(card);
    expect(attempts).toBe(1);
    expect(card.followsEnergyPicker).toBe(false);
  });

  it("satisfies the collection type", () => {
    const typed: EnergyCollectionLike = collection;
    expect(typed.start).toBeInstanceOf(Date);
  });
});
