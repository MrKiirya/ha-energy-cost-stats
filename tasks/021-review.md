# 021 — Review (round 1)

Verdict: CHANGES_REQUESTED

## Checks run
- `uv run --no-sync pytest --cov=custom_components/energy_cost_stats/engine --cov-report=term-missing --cov-fail-under=95`
  (devcontainer, Python 3.14, HA 2026.9) → `907 passed`; `Required test coverage of 95% reached. Total coverage: 99.89%`
- `uv run --no-sync pytest -m unit` → `502 passed, 405 deselected`
- No-HA environment (fresh `uv sync` without the `ha` group, simulating the `unit (windows, no HA)` job):
  `pytest -m unit` → `502 passed`; `pytest -m integration` → `502 deselected` (no tests ran, exit code 5 expected
  by CI); `import homeassistant` fails as intended.
- `uv run --no-sync ruff check .` → `All checks passed!`
- `uv run --no-sync ruff format --check .` → `112 files already formatted`
- `uv run --no-sync pyright` → `0 errors, 0 warnings, 0 informations`
- HA 2025.4.0 sources (`setup.py`, `config_entries.py`, `data_entry_flow.py`, `helpers/reload.py`,
  `helpers/service.py`, `helpers/issue_registry.py`, `util/yaml/__init__.py` at tag `2025.4.0`) read and compared
  with every new API call. The 2025.4.0 test leg itself was not run locally (CI only).

## Focus areas
- **Verified:** lenient `CONFIG_SCHEMA` (setup is not aborted by a list or string block); invalid block at startup
  and on reload leaves the entry and its options untouched and raises the repair; block removal keeps the last YAML
  values and returns to UI mode; read-only options flow (menus only, and Home Assistant validates `next_step_id`
  against `menu_options`, so UI steps are not reachable); tariff subentry `user` / `reconfigure` aborts; the update
  listener skips reconcile in YAML mode and a deleted subentry is restored; export → parse → normalize round trip;
  JSON Schema draft-07 validity and the key-sync test in both directions; `jsonschema` only in the `dev` group,
  `rpds-py` has Windows wheels for cp313 / cp314; `tests/unit/test_config_schema.py` imports neither `engine…` nor
  the integration package (file reads, `yaml`, `jsonschema` only).
- **Startup import race:** HA 2025.4.0 `_async_setup_component` awaits
  `flow.async_wait_import_flow_initialized(domain)` after `async_setup` and then sets up all entries of the domain;
  `ConfigEntries.async_setup` for a domain still being set up defers to the component setup. A reload during a
  pending import starts a second import flow, which Home Assistant aborts (`single_instance_allowed` in
  `async_init` and `async_finish_flow`, other in-progress flows of a single-entry domain are aborted). No double
  import found.
- **HA 2025.4.0 APIs:** `async_integration_yaml_config(hass, name, *, raise_on_failure=False)`,
  `async_register_admin_service(hass, domain, service, func, schema=...)`, `async_create_issue` /
  `async_delete_issue` / `IssueSeverity`, `util.yaml.dump` / `parse_yaml`, `ConfigSubentry(data, subentry_type,
  title, unique_id)`, `async_add_subentry` / `async_remove_subentry` / `async_update_subentry` all exist with the
  used signatures at 2025.4.0.
- **Not verified:** that Developer tools → YAML lists the integration (frontend source not checked), Export
  rendering in the frontend, behaviour with the block split across packages, editor completion. These remain the
  manual acceptance item.

## Acceptance criteria
- [x] `pytest -m unit` green incl. `test_config_schema.py`, also without Home Assistant; engine coverage 99.89 %.
- [x] `pytest -m integration` green on latest HA (2025.4.0 leg left to CI; APIs checked against the sources).
- [x] ruff check / format clean; pyright 0 errors.
- [x] `services.yaml` has `reload:`; `strings.json` has `services.reload`, `issues.invalid_yaml`,
      `exceptions.yaml_invalid` (hassfest / hacs jobs themselves not run locally).
- [x] No `homeassistant` imports in `engine/`, `settings.py`, `yaml_config.py` (grep and
      `test_settings_and_yaml_config_have_no_ha_imports`).
- [x] `homeassistant.components.recorder` only in `recorder_adapter.py`.
- [x] No `empty_config_schema`; list / string blocks load (`test_invalid_yaml_without_entry`,
      `test_invalid_yaml_at_startup_keeps_last_config`).
- [x] YAML-mode steps only show menus; no path to `async_create_entry` (code read and
      `test_options_read_only_in_yaml_mode`).
- [x] Config entry `VERSION` / `MINOR_VERSION` unchanged.
- [x] The design example loads, validates against the schema and round-trips through Export.
- [x] Schema exists, draft-07, root = block content, sync tests green. Note: `test_corpus_covers_every_top_level_key`
      checks `valid/` and `invalid_structure/` only, not `invalid_semantic/` (see Suggestion 6).
- [x] `jsonschema` in the `dev` group only; `uv.lock` adds `jsonschema`, `jsonschema-specifications`,
      `referencing`, `rpds-py`.
- [ ] Manual check in the dev HA and an editor — not done (recorded as such in Implementation notes); needs a human
      before merge.
- [x] SPEC §2 / §3 / §6 / §6.1, README, CONFIG-DESIGN and CLAUDE.md updated.

## Findings
### Required
1. `custom_components/energy_cost_stats/yaml_mode.py:191` — the "YAML configuration replaces the configuration
   made in the UI" warning is suppressed for every entry whose `source` is `import`. Scenario: the entry is created
   from YAML, the block is removed (the entry becomes editable, as designed), the user edits tariffs and options in
   the UI, then adds a block again. `async_sync_entry` overwrites those UI edits and removes UI-added tariff
   subentries without any log line, because the entry's source is still `import`. Since there is no backup by
   design, this warning is the only signal that a UI configuration was replaced, so the YAML → UI → YAML path
   loses data silently. The source check exists to avoid a spurious warning right after the import (options equal,
   subentries not yet added). Direction: base the condition on the entry content instead of its source, e.g. warn
   when the entry has existing tariff subentries or options that differ from the document (a fresh import has
   equal options and no subentries), keeping the once-per-process `DATA_SYNCED` guard; add a test for the
   import → block removed → UI edit → block re-added sequence asserting the warning.

### Suggestions
1. `yaml_mode.py:213-219` — the new subentry gets the document's own `dict` as `data` (with a
   `pyright: ignore`), so the stored subentry and `YamlState.document` share mutable objects. The v1 migration in
   `__init__.py:186` wraps data in `MappingProxyType`; doing the same with a deep copy here removes the ignore and
   the aliasing.
2. Schema stricter than the parser in a few structural spots the corpus does not cover: `tariffs: null`,
   `applied: null` and `compare: null` are accepted by `document_from_yaml` (treated as absent) but rejected by the
   schema; price strings with surrounding spaces (`parse_price` strips) and limit strings such as `"1e-5"`
   (`Decimal` parses) are accepted by the parser but fail the decimal pattern. Either reject these in the parser or
   allow them in the schema, and add a fixture for the chosen behaviour so the corpus documents the boundary.
3. `tests/integration/test_yaml_schema_sync.py:101-115` — `_closed_objects` walks `properties`, `items`,
   `additionalProperties`, `oneOf` and `anyOf` but not `allOf` / `if` / `then` / `else` / `not`. A closed object
   added later under one of those would escape the reverse key check; walking them too keeps the guarantee general.
4. YAML mode with an invalid block: the update listener skips reconcile and reloads, but there is no valid document
   to re-sync from, so a tariff subentry deleted from the integration page is not restored and, if it was in
   `applied`, the entry fails setup until the block is fixed. Consider documenting this in SPEC §2 or skipping the
   reload in that state.
5. `CLAUDE.md:83` — the schema-sync convention line sits in the "Public repo hygiene" list; the task asked for it
   under Test levels / conventions, where it is easier to find.
6. The acceptance criterion says "at least one fixture per folder for every top-level key", while
   `test_corpus_covers_every_top_level_key` covers `valid/` and `invalid_structure/`. Either reword the criterion
   or state in the test docstring why `invalid_semantic/` is exempt (some keys, e.g. `panel`, have no semantic rule).
7. `test_yaml_schema_sync.py::test_schema_validates_exports` validates only `document.options` of the design
   example (no tariffs), which is weaker than its name suggests; the full check is already in
   `test_yaml_config.py::test_export_round_trip`. Rename it or validate the full exported block.
8. The manual acceptance item (Developer tools listing, reload without restart, repair display, Export code block,
   editor completion with the modeline) should be performed and recorded before the PR leaves draft.

# 021 — Review (round 2)

Verdict: APPROVE

## Checks run
- `uv run --no-sync pytest --cov=custom_components/energy_cost_stats/engine --cov-report=term --cov-fail-under=95`
  (devcontainer, Python 3.14, HA 2026.9) → `917 passed`; `Required test coverage of 95% reached. Total coverage: 99.89%`
- `uv run --no-sync ruff check .` → `All checks passed!`
- `uv run --no-sync ruff format --check .` → `113 files already formatted`
- `uv run --no-sync pyright` → `0 errors, 0 warnings, 0 informations`

## Previous required items
1. Resolved. `yaml_mode.async_sync_entry` now warns when the document changes the entry and the entry has content
   of its own (existing tariff subentries or options that differ from the document). A fresh import has equal
   options and no subentries, so it does not warn. Removing the block clears the once-per-process guard, so later
   UI edits are reported when a block replaces them again.
   `test_warning_when_yaml_replaces_ui_edits_after_import` covers import → block removed → UI edit (option and
   added tariff) → block re-added, and checks both the warning and the replaced content.

## Previous suggestions
1. Done: new subentries get `MappingProxyType(copy.deepcopy(tariff))`, and the `pyright: ignore` is gone.
2. Done: the schema accepts `null` for `tariffs` / `applied` / `compare`, decimal strings with surrounding spaces,
   and exponent strings (one shared `decimal` definition). New fixtures: `valid/null_collections`,
   `valid/price_with_spaces`, `valid/spike_limit_exponent_string`, and `invalid_semantic/price_exponent`, which
   records that the parser rejects exponents in prices but accepts them in limits.
3. Done: `_closed_objects` also walks `allOf`, `if`, `then`, `else` and `not`.
4. Done. The update listener now skips reconciliation only while a valid YAML document is loaded. With an invalid
   block it reconciles the options against the tariffs that exist, so the entry still loads after a subentry is
   deleted. No data is lost: the YAML file stays the source of truth, and the next valid load restores the
   subentry and `applied`. No restore loop: reconciling writes the options once, and the listener call that
   follows finds them consistent and only reloads. `test_invalid_block_and_deleted_subentry_does_not_fail_setup`
   covers this; `async_block_till_done` would hang on a loop. The UI stays read-only in that state.
5. Done: the convention line in `CLAUDE.md` is now a standalone "Convention" bullet.
6. and 7. Done: the corpus wording is aligned, and the full export is validated against the schema.

## Findings
### Required
None.
### Suggestions
1. Run the manual acceptance check (Developer tools → YAML listing, reload without restart, the repair, how the
   Export code block renders, editor completion with the modeline) and record the result in the task file before
   the PR leaves draft. The HA 2025.4.0 test leg is checked by CI only.
