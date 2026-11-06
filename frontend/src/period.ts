/**
 * Calendar periods for the card's period picker.
 *
 * A period is a closed range of local calendar dates `[start, end]` as
 * `YYYY-MM-DD` strings; the report request uses `end + 1 day` as its exclusive
 * end (docs/SPEC.md §2: a date bound means local midnight in the settings
 * time zone). All arithmetic here is on calendar dates only, so it is free of
 * time zones and DST: dates are carried as UTC midnights internally.
 *
 * Arrow navigation follows Home Assistant's energy period selector
 * (frontend `shiftDateRange`): a range of whole calendar months moves by its
 * length in months (month, quarter, year, 12 months), any other range moves by
 * its length in days (day, week, custom). Weeks start on Monday, like the
 * engine's weekly grouping (SPEC §5).
 */

export interface Period {
  start: string;
  end: string;
}

export const PRESETS = [
  "today",
  "yesterday",
  "this_week",
  "last_week",
  "this_month",
  "last_month",
  "this_quarter",
  "this_year",
  "now-7d",
  "now-30d",
  "now-12m",
] as const;

export type Preset = (typeof PRESETS)[number];

/** What a period looks like, for labels and the "now" button. */
export type PeriodKind =
  | "day"
  | "week"
  | "month"
  | "quarter"
  | "year"
  | "months"
  | "days";

const DAY_MS = 86_400_000;

function parse(date: string): Date {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date);
  if (!match) {
    throw new Error(`invalid date: ${date}`);
  }
  const [, y, m, d] = match;
  return new Date(Date.UTC(Number(y), Number(m) - 1, Number(d)));
}

function format(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function isValidDate(date: string): boolean {
  try {
    return format(parse(date)) === date;
  } catch {
    return false;
  }
}

export function addDays(date: string, days: number): string {
  return format(new Date(parse(date).getTime() + days * DAY_MS));
}

/** First day of the month `months` months after the month of `date`. */
function monthStart(date: string, months = 0): string {
  const d = parse(date);
  return format(new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + months, 1)));
}

/** Last day of the month `months` months after the month of `date`. */
function monthEnd(date: string, months = 0): string {
  const d = parse(date);
  return format(new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + months + 1, 0)));
}

/** Monday of the week containing `date`. */
function weekStart(date: string): string {
  const weekday = (parse(date).getUTCDay() + 6) % 7; // Monday = 0
  return addDays(date, -weekday);
}

/** Number of days in `[start, end]`. */
export function dayCount(period: Period): number {
  return Math.round((parse(period.end).getTime() - parse(period.start).getTime()) / DAY_MS) + 1;
}

/** Number of calendar months in `[start, end]` when both ends are month bounds. */
function wholeMonths(period: Period): number | null {
  const start = parse(period.start);
  if (start.getUTCDate() !== 1 || monthEnd(period.end) !== period.end) {
    return null;
  }
  const end = parse(period.end);
  return (
    (end.getUTCFullYear() - start.getUTCFullYear()) * 12 +
    (end.getUTCMonth() - start.getUTCMonth()) +
    1
  );
}

/** Today's date in an IANA time zone (falls back to the browser's zone). */
export function todayIn(timeZone: string | undefined, now: Date = new Date()): string {
  const options: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  };
  let parts: Intl.DateTimeFormatPart[];
  try {
    parts = new Intl.DateTimeFormat("en-CA", { ...options, timeZone }).formatToParts(now);
  } catch {
    parts = new Intl.DateTimeFormat("en-CA", options).formatToParts(now);
  }
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? "";
  return `${get("year")}-${get("month")}-${get("day")}`;
}

export function presetPeriod(preset: Preset, today: string): Period {
  switch (preset) {
    case "today":
      return { start: today, end: today };
    case "yesterday": {
      const day = addDays(today, -1);
      return { start: day, end: day };
    }
    case "this_week": {
      const start = weekStart(today);
      return { start, end: addDays(start, 6) };
    }
    case "last_week": {
      const start = addDays(weekStart(today), -7);
      return { start, end: addDays(start, 6) };
    }
    case "this_month":
      return { start: monthStart(today), end: monthEnd(today) };
    case "last_month":
      return { start: monthStart(today, -1), end: monthEnd(today, -1) };
    case "this_quarter": {
      const month = parse(today).getUTCMonth();
      const first = monthStart(today, -(month % 3));
      return { start: first, end: monthEnd(first, 2) };
    }
    case "this_year": {
      const year = today.slice(0, 4);
      return { start: `${year}-01-01`, end: `${year}-12-31` };
    }
    case "now-7d":
      return { start: addDays(today, -6), end: today };
    case "now-30d":
      return { start: addDays(today, -29), end: today };
    case "now-12m":
      return { start: monthStart(today, -11), end: monthEnd(today) };
  }
}

export function periodKind(period: Period): PeriodKind {
  const months = wholeMonths(period);
  if (months !== null) {
    const startMonth = parse(period.start).getUTCMonth();
    if (months === 1) return "month";
    if (months === 3 && startMonth % 3 === 0) return "quarter";
    if (months === 12 && startMonth === 0) return "year";
    return "months";
  }
  const days = dayCount(period);
  if (days === 1) return "day";
  if (days === 7 && weekStart(period.start) === period.start) return "week";
  return "days";
}

/** The period one step earlier (`-1`) or later (`+1`), keeping its length. */
export function shiftPeriod(period: Period, direction: 1 | -1): Period {
  const months = wholeMonths(period);
  if (months !== null) {
    const step = months * direction;
    return { start: monthStart(period.start, step), end: monthEnd(period.end, step) };
  }
  const step = dayCount(period) * direction;
  return { start: addDays(period.start, step), end: addDays(period.end, step) };
}

/**
 * The period of the same kind and length that contains today
 * (Home Assistant's "now" button).
 */
export function currentPeriod(period: Period, today: string): Period {
  const kind = periodKind(period);
  switch (kind) {
    case "day":
      return presetPeriod("today", today);
    case "week":
      return presetPeriod("this_week", today);
    case "month":
      return presetPeriod("this_month", today);
    case "quarter":
      return presetPeriod("this_quarter", today);
    case "year":
      return presetPeriod("this_year", today);
    case "months": {
      const months = wholeMonths(period) ?? 1;
      return { start: monthStart(today, -(months - 1)), end: monthEnd(today) };
    }
    case "days":
      return { start: addDays(today, -(dayCount(period) - 1)), end: today };
  }
}

/** True when the period contains `today` (it may still grow). */
export function containsDate(period: Period, date: string): boolean {
  return period.start <= date && date <= period.end;
}

/** Exclusive end bound for the report request. */
export function exclusiveEnd(period: Period): string {
  return addDays(period.end, 1);
}

/**
 * The `end` bound to request. For a period that contains today it is the start
 * of the current local hour (an ISO datetime with the zone's UTC offset), so
 * the hours that have not happened yet are not
 * reported as missing data; the period's `[start, end]` dates stay as chosen.
 * Otherwise (or in a zone with a non-whole-hour UTC offset, where the backend
 * would reject such a bound) it is the exclusive end date.
 */
export function requestEnd(
  period: Period,
  timeZone: string | undefined,
  now: Date = new Date(),
): string {
  const today = todayIn(timeZone, now);
  if (!containsDate(period, today)) return exclusiveEnd(period);
  let parts: Intl.DateTimeFormatPart[];
  try {
    parts = new Intl.DateTimeFormat("en-GB", {
      timeZone,
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    }).formatToParts(now);
  } catch {
    return exclusiveEnd(period);
  }
  const hour = Number(parts.find((p) => p.type === "hour")?.value);
  const minute = Number(parts.find((p) => p.type === "minute")?.value);
  if (!Number.isFinite(hour) || minute !== now.getUTCMinutes()) {
    return exclusiveEnd(period);
  }
  // In the first hour of the period's first day there is no finished hour yet:
  // ask for that hour (it shows as not compiled yet) rather than an empty range.
  const endHour = period.start === today ? Math.max(hour, 1) : hour;
  // Explicit UTC offset of that local hour: during a DST fall-back the repeated
  // hour would be ambiguous as a naive local time.
  const offset = utcOffset(timeZone, now, endHour - hour);
  return `${today}T${String(endHour).padStart(2, "0")}:00:00${offset}`;
}

/** `+HH:MM` offset of `timeZone` at `now` shifted by `hours` hours. */
function utcOffset(timeZone: string | undefined, now: Date, hours: number): string {
  const at = new Date(now.getTime() + hours * 3_600_000);
  const name =
    new Intl.DateTimeFormat("en-US", { timeZone, timeZoneName: "longOffset" })
      .formatToParts(at)
      .find((p) => p.type === "timeZoneName")?.value ?? "GMT";
  const match = /^GMT([+-]\d{2}):?(\d{2})?$/.exec(name);
  if (!match) return "+00:00";
  return `${match[1]}:${match[2] ?? "00"}`;
}

export type Grouping = "hour" | "day" | "week" | "month" | "total";

/** Hourly reports are limited to 31 days by the backend (SPEC §2). */
export const MAX_HOURLY_DAYS = 31;

/** The grouping the card picks when the user leaves it on "auto". */
export function autoGrouping(period: Period): Grouping {
  const days = dayCount(period);
  if (days <= 2) return "hour";
  if (days <= 45) return "day";
  if (days <= 120) return "week";
  return "month";
}

export function groupingAllowed(grouping: Grouping, period: Period): boolean {
  return grouping !== "hour" || dayCount(period) <= MAX_HOURLY_DAYS;
}
