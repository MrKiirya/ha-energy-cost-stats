# 004 — Tariff model: versioned plans, zones, validation, presets

Status: planned
Roadmap: SPEC §8 stage 1 (engine + unit tests), task 1 of 4 (004-tariff-model, 005-time-and-zones,
006-pricing-and-grouping, 007-data-quality)
Spec sections: SPEC §2 (engine is pure Python), §3 (tariff data model), §5 (pitfalls); CLAUDE.md principles 3, 4, 6

> **Human decisions (see "Open questions" at the end) override anything in this file that conflicts with them** —
> e.g. single-rate key `t0`, missing data as `None`, money/kWh serialized as strings, 7-day gap cap.
> Update the affected tests/criteria accordingly.

## Goal
The engine gets its first real code: an immutable, validated tariff data model (versioned plans → zones →
whole-hour periods, prices as `Decimal`), a schedule that answers "which plan applies on this local date"
and "which zone applies at this local hour", and the three presets (single-rate, RU two-zone, RU
three-zone). No time zones, no UTC, no consumption data yet: this task works only with local dates and
local hours 0–23. Later tasks (005–007), the config flow (stage 2) and the websocket layer (stage 3) build on
these types. The human decisions for stage 1 are recorded in `docs/SPEC.md` §3/§5 in this same PR.

## Context

### Decisions (human-confirmed, stage 1)
1. **Versioned plans.** A plan has `valid_from` (a *local* calendar date) and applies from local midnight
   of that date until the next plan's `valid_from`. There is no end date. Any change, even price only,
   is a new plan. Two plans with the same `valid_from` are invalid.
2. **Zones** have a stable `key` (used in statistics and reports), a display-only `name`, a `price` per kWh
   and one or more `periods` on whole hours. **Validation:** within a plan the zones cover each of the 24
   local hours exactly once (no gap, no overlap).
3. **Presets:** single-rate; RU two-zone (day 07–23, night 23–07); RU three-zone (peak 07–10 and 17–21,
   semi-peak 10–17 and 21–23, night 23–07). Generic real-world example used in tests: two-zone, day
   `10.30`, night `4.43` per kWh.
4. **Volume tiers are out of stage 1 computation, but the model reserves room.** RU "consumption ranges"
   are monthly household kWh bands with different prices (for example ≤ 3900, 3901–6000, > 6000 kWh/month).
   The model gets optional fields (below) so adding tier pricing later is non-breaking. The engine uses the
   first-band price (`Zone.price`) everywhere in stage 1. Future method (document only, do not implement):
   compute the household monthly bill by bands → derive a blended per-zone price for that month → apply it
   to all devices.
5. **Money is `Decimal` everywhere.** No `float` in the model. Rounding to 2 decimals happens only at
   output (task 006).

### Model design (this task defines it; later tasks consume it)
Module `engine/tariff.py`. All classes are `@dataclass(frozen=True, slots=True)`, validate in
`__post_init__`, and store collections as `tuple` (immutable, hashable). `dataclasses.replace()` re-runs
validation (it calls `__init__`), which is how a UI "duplicate current plan" and presets "editable after
creation" work.

- `class TariffValidationError(ValueError)`: raised on every validation failure. The message names the
  problem concretely (e.g. `"hours not covered: 23, 0"`, `"hour 22 covered by zones t1 and t2"`,
  `"duplicate zone key: t1"`). Stage 2's config flow will show these messages.
- `Period(start_hour: int, end_hour: int)`: the half-open local-hour interval `[start, end)`.
  - `start_hour` in 0..23, `end_hour` in 1..24, `start_hour != end_hour`. `bool` is rejected (it is an
    `int` subclass).
  - `end_hour < start_hour` means the period crosses midnight: `Period(23, 7)` = hours 23, 0, 1, …, 6.
  - The full day is `Period(0, 24)`.
  - `hours() -> tuple[int, ...]` in wall-clock order starting at `start_hour`.
  - `Period.parse(start: str, end: str) -> Period` accepts `"HH:MM"` strings as in the SPEC §3 JSON. Minutes
    must be `00` (whole hours, hourly statistics limit). `"00:00"` or `"24:00"` as **end** means 24.
    `"24:00"` as start is invalid. Anything else (`"7"`, `"07:30"`, `"25:00"`, `"ab:cd"`) raises.
  - Reserved for later (do not add now): an optional weekday filter (SPEC §3). Because `Period` is a
    dataclass, adding `weekdays: frozenset[int] | None = None` later is non-breaking.
- `Zone(key: str, name: str, price: Decimal, periods: tuple[Period, ...], band_prices: tuple[Decimal, ...] = ())`
  - `key` matches `^[a-z0-9_]{1,32}$` (stable, statistics-safe). `name` is non-empty after `strip()`.
  - `price` is a finite `Decimal` ≥ 0 (a runtime `isinstance(price, Decimal)` check rejects `float`/`int`,
    so config-layer mistakes fail loudly). NaN and Infinity are rejected.
  - `periods` is non-empty.
  - `band_prices` (reserved, see decision 4): prices for volume bands 2..n+1. Band 1 is `price`. Each is a
    finite `Decimal` ≥ 0. The engine ignores it in stage 1.
- `TariffPlan(valid_from: date, name: str, zones: tuple[Zone, ...], volume_band_limits_kwh: tuple[Decimal, ...] = ())`
  - `zones` non-empty, keys unique, 24-hour coverage exactly once (decision 2). Build a 24-entry lookup in
    `__post_init__`. With `slots=True` + `frozen=True`, set it via `object.__setattr__` on a field declared
    with `field(init=False, repr=False, compare=False)`.
  - `volume_band_limits_kwh` (reserved): ascending upper limits of monthly household kWh for bands 1..n
    (band n+1 has no upper limit). Each limit > 0, strictly increasing. If it is empty, every zone's
    `band_prices` must be empty. If it is non-empty, every zone's `band_prices` must have exactly
    `len(volume_band_limits_kwh)` entries.
  - `zone_for_hour(hour: int) -> Zone` (0..23, otherwise `ValueError`).
  - `zone_keys() -> tuple[str, ...]` in declaration order.
- `TariffSchedule(plans: tuple[TariffPlan, ...])`
  - Non-empty; no two plans with the same `valid_from`. Stores plans **sorted by `valid_from`** whatever
    the input order.
  - `plan_for(local_date: date) -> TariffPlan | None`: the latest plan with `valid_from <= local_date`,
    `None` before the first plan (task 006 reports such hours as "unpriced"). Use `bisect`.
  - `plans_between(start: date, end: date) -> tuple[TariffPlan, ...]`: plans in effect on at least one
    local date in `[start, end)`, in order.

Module `engine/presets.py`, keyword-only arguments, each returns a `TariffPlan`:
- `single_rate(*, valid_from: date, price: Decimal, name: str = "Single-rate")` → one zone
  `t1` "Single-rate", `Period(0, 24)`.
- `ru_two_zone(*, valid_from, day_price, night_price, name="Two-zone")` → `t1` "Day" `[7, 23)`,
  `t2` "Night" `[23, 7)`.
- `ru_three_zone(*, valid_from, peak_price, semi_peak_price, night_price, name="Three-zone")` →
  `t1` "Peak" `[7, 10)` + `[17, 21)`, `t2` "Night" `[23, 7)`, `t3` "Semi-peak" `[10, 17)` + `[21, 23)`.
- **Key convention (proposed, see open questions):** keys follow the labels on Russian multi-tariff meters:
  T1 = peak (or day), T2 = night, T3 = semi-peak. So "night" is always `t2` in both RU presets.

### What was checked
- No Home Assistant API is involved in this task (pure Python, stdlib only: `dataclasses`, `datetime.date`,
  `decimal`, `bisect`, `re`).
- The engine package rules from task 001 apply: relative imports only inside `engine/`; unit tests import
  `engine.tariff` / `engine.presets`, never `custom_components…`; pyright strict on `engine/`.

## Files
- create: `custom_components/energy_cost_stats/engine/tariff.py` — `TariffValidationError`, `Period`,
  `Zone`, `TariffPlan`, `TariffSchedule` as above.
- create: `custom_components/energy_cost_stats/engine/presets.py` — the three presets.
- create: `tests/unit/test_tariff.py`
- create: `tests/unit/test_presets.py`
- modify: `docs/SPEC.md` — record the stage 1 decisions (see "SPEC edits" below). Keep edits to §3 and §5.

### SPEC edits
§3 (tariff data model), add or replace bullets so that it says:
- `valid_from` is a local calendar date; the plan applies from local midnight of that date; no end date;
  same-date duplicates are invalid.
- Periods are half-open whole-hour intervals `[start, end)`; `end < start` crosses midnight; `00:00`/`24:00`
  as end = end of day; full day = `00:00–24:00`.
- Presets with the key convention (t1 peak/day, t2 night, t3 semi-peak) and the generic example plan.
- Volume tiers ("consumption ranges"): reserved fields `volume_band_limits_kwh` (plan) and `band_prices`
  (zone); stage 1 uses the first band only; the future blended-price method (decision 4).
- Money is `Decimal`; rounding to 2 decimals only at output.

§5 (pitfalls), add or replace bullets so that it says:
- Engine input is hourly deltas keyed by **UTC hour start**; zones, plan switches and groupings use local
  time (IANA tz via `zoneinfo`); DST days have 23/25 hours and are handled; weeks start on Monday; months
  are local calendar months; groupings: hour/day/week/month/custom range (+ totals).
- Data quality (implemented in task 007): an offline gap followed by a catch-up delta is spread evenly over
  the gap hours plus the catch-up hour, each hour priced in its own zone, flagged "estimated". Negative
  deltas and deltas above a per-device limit (default 4 kWh/h ≈ a 16 A socket at 3.7 kW; global setting;
  per-device override or disable) are excluded and reported (count, kWh, when), flagged "excluded".
  Missing data is always explicit (missing/partial), never a silent zero.
- Known limitation: plugs that report late across a zone boundary put some kWh into the wrong zone
  (boundary misattribution). The engine cannot detect this from hourly statistics.
- Meter resets of `total_increasing` sensors are already handled by HA when it compiles the statistics
  `change`. Small drops (< 10 %) are not treated as resets and appear as negative deltas (excluded above).
- Out of stage 1: main meter / "untracked" row, nested-meter de-duplication, short-term statistics for the
  current hour (the engine accepts whatever hours it is given).

## Tests to write first
All tests are `unit` (auto-marked by directory). Prices in tests are built from strings, e.g.
`Decimal("10.30")`. Dates are generic (2026).

| Level | Test | Asserts |
|---|---|---|
| unit | `tests/unit/test_tariff.py::test_period_hours_simple` | `Period(7, 23).hours() == tuple(range(7, 23))` (16 hours). |
| unit | `tests/unit/test_tariff.py::test_period_crossing_midnight` | `Period(23, 7).hours() == (23, 0, 1, 2, 3, 4, 5, 6)`. |
| unit | `tests/unit/test_tariff.py::test_period_full_day` | `Period(0, 24).hours() == tuple(range(24))`. |
| unit | `tests/unit/test_tariff.py::test_period_invalid` | Parametrized `(24, 5)`, `(-1, 5)`, `(5, 5)`, `(5, 0)`, `(5, 25)`, `(True, 5)` → `TariffValidationError`. |
| unit | `tests/unit/test_tariff.py::test_period_parse_valid` | Parametrized: `("07:00","23:00")→(7,23)`, `("23:00","00:00")→(23,24)`, `("00:00","00:00")→(0,24)`, `("00:00","24:00")→(0,24)`, `("23:00","07:00")→(23,7)`. |
| unit | `tests/unit/test_tariff.py::test_period_parse_invalid` | Parametrized `("07:30","23:00")`, `("7","23:00")`, `("25:00","07:00")`, `("24:00","07:00")`, `("ab:cd","07:00")`, `("07:00","07:00")` → `TariffValidationError`. |
| unit | `tests/unit/test_tariff.py::test_zone_invalid` | Parametrized: empty key, key `"T 1"`, key longer than 32 chars, name `"  "`, price `Decimal("-0.01")`, `Decimal("NaN")`, `Decimal("Infinity")`, price `10.3` (float), no periods → `TariffValidationError`. |
| unit | `tests/unit/test_tariff.py::test_plan_zone_for_hour_two_zone` | Two-zone plan built by hand: hours 0–6 and 23 → key `t2`; hours 7–22 → `t1`; `zone_for_hour(24)` and `zone_for_hour(-1)` raise `ValueError`. |
| unit | `tests/unit/test_tariff.py::test_plan_multiple_periods_per_zone` | A zone with periods `[7,10)` + `[17,21)` maps hours 7, 8, 9, 17, 18, 19, 20 to that zone. |
| unit | `tests/unit/test_tariff.py::test_plan_coverage_gap` | Only a day zone `[7,23)` → error; the message lists the uncovered hours (contains `"23"` and `"0"`). |
| unit | `tests/unit/test_tariff.py::test_plan_coverage_overlap` | Day `[7,23)` + night `[22,7)` → error whose message mentions hour `22`. |
| unit | `tests/unit/test_tariff.py::test_plan_duplicate_zone_key_and_empty` | Two zones with key `t1` → error; `zones=()` → error. |
| unit | `tests/unit/test_tariff.py::test_plan_volume_bands_reserved` | Plan with `volume_band_limits_kwh=(Decimal("3900"), Decimal("6000"))` and each zone having 2 `band_prices` is valid; `zone_for_hour(12).price` is still the first-band price. |
| unit | `tests/unit/test_tariff.py::test_plan_volume_bands_invalid` | Parametrized: limits `(3900, 6000)` with a zone having 1 band price; `band_prices` without limits; limits `(6000, 3900)`; limits `(0,)`; negative band price → `TariffValidationError`. |
| unit | `tests/unit/test_tariff.py::test_replace_revalidates` | `dataclasses.replace(plan, zones=<overlapping zones>)` raises; `dataclasses.replace(plan, valid_from=date(2026, 7, 1))` returns a valid new plan and leaves the original unchanged. |
| unit | `tests/unit/test_tariff.py::test_models_frozen` | Assigning `plan.name = "x"` raises `dataclasses.FrozenInstanceError`. |
| unit | `tests/unit/test_tariff.py::test_schedule_sorts_and_rejects_duplicates` | Plans given as (2026-07-01, 2026-01-01) are stored in ascending order; two plans with the same `valid_from` → error; `TariffSchedule(())` → error. |
| unit | `tests/unit/test_tariff.py::test_schedule_plan_for` | Plans A (2026-01-01) and B (2026-07-01): `2025-12-31 → None`, `2026-01-01 → A`, `2026-06-30 → A`, `2026-07-01 → B`, `2030-01-01 → B`. |
| unit | `tests/unit/test_tariff.py::test_schedule_price_only_change` | Plan B is a `replace()` of A with only a new `valid_from` and new prices; both coexist; `plan_for` returns the right prices on each side of the switch. |
| unit | `tests/unit/test_tariff.py::test_schedule_plans_between` | Same A/B: `[2026-06-15, 2026-07-15) → (A, B)`; `[2026-07-02, 2026-08-01) → (B,)`; `[2025-06-01, 2025-07-01) → ()`; `[2026-07-01, 2026-07-01)` (empty range) → `()`. |
| unit | `tests/unit/test_presets.py::test_single_rate` | One zone `t1`; every hour 0–23 maps to it; price as given. |
| unit | `tests/unit/test_presets.py::test_ru_two_zone` | `day_price=Decimal("10.30")`, `night_price=Decimal("4.43")`: `t1` "Day" covers 16 hours (7–22), `t2` "Night" covers 8 hours (23, 0–6); prices match. |
| unit | `tests/unit/test_presets.py::test_ru_three_zone` | `t1` "Peak" = {7, 8, 9, 17, 18, 19, 20} (7 h); `t3` "Semi-peak" = {10…16, 21, 22} (9 h); `t2` "Night" = {23, 0…6} (8 h). |
| unit | `tests/unit/test_presets.py::test_presets_editable` | `dataclasses.replace` on a preset plan with a renamed zone (`replace(zone, name="Daytime")`) keeps the key and stays valid. |

## Acceptance criteria
Windows native:
- [ ] `uv run pytest -m unit` → all tests pass, including the task 001 guard tests
  (`test_engine_has_no_forbidden_imports` still passes with the new modules).
- [ ] `uv run pytest -m unit --cov=custom_components/energy_cost_stats/engine --cov-branch --cov-report=term-missing --cov-fail-under=95` → passes; `tariff.py` and `presets.py` are listed.
- [ ] `uv run ruff check .` and `uv run ruff format --check .` → exit 0.
- [ ] `uv run pyright custom_components/energy_cost_stats/engine tests/unit` → 0 errors (engine is strict).

General:
- [ ] `rg -n "float" custom_components/energy_cost_stats/engine` → matches only in comments/docstrings or the
  runtime `isinstance` rejection, never as a price type.
- [ ] `rg -n "homeassistant|zoneinfo|timezone" custom_components/energy_cost_stats/engine/tariff.py custom_components/energy_cost_stats/engine/presets.py` → no imports (this task is time-zone free).
- [ ] `docs/SPEC.md` §3 and §5 contain the decisions listed under "SPEC edits"; no other section changed.
- [ ] No files touched outside the "Files" list (the working tree may contain other agents' changes; do not
  modify or stage them).

## Out of scope
- Time zones, UTC hours, DST, groupings → **005-time-and-zones**.
- Consumption data, costs, report structure, rounding/serialization → **005/006**.
- Gap spreading, spike/negative filtering → **007-data-quality**.
- Volume-tier computation (only the reserved fields and their validation are in scope); weekday filters.
- Config flow / subentries (stage 2), storage format / JSON parsing of whole plans (stage 2 decides whether
  subentry data maps 1:1 to these dataclasses).
- Verifying the real RU zone hours of a specific region ("Verify RU zones before shipping", SPEC §3) — the
  presets are editable; the check belongs before the stage 2 release.

## Open questions
None — resolved by the human (2026-09-25):
- **Zone keys follow RU meter registers:** `t0` = single-rate, `t1` = day / peak, `t2` = night, `t3` = semi-peak
  (not time-of-day order). Keys are stable forever once users have data; display names are separate.
  Update the presets and SPEC §3 (it currently says single-rate uses `t1`).
- **Single-rate key is `t0`** (distinct column; never mixed with two-zone `t1` in multi-plan reports).
- **Prices must be ≥ 0**; a negative price is a validation error (0 = free hours is allowed).

<!-- Filled in by implementer -->
## Implementation notes
## Follow-ups
