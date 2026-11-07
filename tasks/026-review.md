# 026 — Review (round 1)

Verdict: CHANGES_REQUESTED

## Checks run
- `npm test` (devcontainer, `frontend/`) → `Test Files 7 passed (7)`, `Tests 187 passed (187)`
- `npm run typecheck` → `tsc --noEmit`, no errors
- `npm run check-bundle` → `Card bundle is up to date.`
- No conflict markers in `frontend/src/card.ts` or `docs/SPEC.md`. No Python files are touched, so `ruff check .` is
  not affected.

## Merge result (card)
`frontend/src/card.ts` contains only additions relative to `HEAD`, apart from the `hass` property declaration. From
task 016 it keeps the collection lookup, the `collection_key` validation, attach, subscribe and detach (on
`setConfig` and on disconnect), the `subscribe()`-threw guard, the followed-period line and the fallback note.
From task 022 it keeps the comparison section, nested rows and the `hassChanged` gate. From task 025 it keeps
sorting and the sticky `.controls` observer. The comparison follows the energy period because `_period` drives
`_load()`, which loads both the report and the comparison. A new test covers this (`compare` with
`start: "2026-11-02"`).
Outside `panel.ts`, `frontend/src` and `frontend/test` contain no formatting churn: every hunk in `i18n.ts`,
`report.ts` and the tests is a functional change.

## Acceptance criteria
- [x] No conflict markers; `npm test`, `npm run typecheck`, `npm run check-bundle` pass. Verified by running them in
  the devcontainer.
- [x] Python checks unchanged. Verified: no Python files appear in the diff.
- [ ] Manual dashboard and sidebar check. Not done; this criterion is left open in the task file, which is correct.

## Findings
### Required
1. `frontend/src/card.ts:251-257` (`set hass`): `waiting` stays true for as long as no collection is found. That
   covers two states. One is a dashboard with `period_source: energy` and no picker, which is the documented
   fallback. The other is the sidebar panel when `createCardElement` returns an element whose collection never
   appears: for an unknown or failing type HA returns an error card, not `undefined`, so
   `frontend/src/panel.ts:98` does not catch this case. In both states, every entity-state-only `hass` push
   re-renders the card while the card's own picker (`<select>` controls) is on screen. The task-022 gate exists to
   prevent exactly this (the comment at `card.ts:113`). Fix: do the cheap `findEnergyCollection(...)` lookup inside
   the setter. Call `requestUpdate` only when it returns a collection that differs from `_energyBroken`, or when
   `hassChanged` is true. Add a test: with `period_source: energy` and no collection, a state-only `hass` change
   must not re-render (for example, check that `updateComplete` resolves without a render, or count calls to
   `render`). Then make the collection appear and check that the next `hass` attaches it.

### Suggestions
1. `frontend/src/panel.ts` `render()`: the `this.narrow ? ... : nothing` block and the `.content` ternary were
   reformatted in a style the rest of `frontend/src` does not use (`${` on its own line, `<svg>` split over three
   lines). Behaviour is unchanged, but these lines belong to the formatting run, not to this task. Restoring the
   previous formatting keeps the diff focused.
2. `frontend/src/panel.ts` `willUpdate`: the cost card is created first with its own picker and then recreated once
   the picker resolves. The first report and comparison request (`this_month`) is therefore wasted, and the
   card's own picker flashes briefly. One option is to wait for `_createPicker()` to settle before the first card is
   created. Its rejection or a missing helper already leads to the fallback.
3. `frontend/test/panel.test.ts`: nothing asserts that the panel passes `hass` to the picker element, either when
   the picker is created or on later `hass` updates. Nothing asserts the `has-picker` attribute either. Both would be
   cheap to add.
4. `frontend/src/panel.ts` `disconnectedCallback` and `connectedCallback`: after the panel is reconnected, the new
   `ResizeObserver` observes nothing until the next render, because `_observedPicker` is reset but no update is
   requested. The last height value stays in effect, so the impact is minor. Calling `this.requestUpdate()` in
   `connectedCallback` when `_picker` already exists would fix it.
5. While the card waits for a collection that appears later (for example, in the panel before HA's picker
   connects), the fallback warning `energy_picker_missing` is shown briefly. Consider suppressing the note during
   the first few updates, or until `hass` has been set more than once.

# 026 — Review (round 2)

Verdict: APPROVE

## Checks run
- `npm test` (devcontainer, `frontend/`) → `Test Files 7 passed (7)`, `Tests 190 passed (190)`
- `npm run typecheck` → `tsc --noEmit`, no errors
- `npm run check-bundle` → `Card bundle is up to date.`

## Previous required items
1. Resolved. `frontend/src/card.ts` `set hass` now runs `findEnergyCollection` itself and calls `requestUpdate` only
   for a usable collection (one that is not `_energyBroken`) or when `hassChanged` is true. A new test in
   `frontend/test/energy-period.test.ts` covers both halves. First, a state-only `hass` change without a collection
   must not call `render`. Second, a collection that appears later is attached on the next `hass`. The first half
   would fail against the round-1 code. The panel now also treats `hui-error-card` as no picker, and a test
   covers this.

## Regressions and churn
- The panel creates the cost card only after the picker attempt has finished. With no helpers, the early `return`
  runs before any `await`, so `finally` marks the attempt finished before the first render. The existing panel tests
  (title, card config, errors, sticky toolbar) still pass.
- The panel now requests an update on reconnect when a picker exists. A test now checks that `hass` reaches the
  picker and that the panel sets the `has-picker` attribute (round-1 suggestion 3).
- The formatter changes in `panel.ts` `render()` are gone. The only change left there is the picker row. Across
  `frontend/src` and `frontend/test`, no unrelated formatting remains.

## Findings
### Required
None.
### Suggestions
1. `frontend/src/panel.ts` `willUpdate`: the cost card waits for `_pickerSettled`. If `loadCardHelpers()` never
   settles, the panel stays empty. A short timeout (or `Promise.race`) that falls back to the card's own picker
   would bound this.
2. Round-1 suggestion 5 is still open: the `energy_picker_missing` note can flash before HA's picker creates its
   collection.
