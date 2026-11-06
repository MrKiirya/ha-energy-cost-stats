# 015 — Tariff comparison scenarios

Status: in-review (round 1: 2 required — fixed; round 2: 1 required — fixed after the review; review limit
(2 rounds) reached, so the last fix is for the human to check)
Roadmap: stage 4 (card) — author request 2026-11-06: "which tariff is cheaper for my actual usage — my current
one, single-rate or three-zone?"
Spec sections: SPEC §4 (JSON contract), §4.1 (card), §4.2 (new)

## Goal
For any period the user can see what the same consumption would have cost on other tariffs (single-rate,
two-zone, three-zone, with their own prices and optionally regional zone hours) next to the current tariff,
with the difference and the cheapest option marked.

## Context
- Russian residential tariffs are published per region as a set: single-rate, two-zone, three-zone prices; a
  household may switch. The integration already has the three presets (`engine/presets.py`).
- Re-pricing must use the *same* counted hours as the real report (quality rules, estimated/excluded hours), so
  statistics are read once and only the schedule changes: `build_report` with a one-plan `TariffSchedule`.
- Decision (taken in the night run, open for the author): scenarios live in the **card config** (YAML), sent with
  the request; nothing is stored in the integration. Storing them as subentries ("comparison plans") can be added
  later without changing the websocket contract.

## Files
- create: `custom_components/energy_cost_stats/engine/scenario.py` — `scenario_from_data`, `Scenario`, presets.
- modify: `custom_components/energy_cost_stats/report_api.py` — shared `_async_prepare` (validation + one
  statistics read), `async_get_comparison`, `parse_scenarios`.
- modify: `websocket.py` (`energy_cost_stats/compare`), `const.py`, `strings.json`, `translations/en.json`
  (`invalid_scenario`).
- modify: `frontend/src/{card,report,i18n}.ts` — `compare` config, request, "Tariff comparison" section.
- create: `tests/unit/test_scenario.py`, `frontend/test/compare.test.ts`; modify
  `tests/integration/test_report_api.py`, `frontend/test/fixtures.ts`.
- modify: `docs/SPEC.md` (§4.1 config, new §4.2).

## Tests to write first
| Level | Test | Asserts |
|---|---|---|
| unit | `tests/unit/test_scenario.py` | presets → plans (prices as decimals, comma accepted), name, period overrides; errors: missing/unknown preset, wrong zone set, non-string/negative/garbage price, unknown/invalid/uncovering periods, blank name, unknown keys; same consumption priced by single-rate and two-zone scenarios |
| integration | `test_report_api.py::test_compare_*` | actual equals the day report; single-rate 72 kWh × 7.50; three-zone per-zone kWh and cost; no configured plan → actual cost `null`, scenario priced; entities subset; errors (`invalid_scenario` incl. 0/6 scenarios, `invalid_period`, `unknown_entity`, `period_too_long`, schema), `not_loaded`; error names the scenario |
| card | `frontend/test/compare.test.ts` | no request without config; request fields (same period/end, entities, prices as strings); rows, best badge, signed differences with %; tie → no badge; null zones hidden; grouping change does not re-request; backend error shown; incomplete-current warning; config validation |

## Acceptance criteria
- [x] `script/test` → 535+ passed, engine coverage ≥ 95 % (scenario.py 100 %); `script/lint` clean; pyright 0.
- [x] Card: vitest 100 passed; `tsc` clean; bundle rebuilt and `check-bundle` up to date.
- [x] Dev HA with real statistics: comparison renders for a month and for today; numbers consistent
      (current tariff total equals the main table total).
- [ ] CI green on the PR.

## Out of scope
- Storing scenarios in the integration / a UI editor for them; a service for automations.
- Volume tiers (SPEC §3 bands), weekday-dependent tariffs.
- Per-device comparison (only totals are shown; the documents contain per-device rows already).

## Open questions
- Keep scenarios in the card config, or store them in the integration (shared by all cards, editable in the UI)?
- Real regional prices/hours for the author's tariffs to put in the docs example.

<!-- Filled in by implementer -->
## Implementation notes
- The scenario plan has `valid_from` 1970-01-01, so it covers every window; its name defaults to the preset's.
- `compare` reuses the report documents (grouping `total`) instead of a new compact format: one contract for the
  card, per-device rows available for later.
- In the card, the comparison is fetched after the report succeeded (the integration's time zone is known then),
  with its own request sequence; the "best" badge needs a unique minimum.

- Review round 1: (R1) an incomplete current tariff (unpriced hours / no plan / `null` cost) is left out of the
  "best" choice and gets no differences; (R2) the comparison is keyed by period + sensors instead of a
  "with comparison" flag: a grouping change while the new period's report is pending can no longer skip it, and
  the previous period's comparison is cleared when the key changes. Suggestions applied: unnamed scenarios get the
  localized preset name; the comparison uses the report request's own `end`; zone kWh matched by key;
  `periods` must be a mapping when given (`""`/`[]` rejected); the card's `MAX_SCENARIOS` constant is checked
  against the engine's by a unit test; refresh re-requests the comparison.

- Review round 2: (R1) a config edit (e.g. a scenario price) with the same period and sensors left the comparison
  "Loading…" forever / kept an old error: the comparison key now includes the scenarios, and `setConfig` drops the
  shown result, the error, the key and any request in flight (new test). SPEC §4.2 describes the card behaviour.

## Follow-ups
- Decide where scenarios live (see open questions); maybe a `get_comparison` service.
