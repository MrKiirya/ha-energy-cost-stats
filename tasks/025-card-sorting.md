# 025 — Card: sortable device table, sticky table header and sticky controls

Status: in-review (round 1: CHANGES_REQUESTED; round 2: APPROVE; manual browser checks open)
Roadmap: Configuration v2 (docs/CONFIG-DESIGN.md "Tasks") — stage 4 card follow-up
Spec sections: SPEC §4 (JSON contract: `zones`, `totals.rows[].zones[].key`, `devices[].upstream`), §4.1 (card:
config, table, layout, nested devices, sidebar panel, language), §6 (minimum HA version)

## Goal
The device table can be sorted by clicking a column header in its top header row: by device name, by the cost of
one zone, by total cost or by average price. A second click on the active header reverses the direction; the active header shows ▲ / ▼ and carries
`aria-sort`. The default is total cost, descending, and a card can set another default in YAML (`sort`,
`sort_direction`). The last click is remembered per card in the browser. Nested devices stay under their upstream
and are sorted among their siblings; the total row stays at the bottom. While scrolling, the table header rows stay
visible (also with the sticky name column), and the card's period controls stay visible below Home Assistant's top
bar, in a dashboard and in the sidebar panel.

## Context
- **Header layout (changed by this task).** `card.ts::_renderHead` renders two head rows: row 1 = `th.name`
  (rowspan 2, "Device"), one `th.zone.group-start` (colspan 2) per `report.zones` entry (name + period price),
  `th.zone.sum.group-start` "Total" (colspan 2: kWh + cost) and a new top-level `th.num.group-start.avg` "Avg.
  price" (rowspan 2, like Device); row 2 = kWh / cost per zone, then kWh / cost of Total. Body and footer rows keep
  the same cell order (the average price is the last cell, with a group separator). All top-row header cells use
  `vertical-align: top`, including the two-row-tall Device and Avg. price cells, so labels and ▲ / ▼ indicators
  line up on one line.
- **Current table (tasks 014, 022).**
  `_renderHead` is shared with the "By period" table (first column label differs). Body rows come from
  `_deviceRows(report)`, which orders `report.totals.rows` via `compare.ts::orderNested(report.devices)`
  (depth-first, report order among siblings, missing upstream = root, cycle-safe). The total row is in `<tfoot>`.
  The table is in `.table-wrap { overflow-x: auto; container-type: inline-size }`; `th.name` is `position: sticky;
  left: 0` with an opaque background and an inset shadow.
- **Sort keys — by money, never by kWh.** Four kinds of key, each sorting by a money value from the report row:
  - `name` — device name (`report.devices[].name`, falling back to the entity id), compared with
    `Intl.Collator(<card language>, { sensitivity: "base", numeric: true })`.
  - `total` — `row.cost` (total cost of the device for the period).
  - `avg_price` — `row.cost / row.kwh` (average price); `null` when the cost is `null`, the kWh is `null`, not
    positive or the quotient is not finite.
  - a zone key (e.g. `t1`) — `row.zones[].cost` of the cell whose `key` equals the zone key (look up by `key`, not
    by index). With two zones the keys are: name, zone 1 cost, zone 2 cost, total cost, avg. price.
  Costs are decimal strings; parse with `Number()` for comparison only (display unchanged). `null`, a missing zone
  cell or a non-finite value is "unpriced" and **sorts last in both directions**. Ties (equal values, or both
  unpriced) are broken by name ascending (collator above), then by entity id, so the order is deterministic and
  independent of the direction. For `name` ties fall back to entity id.
- **Direction.** Clicking an inactive header activates it with its natural direction: `name` ascending, money keys
  descending. Clicking the active header toggles the direction. Default: `total`, `desc`.
- **Tree sort.** `orderNested` gains an optional sibling comparator: roots are sorted with it, and the children of
  each device are sorted with it among themselves, recursively; every child still follows its upstream directly
  (depth-first). Without a comparator the current behaviour (report order) is unchanged — the "By period" device
  dropdown and existing tests rely on it. Cycle members appended at the end keep report order.
- **Total row.** Stays in `<tfoot>`, never sorted.
- **Header buttons and accessibility.** In the device table only, each sortable header, all in the top head row
  (`th.name`, each zone `th`, the "Total" group `th`, the "Avg. price" `th`), contains a `<button class="sort" data-sort="<key>">` with the header text
  (the zone price sub-line stays inside the button). The active header `th` gets `aria-sort="ascending"` /
  `"descending"`; inactive sortable headers have no `aria-sort` attribute (WAI-ARIA: set it on one header at a time).
  The indicator is a `<span class="sort-indicator" aria-hidden="true">` with ▲ (asc) or ▼ (desc), only on the active
  header. The button's `title` / accessible description says what a click does, e.g. "Sort by {column} (cost),
  descending" — exact strings in `i18n.ts`. The second head row (kWh / cost) has no buttons. The "By period" and
  comparison tables keep plain headers (`_renderHead` gets a `sortable` flag or an optional sort argument).
  Sorting is client-side only: it never sends a websocket request.
- **YAML options.** `sort?: string` — `name`, `total`, `avg_price` or a zone key (the zone keys are only known after the first
  report, so `setConfig` validates the type only: a non-empty string, else `throw new Error("sort must be name,
  total or a zone key")`); `sort_direction?: "asc" | "desc"` (anything else throws). When `sort` is given without
  `sort_direction`, the direction is that key's natural direction. `name`, `total` and `avg_price` are reserved: a zone whose key
  is literally `name` or `total` cannot be the default sort (it is still sortable by click; see Open questions).
  A configured zone key that is not in the current report falls back to `total` / `desc` for that report, without
  an error (a plan change can remove a zone); the configured value is kept, so it applies again when the zone is back.
- **Remembered choice (localStorage).** After a header click the card stores `{ sort, direction }` as JSON under
  `energy-cost-stats-card.sort.v1|<location.pathname>|<JSON of [title, entities, sort, sort_direction]>`. Including
  the configured `sort` / `sort_direction` in the key means a YAML change of the default takes effect again instead
  of being shadowed by an old click. On load the stored value is used if it parses and names `name`, `total` or a
  string (zone keys are checked against the report like the YAML value). Every `localStorage` access is in
  `try/catch` (storage disabled, private mode, quota, sandboxed iframe): on failure the card simply uses the YAML or
  built-in default and does not log noisily. Two cards with identical title / entities / sort on the same dashboard
  share the remembered choice; this is accepted. In the sidebar panel the pathname is the panel's URL path.
- **Which element scrolls (checked).** Dashboards scroll the **window/document**, not the card: in
  `home-assistant/frontend` `src/panels/lovelace/hui-root.ts` (branch `dev`) `.header` is `position: fixed; top: 0;
  padding-top: var(--safe-area-inset-top); z-index: 4`, `.toolbar` has `height: var(--header-height)`, the view
  container pads itself by `var(--header-height) + var(--safe-area-inset-top)`, and scroll position is read from
  `window.scrollY`. In edit mode a second tab bar (`--tab-bar-height`, 56 px) is added. `ha-card`'s `:host` has
  `position: relative` and **no** `overflow` / `contain` / `transform`; `hui-grid-section` and `hui-sections-view`
  set none of these on their wrappers either. So a `position: sticky` element inside the card sticks to the page
  viewport, bounded by the card (it sticks only while the card is on screen, which is wanted).
  **Unverified for 2025.4:** the same CSS at frontend tag `20250411.0` (in particular whether
  `--safe-area-inset-top` exists there or `env(safe-area-inset-top)` was used), and `hui-masonry-view` /
  `hui-panel-view` wrappers; the implementer checks and records the result in Implementation notes.
- **Sticky controls.** Wrap the picker row and the custom-range row in one `<div class="controls">` with
  `position: sticky; top: var(--energy-cost-stats-sticky-top, calc(var(--header-height, 56px) +
  var(--safe-area-inset-top, env(safe-area-inset-top, 0px))))`, an opaque background
  (`var(--ha-card-background, var(--card-background-color, white))`, same as `ha-card`), a z-index above the table's
  sticky cells (e.g. 4; `ha-card` has no stacking context of its own that would matter, the HA header has z-index 4
  but is outside the card and `position: fixed` — use a value that keeps the controls below the HA header, verify
  manually), and negative inline margins / matching padding so the table does not show through at the card's
  padding edges. The card title (`.header`) scrolls away. The CSS custom property
  `--energy-cost-stats-sticky-top` is the override point (themes, card-mod, kiosk setups without a header) and is
  documented in SPEC §4.1.
- **Sidebar panel (task 023).** The panel draws its own top bar (`height: var(--header-height, 56px)`); there is no
  HA dashboard header there. Make the panel's `.toolbar` `position: sticky; top: 0; z-index: 5` and set
  `--energy-cost-stats-sticky-top: var(--header-height, 56px)` on the panel's `:host`, so the card's controls stick
  directly under the panel bar (custom properties inherit through shadow roots). **Unverified:** which ancestor
  scrolls in a custom panel (document or a container inside `home-assistant-main` / `ha-drawer`); sticky works
  against whichever is the nearest scrolling ancestor, so this only matters if an ancestor between the panel and
  that scroller sets `overflow` — manual check.
- **Comparison table.** It already has "Avg. price" as its own two-row-tall column with a separator; it stays as is
  (consistent with the device table). Sorting it is out of scope.
- **Sticky table header — why the table gets its own vertical scroll box.** A sticky element sticks to its nearest
  scrolling ancestor. `.table-wrap` must keep `overflow-x: auto` (horizontal scroll on phones), and per CSS Overflow
  Level 3 `overflow-x: auto` with `overflow-y: visible` computes `overflow-y` to `auto`, so `.table-wrap` *is* the
  scrolling ancestor of the head cells and `top: 0` would never stick to the page
  (https://developer.mozilla.org/en-US/docs/Web/CSS/overflow — "visible ... computes to auto if the other is not
  visible"; https://developer.mozilla.org/en-US/docs/Web/CSS/position#sticky). `overflow-x: clip` would avoid the
  scroll container but removes horizontal scrolling. Chosen approach: `.table-wrap` becomes a bounded scroll box in
  both axes — `overflow: auto; max-height: calc(100vh - <sticky top> - var(--energy-cost-stats-controls-height,
  0px) - 8px)` with a `100dvh` override line — so the head sticks inside it (`top: 0`) and the name column sticks
  left inside it. The card measures the `.controls` height with a `ResizeObserver` (created in `firstUpdated` /
  `connectedCallback`, disconnected in `disconnectedCallback`, skipped when `ResizeObserver` is undefined) and sets
  `--energy-cost-stats-controls-height` on the host. Short tables are unaffected (`max-height` only caps). Trade-off:
  a long table scrolls inside the card (scroll chaining hands over to the page at its ends). A JS-synchronised
  cloned header that sticks to the page is the alternative (Open questions).
- **Sticky head cells.** Both head rows stick: either `thead { position: sticky; top: 0; z-index: 2 }` or per-cell
  `thead th { position: sticky }` with row 2 at `top: var(--head-row-1-height)` (measured). Implementer's choice;
  prefer sticky `thead` and fall back to per-cell if a browser does not combine it with the sticky name column.
  Head cells need an opaque background and draw their bottom border as `box-shadow` (borders of sticky cells scroll
  away in collapsed tables, as already noted for `th.name`). The top-left cell (`thead th.name`) is sticky in both
  directions (`left: 0` plus the head's `top: 0`) with the highest z-index inside the table (e.g. 3; body
  `th.name` 1, head 2). Apply the same `.table-wrap` / head rules to all three tables (device, comparison, "By
  period" — the last is the longest with hourly grouping); only the device table gets sort buttons.
- **i18n.** New strings in `frontend/src/i18n.ts`, English and Russian: e.g. `sort.by` ("Sort by {column}" /
  "Сортировать по: {column}"), `sort.ascending` ("ascending" / "по возрастанию"), `sort.descending`
  ("descending" / "по убыванию"), `sort.cost_of` ("{zone} cost" / "стоимость: {zone}") or equivalent — keys at the
  implementer's discretion, every key present in both languages (existing pattern).
- **Minimum HA (SPEC §6).** No new HA API is used; `position: sticky`, `ResizeObserver`, `Intl.Collator` and `dvh`
  (with a `vh` fallback) are available in every browser supported by the HA 2025.4 frontend.
- **Playwright** is still not available (task 022); layout behaviour is a manual criterion.

## Files
- create: `frontend/src/sort.ts` — pure helpers: `SortKey` (`"name" | "total" | "avg_price" | string`), `SortDirection`,
  `naturalDirection(key)`, `validateSortConfig(sort, direction)` (throws the setConfig errors), `resolveSort(spec,
  zoneKeys)` (unknown zone → total/desc), `sortValue(row, key)` (cost as number or `null`), `makeComparator(spec,
  names, language)` (nulls last both ways, ties by name then entity id), `storageKey(...)`, `loadSort(key)` /
  `saveSort(key, spec)` (try/catch around `localStorage`).
- modify: `frontend/src/compare.ts` — `orderNested(devices, compare?)`: optional sibling comparator (roots and each
  children list), default behaviour unchanged.
- modify: `frontend/src/card.ts` — `CardConfig.sort` / `sort_direction` and validation in `setConfig`; `_sort` state
  (initialised from storage, else config, else total/desc; resolved against `report.zones` at render); sortable head
  buttons with `aria-sort` and indicator in the device table only; `_deviceRows` passes the comparator;
  `.controls` wrapper; `ResizeObserver` for the controls height; CSS for sticky controls, sticky head, the
  bounded `.table-wrap`, the top-left cell, sort buttons (inherit font/colour, full cell width, focus-visible
  outline).
- modify: `frontend/src/panel.ts` — sticky toolbar, `--energy-cost-stats-sticky-top` on `:host`.
- modify: `frontend/src/i18n.ts` — new EN + RU strings.
- create: `frontend/test/sort.test.ts` — unit tests of `sort.ts`.
- modify: `frontend/test/compare.test.ts` — `orderNested` with a comparator.
- modify: `frontend/test/card.test.ts` — `sorting` and `sticky` groups (below); a `localStorage` stub/reset in
  `beforeEach`.
- modify: `frontend/test/panel.test.ts` — sticky toolbar / custom property.
- modify: `frontend/test/fixtures.ts` — if needed, a report with ≥ 3 devices whose zone costs order differently
  from their total costs, one `null` cost, a tie, and one nested device.
- modify: `custom_components/energy_cost_stats/frontend/energy-cost-stats-card.js` — rebuilt bundle (`npm run build`).
- modify: `docs/SPEC.md` — §4.1: Config (`sort`, `sort_direction`), Table (sorting, remembered choice), Layout
  (sticky controls and head, `--energy-cost-stats-sticky-top`, bounded table scroll), Sidebar panel (sticky bar).

## Tests to write first
| Level | Test | Asserts |
|---|---|---|
| card | `sort.test.ts::sortValue > reads the total, average price or zone cost by key` | `avg_price` → cost / kWh, `null` without kWh or cost; `total` → `Number(row.cost)`; zone key → the cell with that `key` even when zones are in another order; missing cell, `null` and non-numeric → `null`; kWh is never used (a row with high kWh but low cost sorts by cost) |
| card | `sort.test.ts::comparator > unpriced last in both directions` | rows with costs 5, null, 10 → desc 10, 5, null; asc 5, 10, null |
| card | `sort.test.ts::comparator > ties broken by name, then entity id` | equal costs (and two `null`s) → name ascending in both directions; equal names → entity id |
| card | `sort.test.ts::comparator > name sort uses the collator` | `name` asc/desc; "Plug 2" before "Plug 10" (numeric); Cyrillic names ordered with `ru` |
| card | `sort.test.ts::naturalDirection` | `name` → asc; `total`, `avg_price` and a zone key → desc |
| card | `sort.test.ts::validateSortConfig` | accepts undefined, `name`, `total`, `avg_price`, `t1`, `asc`, `desc`; throws for `""`, a number, `sort_direction: "up"` |
| card | `sort.test.ts::resolveSort > unknown zone falls back` | `{t9, asc}` with zones `[t1, t2]` → `{total, desc}`; `{t2, asc}` stays |
| card | `sort.test.ts::storage > round trip and failures` | `saveSort` then `loadSort` returns the spec; malformed JSON → `undefined`; a `localStorage` whose getters/setters throw → no exception, `undefined`; key contains pathname and the configured sort |
| card | `compare.test.ts::orderNested with a comparator` | roots sorted, children sorted among siblings and still directly after their parent, grandchild depth 2; without comparator the existing order tests still pass |
| card | `card.test.ts::sorting > defaults to total cost descending` | body row order by `row.cost` desc, the `null`-cost device last; the "Total" group `th` has `aria-sort="descending"` and ▼; other sortable headers have no `aria-sort`; tfoot total row unchanged and last |
| card | `card.test.ts::sorting > clicking a zone header sorts by that zone's cost and toggles` | click `button.sort[data-sort="t2"]` → order by t2 cost desc (differs from total order), ▼ on the zone header; click again → asc with `null` still last, ▲; no new `callWS` |
| card | `card.test.ts::sorting > header layout` | top row: Device and Avg. price have `rowspan=2`, Total has `colspan=2`; every sort button is in row 1; row 2 has no buttons; Avg. price follows Total; the styles set `vertical-align: top` on top-row cells |
| card | `card.test.ts::sorting > clicking the avg. price header sorts by average price` | order by cost / kWh desc, then asc, unpriced last |
| card | `card.test.ts::sorting > clicking the name header sorts ascending first` | click name → names A→Z, `aria-sort="ascending"`; click again → Z→A |
| card | `card.test.ts::sorting > nested devices stay under their upstream` | a child with a high cost stays directly after its parent (indented) and is ordered among its siblings; the parent moves with its subtree |
| card | `card.test.ts::sorting > yaml default` | `sort: name` → name asc; `sort: t1, sort_direction: asc` → t1 cost asc; `sort: t9` (not in report) → total desc, no error shown |
| card | `card.test.ts::sorting > setConfig rejects invalid sort options` | `sort: ""`, `sort: 3`, `sort_direction: "down"` throw |
| card | `card.test.ts::sorting > remembers the click per card` | click a header, mount a new card with the same config → same sort; a card with a different `sort` in YAML ignores it |
| card | `card.test.ts::sorting > works without localStorage` | stubbed `localStorage` that throws on every access → card renders, clicks sort, no error displayed |
| card | `card.test.ts::sorting > only the device table is sortable` | "By period" and comparison tables contain no `button.sort` |
| card | `card.test.ts::sorting > speaks Russian` | `language = "ru"` → sort button `title` / label in Russian |
| card | `card.test.ts::sticky > controls wrapper` | `.controls` contains the picker and, when open, the custom-range row; `.header` is outside it; card styles contain a `.controls` rule with `position: sticky` and `--energy-cost-stats-sticky-top`, and `thead` (or `thead th`) sticky rules |
| card | `card.test.ts::sticky > no ResizeObserver` | with `ResizeObserver` undefined the card mounts and renders without throwing |
| card | `panel.test.ts::sticky toolbar` | panel styles contain a sticky `.toolbar` rule and set `--energy-cost-stats-sticky-top` |

## Acceptance criteria
- [x] All tests above written first and green: `npm test` (in `frontend/`) → all pass.
- [x] `npm run typecheck` → no errors.
- [x] `npm run build` run and the bundle committed; `npm run check-bundle` → passes.
- [x] Sorting is by money only: no key sorts by kWh (average price is cost / kWh).
- [x] No websocket request is sent by a sort click (covered by a test); no Python files changed
      (`git diff --stat master... -- '*.py'` → empty).
- [x] Every new i18n key exists in both `en` and `ru` (existing i18n test, or a new one, passes).
- [x] `docs/SPEC.md` §4.1 documents `sort` / `sort_direction`, the cost-based tree sort (unpriced last, ties by
      name), the remembered choice, the sticky controls / head, `--energy-cost-stats-sticky-top` and the bounded
      table scroll box.
- [ ] Implementation notes record the 2025.4 check of `hui-root` / `hui-masonry-view` / `hui-panel-view` CSS
      (frontend tag `20250411.0`) and the safe-area variable used.
- [ ] Manual (dev HA, sections dashboard, desktop): clicking headers sorts, ▲ / ▼ follows, keyboard Tab + Enter /
      Space sorts, a screen reader (or the accessibility tree in devtools) shows `aria-sort` on the active header;
      reload keeps the last choice.
- [ ] Manual (phone or devtools 360–390 px, sections and masonry dashboards): while scrolling the page the period
      controls stay visible directly under HA's top bar (not hidden under it); the two head rows stay visible
      while scrolling a long table; the top-left cell stays put when scrolling horizontally and vertically; the
      name column still sticks left.
- [ ] Manual (sidebar panel, narrow and wide): the panel bar stays at the top and the card controls stick right
      under it.

## Out of scope
- Sorting of the comparison table and of the "By period" table (follow-up).
- Sorting by kWh.
- Server-side changes (websocket, service, engine).
- A visual card editor field for `sort`.
- Playwright visual tests (follow-up from task 022).
- A JS-synchronised header that sticks to the page instead of the table's own scroll box (see Open questions).

## Open questions
- **Zone keys `name` / `total`.** Resolved (default kept): reserved words win, so such a zone cannot be the YAML default (click
  sorting still works). Alternative: zone keys as `zone:<key>` in YAML — unambiguous but more verbose.
- **Natural direction on first click.** Resolved (default kept): name ascending, costs descending. Alternative: always descending
  first.
- **Ties.** Resolved (default kept): name ascending regardless of direction. Alternative: ties follow the direction.
- **Inner scroll box for the table.** Resolved: the table scrolls inside a box capped at the visible height so its
  head can stick (simple approach). A cloned page-sticky header synchronised with the horizontal scroll is a
  follow-up.
- **Sticky controls always on.** Resolved (default kept): yes, with the `--energy-cost-stats-sticky-top` CSS override.
  Alternative: a `sticky_controls: false` card option for dashboards where the header is hidden or the card is
  short. In dashboard edit mode the extra tab bar may cover the controls; default: accepted.
- **Remembered choice key.** Resolved (default kept): per dashboard path + title + entities + configured sort, so identical cards
  on one dashboard share it. Alternative: an explicit `id` card option.

## Implementation notes
- Layout, sort keys (including `avg_price`), YAML options and sticky approach follow the task text as revised:
  all sort controls in the top header row, Avg. price a separate two-row-tall column after Total, simple
  bounded scroll box with sticky `thead`, sticky controls and sticky panel bar.
- `makeComparator(spec, rows, names, language)` works on entity ids; `orderNested` takes the comparator as an
  optional second argument (roots and each children list are sorted before the depth-first walk).
- The default order changed from report order to total cost descending, so the existing nested-devices test now
  sets `sort: "name"`.
- The head cells use an internal `--ecs-sticky-top` that wraps the public `--energy-cost-stats-sticky-top`
  override, so the `max-height` of the table box and the controls offset share one definition.
- `ResizeObserver` measures `.controls` and sets `--energy-cost-stats-controls-height` on the host; it is skipped
  when `ResizeObserver` is undefined.
- `.controls` uses z-index 3 (below HA's fixed header at 4); the table's sticky cells live inside `.table-wrap`.
- Not verified here: the Home Assistant frontend CSS at tag `20250411.0` (`hui-root`, `hui-masonry-view`,
  `hui-panel-view`, safe-area variable) and all manual layout criteria; the CSS falls back from
  `--safe-area-inset-top` to `env(safe-area-inset-top)`.
- No Python files changed.

## Follow-ups
- Page-sticky table header synchronised with the horizontal scroll (replaces the inner scroll box).
- Verify the HA 2025.4 frontend sticky behaviour and the manual criteria in a dev HA.
