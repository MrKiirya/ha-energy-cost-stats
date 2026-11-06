# 015 — Review (round 1)

Verdict: CHANGES_REQUESTED

Scope reviewed: `git diff task/014-cost-card..HEAD` (commits 8b348f9, 1d346a4, 26343ad, 272de3c).

## Checks run
- `sh script/test` (ecs-dev) → `536 passed in 95.63s`; engine coverage 100.00 % (`engine/scenario.py` 79 stmts, 28 branches, 100 %).
- `sh script/lint` → `All checks passed!` / `87 files already formatted`.
- `uv run --group ha pyright` → `0 errors, 0 warnings, 0 informations`.
- `npx vitest run` → `Tests 93 passed (93)`; `npx tsc --noEmit` → clean; `npm run check-bundle` → `Card bundle is up to date.`
- Hygiene: added lines contain only `sensor.plug_01` / `sensor.other`; none of the 36 entity ids in
  `tests/fixtures/private/ha_energy_statistics.csv` occurs in the diff (bundle included); no paths, hosts or secrets.
- HA 2025.4.0 leg: not run locally (CI).

## Acceptance criteria
- [x] `script/test` 535+ passed, engine coverage ≥ 95 %, `scenario.py` 100 %, lint clean, pyright 0 — verified above (536).
- [x] Card: vitest 93 passed, `tsc` clean, bundle up to date — verified above.
- [ ] Dev HA with real statistics, current tariff total equals the main table total — not independently verified:
  the dev HA answers on :8123 but needs an auth token, which the reviewer did not create. The backend side is
  covered by `test_compare_prices_the_same_consumption` (actual == day report, 600.72). Note required item 2: in
  the card the two totals can disagree after a quick period/grouping change, and suggestion 2 for open periods.
- [ ] CI green on the PR — not yet (no PR / CI run to check).

## What is right
- `engine/scenario.py` is pure (imports only `engine.*` and stdlib), money is `Decimal` via `parse_price`
  (comma accepted, negatives/garbage rejected by the existing regex, floats rejected with "decimal string"),
  exact zone-set check, unknown keys/zones rejected, period overrides parsed with `parse_periods`, coverage
  enforced by `TariffPlan` construction, blank name rejected. `valid_from` 1970-01-01 makes the one-plan schedule
  cover any window.
- `async_get_comparison` does one `_async_prepare` (one `async_read_hourly_changes`, same `QualitySettings`),
  then `build_report` per schedule in one executor job on the same `series` — scenarios price exactly the hours
  the report counts. `async_get_report` behaviour is unchanged by the refactor (existing tests pass).
- Errors: `invalid_scenario` in `const.py`, `ERROR_MESSAGES`, `strings.json` and `translations/en.json` (identical
  files; `test_all_error_codes_translated` extended); the message names the scenario index. Websocket schema
  `scenarios: [dict]`, no `grouping` accepted (`invalid_format` tested), no admin requirement, same as `report`.
- Card request: same `start`, same `requestEnd` rules with the integration's time zone, entities passed, YAML
  numbers stringified (`String(7.5)` → `"7.5"`), comparison skipped without `compare`; tie → no badge;
  percentage = rounded difference / current cost, no % when the base is 0.
- SPEC §4.2 matches the implementation (request/response shape, zone keys, 1–5, `actual` may be partial/null,
  websocket only, card behaviour).

## Findings
### Required
1. `frontend/src/card.ts:657-668, 681-684` — the "best" badge and the differences use the current tariff's cost
   even when it is incomplete. Per SPEC §4 the actual `cost` is the sum over *priced* hours only (non-null as
   soon as one hour is priced), while every scenario prices *all* counted hours. With `unpriced_hours > 0` the
   current tariff is systematically understated, so it can get the "best" badge and every scenario shows as
   "dearer" — a wrong recommendation, only softened by the warning at line 711. Fix direction: when
   `comparison.actual.unpriced_hours > 0` (or `plans` is empty), leave the current row out of the minimum and
   show no difference (`—`) for the scenarios (or compare only scenario vs. scenario); keep the warning. Add a
   card test: actual partial and cheapest → no badge on the current row, differences hidden.
2. `frontend/src/card.ts:213-217, 243-245` — comparison sequencing can lose the request for a new period and
   leaves stale numbers on screen. (a) Change the period, and change the grouping before that report returns:
   the period load (seq N, `withComparison=true`) is discarded by the seq guard, the grouping load (seq N+1)
   runs with `withComparison=false`, so the comparison for the new period is never requested and the previous
   period's comparison stays displayed under the new report indefinitely (until a refresh tick, which only
   happens for open periods). (b) Even without the race, `_comparison` is not cleared when the period changes,
   so the old period's comparison is shown next to the new report until the new response arrives. Fix
   direction: decide on "needs comparison" by a key (period start/end + entities) of the last requested
   comparison rather than by a boolean passed through `_load`, and clear `_comparison`/`_comparisonError` (or
   show loading) when that key changes. Add a test: change period, then grouping before the report resolves →
   exactly one new compare call for the new period and no old numbers rendered.

### Suggestions
1. `custom_components/energy_cost_stats/engine/scenario.py:125` / card — an unnamed scenario is called by the
   preset's English plan name ("Single-rate"), also in the Russian card. The response carries `preset`, so the
   card could localize the default name when the config has no `name` (or the engine could return `name: null`).
   SPEC §4.2 should state the default name either way.
2. `frontend/src/report.ts:165` — the comparison computes its own `end` with a second `new Date()`; for an open
   period (today) the report and the comparison can straddle an hour boundary and the "current tariff" total
   then differs from the main table by the latest hour. Pass the report request's `end` (or `now`) into
   `fetchComparison`.
3. `frontend/src/card.ts:687` — zone kWh are matched to `doc.zones` by index; matching `total.zones` by `key`
   would not depend on the serializer keeping both lists in the same order.
4. `custom_components/energy_cost_stats/engine/scenario.py:87` — `data.get("periods") or {}` silently accepts
   `""`, `[]`, `0` as "no overrides"; `if "periods" in data` plus a mapping check would reject them like other
   wrong types.
5. `frontend/src/card.ts:132` — the 1–5 limit is a literal; export a constant next to `SCENARIO_PRESETS`
   (mirroring `MAX_SCENARIOS`) so the two cannot drift.
6. `tests/unit/test_scenario.py::test_max_scenarios_is_small` asserts little; the real limit is already covered
   by the integration test with 6 scenarios — consider dropping it.
