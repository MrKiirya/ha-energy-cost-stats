# 016 — Review (round 2)

Verdict: APPROVE

Scope reviewed: `git diff task/015-tariff-comparison..HEAD` (commits 6195618, edef524); round-1 fixes in edef524
(`git show HEAD`). Re-checked against HA frontend `dev` (2026-11-06): `src/data/energy.ts`,
`src/data/energy-collection-controller.ts`, `src/common/datetime/calc_date.ts`, `resolve-time-zone.ts`.

## Checks run
- `npx vitest run` (ecs-dev, container TZ = UTC) → `Tests 116 passed (116)` (energy-period.test.ts: 16).
- Same suite with `TZ=America/New_York` → `Tests 116 passed (116)`; `energy-period.test.ts` with `TZ=UTC` → 16 passed
  (the card tests do not depend on the machine's zone).
- `npx tsc --noEmit` → clean; `npm run check-bundle` → `Card bundle is up to date.`
- Python: no Python files in the diff; `sh script/lint` was `All checks passed!` in round 1, not re-run.
- Hygiene: no entity ids, personal data, paths or secrets in the added lines.

## Round-1 required items
1. Config edits did not re-evaluate the followed collection — **resolved.** `setConfig` now calls `_detachEnergy()`
   and clears `_energyBroken` when a previous config exists (`card.ts:188-192`); `willUpdate` re-attaches before the
   preset fallback, so the period is re-read from the collection rather than from `config.period`. Test
   `re-attaches after config edits` covers a title edit (still following, one listener, Oct period), a
   `collection_key` change (old listener removed, new one added, Sep period) and switching to `card` (no listener,
   own picker, configured preset). It would fail without the change (listener count and period assertions).
2. Every HA energy card creates the collection — **resolved** by making following opt-in: `period_source` is
   `card` (default) / `energy`; `_attachEnergy` returns unless `energy` (`card.ts:273`). Test
   `keeps its own picker by default, even when an energy collection exists`. SPEC §4.1 and the task's open question
   explain why, and that true picker detection is left to the author. (`auto` is now rejected; the feature was never
   released, so no migration is needed.)
3. The 12 h rule broke for zones 12 h or more apart — **resolved.** `pickerTimeZone` returns `hass.config.time_zone`
   for profile `server` and `undefined` (browser) otherwise, the same choice HA's `calcDate` makes
   (`locale.time_zone === TimeZone.server ? zoned : native`); `collectionPeriod` reads the bounds' own calendar dates
   in that zone, which is exact and DST-safe because HA computes them there with `startOfDay`/`endOfDay`. Tests use
   Honolulu and Tokyo bounds (the round-1 failing cases) plus the profile-setting mapping; the card tests use
   `time_zone: "server"` with Moscow bounds. SPEC wording is now accurate.

Round-1 suggestions applied: `hass.panelUrl` with path fallback (`dashboardPath`), no retry after `subscribe()` threw
(test `does not retry a collection whose subscribe() throws`), `collection_key` must start with `energy_`.

## Acceptance criteria
- [x] vitest 116 passed, tsc clean, bundle up to date — verified (above).
- [ ] Dev HA 2026.9 `vertical-stack` + Playwright — not independently verified (no screenshots/script in the diff;
      the review does not drive the browser). Key lookup and the payload shape match HA `dev`, so it is plausible;
      note the check must now use `period_source: energy`.
- [ ] CI green on the PR — not checked by the review.

## Findings
### Required
None.

### Suggestions
1. `frontend/src/card.ts:113` — the comment still says "period_source auto/energy"; `auto` is gone.
2. `tasks/016-energy-period-sync.md:31` — the tests table still describes the round-0 behaviour ("UTC+5 / UTC−5
   browser vs Moscow report", "`period_source: card` ignores it"); update to the opt-in default and the
   picker-zone tests.
3. Carried over from round 1 (still open, non-blocking): HA notifies subscribers only after its energy fetch
   publishes, so a failing fetch leaves the card on the old period — re-reading `collection.start/end` on `hass`
   updates while following would cover it; the own picker briefly shows after a reconnect until the next `hass`
   update; no test pins a picker change with `compare` configured or the auto-refresh while following (both correct
   by reading).
4. With `period_source: energy` on a dashboard that has another energy card but no date picker, the card still
   follows HA's default period with no picker; the SPEC now says presence is not proof — a one-line hint in the
   `energy_picker_followed` tooltip or the README ("add the Energy date selection card") would help users.
