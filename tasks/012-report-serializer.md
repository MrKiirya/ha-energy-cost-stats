# 012 — Report JSON serializer (card contract) and reports without a tariff plan

Status: in-review
Roadmap: SPEC §8 stage 3 (websocket `report` + service + integration tests), task 2 of 3 (011-recorder-adapter,
**012-report-serializer**, 013-report-websocket-and-service). Pure engine work: it does not depend on 011 and can run
in parallel with it. Branch from the 010 stack, or from `master` once 006/007/010 are merged (it uses
`engine/plan_codec.py` from 010).
Spec sections: SPEC §4 (report output, rounding), §3 (plan JSON), §2 (no plan → unpriced); tasks/006 decisions on
`None` vs `0`; tasks/010 D-6 ("stage 3 reports all hours as unpriced" when no plan exists); CLAUDE.md principles 3, 4, 6

> Planner decisions are marked **(D-n)** and also appear under "Open questions" as "decided by planner, confirm in
> PR review". The human was away when this was planned.

## Goal
1. A pure engine module `engine/serialize.py` turns a `Report` into a JSON-ready `dict`. This is the **only** place
   where exact `Decimal`s get rounded (via `engine/rounding.py`). The websocket command and the service (task 013)
   return this dict unchanged, and the stage 4 card consumes it. The shape is versioned and documented in SPEC §4.
2. `build_report` and `classify_hours` accept `schedule=None`, meaning no tariff plan exists yet. Every hour is then
   unpriced. Task 010 lets the user delete the last plan (`RuntimeData.schedule is None`), and 010 D-6 promised that
   stage 3 reports such hours as unpriced ("unknown", not "free") instead of failing.

## Context
- Engine types (`engine/models.py`): `Report(request, zones, plans, buckets, totals, unpriced_hours, issues)`,
  `Bucket(start, end, hours, rows, total)`, `Row(device_id | None, zones, kwh, cost, unpriced_kwh, estimated_kwh,
  excluded_kwh, coverage)` with `status`, `ZoneCell(key, kwh, cost, price)`, `Coverage(expected, measured, estimated,
  excluded, missing)`, `QualityIssue(kind, device_id, start, end, kwh)`. Bucket/issue datetimes are already in the
  report time zone. `ReportRequest.start/end` are UTC.
- Rounding (`engine/rounding.py`): `round_money` (2), `round_kwh` (3), `round_price` (4), `ROUND_HALF_UP`, never
  `-0`. They take a `Decimal` only. The serializer maps `None` itself (stated in that module's docstring).
- `engine/plan_codec.plan_to_data(plan)` already gives the stored plan JSON (prices as strings, user scale kept,
  `"24:00"`), so the report reuses it for `plans`.
- `classify_hours(schedule, ...)` calls `schedule.plan_for(...)`. `TariffSchedule` cannot be empty (it raises), so
  today the integration cannot build a report with no plans.

### Design decisions
- **D-1 Numbers are decimal strings.** Every kWh, money and price value is a string in plain notation after rounding:
  `format(round_x(v), "f")`, for example `"240.00"`, `"29.000"`, `"10.3000"`. A missing value is JSON `null`. Hour
  counts are JSON integers. Reasons: it is exact, the scale is fixed (the card shows `"240.00"`, not `240`), and it
  matches the project rule that decimals are strings (SPEC §2 settings, §3 prices). The cost is that automations
  must apply `| float` in templates, which is noted in the service description (013). No `float` is ever produced.
- **D-2 Contract** (`schema_version: 1`; field order as listed; all keys always present):
  ```json
  {
    "schema_version": 1,
    "time_zone": "Europe/Moscow",
    "currency": "EUR",
    "start": "2026-01-15T00:00:00+03:00",
    "end": "2026-01-16T00:00:00+03:00",
    "grouping": "day",
    "zones": [ { "key": "t1", "name": "Day" }, { "key": "t2", "name": "Night" } ],
    "plans": [ { "valid_from": "2026-01-01", "name": "Two-zone", "zones": [ "...plan_to_data(...)" ] } ],
    "devices": [ { "entity_id": "sensor.plug_01", "name": "Plug 01", "statistics": "ok" } ],
    "buckets": [ "<bucket>" ],
    "totals": "<bucket>",
    "unpriced_hours": 0,
    "issues": [ { "kind": "estimated", "entity_id": "sensor.plug_01",
                  "start": "2026-01-15T05:00:00+03:00", "end": "2026-01-15T10:00:00+03:00",
                  "hours": 5, "kwh": "10.000" } ]
  }
  ```
  `<bucket>` = `{ "start", "end", "hours", "rows": [<row>, ...], "total": <row> }`.
  `<row>` =
  ```json
  { "entity_id": "sensor.plug_01", "kwh": "29.000", "cost": "240.00",
    "unpriced_kwh": "0.000", "estimated_kwh": "10.000", "excluded_kwh": "0.000",
    "status": "estimated",
    "coverage": { "expected": 24, "measured": 19, "estimated": 5, "excluded": 0, "missing": 0 },
    "zones": [ { "key": "t1", "kwh": "19.000", "cost": "195.70", "price": "10.3000" },
               { "key": "t2", "kwh": "10.000", "cost": "44.30", "price": "4.4300" } ] }
  ```
  - `start`/`end` (top level) = `request.start/end` converted to the report time zone, in ISO 8601 with the offset
    (`datetime.isoformat()`). Bucket and issue times are the same, taken as they are.
  - `grouping` = `Grouping` value. `zones` = `Report.zones` in order. Every row's `zones` list is aligned with it,
    one entry per zone, and each entry repeats its `key`.
  - `plans` = `[plan_to_data(p) for p in report.plans]`. These are the stored plan data, **not rounded** (they are
    configuration, not results).
  - `devices` comes from the caller (D-3), in the same order as the rows. The total row has `"entity_id": null`.
  - `status` = `Row.status` value (`complete` / `estimated` / `partial` / `missing`). Issue `kind` = `IssueKind`
    value. Issue `hours` = `(end - start) / 1 h` (exact integer) and `kwh` = `round_kwh`.
  - `currency` comes from the caller (HA's configured currency code, or `null`).
  - With `Grouping.TOTAL`, `buckets` is `[totals]`, as in the engine.
  - Cell `effective_price` is not serialized (the card can derive it). It may be added later in a minor,
    backwards-compatible schema change (new keys only). Removing or renaming a key bumps `schema_version`.
- **D-3 Serializer API** (`engine/serialize.py`, stdlib + relative imports only, strict pyright):
  ```python
  SCHEMA_VERSION = 1


  @dataclass(frozen=True, slots=True)
  class DeviceInfo:
      device_id: str
      name: str
      statistics: str  # adapter status value, e.g. "ok", "no_statistics", "unsupported"


  def report_to_json(
      report: Report,
      *,
      devices: Sequence[DeviceInfo],
      time_zone: str,
      currency: str | None,
  ) -> dict[str, Any]: ...
  ```
  - `ValueError` if `[d.device_id for d in devices]` differs from the device ids of `report.totals.rows` (same order),
    or if `time_zone` is empty.
  - The output contains only `dict`, `list`, `str`, `int` (never `bool` or `float`) and `None`, so `json.dumps`
    works without a custom encoder and the dict is a valid HA `ServiceResponse`.
  - The engine's exact values are never changed. Rounding happens only on the output copy. Totals are rounded from
    their exact sums, not summed from rounded cells (SPEC §4: a displayed total may differ by 0.01).
- **D-4 No tariff plan.** `classify_hours(schedule: TariffSchedule | None, ...)` and `build_report(request, schedule:
  TariffSchedule | None, devices, *, quality=None)`. `None` means every hour has `plan = zone = None`. The positional
  parameters stay the same, only the type widens. The result: `zones == ()`, `plans == ()`, `unpriced_hours ==
  hours`, rows have `kwh` = counted kWh, `cost = None` and `unpriced_kwh == kwh`, and data quality still applies.

### Environment for the implementer
Native, without HA: `uv run pytest -m unit`, the coverage command and ruff. Pyright runs in the devcontainer/CI
(`dx uv run --group ha pyright`).

## Files
- create: `custom_components/energy_cost_stats/engine/serialize.py` — D-1 … D-3. The docstring points to this task
  file and SPEC §4.
- modify: `custom_components/energy_cost_stats/engine/classify.py` — D-4 (`schedule` may be `None`; update the
  docstring).
- modify: `custom_components/energy_cost_stats/engine/report.py` — D-4 (type annotation and docstring only; the
  pipeline is unchanged).
- create: `tests/unit/test_serialize.py` — the serializer tests below.
- modify: `tests/unit/test_classify.py` — **append** `test_classify_without_schedule` (existing tests unchanged).
- modify: `tests/unit/test_report.py` — **append** `test_build_report_without_schedule` (existing tests unchanged).
- modify: `docs/SPEC.md` §4 — add a "JSON contract (schema_version 1)" subsection with D-1/D-2 (the example above,
  the field list, `null` vs `"0.000"`, strings for decimals, ISO times in the report time zone, the versioning rule)
  and one bullet: "No tariff plan → every hour unpriced; `cost` is `null`" (D-4).
- modify: `tasks/012-report-serializer.md` — status, notes.

## Tests to write first
Fixtures as in `test_quality.py` (copy the small helpers, do not import across test modules): `MSK`, `sensor.plug_01`
/ `sensor.plug_02`, `ru_two_zone(valid_from=date(2026, 1, 1), day_price=Decimal("10.30"), night_price=Decimal("4.43"))`,
"MSK day" = local 2026-01-15. `devices` = `DeviceInfo(id, "Plug 01"/"Plug 02", "ok")`. Unless stated otherwise:
`time_zone="Europe/Moscow"`, `currency="EUR"`.

| Level | Test | Asserts |
|---|---|---|
| unit | `tests/unit/test_serialize.py::test_full_document_two_zone_day` | The 007 scenario `test_gap_spread_across_zones` (keys for local 05:00–08:00 missing, catch-up `10` at 09:00, 1 kWh/h elsewhere, look-back key at `start - 1 h`), DAY grouping. `report_to_json(...)` **equals a literal dict** with: `schema_version 1`, `start "2026-01-15T00:00:00+03:00"`, `end "2026-01-16T00:00:00+03:00"`, `grouping "day"`, the zones `t1 Day`, `t2 Night`, `plans == [plan_to_data(plan)]`, one bucket whose plug_01 row is the D-2 `<row>` example exactly (`"29.000"`, `"240.00"`, t1 `"19.000"`/`"195.70"`/`"10.3000"`, t2 `"10.000"`/`"44.30"`/`"4.4300"`, coverage 24/19/5/0/0, status `"estimated"`), the total row the same with `entity_id None`, `totals` equal to the bucket, `unpriced_hours 0`, and one issue `{"kind": "estimated", ..., "hours": 5, "kwh": "10.000"}`. |
| unit | `tests/unit/test_serialize.py::test_json_types_only` | Walk the document from the full test plus a HOUR-grouping one: every leaf is `str`, `int` (not `bool`) or `None`, there is no `float` and no `Decimal`. `json.loads(json.dumps(doc)) == doc`. |
| unit | `tests/unit/test_serialize.py::test_rounding_half_up_at_output_only` | A single-rate plan (`single_rate(valid_from=..., price=Decimal("1"))`) and one hour with kWh `Decimal("0.0005")` → kwh `"0.001"`, cost `"0.00"` (exact cost `0.0005` rounds to 2 decimals). A plan price `Decimal("0.00005")` → cell price `"0.0001"`. kWh `Decimal("0.0015")` → `"0.002"` (half up, not banker's). The `Report` object is unchanged afterwards (values still exact). |
| unit | `tests/unit/test_serialize.py::test_total_rounded_from_exact_sum` | Two devices, each one hour of `Decimal("0.005")` kWh at price `1` → each row cost `"0.01"`, total row cost `"0.01"` (exact `0.010` rounded), not `"0.02"`. |
| unit | `tests/unit/test_serialize.py::test_none_vs_zero` | A device with no keys → row `kwh None`, `cost None`, zone cells `kwh`/`cost` `None` but `price` `"10.3000"`, `unpriced_kwh "0.000"`, status `"missing"`. A device with a measured `0` hour → `"0.000"`/`"0.00"`, not `None`. |
| unit | `tests/unit/test_serialize.py::test_no_negative_zero` | An excluded negative delta `Decimal("-0.0001")` → `excluded_kwh "0.000"`, never `"-0.000"`. The `EXCLUDED_NEGATIVE` issue kwh → `"0.000"`. An excluded `Decimal("-0.05")` → `"-0.050"`. |
| unit | `tests/unit/test_serialize.py::test_plan_switch_price_null` | Plans 2026-01-01 (day `10.30`) and 2026-01-16 (day `11.00`, night unchanged), MONTH grouping over January. The month bucket's `t1.price` is `None` and `t2.price` is `"4.4300"`. The day buckets (DAY grouping) have `"10.3000"` / `"11.0000"`. `plans` lists both via `plan_to_data`. |
| unit | `tests/unit/test_serialize.py::test_groupings_and_total` | HOUR → 24 buckets with ascending `start` strings and `hours == 1`. TOTAL → `buckets == [totals]`. WEEK across a Monday → bucket starts on the local Monday. BER on 2026-10-25 → `hours 25` and the end offset `+01:00`. |
| unit | `tests/unit/test_serialize.py::test_devices_must_match_rows` | `ValueError` for a missing device, an extra device, the wrong order, and `time_zone=""`. `currency=None` → `"currency": None`. |
| unit | `tests/unit/test_serialize.py::test_issue_kinds_and_hours` | One spike and one negative → issues `excluded_spike` / `excluded_negative`, each `hours == 1`. The `kwh` strings are rounded to 3 decimals. The order follows `report.issues`. |
| unit | `tests/unit/test_classify.py::test_classify_without_schedule` | `classify_hours(None, start, end, MSK)` → 24 `HourInfo`s with `plan is None` and `zone is None`. The local starts are the same as with a schedule. |
| unit | `tests/unit/test_report.py::test_build_report_without_schedule` | `build_report(req, None, [1 kWh/h for 24 h])` → `zones == ()`, `plans == ()`, `unpriced_hours == 24`, row `kwh == 24`, `cost is None`, `unpriced_kwh == 24`, cells `== ()`. A gap still gets spread (ESTIMATED issue present). Serialized: `"zones": []`, `"cost": None`, `"unpriced_kwh": "24.000"`. |

## Acceptance criteria
Native (no HA):
- [x] Tests were written first: the Implementation notes record `test_serialize.py` failing with
  `ModuleNotFoundError: engine.serialize` and the two appended tests failing before D-4.
- [x] `uv run pytest -m unit` → all pass. Existing tests in `test_classify.py`/`test_report.py` are unchanged
  (`git diff` shows additions only in those files).
- [x] `uv run pytest -m unit --cov=custom_components/energy_cost_stats/engine --cov-branch --cov-report=term-missing --cov-fail-under=95`
  → passes, and `serialize.py` is ≥ 95 % line+branch.
- [x] `uv run ruff check .` / `uv run ruff format --check .` → exit 0.
- [x] `tests/unit/test_engine_isolation.py` passes (`serialize.py` is stdlib + relative imports only).
- [x] `rg -n "round_money|round_kwh|round_price" custom_components/energy_cost_stats` → used only in
  `engine/serialize.py` (definitions in `engine/rounding.py`).
- [x] `rg -n "float" custom_components/energy_cost_stats/engine/serialize.py` → no matches.
- [x] `docs/SPEC.md` §4 has the JSON contract subsection and the no-plan bullet. No other section changed.
- [x] No files outside "Files" touched. Generic ids only.

Devcontainer / CI:
- [x] `dx uv run --group ha pyright` → 0 errors (strict mode for `engine/`).
- [ ] All required checks on the PR green (pending PR).

## Out of scope
- Collecting the inputs (adapter, settings, names, currency) and the websocket/service wiring → task 013.
- Localized number formatting, i18n of zone/status names (the card does that in stage 4).
- `effective_price`, per-zone shares and charts data (card or a later minor schema addition).
- Main meter / "untracked" row.

## Open questions
All decided by planner, confirm in PR review:
- D-1 Decimal values are **strings** (`"240.00"`), not JSON numbers. Automations need `| float`.
- D-2 The contract shape: aligned `zones` lists per row, ISO times with offset in the report time zone, `plans` as
  unrounded stored plan data, `schema_version` (only additions without a version bump).
- D-3 The serializer lives in the pure engine, so it is unit-tested natively. Device names and the currency are
  passed in by the integration.
- D-4 No plan → a report with every hour unpriced (`cost null`), not an error.

<!-- Filled in by implementer -->
## Implementation notes
- Tests first: `tests/unit/test_serialize.py` failed with `ModuleNotFoundError: No module named 'engine.serialize'`
  before the module existed; `test_report.py` (which imports the serializer for the appended test) failed to collect for
  the same reason. Before D-4, `classify_hours(None, ...)` would have raised `AttributeError` (`None.plan_for`).
  I wrote all tests in one step and ran them once against the empty implementation, so the classify test failing was
  inferred from the code, not observed separately.
- D-1..D-4 implemented as planned. All four are still "decided by planner, confirm in PR review" (strings for decimals,
  contract shape, serializer in the pure engine, no plan means unpriced report).
- `grouping` is output via `Grouping(request.grouping).value` (request type is `Grouping | str`).
- Added one extra test, `test_utc_inputs_are_converted_to_report_zone` (request given in UTC, top-level
  `start`/`end` emitted in the report zone).
- Test deviations: in `test_total_rounded_from_exact_sum` the totals bucket is checked via `doc["totals"]`.
  `test_plan_switch_price_null` also checks day boundaries (day 15 at `10.3000`, day 16 at `11.0000`).
  The appended report test imports `engine.serialize` at module level in `test_report.py` (one added import line).
- Results (devcontainer, HA latest leg): unit 339 passed; engine coverage 99.82 % (`serialize.py` 100 %, branch);
  ruff check/format clean; pyright 0 errors. Integration tests not touched, so the HA 2025.4 leg was not run.
- SPEC §4: added the "No tariff plan" bullet and the "JSON contract (schema_version 1)" subsection (before §5).
  I documented the `devices[].statistics` values and the "ignore unknown keys" consumer rule, which the task did not
  state explicitly.

- Review round 1 fixes: issue `hours` is now computed in UTC (`_elapsed_hours`), because same-zone aware datetimes
  subtract by wall clock (Berlin 2026-10-25 gave 3 for a 4-h gap, 2026-03-29 gave 5, a 1-h spike in the fold gave 0).
  Tests added first and seen failing: `test_issue_hours_across_dst` (both transitions) and
  `test_issue_hours_spike_in_fall_back_fold`. The helper also raises `ValueError` if the span is not a whole number
  of hours (suggestion 3). Added `test_nested_key_order` (suggestion 2). SPEC §4 Issues bullet now says "real
  elapsed hours". Grepped the engine for other same-zone subtractions: `quality.py` (`pos`, catch-up span) works on
  UTC-normalised keys, and bucket `hours` are counts, so nothing else needed changing. Suggestion 1 skipped as asked.

## Follow-ups
- Task 013 should describe in the service description that decimals are strings (`| float` in templates).
- 013 must pass `DeviceInfo.statistics` strings that match the adapter's status values; the serializer does not validate them.
- Consider a future minor addition of `effective_price` if the card needs it.
