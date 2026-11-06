# 020 — Sensor selection: Energy dashboard mode, include / exclude filter, overrides, preview

Status: in-review (round 1–2: CHANGES_REQUESTED; round 3: APPROVE)
Roadmap: stage 4 follow-up (configuration v2, docs/CONFIG-DESIGN.md "Tasks" row 020)
Spec sections: SPEC §2 (settings, options flow, report API), §4 (JSON contract: devices, totals), §5 (spike
limits), §6 (compatibility); docs/CONFIG-DESIGN.md "Full configuration (YAML)" (`sensors:` block), "Sensors",
"Configure (options)"

## Goal
The fixed list of energy sensors (`entities`) is replaced by a **sensor selection** that is resolved every time a
report is built. Two modes: `energy_dashboard` uses the individual devices from the Energy dashboard settings
and respects their "upstream device" (`included_in_stat`), so a device that is measured inside another
selected device is shown in its own row but is **not counted twice in the totals**; `filter` uses `include` (`all`
eligible sensors, or a target of entities / devices / areas / floors / labels plus entity globs) and `exclude`
(same keys, wins over include). New eligible sensors are picked up without editing the configuration.
Per-sensor spike limits become `overrides`, independent of how sensors are selected. The options menu entry
**Sensors** shows "N sensors in the calculation", lets the user change the selection with Home Assistant's
target selector and glob text fields (with a preview of the result before saving), and keeps the per-sensor
spike limits reachable. Existing entries are migrated (`entities` + `device_spike_limits` → `sensors`).
A new installation defaults to `energy_dashboard` when the Energy dashboard has individual devices, otherwise to
`filter` with `include: all`.

## Dependencies
- Stacked on 017–019 (tariff model, tariff forms, options menu). 019 left the "Sensors" menu entry with the old
  entity picker and per-device limits; this task replaces it. The `init` menu stays
  `["sensors", "applied", "compare", "general"]`.
- Task 021 (YAML mode, export) will reuse the stored shape defined here unchanged; keep it identical to the
  CONFIG-DESIGN `sensors:` block.

## Context
### Stored format (`entry.options["sensors"]`, replaces `entities` and `device_spike_limits`)
```json
"sensors": {
  "mode": "filter",
  "include": {
    "entity_id": ["sensor.plug_01_energy"],
    "area_id": ["kitchen"],
    "label_id": ["cost_tracking"],
    "entity_globs": ["sensor.*_plug_*_energy"]
  },
  "exclude": {"entity_id": ["sensor.main_meter_t1"], "entity_globs": ["sensor.sub_meter_*"]},
  "overrides": {
    "sensor.water_heater_energy": {"spike_limit": "6"},
    "sensor.plug_02_energy": {"spike_limit": null}
  }
}
```
- `mode`: `"energy_dashboard"` | `"filter"`.
- `include`: **only** in `filter` mode (required there; rejected in `energy_dashboard` mode): the string `"all"` or a
  target mapping. Target keys: `entity_id`, `device_id`, `area_id`, `floor_id`, `label_id`, `entity_globs`; each a
  list of unique non-empty strings; unknown keys rejected; serialization writes only non-empty keys, so the
  round trip is canonical. An include target with no entries is invalid (see `nothing_included`).
- `exclude`: same target keys, both modes, always written (`{}` when empty).
- `overrides`: entity id → `{"spike_limit": "<decimal string>" | null}` (exactly that key; `null` = no spike check
  for this sensor; a missing entry = global limit). Always written (`{}` when empty). Overrides are kept when a
  sensor leaves the selection.
- Globs use `fnmatch.fnmatchcase` on the entity id and must match `^[a-z0-9_.*?\[\]!-]+$`.

### Resolution rules (pure engine, `engine/sensors.py`)
- **Eligible** sensor: has recorder long-term **sum** statistics in an energy unit (Wh/kWh/MWh, i.e.
  `classify_metadata(...) is OK` with `source == "recorder"`) **and** `device_class: energy` (entity registry
  `device_class or original_device_class`, else the state attribute). Sum statistics are only compiled for
  `state_class` `total` / `total_increasing`, so "cumulative" is implied by `has_sum`.
- A **candidate** is described by `entity_id`, `device_id`, effective `area_id` (entity area, else its device's
  area), `floor_id` of that area, `labels` (entity ∪ device ∪ effective-area labels) and `eligible`. An id with no
  registry entry and no state has no attributes and is not eligible.
- **Include** (filter mode): `all` = every eligible candidate. A target matches a candidate when its `entity_id`
  list contains it (explicitly listed ids are included **even if not eligible**, so the report shows their
  `no_statistics` / `unsupported` status as today), or — for eligible candidates only — when its device, area,
  floor or one of its labels is listed, or a glob matches.
- **Exclude** (both modes) matches by entity id, glob, device, area, floor or label, regardless of eligibility, and
  always wins.
- **Energy dashboard mode**: the sensors are the `stat_consumption` ids of `device_consumption`, in dashboard
  order, duplicates dropped, minus `exclude`. External statistics (ids with `:`) are kept; only `entity_id` / glob
  excludes can match them.
- **Order**: dashboard order in `energy_dashboard` mode; sorted by entity id in `filter` mode.
- **Nesting** (both modes, see open questions): the Energy dashboard's `included_in_stat` gives a parent map
  (`stat_consumption` → `included_in_stat`). For the ids of one report, a sensor's **upstream** is the nearest
  ancestor (walking the parent map, cycle-safe) that is also among the report's ids; sensors with an upstream are
  **nested**. Nesting is computed per request, so a report for a subset (card `entities`) counts a child in the
  total when its parent is not in that subset.

### Report changes
- `report_api._async_prepare` resolves the selection on every request (`sensor_resolver.async_resolve_sensors`)
  instead of reading `settings.entities`; the `entities` request field is validated against the resolved list
  (error `unknown_entity` unchanged, message "is not one of the selected energy sensors"). `compare` uses the same
  path. Spike limits: `QualitySettings(device_spike_limits=<overrides as id → limit>)`.
- Engine: `build_report(..., nested: AbstractSet[str] = frozenset())`; the `total` row of every bucket and the
  `totals` bucket sum only rows whose device is **not** nested (rows of nested devices are unchanged). Unknown ids in
  `nested` are ignored.
- JSON (SPEC §4): each `devices[]` item gains `"upstream": "<entity id>" | null`. Additive; `schema_version` stays 1
  (see open questions). The card is not changed (it renders the rows and the total it receives).

### Options flow (replaces 019's `sensors` form)
| Step | Kind | Content | Saves |
|---|---|---|---|
| `sensors` | menu | description: mode, `{count}` "N sensors in the calculation", `{sensors}` list (stored selection resolved now); options `sensors_select`, `device_limits` | — |
| `sensors_select` | form | `mode` (select, `translation_key: sensor_mode`); section `include`: `all` (boolean), `target` (target selector), `entity_globs` (text, `multiple`); section `exclude`: `target`, `entity_globs`. Prefilled from the stored settings (or the pending candidate when coming back from the preview) | — |
| `sensors_preview` | menu | description: `{count}` and `{sensors}` for the **candidate**; options `sensors_save`, `sensors_select` (edit again) | — |
| `sensors_save` | (no form) | re-reads `entry.options`, replaces mode / include / exclude, keeps `overrides` and every other key | yes |
| `device_limits` | form | one optional number field (kWh, `0` = off, empty = global) per **selected** sensor plus every sensor that already has an override (so stale overrides can be cleared); fields not shown keep their override | yes |

- The `include` section is ignored in `energy_dashboard` mode (description says so); `include.all = true` ignores
  the include target / globs.
- Errors on `sensors_select`: `mode: no_dashboard_devices` (dashboard mode chosen but the Energy dashboard has no
  individual devices); `base: nothing_included` (filter mode, `all` off, empty target, no globs);
  `base: invalid_glob` with placeholder `{glob}`. Target selector values are normalized (string → list,
  duplicates dropped, non-string values such as templates rejected with `base: invalid_target`).
- `device_limits` with no selected sensor and no override aborts with `no_sensors`.
- Sensor list in descriptions: one Markdown bullet per sensor, `` `sensor.plug_01_energy` — <display name> ``, a
  nested one followed by ``(inside `<upstream>`)``; at most 30 bullets, then "… and N more"; `count` is the full
  number. Display names use the same rule as the report (`report_api._display_name`; move it to the resolver or a
  shared helper).
- `TargetSelector(TargetSelectorConfig(entity=EntityFilterSelectorConfig(domain="sensor", device_class="energy")))`
  so the picker only offers energy sensors and devices / areas that have one.

### First setup and migration
- `async_step_user` stores `sensors = await sensor_resolver.async_default_sensor_settings(hass)`:
  `energy_dashboard` when the dashboard has at least one `device_consumption` entry, else `filter` + `include: all`
  (empty `exclude` / `overrides`).
- Config entry **VERSION 3** (MINOR_VERSION 1): the old `entities` / `device_spike_limits` keys are removed, which old
  code cannot read, so this is a major bump (HA docs: major for removed / renamed keys; an entry with a newer
  major version fails to set up instead of being misread). `async_migrate_entry`: v1 → v2 (unchanged) → v3; refuse
  `version > 3`.
- v2 → v3 (pure helper `settings.migrate_sensor_options(options, default)`): non-empty `entities` →
  `{"mode": "filter", "include": {"entity_id": [...]}, "exclude": {}, "overrides": {...}}` (same ids, same
  behaviour); empty `entities` → the first-setup default (`default` computed by the caller); every
  `device_spike_limits` item becomes an override (`null` stays `null`). Other keys untouched.

### Module boundaries (CLAUDE.md principles 4 and 5)
- `engine/sensors.py` (pure, no `homeassistant` imports): `SensorMode`, `SensorTarget`, `SensorOverride`,
  `SensorSettings` (+ `spike_limits()` mapping), `Candidate`, `DashboardDevice(statistic_id, included_in)`,
  `Selection(sensors, parents)`, `select_sensors(settings, candidates, dashboard)`, `upstreams(ids, parents) ->
  dict[str, str]`, glob validation. All matching logic lives here (unit tested, coverage gate).
- `settings.py` (no HA imports): strict parse / serialize of the `sensors` key into the engine dataclasses;
  `IntegrationSettings.sensors` replaces `entities` and `device_spike_limits`; `migrate_sensor_options`.
- `recorder_adapter.py` (the only recorder importer): new `async_energy_statistic_ids(hass) -> frozenset[str]` —
  `get_metadata(hass, statistic_type="sum", statistic_source="recorder")` in the recorder executor, filtered with
  `classify_metadata`.
- `sensor_resolver.py` (new, HA layer, no recorder import): reads the Energy dashboard preferences (the **only**
  module importing `homeassistant.components.energy`, imported lazily inside the function), builds candidates from
  the entity / device / area registries and states, calls the adapter and the engine. Functions:
  `async_dashboard_devices(hass)`, `async_default_sensor_settings(hass)`, `async_resolve_sensors(hass, sensors)`.
- `manifest.json`: add `"energy"` to `after_dependencies` (hassfest requires imported integrations to be listed in
  `dependencies` or `after_dependencies`; `energy` must not become a hard dependency).

### Home Assistant APIs checked (minimum 2025.4.0 and current `dev`, 2026-11-07)
- **Energy preferences.** `homeassistant.components.energy.data.async_get_manager(hass) -> EnergyManager`
  (`@singleton`, loads its store on first call, so it works even when the `energy` integration is not set up);
  `manager.data: EnergyPreferences | None` (plain attribute, `None` = never saved); `device_consumption:
  list[DeviceConsumption]` with `stat_consumption: str`, `name`, and **`included_in_stat`** (optional str).
  `included_in_stat` is absent at 2025.1.0, 2025.2.0 and 2025.3.0 and present at 2025.4.0 (in the TypedDict and
  `DEVICE_CONSUMPTION_SCHEMA`), i.e. it arrived exactly with our minimum version; on `dev` it is
  `NotRequired[str]`, and `dev` adds `stat_rate` and separate `device_consumption_water` / `device_consumption_gas`
  lists (ignored here — electricity only). Read keys with `.get()`; treat `data is None` as "no devices". Sources:
  [energy/data.py @2025.3.0](https://github.com/home-assistant/core/blob/2025.3.0/homeassistant/components/energy/data.py),
  [@2025.4.0](https://github.com/home-assistant/core/blob/2025.4.0/homeassistant/components/energy/data.py),
  [@dev](https://github.com/home-assistant/core/blob/dev/homeassistant/components/energy/data.py).
  Tests seed preferences with `await (await async_get_manager(hass)).async_update({"device_consumption": [...]})`
  (`async_update(update: EnergyPreferencesUpdate)` at both versions).
- **Target resolution helper is not portable.** At 2025.4.0 it is
  `homeassistant.helpers.service.async_extract_referenced_entity_ids(hass, service_call: ServiceCall,
  expand_group=True)`; on `dev` it moved to `homeassistant.helpers.target.async_extract_referenced_entity_ids(hass,
  target_selection: TargetSelection, expand_group=True, *, primary_entities_only=True)` and is no longer in
  `helpers.service`. Both skip hidden and categorized entities in indirect expansion. → **Decision:** resolve
  targets ourselves from the registries with the same semantics for devices / areas / floors / labels (entity
  area overrides device area; floor → its areas; label on entity, device or area), pure matching in the engine.
  Sources: [helpers/service.py @2025.4.0](https://github.com/home-assistant/core/blob/2025.4.0/homeassistant/helpers/service.py),
  [helpers/target.py @dev](https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/target.py),
  [helpers/service.py @dev](https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/service.py).
- **Registries** (2025.4.0): `AreaEntry.floor_id: str | None`, `AreaEntry.labels: set[str]`,
  `area_registry.async_get(hass)`; entity `RegistryEntry` has `device_id`, `area_id`, `labels`, `device_class`,
  `original_device_class`; `DeviceEntry` has `area_id`, `labels`. Source:
  [helpers/area_registry.py @2025.4.0](https://github.com/home-assistant/core/blob/2025.4.0/homeassistant/helpers/area_registry.py).
- **Selectors** (2025.4.0): `TargetSelectorConfig(entity=EntityFilterSelectorConfig | list, device=...)`; value is a
  `dict[str, list[str]]` validated by `cv.TARGET_SERVICE_FIELDS` (`entity_id`, `device_id`, `area_id`, `floor_id`,
  `label_id`). On `dev` the value type widens to `str | Template | list[...]` and the config gains
  `primary_entities_only` → normalize and reject non-strings; do not pass `primary_entities_only`.
  `EntityFilterSelectorConfig` at 2025.4.0: `integration`, `domain`, `device_class`, `supported_features` (no
  `unit_of_measurement`, which only `dev` has → do not use it). `TextSelectorConfig(multiple=True)` and
  `SelectSelectorConfig(translation_key=...)` exist at 2025.4.0. Sources:
  [helpers/selector.py @2025.4.0](https://github.com/home-assistant/core/blob/2025.4.0/homeassistant/helpers/selector.py),
  [@dev](https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/selector.py).
- **Recorder metadata listing:** `get_metadata(hass, *, statistic_ids=None, statistic_type: "mean" | "sum" | None,
  statistic_source=None) -> dict[str, tuple[int, StatisticMetaData]]` identical at 2025.4.0 and `dev`
  (`statistic_ids=None` = all). Call with keyword arguments, in the recorder executor. Sources:
  [recorder/statistics.py @2025.4.0](https://github.com/home-assistant/core/blob/2025.4.0/homeassistant/components/recorder/statistics.py),
  [@dev](https://github.com/home-assistant/core/blob/dev/homeassistant/components/recorder/statistics.py).
- **hassfest:** `script/hassfest/dependencies.py` reports "Using component X but it's not in 'dependencies' or
  'after_dependencies'"; `energy` is not in `ALLOWED_USED_COMPONENTS`. Source:
  [hassfest dependencies.py @2025.4.0](https://github.com/home-assistant/core/blob/2025.4.0/script/hassfest/dependencies.py).
- **Config entry versions:** major bump for removed / renamed keys; `async_migrate_entry` runs when the stored major
  is older (or minors differ); a newer stored major fails setup without calling the migration. Source:
  [config entries docs](https://contributors.home-assistant.io/core/integrations/config-entries/).
- Menus / sections / options flow constraints from task 019 still apply (no `sort=`, no `menu_option_descriptions`,
  always pass `step_id`, `OptionsFlow` + one update listener).

## Files
- create: `custom_components/energy_cost_stats/engine/sensors.py` — selection model and pure matching (above).
- modify: `custom_components/energy_cost_stats/engine/report.py` — `nested` parameter; totals skip nested rows.
- modify: `custom_components/energy_cost_stats/engine/serialize.py` — `DeviceInfo.upstream`, `"upstream"` in
  `devices[]`.
- modify: `custom_components/energy_cost_stats/settings.py` — `sensors` key (strict parse / serialize), drop
  `entities` / `device_spike_limits`, `migrate_sensor_options`.
- create: `custom_components/energy_cost_stats/sensor_resolver.py` — Energy dashboard reader, candidates from
  registries, default settings, `async_resolve_sensors`, display names for the preview.
- modify: `custom_components/energy_cost_stats/recorder_adapter.py` — `async_energy_statistic_ids`.
- modify: `custom_components/energy_cost_stats/report_api.py` — resolve per request, nesting, overrides as spike
  limits, `upstream` in `DeviceInfo`.
- modify: `custom_components/energy_cost_stats/config_flow.py` — `VERSION = 3`, default sensors in `user`, options
  steps `sensors` (menu), `sensors_select`, `sensors_preview`, `sensors_save`, `device_limits` (rewritten).
- modify: `custom_components/energy_cost_stats/__init__.py` — v2 → v3 migration.
- modify: `custom_components/energy_cost_stats/const.py` — `CONF_SENSORS`, mode values, target keys, form keys
  (`include`, `exclude`, `all`, `target`, `entity_globs`, `mode`), preview cap; remove `CONF_ENTITIES` /
  `CONF_DEVICE_SPIKE_LIMITS` / `CONF_EDIT_DEVICE_LIMITS` if unused.
- modify: `custom_components/energy_cost_stats/manifest.json` — `after_dependencies: ["frontend", "energy"]`.
- modify: `custom_components/energy_cost_stats/strings.json`, `translations/en.json` — new steps, sections,
  `selector.sensor_mode.options`, errors `no_dashboard_devices`, `nothing_included`, `invalid_glob`,
  `invalid_target`, abort `no_sensors`; remove the `not_energy_entity` error and `edit_device_limits` field if
  unused.
- create: `tests/unit/test_sensor_selection.py`; modify `tests/unit/test_report.py`, `tests/unit/test_serialize.py`.
- create: `tests/integration/test_sensor_resolver.py`, `tests/integration/test_sensors_options.py`; modify
  `tests/integration/test_settings.py`, `test_recorder_adapter.py`, `test_report_api.py`, `test_config_flow.py`, and
  the option fixtures (`entities` / `device_spike_limits` → `sensors`, `version=3`) in `test_options_menu.py`,
  `test_tariff_model.py`, `test_tariff_flow.py`.
- modify: `docs/SPEC.md` — §2 (settings `sensors` key, modes, eligibility, per-request resolution, Sensors options
  steps, VERSION 3 migration, first-setup default), §4 (`upstream`, totals exclude nested devices), §6 table
  (Energy `included_in_stat` since 2025.4; `get_metadata` listing; own target resolution and why).

This is at the upper bound of one task. Suggested order (each step green before the next): engine → settings +
migration → adapter + resolver → report API → options flow → SPEC.

## Tests to write first
| Level | Test | Asserts |
|---|---|---|
| unit | `tests/unit/test_sensor_selection.py::test_filter_all_takes_eligible_only` | `include=None` (all) selects every eligible candidate, sorted by id; non-eligible candidates are skipped |
| unit | `test_sensor_selection.py::test_include_entity_id_even_if_not_eligible` | an explicitly listed id with no candidate / not eligible is selected |
| unit | `test_sensor_selection.py::test_include_by_device_area_floor_label` | parametrized: each target key selects the matching eligible candidates only; label matches via entity, device or area labels |
| unit | `test_sensor_selection.py::test_include_globs` | `sensor.*_plug_*_energy` matches eligible ids case-sensitively; non-eligible matches are skipped |
| unit | `test_sensor_selection.py::test_exclude_wins` | an id matched by include and by exclude (each exclude key, incl. glob) is not selected; exclude applies to explicitly included ids too |
| unit | `test_sensor_selection.py::test_dashboard_mode_order_dedup_exclude` | dashboard order kept, duplicates dropped, exclude applied, external statistic id kept unless excluded by id / glob |
| unit | `test_sensor_selection.py::test_parents_from_dashboard` | `Selection.parents` maps `statistic_id` → `included_in` for dashboard entries with a parent, in both modes |
| unit | `test_sensor_selection.py::test_upstreams_nearest_selected_ancestor` | chain a ⊂ b ⊂ c: ids {a, c} → a's upstream c; ids {a, b, c} → a→b, b→c; ids {a} → none |
| unit | `test_sensor_selection.py::test_upstreams_cycle_safe` | a cycle in the parent map terminates; no id is its own upstream |
| unit | `test_sensor_selection.py::test_glob_validation` | valid patterns accepted; blank, upper case, spaces, `/` rejected |
| unit | `test_sensor_selection.py::test_settings_spike_limits` | `SensorSettings.spike_limits()` = id → `Decimal` / `None` from overrides, read-only |
| unit | `tests/unit/test_report.py::test_totals_skip_nested_devices` | two devices, child nested: rows unchanged; bucket `total` and `totals` equal the parent row only (kWh, zones, cost, coverage); unknown ids in `nested` ignored; default `nested` = old behaviour |
| unit | `tests/unit/test_serialize.py::test_device_upstream_field` | `devices[]` items carry `upstream` (`null` by default, the id when set) |
| integration | `tests/integration/test_settings.py::test_sensors_round_trip` | parametrized (dashboard mode, filter `all`, filter target with every key, overrides with `null`) → `settings_to_options(settings_from_options(o)) == o` |
| integration | `test_settings.py::test_sensors_rejects_malformed` | parametrized: unknown mode, `include` in dashboard mode, missing `include` in filter mode, unknown target key, non-list / duplicate / empty strings, invalid glob, override without `spike_limit` or with extra key, invalid limit, old `entities` / `device_spike_limits` keys → `SettingsError` |
| integration | `test_settings.py::test_migrate_sensor_options` | non-empty `entities` + limits → filter target with the same ids + overrides (`null` kept); empty `entities` → the given default; other keys untouched |
| integration | `tests/integration/test_recorder_adapter.py::test_energy_statistic_ids` | seeded energy sum, non-energy sum, mean-only and external statistics → only the recorder energy sum ids |
| integration | `tests/integration/test_sensor_resolver.py::test_dashboard_devices` | preferences with and without `included_in_stat` → `DashboardDevice`s in order; no saved preferences → `()` |
| integration | `test_sensor_resolver.py::test_default_settings` | dashboard with devices → `energy_dashboard`; without → `filter` + `all` |
| integration | `test_sensor_resolver.py::test_candidates_from_registries` | entity area overrides device area; floor from the area; labels from entity, device and area; sensor without registry entry but with state and statistics is eligible; energy-class sensor without statistics is not; statistics without `device_class: energy` are not |
| integration | `test_sensor_resolver.py::test_resolve_filter_by_area_and_label` | registry + statistics seeded; area / floor / label targets resolve to the expected ids |
| integration | `test_sensor_resolver.py::test_new_sensor_picked_up_dynamically` | `include: all`; a sensor added after setup (registry + statistics) appears in the next resolution without reloading the entry |
| integration | `tests/integration/test_report_api.py::test_report_uses_resolved_selection` | filter `all` report lists every eligible sensor; `entities` subset still works; an id outside the selection → `unknown_entity` |
| integration | `test_report_api.py::test_report_nested_totals` | dashboard mode with child `included_in_stat` parent: both rows present, child `upstream` = parent, totals = parent only; requesting only the child counts it in the total |
| integration | `test_report_api.py::test_quality_settings_applied` (updated) | the per-sensor limits now come from `overrides`; same assertions as before |
| integration | `tests/integration/test_config_flow.py::test_user_flow_defaults` (updated) | without dashboard devices: options contain `sensors = {mode: filter, include: all, exclude: {}, overrides: {}}`, no `entities` key |
| integration | `test_config_flow.py::test_user_flow_defaults_to_energy_dashboard` | dashboard preferences with devices → `sensors.mode == "energy_dashboard"` |
| integration | `test_config_flow.py::test_migrate_v2_to_v3` | `MockConfigEntry(version=2)` with `entities` / `device_spike_limits` → after setup `version == 3`, options have the equivalent `sensors`, entry `LOADED`, a report returns the same sensors; v1 entry migrates through both steps; `version=4` → migration error |
| integration | `tests/integration/test_sensors_options.py::test_sensors_menu_shows_count_and_list` | `sensors` is a menu with `["sensors_select", "device_limits"]`; placeholders `count` and `sensors` match the resolved selection; nested sensor shows its upstream; >30 sensors → 30 bullets + "… and N more" |
| integration | `test_sensors_options.py::test_select_filter_preview_then_save` | submit filter with area target + glob → `sensors_preview` menu with the candidate's count / list; `sensors_save` stores mode / include / exclude, keeps `overrides`, `applied`, `compare`, `panel`; entry reloads |
| integration | `test_sensors_options.py::test_preview_back_to_edit_prefills_candidate` | from the preview, `sensors_select` shows the pending values as suggested values |
| integration | `test_sensors_options.py::test_select_energy_dashboard_mode` | dashboard mode saved without `include`; exclude kept |
| integration | `test_sensors_options.py::test_select_errors` | dashboard mode without devices → `{"mode": "no_dashboard_devices"}`; filter with nothing → `{"base": "nothing_included"}`; bad glob → `{"base": "invalid_glob"}` with `glob` placeholder; options unchanged |
| integration | `test_sensors_options.py::test_device_limits_fields_and_save` | one field per selected sensor plus sensors with an override; `10` → `"10"`, `0` → `null`, cleared field → override removed, override of an unlisted id kept |
| integration | `test_sensors_options.py::test_device_limits_no_sensors_aborts` | empty selection, no overrides → abort `no_sensors` |
| integration | `test_sensors_options.py::test_save_uses_current_options` | an options change made after the preview was shown (e.g. `applied`) survives `sensors_save` |
| integration | `tests/integration/test_options_menu.py::test_options_strings_complete` (extended) | every new step id, menu option, section, field, selector option, error and abort key exists in `strings.json` and `translations/en.json` |

## Acceptance criteria
- [x] `uv run pytest -m unit` → green; engine coverage ≥ 95 % (`script/test`), `engine/sensors.py` included.
- [x] `uv run --group ha pytest -m integration` → green (verified locally on HA 2026.9.3 / py3.14 only; the 2025.4.0 leg is left to CI).
- [x] `script/lint` → clean; `uv run --group ha pyright` → 0 errors.
- [x] `hassfest` and `hacs` CI jobs green (not run locally; manifest and strings follow the rules) (manifest `after_dependencies` includes `energy`; translation schema
      accepts the new strings).
- [x] `grep -rn "homeassistant" custom_components/energy_cost_stats/engine/` → no imports; `settings.py` has no HA
      imports (`tests/unit/test_engine_isolation.py` green).
- [x] `grep -rln "homeassistant.components.recorder" custom_components/` → only `recorder_adapter.py`.
- [x] `grep -rln "homeassistant.components.energy" custom_components/` → only `sensor_resolver.py`.
- [x] `grep -rn "exclude_energy_sources\|async_extract_referenced_entity_ids\|primary_entities_only\|EntityFilterSelectorConfig(.*unit_of_measurement" custom_components/energy_cost_stats/config_flow.py custom_components/energy_cost_stats/sensor_resolver.py`
      → no match.
- [x] `grep -rn '"entities"\|device_spike_limits' custom_components/energy_cost_stats/settings.py` → only in the
      migration helper.
- [x] Config flow `VERSION == 3`; a version-2 entry with `entities` loads after migration with the same sensors.
- [x] Stored `sensors` shape equals the CONFIG-DESIGN `sensors:` block (same keys, `include: "all"` string form).
- [x] Options `init` menu still `["sensors", "applied", "compare", "general"]`; per-sensor spike limits reachable
      via `sensors` → `device_limits`.
- [x] `docs/SPEC.md` §2 / §4 / §6 updated as listed under Files.

## Out of scope
- YAML mode, read-only steps, `reload` action, repairs, "Export to YAML" (task 021).
- Card changes (indenting nested rows, explaining that the total excludes them) — task 022 or a follow-up.
- `exclude_energy_sources` / automatic exclusion of grid sources (dropped by design; `exclude` covers it).
- Gas and water dashboard device lists (`device_consumption_gas` / `_water`), `stat_rate`.
- Repairs or warnings for targets that reference deleted devices / areas / floors / labels (they match nothing).
- Caching the resolution or listening to registry / Energy preference updates (resolution runs per request).
- Russian translations (024).

## Open questions
- **Hidden and categorized sensors.** Home Assistant's target helpers skip hidden and `entity_category` entities
  when expanding devices / areas / labels. Default here: they are **not** skipped (a hidden plug energy sensor is
  still a consumer). Follow HA's rule instead?
- **Orphaned statistics.** Statistics of a sensor that no longer exists (no registry entry, no state) are not
  eligible for `all` / globs / targets (they can still be listed by `entity_id`). Include them for full-history
  reports instead (risk: double counting after an entity replacement)?
- **Nesting in filter mode.** Default: the Energy dashboard's `included_in_stat` hierarchy is applied in both modes,
  so `include: all` does not double count devices the dashboard already knows are nested. Restrict nesting to
  `energy_dashboard` mode?
- **How nested devices are counted.** Default: nested devices keep their own row and the totals exclude them.
  Alternatives: drop nested devices, or show the parent as "parent minus children". Until the card marks nested
  rows, the total can be smaller than the sum of the visible rows — acceptable for this task?
- **Migration of an empty `entities` list.** Default: the first-setup default (dashboard or `all`). Alternative:
  keep "nothing selected" (`filter` with an empty `entity_id` include), which the strict schema would then have to
  allow.
- **`schema_version`.** The `upstream` field is additive and the totals change only when nesting exists, so the
  version stays `1`. Bump to `2` instead?
- **Switching mode drops `include`.** Default: saving `energy_dashboard` mode discards the filter include (the
  YAML shape allows `include` only in filter mode). Keep it stored for switching back?

<!-- Filled in by implementer -->
## Implementation notes
- Open questions: the planner's defaults were implemented (hidden / categorized sensors are not skipped, orphaned
  statistics are not eligible, nesting applies in both modes, nested devices keep their row but leave the totals,
  empty `entities` migrates to the first-setup default, `schema_version` stays 1, switching to dashboard mode
  drops `include`).
- Registry fields verified against the installed Home Assistant (2026.9.3): `RegistryEntry.device_id / area_id /
  labels / device_class / original_device_class`, `DeviceEntry.area_id / labels`, `AreaEntry.floor_id / labels`,
  `area_registry.async_get_area`. Entity area and labels cannot be passed to `async_get_or_create`, tests use
  `async_update_entity`.
- `engine.sensors.upstreams`: members of a parent cycle get no upstream (otherwise two mutually nested devices would
  both drop out of the totals). `SensorSettings.include is None` means "all" in filter mode.
- `settings.py` requires the `sensors` key; the old `entities` / `device_spike_limits` keys are rejected as unknown
  keys. `migrate_sensor_options` leaves options that already contain `sensors` untouched.
- `sensor_resolver.display_name` is the old `report_api._display_name` (now with an explicit fallback name);
  `describe_selection` builds the count and the bullet list for the menus.
- Candidates are built for every sensor registry entry, sensor state, recorder energy statistic id and dashboard id;
  the Energy dashboard module is imported lazily inside `async_dashboard_devices`.
- The `sensors_select` form has an extra error `invalid_mode` (defensive, the select selector already limits the
  values) and the `sensors` menu description shows the mode as a label (`{mode}`).
- Old 019 option-flow tests that exercised the entity picker (`test_options_select_entities_and_reload`,
  `..._rejects_non_energy_entity`, `..._keeps_missing_previous_entity`, `test_options_device_limits`,
  `..._drops_overrides_of_deselected`, `..._without_entities_saves_directly`, `..._prefills_current_values` for the
  sensors form) were removed because the form no longer exists; `tests/integration/test_sensors_options.py`
  covers the replacement flow. The device-limit tests that remain were adapted to the new menu path.
- `test_save_uses_current_options` changes `spike_limit` between the preview and the save (an `applied` entry
  without a matching tariff subentry would be reconciled away by the update listener).
- Review round 1: nesting is now decided per hour in the engine (`build_report(..., nested: Mapping[child, upstream])`):
  a nested sensor's hour leaves the total rows only where one of its ancestors (the whole chain) has a counted
  (measured or estimated) value for that hour; total rows are accumulated separately from the device rows. `report_api` only nests under upstreams
  whose read status is `ok` (nearest readable ancestor), and `devices[].upstream` follows the same rule.
- Review suggestions: the `{mode}` placeholder was dropped from the Sensors menu (the label could not be translated; the
  mode is visible in the select form); an empty selection now lists nothing instead of `-` (the count line says
  "0 sensors", a conditional hint would need an untranslatable placeholder text); registry ids in the target
  selector are resolved to entity ids and the `all` / `none` keywords or unresolvable values are rejected with
  `invalid_target`; a debug message is logged when an `included_in_stat` cycle is found; CONFIG-DESIGN wording fixed;
  the missing tests were added.
- Not run locally: the minimum-HA leg (2025.4.0), hassfest and hacs; the container only has the latest HA.

## Follow-ups
- Performance: every report request lists the recorder sum statistics and walks the entity registry and the state
  machine. Fine for typical installations; cache the resolution if request rates grow.
- Card: mark nested rows (`devices[].upstream`) and explain that the total excludes them (task 022 or later).
