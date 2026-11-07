/** Bundle entry: registers the card element and announces it to the card picker. */

import { CARD_TYPE, EnergyCostStatsCard } from "./card";
import { EnergyCostStatsPanel, PANEL_ELEMENT } from "./panel";

declare global {
  interface Window {
    customCards?: { type: string; name: string; description: string; preview?: boolean }[];
  }
}

export const BOOT_TIMEOUT_MS = 30_000;

/** Define the element in the registry that is current *now* (read at call time). */
export function defineCard(): void {
  const registry = window.customElements;
  if (!registry.get(CARD_TYPE)) {
    registry.define(CARD_TYPE, EnergyCostStatsCard);
    window.customCards = window.customCards ?? [];
    if (!window.customCards.some((card) => card.type === CARD_TYPE)) {
      window.customCards.push({
        type: CARD_TYPE,
        name: "Energy Cost Stats",
        description: "Electricity cost per device, split by tariff zones",
        preview: false,
      });
    }
  }
  // The sidebar panel element lives in the same bundle; it is not a dashboard card.
  if (!registry.get(PANEL_ELEMENT)) registry.define(PANEL_ELEMENT, EnergyCostStatsPanel);
}

/**
 * The integration loads this bundle as an "extra module", which the page imports
 * before Home Assistant's own frontend has booted. Recent frontends install a
 * scoped custom element registry polyfill that replaces `window.customElements`
 * while booting, so an element defined earlier is invisible to the dashboards
 * ("Configuration error"). Wait until the `<home-assistant>` root element is
 * defined (the frontend has booted and the final registry is in place), then
 * define the card. When the bundle is loaded later (e.g. as a dashboard
 * resource) or outside the HA page, define it right away.
 */
export function registerCard(): void {
  const bootPending =
    document.querySelector("home-assistant") !== null &&
    !window.customElements.get("home-assistant");
  if (bootPending) {
    void window.customElements.whenDefined("home-assistant").then(defineCard);
    // Should a future frontend never define <home-assistant> in this registry,
    // do not stay invisible silently: define in whatever registry is current.
    setTimeout(() => {
      if (!window.customElements.get(CARD_TYPE)) {
        console.warn(`${CARD_TYPE}: the frontend did not boot in time; defining the card anyway`);
        defineCard();
      }
    }, BOOT_TIMEOUT_MS);
  } else {
    defineCard();
  }
}

registerCard();
