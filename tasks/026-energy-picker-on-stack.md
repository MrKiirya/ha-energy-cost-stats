# 026 — Follow Home Assistant's energy date picker on top of the configuration stack

Status: in-review (round 1: CHANGES_REQUESTED; round 2: APPROVE; manual checks open)
Roadmap: stage 4 (card)
Spec sections: SPEC §4.1

## Goal
Bring task 016 (follow HA's `energy-date-selection` picker, card option `period_source: energy`) onto the current
card (tasks 022 and 025), and let the sidebar panel use Home Assistant's energy date picker instead of the card's own.

## Context
- Task 016 (`tasks/016-energy-period-sync.md`, reviewed APPROVE) was developed on the earlier card and is merged into
  this branch with conflicts in `frontend/src/card.ts`, `docs/SPEC.md` and the bundle.
- Since task 022 the card's controls are a sticky `.controls` block (task 025); when the card follows the energy
  picker its own picker is hidden, and the followed-period line takes its place.
- The sidebar panel (task 023) renders the cost card at full width with its own picker.

## Work
1. Resolve the merge: keep every behaviour of 016 (lookup of the energy collection, `collection_key`, attach /
   subscribe / detach, followed-period line, fallback note and own picker when no picker is found) together with
   022 (comparison section, hass gate, nested rows) and 025 (sorting, sticky controls). The comparison request must
   follow the energy period exactly like the report. Regenerate the bundle with `npm run build` (never hand-merge it).
2. Sidebar panel: render Home Assistant's `energy-date-selection` card above the cost card (created with the
   frontend's card helpers, e.g. `window.loadCardHelpers().createCardElement(...)`, with a panel-specific
   `collection_key`), and configure the cost card with `period_source: energy` and the same `collection_key`. If the
   helpers or the card are unavailable, fall back to the card's own picker. The picker sits in the sticky panel area.
3. Strings (en + ru) for any new texts; SPEC §4.1 describes both.

## Tests to write first
| Level | Test | Asserts |
|---|---|---|
| card | existing `energy-period.test.ts` and the 016 card tests | still pass on the merged card; compare follows the energy period; sorting and sticky controls unaffected |
| card | `panel.test.ts` | the panel creates an `energy-date-selection` card with its `collection_key` and passes `period_source: energy` + the same key to the cost card; falls back to the own picker when card helpers are missing |

## Acceptance criteria
- [x] No conflict markers; `npm test`, `npm run typecheck`, `npm run check-bundle` pass in the devcontainer.
- [x] Python checks unchanged (`ruff check .`).
- [ ] Manual: a dashboard with `energy-date-selection` + the cost card (`period_source: energy`) follows the picker;
      the sidebar panel shows HA's energy picker and the card follows it.

## Out of scope
- Changing the default `period_source` (stays `card`).

## Implementation notes
- Merge: both sides kept. The sticky `.controls` block now holds either the followed-period line or the fallback
  note plus the card's own picker; `disconnectedCallback` detaches the energy collection and the controls observer.
- The task-022 `hass` update gate would have suppressed the retry that attaches a late-appearing picker collection,
  so `hass` is now a manual accessor: while `period_source: energy` is waiting for its collection every new `hass`
  triggers an update; otherwise the gate is unchanged.
- The test mock of `energy-period.test.ts` answers `compare` requests with a comparison document; a new test checks
  that the comparison follows the picker's period.
- Panel: the picker is created asynchronously from `window.loadCardHelpers()` in `connectedCallback`; only once it
  exists is the cost card (re)created with `period_source: energy` and the same `collection_key`. Any failure or a
  missing helper leaves the card's own picker. The picker row is sticky under the toolbar; a `ResizeObserver`
  feeds its height into `--energy-cost-stats-sticky-top` (attribute `has-picker`). No new strings were needed.
- Review round 1: the `hass` setter now looks up the energy collection itself and bypasses the update gate only
  for a usable (not previously broken) one, so the fallback picker is not re-rendered on state-only updates. The
  panel treats `hui-error-card` as no picker, creates the cost card only after the picker attempt settled, passes
  `hass` to the picker, and re-requests an update on reconnect.
- Manual dashboard checks (last criterion) are not done here.

## Follow-ups
- Fall back to the card's own picker after a short timeout if `loadCardHelpers()` never resolves.
- Suppress the "no energy date picker" note while the picker's collection is still being created.
