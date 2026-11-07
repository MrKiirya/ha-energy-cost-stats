# 025 — Review (round 1)

Verdict: CHANGES_REQUESTED

## Checks run
Run in the devcontainer (`frontend/`):
- `npm test` → `Test Files 6 passed (6)`, `Tests 167 passed (167)`
- `npm run typecheck` (`tsc --noEmit`) → no errors
- `npm run check-bundle` → `Card bundle is up to date.`
- `git diff HEAD --stat -- '*.py'` → empty (no Python changes; pytest, ruff and pyright are not affected)

## Acceptance criteria
- [x] Tests written and green — `sort.test.ts` (sortValue, comparator, naturalDirection, validateSortConfig,
  resolveSort, storage), `compare.test.ts` (comparator tree sort, cycle members), `card.test.ts` (`sorting`,
  `sticky`), `panel.test.ts` (`sticky toolbar`). Each would fail without the code (no buttons, report order,
  no `.controls`, no sticky rules).
- [x] `npm run typecheck` → no errors — verified above.
- [x] Bundle rebuilt; `npm run check-bundle` passes — verified above.
- [x] Money only — `sort.ts::sortValue` reads `row.cost`, `row.zones[].cost` (by `key`) or `cost / kWh`;
  no key returns kWh; covered by "never uses kWh for cost keys".
- [x] No websocket request on a sort click — `card.test.ts` "sorts by a zone and toggles" compares
  `hass.calls.length`; `_onSort` only sets state and calls `saveSort`. No Python files changed.
- [x] i18n keys in `en` and `ru` — five `sort.*` keys in both maps (`RU` is typed `Record<StringKey, string>`,
  so a missing key fails the type check).
- [x] SPEC §4.1 documents `sort` / `sort_direction`, the tree sort, the remembered choice, the sticky parts,
  `--energy-cost-stats-sticky-top` and the bounded scroll box — but see Required 2 for a stale sentence.
- [ ] Implementation notes record the HA 2025.4 frontend CSS check — not met: the notes state it was not
  verified. Accepted as an open manual item (see Suggestion 1), not a blocker of the code.
- [ ] Manual dev-HA checks (desktop, phone / masonry, sidebar panel) — not done; for the human.

## Verified behaviour
- Tree sort: `orderNested(devices, compare)` sorts the roots and every children list, then walks depth-first, so a
  child stays directly after its upstream; cycle members are appended in report order; without a comparator the
  order is unchanged (existing tests pass).
- Comparator: unpriced (`null`, missing zone cell, non-finite, avg. price with `kWh <= 0` or `null`) last in both
  directions; ties by collator name, then entity id, independent of direction; `name` uses
  `Intl.Collator(locale, { sensitivity: "base", numeric: true })`.
- Defaults and directions: built-in `total` / `desc`; first click `name` → asc, money → desc; active header
  toggles; `sort_direction` without `sort` applies to `total`; an unknown zone key falls back to `total` / `desc`
  without an error and the configured value is kept.
- `setConfig` validates `sort` (non-empty string) and `sort_direction` (`asc` / `desc`) before applying.
- Storage: key `energy-cost-stats-card.sort.v1|<pathname>|[title, entities, sort, sort_direction]`; `getItem`,
  `JSON.parse` and `setItem` are all inside `try/catch`; malformed or invalid stored values are ignored.
- Accessibility: real `<button type="button">` per top-row header, `aria-sort` only on the active `th` (Lit
  `nothing` removes the attribute elsewhere), indicator `aria-hidden`, `title` describes the next action,
  `:focus-visible` outline. Second head row has no buttons; "By period" and comparison tables pass no sort spec.
- Markup / CSS: Device and Avg. price `rowspan=2`, Total `colspan=2`, Avg. price after Total with `group-start` on
  head, body and footer cells; `thead tr:first-child th { vertical-align: top }`; zone headers stay centred with
  `group-start`; `thead` sticky (`top: 0; z-index: 2`), opaque head backgrounds with a shadow bottom line,
  `thead th.name` z-index 3, body `th.name` z-index 1; `.table-wrap` `overflow: auto` with `vh` / `dvh`
  `max-height`; `.controls` sticky at `--ecs-sticky-top` (public override, else `--header-height` plus
  `--safe-area-inset-top` / `env()`); `ResizeObserver` guarded and disconnected; panel bar sticky with
  `z-index: 5` and `--energy-cost-stats-sticky-top` on its host.

## Findings
### Required
1. `frontend/src/card.ts:959` — `.controls { z-index: 4 }` equals the z-index of Home Assistant's fixed dashboard
   header (`hui-root .header`, z-index 4, as quoted in the task). If both end up in the same stacking context,
   the later element in DOM order (the card) paints on top, so when the card scrolls out and its sticky controls
   are pushed up past the top bar, they cover the header instead of sliding under it. The task asks for "a value
   that keeps the controls below the HA header". The table's sticky cells live inside `.table-wrap`, which is
   already its own stacking context (`container-type: inline-size` implies layout containment), so the controls
   only need to be above that box. Direction: use `z-index: 3` (or lower, e.g. 1) and keep the panel bar at 5;
   optionally assert the value in the `sticky` test.
2. `docs/SPEC.md:436` (§4.1 "Nested devices") still says nested devices follow their upstream "depth-first,
   report order among siblings", which contradicts the new "Sorting" paragraph (siblings are now sorted by the
   active key). The same wording is in the `orderNested` doc comment (`frontend/src/compare.ts:26`), which is
   still correct only for the no-comparator case. Direction: reword the SPEC sentence to "sorted among siblings
   by the active sort (see Sorting)"; in the doc comment say "report order among siblings unless `compare` is
   given".

### Suggestions
1. Acceptance criterion "HA 2025.4 frontend CSS check" is open. Before merge, check `hui-root.ts`,
   `hui-masonry-view.ts` and `hui-panel-view.ts` at frontend tag `20250411.0` (safe-area variable name, any
   `overflow` / `contain` / `transform` on wrappers) and record the result in Implementation notes, or move it
   to Follow-ups explicitly.
2. `frontend/src/card.ts` `thead th` / `.group-start` — the head now sticks, but the zone separators of head cells
   are still `border-inline-start` in a `border-collapse: collapse` table. Collapsed borders of sticky cells may
   not move with them (the reason the bottom line and the name column use `box-shadow`). Include the head
   separators in the manual check while scrolling; if they disappear, draw them as an inset `box-shadow` too.
3. `frontend/src/i18n.ts` (RU `sort.by` + `sort.cost_of`) — the zone title renders as
   "Сортировать по: стоимость: Day, по убыванию" (two colons). Consider e.g. `sort.cost_of` = "стоимость ({zone})"
   or `sort.by` = "Сортировка: {column}, {direction}".
4. `frontend/test/card.test.ts` "only the device table is sortable" — assert that `table.buckets` and
   `table.comparison` exist before checking that they contain no `button.sort`, so the test cannot pass
   vacuously if either table stops rendering in this fixture.
5. `frontend/src/card.ts` `connectedCallback` / `_observeControls` — after a disconnect / reconnect (view switch)
   the new observer is only attached on the next update; the last measured height stays on the host meanwhile,
   so this is harmless, but calling `this._observeControls()` at the end of `connectedCallback` (when a shadow
   root exists) would make it immediate.
6. `frontend/src/card.ts` `_renderHead` — the `const title = s.t("sort.by", …)` line is well over the line
   length used elsewhere in the file; wrap it for readability.

# 025 — Review (round 2)

Verdict: APPROVE

## Checks run
Run in the devcontainer (`frontend/`):
- `npm test` → `Test Files 6 passed (6)`, `Tests 167 passed (167)`
- `npm run typecheck` (`tsc --noEmit`) → no errors
- `npm run check-bundle` → `Card bundle is up to date.`

## Previous required items
1. Resolved — `frontend/src/card.ts` `.controls` now uses `z-index: 3` with a comment (below the fixed Home
   Assistant header at 4, above the table box); the `sticky` test in `frontend/test/card.test.ts` asserts the
   value. The panel bar stays at 5 and the table's internal z-indexes (1–3) are unchanged.
2. Resolved — `docs/SPEC.md` §4.1 "Nested devices" now reads "siblings sorted by the active sort, see
   'Sorting'"; the `orderNested` doc comment in `frontend/src/compare.ts` says report order applies unless
   `compare` is given.

## Previous suggestions
- 1 (HA 2025.4 frontend CSS check) — moved to Follow-ups in the task file; the acceptance criterion stays open
  for the manual verification, together with the manual dev-HA criteria.
- 2 (head separators) — remains a manual check while scrolling; no code change needed until a browser shows
  the problem.
- 3 — RU `sort.cost_of` is now "стоимость {zone}" (no double colon).
- 4 — the test asserts that `table.buckets` and `table.comparison` render before checking for sort buttons.
- 5 — `connectedCallback` calls `_observeControls()` after creating the observer.
- 6 — the long `title` line is wrapped.

## Findings
### Required
None.
### Suggestions
None new. No regressions found in the touched files.
