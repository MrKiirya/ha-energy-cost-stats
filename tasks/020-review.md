# 020 — Review (round 1)

Verdict: CHANGES_REQUESTED

## Checks run
Run in the devcontainer (HA 2026.9.3, Python 3.14) with `uv run --no-sync`:
- `pytest --cov=custom_components/energy_cost_stats/engine --cov-report=term-missing --cov-fail-under=95` →
  `726 passed`; `Required test coverage of 95% reached. Total coverage: 99.89%` (`engine/sensors.py` 100 %).
- `pytest -m unit` → `447 passed, 279 deselected`.
- `pytest -m integration` → `279 passed, 447 deselected`.
- `ruff check .` → `All checks passed!`
- `ruff format --check .` → `104 files already formatted`
- `pyright` → `0 errors, 0 warnings, 0 informations`
- Home Assistant 2025.4.0 APIs checked against the 2025.4.0 sources (not run): `energy/data.py`
  (`async_get_manager` is a `@singleton` coroutine, `manager.data: EnergyPreferences | None`, `included_in_stat`
  in the TypedDict and in `DEVICE_CONSUMPTION_SCHEMA`), `helpers/selector.py` (`TargetSelectorConfig.entity`,
  `EntityFilterSelectorConfig(domain, device_class)`, `TextSelectorConfig.multiple`,
  `SelectSelectorConfig.translation_key`), `data_entry_flow.add_suggested_values_to_schema` (recurses into
  sections), `recorder/statistics.get_metadata` (keyword-only `statistic_ids` / `statistic_type` /
  `statistic_source`), `area_registry.async_get_area`, `AreaEntry.floor_id` / `labels`, entity and device registry
  `area_id` / `labels` / `device_class` / `original_device_class`, `config_entries.async_migrate` (at 2025.4.0 the
  migration is called even for a newer stored major, so the `version > 3` guard is needed and correct), and
  `script/hassfest/dependencies.py` (`after_dependencies` is an allowed reference; `energy` has no dependency on
  this integration, so no cycle). All compatible.
- hassfest / hacs and the 2025.4.0 test leg were not run locally (CI).

## Acceptance criteria
- [x] Unit tests green, engine coverage ≥ 95 % incl. `engine/sensors.py` — verified by the coverage run above.
- [x] Integration tests green — verified on HA 2026.9.3 / py3.14; the 2025.4.0 leg is left to CI (API surface
      checked against the 2025.4.0 sources, see above).
- [x] Lint and pyright clean — verified above.
- [x] hassfest / hacs — not run; `manifest.json` has `"after_dependencies": ["frontend", "energy"]`, the
      `strings.json` / `translations/en.json` additions use the same shapes (menus, sections, selector options) that
      already pass hassfest from task 019, and both files are identical.
- [x] No `homeassistant` imports in `engine/` or `settings.py` — verified by grep (only docstring mentions).
- [x] `homeassistant.components.recorder` only in `recorder_adapter.py` — verified by grep.
- [x] `homeassistant.components.energy` only in `sensor_resolver.py` (lazy import inside
      `async_dashboard_devices`) — verified by grep.
- [x] No `exclude_energy_sources` / `async_extract_referenced_entity_ids` / `primary_entities_only` /
      `unit_of_measurement` filter — verified by grep.
- [x] `"entities"` / `device_spike_limits` in `settings.py` only in `migrate_sensor_options` — verified by grep.
- [x] `VERSION == 3`; a version-2 entry loads after migration with the same sensors — verified in `config_flow.py`
      and `test_migrate_v2_to_v3` (settings level; see Suggestion 3 for the report-level assertion).
- [x] Stored `sensors` shape equals the CONFIG-DESIGN `sensors:` block — verified in `_sensors_to_data` and the
      round-trip tests (`include: "all"` string, `exclude` / `overrides` always written, empty target keys omitted).
- [x] `init` menu unchanged; spike limits reachable via `sensors` → `device_limits` — verified in
      `test_options_menu.py` and `test_sensors_options.py`.
- [x] `docs/SPEC.md` §2 / §4 / §6 updated — verified in the diff.

Migration (v2 → v3): `migrate_sensor_options` copies the options and only pops `entities` /
`device_spike_limits`; `applied`, `compare`, `panel`, `time_zone`, `spike_limit` are preserved, every limit
(including `null`) becomes an override, and the v1 path continues into the v2 step in the same call. No data loss
found.

Removed 019 option tests: the entity-picker tests (`select_entities_and_reload`, `rejects_non_energy_entity`,
`keeps_missing_previous_entity`) have no counterpart because the picker no longer exists;
`drops_overrides_of_deselected` is intentionally reversed (overrides are kept) and covered by
`test_device_limits_fields_and_save`; `device_limits_without_entities_saves_directly` is replaced by
`test_device_limits_no_sensors_aborts`; reload after save is covered by `test_select_filter_preview_then_save`.
The prefill of the stored selection is only partially covered (Suggestion 3).

## Findings
### Required
1. `custom_components/energy_cost_stats/report_api.py:177` and `engine/report.py:282` — a sensor is treated as
   nested (and dropped from every `total` row) as soon as its upstream id is among the requested ids, regardless of
   whether the upstream has any data. If the upstream's read status is not `ok` (`no_statistics` after its
   statistics were deleted, `unsupported` unit) or its statistics start later than the child's (a sub-meter added to
   the Energy dashboard after the plug inside it), the child's consumption is missing from the totals for those
   hours while no other row accounts for it, so totals and costs silently under-count. This is a partial-data
   correctness issue in exactly the retroactive reports the integration is built for. Direction: compute the
   nesting after the read and only nest under an upstream whose status is `ok` (walking further up the chain or
   leaving the child un-nested otherwise), with an integration test (parent in the dashboard without statistics →
   child counted in the totals, `upstream` `null`). For the per-hour case either exclude a nested row's hour from a
   `total` only when the upstream has a value for that hour (engine change, unit test), or state the limitation
   explicitly in SPEC §4 (`devices[].upstream`) and add a follow-up to the task file.

### Suggestions
1. `docs/CONFIG-DESIGN.md:108` still says targets are "resolved by Home Assistant's target helpers". The task
   decided to resolve them from the registries (hidden and categorized entities are not skipped, unlike HA's
   helpers); update the sentence so the design document matches SPEC §2 / §6.
2. `custom_components/energy_cost_stats/config_flow.py:361` — `_MODE_LABELS` passes hard-coded English mode names
   into the `{mode}` placeholder, which cannot be translated (task 024). Consider two description variants or a
   translated label (for example a dedicated menu step per mode, or omitting `{mode}` and relying on the form).
3. Test gaps worth closing: `invalid_target` and the string → list normalization of target values are not
   exercised (`_string_list`, `_target_from_input`); the prefill of a stored filter target / exclude when entering
   `sensors_select` from the menu is not asserted (only `mode` and `include.all` are); `test_migrate_v2_to_v3` does not
   run a report to show "a report returns the same sensors" as listed in the task table;
   `test_select_filter_preview_then_save` does not include `applied` / `compare` in the options, so the "keeps
   `applied`, `compare`" part of its row is only covered indirectly by `test_save_uses_current_options`.
4. `custom_components/energy_cost_stats/sensor_resolver.py:173` — an empty selection renders `-` (an empty
   Markdown bullet) after "0 sensors in the calculation:". A short translated hint ("No sensors match the
   selection.") would read better and help users who just saved an over-broad exclude.
5. At 2025.4.0 the target selector validates with `cv.TARGET_SERVICE_FIELDS`, which also accepts entity registry
   ids and the `all` / `none` keywords; `_target_from_input` stores them verbatim and they match nothing. Consider
   rejecting values that are not entity ids (`entity_id`) with `invalid_target`, or documenting that they are
   ignored.
6. Two dashboard devices that point at each other (`included_in_stat` cycle) both stay un-nested and are therefore
   counted twice in the totals. The behaviour is documented in SPEC §2; a debug log when a cycle is detected
   would make such misconfigurations easier to diagnose.
7. Every report request now runs `get_metadata` over all recorder sum statistics and walks the entity registry
   and state machine. Fine for typical installations; keep it in mind if the card's request rate grows (caching is
   out of scope for this task).

---

# 020 — Review (round 2)

Verdict: CHANGES_REQUESTED

## Checks run
Run in the devcontainer (HA 2026.9.3, Python 3.14) with `uv run --no-sync`:
- `pytest --cov=custom_components/energy_cost_stats/engine --cov-report=term-missing --cov-fail-under=95` →
  `741 passed`; `Required test coverage of 95% reached. Total coverage: 99.89%` (`engine/report.py` and
  `engine/sensors.py` 100 %).
- `pytest -m unit` → `449 passed, 292 deselected`.
- `pytest -m integration` → `292 passed, 449 deselected`.
- `ruff check .` → `All checks passed!`
- `ruff format --check .` → `105 files already formatted`
- `pyright` → `0 errors, 0 warnings, 0 informations`
- `er.async_resolve_entity_id` (new in `config_flow.py`) checked against the 2025.4.0 sources: present with the
  same signature and semantics (a valid entity id is returned unchanged, a registry id is resolved, anything else is
  `None`).
- Ad-hoc engine probe (not committed): three devices `a ⊂ b ⊂ c`, `c` 1 kWh every hour, `b` 0.6 kWh only from
  hour 12, `a` 0.5 kWh every hour, `nested = {a: b, b: c}` → `totals.total.kwh == 30.0` instead of `24`.

## Previous required items
1. Nested totals ignoring upstream data availability — **partly resolved.**
   - Status: `report_api._async_prepare` now computes `upstreams` over the ids whose read status is `ok` only, so
     an unreadable parent no longer hides its child and the nearest readable ancestor takes over
     (`test_nested_child_counts_when_upstream_unreadable`). Resolved.
   - Per hour: `engine/report.py` builds the `total` rows from their own accumulators and skips a nested device's
     hour only when its upstream has a counted (measured or estimated) value in that hour. Verified:
     - Decimal exactness: the totals accumulate the same `Decimal` values under `prec=50`, so for reports without
       nesting the totals equal the old sum of rows (all pre-existing report tests unchanged and green;
       `test_totals_skip_nested_devices` compares the totals with a parent-only report field by field).
     - Per-zone pricing: every counted hour of the total is priced with that hour's zone and price
       (`zone_of[i]`, `price_of[i]`), so a child's hours before the parent existed are split into zones correctly;
       the zone costs sum to the total cost (`test_nested_child_counts_where_upstream_has_no_value`).
     - Estimated upstream hours (gap spread) count as covered, so the child is skipped there; missing upstream hours
       let the child count (same test, hourly buckets 0–2, 12 and 15).
     - Spike-excluded upstream hours let the child count
       (`test_nested_child_counts_when_upstream_hour_is_excluded`).
     - Coverage of the total counts each contributing device-hour once; skipped child hours contribute nothing.
   - **Multi-level nesting is not handled** — see Required 1 below.

## Previous suggestions
1. CONFIG-DESIGN target resolution sentence — resolved (`docs/CONFIG-DESIGN.md:108`).
2. Untranslatable `{mode}` label — resolved (the placeholder and `_MODE_LABELS` were removed).
3. Test gaps — resolved for `invalid_target` / normalization (`test_target_normalization`,
   `test_target_rejects_unsupported_values`), stored-selection prefill (`test_select_prefills_stored_target_and_exclude`)
   and `applied` / `compare` preservation (`test_preview_and_save_keep_applied_and_compare`). Still open:
   `test_migrate_v2_to_v3` asserts the migrated settings but does not run a report (the task table asks for "a
   report returns the same sensors"); see Suggestion 1.
4. Empty selection — resolved as described (`test_empty_selection_lists_nothing`).
5. Registry ids and `all` / `none` keywords in the target value — resolved: registry ids are resolved with
   `er.async_resolve_entity_id`, keywords and unresolvable values are rejected with `invalid_target`
   (`test_select_resolves_registry_ids_and_rejects_keywords`).
6. Cycle diagnostics — resolved (`engine/sensors.py` logs at debug level; stdlib `logging` keeps the engine free of
   `homeassistant` imports; `test_upstreams_cycle_safe` checks the message).
7. Per-request cost — recorded as a follow-up in the task file.

## Findings
### Required
1. `custom_components/energy_cost_stats/engine/report.py` (total accumulation loop after `# Total rows: ...`) —
   the per-hour check only looks at the **immediate** upstream. With a chain `a ⊂ b ⊂ c` in one report, an hour where
   `b` has no counted value but `c` does counts `a` in the total although `a`'s energy is already part of `c`, so it
   is counted twice (probe above: 30 kWh instead of 24). This is the realistic case the round-1 item was about: a
   sub-meter `b` added to the Energy dashboard after the plug `a` and the circuit `c` already had history. SPEC §2
   (`docs/SPEC.md:105-108`) states that a nested device "is not counted twice and not lost either", which does not
   hold for chains. Direction: for each hour, skip a nested device's value when **any** ancestor reachable through
   `nested` (walk `nested[a] → nested[b] → …`, cycle-safe, ids of the report only) has a counted value in that hour;
   add a unit test with a three-level chain where the middle device starts later (expected total = the top device
   only for hours where it has a value) and one where the top device has a gap (the middle device covers it).

### Suggestions
1. `tests/integration/test_config_flow.py:430` — run a report after migrating the version-2 entry and assert the
   device ids, as listed in the task's test table.
2. `tasks/020-sensors.md:364` — the follow-up reads "(review suggestion 7, no change made)"; describe the follow-up
   on its own terms instead of referring to the review process.
3. `docs/SPEC.md:108` and the `devices[].upstream` paragraph, and `docs/CONFIG-DESIGN.md:108`, now exceed the
   line width used elsewhere in these documents; rewrap for consistency.

---

# 020 — Review (round 3)

Verdict: APPROVE

## Checks run
Run in the devcontainer (HA 2026.9.3, Python 3.14) with `uv run --no-sync`:
- `pytest --cov=custom_components/energy_cost_stats/engine --cov-report=term-missing --cov-fail-under=95` →
  `744 passed`; `Required test coverage of 95% reached. Total coverage: 99.89%` (`engine/report.py` 100 %).
- `pytest -m unit` → `452 passed, 292 deselected`.
- `pytest -m integration` → `292 passed, 452 deselected`.
- `ruff check .` → `All checks passed!`
- `ruff format --check .` → `105 files already formatted`
- `pyright` → `0 errors, 0 warnings, 0 informations`
- Round-2 engine probe (`a ⊂ b ⊂ c`, middle device starting at hour 12) re-run → `totals.total.kwh == 24`
  (was 30.0).

## Previous required items
1. Multi-level nesting double count — **resolved.** The total accumulation in `engine/report.py` now collects every
   ancestor reachable through `nested` (cycle-safe via a `seen` set, ids outside the report skipped) and leaves a
   nested hour out of the totals when any of them has a counted value in that hour. Unit tests cover the
   three-level chain with a late middle device, a gap in the top device (the middle device covers it) and a cyclic
   mapping (terminates; the integration never passes one because `upstreams` gives cycle members no upstream).
   Single-level behaviour, zone pricing and coverage are unchanged (all earlier nesting tests green).

## Previous suggestions
1. `test_migrate_v2_to_v3` now seeds statistics and runs a report after migration, asserting the same device ids —
   resolved.
2. Task-file follow-up reworded without process references — resolved.
3. Rewrapped lines — resolved for the §2 nesting paragraph and CONFIG-DESIGN; the `devices[].upstream` paragraph in
   SPEC §4 still has one long line (cosmetic, see below).

## Findings
### Required
None.

### Suggestions
1. `docs/SPEC.md` §4, `devices[].upstream` paragraph — one line still exceeds the document's usual width; rewrap
   when the file is next touched.
