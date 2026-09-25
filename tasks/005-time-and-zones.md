# 005 — Time and zones: UTC hours → local zones, DST, bucket keys, engine I/O types

Status: in-review
Roadmap: SPEC §8 stage 1 (engine + unit tests), task 2 of 4 (after 004-tariff-model)
Spec sections: SPEC §2, §3, §4 (report output), §5 (UTC vs local, DST, missing data); CLAUDE.md principles 2–4, 6

> **Human decisions (see "Open questions" at the end) override anything in this file that conflicts with them** —
> e.g. single-rate key `t0`, missing data as `None`, money/kWh serialized as strings, 7-day gap cap.
> Update the affected tests/criteria accordingly.

> **Performance note from 004 review:** `TariffPlan.zone_for_hour` rebuilds its 24-entry lookup on every call
> (~2.7 µs). Do not call it per device × hour: build the per-plan hour→zone table once (e.g. a public
> `hour_zones()` added here, or a local cache) and classify each hour once per request, reusing it for all devices.

## Goal
For any window of UTC hours and a given IANA time zone, the engine can tell each hour's local start time,
the tariff plan and zone in force, and which hour/day/week/month bucket the hour belongs to. DST days
(23 and 25 hours) come out right. This task also fixes the **engine's public input and output types**
(`ReportRequest`, `DeviceSeries`, and the `Report` dataclasses). Task 006 (pricing and grouping), task 007
(data quality) and the stage 3 websocket/service layer then all use one stable structure. No costs are
computed yet.

## Context

### Decisions (human-confirmed, stage 1)
1. **Input** is hourly energy deltas (kWh) keyed by the **UTC start of the hour** (the `change` value from
   recorder long-term statistics, SPEC §2). Zones, plan switches and groupings use **local time** from an
   IANA zone via `zoneinfo`.
2. **DST:** local days of 23 and 25 hours are handled correctly. Tests use a European zone with DST
   (`Europe/Berlin`). RU zones have no DST (`Europe/Moscow`, UTC+3 all year).
3. **Weeks start on Monday; months are local calendar months.** Groupings: hour, day, week, month, and a
   custom range (any start/end), optionally as one total bucket.
4. **The engine accepts whatever hours it is given.** It knows nothing about "now" or about long-term vs
   short-term statistics.
5. **Missing data is explicit, never a silent zero.** An hour with no key in the input is *missing*, not 0.
6. **Money and energy are `Decimal`.** Rounding happens only at output (task 006).

### Design decisions made in this task
- **Which local hour an hour belongs to.** Every UTC hour `h` is attributed by its local start
  `h.astimezone(tz)`:
  - zone = `plan.zone_for_hour(local_start.hour)`;
  - plan = `schedule.plan_for(local_start.date())`;
  - day/week/month bucket = derived from `local_start.date()`.

  This rule covers the following cases with no special code:
  - a plan switch takes effect at local midnight of `valid_from` (the decision from task 004);
  - a zone that crosses midnight works: the local 23:00 hour belongs to the day it starts in;
  - spring-forward: the skipped local hour simply never occurs;
  - fall-back: the repeated local hour occurs twice, both times in the same zone. `astimezone` sets `fold`
    correctly (see the Python docs below);
  - a time zone whose DST switch happens at midnight (so local midnight does not exist) also works. The
    engine never constructs local midnights; it only reads the local dates of real instants.
- **Non-whole-hour UTC offsets** (e.g. +05:30): UTC hours then start at local `xx:30`. Rule: the hour is
  attributed to the local hour and date its start falls in. Not relevant for RU; see open questions.
- **Window bounds** are aware datetimes on **UTC hour boundaries** (minute = second = microsecond = 0 after
  conversion to UTC). The end is exclusive. The caller (stage 3) computes local-midnight bounds. The engine
  offers `local_day_start()` for that and for tests.
- **Buckets are identified by keys**, not by constructed local datetimes:
  - HOUR → the UTC hour;
  - DAY → the local `date`;
  - WEEK → the `date` of that week's Monday;
  - MONTH → the `date` of the 1st of the month;
  - TOTAL → one key (`None`) for the whole window.

  In the report, a bucket's `start` is the start of its first hour and its `end` is the end of its last
  hour, counting only hours *inside the window*. So edge buckets are clipped. Both are expressed in the
  report time zone.

### API defined in this task

`engine/timeutil.py` (functions, stdlib only; must **not** import `models.py`, which imports timeutil):
- `to_utc_hour(value: datetime) -> datetime` rejects naive datetimes and values not on a UTC hour boundary
  (`ValueError`). It returns the same instant with `tzinfo=UTC`.
- `iter_hours(start: datetime, end: datetime) -> Iterator[datetime]` yields the UTC hour starts in
  `[start, end)`.
- `local_day_start(day: date, tz: tzinfo) -> datetime` returns the earliest UTC hour start whose local date
  is `day`. Implement it by searching around `datetime.combine(day, time(), tz)` (± a few hours) and
  checking the local date of each candidate UTC hour. Do not trust the naive construction alone.

`engine/models.py` (public I/O types: frozen, slotted dataclasses and `StrEnum`s):
- `class Grouping(StrEnum)`: `HOUR="hour"`, `DAY="day"`, `WEEK="week"`, `MONTH="month"`, `TOTAL="total"`.
  A "custom range" is any `start`/`end` with any grouping; `TOTAL` gives one bucket.
- `ReportRequest(start: datetime, end: datetime, time_zone: tzinfo, grouping: Grouping)`:
  `__post_init__` normalizes `start`/`end` via `to_utc_hour` and requires `end > start`.
- `DeviceSeries(device_id: str, deltas: Mapping[datetime, Decimal])`:
  - `device_id` must be non-empty.
  - Keys are normalized to UTC hours and stored as a read-only copy (e.g. `MappingProxyType(dict)`). Two
    keys for the same instant → `ValueError`.
  - Values must be finite `Decimal`s (runtime check).
  - Keys outside the report window are allowed (task 007 uses them as look-back).
  - Classmethod `from_floats(device_id, deltas: Mapping[datetime, float])` converts each value with
    `Decimal(repr(x))`, so `0.1` becomes `Decimal("0.1")`. This is the only `float` entry point (for the
    stage 3 adapter).
- `class DataStatus(StrEnum)`: `COMPLETE`, `ESTIMATED`, `PARTIAL`, `MISSING` (values lowercase).
- `Coverage(expected: int, measured: int, estimated: int, excluded: int, missing: int)`:
  - invariant `expected == measured + estimated + excluded + missing`, all fields ≥ 0 (else `ValueError`);
  - `__add__` sums field by field; `Coverage.empty()` returns all zeros;
  - property `status`: `MISSING` if `measured + estimated == 0` (this includes `expected == 0`); else
    `PARTIAL` if `excluded + missing > 0`; else `ESTIMATED` if `estimated > 0`; else `COMPLETE`.
- `ZoneLabel(key: str, name: str)`.
- `ZoneCell(key: str, kwh: Decimal, cost: Decimal, price: Decimal | None)`:
  - `price` is the single price applied to that zone in the bucket. It is `None` if several prices applied
    (plan switch inside the bucket) or the zone was not in force.
  - Property `effective_price -> Decimal | None` = `cost / kwh`, or `None` when `kwh == 0`.
- `Row(device_id: str | None, zones: tuple[ZoneCell, ...], kwh: Decimal, cost: Decimal,
  unpriced_kwh: Decimal, estimated_kwh: Decimal, excluded_kwh: Decimal, coverage: Coverage)`:
  - `device_id=None` marks the total row.
  - `zones` has one cell per `Report.zones` entry, in the same order.
  - `kwh` = all counted kWh (priced + unpriced, measured + estimated).
  - `cost` = cost of priced kWh only.
  - `excluded_kwh` is *not* part of `kwh`.
  - Property `status` → `coverage.status`.
- `Bucket(start: datetime, end: datetime, hours: int, rows: tuple[Row, ...], total: Row)`: `rows` are in
  input device order.
- `class IssueKind(StrEnum)`: `ESTIMATED="estimated"`, `EXCLUDED_NEGATIVE="excluded_negative"`,
  `EXCLUDED_SPIKE="excluded_spike"`.
- `QualityIssue(kind: IssueKind, device_id: str, start: datetime, end: datetime, kwh: Decimal)`: filled in
  by task 007. `start`/`end` are in the report time zone.
- `Report(request: ReportRequest, zones: tuple[ZoneLabel, ...], plans: tuple[TariffPlan, ...],
  buckets: tuple[Bucket, ...], totals: Bucket, unpriced_hours: int, issues: tuple[QualityIssue, ...] = ())`.

`engine/classify.py`:
- `HourInfo(utc_start: datetime, local_start: datetime, plan: TariffPlan | None, zone: Zone | None)`
  (frozen dataclass).
- `classify_hours(schedule: TariffSchedule, start: datetime, end: datetime, tz: tzinfo) -> tuple[HourInfo, ...]`
  returns one entry per UTC hour in the window. It is computed once per report and shared by all devices
  (task 006). `plan`/`zone` are `None` before the first plan.
- `bucket_key(info: HourInfo, grouping: Grouping) -> BucketKey`, where `BucketKey = datetime | date | None`
  (HOUR → `info.utc_start`; DAY/WEEK/MONTH → local dates as defined above; TOTAL → `None`).

### Checked references
- Python `zoneinfo` docs (https://docs.python.org/3/library/zoneinfo.html) say: "Some systems, including
  notably Windows systems, do not have an IANA database available … it is recommended to declare a
  dependency on tzdata." → **add `tzdata` to the `dev` dependency group**. Without it,
  `ZoneInfo("Europe/Berlin")` fails in the native Windows unit tests. The same docs say that converting with
  `astimezone()` sets `fold` correctly for the repeated fall-back hour.
- Home Assistant passes its configured zone as a `zoneinfo.ZoneInfo` (`dt_util.get_default_time_zone()`).
  Typing `time_zone` as `datetime.tzinfo` accepts it without importing HA.
- DST 2026 in `Europe/Berlin`:
  - spring forward on Sun 2026-03-29 at 01:00 UTC: the local day has 23 hours,
    2026-03-28T23:00Z … 2026-03-29T22:00Z;
  - fall back on Sun 2026-10-25 at 01:00 UTC: the local day has 25 hours,
    2026-10-24T22:00Z … 2026-10-25T23:00Z.

  The implementer confirms these with `zoneinfo` while writing the tests.
- Calendar: 2026-01-01 is a Thursday. Mondays in January 2026: 5, 12, 19, 26.

## Files
- create: `custom_components/energy_cost_stats/engine/timeutil.py` — as above.
- create: `custom_components/energy_cost_stats/engine/models.py` — as above.
- create: `custom_components/energy_cost_stats/engine/classify.py` — as above.
- modify: `pyproject.toml` — add `"tzdata"` to the `dev` group, unpinned (per task 001 decision 2).
- modify: `uv.lock` — regenerated by `uv lock`.
- create: `tests/unit/test_timeutil.py`
- create: `tests/unit/test_models.py`
- create: `tests/unit/test_classify.py`

## Tests to write first
Time zones in tests: `MSK = ZoneInfo("Europe/Moscow")`, `BER = ZoneInfo("Europe/Berlin")`. Plans come from
the task 004 presets (two-zone, day `10.30` / night `4.43`).

| Level | Test | Asserts |
|---|---|---|
| unit | `tests/unit/test_timeutil.py::test_to_utc_hour_normalizes` | `2026-01-15T23:00+03:00` → `2026-01-15T20:00Z` with `tzinfo is UTC`. |
| unit | `tests/unit/test_timeutil.py::test_to_utc_hour_rejects` | Parametrized: naive datetime; `20:30Z`; `20:00:01Z`; 1 µs past the hour; local midnight in `Asia/Kolkata` (= `18:30Z`) → `ValueError`. |
| unit | `tests/unit/test_timeutil.py::test_iter_hours` | `[2026-01-15T00Z, 03Z)` → 3 hours in order; `start == end` → empty. |
| unit | `tests/unit/test_timeutil.py::test_local_day_normal_msk` | `local_day_start(2026-01-15, MSK) == 2026-01-14T21:00Z`; the day has 24 hours. |
| unit | `tests/unit/test_timeutil.py::test_local_day_spring_forward_berlin` | Day 2026-03-29: start `2026-03-28T23:00Z`, next day's start `2026-03-29T22:00Z`, 23 hours; no hour has local `hour == 2`. |
| unit | `tests/unit/test_timeutil.py::test_local_day_fall_back_berlin` | Day 2026-10-25: start `2026-10-24T22:00Z`, next day's start `2026-10-25T23:00Z`, 25 hours; local hour 2 occurs twice, with `utcoffset()` +2 h then +1 h. |
| unit | `tests/unit/test_timeutil.py::test_local_day_start_property` | For every date of 2026 in `BER`, `MSK`, `America/Santiago` and `Asia/Kolkata`: `local_day_start(d).astimezone(tz).date() == d`, and the hour before it has an earlier local date. |
| unit | `tests/unit/test_classify.py::test_bucket_key` | Parametrized (MSK): DAY of local `2026-01-15 23:00` → `date(2026,1,15)`; WEEK of Thu 2026-01-15 → `date(2026,1,12)`; WEEK of Sun 2026-01-18 23:00 → `date(2026,1,12)`; WEEK of Mon 2026-01-19 00:00 → `date(2026,1,19)`; MONTH of 2026-01-31 23:00 → `date(2026,1,1)`; HOUR → the UTC hour; TOTAL → `None`. |
| unit | `tests/unit/test_classify.py::test_bucket_hour_counts_dst_berlin` | Hours counted per key: MONTH March 2026 = 743, April = 720, October = 745; WEEK starting Mon 2026-03-23 = 167; WEEK starting Mon 2026-10-19 = 169. |
| unit | `tests/unit/test_models.py::test_report_request_validation` | Naive start → `ValueError`; `end <= start` → `ValueError`; start at `:30` → `ValueError`; aware `+03:00` bounds are stored as UTC. |
| unit | `tests/unit/test_models.py::test_device_series_normalizes_and_validates` | Keys given in `+03:00` are stored as UTC; the stored mapping is read-only. Each of these → `ValueError`: naive key, `:30` key, `Decimal("NaN")`, float value, empty `device_id`, two keys for the same instant (one UTC, one `+03:00`). |
| unit | `tests/unit/test_models.py::test_device_series_from_floats` | `from_floats("plug_01", {h: 0.1})` → the value is a `Decimal` and `== Decimal("0.1")`. |
| unit | `tests/unit/test_models.py::test_coverage_status` | Parametrized `(expected, measured, estimated, excluded, missing) → status`: `(24,24,0,0,0) COMPLETE`, `(24,20,4,0,0) ESTIMATED`, `(24,20,0,0,4) PARTIAL`, `(24,20,2,1,1) PARTIAL`, `(24,0,0,0,24) MISSING`, `(24,0,0,24,0) MISSING`, `(0,0,0,0,0) MISSING`. |
| unit | `tests/unit/test_models.py::test_coverage_invariant_and_add` | `Coverage(24,1,0,0,0)` → `ValueError`; `Coverage(24,24,0,0,0) + Coverage(24,20,0,0,4) == Coverage(48,44,0,0,4)`. |
| unit | `tests/unit/test_models.py::test_zone_cell_effective_price` | `kwh=0` → `None`; `kwh=Decimal("2")`, `cost=Decimal("8.86")` → `Decimal("4.43")`. |
| unit | `tests/unit/test_models.py::test_enums_serialize_as_lowercase_strings` | `str(Grouping.WEEK) == "week"`, `DataStatus.MISSING == "missing"`, `IssueKind.EXCLUDED_SPIKE == "excluded_spike"`. |
| unit | `tests/unit/test_classify.py::test_two_zone_day_msk` | Local day 2026-01-15 (MSK), plan valid from 2026-01-01: 16 hours `t1`, 8 hours `t2`. The hour `2026-01-15T20:00Z` has local start 23:00 on Jan 15 and zone `t2`; `2026-01-15T03:00Z` (local 06:00) → `t2`; `04:00Z` (local 07:00) → `t1`. |
| unit | `tests/unit/test_classify.py::test_plan_switch_at_local_midnight_msk` | Plans A (2026-01-01) and B (2026-07-01): `2026-06-30T20:00Z` (local 23:00) → A; `2026-06-30T21:00Z` (local 00:00 Jul 1) → B. |
| unit | `tests/unit/test_classify.py::test_plan_switch_on_dst_day_berlin` | B valid from 2026-10-25: `2026-10-24T21:00Z` (local 23:00 CEST) → A; `2026-10-24T22:00Z` (local 00:00) → B. |
| unit | `tests/unit/test_classify.py::test_dst_zone_counts_berlin` | Two-zone plan, local day 2026-03-29: `t1` 16 h, `t2` 7 h; local day 2026-10-25: `t1` 16 h, `t2` 9 h; a normal day: 16 / 8. |
| unit | `tests/unit/test_classify.py::test_before_first_plan_is_unclassified` | Hours on 2025-12-31 (MSK), with the first plan from 2026-01-01 → `plan is None and zone is None`; the first local hour of 2026-01-01 has a plan. |
| unit | `tests/unit/test_classify.py::test_single_rate_then_two_zone` | Single-rate until 2026-06-30, two-zone from 2026-07-01: all hours of Jun 30 → the single-rate zone; Jul 1 → 16 × `t1` and 8 × `t2` from plan B. |
| unit | `tests/unit/test_classify.py::test_classify_rejects_bad_window` | Non-aligned or naive bounds → `ValueError`. |

## Acceptance criteria
Windows native:
- [x] `uv sync` → exit 0; `uv run python -c "import zoneinfo; zoneinfo.ZoneInfo('Europe/Berlin')"` → exit 0.
- [x] `uv lock --check` → exit 0.
- [x] `uv run pytest -m unit` → all pass (tests from tasks 001 and 004 included).
- [x] `uv run pytest -m unit --cov=custom_components/energy_cost_stats/engine --cov-branch --cov-report=term-missing --cov-fail-under=95` → passes (100% reached).
- [x] `uv run ruff check .`, `uv run ruff format --check .` → exit 0.
- [x] `uv run pyright custom_components/energy_cost_stats/engine tests/unit` → 0 errors.

Container (or CI once task 003 has landed):
- [x] `uv sync --group ha` still resolves (the added `tzdata` does not conflict with the PHCC pins), and
  `uv run --group ha pyright` → 0 errors. Verified in a one-off `ghcr.io/astral-sh/uv:python3.14-trixie`
  container (`UV_PROJECT_ENVIRONMENT=/opt/venv`); did not touch the developer's own devcontainer.

General:
- [x] `rg -n "^from |^import " custom_components/energy_cost_stats/engine` shows only stdlib modules and
  relative imports.
- [x] No import cycle: `uv run python -c "import engine.timeutil, engine.models, engine.classify"` run from
  `custom_components/energy_cost_stats` → exit 0.
- [x] Engine code never uses a local midnight built with `datetime.combine(..., tz)` as a bound without
  checking it. The reviewer reads `timeutil.py`; `local_day_start` is covered by the property test.
- [x] No files touched outside the "Files" list.

## Out of scope
- Costs, aggregation into buckets, totals, rounding, serialization → **006-pricing-and-grouping**.
- Gap spreading, spike/negative exclusion, producing `QualityIssue`s → **007-data-quality**. The types exist
  after this task, but nothing fills them yet.
- Reading statistics, short-term statistics for the current hour, look-back window size → stage 3 adapter.
- Main meter / "untracked" row, nested meters.
- Weekday-dependent zones (SPEC §3 "later").

## Open questions
None — resolved by the human (2026-09-25):
- **Non-whole-hour UTC offsets (+05:30 etc.) are accepted**: each UTC hour is attributed by the local time its
  start falls in; the resulting half-hour boundary shift is documented as a known limitation (no error).
- **Missing data is `None`, not 0:** a device/cell with no data carries `kwh = None` / `cost = None` plus
  `status = missing`, so it can never be confused with "measured zero". Totals skip `None` and report partial
  coverage via status.

<!-- Filled in by implementer -->
## Implementation notes
- `to_utc_hour` rejects naive datetimes explicitly (`value.tzinfo is None`), then converts via
  `value.astimezone(UTC)` and checks minute/second/microsecond == 0; this also rejects non-hour-boundary
  instants, including half-hour-offset local midnights (e.g. `Asia/Kolkata`).
- `local_day_start` never trusts `datetime.combine(day, time(), tz)` alone: it rounds that guess down to a
  UTC hour boundary and scans a ±26-hour window of candidate UTC hours for the earliest one whose local
  date (via `.astimezone(tz)`) equals `day`. 26 hours covers every real IANA UTC offset range (including
  half-hour and 45-minute zones) with margin.
- `classify.py` builds one 24-entry hour→zone lookup per **distinct plan object** encountered while
  classifying a window (keyed by `id(plan)`), not per hour and not per device — this satisfies the 004
  review performance note (`TariffPlan.zone_for_hour` was ~2.7 µs per call because it rebuilds its lookup
  every time). Devices are expected to reuse the same `tuple[HourInfo, ...]` from one `classify_hours` call
  (task 006).
- Human decision (missing data is `None`, not 0, resolved 2026-09-25) changes `ZoneCell.kwh`/`ZoneCell.cost`
  and `Row.kwh`/`Row.cost` from `Decimal` (as literally typed in the task body) to `Decimal | None`. The task
  body's own callout says these decisions override conflicting body text; `Row.unpriced_kwh`/`estimated_kwh`/
  `excluded_kwh` were left as plain `Decimal` (defaulting to 0 when a row has no data at all, which is fine
  since `Row.status`/`Coverage.status` — not these fields — is the source of truth for "missing" vs
  "measured zero"). No test in this task exercises the `None` path yet (task 006/007 fill real values); a
  `ZoneCell(kwh=None, cost=None, price=None)` construction/`effective_price` check was added defensively.
- `DeviceSeries`'s "two keys for the same instant → ValueError" case cannot be produced with a plain `dict`
  literal: aware-datetime equality/hash is instant-based, so Python's dict literal already collapses two
  keys representing the same instant into one entry before `DeviceSeries.__post_init__` ever runs. The test
  uses a small custom `Mapping` (`_DupMapping`, a `collections.abc.Mapping` subclass) that preserves both
  pairs via `.items()`, exercising the duplicate check that the *general* `Mapping` input type (not
  necessarily a `dict`) requires.
- Added `tzdata` to the `dev` dependency group (unpinned, per task 001 decision 2); `uv.lock` regenerated.
  Confirmed in a one-off `ghcr.io/astral-sh/uv:python3.14-trixie` container that `uv sync --group ha` still
  resolves and `uv run --group ha pyright` reports 0 errors (did not touch the developer's own running
  devcontainer).
- Added `tests/**` to ruff's `PT011` per-file-ignore (alongside the existing `TID251`): with ~15
  `pytest.raises(ValueError)` call sites across the three new test files, requiring a `match=` regex on each
  would either be redundant boilerplate or fragile coupling to exact error-message wording; a deliberately
  bare `pytest.raises(ValueError)` is standard practice for pure "does this raise" checks and every case here
  is paired with adjacent asserts on the resulting object's state, not on the raise alone.
- Two internal `# pyright: ignore[reportUnnecessaryIsInstance]` comments were added in `models.py`
  (`DeviceSeries.__post_init__`'s value check, `Coverage.__add__`'s `other` check), mirroring the existing
  pattern in `tariff.py`: these are runtime guards against callers who bypass the static type hints (a real
  concern for a `Mapping[datetime, Decimal]` parameter that untrusted config/adapter code populates), so
  strict pyright's "this is always true" is correct but the check must stay.

## Implementation notes — review round 1 fixes
- Restored the `guess = guess.replace(minute=0, second=0, microsecond=0)` round-down in
  `local_day_start` (`timeutil.py`) that was missing from the working tree at the start of this round;
  without it, `local_day_start` for a half-hour-offset zone (e.g. `Asia/Kolkata`) would return a UTC
  instant on `xx:30`, which `to_utc_hour`/`ReportRequest`/`classify_hours` then reject. Also updated the
  adjacent comment ("a handful of hours" → "any real UTC offset range", suggestion 6) since the search
  already spans ±26 hours.
- `docs/SPEC.md` §5: added a "Known limitation" bullet documenting the non-whole-hour UTC offset behavior
  (local day/zone boundaries shift by the offset's minute remainder; no error raised). Mirrored a short
  version in `classify_hours`'s docstring in `classify.py`.
- `tests/unit/test_timeutil.py::test_local_day_start_property`: now also asserts
  `to_utc_hour(start) == start` and `start.tzinfo is UTC` for every date/zone, catching removal of the
  round-down above (confirmed it fails with the mutation applied, for the `Asia/Kolkata` case).
- `tests/unit/test_classify.py::test_half_hour_offset_zone_kolkata` (new): classifies one local day in
  `Asia/Kolkata`, asserts 24 hours, first hour's `local_start` is `00:30` on the requested date, and the
  day/night zone split is still 16/8 (the RU two-zone boundaries shift by the same 30-minute remainder as
  the day start, so the count is unaffected).
- `tests/unit/test_classify.py::test_dst_fall_back_repeated_hour_berlin` (new): for the Berlin fall-back
  day, asserts every hour's `local_start.astimezone(UTC) == utc_start` (via `astimezone`, not direct `==`,
  since PEP 495 makes fold-ambiguous inter-zone equality always `False`), and that the two hours with
  `local_start.hour == 2` have `utcoffset()` `+2h` then `+1h` in UTC order. Confirmed this fails if
  `classify.py` drops `fold` (e.g. `hour.astimezone(tz).replace(fold=0)`).
- `ReportRequest.grouping`: type widened to `Grouping | str` and `__post_init__` now normalizes via
  `Grouping(self.grouping)`, raising a clear `ValueError` (listing the valid values) for anything else.
  This makes `bucket_key`'s `is`-comparisons and its "unknown grouping" branch correct at runtime once
  stage 3 passes JSON strings, per the reviewer's suggestion 3. Covered by
  `test_report_request_grouping_accepts_enum_or_value_string` and
  `test_report_request_grouping_rejects_unknown_value` in `test_models.py`.
- Verified (native Windows): `uv run pytest -m unit --cov=... --cov-fail-under=95` → 155 passed, 100%
  coverage; `uv run ruff check .` / `ruff format --check .` → clean; `uv run pyright
  custom_components/energy_cost_stats/engine tests/unit` → 0 errors.

## Follow-ups
- Reviewer suggestion 1: widen the DST week-count test to a whole month and assert `Counter(...)[week_key]`
  for the March/October DST weeks specifically, not just `len()` of an already-one-week window.
- Reviewer suggestion 2: add `Coverage(24, 20, 0, 4, 0) → PARTIAL` (excluded-only) and
  `Coverage(True, 1, 0, 0, 0) → ValueError` cases to `test_coverage_status`/`test_coverage_invariant_and_add`.
- Reviewer suggestion 4: cache `TariffSchedule.plan_for`'s per-date lookup inside `classify_hours` if task
  006 ends up classifying long windows repeatedly (currently ~2.3 µs/hour total, not a blocker).
- Reviewer suggestion 5: add `match=` to the `pytest.raises` calls where one function raises for several
  distinct reasons (e.g. `DeviceSeries.__post_init__`), to pin down which check fired.
- Reviewer suggestion 7: note in `DeviceSeries`'s docstring that it holds a `MappingProxyType` and is
  therefore unhashable / not `asdict()`-safe, so stage 3 should not try to serialize it directly.
