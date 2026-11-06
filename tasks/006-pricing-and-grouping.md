# 006 — Pricing and grouping: hourly deltas + schedule → full `Report`

Status: in-review
Roadmap: SPEC §8 stage 1 (engine + unit tests), task 3 of 4 (004-tariff-model, 005-time-and-zones,
**006-pricing-and-grouping**, 007-data-quality)
Spec sections: SPEC §3 (tariff model, rounding), §4 (report output), §5 (UTC vs local, DST, missing data);
CLAUDE.md principles 3, 4, 6

## Goal
The pure-Python engine gets one entry point,
`build_report(request, schedule, devices) -> Report`. It turns a `ReportRequest`, a `TariffSchedule` and a
sequence of `DeviceSeries` into a complete `Report` (the types task 005 fixed in `engine/models.py`). The
report has:
- one row per device plus a total row, with kWh, price and cost per zone;
- unpriced kWh (hours before the first plan);
- coverage: measured and missing hours (estimated and excluded stay 0 until task 007);
- one bucket per hour, day, week or month, or a single total bucket, all DST-correct;
- the whole-window `totals` bucket.

Every past hour is re-priced from the schedule on each call (principle 3). Missing hours never turn into
zeros. Sums are exact `Decimal`s. A small rounding helper module is added for the stage 3 serializer.
Task 007 can later add a data-quality pre-pass behind the same public signature.

## Context

### Human decisions (confirmed 2026-11-01)
1. **Rounding.** The engine keeps exact `Decimal` values in the `Report`, and nothing inside the engine's sums
   is rounded. Totals are exact sums, not sums of rounded cells. A small output helper rounds money to
   2 decimals with `ROUND_HALF_UP`, and the stage 3 serializer calls it. kWh precision is set below (3
   decimals). A displayed total may differ from the sum of the displayed cells by 0.01. This is accepted
   and must be written into SPEC §4.
2. **Missing hours are never silent zeros.** They are counted in `coverage.missing`. A cell or row with no
   counted hour carries `None` (task 005 decision, 2026-09-25), never `Decimal("0")`.

### Decisions inherited from tasks 004/005 (do not re-open)
- Each UTC hour is attributed by its local start. Plan = `schedule.plan_for(local_start.date())`. A plan
  switch takes effect at local midnight of `valid_from`.
- Bucket keys come from `classify.bucket_key`. A bucket's `start` and `end` are the start of its first
  window hour and the end of its last window hour, so edge buckets are clipped. Both are in the report time
  zone.
- `classify_hours` runs **once per report**, and all devices share its result. Never call
  `TariffPlan.zone_for_hour` per device × hour.
- Zone keys: `t0` single-rate, `t1` day/peak, `t2` night, `t3` semi-peak. `t0` never merges with `t1`.
- Stage 1 prices every hour with `Zone.price`. Volume bands are reserved and ignored.

### Design decisions made in this task
1. **Public entry point** (`engine/report.py`):
   ```python
   def build_report(
       request: ReportRequest,
       schedule: TariffSchedule,
       devices: Sequence[DeviceSeries],
   ) -> Report
   ```
   Pipeline: `classify_hours(...)` once → **prepare** each device → **assemble**.
   - In this task the prepare step is `prepare_measured(series, hours) -> PreparedSeries`.
   - Task 007 replaces that call inside `build_report` with its quality pre-pass. The pre-pass returns the
     same `PreparedSeries` plus `QualityIssue`s.
   - The three positional parameters are frozen. Task 007 may add **keyword-only parameters with defaults**
     (e.g. quality settings). That is source-compatible and is the documented extension point.
   - Stage 3 callers use only `build_report` and `engine.rounding`.
2. **Prepared values (engine-internal seam, `engine/report.py`):**
   - `class HourKind(StrEnum)`: `MEASURED`, `ESTIMATED`, `EXCLUDED` (values lowercase).
   - `HourValue(kwh: Decimal, kind: HourKind)` (frozen, slotted).
   - `PreparedSeries(device_id: str, values: tuple[HourValue | None, ...])` (frozen, slotted).
     `values[i]` belongs to `hours[i]`, and `None` = missing.
   - `assemble_report(request, hours, prepared, issues=()) -> Report` is the pure aggregation. It
     **already handles all three kinds**:
     - MEASURED counts in `kwh`, zone cells and `cost`, plus `coverage.measured`.
     - ESTIMATED counts the same way, and also in `estimated_kwh` and `coverage.estimated`.
     - EXCLUDED counts only in `excluded_kwh` and `coverage.excluded`. It is not part of `kwh`, cells or
       cost.

     With this split, task 007 only writes the pre-pass. The ESTIMATED and EXCLUDED branches are tested
     here by calling `assemble_report` with hand-built `PreparedSeries`.
   - `assemble_report` validates its input and raises `ValueError` if:
     - `len(values) != len(hours)`;
     - two entries share a `device_id`;
     - `hours` is empty (it cannot be, for a valid `ReportRequest`).
3. **Look-back keys.** `prepare_measured` reads `series.deltas.get(info.utc_start)` for each classified hour.
   Keys outside `[request.start, request.end)` are ignored here, because task 007 uses them as look-back.
4. **Grouping type** (005 review suggestion 1). `ReportRequest.grouping` stays annotated `Grouping | str`,
   so `models.py` and its tests do not change. `build_report` and `assemble_report` read it once as
   `grouping = Grouping(request.grouping)`. That call does nothing to an existing member, and it keeps
   pyright strict happy without a cast.
5. **Duplicate `device_id`s** in `devices` → `ValueError`. Rows must be addressable by id in stage 3.
   An **empty `devices`** sequence is valid:
   - every bucket has `rows == ()`;
   - the total row has `Coverage.empty()`, so its status is `MISSING`, and `kwh = cost = None`;
   - cells are `None`, but prices are still filled from the schedule.
6. **Buckets.**
   - One bucket for **every** bucket key that has at least one window hour, even when no device has data.
     Data gaps then show up as `MISSING` rows instead of vanishing buckets.
   - Buckets are in chronological order and contiguous: `buckets[i].end == buckets[i+1].start`,
     `buckets[0].start == request.start` and `buckets[-1].end == request.end`, as instants.
   - `Bucket.hours` = number of window hours in the bucket.
   - `start = first.local_start`. `end = (last.utc_start + 1 h).astimezone(tz)`.
   - For `Grouping.TOTAL`, `buckets == (totals,)`.
   - `Report.totals` is always the whole-window bucket, built by the same code path as any other bucket.
     Do not sum the other buckets to get it, so the invariant test below is meaningful.
7. **`Report.plans`** = the distinct plans that are in force for at least one window hour (from the
   classification), in chronological order.
   **`Report.unpriced_hours`** = the number of window hours with `plan is None`. It depends only on the
   schedule, not on the devices.
8. **`Report.zones` ordering and union.**
   - Take the union of zone keys over `Report.plans`, in order of first appearance: plans in chronological
     order, and each plan's zones in its declaration order. Example: `t0` single-rate followed by `t1`/`t2`
     two-zone gives `(t0, t1, t2)`. A three-zone plan followed by a two-zone plan gives `(t1, t2, t3)`.
   - `ZoneLabel.name` = the name the key has in the **latest** of `Report.plans` that contains it, so a
     rename shows up as the current name.
   - Plans outside the window add no zones.
   - Window entirely before the first plan: `zones == ()`, `plans == ()`, and every row has `zones == ()`.
9. **Cells** (`ZoneCell`, one per `Report.zones` entry, same order, in every row and the total row):
   - `kwh` and `cost` = exact sums over the device's counted hours (MEASURED and ESTIMATED) whose zone key
     is the cell's key. Both are `None` if there are **no** such hours. That covers a missing zone and a zone
     not in force in the bucket alike. A measured `0` stays `Decimal("0")`.
   - `price` comes from the schedule, not the data, so it is the same for every row in the bucket. It is the
     single `Zone.price` among the bucket's window hours in that zone. If those prices differ (a plan switch
     with a price change inside the bucket), it is `None`. If the zone has no hour in the bucket, it is also
     `None`.
   - Prices are compared by value: `10.3 == 10.30` counts as one price, and the first one met is kept. So a
     plan switch that only renames something keeps a single price.
10. **Rows.**
    - `kwh` = the sum of counted kWh, priced plus unpriced. It is `None` iff the row has no counted hour,
      i.e. `coverage.measured + coverage.estimated == 0`.
    - `cost` = the sum of cell costs. It is `None` iff no counted hour was **priced**. A row that has only
      unpriced data therefore gets `cost = None`, which means "unknown", not "free".
    - `unpriced_kwh` = counted kWh in hours with `plan is None`, `Decimal("0")` if none.
      `estimated_kwh` and `excluded_kwh` are `Decimal("0")` when there are none.
    - `coverage.expected = bucket.hours` for each device row.
11. **Total row** (`device_id=None`):
    - Each numeric field is the sum over the device rows, skipping `None`. It is `None` iff every device
      value is `None`.
    - `coverage` = the sum of the device coverages, so `expected = hours × devices`.
    - Cell prices are the same as in the device rows.
12. **Exactness.**
    - All engine arithmetic runs inside `decimal.localcontext(prec=50)` (keyword form, Python ≥ 3.11). The
      results then do not depend on the caller's context, and a sum fits 50 significant digits.
    - Exactness is therefore guaranteed for any realistic input.
    - The engine never calls `quantize` or `round`.
    - Cost may be computed per hour (`kwh * price`) or per `(zone, price)` group (`sum(kwh) * price`). Both
      are exact at this precision.
13. **Negative deltas** pass through unchanged in this task: they count as MEASURED and are summed as-is.
    Task 007 excludes them. No test pins this behaviour, so 007 can change it freely.
14. **Performance.**
    - Aggregate in a single pass, O(devices × hours). Precompute each hour's bucket index and zone key once
      from `hours`, and do not re-scan the hours per bucket.
    - The cached per-plan hour lookup from 005 is enough. Caching `plan_for` per date (005 follow-up 4) stays
      out of scope: about 20 ms for a one-year window, called once per report.
15. **Rounding helpers** (`engine/rounding.py`, for the stage 3 serializer and the card payload):
    - `MONEY_QUANTUM = Decimal("0.01")`, `KWH_QUANTUM = Decimal("0.001")`,
      `PRICE_QUANTUM = Decimal("0.0001")`.
    - `round_money(value: Decimal) -> Decimal`, `round_kwh(value: Decimal) -> Decimal` and
      `round_price(value: Decimal) -> Decimal` all quantize with `ROUND_HALF_UP` inside
      `localcontext(prec=50)`.
    - Prices get 4 decimals: configured prices with 2 decimals still show exactly, and effective prices of
      mixed-price cells (`cost / kwh`) stay meaningful.
    - Non-`Decimal` input (including `bool`, `int` and `float`) or a non-finite value → `ValueError`.
    - A negative zero result is normalized to positive zero, so `str` gives `"0.00"`, never `"-0.00"`.
    - Results never use exponent notation (`Decimal("1E+2")` → `"100.00"`).
    - The helpers take `Decimal` only. The serializer maps `None` itself.

### References checked
- Python `decimal` docs (https://docs.python.org/3/library/decimal.html):
  - `localcontext()` accepts context attributes as keyword arguments since 3.11, e.g.
    `localcontext(prec=42)`. Minimum supported Python here is 3.13.
  - `quantize(exp, rounding=...)` signals `InvalidOperation` if the coefficient would exceed the
    precision, which is why the helpers raise the precision too.
  - `ROUND_HALF_UP` = "round to nearest with ties going away from zero".
  - Signed zeros keep their sign after quantize, e.g. `Decimal("-0.004")` → `Decimal("-0.00")`. Hence the
    explicit normalization above.
- No Home Assistant or recorder API is touched (the engine stays pure), so SPEC §6 is not affected.
- Calendar and DST facts used below were already verified in task 005:
  - 2026-01-01 is a Thursday, 2026-03-01 is a Sunday, and 2026-10-25 is a Sunday.
  - In Berlin, 2026-03-29 has 23 h and 2026-10-25 has 25 h.
  - March 2026 has 743 h, October 2026 has 745 h, the week of Mon 2026-03-23 has 167 h and the week of
    Mon 2026-10-19 has 169 h.

  The implementer re-confirms the new local start/end values with `zoneinfo` while writing the tests.

### Environment for the implementer
The implementer runs natively on Linux **without Home Assistant** (`uv sync`, no `ha` group).
- Unit tests, coverage and ruff run locally.
- **Pyright is verified by CI.** The full `uv run --group ha pyright` needs HA. The scoped
  `uv run pyright custom_components/energy_cost_stats/engine tests/unit` worked natively in task 005 and is
  recommended as a local check. It is not a gate here.

## Files
- create: `custom_components/energy_cost_stats/engine/report.py` — contents:
  - `HourKind`, `HourValue`, `PreparedSeries`;
  - `prepare_measured`, `assemble_report`, `build_report`.

  Stdlib plus relative imports only. Docstrings point to this task file for the rules above.
- create: `custom_components/energy_cost_stats/engine/rounding.py` — quanta constants and `round_money` /
  `round_kwh` / `round_price`.
- create: `tests/unit/test_report.py` — report tests below.
- create: `tests/unit/test_rounding.py` — rounding tests below.
- modify: `tests/unit/test_models.py` — two cheap 005 review follow-ups (round-1 suggestion 2), listed below.
- modify: `docs/SPEC.md` §4 — document:
  - the row and cell semantics (decisions 8–11, including `None` vs `0` and `cost = None` for unpriced-only
    rows);
  - the zone-union ordering;
  - totals as exact sums;
  - rounding at output only (money 2 decimals, kWh 3, price 4, `ROUND_HALF_UP`);
  - that a displayed total may differ from the sum of the displayed cells by 0.01.

  Also replace §3's "rounding to 2 decimals happens only at report output" with a pointer to §4.
- modify: `tasks/006-pricing-and-grouping.md` — status, implementation notes, follow-ups.

Do **not** modify `engine/models.py`, `engine/classify.py`, `engine/tariff.py` or `engine/timeutil.py`. If a
change there turns out to be unavoidable, stop and record why in the implementation notes.

## Tests to write first
Common fixtures (generic only):
- Time zones: `MSK = ZoneInfo("Europe/Moscow")`, `BER = ZoneInfo("Europe/Berlin")`.
- Device ids: `"sensor.plug_01"`, `"sensor.plug_02"`, `"sensor.plug_03"`.
- Default plan: `ru_two_zone(valid_from=date(2026, 1, 1), day_price=Decimal("10.30"), night_price=Decimal("4.43"))`.
- Window bounds come from `local_day_start`.
- Unless stated otherwise:
  - "1 kWh/h" means `Decimal("1")` for every window hour;
  - "MSK day" means local 2026-01-15 (24 h);
  - comparisons are `Decimal ==`.

| Level | Test | Asserts |
|---|---|---|
| unit | `tests/unit/test_report.py::test_single_device_two_zone_day_msk` | MSK day, DAY grouping, plug_01 at 1 kWh/h. Expect one bucket: `hours == 24`, `start == 2026-01-15T00:00+03:00`, `end == 2026-01-16T00:00+03:00`. `zones == (ZoneLabel("t1","Day"), ZoneLabel("t2","Night"))`. Row cells: `t1` kWh 16, cost 164.80, price 10.30; `t2` kWh 8, cost 35.44, price 4.43. Row `kwh == 24`, `cost == Decimal("200.24")`, `unpriced_kwh == 0`, `coverage == Coverage(24,24,0,0,0)`, status `COMPLETE`. `totals` equals that bucket. `unpriced_hours == 0`, `issues == ()`. |
| unit | `tests/unit/test_report.py::test_total_row_sums_devices_in_input_order` | MSK day. Devices passed as plug_02 (0.5 kWh/h) then plug_01 (1 kWh/h). `rows[0].device_id == "sensor.plug_02"`. plug_02: `t1` 8 kWh / 82.40, `t2` 4 kWh / 17.72, total 12 kWh / 100.12. Total row: `device_id is None`, `t1` 24 kWh / 247.20, `t2` 12 kWh / 53.16, `kwh == 36`, `cost == Decimal("300.36")`, `coverage == Coverage(48,48,0,0,0)`. |
| unit | `tests/unit/test_report.py::test_missing_hours_are_not_zero` | MSK day; plug_01 has no keys for local 00:00–03:00 (4 night hours) and 1 kWh in the other hours. `coverage == Coverage(24,20,0,0,4)`, status `PARTIAL`, `kwh == 20`, `t2` kWh 4 / cost 17.72. |
| unit | `tests/unit/test_report.py::test_device_without_data_is_none_not_zero` | MSK day. plug_01 has an empty mapping and plug_02 has `Decimal("0")` every hour. plug_01: `kwh is None`, `cost is None`, every cell `kwh is None and cost is None`, prices still 10.30 / 4.43, `coverage == Coverage(24,0,0,0,24)`, status `MISSING`. plug_02: `kwh == 0`, `cost == 0`, status `COMPLETE`. Total row: `kwh == 0`, `coverage == Coverage(48,24,0,0,24)`, status `PARTIAL`. |
| unit | `tests/unit/test_report.py::test_zone_without_counted_hours_is_none` | MSK day; plug_01 has data only in the 16 day hours. `t2` cell: `kwh is None`, `cost is None`, `price == Decimal("4.43")`. Row `cost == Decimal("164.80")`, status `PARTIAL`. |
| unit | `tests/unit/test_report.py::test_unpriced_hours_before_first_plan` | MSK, window local 2025-12-31 to 2026-01-02 (48 h), DAY grouping, 1 kWh/h. `unpriced_hours == 24`. Dec 31 bucket row: `kwh == 24`, `unpriced_kwh == 24`, `cost is None`, cells `kwh is None` and `price is None`, `coverage == Coverage(24,24,0,0,0)`. `totals.total`: `kwh == 48`, `unpriced_kwh == 24`, `cost == Decimal("200.24")`. `plans` holds only the two-zone plan. |
| unit | `tests/unit/test_report.py::test_window_entirely_before_first_plan` | MSK, local 2025-12-31 only. `zones == ()`, `plans == ()`, `unpriced_hours == 24`. Every row has `zones == ()`, `cost is None`, `unpriced_kwh == kwh == 24`. |
| unit | `tests/unit/test_report.py::test_single_rate_then_two_zone_union` | Schedule: `single_rate(valid_from=2026-01-01, price=Decimal("7.00"))`, then the default two-zone plan from 2026-07-01. MSK, local Jun 30 to Jul 2 (48 h), DAY grouping, 1 kWh/h. `[z.key for z in zones] == ["t0","t1","t2"]`; `plans` = both, in order. Jun 30: `t0` 24 kWh / 168.00 / price 7.00; `t1`/`t2` `kwh is None`, `price is None`. Jul 1: `t0` `kwh is None`, `price is None`; `t1` 16 / 164.80 / 10.30; `t2` 8 / 35.44 / 4.43. Totals: `kwh == 48`, `cost == Decimal("368.24")`, each zone's price single. |
| unit | `tests/unit/test_report.py::test_zone_union_order_and_window_scope` | Plans: `t0` (2026-01-01), then three-zone (2026-02-01, declared `t1,t2,t3`), then two-zone (2026-03-01). A window spanning Jan 31 to Mar 2 gives keys `("t0","t1","t2","t3")` and all 3 plans. A window inside February gives `("t1","t2","t3")` and only the three-zone plan. |
| unit | `tests/unit/test_report.py::test_price_none_on_mid_bucket_price_change` | Plan A = default (from 2026-01-01). Plan B = two-zone 11.00 / 4.80 from Thu 2026-01-15. MSK, WEEK grouping, window Mon 2026-01-12 to Mon 2026-01-19 (168 h), 1 kWh/h. One bucket: `t1` `price is None`, `kwh == 112`, `cost == Decimal("1198.40")` (3·16·10.30 + 4·16·11.00), `effective_price == Decimal("10.7")`. `t2` `price is None`, `kwh == 56`, `cost == Decimal("259.92")`. DAY grouping on the same window: every day has single prices (Jan 14 → 10.30, Jan 15 → 11.00). |
| unit | `tests/unit/test_report.py::test_same_price_switch_keeps_price_and_latest_name` | Plan B from 2026-01-15 has the same prices as A, but `t1` is renamed `"Peak day"`. WEEK bucket as above: `t1.price == Decimal("10.30")`, `t2.price == Decimal("4.43")`. The `t1` label name is `"Peak day"`. |
| unit | `tests/unit/test_report.py::test_hour_grouping` | MSK, window 2026-01-15T03:00Z–06:00Z, HOUR grouping. 3 buckets, each `hours == 1`. `buckets[0].start == 2026-01-15T06:00+03:00`. `buckets[0]` has the `t2` cell priced, with `t1` `kwh is None` and `price is None`. `buckets[1]` (local 07:00) has `t1` priced. |
| unit | `tests/unit/test_report.py::test_dst_buckets_spring_berlin` | BER, window local March 2026 (`local_day_start(2026-03-01)` to `local_day_start(2026-04-01)`), 1 kWh/h. MONTH: one bucket, `hours == 743`, `total.kwh == 743`. DAY: 31 buckets. The Mar 29 bucket has `hours == 23`, `start == 2026-03-29T00:00+01:00`, `end == 2026-03-30T00:00+02:00`, `t1` 16, `t2` 7. WEEK: `[b.hours for b in buckets] == [24,168,168,168,167,48]`, i.e. clipped Sun Mar 1, then Mar 2/9/16, Mar 23 (DST) and the clipped Mar 30–31. This covers 005 review follow-up 1. |
| unit | `tests/unit/test_report.py::test_dst_buckets_fall_berlin` | BER, window local October 2026, 1 kWh/h. MONTH `hours == 745`. The Oct 25 DAY bucket has `hours == 25`, `start == 2026-10-25T00:00+02:00`, `end == 2026-10-26T00:00+01:00`, `t1` 16, `t2` 9. The WEEK bucket starting Mon 2026-10-19 has `hours == 169`. |
| unit | `tests/unit/test_report.py::test_total_grouping_single_bucket` | TOTAL grouping, any 48-h window: `buckets == (report.totals,)`. |
| unit | `tests/unit/test_report.py::test_grouping_accepts_string` | `ReportRequest(..., grouping="day")` gives the same buckets as `Grouping.DAY`. |
| unit | `tests/unit/test_report.py::test_bucket_invariants_across_groupings` | Parametrized over all 5 groupings. BER, window local 2026-03-20 to 2026-05-04 (crosses DST and two month ends). plug_01 and plug_02 use deterministic non-trivial values (e.g. `Decimal(i % 7) / 10`), with a few deleted hours, under a two-plan schedule that switches on 2026-04-01. Assert: buckets are contiguous, first start == `request.start` and last end == `request.end` (as instants); `sum(b.hours) == totals.hours`. Sums of bucket `total.kwh`, `total.cost`, `total.unpriced_kwh`, per-zone cell kWh/cost (skipping `None`) and coverages all equal the `totals` values exactly. Every row's `len(zones) == len(report.zones)`, with keys in `report.zones` order. |
| unit | `tests/unit/test_report.py::test_lookback_keys_ignored` | Adding keys 48 h before `start` and at/after `end` (huge values) changes nothing: the report equals the one built without them. |
| unit | `tests/unit/test_report.py::test_exact_sums_independent_of_caller_context` | Deltas such as `Decimal("0.1234567890123456789")` over 24 h. `totals.total.kwh` equals the sum computed by hand under `localcontext(prec=60)`. Calling `build_report` inside `localcontext(prec=5)` gives an equal `Report`. |
| unit | `tests/unit/test_report.py::test_totals_are_exact_not_sums_of_rounded_cells` | Three devices, each with 0.0005 kWh in one local day hour (price 10.30). Each row `cost == Decimal("0.005150")` (exact), and the total `cost == Decimal("0.015450")`. `round_money(total.cost) == Decimal("0.02")`, while `sum(round_money(r.cost))` over rows `== Decimal("0.03")`. This documents the accepted 0.01 display difference. |
| unit | `tests/unit/test_report.py::test_empty_devices` | `devices=()`: every bucket has `rows == ()`. Total row: `kwh is None`, `cost is None`, `coverage == Coverage.empty()`. Cells have `kwh is None`, with prices filled. |
| unit | `tests/unit/test_report.py::test_duplicate_device_id_rejected` | Two `DeviceSeries` with id `"sensor.plug_01"` → `ValueError` (from `build_report` and `assemble_report`). |
| unit | `tests/unit/test_report.py::test_prepare_measured` | Window keys become `HourValue(kwh, MEASURED)`; absent window hours become `None`; out-of-window keys are dropped; `len(values) == len(hours)`. |
| unit | `tests/unit/test_report.py::test_assemble_estimated_and_excluded` | Hand-built `PreparedSeries` over the MSK day with 1 kWh MEASURED in 20 hours, plus 2 ESTIMATED day hours at 1.5 kWh and 2 EXCLUDED night hours at 50 kWh. Row: `kwh == 23`, `estimated_kwh == 3`, `excluded_kwh == 100`; `t1` kWh includes the estimated 3; `t2` excludes the 100. `coverage == Coverage(24,20,2,2,0)`, status `PARTIAL`. A second device with **only** EXCLUDED values: `kwh is None`, cells `None`, `excluded_kwh` summed, status `MISSING`. `issues` passed in come back unchanged on `Report.issues`. |
| unit | `tests/unit/test_report.py::test_assemble_rejects_bad_input` | `len(values) != len(hours)` → `ValueError`; empty `hours` → `ValueError`. |
| unit | `tests/unit/test_rounding.py::test_round_money` | Parametrized `str(round_money(Decimal(x)))`: `"0.005"→"0.01"`, `"0.0049"→"0.00"`, `"-0.005"→"-0.01"`, `"-0.004"→"0.00"` (no minus sign), `"200.24"→"200.24"`, `"1E+2"→"100.00"`, `"164.8"→"164.80"`. |
| unit | `tests/unit/test_rounding.py::test_round_kwh_and_price` | `round_kwh`: `"0.0005"→"0.001"`, `"12"→"12.000"`, `"-0.0004"→"0.000"`. `round_price`: `"10.30"→"10.3000"`, `"10.7"→"10.7000"`, `"4.43005"→"4.4301"`. |
| unit | `tests/unit/test_rounding.py::test_rounding_rejects_bad_input` | For each helper: `Decimal("NaN")`, `Decimal("Infinity")`, `1.0`, `1`, `True` → `ValueError`. |
| unit | `tests/unit/test_rounding.py::test_rounding_large_values_independent_of_context` | `round_money(Decimal("12345678901234567890123456789.005"))` inside `localcontext(prec=5)` → `"12345678901234567890123456789.01"`, with no `InvalidOperation`. |
| unit | `tests/unit/test_models.py::test_coverage_status` (extend) | Add case `(24,20,0,4,0) → PARTIAL` (excluded only), from 005 review round-1 suggestion 2. |
| unit | `tests/unit/test_models.py::test_coverage_invariant_and_add` (extend) | Add `Coverage(True, 1, 0, 0, 0)` → `ValueError` (bool guard), from 005 review round-1 suggestion 2. |

Expected values above were computed by hand. If `zoneinfo` disagrees on a DST boundary, trust `zoneinfo`
and record the discrepancy in the implementation notes. Money and kWh values must not be adjusted to make a
test pass.

## Acceptance criteria
Native (Linux or Windows, no HA):
- [x] Tests were written first: the commit history (or the implementation notes) shows `test_report.py` and
  `test_rounding.py` failing before `report.py`/`rounding.py` existed. (rounding.py: tests written first
  but not run red, see notes.)
- [x] `uv run pytest -m unit` → all pass (including every earlier unit test).
- [x] `uv run pytest -m unit --cov=custom_components/energy_cost_stats/engine --cov-branch --cov-report=term-missing --cov-fail-under=95`
  → passes; `report.py` and `rounding.py` are each ≥ 95% line+branch.
- [x] `uv run ruff check .` → exit 0; `uv run ruff format --check .` → exit 0.
- [x] `tests/unit/test_engine_isolation.py` passes: the new modules use stdlib and relative imports only,
  and no `homeassistant` import.
- [x] `rg -n "quantize|round\(" custom_components/energy_cost_stats/engine` → matches only in `rounding.py`.
- [x] `rg -n "zone_for_hour|classify_hours" custom_components/energy_cost_stats/engine/report.py` → no
  `zone_for_hour`, and exactly one `classify_hours` call (in `build_report`).
- [x] `git diff --stat origin/master` touches only the files in "Files"; `models.py`, `classify.py`,
  `tariff.py` and `timeutil.py` are unchanged.
- [x] `docs/SPEC.md` §4 documents decisions 8–11, the rounding rule (2/3/4 decimals, `ROUND_HALF_UP`, output
  only) and the accepted 0.01 display difference. §3 points to it.
- [x] Public-repo hygiene: only generic ids (`sensor.plug_NN`), generic prices and the zones
  `Europe/Moscow`/`Europe/Berlin`; no real entity ids, paths or hosts.

CI (pyright needs the HA environment; the implementer cannot run the full check natively):
- [ ] `uv run --group ha pyright` → 0 errors in the `lint`/`test` jobs. The `engine` package is in pyright
  `strict`, so there must be no `Any` leaks and no unnecessary casts. Locally,
  `uv run pyright custom_components/energy_cost_stats/engine tests/unit` is recommended but not a gate.
- [ ] All required checks on the PR are green.

## Out of scope
- Gap spreading, negative/spike exclusion, producing `QualityIssue`s, the quality settings parameter →
  **007-data-quality**. That task replaces `prepare_measured` inside `build_report`; `assemble_report`
  already supports the ESTIMATED and EXCLUDED kinds.
- Serialization to JSON, string formatting, and applying the rounding helpers to a payload → stage 3
  (websocket/service).
- Main meter / "untracked" row, nested-meter de-duplication (SPEC §5, out of stage 1).
- Volume bands / blended monthly prices (SPEC §3, reserved).
- Caching `TariffSchedule.plan_for` inside `classify_hours` (005 follow-up 4). Not needed: classification
  runs once per report.
- 005 follow-ups 5 (`match=` on `pytest.raises`) and 7 (`DeviceSeries` docstring). They do not belong to
  this task.
- Changing `ReportRequest.grouping`'s annotation (see decision 4).

## Open questions
None blocking. These product-visible choices were made here and should be confirmed in review:
- A cell for a zone **not in force** in the bucket is `kwh = cost = price = None`, the same shape as "zone
  in force but no data" except that `price` is set there. If the card must tell "n/a" apart from "missing",
  stage 3 can derive it from `Report.plans` and the bucket range. No engine change is needed.
- A row with only unpriced data gets `cost = None` ("unknown"), not `0`.
- Price display precision is 4 decimals (`round_price`).

<!-- Filled in by implementer -->
## Implementation notes
- `rounding.py` was written before its tests were run (the tests file was written first but I implemented the
  small module before the first red run). `test_report.py` was run red (`ModuleNotFoundError: engine.report`)
  before `report.py` existed. Everything is green afterwards.
- `report.py` imports `classify` as a module (`from . import classify as _classify`) so the acceptance grep
  for `classify_hours` finds exactly one line, the call in `build_report`.
- Aggregation is one pass; each hour updates its bucket slot and a whole-window slot, so `totals` is built
  independently of the other buckets. Cost is computed per hour (`kwh * price`) inside `localcontext(prec=50)`.
- Own bucket-invariant test sums under `localcontext(prec=50)`: with inexact test values (`/7`) the default
  28-digit context made the test's own sum inexact, not the engine.
- Native checks: `uv run pytest -m unit` 227 passed; engine coverage 100% (line+branch); ruff check and
  format clean. Pyright not run locally (CI). `git diff --stat origin/master` was not run by the
  implementer (the reviewer verified it; `origin/master` is a local ref);
  `models.py`, `classify.py`, `tariff.py`, `timeutil.py` untouched.
- `test_models.py`: added the two 005 follow-up cases. SPEC §3 now points to §4; §4 documents the semantics.
- Extra test `test_report_is_report_type` is a small smoke check, not in the task table.

## Follow-ups
- Task 007: replace `prepare_measured` in `build_report` with the quality pre-pass (keyword-only settings).
- Pyright strict on `report.py`/`test_report.py` is unverified locally; check in CI.
