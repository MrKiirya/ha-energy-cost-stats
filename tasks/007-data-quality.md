# 007 — Data quality: gap spreading, negative/spike exclusion, quality issues

Status: in-review
Roadmap: SPEC §8 stage 1 (engine + unit tests), task 4 of 4 (004-tariff-model, 005-time-and-zones,
006-pricing-and-grouping, **007-data-quality**)
Spec sections: SPEC §4 (rows, coverage), §5 (data quality, resets, missing data), §6 (minimum HA 2025.4);
CLAUDE.md principles 2, 3, 4, 6

## Goal
`build_report` gets a data-quality pre-pass. It replaces the per-device `prepare_measured` step and does
three things:
- An offline gap followed by a catch-up delta is spread evenly over the gap hours plus the catch-up hour.
  Each spread hour is priced in its own zone and flagged ESTIMATED.
- Negative deltas, and deltas above a per-device kWh/h limit, are EXCLUDED and reported.
- Every estimation and exclusion shows up as a `QualityIssue` in `Report.issues`.

With that, `Coverage.estimated/excluded`, `Row.estimated_kwh/excluded_kwh` and `Report.issues` carry real
values. Missing hours stay explicit `None`, never zero. Sums stay exact. The public signature only gains
one keyword-only parameter, `quality`. This finishes stage 1 (the engine).

## Context

### Prerequisite
Task 006 (`engine/report.py`, `engine/rounding.py`) must be merged into `master` first. Branch
`task/007-data-quality` from the updated `master`. If 006's review changes `report.py`, follow the merged
version. The seam this task relies on is `build_report` = `classify_hours` once → per-device prepare →
`assemble_report(request, hours, prepared, issues)`. `assemble_report` already handles MEASURED, ESTIMATED
and EXCLUDED values and passes `issues` through unchanged.

### Human decisions (confirmed)
1. Gap + catch-up → spread evenly over the gap hours plus the catch-up hour. Each hour is priced in its
   own zone and flagged estimated (SPEC §5).
2. **No maximum gap length** (2026-11-01). Any gap that has a catch-up gets spread.
3. A negative delta, or a delta above the per-device limit, is excluded and reported (count, kWh, when).
   - The default limit is 4 kWh/h. It is a global setting, with a per-device override or disable.
   - Small drops (< 10 %) are not resets. They arrive as negative deltas and are excluded.
4. Missing data is always explicit, never a silent zero. A trailing gap with no catch-up yet, and the hours
   before the first data point, stay missing.
5. Exact `Decimal` arithmetic everywhere. Spreading must keep the sum exact.

### How HA's recorder writes `change` for an unavailable `total_increasing` sensor (checked)
I checked HA core on `dev` and at tag `2025.4.0`, the minimum version from SPEC §6. Both behave the same:
- `homeassistant/components/sensor/recorder.py`, `compile_statistics` (5-minute short-term statistics):
  - States are converted with `float(state.state)` (`_entity_history_to_float_and_state`), so
    `unavailable`/`unknown` raise and are dropped.
  - When no valid float state is left in the period (`if not valid_float_states: continue`), the entity is
    **skipped**: no row is written, not even a `change 0` row.
  - The history query starts at `start - timedelta.resolution`, so it includes the last state before the
    period. A sensor that is available but unchanged therefore does get a row, and its change is a
    measured 0.
  - `old_state`/`_sum` are seeded from the **last stored short-term row**
    (`new_state = old_state = last_stat.get("state")`). The first row after an outage therefore adds
    `current value − last value before the outage`. That row is the catch-up delta.
  - Resets: `reset_detected` returns `fstate < 0.9 * previous_fstate`. A drop of 10 % or more is a reset,
    and the sum then continues from 0. A smaller drop is not a reset. It shows up as a negative change.
  - Sources: https://github.com/home-assistant/core/blob/dev/homeassistant/components/sensor/recorder.py
    and https://github.com/home-assistant/core/blob/2025.4.0/homeassistant/components/sensor/recorder.py
- `homeassistant/components/recorder/statistics.py`:
  - `_compile_hourly_statistics` builds an hourly row only for a `metadata_id` that has 5-minute rows in
    that hour, taking the sum from the last 5-minute row. **Fully unavailable hours have no hourly row.**
  - `_augment_result_with_change` sets each row's `change = sum − previous row's sum`. The baseline for
    the first row is the last row **before** the queried period. Missing hours get no row. A row with a
    `NULL` sum gets `change = None`, and the previous sum carries forward.
  - Source: https://github.com/home-assistant/core/blob/dev/homeassistant/components/recorder/statistics.py

Consequences for the design. These go into SPEC §5.
- A gap is an **absence of keys** in `DeviceSeries.deltas`, never a run of zeros. A `0` delta is a measured 0.
- The first key after a gap carries the whole gap's consumption. This holds even when the adapter's query
  starts later, because the baseline is the last row before the period. **But the engine can only see the
  gap if it also gets the key before it.** Look-back keys are therefore required for correct results.
- If a device restarts with a counter reset during an outage, HA counts only the new counter value. The
  energy used during the gap before the restart is lost upstream. This is a known limitation.
- A sensor that stays "available" with a stale value produces measured `0` rows and then one large delta.
  The engine cannot see this as a gap. The spike check may exclude that delta. This is a known limitation.
- Stage 3 adapter rule (not this task): rows with `change is None` are dropped, which makes them missing.

### Design decisions made in this task
1. **Public entry point** (`engine/report.py`). The three positional parameters stay frozen:
   ```python
   def build_report(
       request: ReportRequest,
       schedule: TariffSchedule,
       devices: Sequence[DeviceSeries],
       *,
       quality: QualitySettings | None = None,
   ) -> Report
   ```
   - `None` means `QualitySettings()`, the defaults.
   - The pipeline is `classify_hours` once → `prepare_series(...)` per device → `assemble_report(...,
     issues)`.
   - `prepare_measured` stays, unchanged. It is the baseline for the equivalence test and is no longer
     called by `build_report`.
2. **Module split, to avoid a circular import.** Move `HourKind`, `HourValue` and `PreparedSeries`
   unchanged into a new `engine/prepared.py`. `report.py` imports them from there, so
   `from engine.report import HourKind, HourValue, PreparedSeries` keeps working and `test_report.py` needs
   no change. `engine/quality.py` imports from `prepared.py`, `classify.py` and `models.py`, never from
   `report.py`. `report.py` imports `quality.py`.
3. **Settings** (`engine/quality.py`):
   ```python
   DEFAULT_SPIKE_LIMIT = Decimal("4")  # kWh per hour
   SPREAD_QUANTUM = Decimal("1E-20")  # kWh


   @dataclass(frozen=True, slots=True)
   class QualitySettings:
       spike_limit: Decimal | None = DEFAULT_SPIKE_LIMIT  # None = check disabled globally
       device_spike_limits: Mapping[str, Decimal | None] = field(default_factory=dict)

       # per-device override; value None = check disabled for that device
       def limit_for(self, device_id: str) -> Decimal | None: ...
   ```
   - Validation happens in `__post_init__`. Every limit must be `None` or a finite `Decimal > 0`.
     `bool`, `int`, `float`, NaN, ±Infinity, `0` and negative values → `ValueError`. Override keys must be
     non-empty `str`.
   - The mapping is copied into a `MappingProxyType`, like `DeviceSeries` does it.
   - Overrides for ids that are not in `devices` are ignored, since the config may name removed devices.
   - The negative check **cannot** be disabled. It is not a setting.
4. **Pre-pass**:
   ```python
   def prepare_series(
       series: DeviceSeries,
       hours: Sequence[HourInfo],
       *,
       time_zone: tzinfo,
       settings: QualitySettings,
   ) -> tuple[PreparedSeries, tuple[QualityIssue, ...]]
   ```
   - `hours` is the contiguous, non-empty output of `classify_hours`. Empty `hours` → `ValueError`.
   - Rules, all keyed on UTC hours:
     - a. Sort all keys of `series.deltas`, **including keys outside the window**. Every key `k` with
       delta `D` defines a **span**:
       - If `k` has a predecessor key `p` (the previous key in sorted order, any value, inside or outside
         the window), the span is the UTC hours `(p, k]`, so `n = (k − p) / 1 h` hours.
       - `n == 1` means a contiguous hour. `n > 1` means a gap of `n − 1` hours plus the catch-up hour `k`.
       - Gap length is not capped (human decision 2).
     - b. **The earliest key has no known predecessor.** Its span is just `[k, k+1h)` (`n = 1`), and every
       hour before it stays missing. From the series alone, the engine cannot tell "first ever data
       point" from "catch-up after a gap that started before the look-back". It takes the conservative
       reading: the value is measured as-is, and the spike check still applies. **For window-independent
       results the caller must pass at least the last key before the window and the first key after it.**
       This becomes a stage 3 adapter requirement in SPEC §5.
     - c. A delta can be rejected:
       - `D < 0` → `EXCLUDED_NEGATIVE`. This is checked first, so it wins over the spike check.
       - Otherwise, if `limit = settings.limit_for(device_id)` is not `None` and `D > limit × n`, the delta
         is `EXCLUDED_SPIKE`. This compares the **per-hour average after spreading** with the limit, so a
         legitimate catch-up after a long gap is not excluded. The comparison is strict (an average
         exactly equal to the limit passes), and it is done by multiplication, so no division is involved.
       - For a rejected delta, **only the catch-up hour `k`** becomes `HourValue(D, EXCLUDED)`. The gap
         hours stay **missing** (`None`), because there is no trustworthy value for them.
     - d. An accepted delta with `n == 1` → `HourValue(D, MEASURED)`. A measured `0` stays `0`.
     - e. An accepted delta with `n > 1` (this includes `D == 0`) is spread:
       - `q = (D / n).quantize(SPREAD_QUANTUM, rounding=ROUND_DOWN)`.
       - The `n − 1` gap hours get `q` each. The catch-up hour gets `r = D − (n − 1) × q`.
       - All `n` hours are `ESTIMATED`.
       - `0 ≤ r − q < n × 1E-20`, and `q × (n−1) + r == D` exactly.
       - The remainder goes to the catch-up hour, the only hour with a real reading. This is deterministic.
       - **Zero-change catch-up:** `D == 0` spreads to `n` estimated hours of `0`. The meter shows no
         consumption during the outage, so `0` is known, but these hours are still flagged estimated.
     - f. Hours outside the window are computed with the same `n` but are not emitted. A span that lies
       entirely outside the window has no effect and produces no issue.
     - g. Hours after the last key (a trailing gap) and hours before the earliest key stay `None`.
   - **Window independence** follows from rules a–g. The value of any hour depends only on the series,
     never on the window. A day report and a month report agree hour by hour, given the same series.
   - **Exactness.**
     - Everything runs in `localcontext(prec=50)`.
     - Spread values have exponent ≥ `min(exp(D), −20)`. With realistic magnitudes (< 10⁷ kWh per delta;
       float-derived inputs have ≤ 17 significant digits) they and their sums fit 50 digits. The
       aggregation in `assemble_report` therefore stays exact.
     - `SPREAD_QUANTUM` is a fixed exponent, not a context precision. A 50-digit quotient would make later
       sums inexact.
     - This is the **only** `quantize` outside `rounding.py`. It is internal and is not output rounding.
5. **Issues** (`QualityIssue`):
   - `ESTIMATED`: one issue per spread span that has at least one window hour.
   - `EXCLUDED_NEGATIVE` / `EXCLUDED_SPIKE`: one issue per rejected delta whose catch-up hour is in the
     window. The issue covers that hour only. The gap hours appear as missing coverage.
   - `start`/`end` are **clipped to the window**. `start` is the local start of the first in-window hour of
     the span. `end` = `(last in-window hour's utc_start + 1 h).astimezone(time_zone)`. Both are in the
     report time zone, as for buckets.
   - `kwh` = the sum of the in-window values of that issue: the full `D` for exclusions, the in-window share
     for estimates.
   - **Invariants** (tested), per device over the window:
     - sum of ESTIMATED issue `kwh` == totals row `estimated_kwh`;
     - sum of EXCLUDED_* issue `kwh` == `excluded_kwh`;
     - number of EXCLUDED_* issues == `coverage.excluded`;
     - sum of ESTIMATED issue hours (`(end − start) / 1 h`) == `coverage.estimated`.
   - Order: devices in input order, then by `start`. Consecutive excluded hours are **not** merged, so the
     count in "count, kWh, when" stays direct.
6. **Performance.** O(K log K + H) per device, where K = number of keys and H = number of window hours.
   Sort once. Map in-window hours with `(t − request.start) // 1 h`. Never scan every hour of a long gap that
   lies outside the window, because gaps are uncapped: emit only the overlap with the window. The
   implementer may bisect to the keys around the window.
7. **Existing 006 tests.** None should need a change. Leading and trailing gaps stay missing, the look-back
   values in `test_lookback_keys_ignored` are all outside the window, and the gaps in
   `test_bucket_invariants_across_groupings` now get spread, but the invariants still hold.
   - If a 006 test does fail, it must be explained by a rule above. Record the reason in the implementation
     notes before adjusting the test. Never adjust money or kWh values just to make a test pass.

### Environment for the implementer
Native Linux **without Home Assistant** (`uv sync`, no `ha` group).
- Unit tests, coverage and ruff run locally.
- **Pyright is verified by CI.** `uv run pyright custom_components/energy_cost_stats/engine tests/unit` is
  a recommended local check, not a gate.

## Files
- create: `custom_components/energy_cost_stats/engine/prepared.py` — `HourKind`, `HourValue`,
  `PreparedSeries`, moved unchanged from `report.py`.
- create: `custom_components/energy_cost_stats/engine/quality.py` — `DEFAULT_SPIKE_LIMIT`,
  `SPREAD_QUANTUM`, `QualitySettings`, `prepare_series`. Stdlib and relative imports only. The docstring
  points to this task file.
- modify: `custom_components/energy_cost_stats/engine/report.py`:
  - import the moved types from `prepared.py`;
  - `build_report` gains keyword-only `quality` and calls `prepare_series`;
  - update the module docstring (the pipeline line).
- create: `tests/unit/test_quality.py` — the tests below.
- modify: `docs/SPEC.md` §5:
  - Replace the "Data quality (implemented in task 007)" bullet with the rules from decisions 4–5:
    span/predecessor, earliest key, average-after-spreading spike check, rejected catch-up → only that
    hour excluded and the gap stays missing, zero catch-up, the remainder going to the catch-up hour at
    1E-20, issues clipped to the window, window independence.
  - Add the HA recorder facts with source links: no row for unavailable hours, catch-up relative to the
    last row, the reset ratio of 0.9.
  - Add the stage 3 adapter requirement: pass the neighbouring key before and after the window, and drop
    `change is None` rows.
  - Add the known limitations: counter reset during an outage, stale "available" values.
- modify: `tasks/007-data-quality.md` — status, implementation notes, follow-ups.

Do **not** modify `engine/models.py`, `engine/classify.py`, `engine/tariff.py`, `engine/timeutil.py`,
`engine/rounding.py` or `tests/unit/test_report.py` (see decision 7 for the exception). If a change there
turns out to be unavoidable, stop and record why.

## Tests to write first
Fixtures are the same as in `test_report.py` (copy the small helpers, do not import across test modules):
- `MSK`/`BER`, the device ids `sensor.plug_01`/`sensor.plug_02`;
- the default plan `ru_two_zone(valid_from=date(2026, 1, 1), day_price=Decimal("10.30"),
  night_price=Decimal("4.43"))`, with day = local 07–23 and night = local 23–07;
- "MSK day" = local 2026-01-15, DAY grouping;
- "1 kWh/h elsewhere" = `Decimal("1")` in every other window hour.

Comparisons are `Decimal ==` (by value; `0E-20 == 0`). Hours are given as local times.

| Level | Test | Asserts |
|---|---|---|
| unit | `tests/unit/test_quality.py::test_gap_spread_across_zones` | MSK day; keys for local 05:00–08:00 missing, catch-up at 09:00 = `10`, 1 kWh/h elsewhere. 5 hours estimated at 2 each (05, 06 night; 07, 08, 09 day). Row: `kwh == 29`, `estimated_kwh == 10`, `coverage == Coverage(24,19,5,0,0)`, status `ESTIMATED`. `t1` 19 kWh / `195.70`, `t2` 10 kWh / `44.30`, `cost == Decimal("240.00")`. `issues == (QualityIssue(ESTIMATED, plug_01, 2026-01-15T05:00+03:00, 2026-01-15T10:00+03:00, 10),)`. |
| unit | `tests/unit/test_quality.py::test_spread_remainder_is_exact` | `prepare_series` directly: predecessor at local 10:00, catch-up `1` at 13:00 (n = 3). Values at 11, 12 == `Decimal("0.33333333333333333333")`, at 13 == `Decimal("0.33333333333333333334")`, and their sum `== 1` exactly. Also `D = Decimal("0.1")`, n = 7: the sum of the 7 values == `0.1`, and `0 <= r - q < 7E-20`. |
| unit | `tests/unit/test_quality.py::test_spike_limit_applies_after_spreading` | MSK day; local 10:00–18:00 missing (9 h), catch-up at 19:00. Parametrized: `36` → 10 estimated hours (3.6/h); `40` → estimated (4.0/h equals the limit, which passes); `Decimal("40.0001")` → excluded: hour 19 `EXCLUDED`, hours 10–18 `None`, `coverage == Coverage(24,14,0,1,9)`, status `PARTIAL`, `kwh == 14`, `excluded_kwh == Decimal("40.0001")`, one `EXCLUDED_SPIKE` issue [19:00, 20:00) with kwh `40.0001`. |
| unit | `tests/unit/test_quality.py::test_contiguous_spike_excluded` | MSK day, 1 kWh/h, local 12:00 = `Decimal("4.5")` → `EXCLUDED_SPIKE`, `coverage.excluded == 1`, `kwh == 23`. The same value `4` → measured, no issue. |
| unit | `tests/unit/test_quality.py::test_negative_delta_excluded` | MSK day, 1 kWh/h, local 12:00 = `Decimal("-0.05")` (a small drop, not a HA reset) → `EXCLUDED_NEGATIVE` issue, kwh `-0.05`, `excluded_kwh == Decimal("-0.05")`, `kwh == 23`. With `QualitySettings(spike_limit=None)` it is still excluded (the negative check cannot be disabled). |
| unit | `tests/unit/test_quality.py::test_negative_catch_up_after_gap` | Local 10:00–12:00 missing, 13:00 = `-1` → hour 13 `EXCLUDED_NEGATIVE`, hours 10–12 `None`, `coverage == Coverage(24,20,0,1,3)`. |
| unit | `tests/unit/test_quality.py::test_zero_catch_up_spreads_zero_estimated` | Local 10:00–12:00 missing, 13:00 = `0` → 4 estimated hours of 0; `kwh == 20`, `estimated_kwh == 0`, `coverage.estimated == 4`, one ESTIMATED issue with `kwh == 0`. |
| unit | `tests/unit/test_quality.py::test_leading_and_trailing_gaps_stay_missing` | MSK day; no keys before local 04:00 and none after 19:00 (and none outside the window). `coverage == Coverage(24,16,0,0,8)`, `issues == ()`, no estimated hours. The earliest key (04:00 = `1`) is measured. |
| unit | `tests/unit/test_quality.py::test_earliest_key_without_lookback_is_measured_and_spike_checked` | MSK day; local 00:00–03:00 missing, 04:00 = `14`, 1 kWh/h after. **Without** a look-back key: 00–03 `None`, 04:00 `EXCLUDED_SPIKE` (14 > 4). **With** a look-back key at `start − 3 h` (= `1`): span `(start−3h, 04:00]`, n = 7, 2 kWh/h; in-window 00–04 estimated (5 h, 10 kWh); the ESTIMATED issue is clipped to [00:00, 05:00) with kwh `10`. |
| unit | `tests/unit/test_quality.py::test_gap_with_catch_up_after_window` | MSK day; local 20:00–23:00 missing, and a key `12` at `end + 1 h` (n = 6, 2/h). In-window 20–23 estimated, 8 kWh (t1: 20, 21, 22 → 6 kWh; t2: 23 → 2 kWh). The issue is clipped to [20:00, 2026-01-16T00:00+03:00) with kwh `8`. |
| unit | `tests/unit/test_quality.py::test_gap_entirely_outside_window_no_effect` | Keys before the window with a gap and a spike, all outside, plus a contiguous series inside: the report equals the one built from the in-window keys plus `start − 1 h`. `issues == ()`. |
| unit | `tests/unit/test_quality.py::test_very_long_gap_is_spread` | Predecessor key exactly 400 days before `start` (MSK has no DST, so 9600 h), then no keys until a catch-up `Decimal("9600.5")` at local 12:00 on the MSK day. No cap applies: n = 9600 + 12 = 9612 (compute n via `timedelta` in the test). The 13 window hours 00–12 are estimated with the exact shares: 12 × `q` plus `r` at 12:00, `q` and `r` as in rule e. This also guards performance: the test must run in well under 1 s (no per-hour loop over the out-of-window part). |
| unit | `tests/unit/test_quality.py::test_spread_across_dst_fall_back_berlin` | BER, window local 2026-10-25 (25 h). Keys up to `2026-10-24T21:00Z`; `22:00Z`–`02:00Z` missing (5 UTC h, including the repeated local 02:00); catch-up `6` at `03:00Z` (local 04:00+01:00); 1 kWh/h in the other window hours. n = 6, each 1 kWh, all in `t2`. Bucket `coverage == Coverage(25,19,6,0,0)`, `t2.kwh == 9`. |
| unit | `tests/unit/test_quality.py::test_window_independence` | BER, a series over local 2026-03-28 to 2026-03-31 (3 days, crossing spring DST) with gaps inside a day, a gap across a midnight, one spike and one negative, with no keys outside those 3 days. With HOUR grouping, the report over the 3-day window and the reports over each single day give equal rows (kwh, cells, estimated/excluded kWh, coverage) for every common hour. For each day and each issue kind, the day report's issue kWh sum equals the in-day sum from the 3-day report's hour rows. |
| unit | `tests/unit/test_quality.py::test_issue_invariants` | Parametrized over 2–3 deterministic series with mixed gaps, spikes and negatives, two devices, DAY grouping: the four invariants of decision 5 hold per device on `totals`. Issues come in device input order, then by `start`. Every issue `start`/`end` lies within `[request.start, request.end]` and carries the request tz offset. |
| unit | `tests/unit/test_quality.py::test_clean_series_equals_prepare_measured` | A contiguous series without negatives or spikes: `prepare_series(...)[0] == prepare_measured(...)`, with no issues. `build_report` with the default quality equals `assemble_report(req, hours, [prepare_measured(...)])`. |
| unit | `tests/unit/test_quality.py::test_per_device_override_and_disable` | Two devices, each with an `8` kWh contiguous hour. `QualitySettings(device_spike_limits={plug_01: Decimal("10")})` → plug_01 measured, plug_02 excluded. `{plug_02: None}` → plug_02 measured (disabled). `spike_limit=None` → both measured. An override for an unknown id is ignored. `limit_for` returns the override, `None`, or the global value. |
| unit | `tests/unit/test_quality.py::test_quality_settings_validation` | `ValueError` for global and override limits `Decimal("0")`, `Decimal("-1")`, `Decimal("NaN")`, `Decimal("Infinity")`, `4.0`, `4`, `True`, and for an empty override key. The mapping is read-only (`TypeError` on item assignment). Defaults: `spike_limit == Decimal("4")`. |
| unit | `tests/unit/test_quality.py::test_build_report_quality_is_keyword_only` | Passing `QualitySettings()` as the 4th positional argument → `TypeError`. `quality=None` equals the defaults. |
| unit | `tests/unit/test_quality.py::test_prepare_series_rejects_empty_hours` | `hours=()` → `ValueError`. |

Expected values were computed by hand. If `zoneinfo` disagrees on a DST boundary, trust `zoneinfo` and
record it. Never adjust money or kWh values to make a test pass.

## Acceptance criteria
Native (Linux or Windows, no HA):
- [x] Tests were written first: the implementation notes record `test_quality.py` failing
  (`ModuleNotFoundError: engine.quality` or equivalent) before `quality.py` existed.
- [x] `uv run pytest -m unit` → all pass, including every 006 test, with `test_report.py` unchanged (or a
  change justified in the notes per decision 7).
- [x] `uv run pytest -m unit --cov=custom_components/energy_cost_stats/engine --cov-branch --cov-report=term-missing --cov-fail-under=95`
  → passes; `quality.py` and `prepared.py` are each ≥ 95 % line+branch.
- [x] `uv run ruff check .` → exit 0; `uv run ruff format --check .` → exit 0.
- [x] `tests/unit/test_engine_isolation.py` passes. The new modules use stdlib and relative imports only,
  with no `homeassistant` import.
- [x] `rg -n "quantize" custom_components/energy_cost_stats/engine` → matches only in `rounding.py`, plus
  exactly one line in `quality.py`. `rg -n "round\(" custom_components/energy_cost_stats/engine` → matches
  only in `rounding.py`.
- [x] `rg -n "classify_hours|zone_for_hour" custom_components/energy_cost_stats/engine/quality.py` → no
  matches. `report.py` still has exactly one `classify_hours` call.
- [x] `rg -n "^def build_report" -A 7 custom_components/energy_cost_stats/engine/report.py` shows the three
  positional parameters unchanged and `*, quality: QualitySettings | None = None`.
- [x] `git diff --stat master` touches only the files in "Files". `models.py`, `classify.py`, `tariff.py`,
  `timeutil.py` and `rounding.py` are unchanged.
- [x] `docs/SPEC.md` §5 documents rules a–g, the issue clipping, window independence, the HA recorder facts
  with source links, the stage 3 neighbour-key requirement and the two known limitations.
- [x] Public-repo hygiene: only generic ids (`sensor.plug_NN`), generic prices and the zones
  `Europe/Moscow`/`Europe/Berlin`. No real entity ids, paths or hosts.

CI (pyright needs the HA environment):
- [x] `uv run --group ha pyright` → 0 errors. `engine` is strict: no `Any` leaks, no unnecessary casts.
- [ ] All required checks on the PR are green.

## Out of scope
- Stage 3 adapter: querying `statistics_during_period` with a look-back/look-ahead so the neighbour keys
  are present, dropping `change is None` rows, and float → `Decimal` via `DeviceSeries.from_floats`.
- Stage 2: storing `QualitySettings` in the config entry or options flow, and the per-device override UI.
- Detecting stale-but-available sensors, or counter resets during an outage (documented limitations).
- Merging consecutive excluded hours into one issue, and any issue severity or messages (stage 3/4
  presentation).
- Main meter / "untracked" row, nested-meter de-duplication (SPEC §5, out of stage 1).
- Golden tests on real statistics fixtures (stage 4; no anonymized fixtures exist yet).
- Removing `prepare_measured` (kept as the clean-series baseline).

## Open questions (1-5 accepted by default, confirm in PR review)
None blocking. These product-visible choices were made here and should be confirmed by the human in
review:
1. **Rejected catch-up after a gap:** only the catch-up hour is EXCLUDED (with the full delta), and the gap
   hours stay MISSING. The alternative would be to mark the whole span excluded.
2. **Zero-change catch-up** spreads to ESTIMATED zeros (`coverage.estimated` grows, status `ESTIMATED`).
   The alternative would be to treat the hours as measured zeros, or to leave the gap missing.
3. **The earliest key without a predecessor** is taken as measured and spike-checked, not spread. Correct
   results therefore depend on the stage 3 adapter passing the neighbouring keys. Please confirm this
   contract.
4. **Issues are clipped to the window** (start/end/kWh in-window only), so they sum to the row totals. The
   alternative would be to report the full outage span, including its out-of-window part.
5. **Global disable:** `spike_limit=None` disables the spike check for all devices. SPEC names only a
   per-device disable. Is a global off switch wanted?

<!-- Filled in by implementer -->
## Implementation notes
- Tests first: `tests/unit/test_quality.py` failed with `ModuleNotFoundError: No module named
  'engine.quality'` before `quality.py` existed.
- All commands ran in the devcontainer (`--group ha`): unit+integration 263 passed, engine coverage 100 %
  (line+branch, `quality.py` and `prepared.py` included), full pyright 0 errors, ruff check/format clean.
- `test_report.py` is unchanged and passes.
- Open questions 1-5 are accepted by default; confirm in PR review.
- Two of my own tests were wrong at first and were fixed (not the engine): in
  `test_gap_with_catch_up_after_window` the day-zone kWh is 13 + 6 and night 7 + 2 (the task's 16/8
  counts were off); in `test_gap_entirely_outside_window_no_effect` the outside keys must be contiguous up
  to `start - 1 h`, otherwise the first in-window key is itself a catch-up after a gap and is spread.
- `test_spike_limit_applies_after_spreading` is split into a parametrized pass test (36, 40) and a
  separate exclusion test (40.0001).
- Added `test_rejected_catch_up_after_window_has_no_effect` to cover the branch where a rejected catch-up
  lies after the window.
- `QualitySettings.device_spike_limits` uses `default_factory=dict[str, Decimal | None]` for strict pyright.
- `SPEC.md` §5 updated with rules a-g, recorder facts, adapter requirement and limitations.
## Follow-ups
- Stage 3 adapter must pass the neighbouring keys before/after the window and drop `change is None` rows.
- Stage 2: persist `QualitySettings` in config entry / options.
