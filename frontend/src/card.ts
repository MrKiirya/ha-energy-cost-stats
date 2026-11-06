/**
 * `custom:energy-cost-stats-card` — per-device cost table split by tariff zones,
 * with an Energy-dashboard-style period picker (presets, arrows, "now", custom range).
 * Data comes only from the `energy_cost_stats/report` websocket command (SPEC §2, §4).
 */

import { LitElement, css, html, nothing, type PropertyValues, type TemplateResult } from "lit";
import { Strings, type StringKey } from "./i18n";
import {
  PRESETS,
  addDays,
  autoGrouping,
  containsDate,
  currentPeriod,
  groupingAllowed,
  isValidDate,
  presetPeriod,
  shiftPeriod,
  todayIn,
  type Grouping,
  type Period,
  type Preset,
} from "./period";
import {
  errorCode,
  errorText,
  fetchReport,
  type Bucket,
  type HassLike,
  type ReportDocument,
  type Row,
} from "./report";

export const CARD_TYPE = "energy-cost-stats-card";

type GroupingChoice = Grouping | "auto";
const GROUPING_CHOICES: GroupingChoice[] = ["auto", "hour", "day", "week", "month"];

export interface CardConfig {
  type: string;
  title?: string;
  /** Subset of the integration's sensors; omitted = all. */
  entities?: string[];
  /** Initial period (default `this_month`). */
  period?: Preset;
  /** Initial grouping of the "by period" table (default `auto`). */
  grouping?: GroupingChoice;
  /** Show the "by period" table expanded (default false). */
  show_breakdown?: boolean;
}

/** While the period contains today, re-fetch this often (new hours get compiled). */
const REFRESH_MS = 10 * 60 * 1000;

const ICON_PREV = "M15.41,16.58L10.83,12L15.41,7.41L14,6L8,12L14,18L15.41,16.58Z";
const ICON_NEXT = "M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z";
const ICON_REFRESH =
  "M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z";

function icon(path: string): TemplateResult {
  return html`<svg viewBox="0 0 24 24" aria-hidden="true"><path d=${path}></path></svg>`;
}

export class EnergyCostStatsCard extends LitElement {
  static override properties = {
    hass: { attribute: false },
    _config: { state: true },
    _period: { state: true },
    _groupingChoice: { state: true },
    _report: { state: true },
    _error: { state: true },
    _loading: { state: true },
    _customOpen: { state: true },
    _customStart: { state: true },
    _customEnd: { state: true },
    _breakdownEntity: { state: true },
  };

  hass?: HassLike;
  private _config?: CardConfig;
  private _period?: Period;
  private _groupingChoice: GroupingChoice = "auto";
  private _report?: ReportDocument;
  private _error?: string;
  private _loading = false;
  private _customOpen = false;
  private _customStart = "";
  private _customEnd = "";
  private _breakdownEntity = "";
  private _requestSeq = 0;
  private _timer?: ReturnType<typeof setInterval>;

  static getStubConfig(): CardConfig {
    return { type: `custom:${CARD_TYPE}`, period: "this_month" };
  }

  setConfig(config: CardConfig): void {
    if (!config || typeof config !== "object") {
      throw new Error("Invalid configuration");
    }
    if (config.period !== undefined && !PRESETS.includes(config.period)) {
      throw new Error(`Unknown period: ${String(config.period)}`);
    }
    if (config.grouping !== undefined && !GROUPING_CHOICES.includes(config.grouping)) {
      throw new Error(`Unknown grouping: ${String(config.grouping)}`);
    }
    if (
      config.entities !== undefined &&
      (!Array.isArray(config.entities) || config.entities.some((e) => typeof e !== "string"))
    ) {
      throw new Error("entities must be a list of entity ids");
    }
    const previous = this._config;
    this._config = config;
    this._groupingChoice = config.grouping ?? "auto";
    if (previous && this._period) {
      // Config edited in the dashboard editor: start over from the configured period.
      this._period = undefined;
      this._report = undefined;
    }
  }

  getCardSize(): number {
    return 3 + (this._report?.devices.length ?? 2);
  }

  private get _strings(): Strings {
    return new Strings(this.hass?.locale?.language ?? this.hass?.language);
  }

  /** The report's time zone once known (the integration setting), else HA's. */
  private get _timeZone(): string | undefined {
    return this._report?.time_zone ?? this.hass?.config?.time_zone;
  }

  private _today(): string {
    return todayIn(this._timeZone);
  }

  /** The grouping actually requested for the "by period" table. */
  get grouping(): Grouping {
    const period = this._period;
    if (!period) return "day";
    const choice = this._groupingChoice;
    if (choice !== "auto" && groupingAllowed(choice, period)) return choice;
    return autoGrouping(period);
  }

  override connectedCallback(): void {
    super.connectedCallback();
    this._timer = setInterval(() => {
      if (this._period && containsDate(this._period, this._today()) && !this._loading) {
        void this._load();
      }
    }, REFRESH_MS);
  }

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    if (this._timer !== undefined) clearInterval(this._timer);
    this._timer = undefined;
  }

  protected override willUpdate(changed: PropertyValues): void {
    if (this.hass && this._config && !this._period) {
      this._period = presetPeriod(this._config.period ?? "this_month", this._today());
    }
    super.willUpdate(changed);
  }

  protected override updated(changed: PropertyValues): void {
    super.updated(changed);
    if (!this.hass || !this._period) return;
    if (
      changed.has("_period") ||
      changed.has("_groupingChoice") ||
      (changed.has("hass") && changed.get("hass") === undefined)
    ) {
      void this._load();
    }
  }

  private async _load(): Promise<void> {
    const hass = this.hass;
    const period = this._period;
    if (!hass || !period) return;
    const seq = ++this._requestSeq;
    this._loading = true;
    try {
      const report = await fetchReport(hass, {
        period,
        grouping: this.grouping,
        entities: this._config?.entities,
        timeZone: this._timeZone,
      });
      if (seq !== this._requestSeq) return;
      this._report = report;
      this._error = undefined;
    } catch (err) {
      if (seq !== this._requestSeq) return;
      const code = errorCode(err);
      const known: Record<string, StringKey> = {
        not_loaded: "error.not_loaded",
        invalid_period: "error.invalid_period",
        period_too_long: "error.period_too_long",
        unknown_entity: "error.unknown_entity",
        unknown_command: "error.unknown_command",
      };
      const key = code ? known[code] : undefined;
      this._error = key
        ? this._strings.t(key)
        : this._strings.t("error.generic", { message: errorText(err) });
      this._report = undefined;
    } finally {
      if (seq === this._requestSeq) this._loading = false;
    }
  }

  // ---- period picker ----------------------------------------------------

  private _selectedPreset(): Preset | "" {
    if (!this._period) return "";
    const today = this._today();
    const period = this._period;
    return (
      PRESETS.find((preset) => {
        const candidate = presetPeriod(preset, today);
        return candidate.start === period.start && candidate.end === period.end;
      }) ?? ""
    );
  }

  private _onPreset(ev: Event): void {
    const value = (ev.target as HTMLSelectElement).value;
    if (value === "custom") {
      this._openCustom();
      return;
    }
    if ((PRESETS as readonly string[]).includes(value)) {
      this._customOpen = false;
      this._period = presetPeriod(value as Preset, this._today());
    }
  }

  private _openCustom(): void {
    this._customOpen = true;
    this._customStart = this._period?.start ?? this._today();
    this._customEnd = this._period?.end ?? this._today();
  }

  private _applyCustom(): void {
    const start = this._customStart;
    const end = this._customEnd;
    if (!isValidDate(start) || !isValidDate(end)) return;
    this._period = start <= end ? { start, end } : { start: end, end: start };
    this._customOpen = false;
  }

  private _shift(direction: 1 | -1): void {
    if (this._period) this._period = shiftPeriod(this._period, direction);
  }

  private _now(): void {
    if (this._period) this._period = currentPeriod(this._period, this._today());
  }

  private _onGrouping(ev: Event): void {
    this._groupingChoice = (ev.target as HTMLSelectElement).value as GroupingChoice;
  }

  // ---- rendering --------------------------------------------------------

  protected override render(): TemplateResult | typeof nothing {
    if (!this._config || !this.hass || !this._period) return nothing;
    const s = this._strings;
    const title = this._config.title ?? s.t("title");
    return html`
      <ha-card>
        <div class="header">
          <div class="title">${title}</div>
          ${this._loading
            ? html`<div class="loading" role="status">${s.t("loading")}</div>`
            : nothing}
        </div>
        ${this._renderPicker(s)}
        <div class="content">
          ${this._error
            ? html`<div class="error" role="alert">${this._error}</div>`
            : this._report
              ? this._renderReport(s, this._report)
              : nothing}
        </div>
      </ha-card>
    `;
  }

  private _renderPicker(s: Strings): TemplateResult {
    const period = this._period!;
    const preset = this._selectedPreset();
    const today = this._today();
    const isCurrent = containsDate(period, today);
    const nextStartsInFuture = shiftPeriod(period, 1).start > today;
    return html`
      <div class="picker">
        <select
          class="preset"
          aria-label=${s.t("period")}
          .value=${preset}
          @change=${this._onPreset}
        >
          <option value="" ?hidden=${preset !== ""} ?selected=${preset === ""}>
            ${s.t("custom")}
          </option>
          ${PRESETS.map(
            (p) => html`<option value=${p} ?selected=${p === preset}>${s.preset(p)}</option>`,
          )}
          <option value="custom">${s.t("custom")}…</option>
        </select>
        <div class="nav">
          <button
            class="icon prev"
            title=${s.t("previous")}
            aria-label=${s.t("previous")}
            @click=${() => this._shift(-1)}
          >
            ${icon(ICON_PREV)}
          </button>
          <button class="label" title=${s.t("custom")} @click=${this._openCustom}>
            ${s.periodLabel(period)}
          </button>
          <button
            class="icon next"
            title=${s.t("next")}
            aria-label=${s.t("next")}
            ?disabled=${nextStartsInFuture}
            @click=${() => this._shift(1)}
          >
            ${icon(ICON_NEXT)}
          </button>
          <button class="text now" ?disabled=${isCurrent} @click=${this._now}>
            ${s.t("now")}
          </button>
        </div>
        <button
          class="icon refresh"
          title=${s.t("refresh")}
          aria-label=${s.t("refresh")}
          @click=${() => void this._load()}
        >
          ${icon(ICON_REFRESH)}
        </button>
      </div>
      ${this._customOpen
        ? html`<div class="custom">
            <label
              >${s.t("from")}
              <input
                type="date"
                class="custom-start"
                .value=${this._customStart}
                max=${today}
                @change=${(ev: Event) => {
                  this._customStart = (ev.target as HTMLInputElement).value;
                }}
            /></label>
            <label
              >${s.t("to")}
              <input
                type="date"
                class="custom-end"
                .value=${this._customEnd}
                @change=${(ev: Event) => {
                  this._customEnd = (ev.target as HTMLInputElement).value;
                }}
            /></label>
            <button class="text apply" @click=${this._applyCustom}>${s.t("apply")}</button>
          </div>`
        : nothing}
    `;
  }

  private _renderReport(s: Strings, report: ReportDocument): TemplateResult {
    if (report.devices.length === 0) {
      return html`<div class="note">${s.t("no_devices")}</div>`;
    }
    const names = new Map(report.devices.map((d) => [d.entity_id, d]));
    const totals = report.totals;
    const noPlan = report.plans.length === 0;
    return html`
      ${noPlan ? html`<div class="note warning">${s.t("no_plan")}</div>` : nothing}
      ${!noPlan && report.unpriced_hours > 0
        ? html`<div class="note warning">
            ${s.t("unpriced", { hours: report.unpriced_hours })}
          </div>`
        : nothing}
      <div class="table-wrap">
        <table class="devices">
          ${this._renderHead(s, report, s.t("device"), totals)}
          <tbody>
            ${totals.rows.map((row) => {
              const device = row.entity_id ? names.get(row.entity_id) : undefined;
              const label = device?.name ?? row.entity_id ?? "";
              const statistics =
                device && device.statistics !== "ok"
                  ? s.t(`statistics.${device.statistics}` as StringKey)
                  : "";
              return this._renderRow(s, report, row, label, statistics);
            })}
          </tbody>
          <tfoot>
            ${this._renderRow(s, report, totals.total, s.t("total"), "")}
          </tfoot>
        </table>
      </div>
      ${report.grouping !== "total" ? this._renderBreakdown(s, report) : nothing}
      ${report.issues.length > 0 ? this._renderIssues(s, report, names) : nothing}
    `;
  }

  private _renderHead(
    s: Strings,
    report: ReportDocument,
    firstColumn: string,
    totals: Bucket,
  ): TemplateResult {
    const currency = report.currency;
    return html`
      <thead>
        <tr>
          <th rowspan="2" class="name">${firstColumn}</th>
          ${report.zones.map((zone, index) => {
            const price = totals.total.zones[index]?.price ?? null;
            return html`<th colspan="2" class="zone">
              ${zone.name}${price !== null
                ? html`<span class="price">${s.money(price, currency)}</span>`
                : nothing}
            </th>`;
          })}
          <th colspan="3" class="zone sum">${s.t("total")}</th>
        </tr>
        <tr>
          ${report.zones.map(
            () => html`<th class="num">${s.t("kwh")}</th><th class="num">${s.t("cost")}</th>`,
          )}
          <th class="num">${s.t("kwh")}</th>
          <th class="num">${s.t("cost")}</th>
          <th class="num">${s.t("avg_price")}</th>
        </tr>
      </thead>
    `;
  }

  private _renderRow(
    s: Strings,
    report: ReportDocument,
    row: Row,
    label: string,
    note: string,
  ): TemplateResult {
    const currency = report.currency;
    const c = row.coverage;
    const coverage = s.t("coverage", {
      measured: c.measured,
      estimated: c.estimated,
      excluded: c.excluded,
      missing: c.missing,
      expected: c.expected,
    });
    return html`
      <tr class="status-${row.status}">
        <th scope="row" class="name">
          <span>${label}</span>
          ${row.status !== "complete"
            ? html`<span
                class="badge ${row.status}"
                title="${s.t(`status.${row.status}` as StringKey)} · ${coverage}"
                >${row.status === "estimated" ? "≈" : "!"}</span
              >`
            : nothing}
          ${note ? html`<span class="sub">${note}</span>` : nothing}
        </th>
        ${row.zones.map(
          (cell) =>
            html`<td class="num">${s.number(cell.kwh, 2)}</td>
              <td class="num">${s.money(cell.cost, currency)}</td>`,
        )}
        <td class="num strong">${s.number(row.kwh, 2)}</td>
        <td class="num strong">${s.money(row.cost, currency)}</td>
        <td class="num">${s.avgPrice(row.cost, row.kwh)}</td>
      </tr>
    `;
  }

  private _renderBreakdown(s: Strings, report: ReportDocument): TemplateResult {
    const entity = this._breakdownEntity;
    const index = entity ? report.devices.findIndex((d) => d.entity_id === entity) : -1;
    const pick = (bucket: Bucket): Row =>
      index >= 0 ? (bucket.rows[index] ?? bucket.total) : bucket.total;
    return html`
      <details class="breakdown" ?open=${this._config?.show_breakdown ?? false}>
        <summary>${s.t("breakdown")}</summary>
        <div class="breakdown-controls">
          <label
            >${s.t("breakdown_device")}
            <select
              class="breakdown-device"
              .value=${index >= 0 ? entity : ""}
              @change=${(ev: Event) => {
                this._breakdownEntity = (ev.target as HTMLSelectElement).value;
              }}
            >
              <option value="">${s.t("all_devices")}</option>
              ${report.devices.map(
                (d) =>
                  html`<option value=${d.entity_id} ?selected=${d.entity_id === entity}>
                    ${d.name}
                  </option>`,
              )}
            </select>
          </label>
          <label
            >${s.t("grouping")}
            <select class="grouping" .value=${this._groupingChoice} @change=${this._onGrouping}>
              ${GROUPING_CHOICES.map((g) => {
                const allowed = g === "auto" || groupingAllowed(g, this._period!);
                return html`<option
                  value=${g}
                  ?disabled=${!allowed}
                  ?selected=${g === this._groupingChoice}
                >
                  ${allowed ? s.grouping(g) : s.t("grouping.hour_too_long")}
                </option>`;
              })}
            </select>
          </label>
        </div>
        <div class="table-wrap">
          <table class="buckets">
            ${this._renderHead(s, report, s.t("period"), report.totals)}
            <tbody>
              ${report.buckets.map((bucket) =>
                this._renderRow(s, report, pick(bucket), this._bucketLabel(s, report, bucket), ""),
              )}
            </tbody>
            <tfoot>
              ${this._renderRow(s, report, pick(report.totals), s.t("total"), "")}
            </tfoot>
          </table>
        </div>
      </details>
    `;
  }

  private _bucketLabel(s: Strings, report: ReportDocument, bucket: Bucket): string {
    if (report.grouping === "week") {
      const start = bucket.start.slice(0, 10);
      const end = addDays(bucket.end.slice(0, 10), -1);
      return s.periodLabel({ start, end: end < start ? start : end });
    }
    return s.bucketLabel(bucket.start, report.grouping);
  }

  private _renderIssues(
    s: Strings,
    report: ReportDocument,
    names: Map<string, { name: string }>,
  ): TemplateResult {
    return html`
      <details class="issues">
        <summary>${s.t("data_quality")} (${report.issues.length})</summary>
        <ul>
          ${report.issues.map(
            (issue) =>
              html`<li>
                <span class="who">${names.get(issue.entity_id)?.name ?? issue.entity_id}</span>:
                ${s.t(`issue.${issue.kind}` as StringKey)},
                ${s.bucketLabel(issue.start, "hour")} – ${s.bucketLabel(issue.end, "hour")}
                (${issue.hours} h, ${s.number(issue.kwh, 3)} ${s.t("kwh")})
              </li>`,
          )}
        </ul>
      </details>
    `;
  }

  static override styles = css`
    :host {
      display: block;
    }
    ha-card {
      padding: 12px 16px 16px;
      box-sizing: border-box;
    }
    .header {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 8px;
    }
    .title {
      font-size: 1.25rem;
      font-weight: 500;
      line-height: 2;
    }
    .loading {
      color: var(--secondary-text-color);
      font-size: 0.85rem;
    }
    .picker,
    .custom,
    .breakdown-controls {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      margin: 4px 0 8px;
    }
    .nav {
      display: flex;
      align-items: center;
      gap: 2px;
      flex: 1 1 auto;
    }
    select,
    input,
    button {
      font: inherit;
      color: var(--primary-text-color);
    }
    select,
    input {
      background: var(--card-background-color, transparent);
      border: 1px solid var(--divider-color);
      border-radius: 6px;
      padding: 4px 6px;
    }
    button {
      background: none;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      padding: 4px 8px;
    }
    button:hover:not([disabled]) {
      background: var(--secondary-background-color);
    }
    button[disabled] {
      opacity: 0.4;
      cursor: default;
    }
    button.icon {
      padding: 4px;
      line-height: 0;
    }
    button.icon svg {
      width: 24px;
      height: 24px;
      fill: currentColor;
    }
    button.label {
      font-weight: 500;
      min-width: 9em;
    }
    button.text {
      color: var(--primary-color);
    }
    .content {
      margin-top: 4px;
    }
    .error {
      color: var(--error-color, #db4437);
    }
    .note {
      color: var(--secondary-text-color);
      margin: 4px 0;
    }
    .note.warning {
      color: var(--warning-color, #ffa600);
    }
    .table-wrap {
      overflow-x: auto;
    }
    table {
      border-collapse: collapse;
      width: 100%;
      font-size: 0.9rem;
    }
    th,
    td {
      padding: 4px 6px;
      white-space: nowrap;
    }
    thead th {
      color: var(--secondary-text-color);
      font-weight: 500;
      border-bottom: 1px solid var(--divider-color);
    }
    th.zone {
      text-align: center;
    }
    th.zone .price {
      display: block;
      font-size: 0.8em;
      font-weight: 400;
    }
    th.name {
      text-align: start;
      position: sticky;
      left: 0;
      background: var(--card-background-color, var(--ha-card-background, white));
    }
    tbody th.name {
      font-weight: 400;
    }
    .num {
      text-align: end;
      font-variant-numeric: tabular-nums;
    }
    .strong {
      font-weight: 500;
    }
    tbody tr + tr {
      border-top: 1px solid var(--divider-color);
    }
    tfoot tr {
      border-top: 2px solid var(--divider-color);
      font-weight: 600;
    }
    tfoot th.name {
      font-weight: 600;
    }
    .badge {
      display: inline-block;
      margin-inline-start: 4px;
      min-width: 1.2em;
      text-align: center;
      border-radius: 8px;
      font-size: 0.8em;
      cursor: help;
      color: var(--text-primary-color, white);
      background: var(--warning-color, #ffa600);
    }
    .badge.partial,
    .badge.missing {
      background: var(--error-color, #db4437);
    }
    .sub {
      display: block;
      font-size: 0.8em;
      color: var(--secondary-text-color);
    }
    details {
      margin-top: 12px;
    }
    summary {
      cursor: pointer;
      font-weight: 500;
    }
    .issues ul {
      margin: 4px 0;
      padding-inline-start: 20px;
      color: var(--secondary-text-color);
    }
  `;
}
