/**
 * Follow the period of Home Assistant's own energy date picker
 * (the `energy-date-selection` card) when it is on the same dashboard.
 *
 * The picker keeps its period in an "energy collection" stored on the websocket
 * connection: `connection["_" + collection_key]`, where the key is the card's
 * `collection_key` or, by default, `energy_<dashboard url path>` (HA frontend
 * `src/data/energy.ts`, `convertCollectionKeyToConnection`, checked on `dev`
 * 2026-11-06). This is not a public API: everything here is defensive, and the
 * card falls back to its own picker when no usable collection is found.
 */

import type { Period } from "./period";
import { todayIn } from "./period";

/** The slice of HA's EnergyCollection the card relies on. */
export interface EnergyCollectionLike {
  start: Date;
  end?: Date;
  subscribe(callback: (data: { start: Date; end?: Date }) => void): () => void;
}

const PREFIX = "energy_";

/** Connection property names to look at, most specific first. */
export function collectionProperties(
  collectionKey: string | undefined,
  panelUrl: string | undefined,
): string[] {
  if (collectionKey) return [`_${collectionKey}`];
  return panelUrl ? [`_${PREFIX}${panelUrl}`] : [];
}

/** HA requires custom collection keys to start with `energy_` (validateEnergyCollectionKey). */
export function isValidCollectionKey(key: string): boolean {
  return key.startsWith(PREFIX);
}

/** The dashboard's URL path: `hass.panelUrl`, else the first segment of the page path. */
export function dashboardPath(
  panelUrl: string | undefined,
  pathname: string,
): string | undefined {
  return panelUrl || pathname.split("/").filter(Boolean)[0];
}

function isCollection(value: unknown): value is EnergyCollectionLike {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<EnergyCollectionLike>;
  return candidate.start instanceof Date && typeof candidate.subscribe === "function";
}

export function findEnergyCollection(
  connection: unknown,
  collectionKey: string | undefined,
  panelUrl: string | undefined,
): EnergyCollectionLike | undefined {
  if (!connection || typeof connection !== "object") return undefined;
  for (const property of collectionProperties(collectionKey, panelUrl)) {
    const value = (connection as Record<string, unknown>)[property];
    if (isCollection(value)) return value;
  }
  return undefined;
}

/**
 * The zone HA computed the picker's bounds in: the server's time zone when the
 * user's profile says `server`, else the browser's (`local`, `undefined` here).
 * HA frontend: `calcDate` / `resolveTimeZone`.
 */
export function pickerTimeZone(
  locale: { time_zone?: string } | undefined,
  serverTimeZone: string | undefined,
): string | undefined {
  return locale?.time_zone === "server" ? serverTimeZone : undefined;
}

/**
 * The collection's range as the calendar dates the user picked: HA keeps `start`
 * at a midnight and `end` at the end of the last day (`23:59:59.999`) in
 * `pickerZone` (see `pickerTimeZone`); an open `end` means "until today". The
 * dates are then reported in the integration's time zone like any other period.
 * Returns `undefined` for an unusable range.
 */
export function collectionPeriod(
  data: { start: Date; end?: Date },
  pickerZone: string | undefined,
): Period | undefined {
  if (!(data.start instanceof Date) || Number.isNaN(data.start.getTime())) return undefined;
  const start = todayIn(pickerZone, data.start);
  const end =
    data.end instanceof Date && !Number.isNaN(data.end.getTime())
      ? todayIn(pickerZone, data.end)
      : todayIn(pickerZone);
  return end < start ? undefined : { start, end };
}
