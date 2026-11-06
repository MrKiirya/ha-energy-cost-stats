# 015 — Review (round 2)

Verdict: CHANGES_REQUESTED

Scope reviewed: `git diff task/014-cost-card..HEAD` (commits 8b348f9, 1d346a4, 26343ad, 272de3c, 99106ec);
round-1 fixes in 99106ec (`git show HEAD`).

## Checks run
- `sh script/test` (ecs-dev, HEAD 99106ec) → `538 passed in 90.32s`; total coverage 100.00 %
  (`engine/scenario.py` 81 stmts, 30 branches, 100 %).
- `sh script/lint` → `All checks passed!` / `88 files already formatted`.
- `uv run --group ha pyright` → `0 errors, 0 warnings, 0 informations`.
- `npx vitest run` → `Tests 99 passed (99)`; `npx tsc --noEmit` → clean; `npm run check-bundle` → `Card bundle is up to date.`
- Hygiene: added lines contain only `sensor.plug_01` / `sensor.other`; none of the 36 entity ids in
  `tests/fixtures/private/ha_energy_statistics.csv` occurs in the diff (bundle included); no paths, hosts or secrets.
- HA 2025.4.0 leg: not run locally (CI).

## Round-1 required items
1. Incomplete current tariff used for "best" and differences — **resolved.** `card.ts:664-669` defines
   `actualComplete` (cost not null, `unpriced_hours === 0`, plans present); the current row is excluded from the
   minimum (`:686`) and from `best` (`:709-713`), differences are `—` when incomplete (`:714-717`), the warning
   uses the same condition (`:743`). Test `does not compare against an incomplete current tariff` would fail
   without the change (actual 10.00 would be cheapest and differences shown).
2. Comparison sequencing / stale numbers — **resolved for period and grouping changes**: the comparison is now
   keyed by `[period, entities]` (`card.ts:256-265`), the old result/error is cleared when the key changes, and the
   grouping race is covered by `requests the new period's comparison even if the grouping changed meanwhile`
   (exactly 2 compare calls, second for 2026-10-01..2026-11-01) and `clears the previous period's comparison until
   the new one arrives`. However the new key introduced a regression for config edits — see required item 1 below.

## Round-1 suggestions
1. Localized default scenario name — applied in the card (`presetName`, test in Russian). SPEC §4.2 still does not
   state the default name (see suggestion 2).
2. Comparison uses the report request's `end` — applied (`card.ts:236, 265`, `report.ts:171`), tested.
3. Zone kWh matched by key — applied (`card.ts:720`).
4. `periods` must be a mapping when given — applied (`scenario.py:87-89`), `""` and `[]` tested.
5. `MAX_SCENARIOS` constant in the card — applied, and a unit test checks it against the engine's value.
6. `test_max_scenarios_is_small` — replaced by the cross-check test.

## Acceptance criteria
- [x] `script/test` 535+ passed, engine coverage ≥ 95 %, `scenario.py` 100 %, lint clean, pyright 0 — verified (538).
- [x] Card: vitest 99 passed, `tsc` clean, bundle up to date — verified.
- [ ] Dev HA with real statistics, current tariff total equals the main table total — not independently verified
  (dev HA needs an auth token the reviewer did not create). Backend side covered by
  `test_compare_prices_the_same_consumption`; with the shared `end` the card no longer straddles an hour.
- [ ] CI green on the PR — not yet (no PR / CI run to check).

## Findings
### Required
1. `frontend/src/card.ts:152-160` (with `:256-265`) — editing the card config in the dashboard editor leaves the
   comparison stuck. `setConfig` on an edit clears `_comparison` but not `_comparisonKey` (nor
   `_comparisonError`). The period is then re-created from the configured preset; when it is the same period and
   the same `entities` (the usual case: the user tunes a scenario price or adds a scenario), the key is unchanged,
   `_load()` runs with `refresh = false`, so no compare request is sent and `_renderComparison` shows
   "Loading…" indefinitely (closed periods have no refresh tick; only the refresh button recovers). If the previous
   comparison failed with `invalid_scenario`, fixing the scenario keeps showing the old error the same way. Round 1
   did not have this (a period change always re-requested). Fix direction: in `setConfig` on an edit reset
   `_comparisonKey = undefined` and `_comparisonError = undefined` (and arguably include `compare` in the key, so
   the key describes the request that produced the shown comparison). Add a card test: mount with `compare`, call
   `setConfig` again with a changed price and the same period → a second compare call is sent and its rows render.

### Suggestions
1. `frontend/src/card.ts:152-160` — while fixing the above: an in-flight comparison from the old config can still
   land after the edit (its `_comparisonSeq` is still current); the key reset plus the new request bumps the
   sequence and discards it — worth asserting in the same test.
2. `docs/SPEC.md` §4.2 "Card" — document the round-1 behaviour: when the current tariff is incomplete (unpriced
   hours or no plan) it gets no "best" badge and scenarios show no difference, with a warning; an unnamed scenario
   is shown by its localized preset name (the response `name` is the English plan name). Also "re-requested when
   the period changes" now reads "when the period or sensors change, or on refresh".
