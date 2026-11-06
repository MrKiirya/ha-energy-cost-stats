# 017 — Review (round 1)

Verdict: CHANGES_REQUESTED

## Checks run
- `podman exec ... ecs-dev sh script/test` → `538 passed`; `Required test coverage of 95% reached. Total coverage: 99.86%`
  (`engine/tariff_config.py` 100 %). Includes `tests/integration/test_tariff_model.py` and the updated
  `tests/integration/test_report_api.py`.
- `podman exec ... ecs-dev sh script/lint` → `All checks passed!` / `87 files already formatted`
- `podman exec ... ecs-dev uv run --group ha pyright` → `0 errors, 0 warnings, 0 informations`
- Minimum HA (2025.4.0) API check against upstream `homeassistant/config_entries.py` at tag `2025.4.0`:
  `ConfigEntries.async_add_subentry`, `async_remove_subentry`, `async_update_entry(..., version=)` and
  `ConfigEntryState.MIGRATION_ERROR` all exist with the signatures the migration uses. No 3.13/HA 2025.4 venv
  is available locally; the CI leg remains the final check.
- Principles: `tests/unit/test_engine_isolation.py` green; `rg homeassistant engine/` → only the docstring;
  `homeassistant.components.recorder` imported only by `recorder_adapter.py`; no entities or platforms added.
- Hygiene: the diff and new files only use generic ids (`sensor.plug_01`, `two_zone`, `main`), no IPs,
  hostnames, local paths or personal names.
- Deleted `subentry_flow.py` / `test_tariff_subentries.py`: no remaining references in code, tests or strings
  (only historical task 010 files mention them).

## Acceptance criteria
- [x] `script/test` green, engine coverage ≥ 95 %; `script/lint`; pyright 0 — verified by running all three
  in the container (see above).
- [x] Engine stays free of Home Assistant imports; recorder access only via the adapter — verified by grep and
  the isolation test; `engine/tariff_config.py` imports only stdlib and sibling engine modules.
- [x] SPEC §3 describes the model and the configuration shape above — §3 contains the agreed YAML shape
  verbatim, the rules, storage and migration; §2 mentions the `compare` command, `applied`/`compare` options and
  `VERSION` 2; new §4.2 documents the comparison contract and errors.

Task "Tests to write first" table: unit (presets, overrides, inheritance, explicit zones, validation errors,
short `applied`, effective schedule across a switch, comparison schedule, default compare) and integration
(migration with two plans / no plans / broken plan, report across an applied switch, compare default list,
subset, configured list, `unknown_tariff`, `not_loaded`) are all present and meaningful.

## Findings
### Required
1. `custom_components/energy_cost_stats/settings.py:112-141`, `settings.py:161-166`,
   `custom_components/energy_cost_stats/config_flow.py:219,283` — new behaviour without tests. Parsing of
   `applied`/`compare` (including the `SettingsError` paths: non-list, item not exactly `{from, tariff}`,
   non-string values, non-string compare ids), writing them to the options only when set, and the options flow
   carrying them through via `dataclasses.replace` are not covered by any test (`rg "applied|compare"
   tests/integration/test_settings.py tests/integration/test_config_flow.py` → nothing). The options flow case
   matters most: if `replace` ever regresses to building a fresh `IntegrationSettings`, saving the options
   after a v1 → v2 migration would silently drop `applied`, and every past hour would become unpriced. That
   breaks principle 3 (retroactive pricing) with no test failing. The integration coverage gate only covers
   `engine/`, so CI cannot catch this. Fix direction: in `test_settings.py`, add round-trip and error-case tests
   for `applied`/`compare`, plus a check that both keys are absent when unset. In `test_config_flow.py`, add an
   options-flow test that starts from options with `applied` and `compare`, completes the flow (both the plain
   path and the device-limits path), and asserts that both survive in `entry.options`.

### Suggestions
1. `custom_components/energy_cost_stats/__init__.py:146` — wrap the migrated subentry data in
   `MappingProxyType(...)` the way HA itself builds `ConfigSubentry` (2025.4 `config_entries.py` does
   `ConfigSubentry(data=MappingProxyType(...))`). This drops the `pyright: ignore` and keeps the data
   read-only until the entry is reloaded.
2. `tests/unit/test_tariff_config.py:164-308` — the task lists "uncovered/overlapping hours", but only the
   uncovered case is tested at this level. Add one overlap case, for example a `ru_two_zone` version with
   `hours: {t1: "06:00-23:00"}`. The check lives in `TariffPlan` and is tested in `test_tariff.py`; this case
   would pin down that hour overrides go through it.
3. `custom_components/energy_cost_stats/report_api.py:252` — `tariffs if tariffs else config.compare` treats an
   explicit `tariffs: []` like an omitted field and uses the default list. Either document that in §4.2 or use
   `tariffs is not None` so that `[]` means "actual only".
4. `custom_components/energy_cost_stats/engine/tariff_config.py:133` — `_date` accepts any `date` instance,
   which includes `datetime`. Comparing a `datetime` with a `date` later raises `TypeError` instead of
   `TariffValidationError`. This only matters once the YAML layer (task 021) passes native values in; rejecting
   `datetime` explicitly would keep parsing strict.
5. `custom_components/energy_cost_stats/__init__.py:104` — `_plan_to_version` silently drops the reserved
   `volume_band_limits_kwh` / `band_prices` of v1 plans. The v1 flow never wrote them and the engine does not
   price them, so nothing changes today. A one-line comment (or a logged warning when they are present) would
   make the loss explicit.
6. `docs/SPEC.md:29` — "Both are registered once ... take the same fields" now comes right after the new
   `compare` bullet, so "Both" reads ambiguously. Say "`report` and `get_report` are registered ...".

# 017 — Review (round 2)

Verdict: APPROVE

## Checks run
- `podman exec ... ecs-dev sh script/test` → `556 passed`; `Required test coverage of 95% reached. Total coverage: 99.86%`
  (`engine/tariff_config.py` 100 %).
- `podman exec ... ecs-dev sh script/lint` → `All checks passed!` / `88 files already formatted`
- `podman exec ... ecs-dev uv run --group ha pyright` → `0 errors, 0 warnings, 0 informations`
- Hygiene: no local paths, IPs, hostnames or personal names in the diff or the new files; only generic ids.

## Previous required items
1. Resolved. `tests/integration/test_settings.py` now covers the `applied`/`compare` round trip, both keys absent
   when unset, an explicit empty `compare` kept as `[]`, and the `SettingsError` paths: non-list, item that is not
   a mapping, missing key, extra key, non-string `from`/`tariff`, non-list and non-string `compare`.
   `tests/integration/test_config_flow.py::test_options_flow_keeps_applied_and_compare` and
   `::test_options_flow_device_limits_keeps_applied_and_compare` start from a v2 entry with `applied` and
   `compare`, complete the plain path and the device-limits path, and assert that both survive in
   `entry.options`. If `replace` regressed to a fresh `IntegrationSettings`, both tests would fail.

## Previous suggestions
1. Done. The migrated subentry data is wrapped in `MappingProxyType`, and the `pyright: ignore` is gone.
2. Done. `tests/unit/test_tariff_config.py` has the overlap case (`ru_two_zone` with `hours: {t1: "06:00-23:00"}`
   → "covered by zones").
3. Done. `report_api.py` uses `config.compare if tariffs is None else tariffs`. This is safe: the websocket
   schema has `vol.Optional(ATTR_TARIFFS)` with no default, so an omitted field is `None`, and `msg.get` passes it
   through. `test_compare_explicit_empty_list_compares_nothing` pins `[]` → `tariffs: []` with the actual
   document still priced. §4.2 documents the behaviour. Note that `entities: []` still means "all sensors", so
   the two empty lists behave differently. This is now documented, so it is acceptable.
4. Done. `_date` rejects `datetime` before the `date` check. It is used for both `valid_from` and `applied`
   `from`, so both are covered. `test_datetime_is_not_a_date` pins this, and native `date` values are still
   accepted.
5. Done. The `_plan_to_version` docstring explains why the volume-band fields are dropped.
6. Done. §2 now says "`report` and `get_report` are registered once ...".

## Findings
### Required
None.

### Suggestions
1. `docs/SPEC.md` §2 (the "`report` and `get_report` are registered" bullet) and §4.2 (first paragraph): the
   S6/S3 edits left uneven line wrapping. One line breaks after "(required; a local date", and another runs past
   the usual width. This is cosmetic only, so reflow them when convenient.
2. `tasks/017-tariff-model.md`: the status line, the implementation note about the files that could not be
   deleted, and the "Follow-ups" item about deleting `subentry_flow.py` / `test_tariff_subentries.py` are now
   out of date, because both files are staged for removal. Update the status and remove or close that follow-up
   before the commit, so the public task file matches the final state.
