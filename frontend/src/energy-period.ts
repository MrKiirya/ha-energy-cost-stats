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
const HALF_DAY_MS = 12 * 3_600_000;

/** Connection property names to look at, most specific first. */
export function collectionProperties(
  collectionKey: string | undefined,
  pathname: string,
): string[] {
  if (collectionKey) return [`_${collectionKey}`];
  const panelUrl = pathname.split("/").filter(Boolean)[0];
  return panelUrl ? [`_${PREFIX}${panelUrl}`] : [];
}

function isCollection(value: unknown): value is EnergyCollectionLike {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<EnergyCollectionLike>;
  return candidate.start instanceof Date && typeof candidate.subscribe === "function";
}

export function findEnergyCollection(
  connection: unknown,
  collectionKey: string | undefined,
  pathname: string,
): EnergyCollectionLike | undefined {
  if (!connection || typeof connection !== "object") return undefined;
  for (const property of collectionProperties(collectionKey, pathname)) {
    const value = (connection as Record<string, unknown>)[property];
    if (isCollection(value)) return value;
  }
  return undefined;
}

/**
 * The collection's range as calendar dates in `timeZone`. HA keeps `start` at a
 * midnight and `end` at the end of the last day (`23:59:59.999`) — in the
 * browser's or the server's time zone, depending on the user's profile — and an
 * open `end` means "until now". Reading the dates 12 hours inside the range makes
 * the result independent of which of those zones HA used (offsets differ by less
 * than 12 h in practice). Returns `undefined` for an unusable range.
 */
export function collectionPeriod(
  data: { start: Date; end?: Date },
  timeZone: string | undefined,
): Period | undefined {
  if (!(data.start instanceof Date) || Number.isNaN(data.start.getTime())) return undefined;
  const start = todayIn(timeZone, new Date(data.start.getTime() + HALF_DAY_MS));
  const end =
    data.end instanceof Date && !Number.isNaN(data.end.getTime())
      ? todayIn(timeZone, new Date(data.end.getTime() - HALF_DAY_MS))
      : todayIn(timeZone);
  return end < start ? undefined : { start, end };
}
