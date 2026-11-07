import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import "../src/index";
import { EnergyCostStatsCard } from "../src/card";
import { EnergyCostStatsPanel } from "../src/panel";
import type { HassLike } from "../src/report";
import { compareDoc, report } from "./fixtures";

type Msg = Record<string, unknown>;

function makeHass(language = "en"): HassLike & { calls: Msg[] } {
  const calls: Msg[] = [];
  return {
    calls,
    language,
    locale: { language },
    config: { time_zone: "UTC", currency: "EUR" },
    callWS: <T>(msg: Msg) => {
      calls.push(msg);
      return Promise.resolve(
        msg.type === "energy_cost_stats/compare" ? compareDoc() : report(),
      ) as Promise<T>;
    },
  };
}

async function settle(el: EnergyCostStatsPanel): Promise<void> {
  for (let i = 0; i < 5; i++) {
    await el.updateComplete;
    await Promise.resolve();
    await new Promise((r) => setTimeout(r, 0));
    const card = el.shadowRoot?.querySelector<EnergyCostStatsCard>("energy-cost-stats-card");
    if (card) await card.updateComplete;
  }
}

async function mount(
  props: Partial<{
    hass: HassLike;
    narrow: boolean;
    panel: { title?: string; config?: Record<string, unknown> };
  }> = {},
): Promise<EnergyCostStatsPanel> {
  const el = document.createElement("energy-cost-stats-panel") as EnergyCostStatsPanel;
  el.hass = props.hass ?? makeHass();
  el.narrow = props.narrow ?? false;
  el.panel = props.panel ?? { title: "Energy cost", config: {} };
  document.body.appendChild(el);
  await settle(el);
  return el;
}

function cardOf(el: EnergyCostStatsPanel): EnergyCostStatsCard {
  return el.shadowRoot!.querySelector<EnergyCostStatsCard>("energy-cost-stats-card")!;
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-11-06T12:00:00Z"));
});

afterEach(() => {
  vi.useRealTimers();
  document.body.innerHTML = "";
});

describe("panel", () => {
  it("renders the card with hass", async () => {
    const hass = makeHass();
    const el = await mount({ hass });
    const cards = el.shadowRoot!.querySelectorAll("energy-cost-stats-card");
    expect(cards).toHaveLength(1);
    expect(cards[0]).toBeInstanceOf(EnergyCostStatsCard);
    expect(cardOf(el).hass).toBe(hass);
    expect(hass.calls.some((c) => c.type === "energy_cost_stats/report")).toBe(true);
  });

  it("shows the panel title in the top bar", async () => {
    const el = await mount({ panel: { title: "Costs", config: {} } });
    expect(el.shadowRoot!.querySelector(".toolbar")!.textContent!.trim()).toBe("Costs");
    expect(cardOf(el).shadowRoot!.querySelector(".title")).toBeNull();
  });

  it("menu button only when narrow", async () => {
    const wide = await mount({ narrow: false });
    expect(wide.shadowRoot!.querySelector("button.menu")).toBeNull();
    wide.remove();

    const narrow = await mount({ narrow: true });
    const button = narrow.shadowRoot!.querySelector<HTMLButtonElement>("button.menu")!;
    expect(button).not.toBeNull();
    const seen: Event[] = [];
    document.body.addEventListener("hass-toggle-menu", (ev) => seen.push(ev));
    button.click();
    expect(seen).toHaveLength(1);
    expect(seen[0]!.bubbles).toBe(true);
    expect(seen[0]!.composed).toBe(true);
  });

  it("forwards hass updates without re-rendering", async () => {
    const hass = makeHass();
    const el = await mount({ hass });
    const render = vi.spyOn(el as unknown as { render: () => unknown }, "render");
    const calls = hass.calls.length;

    const next = { ...hass, states: { a: 1 } } as HassLike & { calls: Msg[] };
    el.hass = next;
    await settle(el);
    expect(render).not.toHaveBeenCalled();
    expect(cardOf(el).hass).toBe(next);
    expect(hass.calls.length).toBe(calls);

    el.hass = { ...next, language: "ru", locale: { language: "ru" } };
    await settle(el);
    expect(render).toHaveBeenCalled();
  });

  it("properties set before definition survive", async () => {
    const tag = "energy-cost-stats-panel-late";
    const el = document.createElement(tag) as EnergyCostStatsPanel;
    const hass = makeHass();
    el.hass = hass;
    el.narrow = true;
    el.panel = { title: "Late", config: {} };
    document.body.appendChild(el);
    window.customElements.define(tag, class extends EnergyCostStatsPanel {});
    await settle(el);
    expect(el.shadowRoot!.querySelector(".toolbar")!.textContent).toContain("Late");
    expect(el.shadowRoot!.querySelector("button.menu")).not.toBeNull();
    expect(cardOf(el).hass).toBe(hass);
  });

  it("card config cannot override the card type", async () => {
    const el = await mount({
      panel: { title: "X", config: { card: { type: "custom:other-card" } } },
    });
    expect(cardOf(el)).toBeInstanceOf(EnergyCostStatsCard);
    expect(el.shadowRoot!.querySelector('[role="alert"]')).toBeNull();
    expect((cardOf(el) as unknown as { _config: { type: string } })._config.type).toBe(
      "custom:energy-cost-stats-card",
    );
  });

  it("card config from panel.config.card", async () => {
    const el = await mount({
      panel: { title: "X", config: { card: { period: "last_month" } } },
    });
    expect(cardOf(el).shadowRoot!.querySelector<HTMLSelectElement>("select.preset")!.value).toBe(
      "last_month",
    );

    const bad = await mount({
      panel: { title: "X", config: { card: { period: "fortnight" } } },
    });
    expect(bad.shadowRoot!.querySelector('[role="alert"]')!.textContent).toMatch(/period/);
  });
});

describe("sticky toolbar", () => {
  it("keeps the bar on top and tells the card where to stick", () => {
    const css = EnergyCostStatsPanel.styles.toString();
    expect(css).toMatch(/\.toolbar\s*{[^}]*position: sticky/);
    expect(css).toMatch(/--energy-cost-stats-sticky-top:\s*var\(--header-height/);
  });
});
