/** Bundle entry: registers the card element and announces it to the card picker. */

import { CARD_TYPE, EnergyCostStatsCard } from "./card";

declare global {
  interface Window {
    customCards?: { type: string; name: string; description: string; preview?: boolean }[];
  }
}

/** Define the element in the registry that is current *now* (read at call time). */
export function defineCard(): void {
  const registry = window.customElements;
  if (registry.get(CARD_TYPE)) return;
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
  } else {
    defineCard();
  }
}

registerCard();
