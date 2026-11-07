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

  get hass(): HassLike | undefined {
    return this._hass;
  }

  /** Every new object reaches the card; the panel itself re-renders like the card does. */
  set hass(value: HassLike | undefined) {
    const previous = this._hass;
    this._hass = value;
    if (this._card) this._card.hass = value;
    if (hassChanged(value, previous)) this.requestUpdate("hass", previous);
  }

  protected override willUpdate(_changed: PropertyValues): void {
    const config: Record<string, unknown> = {
      title: "",
      ...(this.panel?.config?.card ?? {}),
      type: `custom:${CARD_TYPE}`,
    };
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
      background: var(--primary-background-color);
      color: var(--primary-text-color);
    }
    .toolbar {
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
