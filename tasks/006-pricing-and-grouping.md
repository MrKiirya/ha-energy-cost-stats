# 006 — Pricing and grouping: compute_report, totals, rounding at output

Status: planned
Roadmap: SPEC §8 stage 1 (engine + unit tests), task 3 of 4 (after 005-time-and-zones)
Spec sections: SPEC §3, §4 (report output), §5 (missing data, UTC vs local); CLAUDE.md principles 2–4, 6

> **Human decisions (see "Open questions" at the end) override anything in this file that conflicts with them** —
> e.g. single-rate key `t0`, missing data as `None`, money/kWh serialized as strings, 7-day gap cap.
> Update the affected tests/criteria accordingly.

## Goal
The engine produces the actual report. `compute_report(request, schedule, series)` takes hourly deltas for
any number of devices and returns a `Report` (types from task 005). The report has, per bucket
(hour/day/week/month/total) and per device, kWh, cost and price for each zone, row totals, a total row
across devices, and data coverage. Pricing is retroactive: the result depends only on the inputs, so
changing a plan and recomputing re-prices every past hour. All arithmetic is exact `Decimal`. A separate
serializer turns the report into a JSON-ready dict and rounds money to 2 decimals only there. This is the
structure stage 3 sends over the websocket and returns from the service.

## Context

### Decisions (human-confirmed, stage 1)
- Money and energy are `Decimal` throughout. Rounding to 2 decimals happens **only at output**.
- Groupings: hour/day/week/month/custom range, plus totals. Weeks start on Monday; months are local
  calendar months (bucket rules from task 005).
- Missing data is explicit (`missing`/`partial`), never a silent zero.
- Volume tiers are not computed: always use `Zone.price` (first band).

### Algorithm (normative)
1. `hours = classify_hours(schedule, request.start, request.end, request.time_zone)`, computed once and
   shared by all devices.
2. Group the hour indices by `bucket_key(info, request.grouping)`, keeping chronological order. Bucket
   `start` = `first.utc_start.astimezone(tz)`; `end` = `(last.utc_start + 1h).astimezone(tz)`;
   `hours` = the count.
3. For each device and each hour in the window: look up `series.deltas.get(info.utc_start)`.
   - If there is no value, the hour is **missing** (`coverage.missing += 1`) and contributes 0 kWh.
   - If there is a value and `info.zone` is set, add `kwh` to that zone's cell and `kwh * zone.price` to its
     cost (exact `Decimal`, default context, never quantized here).
   - If there is a value and `info.zone is None` (before the first plan), add it to `unpriced_kwh`; no
     cost.
   - Every present value is `measured` in this task. Task 007 adds `estimated`/`excluded`. Negative or huge
     values are taken as-is here; task 007 filters them.
   - Keys outside the window are ignored.
4. `ZoneCell.price` = the single distinct price of that zone key over the bucket's hours (the same for
   every row in the bucket); `None` if there are several or if the zone was never in force in the bucket.
5. Row `kwh` = sum of the zone kWh + `unpriced_kwh`; row `cost` = sum of the zone costs. Total row
   (`device_id=None`) = sums of the device rows, field by field, including `Coverage.__add__`.
6. `Report.zones` = the union of zone keys of all plans in force in the window, sorted by key; each label's
   `name` comes from the **latest** plan in the window that has that key (names are display-only).
   `Report.plans` = the plans in force in the window, in order. `Report.unpriced_hours` = the number of
   window hours with `zone is None`.
7. `Report.totals` = one bucket over the whole window, computed with the same code path as a TOTAL bucket.
   For every grouping, the sums of the buckets' exact values equal the totals' values.
8. Validation: duplicate `device_id` in `series` → `ValueError`. An empty `series` is valid: rows are
   empty and the total row has `Coverage.empty()` → status `missing`.

Implementation hint (not a requirement): prepare per-device samples through a small internal function
(e.g. `_samples(series, hours) -> dict[datetime, Sample]` with `Sample(kwh, estimated=False)`), so that
task 007 can swap in quality processing without changing the aggregation code.

### Output helpers
- `engine/money.py`: `quantize_money(x: Decimal) -> Decimal` (2 dp) and `quantize_kwh(x: Decimal) -> Decimal`
  (3 dp), both `ROUND_HALF_UP` (see open questions). Use `Decimal.quantize` with an explicit rounding
  argument; never change the global decimal context.
- `engine/serialize.py`: `report_to_dict(report: Report) -> dict[str, object]`. The result must pass
  `json.dumps()` with no custom encoder. We checked Home Assistant's JSON encoder
  (https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/json.py, `json_encoder_default`):
  it handles `set`/`tuple`/`float`/datetime/`as_dict` objects but **not `Decimal`**, so Decimals must be
  converted here. Rules:
  - money (`cost`) → `float(quantize_money(x))`; kWh (`kwh`, `unpriced_kwh`, `estimated_kwh`,
    `excluded_kwh`) → `float(quantize_kwh(x))`; `price` → `float(x)` unrounded, or `None`. Floats are
    created only here, after quantizing.
  - Every rounded figure is rounded from its own exact value (row and total costs are **not** sums of
    already rounded cells). So displayed parts may differ from the displayed total by ±0.01. Document this
    in the module docstring.
  - datetimes → `isoformat()` in the report time zone (offset included); dates → ISO strings; enums → their
    string value; time zone → `getattr(tz, "key", None) or str(tz)`.
  - Shape:
    ```
    {"start", "end", "time_zone", "grouping",
     "zones": [{"key", "name"}], "plans": [{"valid_from", "name"}], "unpriced_hours",
     "buckets": [BUCKET], "totals": BUCKET, "issues": [{"kind", "device_id", "start", "end", "kwh"}]}
    BUCKET = {"start", "end", "hours", "rows": [ROW], "total": ROW}
    ROW = {"device_id", "kwh", "cost", "unpriced_kwh", "estimated_kwh", "excluded_kwh", "status",
           "coverage": {"expected", "measured", "estimated", "excluded", "missing"},
           "zones": {<key>: {"kwh", "cost", "price"}}}
    ```

### Reference numbers used in tests (MSK = `Europe/Moscow`, 1 kWh every hour unless stated)
- Two-zone B (valid from 2026-07-01): day `10.30`, night `4.43`. One day: `t1` 16 kWh → `164.80`,
  `t2` 8 kWh → `35.44`, total `200.24`.
- Two-zone A (valid from 2026-01-01): day `9.00`, night `4.00`. One day: `144.00 + 32.00 = 176.00`.
- Window 2026-06-30 → 2026-07-02 local, TOTAL: `t1` 32 kWh, cost `308.80`, price `None`; `t2` 16 kWh,
  cost `67.44`, price `None`; total `376.24`.
- Three-zone (peak `12.00`, semi-peak `9.00`, night `4.00`): one day = 7 × 12 + 9 × 9 + 8 × 4 = `197.00`.
- Single-rate `6.00` until 2026-06-30, plan B from 2026-07-01, window Jun 30 → Jul 2, TOTAL:
  `t1` 40 kWh, cost `144.00 + 164.80 = 308.80`; `t2` 8 kWh, `35.44`; zone labels `t1` "Day", `t2` "Night".

## Files
- create: `custom_components/energy_cost_stats/engine/report.py` — `compute_report`.
- create: `custom_components/energy_cost_stats/engine/money.py` — quantize helpers.
- create: `custom_components/energy_cost_stats/engine/serialize.py` — `report_to_dict`.
- modify (only if needed): `custom_components/energy_cost_stats/engine/models.py` — small additions found
  necessary; no renames or removals of task 005 fields.
- create: `tests/unit/test_report_pricing.py`
- create: `tests/unit/test_report_grouping.py`
- create: `tests/unit/test_money.py`
- create: `tests/unit/test_serialize.py` (+ its syrupy `__snapshots__/` file)

## Tests to write first
Device ids in tests are generic (`plug_01`, `plug_02`). A shared helper builds a `DeviceSeries` with a
constant value for every UTC hour in a range.

| Level | Test | Asserts |
|---|---|---|
| unit | `tests/unit/test_report_pricing.py::test_single_day_two_zone` | MSK, plan B, 2026-07-15 local day, DAY grouping: 1 bucket; `t1` kWh 16, cost `Decimal("164.80")`, price `10.30`; `t2` 8, `35.44`, `4.43`; row kwh 24, cost `200.24`; status `complete`; coverage `(24,24,0,0,0)`. |
| unit | `tests/unit/test_report_pricing.py::test_three_zone_day` | Three-zone reference day → peak 7 kWh `84.00`, semi-peak 9 `81.00`, night 8 `32.00`, total `197.00`. |
| unit | `tests/unit/test_report_pricing.py::test_plan_switch_mid_period` | Plans A + B, window 2026-06-30 → 2026-07-02: DAY buckets cost `176.00` and `200.24`; TOTAL grouping gives the reference numbers (prices `None`, `308.80`, `67.44`, `376.24`); `report.plans == (A, B)`. |
| unit | `tests/unit/test_report_pricing.py::test_single_rate_then_two_zone` | Reference numbers above; `report.zones == (ZoneLabel("t1","Day"), ZoneLabel("t2","Night"))`; in the Jun 30 DAY bucket `t2` has kwh 0 and price `None`. |
| unit | `tests/unit/test_report_pricing.py::test_retroactive_repricing` | Same series, twice: once with A day `9.00`, once with A replaced (`dataclasses.replace`) by day `9.50`. The Jun 30 day cost changes from `176.00` to `184.00`; the Jul 1 cost is unchanged. |
| unit | `tests/unit/test_report_pricing.py::test_hours_before_first_plan_unpriced` | Window 2025-12-31 → 2026-01-02 (MSK), first plan from 2026-01-01: `report.unpriced_hours == 24`; the Dec 31 bucket has `unpriced_kwh == 24`, `kwh == 24`, `cost == 0`, all zone cells 0 with price `None`; the Jan 1 bucket is priced normally. |
| unit | `tests/unit/test_report_pricing.py::test_decimal_exactness` | 3 hours of `Decimal("0.1")` in the day zone at `10.30` → cost `== Decimal("3.09")`; every `kwh`/`cost` in the report is a `Decimal` (walk the dataclasses). |
| unit | `tests/unit/test_report_pricing.py::test_two_devices_and_total_row` | `plug_01` 1 kWh/h, `plug_02` 0.5 kWh/h for one day: rows keep input order; total row kwh 36, cost `300.36`, coverage `(48,48,0,0,0)`. |
| unit | `tests/unit/test_report_pricing.py::test_duplicate_device_ids_rejected` | Two series with id `plug_01` → `ValueError`. |
| unit | `tests/unit/test_report_pricing.py::test_empty_inputs` | (a) `series=[]` → every bucket's `rows == ()`, total kwh 0, status `missing`. (b) one device with no deltas → kwh 0, cost 0, coverage `(24,0,0,0,24)`, status `missing`. |
| unit | `tests/unit/test_report_pricing.py::test_partial_day` | Data for 20 of 24 hours (4 night hours missing) → coverage `(24,20,0,0,4)`, status `partial`, `t2` kwh 4. |
| unit | `tests/unit/test_report_pricing.py::test_hours_outside_window_ignored` | Values 1 h before start and at `end` do not change any figure. |
| unit | `tests/unit/test_report_grouping.py::test_hour_grouping` | One MSK day, HOUR → 24 buckets; bucket 0 starts at local `00:00+03:00`, each `hours == 1`. |
| unit | `tests/unit/test_report_grouping.py::test_zone_crossing_midnight_day_buckets` | `plug_01`: 2.0 at `2026-07-15T20:00Z` (local 23:00 Jul 15), 3.0 at `21:00Z` (local 00:00 Jul 16), nothing else. DAY grouping over Jul 15–16: Jul 15 bucket `t2` kwh 2 (`8.86`); Jul 16 bucket `t2` kwh 3 (`13.29`). |
| unit | `tests/unit/test_report_grouping.py::test_week_grouping_monday_clipped` | MSK window Sat 2026-01-10 → Tue 2026-01-20: 3 buckets with `hours` 48, 168, 24 and local starts Jan 10, Jan 12, Jan 19 (00:00). |
| unit | `tests/unit/test_report_grouping.py::test_month_grouping` | MSK window 2026-01-15 → 2026-03-01: 2 buckets, 408 and 672 hours. |
| unit | `tests/unit/test_report_grouping.py::test_dst_day_buckets_berlin` | Berlin, 1 kWh/h, windows 2026-03-28 → 03-31 and 2026-10-24 → 10-27: DAY bucket kWh 24/23/24 and 24/25/24. |
| unit | `tests/unit/test_report_grouping.py::test_dst_hour_buckets_fall_back` | Berlin 2026-10-25, HOUR: 25 buckets; exactly two starts have wall-clock 02:00, with different `utcoffset()`. |
| unit | `tests/unit/test_report_grouping.py::test_dst_month_berlin` | Berlin March 2026, MONTH, 1 kWh/h → kwh 743. |
| unit | `tests/unit/test_report_grouping.py::test_custom_range_total` | MSK local 2026-07-15 10:00 → 14:00, TOTAL: one bucket, 4 hours, all `t1`, cost `41.20`. |
| unit | `tests/unit/test_report_grouping.py::test_totals_equal_sum_of_buckets` | Parametrized over all 5 groupings, a mixed two-device series over 2026-06-28 → 2026-07-06 with the A/B plan switch: the totals' `kwh`, `cost` and each zone's kwh/cost equal the exact sums over buckets; the `TOTAL` grouping's single bucket equals `report.totals`. |
| unit | `tests/unit/test_money.py::test_quantize_half_up` | Parametrized: `0.005→0.01`, `0.015→0.02`, `2.675→2.68`, `-0.005→-0.01`, `200.24→200.24`; `quantize_kwh(Decimal("1.0005")) == Decimal("1.001")`. |
| unit | `tests/unit/test_serialize.py::test_json_serializable` | `json.dumps(report_to_dict(report))` works without `default=`; the top-level keys are exactly the shape above. |
| unit | `tests/unit/test_serialize.py::test_rounding_from_exact_values` | Two devices each costing exactly `1.004` → each row cost `1.0`; the total cost `2.01` (rounded from `2.008`, not `1.00 + 1.00`). |
| unit | `tests/unit/test_serialize.py::test_datetimes_and_enums` | Bucket `start` is `"2026-07-15T00:00:00+03:00"`; `status == "complete"`; `grouping == "day"`; `time_zone == "Europe/Moscow"`; a `None` price becomes JSON `null`. |
| unit | `tests/unit/test_serialize.py::test_snapshot` | syrupy snapshot of `report_to_dict` for the one-day two-zone report (fixes the wire format for stage 3/4). |

## Acceptance criteria
Windows native:
- [ ] `uv run pytest -m unit` → all pass.
- [ ] `uv run pytest -m unit --cov=custom_components/energy_cost_stats/engine --cov-branch --cov-report=term-missing --cov-fail-under=95` → passes.
- [ ] `uv run ruff check .`, `uv run ruff format --check .` → exit 0.
- [ ] `uv run pyright custom_components/energy_cost_stats/engine tests/unit` → 0 errors.

General:
- [ ] `rg -n "float\(" custom_components/energy_cost_stats/engine` → matches only in `serialize.py` (and the
  `from_floats` constructor from task 005).
- [ ] `rg -n "getcontext|setcontext|localcontext" custom_components/energy_cost_stats/engine` → no matches.
- [ ] `rg -n "quantize" custom_components/energy_cost_stats/engine` → matches only in `money.py`.
- [ ] `compute_report` does no I/O and keeps no module-level state: the reviewer checks for module-level
  mutable variables and caches in `report.py`.
- [ ] No files touched outside the "Files" list.

## Out of scope
- Gap spreading, negative/spike exclusion, filling `QualityIssue`s → **007-data-quality**. In this task,
  negative and huge deltas pass through unchanged. Do not write tests that pin this, because task 007
  changes it.
- Volume-tier pricing; main meter / "untracked" row; nested-meter de-duplication.
- Websocket command, service schema, card rendering (stages 3–4) — only the dict shape is fixed here.
- Performance tuning. The design already classifies each hour once; a benchmark is not required.
- Localized number formatting (the card's job).

## Open questions
None — resolved by the human (2026-09-25):
- **Rounding:** `ROUND_HALF_UP` (as on bills), applied only at output.
- **Wire format for money: JSON strings** (`"200.24"`, exact — like C# `decimal`), not floats.
- **kWh at output: 3 decimals** (also serialized as strings for consistency; note it in the serializer docs).

<!-- Filled in by implementer -->
## Implementation notes
## Follow-ups
