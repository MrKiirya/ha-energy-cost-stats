# 013 — Websocket command `energy_cost_stats/report` and service `energy_cost_stats.get_report`

Status: in-review
Roadmap: SPEC §8 stage 3 (websocket `report` + service + integration tests), task 3 of 3 (011-recorder-adapter,
012-report-serializer, **013-report-websocket-and-service**). Depends on **011** (adapter, `seed_statistics` fixture)
and **012** (serializer, `schedule=None`). Branch after both are merged, or stacked on them.
Spec sections: SPEC §2 (websocket command, service with `SupportsResponse`, settings in `entry.options`), §4 (report
semantics, JSON contract from 012), §5 (data quality settings), §6 (min HA 2025.4); CLAUDE.md principles 1, 2, 3, 6

> Planner decisions are marked **(D-n)** and also appear under "Open questions" as "decided by planner, confirm in
> PR review". The human was away when this was planned.

## Goal
Users and the stage 4 card can request a cost report for any period:
- the websocket command `energy_cost_stats/report` (for the card);
- the response-only action `energy_cost_stats.get_report` (for scripts and automations, `response_variable`).

Both take `start`, `end`, `grouping` and an optional `entities` list. They read the configured settings (time zone,
spike limits, entities) and the current tariff schedule from the loaded entry. They read statistics through the 011
adapter, build the report with the engine in an executor, and return **the same** 012 JSON document. Every hour is
priced with the current plans on each call (retroactive). Errors are explicit: websocket error codes, or translated
`ServiceValidationError`s. No entities are created.

## Context

### HA API checked (2026-11-01)
- Actions:
  [contributors.home-assistant.io/core/integrations/actions](https://contributors.home-assistant.io/core/integrations/actions/)
  (formerly developers.home-assistant.io/docs/dev_101_services). Register actions in `async_setup` (quality-scale
  rule "action-setup"), so the action exists even with no loaded entry and gives a clear error.
  `hass.services.async_register(DOMAIN, name, handler, schema=..., supports_response=SupportsResponse.ONLY)`. The
  handler returns a JSON-serializable `dict` (`ServiceResponse`). User mistakes raise
  `ServiceValidationError(translation_domain=DOMAIN, translation_key=..., translation_placeholders=...)`, with the
  message in `strings.json` → `exceptions.<key>.message`. `strings.json` → `services.<name>` needs `name`,
  `description` and every field's `name`/`description`. `SupportsResponse` dates from 2023.7 and translated
  `ServiceValidationError` from 2023.11, so both are in 2025.4.0.
  - `service.async_get_config_entry` is newer than our floor. **Do not use it.** Look the entry up yourself (D-2).
- Websocket: `homeassistant.components.websocket_api`: `@websocket_api.websocket_command({vol.Required("type"):
  "energy_cost_stats/report", ...})`, `@websocket_api.async_response`, `websocket_api.async_register_command(hass,
  handler)`, `connection.send_result(msg["id"], result)`, `connection.send_error(msg["id"], code, message)`.
  Schema failures are answered automatically with `invalid_format`. An uncaught exception in an `async_response`
  handler is answered with `unknown_error`. This has been stable for years. It is the same at 2025.4.0 and `dev`:
  [websocket_api/decorators.py @dev](https://github.com/home-assistant/core/blob/dev/homeassistant/components/websocket_api/decorators.py),
  [@2025.4.0](https://github.com/home-assistant/core/blob/2025.4.0/homeassistant/components/websocket_api/decorators.py).
- hassfest allows `websocket_api` to be imported without listing it in `manifest.json` `dependencies` (it is in the
  allowed-used-components list). If CI `hassfest` disagrees, add `"websocket_api"` to `dependencies` and record it.
- Test fixtures (PHCC 0.13.232 and latest): `hass_ws_client` (`await client.send_json_auto_id({...})`, `await
  client.receive_json()`), `hass_read_only_access_token`, `MockConfigEntry(options=..., subentries_data=[...])` (used
  by 010), `hass.services.async_call(DOMAIN, "get_report", data, blocking=True, return_response=True)`.

### Inputs from earlier tasks
- `entry.runtime_data` (009/010): `settings: IntegrationSettings` (`time_zone`, `spike_limit`, `device_spike_limits`,
  `entities`), `tzinfo`, `schedule: TariffSchedule | None`.
- 011: `async_read_hourly_changes(hass, ids, start, end) -> tuple[HourlySeries, ...]` (status + `DeviceSeries` +
  metadata name).
- 012: `build_report(request, schedule | None, devices, *, quality=...)`,
  `report_to_json(report, *, devices: Sequence[DeviceInfo], time_zone, currency)`.
- `engine.quality.QualitySettings(spike_limit, device_spike_limits)` takes the same types as `IntegrationSettings`
  (`None` = off).

### Design decisions
- **D-1 Request fields** (identical for websocket and service):
  | Field | Type | Rule |
  |---|---|---|
  | `start` | string, required | Either a local date `YYYY-MM-DD`, meaning local midnight in the **settings** time zone, or an ISO datetime. A datetime without an offset is read in the settings time zone (fold 0). Parse with `dt_util.parse_datetime`. |
  | `end` | string, required | Same formats. **Exclusive**: `start 2026-01-01`, `end 2026-02-01` is January. |
  | `grouping` | `hour` / `day` / `week` / `month` / `total`, required | `vol.In(Grouping values)`. |
  | `entities` | list of entity ids, optional | Omitted or `[]` means all configured `settings.entities`, in settings order. Otherwise the list must be a subset of the configured entities, in the order given, with duplicates removed (first occurrence kept). |
  - The time zone is **not** a request field. The settings time zone defines zones and groupings (SPEC §2), and an
    override would re-zone hours differently from the configured plans.
  - Date bounds in a time zone with a non-whole-hour offset: local midnight is not a UTC hour, so the bound becomes
    the **first UTC hour whose local start is on or after** local midnight (ceil). This matches SPEC §5's attribution
    rule. A datetime bound must already fall on a whole UTC hour, otherwise `invalid_period`.
- **D-2 Processing** (`report_api.py`, shared by both front ends):
  1. Entry: the single entry of `DOMAIN` with `state is ConfigEntryState.LOADED`, else `not_loaded`.
  2. Bounds → `ReportRequest(start, end, tzinfo, grouping)`. A parse failure, a non-whole hour or `end <= start` →
     `invalid_period` (placeholder `detail`).
  3. Limits: `grouping == hour` and `end - start > 31 days + 1 h` → `period_too_long` (max 745 hourly buckets).
     Otherwise `end - start > 3660 days` → `period_too_long`. Placeholders `max`.
  4. Entities (D-1). An unknown one → `unknown_entity` (placeholder `entity_id`, the first offender).
  5. `await async_read_hourly_changes(hass, ids, request.start, request.end)`.
  6. `quality = QualitySettings(spike_limit=settings.spike_limit, device_spike_limits=settings.device_spike_limits)`.
  7. `report = await hass.async_add_executor_job(partial(build_report, request, schedule, [s.series for s in read],
     quality=quality))`. The engine never runs in the event loop.
  8. Names: `hass.states.get(id).name` if the state exists, else the entity registry entry's `name or
     original_name`, else the adapter's metadata `name`, else the id. `DeviceInfo(id, name, status.value)`.
  9. `report_to_json(report, devices=..., time_zone=settings.time_zone, currency=hass.config.currency)`.
  - Errors are a `ReportError(Exception)` with `code: str` and `placeholders: dict[str, str]`. The websocket maps it
    to `send_error(msg["id"], code, english_message)`. The service maps it to `ServiceValidationError(translation_domain=
    DOMAIN, translation_key=code, translation_placeholders=placeholders)`. Recorder or engine exceptions are not
    caught: the websocket answers `unknown_error`, and the service raises them (011 D-5).
  - Error codes: `not_loaded`, `invalid_period`, `period_too_long`, `unknown_entity`.
- **D-3 Websocket command** `energy_cost_stats/report` (`websocket.py`). Any authenticated user may call it, **no
  `require_admin`**: the report is read-only and per-device energy is already visible to non-admins in the Energy
  dashboard. The result is the 012 document.
- **D-4 Service** `energy_cost_stats.get_report` (`services.py`, `services.yaml`). `SupportsResponse.ONLY`, and the
  schema mirrors D-1 (`cv.string` for the bounds, `cv.entity_ids` for `entities`). The response is the **same** dict
  as the websocket result. `services.yaml` uses `text` selectors for `start`/`end` (examples `2026-01-01` and
  `2026-01-01T07:00:00+03:00`), a `select` with `translation_key: grouping`, and an `entity` selector (`multiple`,
  filter `domain: sensor`, `device_class: energy`). The description says that numbers are strings (`| float` in
  templates) and that `end` is exclusive.
- **D-5 Registration.** `async_setup` registers the websocket command and the service once. `async_unload_entry`
  does not unregister them (action-setup rule). With no loaded entry, both answer `not_loaded`.

## Files
- create: `custom_components/energy_cost_stats/report_api.py` — `ReportError`, `parse_bound(text, tz) -> datetime`,
  `async_get_report(hass, *, start, end, grouping, entities) -> dict[str, Any]` (D-1, D-2).
- create: `custom_components/energy_cost_stats/websocket.py` — the command and `async_register_websocket(hass)` (D-3).
- create: `custom_components/energy_cost_stats/services.py` — the handler, schema and `async_register_services(hass)`
  (D-4).
- create: `custom_components/energy_cost_stats/services.yaml` — D-4.
- modify: `custom_components/energy_cost_stats/__init__.py` — `async_setup` registers both (D-5). Update the module
  docstring (no longer "no services").
- modify: `custom_components/energy_cost_stats/const.py` — `SERVICE_GET_REPORT`, `WS_TYPE_REPORT`, field names, error
  codes, limits.
- modify: `custom_components/energy_cost_stats/strings.json` — `services.get_report` (name, description, fields
  `start`/`end`/`grouping`/`entities`), `selector.grouping.options` (hour/day/week/month/total; keep the existing
  `selector.preset`), and `exceptions` for the four codes. Use literal text, with placeholders `{detail}`, `{max}` and
  `{entity_id}`.
- modify: `custom_components/energy_cost_stats/translations/en.json` — identical to `strings.json`.
- create: `tests/integration/test_report_api.py` — the tests below.
- modify: `docs/SPEC.md` §2 — under "websocket command" and "service", add the request fields (D-1), the error codes
  (D-2), no admin requirement (D-3), "same JSON as §4", `end` exclusive, and "the time zone comes from the settings".
- modify: `tasks/013-report-websocket-and-service.md` — status, notes.

## Tests to write first
All `integration`. Setup helper: `MockConfigEntry(domain=DOMAIN, options={"time_zone": "Europe/Moscow", "spike_limit":
"4", "device_spike_limits": {}, "entities": ["sensor.plug_01", "sensor.plug_02"]}, subentries_data=[<two-zone plan
2026-01-01, day "10.30", night "4.43">])`. "MSK day" = `start "2026-01-15"`, `end "2026-01-16"` = UTC
`[2026-01-14T21:00Z, 2026-01-15T21:00Z)`. Seed via the 011 `seed_statistics` fixture: plug_01 1 kWh/h and plug_02
2 kWh/h, each from the look-back hour `2026-01-14T20:00Z` through `2026-01-15T21:00Z`. `hass.states.async_set(
"sensor.plug_01", "0", {"friendly_name": "Plug 01"})`. plug_02 has no state.

Expected (day = local 07–23, 16 h; night 8 h): plug_01 t1 `"16.000"`/`"164.80"`, t2 `"8.000"`/`"35.44"`, cost
`"200.24"`, kwh `"24.000"`. plug_02 `"329.60"` + `"70.88"` = `"400.48"`. Total `"600.72"`, kwh `"72.000"`.

| Level | Test | Asserts |
|---|---|---|
| integration | `tests/integration/test_report_api.py::test_ws_report_two_zone_day` | ws `{type, start, end, grouping: "day"}` → `success`. The result has `schema_version 1`, `time_zone "Europe/Moscow"`, `start "2026-01-15T00:00:00+03:00"`, one bucket with the expected values above, and `devices == [{"entity_id": "sensor.plug_01", "name": "Plug 01", "statistics": "ok"}, {"entity_id": "sensor.plug_02", "name": "sensor.plug_02", "statistics": "ok"}]`. Every row status is `"complete"`. `issues == []`. `currency == hass.config.currency`. |
| integration | `tests/integration/test_report_api.py::test_service_returns_same_document` | `async_call(DOMAIN, "get_report", same fields, blocking=True, return_response=True)` == the ws result. `json.dumps` works on it. Calling without `return_response=True` raises (`ServiceValidationError` from HA's response-only check). |
| integration | `tests/integration/test_report_api.py::test_hour_grouping` | `grouping "hour"` → 24 buckets. The bucket starting `"2026-01-15T07:00:00+03:00"` has plug_01 t1 `"1.000"`/`"10.30"` and t2 `None` kWh. The 06:00 bucket has t2 `"4.43"`. |
| integration | `tests/integration/test_report_api.py::test_entities_subset_and_order` | `entities ["sensor.plug_02"]` → one device row. `["sensor.plug_02", "sensor.plug_01", "sensor.plug_02"]` → rows in order plug_02, plug_01. `[]` and omitted → both, in settings order. |
| integration | `tests/integration/test_report_api.py::test_ws_errors` | Parametrized: `start "2026-13-01"`, `start "yesterday"`, `end == start`, `start "2026-01-15T07:30:00+03:00"` → error `invalid_period`. `hour` over `2026-01-01`…`2026-02-02` → `period_too_long`. `day` over 3661 days → `period_too_long`. `entities ["sensor.other_01"]` → `unknown_entity`. `grouping "year"` → `invalid_format`. |
| integration | `tests/integration/test_report_api.py::test_service_errors` | The same faults through the service raise `ServiceValidationError` with `translation_domain == DOMAIN` and the matching `translation_key`. A bad `grouping` raises `vol.Invalid`. Each key exists in `strings.json` `exceptions`. |
| integration | `tests/integration/test_report_api.py::test_not_loaded` | After `async_setup_component(hass, DOMAIN, {})` with no entry, the service is registered (`hass.services.has_service`). Both front ends answer `not_loaded`. After unloading a loaded entry, they answer `not_loaded` too. |
| integration | `tests/integration/test_report_api.py::test_naive_and_offset_datetimes` | `start "2026-01-15T07:00:00"` (naive) equals `"2026-01-15T07:00:00+03:00"`, `"2026-01-15 07:00:00"` and `"2026-01-15T04:00:00Z"`: the top-level `start` is `"2026-01-15T07:00:00+03:00"` in all four cases. |
| integration | `tests/integration/test_report_api.py::test_half_hour_time_zone_date_bounds` | Settings `time_zone "Asia/Kolkata"`, `start "2026-01-15"`, `end "2026-01-16"` → `start "2026-01-15T00:30:00+05:30"` and `end "2026-01-16T00:30:00+05:30"` (ceil to the UTC hour, SPEC §5 limitation). No error. |
| integration | `tests/integration/test_report_api.py::test_no_plan_reports_unpriced` | Entry without subentries → `zones == []`, `plans == []`, row `cost None`, `unpriced_kwh "24.000"`, `unpriced_hours 24`. |
| integration | `tests/integration/test_report_api.py::test_retroactive_reprice` | Report, then `hass.config_entries.async_update_subentry(entry, plan, data=<day "11.00">)`, `await hass.async_block_till_done()`, report again → plug_01 t1 cost `"176.00"`, cost `"211.44"`. The statistics are unchanged. |
| integration | `tests/integration/test_report_api.py::test_quality_settings_applied` | plug_02 has one hour of `5` kWh (local 12:00), otherwise 2 kWh/h. With `spike_limit "4"` → plug_02 `excluded_kwh "5.000"`, status `"partial"`, one `excluded_spike` issue with `hours 1`. With options `device_spike_limits {"sensor.plug_02": None}` → measured, no issue. With a gap of local 05:00–08:00 in plug_01 → status `"estimated"` and an `estimated` issue. |
| integration | `tests/integration/test_report_api.py::test_device_without_statistics` | `entities` setting includes `sensor.plug_03` with no statistics → `devices[2].statistics == "no_statistics"`, row `kwh None`, status `"missing"`. The other rows are unaffected. A `W`-unit statistic configured as an entity → `"unsupported"`. |
| integration | `tests/integration/test_report_api.py::test_non_admin_may_call_ws` | `hass_ws_client(hass, hass_read_only_access_token)` → `success`. |
| integration | `tests/integration/test_report_api.py::test_engine_runs_in_executor` | Patch `report_api.build_report` with a wrapper that asserts no running loop (`asyncio.get_running_loop()` raises) and then delegates. The report succeeds. |
| integration | `tests/integration/test_report_api.py::test_no_entities_created` | After setup and a report, `hass.states.async_all()` has no entity whose platform is this domain (principle 1). |

## Acceptance criteria
Devcontainer:
- [x] Tests were written first: the Implementation notes record `test_report_api.py` failing (import error or
  `unknown_command`) before the code existed.
- [x] `dx uv run --group ha pytest -m integration` → all pass (009/010/011 tests included).
- [x] `dx script/test` → all levels pass. The engine coverage gate holds.
- [x] `dx uv run --group ha pyright` → 0 errors. `dx script/lint` → exit 0.

Either environment:
- [x] `uv run pytest -m unit` → passes (`test_strings_match_en_translation` included).
- [x] `rg -n "homeassistant.components.recorder" custom_components/` → only `recorder_adapter.py`.
- [x] `rg -n "round_money|round_kwh|round_price|quantize" custom_components/energy_cost_stats/*.py` → no matches
  outside `engine/` (rounding only in the serializer).
- [x] `rg -n "float\(" custom_components/energy_cost_stats/report_api.py custom_components/energy_cost_stats/websocket.py custom_components/energy_cost_stats/services.py`
  → no matches.
- [x] `rg -n "async_get_config_entry|require_admin" custom_components/energy_cost_stats` → no matches.
- [x] `strings.json` == `translations/en.json`, and both contain `services.get_report` with all four fields and
  `exceptions` for the four codes.
- [x] `docs/SPEC.md` §2 updated as listed. No other section changed.
- [x] No files outside "Files" touched (`manifest.json` only if hassfest requires `websocket_api`, recorded in the
  notes). Generic ids only.

CI:
- [ ] Both matrix legs green (HA 2025.4.0 / latest), plus `hassfest` and `hacs`.
- [ ] Manual (optional, human): in `script/develop`, *Developer tools → Actions* →
  `energy_cost_stats.get_report` with `start` = a recent date, `grouping: day` → the response shows per-device
  zones, and the log is clean.

## Out of scope
- The Lovelace card, static path and extra JS (stage 4).
- Short-term statistics for the current hour (011 D-4). Today's last hour shows as missing.
- Caching, pagination or streaming of large reports. Only the D-2 limits apply.
- A request-level time zone or spike-limit override.
- `icons.json` for the action (cosmetic; add with the card work).
- Main meter / "untracked" row, nested meters.

## Open questions
All decided by planner, confirm in PR review:
- D-1 `start`/`end` accept local dates or ISO datetimes, naive = the settings time zone. `end` is **exclusive**. The
  time zone cannot be overridden per request. Date bounds in half-hour time zones round up to the UTC hour.
- D-1 Omitted or empty `entities` = all configured entities. Explicit entities must be configured ones (no
  arbitrary statistic ids).
- D-2 Limits: hourly reports ≤ 31 days (745 buckets), other groupings ≤ 3660 days.
- D-2 Device display name order: state name → registry name → statistics metadata name → entity id.
- D-3 The websocket command needs no admin rights.
- D-4 The service returns exactly the websocket document (decimal strings).

<!-- Filled in by implementer -->
## Implementation notes
- Tests first: `test_report_api.py` failed at collection with `ImportError: cannot import name 'report_api'` before any code
  existed. After implementing, all passed on the first run.
- D-1..D-5 implemented as planned; all remain "decided by planner, confirm in PR review". `manifest.json` untouched
  (`websocket_api` imported without a dependency; hassfest result pending CI).
- pyright flags `homeassistant.components.websocket_api` re-exports as private, so `websocket.py` imports
  `websocket_command`/`async_response` from `.decorators`, `ActiveConnection` from `.connection`, and
  `async_register_command` from the package.
- 012 carry-over (time zone): `report_api._zone_name` takes the IANA key from the `ZoneInfo` the report is built in and
  raises `RuntimeError` if it differs from `settings.time_zone`; the serializer gets that derived name. Test:
  `test_time_zone_name_matches_report_zone`.
- Strict validation: websocket schema (`str` bounds, `vol.In(Grouping)`, `[cv.entity_id]`) gives `invalid_format`;
  bounds must be exactly `YYYY-MM-DD` or an ISO datetime on a whole UTC hour (`2026-1-15` is refused). Added tests
  beyond the task table: `test_ws_schema_errors` (non-string start, string `entities`, bad id), more `invalid_period`
  cases (end before start, short date), and `test_all_error_codes_translated` (strings.json shape, service
  description mentions strings).
- Service description says decimals are strings (`| float`) and `end` is exclusive. `devices[].statistics` is
  `HourlySeries.status.value`.
- `services.yaml` `grouping` select lists the options explicitly plus `translation_key: grouping`.
- Results (devcontainer): `script/test` 491 passed, coverage 100 %; HA 2025.4.0 leg `-m integration` 147 passed;
  pyright 0 errors; ruff check/format clean. Grep checks (recorder import, `float(`, `require_admin`) clean.
  Not run: CI matrix, hassfest/hacs, manual check.

## Follow-ups
- Today's last (incomplete) hour shows as missing until short-term statistics are considered (011 D-4).
- `icons.json` for the action when the card lands.

### Review round 1 follow-up (suggestions 1 and 2)
- `parse_bound` now rejects bounds outside years 1970..9000 (`ValueError`), and `async_get_report` also maps
  `OverflowError` to `invalid_period`. Four parametrized cases were added to the shared error table (`0001-01-01`,
  `9999-12-30`, `9999-12-31T23:30:00-05:00`, `1969-12-31`), so they run for both the websocket and the service. I added
  the cases and the code in one step and did not run the new cases against the old code, so I did not observe them failing.
- `test_no_entities_created` now asserts that the set of states equals `{sensor.plug_01}` (the seeded one), so any
  state added by the integration would fail it.
