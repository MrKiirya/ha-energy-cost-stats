# 011 — Recorder adapter: hourly `change` statistics with neighbour keys

Status: in-review
Roadmap: SPEC §8 stage 3 (websocket `report` + service + integration tests), task 1 of 3 (**011-recorder-adapter**,
012-report-serializer, 013-report-websocket-and-service). Stacked on 010 (branch from `task/010-tariff-plan-subentries`
or from `master` once 006/007/009/010 are merged).
Spec sections: SPEC §2 (adapter module), §5 (data quality, stage 3 adapter requirement, current hour), §6
(compatibility table, metadata reading); tasks/007-data-quality.md Open question 3 and "Stage 3 adapter rule";
CLAUDE.md principles 2, 5, 6

> Planner decisions are marked **(D-n)** and also appear under "Open questions" as "decided by planner, confirm in
> PR review". The human was away when this was planned.

## Goal
A new module `recorder_adapter.py` (the **only** module that imports `homeassistant.components.recorder`) reads the
hourly `change` long-term statistics of a list of statistic ids over a report window and returns one engine
`DeviceSeries` per id. Each series holds every in-window key, **plus the last key before the window and the first key
after it** wherever such keys exist, however far away they are. With those keys the engine's gap rules (task 007)
give window-independent results. Rows with `change is None` are dropped, so those hours are missing. Energy is
converted to kWh by the recorder. All database work runs in the recorder executor. Metadata is read through a small
pure function that ignores unknown fields. Nothing is wired to the websocket or a service yet (task 013).

## Context

### Engine contract this adapter serves (tasks/007-data-quality.md, SPEC §5)
- `DeviceSeries(device_id, deltas: Mapping[datetime, Decimal])`, keyed by UTC hour start. Floats enter **only**
  through `DeviceSeries.from_floats` (`Decimal(repr(x))`).
- A gap is an **absence of keys**. Every key's span reaches back to the previous key, wherever it is. The earliest key
  has no predecessor and is taken as measured (and spike-checked). So without the look-back key, a gap that started
  before the window turns into a false "measured" value, or a false spike. Without the look-ahead key, a trailing
  in-window gap whose catch-up comes after the window stays missing instead of estimated.
- 007's "Stage 3 adapter rule": drop rows with `change is None`.

### HA recorder API checked (2026-11-01)
Sources: [recorder/statistics.py @2025.4.0](https://github.com/home-assistant/core/blob/2025.4.0/homeassistant/components/recorder/statistics.py),
[recorder/statistics.py @dev](https://github.com/home-assistant/core/blob/dev/homeassistant/components/recorder/statistics.py),
[recorder/models/statistics.py @2025.4.0](https://github.com/home-assistant/core/blob/2025.4.0/homeassistant/components/recorder/models/statistics.py),
[recorder/models/statistics.py @dev](https://github.com/home-assistant/core/blob/dev/homeassistant/components/recorder/models/statistics.py),
[recorder statistics API changes (2025-10-16)](https://contributors.home-assistant.io/blog/2025/10/16/recorder-statistics-api-changes/).
- `statistics_during_period(hass, start_time: datetime, end_time: datetime | None, statistic_ids: set[str] | None,
  period: Literal["5minute", "day", "hour", "week", "month"], units: dict[str, str] | None, types: set[Literal["change",
  "last_reset", "max", "mean", "min", "state", "sum"]]) -> dict[str, list[StatisticsRow]]`. The parameters are the same
  (positional order and types) at 2025.4.0 and on `dev`. `dev` only adds `"year"` to `period`, which we do not use.
  **Call it with keyword arguments** so a future reorder fails loudly in CI.
- Result rows: `start` is a **float UNIX timestamp** (`StatisticsRow.start: float`). `change: float | None`. Ids
  without rows in the range are **absent** from the dict. Rows come sorted by `start`.
- `change` computation (both versions): `change` is requested, so `sum` is fetched internally. The baseline is
  the last row **before `start_time`** (`_statistics_at_time`), or 0 if there is none. Each row gives `change = sum -
  prev_sum`. A row with a `NULL` sum gives `change = None`, and `prev_sum` is **not** advanced, so the next row's
  change covers it. **Correction (review round 1):** the baseline is the last row before `start_time` even when its `sum` is
  `NULL` (taken as 0), so the first non-null row of a query can carry its full cumulative sum. A row's `change`
  only matches "relative to the previous non-null row" away from a query's first row. The adapter recomputes it.
- `units` maps a **unit class** to a display unit. `{"energy": "kWh"}` converts Wh/MWh/... to kWh, and the conversion
  applies to `change` too. `EnergyConverter` (`homeassistant.util.unit_conversion`, not a recorder module) has
  `UNIT_CLASS == "energy"` and `VALID_UNITS`.
- `get_metadata(hass, *, statistic_ids: set[str] | None = None, statistic_type: Literal["mean", "sum"] | None = None,
  statistic_source: str | None = None) -> dict[str, tuple[int, StatisticMetaData]]` has the same signature at 2025.4.0
  and on `dev`.
- `StatisticMetaData`: at 2025.4.0 `has_mean` (NotRequired, deprecated), `mean_type`, `has_sum`, `name`, `source`,
  `statistic_id`, `unit_of_measurement`. `dev` adds `unit_class`. 2026.11 removes `has_mean`. The adapter reads
  **only** `has_sum` and `unit_of_measurement`, with `.get()`, and ignores every other key (SPEC §6).
- Executor: the statistics functions open recorder DB sessions and must not run in the event loop. Use
  `get_instance(hass).async_add_executor_job(fn, *args)` (`from homeassistant.components.recorder import
  get_instance`), the same at 2025.4.0 and latest.
- Test seeding (integration tests only): `async_import_statistics(hass, metadata, statistics)` (source `"recorder"`,
  `statistic_id` a valid entity id) and `async_add_external_statistics(hass, metadata, statistics)` (`"<domain>:<id>"`,
  source = domain). `start` must be aware and on the whole hour. `mean_type` is accepted at 2025.4.0. On latest,
  omitting `mean_type` or `unit_class` calls `report_usage` (it breaks in 2026.11), so the test helper passes
  `unit_class` **only when** `"unit_class" in StatisticMetaData.__annotations__` (absent at 2025.4.0). After seeding,
  `await async_wait_recording_done(hass)`. That helper lives in
  `pytest_homeassistant_custom_component.components.recorder.common` and exists in PHCC 0.13.232 (checked) and latest.
  An omitted `sum` key gives a `NULL` sum row.

### Design decisions
- **D-1 Public API** (`custom_components/energy_cost_stats/recorder_adapter.py`):
  ```python
  class StatisticsStatus(StrEnum):
      OK = "ok"  # sum statistics in an energy unit
      NO_STATISTICS = "no_statistics"  # no metadata for this statistic id
      UNSUPPORTED = (
          "unsupported"  # has_sum is not True, or the unit is not an energy unit
      )


  @dataclass(frozen=True, slots=True)
  class HourlySeries:
      statistic_id: str
      status: StatisticsStatus
      series: DeviceSeries  # device_id == statistic_id; empty deltas unless status is OK
      name: str | None  # metadata "name" (display fallback for 013), None if absent


  def classify_metadata(metadata: Mapping[str, Any]) -> StatisticsStatus: ...


  async def async_read_hourly_changes(
      hass: HomeAssistant,
      statistic_ids: Sequence[str],
      start: datetime,
      end: datetime,
  ) -> tuple[HourlySeries, ...]: ...
  ```
  - The result keeps **input order**. Duplicate ids, an empty id, a naive `start`/`end`, a bound off the whole UTC
    hour, or `end <= start` → `ValueError` (raised before any DB work). Reuse `engine.timeutil.to_utc_hour`.
  - An empty `statistic_ids` → `()` without touching the recorder.
  - `classify_metadata`: `OK` iff `metadata.get("has_sum") is True` and `metadata.get("unit_of_measurement") in
    EnergyConverter.VALID_UNITS`. Everything else is `UNSUPPORTED`. Unknown keys (`mean_type`, `unit_class`,
    `has_mean`, future keys) never matter.
- **D-2 Which keys are returned.** For an `OK` id, `series.deltas` holds exactly:
  - every row with `start <= t < end` and `change is not None`;
  - the **last** row with `t < start` and `change is not None`, if any exists in the whole history;
  - the **first** row with `t >= end` and `change is not None`, if any exists in the whole history.
  Rows further out are trimmed, so the output is deterministic and small. Their values would be ignored anyway.
  Values come from `DeviceSeries.from_floats` on the converted `change`.
- **D-3 Query plan** (all inside **one** recorder-executor job; `period="hour"`, `units={"energy": "kWh"}`,
  `types={"change"}`). Constants `NEAR = timedelta(days=1)`, `FAR = timedelta(days=31)`,
  `EPOCH = datetime(1970, 1, 1, tzinfo=UTC)`:
  1. `get_metadata(hass, statistic_ids=set(ids))` → statuses. Only `OK` ids are queried.
  2. Main query `[start - NEAR, end + NEAR)` for all `OK` ids.
  3. Look-back, only for ids that still have no row before `start`: `[start - FAR, start - NEAR)`, then, for those still
     missing, `[EPOCH, start - FAR)`. Take the last usable row.
  4. Look-ahead, only for ids that still have no row at or after `end`: `[end + NEAR, end + FAR)`, then
     `[end + FAR, None)` (open end = up to now). Take the first usable row. Skip a look-ahead step whose start is after
     `dt_util.utcnow()`, because there can be no rows there.
  - The common case (data at most a day apart around the window) is **one** statistics query. Each fallback level
    runs only for the ids that need it.
  - Known cost (documented, accepted): the unbounded steps return every row in their range. That costs O(history)
    only for an id with a > 31-day hole right before (or after) the window. An id with no history at all on that side
    returns nothing and stays cheap. The recorder has no public "last row before t" query. `_statistics_at_time` is
    private, and we do not use private recorder functions.
- **D-4 The current, incomplete hour stays out of scope.** SPEC §5 mentions short-term (5-minute) statistics for the
  current hour. This stage still reads hourly long-term statistics only. The not-yet-compiled hour (and the last
  compiled hour until the recorder finishes, a few seconds after the hour) shows as **missing**, the same as any
  trailing gap, never as zero. Mixing 5-minute rows into hourly keys would add a second data source with its own
  gaps and catch-ups. Follow-up task: "today" accuracy through short-term statistics.
- **D-5 Recorder errors are not caught.** Exceptions from the recorder propagate to the caller (013 turns them into
  an error response). The adapter never returns partial data silently.
- **D-6 Test seeding fixture.** `tests/integration/conftest.py` gains a fixture `seed_statistics`. It returns
  `async def seed(statistic_id: str, sums: Mapping[datetime, float | None], *, unit: str = "kWh", has_sum: bool = True,
  mean_type: StatisticMeanType = StatisticMeanType.NONE, name: str | None = None) -> None`. Ids containing `:` go
  through `async_add_external_statistics` (source = the part before `:`), others through `async_import_statistics`
  (source `"recorder"`). `None` sums are written without a `sum` key. Rows with `has_sum=False` get `mean` values
  instead. `unit_class` is added only when supported (see Context). The fixture ends with `async_wait_recording_done`.
  It is shared with task 013.

### Environment for the implementer
Linux devcontainer (`dx` runs a command in it): `dx uv run --group ha pytest -m integration`, `dx script/test`,
`dx uv run --group ha pyright`, `dx script/lint`. CI runs both legs (HA 2025.4.0 / py3.13 and latest / py3.14). If
you can only run one leg locally, say which in Implementation notes.

## Files
- create: `custom_components/energy_cost_stats/recorder_adapter.py` — D-1 … D-5. Module docstring points to this task
  file. Imports: `homeassistant.components.recorder` (`get_instance`), `homeassistant.components.recorder.statistics`
  (`get_metadata`, `statistics_during_period`), `homeassistant.util.unit_conversion.EnergyConverter`,
  `homeassistant.util.dt`, and the engine (`.engine.models.DeviceSeries`, `.engine.timeutil.to_utc_hour`).
- modify: `tests/integration/conftest.py` — the `seed_statistics` fixture (D-6). The existing autouse fixture stays.
- create: `tests/integration/test_recorder_adapter.py` — the tests below.
- modify: `docs/SPEC.md`:
  - §2: replace "`recorder_adapter.py` (name TBD)" with the final name and one sentence on what it returns.
  - §5: under the stage 3 adapter requirement, add "implemented in task 011". Describe the trimmed neighbour keys,
    the widening query plan and its O(history) worst case. Replace the line "Current hour isn't compiled into LTS
    yet → use short-term ..." with D-4 (the current hour is missing in stage 3; short-term statistics are a
    follow-up).
  - §6: add a row "`get_metadata(statistic_ids=...)` | ≤ 2023.x | adapter reads only `has_sum` and
    `unit_of_measurement`". Add a note that the `statistics_during_period` parameters were verified identical at
    2025.4.0 and `dev` on 2026-11-01 (`dev` adds `period="year"`), with the links above.
- modify: `tasks/011-recorder-adapter.md` — status, implementation notes, follow-ups.

5 files (+ this task file).

## Tests to write first
All `integration` (they need the HA harness and the in-memory recorder). Generic ids only (`sensor.plug_01`,
`sensor.plug_02`, `sensor.power_01`, external `test:meter_01`). Window `W = [2026-01-15T00:00Z, 2026-01-16T00:00Z)`
unless stated otherwise. "1 kWh/h" means cumulative sums `1, 2, 3, ...` on consecutive hours. Compare values as
`Decimal` (`Decimal("1.0") == 1`).

| Level | Test | Asserts |
|---|---|---|
| integration | `tests/integration/test_recorder_adapter.py::test_reads_window_and_trims_neighbours` | plug_01 at 1 kWh/h from `W.start - 3 h` to `W.end + 3 h`. The result is one `HourlySeries` with `status OK` and `series.device_id == "sensor.plug_01"`. The deltas keys are exactly `W.start - 1 h`, the 24 window hours and `W.end` (26 keys), all UTC-aware, each value `== 1`. |
| integration | `tests/integration/test_recorder_adapter.py::test_change_relative_to_previous_row` | Sums `10.0` at `W.start - 1 h`, `12.5` at `W.start`, `13.0` at `W.start + 1 h`. The values are `12.5 - 10.0` and `0.5`, not the raw sums. The look-back key's own value is its sum minus the baseline (0 here, since it is the first row ever). |
| integration | `tests/integration/test_recorder_adapter.py::test_lookback_far` | Parametrized predecessor distances `2 days`, `40 days`, `400 days` before `W.start` (one row there), then 1 kWh/h inside W from `W.start + 2 h`. The predecessor key is present with its value, and the earliest in-window key carries the whole catch-up `change`. Feeding the series to `build_report` (MSK, the two-zone plan from 006/007) marks `W.start` … `W.start + 2 h` as estimated. Without the predecessor (seed only the in-window rows) the first key is measured as-is. |
| integration | `tests/integration/test_recorder_adapter.py::test_lookahead_far` | 1 kWh/h until `W.start + 20 h`, then nothing until one row at `W.end + 5 days` (and, parametrized, `+ 60 days`). That first after-window key is present, and no later key is. Through `build_report` the in-window hours 20–23 are estimated (not missing). |
| integration | `tests/integration/test_recorder_adapter.py::test_no_neighbours` | Data only from `W.start + 5 h` to `W.start + 10 h`, nothing before or after. The deltas contain exactly those 6 keys. |
| integration | `tests/integration/test_recorder_adapter.py::test_null_sum_rows_dropped` | 1 kWh/h, but the row at `W.start + 4 h` has no `sum`. That key is absent, and the `W.start + 5 h` value is `2` (the change relative to the last non-null sum). |
| integration | `tests/integration/test_recorder_adapter.py::test_wh_converted_to_kwh` | plug_02 with unit `"Wh"` and sums `1000, 2000, ...` per hour → every value `== Decimal("1.0")`. |
| integration | `tests/integration/test_recorder_adapter.py::test_statuses` | Ids in this order: `sensor.plug_01` (OK), `sensor.missing_01` (no statistics), `sensor.power_01` (unit `"W"`, `has_sum=False`, `mean_type=ARITHMETIC`). The statuses are `OK`, `NO_STATISTICS`, `UNSUPPORTED`, in input order. Non-OK series have empty deltas. `name` comes from the metadata. |
| integration | `tests/integration/test_recorder_adapter.py::test_classify_metadata_ignores_unknown_fields` | `classify_metadata` on `{"has_sum": True, "unit_of_measurement": "kWh", "mean_type": 0, "unit_class": "energy", "has_mean": False, "future_key": "x"}` → `OK`. Missing `has_sum` → `UNSUPPORTED`. `has_sum: False` → `UNSUPPORTED`. Unit `None` / `"W"` / `"m³"` → `UNSUPPORTED`. `"Wh"`, `"MWh"` → `OK`. |
| integration | `tests/integration/test_recorder_adapter.py::test_external_statistic_id` | `test:meter_01` seeded with `async_add_external_statistics` is read like an entity id (status OK, values correct). |
| integration | `tests/integration/test_recorder_adapter.py::test_rejects_bad_arguments` | `ValueError` for: duplicate ids, `""`, naive `start`, `start` at `:30`, `end == start`. `[]` → `()`. |
| integration | `tests/integration/test_recorder_adapter.py::test_runs_in_recorder_executor` | Patch `recorder_adapter.statistics_during_period` with a wrapper that records `asyncio.get_running_loop()` raising `RuntimeError` (not in the event loop) and then calls the real function. Every call ran off the loop. |
| integration | `tests/integration/test_recorder_adapter.py::test_single_query_when_neighbours_are_near` | Two OK ids with rows within 1 day around W. `statistics_during_period` is called exactly once (count with `wraps=`). With one id needing a 40-day look-back: three calls, and the fallback call only names that id. |
| integration | `tests/integration/test_recorder_adapter.py::test_window_independence_end_to_end` | BER time zone, plug_01 over local 2026-03-28 … 2026-03-31 with a gap inside a day, a gap across a midnight and one spike. Through `async_read_hourly_changes` + `build_report(HOUR)`, the 3-day window and each single-day window give equal rows for every common hour. |
| integration | `tests/integration/test_recorder_adapter.py::test_only_adapter_imports_recorder` | AST-scan every `.py` under `custom_components/energy_cost_stats`: only `recorder_adapter.py` imports `homeassistant.components.recorder` (or a submodule). This duplicates ruff TID251 as a test, because the ruff rule can be silenced per file. |

Expected values come from the rules in 007. If HA disagrees with the "checked" facts above, trust HA, fix the test,
and record it in Implementation notes. Never adjust kWh values just to make a test pass.

## Acceptance criteria
Devcontainer:
- [x] Tests were written first: the Implementation notes record `test_recorder_adapter.py` failing (import error)
  before `recorder_adapter.py` existed.
- [x] `dx uv run --group ha pytest tests/integration/test_recorder_adapter.py` → all pass.
- [x] `dx script/test` → all levels pass. The engine coverage gate (≥ 95 %) still holds.
- [x] `dx uv run --group ha pyright` → 0 errors.
- [x] `dx script/lint` → exit 0.

Either environment:
- [x] `uv run pytest -m unit` → passes (no unit test changed).
- [x] `rg -n "homeassistant.components.recorder" custom_components/` → matches only in `recorder_adapter.py`.
- [x] `rg -n "_statistics_at_time|from homeassistant.components.recorder.db_schema" custom_components/` → no
  matches (no private recorder API).
- [x] `rg -n "statistics_during_period\(" custom_components/energy_cost_stats/recorder_adapter.py -A 8` shows keyword
  arguments only.
- [x] `rg -n "float\(|Decimal\(" custom_components/energy_cost_stats/recorder_adapter.py` → no matches (floats enter
  only via `DeviceSeries.from_floats`).
- [x] `docs/SPEC.md` §2/§5/§6 updated as listed in "Files". No other section changed.
- [x] No files outside "Files" touched. Public-repo hygiene: generic ids, no real entity ids or paths.

CI:
- [ ] Both matrix legs green (HA 2025.4.0 / py3.13 and latest / py3.14), plus `hassfest`/`hacs`.

## Out of scope
- The websocket command, the service, the serializer and wiring settings into a report (tasks 012, 013).
- Short-term (5-minute) statistics for the current hour (D-4) → follow-up.
- Main meter / "untracked" row, nested-meter de-duplication, renamed-entity statistic id mapping (SPEC §5).
- Caching query results between reports.
- Writing external statistics (SPEC §2 stage 2), which is where `mean_type`/`unit_class` matter for writes.

## Open questions
All decided by planner, confirm in PR review:
- D-1 The adapter returns engine `DeviceSeries` plus a per-id status (`ok` / `no_statistics` / `unsupported`). Wrong
  units or non-sum statistics are reported, not raised.
- D-2 The neighbour keys are trimmed to exactly one before and one after the window.
- D-3 The look-back and look-ahead are unbounded (no cap) via widening queries. The worst case is O(history) for an id
  with a > 31-day hole next to the window. No private recorder API is used.
- D-4 The current incomplete hour is reported as missing in stage 3. Short-term statistics are a follow-up.
- D-5 Recorder exceptions propagate (no partial results).

<!-- Filled in by implementer -->
## Implementation notes
- Tests first: `tests/integration/test_recorder_adapter.py` was run before `recorder_adapter.py` existed and failed at
  collection with `ImportError: cannot import name 'recorder_adapter'`.
- Results: latest HA (py3.14) `script/test` 428 passed, engine coverage 100 %; integration 102 passed on HA 2025.4.0
  (py3.13 venv, `--no-sync`) and on latest; pyright 0 errors; ruff check and format clean. Not run: CI itself,
  hassfest/hacs.
- `get_instance` is imported from `homeassistant.helpers.recorder` (same function, public export). Pyright
  reports `homeassistant.components.recorder.get_instance` as a private import (`reportPrivateImportUsage`).
  The task text said `components.recorder`; behaviour is identical and the helpers path exists at 2025.4.0.
  The AST test and the `rg` criterion still hold (only `recorder_adapter.py` mentions `components.recorder`).
- `StatisticsRow` keys are not required in the TypedDict, so rows without `start` or with `change is None` are
  skipped (`row.get`) instead of indexing. `hass` is passed by keyword too.
- The look-ahead stops widening when the next step starts after `dt_util.utcnow()`.
- The `seed_statistics` fixture lives in `tests/integration/conftest.py`; the test module defines its own
  `SeedStatistics` callable alias (`tests/integration` is not a package, so relative imports fail).
- Extra test beyond the table: `test_lookback_missing_means_first_key_is_measured` (the "without predecessor" half of
  `test_lookback_far`, kept separate).
- `test_change_relative_to_previous_row`: the second value is `12.5 - 10.0 = 2.5` and the third `0.5`; the first
  (look-back) key is `10.0` (baseline 0).
- Review round 1 fixes: Required 1 (NULL-sum baseline). `types={"sum","change"}` is requested; the first non-null row
  of every query has its `change` recomputed as `sum - previous fetched non-null sum` (when one was fetched), HA's
  `change` is kept otherwise. Non-first rows keep HA's `change`: only the first non-null row of a query can have a bad
  baseline, so recomputing that one row is sufficient (HA converts `sum` to kWh before subtracting, so recomputing
  more rows would not add float noise either; it is just unnecessary). Regression tests: `test_null_sum_row_before_main_query_start`, `..._before_lookahead_query_start`,
  `..._before_lookback_step_start`; the first two failed on both HA legs before the fix (101 not 1, 24 not 3), the
  look-back one passed already (guard). SPEC §5 corrected. Suggestion 1: `test_runs_in_recorder_executor` now also
  wraps `get_metadata` and checks exactly one `async_add_executor_job` call. Suggestion 2:
  `test_future_lookahead_steps_are_skipped` (window ending now, one query). Suggestion 4: seed fixture maps
  `W`/`kW` to unit class `power`. Suggestion 3 (ban `helpers.recorder`) not done, optional.
- Planner decisions D-1 ... D-5 were implemented as written; confirm in PR review (see Open questions).

## Follow-ups
- "Today" accuracy through short-term (5-minute) statistics (D-4).
- Unbounded look-back/look-ahead is O(history) for an id with a >31-day hole next to the window; consider a cache or
  a different strategy if it shows up in practice.
- CI legs (py3.13/HA 2025.4.0, py3.14/latest) and hassfest/hacs still to be confirmed on the PR.
