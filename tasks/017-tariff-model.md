# 017 — Tariffs with versions, applied history and comparison

Status: in-review (round 1: CHANGES_REQUESTED; round 2: APPROVE)
Roadmap: stage 4 follow-up (tariff model v2; prerequisite for the tariff forms, YAML configuration and the
card's tariff comparison)
Spec sections: SPEC §3 (rewritten), §2, §4.2 (new)

## Goal
Tariffs become named, versioned objects: a tariff has a stable `id`, a display `name` and versions (`valid_from`
+ zones with prices and hours). Which tariff was actually applied, and from which date, is a separate list
(`applied`), so a household can switch tariffs over time; any other tariff can be priced over the same consumption
for comparison. The internal configuration document has exactly the shape of the planned YAML configuration
(task 021), so the forms (task 018) and YAML write and read the same thing.

## Target configuration shape (agreed)
```yaml
energy_cost_stats:
  tariffs:
    - id: two_zone                       # ^[a-z0-9_]{1,32}$, stable
      name: Two-zone                     # display name, any language
      versions:
        - valid_from: 2026-01-01
          preset: ru_two_zone            # single_rate | ru_two_zone | ru_three_zone
          prices: { t1: "8.10", t2: "3.20" }
          hours: { t1: "07:00-23:00" }   # optional per-zone override of the preset hours
        - valid_from: 2026-07-01         # zones (keys, names, hours) inherited from the previous version
          prices: { t1: "8.75", t2: "3.45" }
    - id: three_zone
      name: Three-zone
      versions:
        - valid_from: 2026-07-01
          zones:                         # explicit zones instead of a preset
            - { key: t1, name: Peak,      price: "10.20", hours: "07:00-10:00, 17:00-21:00" }
            - { key: t3, name: Semi-peak, price: "8.75",  hours: "10:00-17:00, 21:00-23:00" }
            - { key: t2, name: Night,     price: "3.45",  hours: "23:00-07:00" }
  applied:                               # or the short form: applied: two_zone
    - { from: 2026-01-01, tariff: two_zone }
  compare: [three_zone]                  # optional; default: every tariff that is never applied
```
Sensors, panel and general settings belong to later tasks (019–021) and are not part of this document yet.

## Rules
- **Versions.** Sorted by `valid_from`, distinct dates. The first version needs `preset` or `zones`. A later
  version may omit both: it inherits the previous version's zones and must give `prices` for exactly those keys;
  `hours` may override the hours of inherited zones. A version with `preset` or `zones` starts a new zone set.
  With a preset, `prices` must name exactly the preset's keys; `zones` and `preset` are mutually exclusive.
- **Hours** are text `"HH:MM-HH:MM, ..."` (whole hours, `24:00` = end of day); every version covers each hour of
  the day exactly once. A mapping form for weekday-dependent hours (`{mon-fri: "...", sat-sun: "..."}`) is
  reserved: it is rejected with a clear message for now.
- **Applied.** Sorted, distinct `from` dates; each `tariff` must exist and must have a version valid on its `from`
  date (no unpriced gap inside the applied history). Hours before the first `from` are unpriced. The short form
  `applied: <id>` means "from the first version of that tariff". No `applied` (or no tariffs) → every hour unpriced.
- **Effective schedule** for the real cost: for each applied interval `[from_i, from_i+1)`, the version of the
  applied tariff in force at `from_i` (re-dated to `from_i`) plus its later versions inside the interval.
- **Comparison.** A compared tariff is priced with its own versions only (hours before its first version are
  unpriced). `compare` lists tariff ids; default = all tariffs that never appear in `applied`.
- **Prices** are decimal strings in the document (money never as float); numbers are accepted only by the YAML
  layer (task 021), which converts them.

## Storage and migration
- One config subentry of type `tariff` per tariff; `unique_id` = `id`; title = `name`; data = the tariff's
  document (as above, presets kept as written so the forms and the YAML export show what the user entered).
- `entry.options` gains `applied` (list of `{from, tariff}`) and optional `compare` (list of ids).
- Config entry `version` 1 → 2 migration: existing `tariff_plan` subentries become one tariff `id: main`
  (name of the latest plan) whose versions are the old plans with explicit zones; `applied: [{from: <first
  valid_from>, tariff: main}]`; the old subentries are removed. No plans → no tariff, no `applied`.
- The `tariff_plan` subentry flow is removed; the `tariff` forms come in task 018 (same stack, merged together).

## API
- `energy_cost_stats/report` / `get_report`: unchanged contract; priced with the effective schedule.
- New websocket `energy_cost_stats/compare` (read-only): `start`, `end`, optional `entities`, optional `tariffs`
  (ids; default = the configured `compare`). Statistics are read once; returns
  `{ "actual": <document>, "tariffs": [ { "id", "name", "report": <document> } ] }` with §4 documents, grouping
  `total`. Errors as `report`, plus `unknown_tariff`.

## Files
- create: `engine/tariff_config.py` — `Tariff`, `AppliedChange`, `TariffConfig`, `config_from_data`,
  `effective_schedule`, `comparison_schedule`, `default_compare`.
- modify: `engine/presets.py` (preset table: keys, default names, hours), `settings.py` (`applied`, `compare`),
  `__init__.py` (load tariffs from subentries, migration), `report_api.py` (shared prepare, comparison),
  `websocket.py`, `const.py`, `strings.json`, `translations/en.json`.
- delete: `subentry_flow.py` (`tariff_plan` flow; replaced in task 018), related strings.
- tests: `tests/unit/test_tariff_config.py`; integration tests for migration, report with applied history, compare.
- docs: SPEC §3 rewritten for the new model, §2, new §4.2.

## Tests to write first
| Level | Test | Asserts |
|---|---|---|
| unit | `test_tariff_config.py` | preset expansion and hour overrides; inheritance of zones; explicit zones; validation errors (ids, duplicate ids/dates, first version without zones, price key mismatch, preset + zones, uncovered/overlapping hours, weekday mapping reserved, applied refs/order/no version at `from`, compare refs); short `applied`; effective schedule across a tariff switch (re-dated version, later versions, zone keys change); comparison schedule; default compare |
| integration | migration | v1 entry with two `tariff_plan` subentries → v2 with one `tariff` subentry + `applied`; no plans → nothing |
| integration | report | cost follows the applied history across a switch date inside the window |
| integration | compare | actual + compared tariffs over the same counted kWh; default list; `tariffs` subset; `unknown_tariff` |

## Acceptance criteria
- [x] `script/test` green, engine coverage ≥ 95 %; `script/lint`; pyright 0.
- [x] Engine stays free of Home Assistant imports; recorder access only via the adapter.
- [x] SPEC §3 describes the model and the configuration shape above.

## Out of scope
- The `tariff` forms and the options menu (018, 019), sensor selection (020), YAML mode / reload / export (021),
  the card's comparison section (022), sidebar panel (023), Russian translations (024).
- Weekday-dependent hours and volume bands (reserved, see Rules).

## Implementation notes
- `engine/tariff_config.py`: `AppliedChange` fields are `(from_date, tariff)`; `TariffConfig.compare` is already
  resolved (explicit list, else `default_compare`). Version names equal the tariff name. Presets live in
  `engine/presets.py::PRESET_ZONES` (the old `single_rate`/`ru_*` factory functions stay for their tests).
- Settings keep `applied` as `(iso_date, tariff_id)` pairs and `compare` as `tuple | None`; they are written to
  the options only when set. The options flow now carries them through (`dataclasses.replace`).
- Config entry `VERSION = 2`; `async_migrate_entry` in `__init__.py` uses `async_remove_subentry`,
  `async_add_subentry` and `async_update_entry(version=2)` (all present in HA 2025.4.0). A stored plan that fails
  strict parsing makes the migration return `False` (test `test_migration_of_a_broken_plan_fails`).
- `report_api.py`: `_async_prepare` (validation + one statistics read) and `_async_priced_document`, used by
  `async_get_report` and the new `async_get_comparison`. `unknown_tariff` has a translated exception message.
- Tests: `tests/unit/test_tariff_config.py` keeps the planned cases (plus `assert ... is not None` lines for
  pyright) and adds an overlapping-hours case. Extra edge cases in `tests/unit/test_tariff_config_edges.py` (coverage).
  `tests/integration/test_report_api.py` now builds a v2 entry (tariff subentry + `applied`) and its
  `test_all_error_codes_translated` includes `unknown_tariff`. New `tests/integration/test_tariff_model.py`.
- The old `tariff_plan` flow (`subentry_flow.py`) and its tests (`test_tariff_subentries.py`) are removed.
- The `preset` selector strings were removed together with the `tariff_plan` subentry strings; task 018 re-adds
  what the new forms need.
- Plan/spec detail: `plan_codec.py` is still used by the migration and the report's `plans` serialization.

## Follow-ups
None.
