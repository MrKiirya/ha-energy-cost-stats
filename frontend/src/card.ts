/**
 * `custom:energy-cost-stats-card` — per-device cost table split by tariff zones,
 * with an Energy-dashboard-style period picker (presets, arrows, "now", custom range).
 * Data comes only from the `energy_cost_stats/report` websocket command (SPEC §2, §4).
 */

import { LitElement, css, html, nothing, type PropertyValues, type TemplateResult } from "lit";
import { live } from "lit/directives/live.js";
import {
  collectionPeriod,
  dashboardPath,
  findEnergyCollection,
  isValidCollectionKey,
  pickerTimeZone,
  type EnergyCollectionLike,
} from "./energy-period";
import { Strings, type StringKey } from "./i18n";
import {
  PRESETS,
  addDays,
  autoGrouping,
  containsDate,
  currentPeriod,
  exclusiveEnd,
  groupingAllowed,
  isValidDate,
  presetPeriod,
  requestEnd,
  shiftPeriod,
  todayIn,
  type Grouping,
  type Period,
  type Preset,
} from "./period";
import { difference, orderNested } from "./compare";
import { hassChanged } from "./hass";
import {
  DEFAULT_SORT,
  loadSort,
  makeComparator,
  naturalDirection,
  resolveSort,
  saveSort,
  storageKey,
  validateSortConfig,
  type SortDirection,
  type SortSpec,
} from "./sort";
import {
  errorCode,
  errorText,
  fetchCompare,
  fetchReport,
  type Bucket,
  type CompareDocument,
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
  /** Default sort of the device table: `name`, `total`, `avg_price` or a zone key (default `total`). */
  sort?: string;
  /** Default direction (default: the key's natural one, descending for money). */
  sort_direction?: SortDirection;
  /**
   * Where the period comes from: `card` (default) — the card's own picker;
   * `energy` — Home Assistant's energy date picker (`energy-date-selection` card)
   * on the same dashboard, falling back to the own picker (with a note) when it
   * is not there. Opt-in because every HA energy card creates the collection the
   * picker uses, so its presence does not prove a picker is shown.
   */
  period_source?: PeriodSource;
  /** `collection_key` of the energy date picker to follow (when it sets one). */
  collection_key?: string;
}

type PeriodSource = "card" | "energy";
const PERIOD_SOURCES: PeriodSource[] = ["card", "energy"];

/** While the period contains today, re-fetch this often (new hours get compiled). */
const REFRESH_MS = 10 * 60 * 1000;

const ICON_PREV = "M15.41,16.58L10.83,12L15.41,7.41L14,6L8,12L14,18L15.41,16.58Z";
const ICON_NEXT = "M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z";
const ICON_REFRESH =
  "M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z";

function icon(path: string): TemplateResult {
  return html`<svg viewBox="0 0 24 24" aria-hidden="true"><path d=${path}></path></svg>`;
}

type CardHass = HassLike & { connection?: unknown; panelUrl?: string };

export class EnergyCostStatsCard extends LitElement {
  static override properties = {
    // Entity-state-only updates must not re-render (they close an open <select>).
    hass: { attribute: false, noAccessor: true },
    _config: { state: true },
    _period: { state: true },
    _groupingChoice: { state: true },
    _report: { state: true },
    _compare: { state: true },
    _compareError: { state: true },
    _compareLoading: { state: true },
    _compareHidden: { state: true },
    _error: { state: true },
    _loading: { state: true },
    _customOpen: { state: true },
    _customStart: { state: true },
    _customEnd: { state: true },
    _breakdownEntity: { state: true },
    _sortChoice: { state: true },
  };

  /** HA's energy collection being followed (`period_source: energy`). */
  private _energy?: EnergyCollectionLike;
  private _unsubEnergy?: () => void;
  /** The collection's subscribe() threw: do not retry it on every update. */
  private _energyBroken?: EnergyCollectionLike;
  private _config?: CardConfig;
  private _period?: Period;
  private _groupingChoice: GroupingChoice = "auto";
  private _report?: ReportDocument;
  private _compare?: CompareDocument;
  private _compareError?: string;
  /** A compare request is in flight (the shown comparison may be of a previous period). */
  private _compareLoading = false;
  /** The integration predates `compare`: the section is not shown. */
  private _compareHidden = false;
  private _error?: string;
  private _loading = false;
  private _customOpen = false;
  private _customStart = "";
  private _customEnd = "";
  private _breakdownEntity = "";
  /** The user's last header click (remembered in localStorage), else the YAML default. */
  private _sortChoice?: SortSpec;
  private _storageKey = "";
  private _controlsObserver?: ResizeObserver;
  private _observedControls?: Element;
  private _requestSeq = 0;
  private _compareSeq = 0;
  /** The integration's time zone, learned from the first report (kept on errors). */
  private _reportTimeZone?: string;
  /** The last request was cut at the current hour: refresh until it is not. */
  private _lastRequestOpen = false;
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
    validateSortConfig(config.sort, config.sort_direction);
    if (config.period_source !== undefined && !PERIOD_SOURCES.includes(config.period_source)) {
      throw new Error(`Unknown period_source: ${String(config.period_source)}`);
    }
    if (
      config.collection_key !== undefined &&
      (typeof config.collection_key !== "string" || !isValidCollectionKey(config.collection_key))
    ) {
      throw new Error('collection_key must start with "energy_" (as in the energy date picker)');
    }
    const previous = this._config;
    if (previous) {
      // period_source or collection_key may have changed: attach again from scratch.
      this._detachEnergy();
      this._energyBroken = undefined;
    }
    this._config = config;
    this._storageKey = storageKey(globalThis.location?.pathname ?? "", config);
    this._sortChoice = loadSort(this._storageKey);
    this._groupingChoice = config.grouping ?? "auto";
    if (previous && this._period) {
      // Config edited in the dashboard editor: start over from the configured period.
      this._period = undefined;
      this._report = undefined;
      this._compare = undefined;
    }
  }

  getCardSize(): number {
    const compared = this._compare && !this._compareHidden ? this._compare.tariffs.length + 3 : 0;
    return 3 + (this._report?.devices.length ?? 2) + compared;
  }

  /** Sections views: take the section's full width (a user `grid_options` still wins). */
  getGridOptions(): { columns: number | "full"; min_columns: number } {
    return { columns: "full", min_columns: 6 };
  }

  private get _strings(): Strings {
    return new Strings(this.hass?.locale?.language ?? this.hass?.language);
  }

  /** The report's time zone once known (the integration setting), else HA's. */
  private get _timeZone(): string | undefined {
    return this._reportTimeZone ?? this.hass?.config?.time_zone;
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

  private _hass?: CardHass;

  get hass(): CardHass | undefined {
    return this._hass;
  }

  set hass(value: CardHass | undefined) {
    const previous = this._hass;
    this._hass = value;
    // While waiting for the energy picker's collection, a hass object that carries a usable one
    // is a retry; without it the usual gate applies.
    let attachable = false;
    if (this._config?.period_source === "energy" && !this._energy) {
      const found = findEnergyCollection(
        value?.connection,
        this._config.collection_key,
        dashboardPath(value?.panelUrl, window.location.pathname),
      );
      attachable = found !== undefined && found !== this._energyBroken;
    }
    if (attachable || hassChanged(value, previous)) this.requestUpdate("hass", previous);
  }

  override connectedCallback(): void {
    super.connectedCallback();
    if (typeof ResizeObserver !== "undefined") {
      this._controlsObserver = new ResizeObserver((entries) => {
        const entry = entries[entries.length - 1];
        if (!entry) return;
        const height = entry.target.getBoundingClientRect().height;
        this.style.setProperty("--energy-cost-stats-controls-height", `${Math.ceil(height)}px`);
      });
    }
    this._observeControls();
    this._timer = setInterval(() => {
      // Keep refreshing while the period is still running, plus once after it ended
      // (its last hour is only compiled then).
      if (this._period && this._lastRequestOpen && !this._loading) {
        void this._load();
      }
    }, REFRESH_MS);
  }

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    if (this._timer !== undefined) clearInterval(this._timer);
    this._timer = undefined;
    this._detachEnergy();
    this._controlsObserver?.disconnect();
    this._controlsObserver = undefined;
    this._observedControls = undefined;
  }

  /** Keeps `--energy-cost-stats-controls-height` in sync with the sticky controls bar. */
  private _observeControls(): void {
    const observer = this._controlsObserver;
    if (!observer) return;
    const controls = this.shadowRoot?.querySelector(".controls") ?? undefined;
    if (controls === this._observedControls) return;
    if (this._observedControls) observer.unobserve(this._observedControls);
    this._observedControls = controls;
    if (controls) observer.observe(controls);
  }

  protected override willUpdate(changed: PropertyValues): void {
    if (this.hass && this._config && this.isConnected && !this._energy) {
      this._attachEnergy();
    }
    if (this.hass && this._config && !this._period) {
      this._period = presetPeriod(this._config.period ?? "this_month", this._today());
    }
    super.willUpdate(changed);
  }

  /** True while the period follows HA's energy date picker. */
  get followsEnergyPicker(): boolean {
    return this._energy !== undefined;
  }

  /**
   * Follow HA's energy date picker when allowed and present. The collection can
   * appear after this card (the picker card creates it), so this is retried on
   * every update until found.
   */
  private _attachEnergy(): void {
    if (this._config?.period_source !== "energy") return;
    const collection = findEnergyCollection(
      this.hass?.connection,
      this._config.collection_key,
      dashboardPath(this.hass?.panelUrl, window.location.pathname),
    );
    if (!collection || collection === this._energyBroken) return;
    this._energy = collection;
    const follow = (data: { start: Date; end?: Date }) => {
      const period = collectionPeriod(
        data,
        pickerTimeZone(this.hass?.locale, this.hass?.config?.time_zone),
      );
      if (!period) return;
      if (period.start !== this._period?.start || period.end !== this._period?.end) {
        this._customOpen = false;
        this._period = period;
      }
    };
    follow(collection);
    try {
      this._unsubEnergy = collection.subscribe(follow);
    } catch {
      // A changed internal API: fall back to the card's own picker, once.
      this._energy = undefined;
      this._energyBroken = collection;
    }
  }

  private _detachEnergy(): void {
    try {
      this._unsubEnergy?.();
    } catch {
      // Ignore: the collection may already be gone.
    }
    this._unsubEnergy = undefined;
    this._energy = undefined;
  }

  protected override updated(changed: PropertyValues): void {
    super.updated(changed);
    this._observeControls();
    if (!this.hass || !this._period) return;
    if (changed.has("_period") || (changed.has("hass") && changed.get("hass") === undefined)) {
      void this._load();
    } else if (changed.has("_groupingChoice")) {
      // The comparison has no grouping: only the report is re-requested.
      void this._loadReport();
    }
  }

  /** Report and comparison for the same period. */
  private _load(): Promise<void> {
    void this._loadCompare();
    return this._loadReport();
  }

  private async _loadCompare(): Promise<void> {
    const hass = this.hass;
    const period = this._period;
    if (!hass || !period) return;
    const seq = ++this._compareSeq;
    this._compareLoading = true;
    try {
      const compare = await fetchCompare(hass, {
        period,
        entities: this._config?.entities,
        timeZone: this._timeZone,
      });
      if (seq !== this._compareSeq) return;
      this._compare = compare;
      this._compareError = undefined;
      this._compareHidden = false;
    } catch (err) {
      if (seq !== this._compareSeq) return;
      this._compare = undefined;
      const code = errorCode(err);
      if (code === "unknown_command") {
        this._compareHidden = true;
        this._compareError = undefined;
        return;
      }
      this._compareHidden = false;
      this._compareError = this._strings.t("compare.error", { message: this._errorMessage(err) });
    } finally {
      if (seq === this._compareSeq) this._compareLoading = false;
    }
  }

  private _errorMessage(err: unknown): string {
    const code = errorCode(err);
    const known: Record<string, StringKey> = {
      not_loaded: "error.not_loaded",
      invalid_period: "error.invalid_period",
      period_too_long: "error.period_too_long",
      unknown_entity: "error.unknown_entity",
      unknown_tariff: "error.unknown_tariff",
    };
    const key = code ? known[code] : undefined;
    return key ? this._strings.t(key) : errorText(err);
  }

  private async _loadReport(): Promise<void> {
    const hass = this.hass;
    const period = this._period;
    if (!hass || !period) return;
    const seq = ++this._requestSeq;
    const timeZone = this._timeZone;
    this._loading = true;
    try {
      const report = await fetchReport(hass, {
        period,
        grouping: this.grouping,
        entities: this._config?.entities,
        timeZone,
      });
      if (seq !== this._requestSeq) return;
      this._report = report;
      this._error = undefined;
      this._reportTimeZone = report.time_zone;
      this._lastRequestOpen = requestEnd(period, report.time_zone) !== exclusiveEnd(period);
      if (report.time_zone !== timeZone && containsDate(period, todayIn(report.time_zone))) {
        // "Today" and the current hour were computed in HA's zone, not the
        // integration's: ask again with the right one.
        void this._load();
      }
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
        ${title || this._loading
          ? html`<div class="header">
              ${title ? html`<div class="title">${title}</div>` : nothing}
              ${this._loading
                ? html`<div class="loading" role="status">${s.t("loading")}</div>`
                : nothing}
            </div>`
          : nothing}
        <div class="controls">
          ${this._energy
            ? this._renderFollowedPeriod(s)
            : html`${this._config.period_source === "energy"
                ? html`<div class="note warning">${s.t("energy_picker_missing")}</div>`
                : nothing}${this._renderPicker(s)}`}
        </div>
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

  /** Period line when HA's energy date picker drives the period. */
  private _renderFollowedPeriod(s: Strings): TemplateResult {
    return html`
      <div class="picker followed">
        <span class="label" title=${s.t("energy_picker_followed")}>
          ${s.periodLabel(this._period!)}
        </span>
        <button
          class="icon refresh"
          title=${s.t("refresh")}
          aria-label=${s.t("refresh")}
          @click=${() => void this._load()}
        >
          ${icon(ICON_REFRESH)}
        </button>
      </div>
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
          .value=${live(preset)}
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

  // ---- sorting ----------------------------------------------------------

  /** The sort in effect for a report: click, else YAML, else total cost descending. */
  private _activeSort(report: ReportDocument): SortSpec {
    const config = this._config;
    const configured: SortSpec | undefined = config?.sort
      ? { sort: config.sort, direction: config.sort_direction ?? naturalDirection(config.sort) }
      : config?.sort_direction
        ? { sort: DEFAULT_SORT.sort, direction: config.sort_direction }
        : undefined;
    const spec = this._sortChoice ?? configured ?? DEFAULT_SORT;
    return resolveSort(
      spec,
      report.zones.map((z) => z.key),
    );
  }

  private _onSort(key: string): void {
    if (!this._report) return;
    const active = this._activeSort(this._report);
    const direction =
      active.sort === key ? (active.direction === "asc" ? "desc" : "asc") : naturalDirection(key);
    this._sortChoice = { sort: key, direction };
    saveSort(this._storageKey, this._sortChoice);
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
          ${this._renderHead(s, report, s.t("device"), totals, this._activeSort(report))}
          <tbody>
            ${this._deviceRows(report).map(({ row, depth }) => {
              const device = row.entity_id ? names.get(row.entity_id) : undefined;
              const label = device?.name ?? row.entity_id ?? "";
              const statistics =
                device && device.statistics !== "ok"
                  ? s.t(`statistics.${device.statistics}` as StringKey)
                  : "";
              const upstream = device?.upstream ? names.get(device.upstream) : undefined;
              return this._renderRow(s, report, row, label, statistics, {
                depth,
                title:
                  depth > 0 && upstream
                    ? `${label} — ${s.t("nested.title", { name: upstream.name })}`
                    : label,
              });
            })}
          </tbody>
          <tfoot>
            ${this._renderRow(s, report, totals.total, s.t("total"), "")}
          </tfoot>
        </table>
      </div>
      ${report.devices.some((d) => d.upstream && names.has(d.upstream))
        ? html`<div class="note nested-note">${s.t("nested.note")}</div>`
        : nothing}
      ${this._renderComparison(s, report)}
      ${report.grouping !== "total" ? this._renderBreakdown(s, report) : nothing}
      ${report.issues.length > 0 ? this._renderIssues(s, report, names) : nothing}
    `;
  }

  /** Rows in display order: nested devices directly after their upstream. */
  private _deviceRows(report: ReportDocument): { row: Row; depth: number }[] {
    const byId = new Map(report.totals.rows.map((r) => [r.entity_id, r]));
    const rows = new Map<string, Row>();
    for (const row of report.totals.rows) if (row.entity_id) rows.set(row.entity_id, row);
    const names = new Map(report.devices.map((d) => [d.entity_id, d.name]));
    const compare = makeComparator(
      this._activeSort(report),
      rows,
      names,
      this._strings.locale,
    );
    const out: { row: Row; depth: number }[] = [];
    const used = new Set<Row>();
    for (const { entity_id, depth } of orderNested(report.devices, compare)) {
      const row = byId.get(entity_id);
      if (row && !used.has(row)) {
        used.add(row);
        out.push({ row, depth });
      }
    }
    for (const row of report.totals.rows) {
      if (!used.has(row)) out.push({ row, depth: 0 });
    }
    return out;
  }

  private _renderComparison(s: Strings, report: ReportDocument): TemplateResult | typeof nothing {
    if (this._compareHidden) return nothing;
    const compare = this._compare;
    const error = this._compareError;
    if (!compare && !error) return nothing;
    const currency = report.currency;
    let body: TemplateResult | typeof nothing = nothing;
    if (error) {
      body = html`<div class="error" role="alert">${error}</div>`;
    } else if (compare && compare.tariffs.length === 0) {
      body = html`<div class="note">${s.t("compare.empty")}</div>`;
    } else if (compare) {
      const actual = compare.actual;
      const actualTotal = actual.totals.total;
      const plans = actual.plans.map((p) => p.name).join(" → ");
      body = html`<div class="table-wrap">
        <table class="comparison">
          <thead>
            <tr>
              <th rowspan="2" class="name">${s.t("compare.tariff")}</th>
              <th rowspan="2" class="num">${s.t("cost")}</th>
              <th colspan="2" class="zone group-start">${s.t("compare.difference")}</th>
              <th rowspan="2" class="num group-start">${s.t("avg_price")}</th>
            </tr>
            <tr>
              <th class="num group-start">${currency ?? ""}</th>
              <th class="num">%</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row" class="name" title=${s.t("compare.actual")}>
                <span>${s.t("compare.actual")}</span>
                ${plans ? html`<span class="sub">${plans}</span>` : nothing}
              </th>
              <td class="num strong">${s.money(actualTotal.cost, currency)}</td>
              <td class="num group-start">—</td>
              <td class="num">—</td>
              <td class="num group-start">${s.avgPrice(actualTotal.cost, actualTotal.kwh)}</td>
            </tr>
            ${compare.tariffs.map((tariff) => {
              const total = tariff.report.totals.total;
              const diff = difference(actualTotal.cost, total.cost);
              const own = tariff.report.unpriced_hours;
              const hours = own || actual.unpriced_hours;
              const hint = s.t(own > 0 ? "compare.unpriced" : "compare.unpriced_actual", { hours });
              return html`<tr>
                <th scope="row" class="name" title=${tariff.name}>
                  <span>${tariff.name}</span>
                  ${hours > 0
                    ? html`<span class="badge partial" title=${hint}
                        >!</span
                      >`
                    : nothing}
                </th>
                <td class="num strong">${s.money(total.cost, currency)}</td>
                <td class="num group-start">${s.signedMoney(diff.amount, currency)}</td>
                <td class="num">${s.signedPercent(diff.percent)}</td>
                <td class="num group-start">${s.avgPrice(total.cost, total.kwh)}</td>
              </tr>`;
            })}
          </tbody>
        </table>
      </div>`;
    }
    const loading = this._compareLoading;
    return html`<section
      class="comparison ${loading ? "loading" : ""}"
      aria-busy=${loading ? "true" : "false"}
    >
      <h3>
        ${s.t("compare.title")}
        ${loading ? html`<span class="loading" role="status">${s.t("loading")}</span>` : nothing}
      </h3>
      ${body}
    </section>`;
  }

  /**
   * Two head rows. With `sort` (the device table) every top-row header is a sort button;
   * the second row (kWh / cost) never is.
   */
  private _renderHead(
    s: Strings,
    report: ReportDocument,
    firstColumn: string,
    totals: Bucket,
    sort?: SortSpec,
  ): TemplateResult {
    const currency = report.currency;
    const header = (key: string, column: string, content: TemplateResult | string) => {
      if (!sort) return content;
      const active = sort.sort === key;
      const next: SortDirection = active
        ? sort.direction === "asc"
          ? "desc"
          : "asc"
        : naturalDirection(key);
      const title = s.t("sort.by", {
        column,
        direction: s.t(next === "asc" ? "sort.ascending" : "sort.descending"),
      });
      return html`<button
        type="button"
        class="sort"
        data-sort=${key}
        title=${title}
        @click=${() => this._onSort(key)}
      >
        ${content}${active
          ? html`<span class="sort-indicator" aria-hidden="true"
              >${sort.direction === "asc" ? "▲" : "▼"}</span
            >`
          : nothing}
      </button>`;
    };
    const ariaSort = (key: string) =>
      sort && sort.sort === key
        ? sort.direction === "asc"
          ? "ascending"
          : "descending"
        : nothing;
    return html`
      <thead>
        <tr>
          <th rowspan="2" class="name" aria-sort=${ariaSort("name")}>
            ${header("name", firstColumn, firstColumn)}
          </th>
          ${report.zones.map((zone, index) => {
            const price = totals.total.zones[index]?.price ?? null;
            return html`<th colspan="2" class="zone group-start" aria-sort=${ariaSort(zone.key)}>
              ${header(
                zone.key,
                s.t("sort.cost_of", { zone: zone.name }),
                html`${zone.name}${price !== null
                  ? html`<span class="price">${s.money(price, currency)}</span>`
                  : nothing}`,
              )}
            </th>`;
          })}
          <th colspan="2" class="zone sum group-start" aria-sort=${ariaSort("total")}>
            ${header("total", s.t("sort.total_cost"), s.t("total"))}
          </th>
          <th rowspan="2" class="num avg group-start" aria-sort=${ariaSort("avg_price")}>
            ${header("avg_price", s.t("avg_price"), s.t("avg_price"))}
          </th>
        </tr>
        <tr>
          ${report.zones.map(
            () =>
              html`<th class="num group-start">${s.t("kwh")}</th>
                <th class="num">${s.t("cost")}</th>`,
          )}
          <th class="num group-start">${s.t("kwh")}</th>
          <th class="num">${s.t("cost")}</th>
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
    nested: { depth: number; title: string } = { depth: 0, title: label },
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
      <tr class="status-${row.status} ${nested.depth > 0 ? "nested" : ""}">
        <th
          scope="row"
          class="name"
          title=${nested.title}
          style=${nested.depth > 0 ? `--depth: ${nested.depth}` : nothing}
        >
          <span>${nested.depth > 0 ? "↳ " : ""}${label}</span>
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
            html`<td class="num group-start">${s.number(cell.kwh, 2)}</td>
              <td class="num">${s.money(cell.cost, currency)}</td>`,
        )}
        <td class="num strong group-start">${s.number(row.kwh, 2)}</td>
        <td class="num strong">${s.money(row.cost, currency)}</td>
        <td class="num group-start">${s.avgPrice(row.cost, row.kwh)}</td>
      </tr>
    `;
  }

  private _renderBreakdown(s: Strings, report: ReportDocument): TemplateResult {
    const entity = this._breakdownEntity;
    const index = entity ? report.devices.findIndex((d) => d.entity_id === entity) : -1;
    const pick = (bucket: Bucket): Row =>
      (index >= 0 ? bucket.rows.find((row) => row.entity_id === entity) : undefined) ??
      bucket.total;
    // A choice the period does not allow (hours over 31 days) falls back to auto.
    const choice = this._groupingChoice;
    const shownGrouping =
      choice === "auto" || groupingAllowed(choice, this._period!) ? choice : "auto";
    return html`
      <details class="breakdown" ?open=${this._config?.show_breakdown ?? false}>
        <summary>${s.t("breakdown")}</summary>
        <div class="breakdown-controls">
          <label
            >${s.t("breakdown_device")}
            <select
              class="breakdown-device"
              .value=${live(index >= 0 ? entity : "")}
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
            <select class="grouping" .value=${live(shownGrouping)} @change=${this._onGrouping}>
              ${GROUPING_CHOICES.map((g) => {
                const allowed = g === "auto" || groupingAllowed(g, this._period!);
                return html`<option
                  value=${g}
                  ?disabled=${!allowed}
                  ?selected=${g === shownGrouping}
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
      // Label the whole calendar week, also when the last bucket is cut at the
      // current hour or the period starts mid-week.
      const start = bucket.start.slice(0, 10);
      return s.periodLabel({ start, end: addDays(start, 6) });
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
      /* Where the controls stick: below Home Assistant's top bar (override per theme / kiosk). */
      --ecs-sticky-top: var(
        --energy-cost-stats-sticky-top,
        calc(
          var(--header-height, 56px) + var(--safe-area-inset-top, env(safe-area-inset-top, 0px))
        )
      );
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
    .controls {
      position: sticky;
      top: var(--ecs-sticky-top);
      /* Below Home Assistant's fixed header (z-index 4); above the table box. */
      z-index: 3;
      margin-inline: -16px;
      padding-inline: 16px;
      background: var(--ha-card-background, var(--card-background-color, white));
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
    .picker.followed {
      justify-content: space-between;
    }
    .picker.followed .label {
      font-weight: 500;
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
      /* Scrolls in both axes inside the card so the head rows can stick to its top. */
      overflow: auto;
      max-height: calc(100vh - var(--ecs-sticky-top) - var(--energy-cost-stats-controls-height, 0px) - 8px);
      max-height: calc(100dvh - var(--ecs-sticky-top) - var(--energy-cost-stats-controls-height, 0px) - 8px);
      container-type: inline-size;
    }
    section.comparison {
      margin-top: 12px;
    }
    section.comparison.loading .table-wrap {
      opacity: 0.5;
    }
    section.comparison h3 .loading {
      margin-inline-start: 8px;
      font-size: 0.85rem;
      font-weight: 400;
    }
    section.comparison h3 {
      margin: 0 0 4px;
      font-size: 1rem;
      font-weight: 500;
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
    thead {
      position: sticky;
      top: 0;
      z-index: 2;
    }
    thead th {
      color: var(--secondary-text-color);
      font-weight: 500;
      background: var(--ha-card-background, var(--card-background-color, white));
      /* A shadow, not a border: borders of sticky cells scroll away in collapsed tables. */
      box-shadow: inset 0 -1px 0 var(--divider-color);
    }
    thead tr:first-child th {
      vertical-align: top;
    }
    button.sort {
      display: block;
      width: 100%;
      padding: 0;
      border-radius: 0;
      color: inherit;
      font-weight: inherit;
      text-align: inherit;
      white-space: inherit;
    }
    button.sort:hover:not([disabled]) {
      background: none;
      color: var(--primary-text-color);
    }
    button.sort:focus-visible {
      outline: 2px solid var(--primary-color);
      outline-offset: 2px;
    }
    .sort-indicator {
      margin-inline-start: 4px;
      font-size: 0.75em;
    }
    th.avg {
      text-align: end;
    }
    th.zone {
      text-align: center;
    }
    th.zone .price {
      display: block;
      font-size: 0.8em;
      font-weight: 400;
    }
    .group-start {
      border-inline-start: 1px solid var(--divider-color);
    }
    th.name {
      text-align: start;
      position: sticky;
      left: 0;
      background: var(--card-background-color, var(--ha-card-background, white));
      /* A shadow, not a border: borders of a sticky cell scroll away in collapsed tables. */
      box-shadow: inset -1px 0 0 var(--divider-color);
      z-index: 1;
    }
    thead th.name {
      z-index: 3;
      box-shadow:
        inset -1px 0 0 var(--divider-color),
        inset 0 -1px 0 var(--divider-color);
    }
    tbody th.name,
    tfoot th.name {
      white-space: normal;
      overflow-wrap: anywhere;
      min-width: 6.5em;
      max-width: max(6.5em, 35cqi);
    }
    tr.nested th.name {
      padding-inline-start: calc(6px + var(--depth, 0) * 1.2em);
    }
    .nested-note {
      font-size: 0.85em;
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
