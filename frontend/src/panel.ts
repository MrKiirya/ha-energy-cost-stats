/**
 * `energy-cost-stats-panel` — the sidebar page (SPEC §4.1): a top bar with the panel
 * title and, on narrow screens, a menu button, and the cost card at full width. Home
 * Assistant creates the element for the custom panel and sets `hass`, `narrow`, `route`
 * and `panel` on it.
 */

import { LitElement, css, html, nothing, type PropertyValues, type TemplateResult } from "lit";
import { CARD_TYPE, type CardConfig, type EnergyCostStatsCard } from "./card";
import { hassChanged } from "./hass";
import { Strings } from "./i18n";
import type { HassLike } from "./report";

export const PANEL_ELEMENT = "energy-cost-stats-panel";

const ICON_MENU = "M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z";

interface CardHelpers {
  createCardElement(config: Record<string, unknown>): HTMLElement | undefined;
}

/** The part of Home Assistant's panel info the element reads. */
export interface PanelInfo {
  title?: string | null;
  config?: { card?: Partial<CardConfig> } & Record<string, unknown>;
}

export class EnergyCostStatsPanel extends LitElement {
  static override properties = {
    // Written by the accessor below (forwards to the card, gated re-render).
    hass: { attribute: false, noAccessor: true },
    narrow: { type: Boolean },
    route: { attribute: false },
    panel: { attribute: false },
    _error: { state: true },
  };

  narrow = false;
  route?: unknown;
  panel?: PanelInfo;
  private _error?: string;
  private _hass?: HassLike;
  private _card?: EnergyCostStatsCard;
  private _cardKey = "";
  private _picker?: HTMLElement;
  private _pickerRequested = false;
  /** The picker attempt finished (created or given up): the cost card is created only then. */
  private _pickerSettled = false;
  private _pickerObserver?: ResizeObserver;
  private _observedPicker?: Element;
  /** `collection_key` shared by HA's energy date picker and the cost card. */
  private readonly _collectionKey = "energy_energy_cost_stats_panel";

  get hass(): HassLike | undefined {
    return this._hass;
  }

  /** Every new object reaches the card; the panel itself re-renders like the card does. */
  set hass(value: HassLike | undefined) {
    const previous = this._hass;
    this._hass = value;
    if (this._card) this._card.hass = value;
    if (this._picker) (this._picker as HTMLElement & { hass?: HassLike }).hass = value;
    if (hassChanged(value, previous)) this.requestUpdate("hass", previous);
  }

  override connectedCallback(): void {
    super.connectedCallback();
    if (typeof ResizeObserver !== "undefined") {
      this._pickerObserver = new ResizeObserver((entries) => {
        const entry = entries[entries.length - 1];
        if (!entry) return;
        const height = entry.target.getBoundingClientRect().height;
        this.style.setProperty("--ecs-panel-picker-height", `${Math.ceil(height)}px`);
      });
    }
    void this._createPicker();
    if (this._picker) this.requestUpdate();
  }

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    this._pickerObserver?.disconnect();
    this._pickerObserver = undefined;
    this._observedPicker = undefined;
  }

  /** Home Assistant's own energy date picker, via the frontend's card helpers (best effort). */
  private async _createPicker(): Promise<void> {
    if (this._pickerRequested) return;
    this._pickerRequested = true;
    try {
      const load = (window as unknown as { loadCardHelpers?: () => Promise<CardHelpers> })
        .loadCardHelpers;
      if (typeof load !== "function") return;
      const helpers = await load.call(window);
      const picker = helpers.createCardElement({
        type: "energy-date-selection",
        collection_key: this._collectionKey,
      });
      // An unknown or failing card type yields HA's error card: no picker then.
      if (!picker || picker.tagName.toLowerCase() === "hui-error-card") return;
      (picker as HTMLElement & { hass?: HassLike }).hass = this._hass;
      this._picker = picker;
      this.setAttribute("has-picker", "");
    } catch {
      // Unavailable: the cost card keeps its own picker.
    } finally {
      this._pickerSettled = true;
      this.requestUpdate();
    }
  }

  protected override updated(_changed: PropertyValues): void {
    const picker = this.shadowRoot?.querySelector(".picker") ?? undefined;
    if (picker === this._observedPicker || !this._pickerObserver) return;
    if (this._observedPicker) this._pickerObserver.unobserve(this._observedPicker);
    this._observedPicker = picker;
    if (picker) this._pickerObserver.observe(picker);
  }

  protected override willUpdate(_changed: PropertyValues): void {
    if (!this._pickerSettled) return;
    const config: Record<string, unknown> = {
      title: "",
      ...(this.panel?.config?.card ?? {}),
      type: `custom:${CARD_TYPE}`,
    };
    if (this._picker) {
      config.period_source = "energy";
      config.collection_key = this._collectionKey;
    }
    const key = JSON.stringify(config);
    if (key === this._cardKey && (this._card || this._error)) return;
    this._cardKey = key;
    try {
      const card = document.createElement(CARD_TYPE) as EnergyCostStatsCard;
      card.setConfig(config as unknown as CardConfig);
      card.hass = this._hass;
      this._card = card;
      this._error = undefined;
    } catch (err) {
      this._card = undefined;
      this._error = err instanceof Error ? err.message : String(err);
    }
  }

  private _toggleMenu(): void {
    this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true }));
  }

  protected override render(): TemplateResult {
    const s = new Strings(this._hass?.locale?.language ?? this._hass?.language);
    return html`
      <div class="toolbar">
        ${this.narrow
          ? html`<button class="menu" aria-label=${s.t("menu")} @click=${this._toggleMenu}>
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d=${ICON_MENU}></path></svg>
            </button>`
          : nothing}
        <div class="title">${this.panel?.title ?? ""}</div>
      </div>
      ${this._picker ? html`<div class="picker">${this._picker}</div>` : nothing}
      <div class="content ${this.narrow ? "narrow" : ""}">
        ${this._error
          ? html`<div class="error" role="alert">${this._error}</div>`
          : this._card}
      </div>
    `;
  }

  static override styles = css`
    :host {
      display: block;
      min-height: 100vh;
      /* The card's period controls stick directly under the panel bar. */
      --energy-cost-stats-sticky-top: var(--header-height, 56px);
      background: var(--primary-background-color);
      color: var(--primary-text-color);
    }
    :host([has-picker]) {
      --energy-cost-stats-sticky-top: calc(
        var(--header-height, 56px) + var(--ecs-panel-picker-height, 0px)
      );
    }
    .picker {
      position: sticky;
      top: var(--header-height, 56px);
      z-index: 4;
      background: var(--primary-background-color);
      border-bottom: 1px solid var(--divider-color);
    }
    .toolbar {
      position: sticky;
      top: 0;
      z-index: 5;
      display: flex;
      align-items: center;
      gap: 8px;
      box-sizing: border-box;
      height: var(--header-height, 56px);
      padding: 0 12px;
      background-color: var(--app-header-background-color, var(--primary-color));
      color: var(--app-header-text-color, var(--text-primary-color, #fff));
      font-size: 20px;
      font-weight: 400;
    }
    .menu {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 40px;
      height: 40px;
      padding: 0;
      border: none;
      border-radius: 50%;
      background: none;
      color: inherit;
      cursor: pointer;
    }
    .menu svg {
      width: 24px;
      height: 24px;
      fill: currentColor;
    }
    .title {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .content {
      padding: 16px;
    }
    .content.narrow {
      padding: 8px;
    }
    .error {
      color: var(--error-color);
    }
  `;
}
