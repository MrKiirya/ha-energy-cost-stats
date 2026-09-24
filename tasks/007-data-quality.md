# 007 — Data quality: gap spreading, negative/spike exclusion, explicit missing data

Status: planned
Roadmap: SPEC §8 stage 1 (engine + unit tests), task 4 of 4 (after 006-pricing-and-grouping)
Spec sections: SPEC §5 (pitfalls: gaps, negative/absurd deltas, partial data, boundary misattribution); CLAUDE.md principles 2–4, 6

> **Human decisions (see "Open questions" at the end) override anything in this file that conflicts with them** —
> e.g. single-rate key `t0`, missing data as `None`, money/kWh serialized as strings, 7-day gap cap.
> Update the affected tests/criteria accordingly.

## Goal
The report stops trusting raw deltas blindly:
- When a plug was offline and then reports one big catch-up delta, that energy is spread evenly over the
  gap. Each hour of the gap is priced in its own zone and plan, and the hours are flagged **estimated**.
- Negative deltas are **excluded**, not summed.
- Implausibly large deltas (above a per-device kWh/h limit) are also **excluded**.
- Every exclusion and estimate is listed in `Report.issues` (what, which device, when, how many kWh). Rows
  carry counts and kWh for estimated/excluded hours.

Missing hours stay explicitly missing. With this, stage 1 (engine + unit tests) is complete.

## Context

### Decisions (human-confirmed, stage 1)
1. **Offline gap + catch-up delta** → spread evenly over the gap hours, each hour priced in its own zone,
   flagged `estimated`.
2. **Negative deltas** and **deltas above a per-device threshold** → excluded and reported (count, kWh,
   when), flagged `excluded`.
3. **Threshold**: default **4 kWh/h** (a typical 16 A socket gives ≈ 3.7 kW). It can be set globally. Each
   device can override it (e.g. a 10 kW water heater → 12 kWh/h) or disable the check.
4. **Missing data is explicit** (`missing` / `partial`), never a silent zero.
5. **Boundary misattribution** (a plug reports late across a zone boundary) is a documented known
   limitation. The engine does not try to correct it. Task 004 already recorded it in SPEC §5; check that
   the wording still matches.

### Facts checked in HA source (how "gaps" look in statistics)
`homeassistant/components/sensor/recorder.py` (dev branch,
https://github.com/home-assistant/core/blob/dev/homeassistant/components/sensor/recorder.py), `compile_statistics`:
- If an entity has no valid numeric state in the hour (e.g. `unavailable` all hour), `if not valid_float_states: continue`
  → **no row** for that hour. So a gap = UTC hours absent from the input. This matches the "absent key =
  missing" rule of task 005.
- The state just before the period start is fetched too, so an entity that is online but unchanged produces
  a row with `change` 0 (not a gap).
- A `total_increasing` reset is detected when the new value drops below 90 % of the previous one, and is
  handled inside the `sum`. Smaller drops show up as **negative `change`** → excluded by rule 2.
- After the gap, the first row's `change` = new value − last value before the gap = the catch-up delta.

### Rules (normative)
Definitions, per device, over the device's input hours in UTC order (**including hours before
`request.start` passed as look-back**):
- A **gap** = one or more consecutive missing hours with a present value **both before and after** it. The
  present value right after the gap is the **catch-up** hour. Missing hours before the first present value
  (leading) or after the last one (trailing) are **not** gaps. They stay `missing`, and the first present
  value is taken as-is.
- `limit = config.limit_for(device_id)`: the per-device override if the device id is in the overrides
  mapping (a value of `None` = check disabled for that device), otherwise the global
  `max_kwh_per_hour` (`None` = disabled for everyone).

Processing order for each present value `d` at hour `h`:
1. `d < 0` → **excluded_negative**. `h` is excluded. If `h` was a catch-up hour, the gap hours before it stay
   `missing`.
2. If `h` is a catch-up hour after `n` missing hours and `config.spread_gaps` is true, then
   `rate = d / (n + 1)`:
   - if `limit` is set and `rate > limit` → **excluded_spike** for `h`; the gap hours stay `missing`;
   - otherwise → the `n` gap hours and `h` itself all become `estimated`. Each of the first `n` hours gets
     `d / (n + 1)`; the last hour gets `d − sum(the others)`, so the parts add up to `d` **exactly**
     (`Decimal` division is not exact, e.g. 1/3).
3. Otherwise (no gap, or `spread_gaps` is false): if `limit` is set and `d > limit` → **excluded_spike**;
   else **measured**.
- The comparison is strict: `d == limit` is kept.
- A zero catch-up after a gap spreads zeros (estimated, 0 kWh): the device was off, which is a legitimate
  estimate.

Reporting:
- Estimated hours add to zone kWh/cost like measured ones (each hour in its own zone and plan) and to
  `Row.estimated_kwh`. Coverage counts `estimated`.
- Excluded hours add nothing to kWh/cost. They add their value to `Row.excluded_kwh`, and coverage counts
  them as `excluded`.
- `Report.issues` gets one `QualityIssue` per excluded hour (`kind`, `device_id`, `start`/`end` of that
  hour, `kwh` = the raw delta) and one per spread gap (`ESTIMATED`, `start` = first gap hour, `end` = end of
  the catch-up hour, `kwh` = the spread total). Everything is **clipped to the report window**: issue hours
  outside the window are dropped, and an estimated span that straddles `request.start` is reported from
  `request.start` with only the in-window kWh. Sort by `start`, then by input device order.
- Look-back hours (before `request.start`) are used only to detect gaps. They never appear in buckets or
  totals.

### API added in this task (`engine/quality.py`)
- `QualityConfig(max_kwh_per_hour: Decimal | None = Decimal("4"), per_device_max_kwh_per_hour: Mapping[str, Decimal | None] = {}, spread_gaps: bool = True)`,
  a frozen dataclass:
  - the mapping is stored as a read-only copy (use `field(default_factory=...)`);
  - thresholds must be finite and `> 0` (else `ValueError`);
  - `limit_for(device_id) -> Decimal | None`.
- `HourSample(kwh: Decimal, state: SampleState)` with `SampleState(StrEnum)`: `MEASURED`, `ESTIMATED`,
  `EXCLUDED_NEGATIVE`, `EXCLUDED_SPIKE` (missing = absent from the result).
- `prepare_series(series: DeviceSeries, config: QualityConfig) -> dict[datetime, HourSample]` covers all of
  the device's input hours, look-back included, plus the filled gap hours. This is a pure function.
- `compute_report(..., quality: QualityConfig | None = None)`: a new keyword argument; `None` means
  `QualityConfig()` (defaults on). `report.py` uses `prepare_series` instead of the task 006 identity
  preparation.

### Stage 3 notes (do not implement)
- The adapter should fetch some look-back hours before `start`, so that a gap which began before the window
  is spread correctly. How many hours is a stage 3 decision.
- Where the global and per-device thresholds are configured (options flow) is stage 2/3.

## Files
- create: `custom_components/energy_cost_stats/engine/quality.py` — as above.
- modify: `custom_components/energy_cost_stats/engine/report.py` — `quality` parameter, use
  `prepare_series`, fill estimated/excluded counts and kWh and `Report.issues`.
- modify (only if needed): `custom_components/energy_cost_stats/engine/models.py` — no renames or removals.
- modify (only if needed): `custom_components/energy_cost_stats/engine/serialize.py` — issues output already
  exists in the task 006 shape. Change only if a bug shows up.
- modify: `tests/unit/test_report_pricing.py` / `tests/unit/test_report_grouping.py` — only where the new
  default filtering changes an existing fixture (none should: task 006 fixtures stay ≤ 4 kWh/h and
  non-negative). Record any change in the implementation notes.
- modify: `docs/SPEC.md` §5 — only if the wording written in task 004 differs from what was built (e.g.
  spread over "gap + catch-up hour", look-back, clipping).
- create: `tests/unit/test_quality.py` — `prepare_series` and `QualityConfig` unit tests.
- create: `tests/unit/test_report_quality.py` — end-to-end through `compute_report`.

## Tests to write first
MSK = `Europe/Moscow`. Two-zone plan B (day `10.30`, night `4.43`) and plan A (day `9.00`, night `4.00`)
as in task 006. `H(n)` = a UTC hour helper.

| Level | Test | Asserts |
|---|---|---|
| unit | `tests/unit/test_quality.py::test_clean_series_all_measured` | Contiguous values ≤ 4 → every sample `MEASURED`, values unchanged. |
| unit | `tests/unit/test_quality.py::test_gap_spread_even` | 0.5 at h0; h1, h2 missing; 1.5 at h3 → h1, h2, h3 each `ESTIMATED` 0.5; h0 `MEASURED`. |
| unit | `tests/unit/test_quality.py::test_spread_sums_exactly` | 1 at h0; h1, h2 missing; `Decimal("1")` at h3 → 3 estimated parts; their sum `== Decimal("1")` exactly; the last part takes the remainder. |
| unit | `tests/unit/test_quality.py::test_spread_rate_over_limit_excluded` | 1 missing hour + catch-up 10 → rate 5 > 4: the catch-up is `EXCLUDED_SPIKE`, the gap hour is absent (missing). |
| unit | `tests/unit/test_quality.py::test_spread_vs_spike_contrast` | 3 missing hours + catch-up 12 → rate 3: 4 × `ESTIMATED` 3. The same 12 with no gap → `EXCLUDED_SPIKE`. |
| unit | `tests/unit/test_quality.py::test_threshold_boundary` | `4` → `MEASURED`; `Decimal("4.001")` → `EXCLUDED_SPIKE`. |
| unit | `tests/unit/test_quality.py::test_negative_excluded` | `Decimal("-0.2")` → `EXCLUDED_NEGATIVE` with kwh `-0.2`. |
| unit | `tests/unit/test_quality.py::test_negative_catch_up_after_gap` | Gap then `-0.3` → catch-up `EXCLUDED_NEGATIVE`; gap hours absent (missing). |
| unit | `tests/unit/test_quality.py::test_leading_and_trailing_missing_not_spread` | First value 2.0 after 5 leading missing hours → `MEASURED` 2.0, nothing filled before it; missing hours after the last value stay absent. |
| unit | `tests/unit/test_quality.py::test_zero_catch_up_spreads_zeros` | Gap of 2 + catch-up 0 → 3 × `ESTIMATED` 0. |
| unit | `tests/unit/test_quality.py::test_spread_disabled` | `spread_gaps=False`: gap hours stay missing; catch-up 3 → `MEASURED` 3; catch-up 10 → `EXCLUDED_SPIKE`. |
| unit | `tests/unit/test_quality.py::test_limits_per_device` | Overrides `{"heater_01": Decimal("12"), "plug_02": None}`: `limit_for("heater_01") == 12`, `limit_for("plug_02") is None`, `limit_for("plug_03") == 4`. A 10 kWh value → `MEASURED` for heater_01, `MEASURED` for plug_02 (50 also `MEASURED`), `EXCLUDED_SPIKE` for plug_03. |
| unit | `tests/unit/test_quality.py::test_global_limit_disabled` | `max_kwh_per_hour=None`: 50 → `MEASURED`; `-1` still `EXCLUDED_NEGATIVE`. |
| unit | `tests/unit/test_quality.py::test_config_validation` | `max_kwh_per_hour=Decimal("0")`, a negative override, `Decimal("NaN")` → `ValueError`; the overrides mapping is read-only after construction. |
| unit | `tests/unit/test_report_quality.py::test_gap_spread_across_zones` | MSK, plan B, `plug_01`: 0.5 at `17:00Z` (local 20:00, day); `18:00Z`, `19:00Z` missing (local 21, 22, day); 3.0 at `20:00Z` (local 23:00, night). Rest of the day 0.5/h measured. The day bucket includes estimated `t1` +2.0 kWh (`20.60`) and `t2` +1.0 (`4.43`); `estimated_kwh == 3.0`; coverage estimated 3; status `estimated` (no other gaps); one `ESTIMATED` issue from local 21:00 to 00:00 with kwh 3.0. |
| unit | `tests/unit/test_report_quality.py::test_gap_spread_across_day_and_plan_switch` | Plans A and B, 1 kWh/h measured except: `2026-06-30T20:00Z` (local 23:00 Jun 30) and `21:00Z` (local 00:00 Jul 1) missing; 3.0 at `22:00Z` (local 01:00 Jul 1). DAY grouping: the Jun 30 bucket `t2` gets 1.0 estimated at A night `4.00`; the Jul 1 bucket `t2` gets 2.0 estimated at B night `4.43`; the costs match the per-plan prices. |
| unit | `tests/unit/test_report_quality.py::test_spike_reported` | `plug_01` with 9.0 at one day hour, 1 kWh/h otherwise → that hour is excluded: row kwh 23, `excluded_kwh == 9`, coverage excluded 1, status `partial`; one `EXCLUDED_SPIKE` issue with the local start of that hour and kwh 9. |
| unit | `tests/unit/test_report_quality.py::test_negative_reported` | `-0.2` at one hour → excluded; `excluded_kwh == Decimal("-0.2")`; issue `EXCLUDED_NEGATIVE`; the total row sums `excluded_kwh` over devices. |
| unit | `tests/unit/test_report_quality.py::test_per_device_override_end_to_end` | `heater_01` with 10 kWh/h for 3 night hours and override 12 → all measured, cost `3 × 10 × 4.43 = 132.90`; `plug_01` with the same data under the default → 3 excluded. |
| unit | `tests/unit/test_report_quality.py::test_lookback_gap_clipped` | Window starts at `S`. Series: 1.0 at `S−3h`; `S−2h`, `S−1h`, `S` missing; 4.0 at `S+1h`; then 1.0/h. The report shows `S` and `S+1h` as estimated 1.0 each; nothing before `S` appears in buckets or totals; the `ESTIMATED` issue starts at `S` with kwh 2.0. |
| unit | `tests/unit/test_report_quality.py::test_lookback_exclusions_not_reported` | A negative value at `S−2h` (look-back) → no issue and no `excluded_kwh` in the report. |
| unit | `tests/unit/test_report_quality.py::test_trailing_missing_is_partial` | Data stops 5 hours before the window end → coverage missing 5, status `partial`, no estimates. |
| unit | `tests/unit/test_report_quality.py::test_empty_inputs_with_quality` | No devices → total status `missing`, `issues == ()`; a device with no data → status `missing`, `issues == ()`. |
| unit | `tests/unit/test_report_quality.py::test_quality_none_uses_defaults` | `compute_report(..., quality=None)` equals `compute_report(..., quality=QualityConfig())` for a series with a spike. |
| unit | `tests/unit/test_report_quality.py::test_issues_sorted_and_serialized` | Two devices with issues at interleaved hours → issues sorted by `start`, then device order; `report_to_dict` renders `kind` strings (`"excluded_spike"` …), ISO `start`/`end`, `kwh` as float with 3 dp. |

## Acceptance criteria
Windows native:
- [ ] `uv run pytest -m unit` → all pass (all task 004–006 tests still green, unchanged unless listed in the
  implementation notes).
- [ ] `uv run pytest -m unit --cov=custom_components/energy_cost_stats/engine --cov-branch --cov-report=term-missing --cov-fail-under=95` → passes; `quality.py` shows ≥ 95 % including branches.
- [ ] `uv run ruff check .`, `uv run ruff format --check .` → exit 0.
- [ ] `uv run pyright custom_components/energy_cost_stats/engine tests/unit` → 0 errors.

Container (or CI once task 003 has landed):
- [ ] `script/test` → green, including the engine coverage gate; `uv run --group ha pyright` → 0 errors.

General:
- [ ] `prepare_series` does not mutate its input (a test or the reviewer checks: `DeviceSeries.deltas` is
  read-only anyway).
- [ ] `rg -n "float\(" custom_components/energy_cost_stats/engine` → still only in `serialize.py` and
  `from_floats`.
- [ ] `docs/SPEC.md` §5 describes: gap spread over gap + catch-up hour, per-device limit (default 4 kWh/h,
  override/disable), negative exclusion, issues, look-back use, boundary misattribution as a known
  limitation.
- [ ] No files touched outside the "Files" list.

## Out of scope
- Correcting boundary misattribution (documented limitation only).
- Main meter / "untracked" reconciliation; nested-meter de-duplication (SPEC §5) — later stages.
- Short-term statistics for the current hour and the look-back length (stage 3 adapter).
- Configuration UI for thresholds (stage 2/3) and persisting them.
- Renamed `entity_id` handling (SPEC §5) — adapter/integration concern.
- Heuristics based on previous consumption (e.g. a "typical profile" instead of an even spread).

## Open questions
None — resolved by the human (2026-09-25):
- **Gap cap: 7 days.** Gaps up to 7 days (168 h) are spread and flagged "estimated". Longer gaps are not spread:
  the gap hours are `missing`, and the catch-up kWh is reported separately as "unallocated" (visible in the
  device's issues/totals, not priced into any zone). Make the cap a module constant/parameter with default 168 h.
- **The catch-up hour is part of the spread and flagged "estimated".**
- **Spike limit on spreads applies to the per-hour average** (`d / (n + 1)`), not the raw catch-up delta.

<!-- Filled in by implementer -->
## Implementation notes
## Follow-ups
