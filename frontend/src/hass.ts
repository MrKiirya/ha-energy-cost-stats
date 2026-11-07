/** Update gate for the `hass` property. */

import type { HassLike } from "./report";

/**
 * Home Assistant assigns a new `hass` object on every state change of any entity. The
 * card reads only the language, the time zone and `callWS`, so it re-renders only when
 * one of those differs. (The newest object is still stored, so `callWS` stays current.)
 */
export function hassChanged(next?: HassLike, prev?: HassLike): boolean {
  if (prev === undefined || next === undefined) return next !== prev;
  return (
    next.language !== prev.language ||
    next.locale?.language !== prev.locale?.language ||
    next.config?.time_zone !== prev.config?.time_zone
  );
}
