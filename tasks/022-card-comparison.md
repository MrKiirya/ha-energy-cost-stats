# 022 — Card: tariff comparison, full width, table layout and dropdown fix

Status: in-review (round 1: CHANGES_REQUESTED; round 2: APPROVE; manual browser checks open)
Roadmap: Configuration v2 (docs/CONFIG-DESIGN.md "Tasks", row 022) — stage 4 card follow-up
Spec sections: SPEC §4 (JSON contract, `devices[].upstream`), §4.1 (card), §4.2 (`energy_cost_stats/compare`), §6
(minimum HA version); CONFIG-DESIGN "Applied history and comparison", "Decisions" (no `compare:` on the card)

## Goal
The card shows, for the selected period and the selected sensors, what the consumption actually cost and what it
would have cost under each tariff the integration compares (from `energy_cost_stats/compare`), with the difference.
It takes the full width of its section in sections dashboards by default. The cost table is easier to read: each
zone's sub-columns form a visibly separated group under a centred zone header, the sticky name column no longer eats
the scrollable area on phones, and devices measured inside another device are marked, with a note that the total
does not count them twice. The native dropdowns (period preset, breakdown device, grouping) stay open on desktop
because the card no longer re-renders on unrelated `hass` updates.

## Context
- **No `compare:` card option.** The comparison list is the integration's (`compare` setting; default every tariff
  never applied). The card sends no `tariffs` field; it only passes the card's `entities` (if set), so the section
  respects the selected sensors. CONFIG-DESIGN "Decisions" withdrew card-side tariff scenarios; do not add one.
- **Two requests.** `compare` has no `grouping` (documents are `total`), so it cannot replace `report` (the card needs
  buckets for "by period"). The card sends `report` and `compare` for the same `start` / `end` / `entities`
  (`reportMessage` logic reused: same `requestEnd`, same time zone). `compare` is re-sent on period change, refresh,
  first `hass`, the 10-minute running-period timer and the time-zone retry — **not** on a grouping change. Both
  go through the existing `_requestSeq`-style stale-response guard (a separate sequence for compare is fine).
- **Actual vs. compared.** "Actual" = `compare.actual.totals.total.cost` (same counted kWh and data-quality handling
  as the compared documents, SPEC §4.2). Each compared tariff = `tariffs[i].report.totals.total.cost`.
  Difference = compared − actual (positive = the compared tariff would have cost more), shown as money and percent
  of actual. If either cost is `null` the difference is "—", never 0. Percent is "—" when actual is `0` or `null`.
  Display only: parse the decimal strings for the difference the same way the card already does for the average
  price (no new rounding rules; money via `Strings.money`).
- **Partial pricing.** A compared tariff's hours before its first version are unpriced (§4.2). When
  `tariffs[i].report.unpriced_hours > 0` (or `actual.unpriced_hours > 0`), the row gets a warning badge with a
  tooltip "{hours} h not priced by this tariff — the difference covers only the priced hours" — the comparison is
  then not like-for-like. Rows keep the integration's order (§4.2: requested/configured order).
- **Empty / unavailable states.**
  - `tariffs: []` → muted note "No tariffs to compare. Choose them in the integration options (Configure → Compare)."
  - Error `unknown_command` (older integration without `compare`) → the section is hidden; no error banner.
  - Any other compare error → a one-line error inside the comparison section only; the device table is unaffected.
  - No plan at all (`actual.plans` empty) → keep the existing "no tariff plan" note; the comparison rows still show
    the compared tariffs' costs, actual is "—".
- **Placement.** A "Tariff comparison" block after the device table and before "By period"; plain (not collapsible).
  Columns: tariff name | cost | difference (money, percent) | avg. price (`cost / kWh`). First row "Actual"
  (subtitle: the names from `actual.plans`, joined with " → " when several). No per-zone columns here (compared
  tariffs may have different zones).
- **Full width (sections view).** Checked: HA developer docs, "Sizing in the sections view"
  (https://developers.home-assistant.io/docs/frontend/custom-ui/custom-card/ — now redirects to
  contributors.home-assistant.io): `getGridOptions()` returns `columns` ("Number of columns, or `\"full\"` for the full
  width", default 12 on a 12-column section grid), `rows` (default `"auto"` = height follows content, not
  resizable), `min_columns` / `max_columns`, `min_rows` / `max_rows`. Introduced with the 2024.11 custom-card sizing
  post (https://developers.home-assistant.io/blog/2024/11/06/custom-card-sections-support), so it is available on the
  minimum HA 2025.4 (SPEC §6). The older `getLayoutOptions()` (`grid_columns`, …, 2024.8–2024.10) is not needed for
  2025.4 and is not implemented. Implement `getGridOptions(): { columns: "full", min_columns: 6 }` and omit `rows`
  (content height). **Unverified:** that `"full"` is accepted from `getGridOptions()` (not only from YAML
  `grid_options`) on 2025.4 — the implementer checks `LovelaceGridOptions` in `home-assistant/frontend`
  (`src/panels/lovelace/types.ts`) at tag `20250402.0` (or the frontend version pinned by HA 2025.4.0) and falls
  back to `columns: 12` if not; record the result in Implementation notes. A card cannot be wider than its section;
  wider layouts are a section setting (`column_span`) and out of the card's control — document this in SPEC §4.1.
  Masonry and panel views are unaffected (`getCardSize` stays).
- **Zone column groups.** Each zone (and the "Total" group) starts with a cell carrying a `group-start` class on all
  rows (head row 1, head row 2, body, footer) with `border-inline-start: 1px solid var(--divider-color)`. Zone headers
  are `text-align: center` over their `colspan`. The sticky name column gets an end border (or subtle shadow) so it
  stays distinguishable while the table scrolls under it.
- **Mobile name column — decision: wrap, not truncate.** Body/footer name cells use `white-space: normal`,
  `overflow-wrap: anywhere` and a width limit relative to the card (e.g. `.table-wrap { container-type:
  inline-size }` and `th.name { max-width: max(6.5em, 35cqi) }`; exact value at the implementer's discretion), plus
  `title` = full name. Justification: wrapped text stays fully readable without interaction, while an ellipsis needs
  a hover or tap that touch devices do not provide reliably for `title`; the cost is taller rows on narrow screens.
  Badges and the statistics sub-line stay inside the cell. Numeric cells stay `nowrap`. Same rule in the "By period"
  and comparison tables.
- **Dropdown bug — diagnosis first.** `hass` is a reactive property; HA sets a new `hass` object on every state
  change of any entity. Hypothesis: every such update re-renders the card while a native `<select>` is open, and the
  browser closes it. Note that Lit only commits *changed* binding values, so a plain re-render may not touch the
  select; the implementer must reproduce in dev HA (a frequently changing entity, e.g. a template sensor with
  `now()`) and confirm the cause before and after the fix. Other candidates if the select still closes after the
  `hass` gate: the card element being detached/re-attached (log `connectedCallback`), the `loading` indicator
  changing the header layout, or `getCardSize()` changes triggering a masonry re-layout. Record the finding in
  Implementation notes.
- **Fix.** Export a pure helper `hassChanged(next, prev): boolean` (in `card.ts` or a small `hass.ts`) and use it as
  the `hass` property's `hasChanged` (or in `shouldUpdate`): true when `prev` is undefined, or when any value the card
  reads differs — `language`, `locale.language`, `config.time_zone` (grep `this.hass` for anything else). The newest
  `hass` is still stored, so `callWS` always uses the current connection. A cursor jump to a screen corner was
  seen only in a gamescope session; it is a manual check in a regular desktop session after the fix.
- **Nested devices.** `devices[].upstream` (SPEC §4, §2) is the nearest ancestor in the report. In the device table
  a nested row is placed directly after its upstream (depth-first, keeping report order among siblings; a device
  whose upstream is not in the report keeps its position), its name is indented per depth level and prefixed with
  "↳", and its `title` reads "Measured inside {name}; not counted again in the total". When at least one nested row
  is shown, a note under the table explains: "Indented rows are measured inside the device above them. The total
  counts their energy only for hours where the device above has no data." Only the device table is reordered;
  `report.devices` order is still used for the breakdown device dropdown.
- **i18n.** New card strings in `frontend/src/i18n.ts`, English and Russian (comparison title, "Actual", difference,
  empty state, unpriced-tariff tooltip, nested-row tooltip and note). The integration's `translations/ru.json` is
  task 024.
- **Tests and existing helpers.** `card.test.ts`'s `makeHass` answers every message with `report()` and `last(hass)`
  returns the last call; with a second request per load both must become type-aware (`respond` dispatches on
  `msg.type`; a `lastOf(hass, type)` helper). Add a `compareDoc()` fixture to `frontend/test/fixtures.ts`.
- **Playwright.** Not added in this task: it needs a browser download in the devcontainer and CI and a new dev
  dependency for one screenshot. The phone-width check is a manual criterion; a Playwright visual test is a
  follow-up.

## Files
- modify: `frontend/src/report.ts` — `WS_TYPE_COMPARE`, `CompareDocument` type (`actual`, `tariffs[{id, name,
  report}]`), `compareMessage(query)` (same `start` / `end` / `entities` as `reportMessage`, no `grouping`),
  `fetchCompare`; `devices[].upstream: string | null` on `ReportDocument`.
- modify: `frontend/src/card.ts` — compare loading and state, comparison section, `getGridOptions`, `hass`
  `hasChanged` gate, `group-start` classes, name-column CSS and `title`, nested-row ordering / indent / note.
- create (optional): `frontend/src/compare.ts` — pure helpers: difference and percent from decimal strings, nested
  row ordering (`orderNested(devices) → {entity_id, depth}[]`). Keeps `card.ts` from growing further.
- modify: `frontend/src/i18n.ts` — new EN and RU strings.
- modify: `frontend/test/fixtures.ts` — `compareDoc()` fixture; `upstream` on report devices.
- modify: `frontend/test/card.test.ts` — type-aware `makeHass` / `lastOf`; new tests below.
- create: `frontend/test/compare.test.ts` — unit tests of the pure helpers (if `compare.ts` is created).
- modify: `custom_components/energy_cost_stats/frontend/energy-cost-stats-card.js` — rebuilt bundle (`npm run build`).
- modify: `docs/SPEC.md` — §4.1: comparison section, full-width grid options (and the section-width limit), zone
  group separators, wrapped name column, nested rows, `hass` update gate.

## Tests to write first
| Level | Test | Asserts |
|---|---|---|
| card | `card.test.ts::comparison > requests compare with the same period and entities` | after mount with `entities: [a, b]`, a `energy_cost_stats/compare` call exists with the same `start` / `end` / `entities` as the report call, and no `tariffs` / `grouping` key |
| card | `card.test.ts::comparison > grouping change does not re-request compare` | choosing another grouping adds a `report` call but no new `compare` call; refresh and period arrows add both |
| card | `card.test.ts::comparison > shows actual and each compared tariff with the difference` | rows "Actual" + tariff names in the response order; cost, signed difference and percent formatted (e.g. actual 100.00, tariff 112.50 → "+12.50", "+12.5 %"; a cheaper tariff → negative) |
| card | `card.test.ts::comparison > null cost gives a dash difference` | compared `cost: null` → cost "—" and difference "—"; actual `"0.00"` → percent "—" |
| card | `card.test.ts::comparison > warns when a tariff leaves hours unpriced` | `report.unpriced_hours > 0` on a compared tariff → badge with the tooltip text |
| card | `card.test.ts::comparison > empty list shows the hint` | `tariffs: []` → the "No tariffs to compare" note, no comparison table |
| card | `card.test.ts::comparison > older integration hides the section` | compare rejects with `{code: "unknown_command"}` → no comparison block, no error, device table rendered |
| card | `card.test.ts::comparison > a compare error does not hide the table` | compare rejects with another code → error text inside the comparison block; device table still rendered |
| card | `card.test.ts::comparison > stale compare response is dropped` | two overlapping loads; the older compare response resolving last does not replace the newer one |
| card | `card.test.ts::comparison > speaks Russian` | `language = "ru"` → Russian section title and "Actual" label |
| card | `card.test.ts::layout > asks for the full width in sections views` | `card.getGridOptions()` equals `{ columns: "full", min_columns: 6 }` (or the verified fallback) and has no `rows` |
| card | `card.test.ts::layout > zone groups start with a separator cell` | for 2 zones: in each body row the cells at the start of zone 1, zone 2 and Total carry `group-start`; head row 1 zone `th`s have `colspan="2"` and `group-start` |
| card | `card.test.ts::layout > name cells carry the full name as title` | body `th.name` has `title` = device name |
| card | `card.test.ts::nested > nested rows follow their upstream, indented, with a note` | devices `[child(upstream=parent), other, parent]` → table order parent, child, other; child row has class `nested` and depth 1 indent, title mentions the parent name; the nesting note is shown; with no `upstream` anywhere the note is absent |
| card | `card.test.ts::hass updates > an entity-state-only hass update does not re-render` | after mount, spy on `render`; assign a new `hass` object with the same language / locale / time zone (and a changed `states`) → `render` not called, no new `callWS`; `card.hass` is the new object |
| card | `card.test.ts::hass updates > a language change re-renders` | new `hass` with `language` / `locale.language` "ru" → re-rendered in Russian; a `config.time_zone` change also triggers an update |
| card | `card.test.ts::hass updates > an open select keeps its value across hass updates` | change the grouping select, push 3 entity-only `hass` updates → the select element is the same node and keeps its value (guards against DOM replacement) |
| card | `compare.test.ts::difference` (if `compare.ts`) | sign, percent, `null` and zero handling on decimal strings |
| card | `compare.test.ts::orderNested` (if `compare.ts`) | depth-first order, depth values, missing upstream keeps position, chains (grandchild depth 2), no cycles assumed but no infinite loop on a malformed cycle |

## Acceptance criteria
- [x] All tests above written first and green: `npm test` (in `frontend/`) → all pass.
- [x] `npm run typecheck` → no errors.
- [x] `npm run build` run and the bundle committed; `npm run check-bundle` → passes.
- [x] No `compare` option added to `CardConfig`; `setConfig` unchanged apart from documentation.
- [x] `getGridOptions` exists; Implementation notes state which source confirmed `"full"` for HA 2025.4 (or why the
      fallback `12` was used).
- [x] `hass` update gate implemented as a pure helper with unit-level coverage (language, locale language, time zone,
      first set).
- [ ] `uv run pytest -m unit` and `uv run ruff check .` / `uv run ruff format --check .` → unchanged, green (no Python
      changes expected).
- [x] `docs/SPEC.md` §4.1 describes the comparison section, full-width default, zone separators, wrapped name
      column, nested rows and the `hass` gate.
- [ ] Manual (dev HA, `script/develop`, sections dashboard): the card spans its section's full width when added
      without `grid_options`; a user-set `grid_options.columns` still overrides it.
- [ ] Manual (browser devtools, 360–390 px viewport): the name column wraps and is at most about a third of the card
      width; the zone/total columns scroll horizontally under the sticky name column; zone group separators and
      centred zone headers are visible in the device, "By period" and comparison tables.
- [ ] Manual (regular desktop browser session, not gamescope, with an entity updating every few seconds): the preset,
      breakdown device and grouping dropdowns open on the first click and stay open until a choice or an outside
      click; the cursor does not jump. The diagnosis (cause confirmed or other cause found) is in Implementation notes.
- [ ] Manual: with the integration's compare list empty, the hint is shown; with one compared tariff, actual and
      compared costs and the difference are shown for the selected period and change with the period and with the
      card's `entities`.

## Out of scope
- Sidebar panel with the energy date picker (task 023).
- `translations/ru.json` for the integration's forms (task 024).
- A custom in-page dropdown replacing the native `<select>` — only if the problem persists outside gamescope after
  this fix (follow-up).
- Per-zone breakdown of compared tariffs, per-device comparison, comparison in the "By period" table.
- Choosing compared tariffs from the card (the list is the integration's `compare` setting).
- Playwright visual tests (follow-up).
- Visual card editor.

## Open questions
- **Difference sign.** Default: compared − actual, so "+" means the alternative would have cost more (savings of the
  current choice). Alternative: show "savings" with the opposite sign. Confirm the wording.
- **Comparison block visibility.** Default: always shown (or the empty-state hint), no card option. Alternative: a
  `show_comparison: false` card option to hide it on compact dashboards.
- **Highlight cheapest.** Default: no highlight. Alternative: mark the cheapest row (actual included).
- **Nested-row ordering.** Default: the card reorders so nested rows follow their upstream. Alternative: keep the
  report's order and only indent / mark — simpler, but an indented row away from its parent is confusing.
- **Name column.** Default: wrap (see Context). Alternative: single line with ellipsis and the full name in `title`.

<!-- Filled in by implementer -->
## Implementation notes
- **Files.** `frontend/src/compare.ts` (`difference`, `orderNested`), `frontend/src/hass.ts` (`hassChanged`),
  `report.ts` (`CompareDocument`, `compareMessage`, `fetchCompare`, `upstream`), `card.ts`, `i18n.ts`, fixtures
  (`totalDoc`, `compareDoc`), tests (`compare.test.ts`, new groups in `card.test.ts`), SPEC §4.1, rebuilt bundle.
  No Python changes (unit tests, ruff and pyright were not re-run).
- **Tests-first caveat.** The pure helpers (`compare.ts`, `hass.ts`) were written before their unit tests; the
  card behaviour tests were written and failed (16 failures) before the card changes.
- **`getGridOptions`.** `columns: "full"` is confirmed by `LovelaceGridOptions` in `home-assistant/frontend`
  (`src/panels/lovelace/types.ts`, tag `20250411.0`, a 2025.4 frontend): `columns?: number | "full"`,
  `getGridOptions?(): LovelaceGridOptions`. Tag `20250402.0` does not exist, so the later 2025.4 tag was used.
  No fallback to `12` is needed.
- **Dropdown diagnosis (automated part).** Reproduced in Vitest against the old behaviour (gate removed):
  every entity-only `hass` update runs `render()` (test fails without the gate), but Lit commits no DOM change
  (a `MutationObserver` on the shadow root sees nothing), the card element is not re-attached
  (`connectedCallback` / `disconnectedCallback` not called), the `ha-card` and select nodes keep identity and
  value, and `getCardSize()` does not change while loading (the previous report is kept during a reload). The
  header does not shift while loading: the indicator shares a flex row with the taller title. So the
  hypothesis "the DOM is replaced" is not supported; the remaining suspects are the render work itself (the
  `live()` directive reads `select.value` on every render) and the compositor, which can only be judged in a
  real browser. The gate removes all of it for unrelated updates. A real-browser check is a manual criterion
  below; if the dropdown still closes, the next step is a custom in-page dropdown (out of scope here).
- **Defaults for the open questions as listed above**: difference = compared − actual,
  comparison always shown, no highlight of the cheapest row, nested rows reordered, name column wraps.
- **Unpriced badge.** A tariff row shows the badge when the tariff's report or the actual report has unpriced
  hours; the tooltip uses the tariff's hours, else the actual's.
- **Compare request timing.** Compare is sent together with the report (before the report reveals the
  integration's time zone) and re-sent together with the report on the time-zone retry.
- **Formatting.** `Strings.money` gained an optional `signed` flag (`signDisplay: "exceptZero"`), plus
  `signedMoney` and `signedPercent` (one decimal, `" %"` suffix).
## Follow-ups
- Playwright visual test for the phone-width layout and the dropdowns (needs a browser in CI).
- If the dropdown still closes in a regular desktop browser after the gate: custom in-page dropdown.
- Card tests: pass the mounted card to `settle` in the refresh-timer test, cover the `compare.unpriced_actual`
  tooltip, and narrow the header loading selector to `.header .loading`.
