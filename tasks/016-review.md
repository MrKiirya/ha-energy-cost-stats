# 016 — Review (round 1)

Verdict: CHANGES_REQUESTED

Scope reviewed: `git diff task/015-tariff-comparison..HEAD` (commit 6195618). Compared against HA frontend `dev`
(fetched 2026-11-06): `src/data/energy.ts` (`ENERGY_COLLECTION_KEY_PREFIX`, `convertCollectionKeyToConnection`,
`getEnergyDataCollection`), `src/data/energy-collection-controller.ts`,
`src/panels/lovelace/cards/energy/hui-energy-{date-selection,distribution}-card.ts`.

## Checks run
- `npx vitest run` (ecs-dev) → `Test Files 5 passed (5)` / `Tests 113 passed (113)` (energy-period.test.ts: 13).
- `npx tsc --noEmit` → clean; `npm run check-bundle` → `Card bundle is up to date.`
- `sh script/lint` → `All checks passed!` / `89 files already formatted` (no Python changed in this diff).
- 12 h heuristic probe (`node -e` with `Intl`, in ecs-dev): picker bounds for 2026-11-06 in
  `Pacific/Honolulu` → report zone `Europe/Moscow` gives `2026-11-07..2026-11-07`; `America/New_York` →
  `Asia/Tokyo` gives `2026-11-07..2026-11-07` (expected `2026-11-06`). See required item 3.
- Hygiene: no entity ids, paths, hosts or secrets in the added lines.

## Acceptance criteria
- [x] vitest 113 passed, tsc clean, bundle up to date — verified (above).
- [ ] Dev HA 2026.9 `vertical-stack` + Playwright screenshots — not independently verified: no screenshots or
      script are in the diff and this review does not drive the browser. Key derivation itself matches HA `dev`
      (see below), so the claim is plausible.
- [ ] CI green on the PR — not checked (no `gh` in review).

Key derivation verified: HA uses `connection["_" + collection_key]`, else `"_energy_" + panelUrl`, else `"_energy"`;
`collectionProperties` (`energy-period.ts:27-35`) matches the first two (the bare `_energy` case only occurs with an
empty panelUrl, fine to skip). The subscribed payload is `EnergyData` with `start`/`end`, as assumed.

## Findings
### Required
1. `frontend/src/card.ts:178-191` with `:238-246` — **config edits do not re-evaluate the followed collection.**
   `setConfig` resets `_period` to undefined but leaves `_energy`/`_unsubEnergy` in place, so `willUpdate` skips
   `_attachEnergy` and recomputes `_period` from `config.period` (default `this_month`) while the card still renders
   the "followed" line (picker hidden). Result after any edit (even the title): the card shows a month while HA's
   picker shows e.g. a day, until the user touches HA's picker. Switching `period_source` to `card` keeps following;
   changing `collection_key` keeps the old collection. HA's own `EnergyCollectionController._subscribe` re-subscribes
   when the key changes. Direction: in `setConfig` (when a previous config exists) call `_detachEnergy()` so the next
   `willUpdate` re-attaches per the new config and re-reads the period from the collection; tests: edit title →
   period still the picker's; `auto` → `card` → own picker, unsubscribed once; `collection_key` change → new
   collection subscribed, old unsubscribed.
2. `frontend/src/energy-period.ts:42-53` / `card.ts:257-283` — **"picker present" is detected by the collection,
   but every HA energy card creates that collection.** `hui-energy-distribution-card`, usage graphs etc. all go
   through `EnergyCollectionController` → `getEnergyDataCollection(... panelUrl ...)` and create
   `_energy_<panelUrl>` without any date-selection card. With the default `period_source: auto`, a dashboard with an
   energy-distribution card but no date picker locks the cost card to HA's default period (today/yesterday or the
   remembered preset) and hides the card's own picker, with no UI to change it. This contradicts SPEC §4.1 ("follows
   … the `energy-date-selection` card … when there is one, and otherwise shows its own picker") and the task goal.
   The collection also outlives its dashboard on the connection (only reached again via the same panelUrl, so less
   severe). Direction (author decision, ties into the open question): make following opt-in (`period_source:
   energy`, default `card`), or keep `auto` but only treat the collection as a picker when the energy date-selection
   card is actually present, or keep the own preset menu available in followed mode. Add a test for "collection
   present, no picker" whatever is chosen, and adjust the SPEC wording.
3. `frontend/src/energy-period.ts:56-74`, `docs/SPEC.md` §4.1 — **the 12 h rule is not zone-independent.** It only
   holds when HA's bound zone and the card's zone differ by < 12 h; the SPEC states unconditionally that it "makes
   the calendar dates independent of that choice". Browser in Honolulu / server or integration zone Moscow, or New
   York / Tokyo, gives the next day for both bounds (probe above) — a silently wrong report. The zone HA used is
   knowable: `hass.locale.time_zone` is `"server"` (→ `hass.config.time_zone`) or `"local"` (→ browser zone); read
   the bounds' calendar dates in that zone (they are exact midnights / 23:59:59.999 there, DST-safe) instead of
   guessing. If kept as is, at least narrow the SPEC claim and the doc comment and add a test documenting the limit.

### Suggestions
1. `card.ts:259-263` — use `hass.panelUrl` (what HA itself keys on via `uiContext`) and fall back to the first
   `location.pathname` segment only when absent; avoids drift if HA's URL → panel mapping changes.
2. `card.ts:266-275` — the subscriber is only called after HA's energy fetch publishes (`publishedSelectionRevision
   === selectionRevision`); if that fetch fails (statistics error), the card never moves. Consider also re-reading
   `collection.start/end` on each `hass` update while following (cheap, no extra request when unchanged).
3. `card.ts:275-281` — if `subscribe` throws, `_energy` is cleared but `follow(collection)` already changed
   `_period`, and the attach is retried (and throws) on every `hass` update. Consider remembering the failed
   collection and not retrying it.
4. `card.ts:241` / disconnect — after `disconnectedCallback` the own picker flashes until the next `hass` update
   re-attaches; harmless, but a `requestUpdate()` in `connectedCallback` would re-attach immediately.
5. `card.ts:154-159` — HA rejects a `collection_key` without the `energy_` prefix
   (`validateEnergyCollectionKey`); mirroring that check gives a clear config error instead of a silent fallback.
6. Tests: no test for a picker change while a comparison is configured (new comparison requested once, old cleared)
   or for the auto-refresh timer while following; both look correct by reading (`_load` keys the comparison by
   period; same-range callbacks from HA's hourly refresh do not change `_period`), but a test would pin it.
7. Subscribing keeps the collection `_active` (HA's hourly refresh keeps running) while the cost card is mounted,
   even if the picker card is gone; acceptable, worth a line in the SPEC note on the internal API.
