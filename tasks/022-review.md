# 022 — Review (round 1)

Verdict: CHANGES_REQUESTED

## Checks run
- `npm test` (in `frontend/`, devcontainer) → `Test Files 4 passed (4)`, `Tests 121 passed (121)`
- `npm run typecheck` → `tsc --noEmit`, no errors
- `npm run check-bundle` → `Card bundle is up to date.`
- `uv run --no-sync ruff check .` → `All checks passed!`
- `uv run --no-sync ruff format --check .` → `114 files already formatted`
- `uv run --no-sync pytest -m unit -q` → `506 passed, 411 deselected`
- `LovelaceGridOptions` in `home-assistant/frontend` at tag `20250411.0` (`src/panels/lovelace/types.ts`) →
  `columns?: number | "full"` and `getGridOptions?(): LovelaceGridOptions` confirmed.

## Acceptance criteria
- [x] All tests written and green — 121 tests pass; the listed card tests exist (`comparison`, `layout`,
  `nested devices`, `hass updates`) plus `compare.test.ts` for `difference`, `orderNested` and `hassChanged`. The
  stale-compare, grouping-without-compare, unknown-command and `render`-spy tests fail without the corresponding
  code. The implementation notes state that the pure helpers were written before their unit tests.
- [x] `npm run typecheck` → no errors.
- [x] Bundle rebuilt; `npm run check-bundle` passes.
- [x] No `compare` option on `CardConfig`; `setConfig` only additionally clears `_compare`.
- [x] `getGridOptions` returns `{columns: "full", min_columns: 6}`; the source is recorded and was independently
  confirmed (see Checks run).
- [x] `hassChanged` is a pure helper (`frontend/src/hass.ts`) with unit tests for first set, language, locale
  language and time zone. A grep of `this.hass` in `card.ts` shows the card reads only `locale.language` /
  `language`, `config.time_zone` and `callWS`; currency comes from the report, theme and dark mode reach the card
  through inherited CSS custom properties, and the user / number-format settings are not read. Lit's generated
  accessor stores the new value before `hasChanged` is consulted, so `callWS` always uses the newest `hass`
  (asserted by the test).
- [x] Python unit tests and ruff green, unchanged (run above; the box in the task file is still unchecked).
- [x] SPEC §4.1 describes the comparison, full width, separators, wrapped name column, nested rows and the gate.
- [ ] Manual: full width in a sections dashboard — open (not verifiable here).
- [ ] Manual: phone-width layout — open; see Suggestion 1.
- [ ] Manual: dropdowns stay open in a regular desktop browser — open.
- [ ] Manual: comparison with an empty and a one-tariff compare list — open.

## Findings
### Required
1. `frontend/src/card.ts:212` and `:264` — the loading indicator covers only the report request. `_load()` starts
   `_loadCompare()` and `_loadReport()` in parallel, `_loading` is set and cleared only by the report, and the
   previous `_compare` is kept until the new response arrives. Compare prices the same hours once per compared
   tariff, so it will usually finish after the report. After a period change (arrows, preset, custom range) or a
   card `entities` change, the card then shows the new period's device table, no loading indicator, and the
   *previous* period's comparison figures under it. The new numbers arrive later without any visual cue, and
   nothing shows that they were stale before. Fix direction: track compare in-flight state (for example a
   `_compareLoading` flag guarded by `_compareSeq`) and either keep the header indicator up until both requests
   have settled, or dim/mark the comparison section while it loads. Clearing `_compare` when a new period starts
   is another option, but it makes the section jump. Add a card test: the report resolves, the compare call stays
   pending after `button.prev`, and the card must not show the old comparison as current (indicator still shown,
   or the section marked as loading).

### Suggestions
1. `frontend/src/card.ts:922` — `max-width` on table cells has undefined effect in CSS table layout and is
   ignored by some engines. With `overflow-wrap: anywhere` the name cells' min-content width is about one
   character. On a phone the table overflows and is laid out at its min-content width, so the name column ends up
   as wide as the longest no-wrap header word ("Device"), whatever the 35cqi limit says. The manual 360–390 px
   check should confirm the result. If the column turns out too narrow, add a real floor (`min-width: 6.5em` on
   body/footer `th.name`), or put the width limit on an inner block element instead of the cell.
2. `frontend/src/card.ts:548` — the comparison table's first column header repeats the section title ("Tariff
   comparison") right under the `h3`. It is also `nowrap`, so on narrow screens this long phrase sets the sticky
   column's minimum width. A short "Tariff" label (EN/RU) would read better.
3. `frontend/src/card.ts:493` — on nested rows the `title` replaces the device name with the
   "Measured inside …" text. Since wrapping keeps the name readable this is acceptable, but
   "{label} — Measured inside {name}; …" would keep the "full name as title" rule on every row.
4. `frontend/src/card.ts:572` — when `actual.unpriced_hours > 0` but the tariff has none, the badge says "{hours}
   h not priced by this tariff", which is wrong for that case (the actual schedule left them unpriced). Consider a
   separate string for actual-side gaps, or a badge on the "Actual" row.
5. Tests — the task lists the time-zone retry and the 10-minute timer as compare re-send triggers, but no test
   covers them. Consider asserting two compare calls in the existing "asks again in the integration's time zone"
   test. There is no timer test at all; one would need fake `setInterval`.
6. `_errorMessage` does not map `unknown_tariff` (SPEC §4.2). This only happens with a stale configured list, and
   the raw message is an acceptable fallback, but a translated string would match the other errors.
7. `tasks/022-card-comparison.md:207` — "(planner's defaults, may change in review)" is a workflow remark.
   "Open-question defaults as listed above" says the same in a neutral tone. Lines 83/158/168 name a specific
   compositor session type. That is technical context and acceptable, but "a nested compositor session" would
   be more generic.

# 022 — Review (round 2)

Verdict: APPROVE

## Checks run
- `npm test` (in `frontend/`, devcontainer) → `Test Files 4 passed (4)`, `Tests 127 passed (127)`
- `npm run typecheck` → `tsc --noEmit`, no errors
- `npm run check-bundle` → `Card bundle is up to date.`

## Previous required items
1. Resolved. `_loadCompare` sets `_compareLoading` and clears it in `finally` only when `seq === _compareSeq`, so a
   stale response cannot end the newer request's loading state. While a compare request is pending, the comparison
   section gets the `loading` class and `aria-busy="true"`, its table is dimmed, and the heading shows a
   `role="status"` "Loading…" label. On the first load the section is not rendered until a response arrives, so no
   stale data is ever presented as current. The new test ("marks the comparison as loading while a slower compare is
   pending") resolves the report, keeps the second compare pending after `button.prev` and asserts the marked
   section; then it resolves the compare and asserts the new data with the mark cleared. Without the flag this test
   fails.

## Round 1 suggestions
- 1: body/footer `th.name` now has `min-width: 6.5em` next to the `max-width` limit. The phone-width result is still
  a manual criterion.
- 2: the comparison table's first column header is "Tariff" / "Тариф" (tested).
- 3: the nested-row `title` is "{name} — Measured inside {upstream}; …" (tested).
- 4: `compare.unpriced_actual` (EN/RU) is used when only the actual schedule has unpriced hours.
- 5: tests for the compare re-send on the time-zone retry and on the 10-minute timer (fake `setInterval`).
- 6: `unknown_tariff` is mapped to a translated string (EN/RU, tested).
- 7: the implementation-notes wording is neutral.

No regressions found: grouping changes still send only the report, error isolation and the `unknown_command`
hiding are unchanged, and the bundle matches the sources.

## Findings
### Required
None.
### Suggestions
1. `frontend/test/card.test.ts` — the timer test calls `settle(hass as never)`. It passes, but `settle` expects
   the card element. Use the mounted `card` so the helper is used as intended.
2. No card test covers the `compare.unpriced_actual` tooltip (the actual schedule has unpriced hours, the tariff
   has none). A test like the existing "warns when a tariff leaves hours unpriced" would pin it.
3. `frontend/test/card.test.ts:760` — `querySelector(".loading")` can now also match the comparison's loading
   label. `.header .loading` would keep the assertion about the header indicator.
