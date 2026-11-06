/**
 * Report JSON contract (schema_version 1, docs/SPEC.md §4) and the websocket call.
 * Decimals arrive as strings; the card only converts them to numbers for display.
 */

import type { Grouping, Period } from "./period";
import { requestEnd } from "./period";

export type RowStatus = "complete" | "estimated" | "partial" | "missing";

export interface ZoneCell {
  key: string;
  kwh: string | null;
  cost: string | null;
  price: string | null;
}

export interface Coverage {
  expected: number;
  measured: number;
  estimated: number;
  excluded: number;
  missing: number;
}

export interface Row {
  entity_id: string | null;
  kwh: string | null;
  cost: string | null;
  unpriced_kwh: string;
  estimated_kwh: string;
  excluded_kwh: string;
  status: RowStatus;
  coverage: Coverage;
  zones: ZoneCell[];
}

export interface Bucket {
  start: string;
  end: string;
  hours: number;
  rows: Row[];
  total: Row;
}

export interface Issue {
  kind: "estimated" | "excluded_negative" | "excluded_spike" | string;
  entity_id: string;
  start: string;
  end: string;
  hours: number;
  kwh: string;
}

export interface ReportDocument {
  schema_version: number;
  time_zone: string;
  currency: string | null;
  start: string;
  end: string;
  grouping: Grouping;
  zones: { key: string; name: string }[];
  plans: { valid_from: string; name: string }[];
  devices: { entity_id: string; name: string; statistics: string }[];
  buckets: Bucket[];
  totals: Bucket;
  unpriced_hours: number;
  issues: Issue[];
}

export const WS_TYPE_REPORT = "energy_cost_stats/report";
export const WS_TYPE_COMPARE = "energy_cost_stats/compare";

export const SCENARIO_PRESETS = ["single_rate", "ru_two_zone", "ru_three_zone"] as const;

/** A tariff scenario as written in the card config (prices may be YAML numbers). */
export interface ScenarioConfig {
  name?: string;
  preset: (typeof SCENARIO_PRESETS)[number];
  prices: Record<string, string | number>;
  periods?: Record<string, string>;
}

/** `energy_cost_stats/compare` result (SPEC §4.2): grouping `total` documents. */
export interface ComparisonDocument {
  actual: ReportDocument;
  scenarios: { name: string; preset: string; report: ReportDocument }[];
}

/** The minimal slice of the `hass` object the card uses. */
export interface HassLike {
  callWS<T>(msg: Record<string, unknown>): Promise<T>;
  language?: string;
  locale?: { language?: string };
  config?: { time_zone?: string; currency?: string };
}

export interface ReportQuery {
  period: Period;
  grouping: Grouping;
  entities?: string[];
  /** Time zone for "today" and the current hour (the report's, else HA's). */
  timeZone?: string;
  now?: Date;
}

export function reportMessage(query: ReportQuery): Record<string, unknown> {
  const msg: Record<string, unknown> = {
    type: WS_TYPE_REPORT,
    start: query.period.start,
    end: requestEnd(query.period, query.timeZone, query.now),
    grouping: query.grouping,
  };
  if (query.entities && query.entities.length > 0) {
    msg.entities = query.entities;
  }
  return msg;
}

export function fetchReport(hass: HassLike, query: ReportQuery): Promise<ReportDocument> {
  return hass.callWS<ReportDocument>(reportMessage(query));
}

/** Error code of a failed websocket call (`{code, message}` from HA), if any. */
export function errorCode(err: unknown): string | undefined {
  if (err && typeof err === "object" && "code" in err) {
    const code = (err as { code: unknown }).code;
    return typeof code === "string" ? code : undefined;
  }
  return undefined;
}

export function errorText(err: unknown): string {
  if (err && typeof err === "object" && "message" in err) {
    return String((err as { message: unknown }).message);
  }
  return String(err);
}

export interface ComparisonQuery {
  period: Period;
  entities?: string[];
  timeZone?: string;
  now?: Date;
  scenarios: ScenarioConfig[];
}

/** Scenario as sent: prices as decimal strings (money never as a JSON float). */
export function scenarioMessage(scenario: ScenarioConfig): Record<string, unknown> {
  const msg: Record<string, unknown> = {
    preset: scenario.preset,
    prices: Object.fromEntries(
      Object.entries(scenario.prices).map(([key, value]) => [key, String(value)]),
    ),
  };
  if (scenario.name) msg.name = scenario.name;
  if (scenario.periods) msg.periods = scenario.periods;
  return msg;
}

export function comparisonMessage(query: ComparisonQuery): Record<string, unknown> {
  const msg: Record<string, unknown> = {
    type: WS_TYPE_COMPARE,
    start: query.period.start,
    end: requestEnd(query.period, query.timeZone, query.now),
    scenarios: query.scenarios.map(scenarioMessage),
  };
  if (query.entities && query.entities.length > 0) {
    msg.entities = query.entities;
  }
  return msg;
}

export function fetchComparison(
  hass: HassLike,
  query: ComparisonQuery,
): Promise<ComparisonDocument> {
  return hass.callWS<ComparisonDocument>(comparisonMessage(query));
}
