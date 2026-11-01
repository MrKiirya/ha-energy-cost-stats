# 009 — Config flow, options flow and config entry setup/unload

Status: in-review
Roadmap: SPEC §8 stage 2 (config flow / options flow / tariff subentries), task 1 of 2 (009-config-and-options-flow,
010-tariff-plan-subentries)
Spec sections: SPEC §2 (integration layer), §5 (spike limit default, per-device override or disable), §6 (min HA
2025.4); CLAUDE.md principles 1, 4, 5, 6

> Planner decisions are marked **(D-n)** and also appear under "Open questions" as "decided by planner,
> confirm in PR review". The human was away when this was planned.

## Goal
Users can add **Energy Cost Stats** from *Settings → Devices & services*. The integration allows one instance
only. Setup asks for two global settings: the time zone used for zones and groupings (default: the Home
Assistant time zone) and the spike limit (default 4 kWh/h, can be turned off). The options flow edits the same
settings and selects which energy sensors to report on (multi-select of `device_class: energy` sensors). It can
also set a per-device spike limit (a number, "off", or "use the global limit"). The config entry sets up and
unloads cleanly. After any options change it reloads through one update listener. Task 010 relies on the same
listener for tariff-plan subentry changes. No entities, platforms, services or recorder access are added. The
parsed settings are kept in `entry.runtime_data` for stage 3.

## Context

### Current state
- `__init__.py` has only `async_setup` with `CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)`. Keep both: stage 3
  registers the websocket command and service in `async_setup`.
- `manifest.json` has `"config_flow": false`. `tests/unit/test_metadata.py::test_manifest_matches_domain`
  asserts `not manifest.get("config_flow", False)`, so that assertion changes in this task.
- `engine/quality.py` (task 007, **not merged yet**, may still change) defines `QualitySettings(spike_limit:
  Decimal | None = Decimal("4"), device_spike_limits: Mapping[str, Decimal | None])`. Here `None` means
  "check disabled" and a limit must be a finite `Decimal > 0`. **Do not import `engine.quality` in this task.**
  This task stores the same semantics (SPEC §5) in its own settings module. Stage 3 maps them to
  `QualitySettings`.
- The engine's `device_id` is the statistic id. For sensor entities that is the `entity_id`, so the options
  store `entity_id`s. SPEC §5 says a renamed entity's statistics stay on the old id. That is stage 3's problem
  (see Out of scope).

### HA API checked (2026-11-01)
- **Minimum 2025.4.0** (source of truth: [config_entries.py @2025.4.0](https://github.com/home-assistant/core/blob/2025.4.0/homeassistant/config_entries.py)):
  - `ConfigFlow.async_create_entry(*, title, data, description=None, description_placeholders=None,
    options=None, subentries=None)`: `options=` is available, so the initial settings can go straight into
    `entry.options`.
  - `OptionsFlow.config_entry` is a property that works in steps, not in `__init__`. `async_get_options_flow`
    returns `OptionsFlowHandler()` **without arguments**. Passing `config_entry` to the constructor is the
    deprecated pattern, and its compatibility shim is "to be removed in 2025.12".
  - `OptionsFlowManager.async_finish_flow` calls `async_update_entry(entry, options=result["data"])`. That fires
    the entry's update listeners only if something changed.
  - **`OptionsFlowWithReload` does not exist in 2025.4.0.** It was added in mid-2025. In the latest HA,
    `OptionsFlowManager.async_finish_flow` raises when an `OptionsFlowWithReload` entry also has update
    listeners. See [options flow docs](https://contributors.home-assistant.io/core/integrations/options-flow/)
    (moved from developers.home-assistant.io/docs/config_entries_options_flow_handler) and
    [config_entries.py @dev](https://github.com/home-assistant/core/blob/dev/homeassistant/config_entries.py).
  - `ConfigEntries.async_add_subentry` / `async_remove_subentry` / `async_update_subentry` also fire the update
    listeners (through `_async_update_entry` / `_async_save_and_notify`) in 2025.4.0 and latest. **Decision (D-1):**
    reload through **one** `entry.add_update_listener(...)` that calls `hass.config_entries.async_reload`. That
    covers options (this task) and subentries (task 010) the same way on both HA versions. Use plain `OptionsFlow`,
    never `OptionsFlowWithReload`.
- `single_config_entry: true` in `manifest.json`. HA itself aborts a second user flow with reason
  `single_instance_allowed`. The integration must still supply the text for that reason.
- `ConfigEntry[T]` with `entry.runtime_data` (generic, typed) is available in 2025.4.
- `homeassistant.util.dt.async_get_time_zone(name)` returns `tzinfo | None` without blocking the loop. Use it to
  validate the time zone. `zoneinfo.available_timezones()` reads the disk, so call it via
  `hass.async_add_executor_job`.
- Selectors (`homeassistant.helpers.selector`): `EntitySelector(EntitySelectorConfig(domain="sensor",
  device_class="energy", multiple=True))`, `SelectSelector(SelectSelectorConfig(options=..., mode=DROPDOWN))`,
  `NumberSelector(NumberSelectorConfig(min=..., step="any", mode=BOX, unit_of_measurement="kWh"))`,
  `BooleanSelector()`. **The `device_class` filter only applies in the frontend picker.** The backend
  `EntitySelector` validates the entity-id format only, so the flow checks the device class itself (D-6).
- Translations: custom integrations load `translations/en.json` at runtime. Hassfest validates `strings.json`
  and `translations/en.json` against the same schema
  ([script/hassfest/translations.py @dev](https://github.com/home-assistant/core/blob/dev/script/hassfest/translations.py)).
  In a custom integration a root-level `title` only gets a warning, but **do not add one**. `[%key:...%]`
  references are **not** resolved for custom integrations, so write every string literally.
- Test harness: `pytest_homeassistant_custom_component.common.MockConfigEntry`. Flows are tested with
  `hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})`, `...flow.async_configure`,
  `hass.config_entries.options.async_init(entry.entry_id)` and `...options.async_configure`. Register entities
  with `er.async_get(hass).async_get_or_create("sensor", "test", "plug_01", suggested_object_id="plug_01",
  original_device_class="energy")`. The `recorder_mock` + `enable_custom_integrations` autouse fixture already
  exists in `tests/integration/conftest.py`.

### Design decisions
- **D-1 Reload mechanism:** one update listener → `async_reload`. Do not use `OptionsFlowWithReload` (not in
  2025.4.0, and it conflicts with update listeners on latest).
- **D-2 Storage:** `entry.data == {}`. All settings live in `entry.options`, so the options flow is their only
  editor and the config flow writes the initial options via `async_create_entry(options=...)`. Format (JSON),
  `VERSION = 1`, `MINOR_VERSION = 1`:
  ```json
  { "time_zone": "Europe/Berlin",
    "spike_limit": "4",
    "device_spike_limits": { "sensor.plug_01": "10", "sensor.plug_02": null },
    "entities": ["sensor.plug_01", "sensor.plug_02"] }
  ```
  Decimals are stored as **strings** (004 human decision: money/kWh serialized as strings), normalized without
  an exponent (`4.0` → `"4"`, `2.50` → `"2.5"`). `spike_limit: null` turns the spike check off globally. In
  `device_spike_limits`, a missing key means "use the global limit", `null` means "off for this device", and a
  string is the device's limit. `entities` keeps selection order and has no duplicates.
- **D-3 Time zone is stored explicitly** and defaults to `hass.config.time_zone` at setup. It does not follow
  HA's setting live: retroactive prices must not move silently if the HA time zone changes later. The user can
  change it in options.
- **D-4 Config flow step `user`:** `time_zone` (dropdown of `available_timezones()`, sorted, default HA's),
  `spike_check` (boolean, default on) and `spike_limit` (number box, kWh, `min=0.001`, default 4, ignored when
  `spike_check` is off). Entity selection is only in the options flow, as SPEC §2 says. Entry title:
  `"Energy Cost Stats"`.
- **D-5 Options flow:** step `init` has the same three fields with the current values pre-filled, plus `entities`
  (energy sensor multi-select) and `edit_device_limits` (boolean, default off). If `edit_device_limits` is on,
  step `device_limits` has one optional number field per selected entity, keyed by its `entity_id`, with
  `min=0` and `step="any"`. Empty means "use the global limit", `0` means "off for this device", and `> 0` is
  the limit. Pre-filled values come from `add_suggested_values_to_schema`, with `null` shown as `0`. Field labels
  are the raw `entity_id`s (dynamic keys cannot be translated). The step description explains the three
  options. Overrides for entities that are no longer selected are dropped on save. If `edit_device_limits` is
  off, the existing overrides for still-selected entities are kept.
- **D-6 Entity validation (server side):** each entity that is **newly** added (not already in
  `options["entities"]`) must exist in the entity registry with `device_class or original_device_class ==
  "energy"`, or, if it is not in the registry, exist as a state with attribute `device_class == "energy"`.
  Otherwise the form shows `errors["entities"] = "not_energy_entity"`. Entities that were already selected stay
  accepted even if they are now missing. Their long-term statistics outlive the entity, and history is the
  point of the integration.
- **D-7 Settings module** `settings.py` (integration layer, no recorder import) provides
  `IntegrationSettings` (frozen dataclass: `time_zone: str`, `spike_limit: Decimal | None`,
  `device_spike_limits: Mapping[str, Decimal | None]` (read-only), `entities: tuple[str, ...]`),
  `settings_from_options(Mapping[str, Any]) -> IntegrationSettings` (strict: wrong types, unknown keys, bad
  decimals, limits `<= 0`, non-finite values and duplicates raise `SettingsError(ValueError)`) and
  `settings_to_options(IntegrationSettings) -> dict[str, Any]`. It must not import `homeassistant` (it is pure
  config mapping), but it lives outside `engine/`, so its tests are integration-level files that need no `hass`
  fixture. It does **not** validate the time zone name, because that needs HA's async helper.
  `async_setup_entry` does.
- **D-8 Setup:** `async_setup_entry` parses the options with `settings_from_options` and resolves the time zone
  via `dt_util.async_get_time_zone`. If either fails, it raises `ConfigEntryError` with a clear message (state
  `SETUP_ERROR`). Valid flows cannot produce such data; this is a guard against hand-edited storage. Otherwise
  it stores `RuntimeData(settings=..., tzinfo=...)` in `entry.runtime_data` and registers the update listener
  with `entry.async_on_unload(entry.add_update_listener(...))`. `async_unload_entry` returns `True` (no
  platforms). Use the type alias `EnergyCostStatsConfigEntry = ConfigEntry[RuntimeData]`.

## Files
- modify: `custom_components/energy_cost_stats/manifest.json` — `"config_flow": true`, `"single_config_entry": true`.
- modify: `custom_components/energy_cost_stats/const.py` — option keys (`CONF_TIME_ZONE`, `CONF_SPIKE_LIMIT`,
  `CONF_DEVICE_SPIKE_LIMITS`, `CONF_ENTITIES`, `CONF_SPIKE_CHECK`, `CONF_EDIT_DEVICE_LIMITS`), `DEFAULT_SPIKE_LIMIT
  = Decimal("4")` (this mirrors SPEC §5 and does not import `engine.quality`), `DEFAULT_TITLE`.
- create: `custom_components/energy_cost_stats/settings.py` — D-7.
- create: `custom_components/energy_cost_stats/config_flow.py` — `EnergyCostStatsConfigFlow` (`VERSION = 1`,
  `MINOR_VERSION = 1`, step `user`, `async_get_options_flow`) and `EnergyCostStatsOptionsFlow` (steps `init`,
  `device_limits`). Keep it ready for task 010, which adds `async_get_supported_subentry_types`. Do not add it
  now.
- modify: `custom_components/energy_cost_stats/__init__.py` — `RuntimeData`, `EnergyCostStatsConfigEntry`,
  `async_setup_entry`, `async_unload_entry`, update listener. Update the module docstring.
- create: `custom_components/energy_cost_stats/strings.json` — `config.step.user` (title, description, `data`,
  `data_description`), `config.abort.single_instance_allowed`, `options.step.init`, `options.step.device_limits`
  (description: "Leave empty to use the global limit, 0 turns the check off for this device."),
  `options.error.not_energy_entity`.
- create: `custom_components/energy_cost_stats/translations/en.json` — identical copy of `strings.json`.
- modify: `tests/unit/test_metadata.py` — the manifest now asserts `config_flow is True` and
  `single_config_entry is True`. Add `test_strings_match_en_translation`.
- create: `tests/integration/test_config_flow.py`
- create: `tests/integration/test_settings.py`
- modify: `docs/SPEC.md` — §2: a short "Settings" paragraph (single instance, options format D-2, time zone D-3,
  per-device spike override D-5, reload via update listener D-1). No other section.

11 files. `tests/integration/test_setup.py` stays unchanged and must still pass.

## Tests to write first
Integration tests run in the devcontainer (they need HA). Use generic ids only (`sensor.plug_01`,
`sensor.plug_02`, `sensor.power_01`, `sensor.plug_old`) and time zones `Europe/Berlin` / `UTC`. Set HA's time
zone with `await hass.config.async_set_time_zone("Europe/Berlin")`.

| Level | Test | Asserts |
|---|---|---|
| unit | `tests/unit/test_metadata.py::test_manifest_matches_domain` (modified) | `manifest["config_flow"] is True`, `manifest["single_config_entry"] is True`; other assertions unchanged. |
| unit | `tests/unit/test_metadata.py::test_strings_match_en_translation` | `json.loads(strings.json) == json.loads(translations/en.json)`; neither has a root-level `"title"`; no value contains `"[%key:"`. |
| integration | `tests/integration/test_settings.py::test_roundtrip` | Options as in D-2 → `settings_from_options` gives `spike_limit == Decimal("4")`, overrides `{"sensor.plug_01": Decimal("10"), "sensor.plug_02": None}`, `entities` a tuple in order; `settings_to_options(...)` returns the original dict exactly. |
| integration | `tests/integration/test_settings.py::test_null_spike_limit_disables` | `"spike_limit": None` → `settings.spike_limit is None`, and it round-trips back to `None`. |
| integration | `tests/integration/test_settings.py::test_decimal_normalization` | `settings_to_options` on `Decimal("4.0")` → `"4"`, `Decimal("2.50")` → `"2.5"`, `Decimal("0.125")` → `"0.125"`; never exponent notation (`Decimal("1E+1")` → `"10"`). |
| integration | `tests/integration/test_settings.py::test_invalid_options` | Parametrized → `SettingsError`: `spike_limit` `"0"`, `"-1"`, `"abc"`, `"NaN"`, `"Infinity"`, `4` (int), `4.0` (float), `True`; override value `"0"`; override key `""`; `entities` not a list / containing a non-str / with duplicates; `time_zone` missing or not a str; an unknown top-level key. |
| integration | `tests/integration/test_settings.py::test_device_limits_read_only` | Item assignment on `settings.device_spike_limits` raises `TypeError`; the dataclass is frozen. |
| integration | `tests/integration/test_config_flow.py::test_user_flow_defaults` | HA tz `Europe/Berlin`: the `user` form's `time_zone` default is `"Europe/Berlin"` and its `spike_limit` default is `4`. Submitting `{"time_zone": "Europe/Berlin", "spike_check": True, "spike_limit": 4}` → `CREATE_ENTRY`, title `"Energy Cost Stats"`, `data == {}`, `options == {"time_zone": "Europe/Berlin", "spike_limit": "4", "device_spike_limits": {}, "entities": []}`; the entry is `LOADED`. |
| integration | `tests/integration/test_config_flow.py::test_user_flow_spike_check_off` | `spike_check: False` with any `spike_limit` → `options["spike_limit"] is None`. |
| integration | `tests/integration/test_config_flow.py::test_user_flow_rejects_unknown_time_zone` | Submitting `time_zone: "Not/AZone"` raises `homeassistant.data_entry_flow.InvalidData` (the dropdown schema guards it). |
| integration | `tests/integration/test_config_flow.py::test_single_instance` | With one `MockConfigEntry` already added, a new user flow → `ABORT`, reason `single_instance_allowed`. |
| integration | `tests/integration/test_config_flow.py::test_setup_and_unload` | `MockConfigEntry(domain=DOMAIN, data={}, options=<D-2 example>)` → `async_setup` → `LOADED`; `entry.runtime_data.settings.entities == ("sensor.plug_01", "sensor.plug_02")`; `runtime_data.tzinfo` is `Europe/Berlin`; `hass.states.async_all()` has no entity of this domain; `async_unload` → `NOT_LOADED`. |
| integration | `tests/integration/test_config_flow.py::test_setup_error_on_corrupt_options` | Parametrized: options with `spike_limit: "abc"`; options with `time_zone: "Not/AZone"` → entry state `SETUP_ERROR`. |
| integration | `tests/integration/test_config_flow.py::test_options_select_entities_and_reload` | Registry has `sensor.plug_01` and `sensor.plug_02` (`original_device_class="energy"`) and `sensor.power_01` (`"power"`). Options `init` with `entities: [plug_01, plug_02]` and `edit_device_limits: False` → `CREATE_ENTRY`; `entry.options["entities"] == [plug_01, plug_02]`; after `async_block_till_done()` the entry is `LOADED` again and `runtime_data.settings.entities` reflects the change (proves the reload). |
| integration | `tests/integration/test_config_flow.py::test_options_init_prefills_current_values` | The `init` form's suggested values equal the current options: tz, `spike_check` derived from `spike_limit is not None`, `spike_limit` as a number, entities. |
| integration | `tests/integration/test_config_flow.py::test_options_rejects_non_energy_entity` | Adding `sensor.power_01` → form again with `errors == {"entities": "not_energy_entity"}`; options unchanged. An energy entity that exists only as a state (`hass.states.async_set("sensor.plug_03", "1", {"device_class": "energy"})`) is accepted. |
| integration | `tests/integration/test_config_flow.py::test_options_keeps_missing_previous_entity` | The current options contain `sensor.plug_old`, which is neither in the registry nor a state; resubmitting with it still selected → accepted (D-6). |
| integration | `tests/integration/test_config_flow.py::test_options_device_limits` | `edit_device_limits: True` → step `device_limits` with exactly one optional field per selected entity; submitting `{plug_01: 10, plug_02: 0}` → `device_spike_limits == {"sensor.plug_01": "10", "sensor.plug_02": None}`; an omitted field → key absent. Reopening the step suggests `10` and `0`. |
| integration | `tests/integration/test_config_flow.py::test_options_drops_overrides_of_deselected` | Existing override for `plug_02`; deselecting `plug_02` with `edit_device_limits: False` → its key is removed and the `plug_01` override is kept. |
| integration | `tests/integration/test_setup.py::test_async_setup` (unchanged) | Still passes: `async_setup_component` without an entry loads and creates no entities. |

## Acceptance criteria
Linux devcontainer (from the host: `devcontainer exec --workspace-folder . --docker-path podman <cmd>`):
- [x] `uv run --group ha pytest -m integration` → all pass, including the tests above.
- [ ] `script/test` → all levels pass; the engine coverage gate (≥ 95 %) still holds.
- [x] `uv run --group ha pyright` → 0 errors.
- [x] `script/lint` → exit 0.

Either environment:
- [x] `uv run pytest -m unit` → passes (including the two metadata tests).
- [x] `uv run ruff check .` and `uv run ruff format --check .` → exit 0.

General:
- [x] `rg -n "homeassistant" custom_components/energy_cost_stats/settings.py` → no matches.
- [x] `rg -n "components.recorder|engine.quality|from .engine" custom_components/energy_cost_stats/config_flow.py custom_components/energy_cost_stats/__init__.py custom_components/energy_cost_stats/settings.py` → no matches (no recorder access, no dependency on unmerged 007).
- [x] `rg -n "OptionsFlowWithReload|async_update_reload_and_abort" custom_components` → no matches (D-1).
- [x] `rg -n "async_get_options_flow" -A4 custom_components/energy_cost_stats/config_flow.py` shows the options flow constructed without a `config_entry` argument.
- [ ] `strings.json` and `translations/en.json` are byte-identical in content (the unit test) and pass `hassfest` in CI (`validate.yml`).
- [ ] CI is green on both matrix legs (HA 2025.4.0 / latest).
- [x] `docs/SPEC.md`: only §2 changed, and it describes D-1, D-2, D-3 and D-5.
- [x] No files touched outside "Files" (the tree may hold other tasks' changes; do not modify or stage them).
- [ ] Manual (optional, human): in `script/develop`, add the integration, open Configure, pick two energy
  sensors, set one per-device limit, check that the entry reloads without errors in the log.

## Out of scope
- Tariff plans as config subentries, the `TariffSchedule` in `runtime_data` → **010-tariff-plan-subentries**.
- Mapping `IntegrationSettings` to `engine.quality.QualitySettings`, the recorder adapter, the websocket command
  and the service → stage 3.
- Checking that a selected sensor has long-term statistics (`state_class`). Stage 3 reports such devices as
  missing data. Selecting statistics of removed entities by `statistic_id`, and following entity renames
  (SPEC §5) → stage 3 follow-up.
- Main meter / "untracked" row, nested-meter de-duplication (SPEC §5, out of stage 1/2).
- Global entities (Recalculate button, current zone/price) → stage 5.
- Translations other than English.

## Open questions
All decided by planner, confirm in PR review:
- D-1 One update listener reloads on options and subentry changes; no `OptionsFlowWithReload`.
- D-2 All settings in `entry.options` (none in `data`), with decimals stored as normalized strings.
- D-3 The time zone is stored explicitly (default = HA's at setup) and does not follow later HA changes.
- D-4 The config flow asks only for time zone + spike limit. Entities are chosen in the options flow.
- D-5 Per-device limits: an optional second options step with one number per entity (empty = global,
  `0` = off), raw `entity_id` labels, and overrides of deselected entities dropped.
- D-6 Newly added entities are checked server-side for `device_class: energy`. Already-selected missing entities
  are kept.
- D-8 Corrupt stored options → `ConfigEntryError` (setup error) instead of silently using defaults.

<!-- Filled in by implementer -->
## Implementation notes
- Implemented D-1..D-8 as planned. All planner decisions remain "confirm in PR review".
- Spike limits from number selectors go through `Decimal(str(value))` (`_to_decimal`); extra test
  `test_user_flow_fractional_spike_limit` (4.1 -> stored "4.1").
- `strings.json` also has `options.abort.invalid_options`: the options flow aborts with it if the stored options
  fail to parse (not in the task; the setup would already be in SETUP_ERROR).
- If `edit_device_limits` is on but no entities are selected, the flow saves directly (an empty second step is pointless).
- On validation errors the init form is re-shown with the user's input as suggested values.
- `EnergyCostStatsConfigEntry` uses a `type` statement (Python 3.12+; both CI legs are 3.13+).
- Tests: `_call` helper in `test_config_flow.py` converts flow results to plain dicts to keep pyright happy.
- Not run locally: the 3.13 / HA 2025.4.0 leg and `script/test` (coverage gate; engine untouched, full suite
  298 passed). hassfest runs in CI only.
## Follow-ups
- Stage 3: map `IntegrationSettings` to `engine.quality.QualitySettings`; follow entity renames.
- Task 010 adds `async_get_supported_subentry_types` to the config flow; the update listener already covers subentries.

## Review round 1 fixes
- Required 1: non-finite selector values (NaN, infinity) and global limits <= 0 are now rejected with the form
  error `invalid_limit` (user flow, options init, and per-device step with the error keyed by entity id). Nothing
  is written on error. Strings added to `strings.json` and `translations/en.json`. `-inf` and `0` are already
  rejected by the selector's own `min` (InvalidData), so they never reach the flow.
- Suggestion 1: test for the `invalid_options` abort (entry in SETUP_ERROR). Kept as an abort; a "reset to defaults" form is not added.
- Suggestion 2: test that per-device editing with no entities saves directly.
- Suggestion 3: `spike_limit` is `vol.Optional` in the options form; when the check is off it is ignored, and when
  it is on and omitted, the current (or default) limit is kept.
- Suggestion 4 skipped as requested.
