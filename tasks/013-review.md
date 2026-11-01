# 013 — Review (round 1)

Verdict: APPROVE

Scope: `git diff task/012-report-serializer` (`__init__.py`, `const.py`, `strings.json`, `translations/en.json`,
`docs/SPEC.md`) plus the untracked `report_api.py`, `websocket.py`, `services.py`, `services.yaml`,
`tests/integration/test_report_api.py` and `tasks/013-report-websocket-and-service.md`. Planner decisions D-1 … D-5
accepted.

## Checks run
All of these ran inside the devcontainer.
- `sh script/test` (latest HA 2026.9.3) → `491 passed in 39.18s`, `Required test coverage of 95% reached. Total
  coverage: 100.00%`.
- `uv run --group ha pyright` → `0 errors, 0 warnings, 0 informations`.
- `uv run --group ha ruff check .` → `All checks passed!`. `ruff format --check .` → `79 files already formatted`.
  `sh script/lint` → exit 0.
- HA 2025.4.0 venv (`--no-sync`) `pytest -m integration` → `147 passed, 344 deselected in 31.81s`. In that venv,
  `from homeassistant.components.websocket_api.decorators import async_response, websocket_command` and
  `from homeassistant.components.websocket_api.connection import ActiveConnection` both import.
- Throw-away probes in the container's `/tmp` (deleted afterwards, nothing written to the repo):
  - **Gap across the window edge.** plug_01/plug_02 at 1 kWh/h, with the keys 2026-01-14T18Z…22Z missing and a
    catch-up at 23Z. The MSK window starts at 21Z. Hourly report for 2026-01-15 vs for 2026-01-14…17: every
    2026-01-15 hour has the same kwh, cost and status in both. The first hours are `1.000` / `estimated`, and the
    day total is `24.000`. So the adapter's look-back/look-ahead neighbours reach the engine, and gap spreading is
    window-independent end to end.
  - **DST, Europe/Berlin.** `2026-10-01`…`2026-11-01` hourly → 745 buckets, accepted (the limit of 31 d + 1 h is
    exactly right for a fall-back month). Naive `2026-10-25T02:00:00` → `02:00+02:00` (fold 0), 3 buckets to
    `04:00+01:00`. An explicit `+01:00` → 2 buckets. On the spring-forward day, the nonexistent naive
    `2026-03-29T02:00:00` → `03:00+02:00`.
  - **Reload race.** I sent a ws report, then changed `time_zone` in the options before reading the answer
    (Berlin, Kolkata, Moscow). Every answer was `success`, with a consistent `time_zone`. No `RuntimeError`.
  - `parse_bound("0001-01-01")` and `parse_bound("9999-12-31T23:30:00-05:00")` raise `OverflowError` (see
    suggestion 1).

## Acceptance criteria
- [x] Tests written first. Recorded in the Implementation notes (ImportError at collection). I can't check this from
  the working tree. The tests do exercise every D-1/D-2 behaviour (see below).
- [x] `pytest -m integration` all pass. Latest HA in `script/test`, and 147 on the 2025.4.0 leg.
- [x] `script/test` → all levels pass. Engine coverage is 100 %.
- [x] pyright 0 errors. `script/lint` exit 0.
- [x] Unit tests pass (they are part of the 491, `test_strings_match_en_translation` included).
- [x] `homeassistant.components.recorder` appears only in `recorder_adapter.py` (grep).
- [x] No `round_money|round_kwh|round_price|quantize` in `custom_components/energy_cost_stats/*.py` (grep).
- [x] No `float(` in `report_api.py`, `websocket.py` or `services.py` (grep).
- [x] No `async_get_config_entry` or `require_admin` (grep).
- [x] `strings.json` and `translations/en.json` are byte-identical (`cmp`). Both have `services.get_report`
  (name, description, the four fields), `selector.grouping.options` (5 values, `selector.preset` kept) and
  `exceptions` for the four codes.
- [x] `docs/SPEC.md`: one hunk, in §2 only. It covers the fields, exclusive `end`, the time zone from the settings,
  half-hour ceil, the limits, the error codes, no admin, "same JSON as §4" and `| float`.
- [x] No files outside "Files". `manifest.json` is untouched, and that is correct (see hassfest below). Only generic
  ids (`sensor.plug_0N`, `sensor.other_01`). No paths, IPs or personal data.
- [ ] CI matrix, hassfest and hacs — not run here (CI only).
- [ ] Manual check in the dev HA — optional, for a human.

## Focus points
- **Recorder → engine → JSON.** The task's expected numbers (`200.24`, `400.48`, `600.72`, `72.000`, hour buckets
  `10.30`/`4.43`) are asserted in full. `[item.series for item in read]` passes the adapter series unchanged,
  neighbour keys included. The edge-gap probe confirms this works. Quality settings come from `IntegrationSettings`
  without conversion. `test_quality_settings_applied` covers the global limit, the per-device `None` override and
  the estimated gap.
- **Validation.** Dates use a strict `^\d{4}-\d{2}-\d{2}$` and `date.fromisoformat`. Datetimes use
  `dt_util.parse_datetime`. Naive values get `replace(tzinfo=tz, fold=0)`. A non-whole UTC hour is refused. Date
  bounds round up to the next UTC hour (Kolkata `00:30+05:30`, tested). `end <= start` is checked. Limits are
  checked before entities, and the hour limit is `> 31 d + 1 h`. Unknown entities give `unknown_entity`. Duplicates
  are dropped, keeping the first. `[]` and an omitted field both mean all entities. Error messages are translated
  for the service (`ServiceValidationError` with the domain, key and placeholders, all keys in `strings.json`). The
  websocket gets English text plus the code.
- **`_zone_name` RuntimeError: unreachable for users.** `async_setup_entry` builds `tzinfo` with
  `dt_util.async_get_time_zone(settings.time_zone)`. Both HA versions implement that as
  `zoneinfo.ZoneInfo(time_zone_str)`, so `.key == settings.time_zone` by construction. `settings` and `tzinfo` are
  stored together in one `RuntimeData` object. `async_get_report` reads `entry.runtime_data` once. While a reload
  runs, the entry is not `LOADED`, so the request gets `not_loaded`. A request already in flight keeps the old,
  self-consistent object. The probe found no race. The check is an internal invariant (it turns the 012 carry-over
  into a hard guarantee), not a user error. A translated `ServiceValidationError` would be wrong for it: it would
  tell the user they made a mistake. Keeping it as `RuntimeError` (`unknown_error` / a logged traceback) is correct.
- **Websocket submodule imports.** `websocket_api/decorators.py` (`async_response`, `websocket_command`) and
  `connection.py` (`ActiveConnection`) are the modules where these names are defined, not re-exports. They have been
  stable for years and import on both 2025.4.0 and 2026.9.3. `async_register_command` comes from the package
  `__init__`, where it is defined. On 2026.9.3 it writes to `hass.data["websocket_api"]` with `setdefault`
  semantics, so registering in our `async_setup` works even before `websocket_api` itself is set up.
- **hassfest `dependencies`: not required.** hassfest is not installed in the container (`script/hassfest` is not
  part of the wheel), so I reasoned from its rules. `script/hassfest/dependencies.py` has `ALLOWED_USED_COMPONENTS`,
  and that set includes `websocket_api` (with `frontend`, `http`, `webhook`, `persistent_notification`, ...).
  Importing it without a manifest dependency passes. At runtime `websocket_api` is always loaded (`default_config`
  / `frontend`). The `hassfest` CI job confirms this on the PR, per the task's fallback.
- **Service.** Registered once in `async_setup` with `SupportsResponse.ONLY`. It is not unregistered on unload, and
  `test_not_loaded` covers both before setup and after unload. `services.yaml` fields (`start`, `end`, `grouping`,
  `entities`) match `strings.json` `services.get_report.fields`. The `select` uses `translation_key: grouping`,
  and `selector.grouping` exists. The yaml has no `name`/`description`, which is correct when translations exist.
- **No blocking I/O in the loop.** The engine runs via `hass.async_add_executor_job` (`test_engine_runs_in_executor`
  asserts there is no running loop). The recorder runs via `get_instance(hass).async_add_executor_job`. The rest is
  cheap in-memory work (registry, states, parsing).
- **Principles.** No platforms or entities. Recorder access only through the adapter. The engine has no
  `homeassistant` imports. The floor is respected (no `async_get_config_entry`; `SupportsResponse` and translated
  `ServiceValidationError` both predate 2025.4).

## Findings
### Required
None.

### Suggestions
1. `custom_components/energy_cost_stats/report_api.py:62-84` (`parse_bound`) — extreme years escape validation.
   `"0001-01-01"` and `"9999-12-31T23:30:00-05:00"` raise `OverflowError` (not a `ValueError`). Also,
   `"9999-12-30"` parses, but the adapter's `end + NEAR` then overflows. The websocket answers `unknown_error`, and
   the service raises an untranslated exception with a traceback in the log, where `invalid_period` was intended.
   Few users will hit this. Fix direction: catch `(ValueError, OverflowError)` in `async_get_report`, and/or reject
   bounds outside e.g. 1970…9000 with `invalid_period`. Add one parametrized case.
2. `tests/integration/test_report_api.py` (`test_no_entities_created`, the states check) —
   `s.entity_id.startswith(DOMAIN)` can never match: an entity of this integration would be
   `sensor.energy_cost_stats_…` / `button.…`. Only the registry assertion below it does real work. Use
   `s.domain == DOMAIN` together with an `entity_registry` platform lookup, or drop the states line.
3. `tests/integration/test_report_api.py` (`test_ws_report_two_zone_day`) — also assert
   `doc["end"] == "2026-01-16T00:00:00+03:00"`. That pins the exclusive end in the main end-to-end test, not only in
   the naive/offset test.
4. Edge-of-window gap spreading has no end-to-end test. The 011 adapter tests cover the neighbours, and my probe
   passed. A small test comparing a narrow and a wide window across a gap at the window start (like the probe
   above) would lock in the recorder → engine contract at this layer.
5. `report_api.py:46-51` — `ERROR_MESSAGES` duplicates `strings.json` `exceptions` (and differs from it by the
   trailing period). This is fine, because the websocket has no translation context. Consider a test that each
   `ERROR_MESSAGES` entry matches its `strings.json` message, without the final period, so the two can't drift.
6. `report_api.py:87` — `_loaded_entry` returns `Any`, so `runtime.settings` / `runtime.tzinfo` are untyped for
   pyright. Typing it as `ConfigEntry[RuntimeData]` (a `TYPE_CHECKING` import from `__init__`) would let pyright
   check the field accesses.
7. Docs: a naive datetime that does not exist on a spring-forward day (Berlin `2026-03-29T02:00:00`) silently
   becomes `03:00+02:00` (fold 0). This is consistent with D-1. One phrase in the field description or SPEC §2
   ("nonexistent local times move forward") would make it explicit.
