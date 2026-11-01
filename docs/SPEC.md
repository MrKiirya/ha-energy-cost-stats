# Energy Cost Stats — product specification

Home Assistant custom integration (HACS) + Lovelace card.
Repo: `ha-energy-cost-stats` · Domain: `energy_cost_stats` · Card: `custom:energy-cost-stats-card`

## 1. What it does
Calculates electricity **cost per device, split by tariff zones** (day/night, peak/semi-peak/off-peak),
for **any period**, using Home Assistant's **existing long-term statistics** — retroactively,
over the whole recorded history, **without creating per-device entities**.

Typical use case: a home with many smart plugs / energy meters (e.g. Zigbee2MQTT, `total_increasing`, kWh)
on a multi-zone time-of-use tariff whose prices change over time — for example, Russian two- and
three-zone residential tariffs.

## 2. Architecture
- `custom_components/energy_cost_stats/engine/` — pure logic: hourly deltas + tariff plans → report table.
  No `homeassistant` imports.
- `custom_components/energy_cost_stats/recorder_adapter.py` (name TBD) — the **only** module that touches
  the recorder statistics API (see §6).
- Integration layer:
  - config flow (setup) + options flow (select energy entities, multi-select, `device_class: energy`);
  - tariff plans stored as **config subentries** (MVP); may move to `helpers.storage.Store` + card editor later;
  - websocket command `energy_cost_stats/report` (period, grouping, entities) → aggregated table;
  - service `energy_cost_stats.get_report` with `SupportsResponse` (for automations/scripts).
- Settings (single instance, `single_config_entry`): all settings live in `entry.options` (`entry.data` is empty):
  `time_zone`, `spike_limit` (decimal string, `null` = check off), `device_spike_limits` (entity id -> decimal
  string; missing = use the global limit, `null` = off for that device) and `entities`. Decimals are strings
  without exponent. The time zone is stored explicitly (default: the Home Assistant time zone at setup) and does
  not follow later Home Assistant changes, so retroactive prices never move silently. The config flow asks for
  time zone and spike limit; the options flow edits them, selects the energy sensors and optionally sets
  per-device spike limits (empty = global, `0` = off). Any options or subentry change reloads the entry through a
  single update listener (not `OptionsFlowWithReload`, which is missing in the minimum HA version). The
  reloaded entry holds the parsed tariff schedule (`None` when no plan exists), so adding, editing or deleting
  a plan re-prices all past hours.
- Card (Lit + TypeScript): renders the table; served by the integration itself (static path + extra JS),
  so users install one HACS repo.
- Stage 2 (optional): write **4 external statistics** series for the Energy dashboard:
  `energy_cost_stats:<zone>_kwh` and `energy_cost_stats:<zone>_cost` per zone (day/night → 4 series).
  Optional toggle (off by default) for per-device cost series. External statistics are not entities.

## 3. Tariff data model
Versioned **tariff plans**. `valid_from` is a *local* calendar date; the plan applies from local midnight
of that date until the next plan's `valid_from`; there is no end date. Any change, even price only, is a
new plan (UX: "duplicate current plan"). Two plans with the same `valid_from` are invalid.
Storage: one config subentry of type `tariff_plan` per plan, with `unique_id` = `valid_from` (ISO date; the
flow reports a duplicate date as a field error) and title `"<valid_from> · <name>"`. The subentry data is the
JSON below, with **prices as decimal strings** (scale kept, no exponent; money never passes through `float`),
period end of day written as `"24:00"`, and reading is strict (unknown keys and wrong types are rejected).
`volume_band_limits_kwh` and `band_prices` are written only when non-empty. The zone set of a plan is fixed
by its preset or the copied plan (the UI edits zone names, prices, periods, plan name and `valid_from`, but
does not add, remove or re-key zones).
```json
{ "valid_from": "2026-07-01", "name": "Two-zone",
  "zones": [
    { "key": "t1", "name": "Day",   "price": "10.30", "periods": [["07:00","23:00"]] },
    { "key": "t2", "name": "Night", "price": "4.43", "periods": [["23:00","07:00"]] } ] }
```
- Periods are half-open whole-hour intervals `[start, end)`; `end < start` crosses midnight (e.g.
  `["23:00","07:00"]` = hours 23, 0, 1, ..., 6); `00:00`/`24:00` as **end** means end of day; the full
  day is `00:00–24:00`. Boundaries are whole hours only (hourly statistics limit).
- `key` is stable (used in statistics and reports) and follows the labels on Russian multi-tariff meters:
  `t0` = single-rate (a distinct key, never mixed with the two-zone `t1` in multi-plan reports), `t1` =
  day/peak, `t2` = night, `t3` = semi-peak. `name` is display-only (renaming must not break statistics).
- Prices are `Decimal` and must be `>= 0` (0 = free hours is allowed); money is `Decimal` everywhere in
  the engine, never `float`; rounding happens only at report output (see §4).
- Validation: zones cover 24h exactly once (no gap, no overlap); boundaries on whole hours.
- Presets (editable after creation): single-rate (`t0`); RU two-zone (`t1` day 7–23, `t2` night 23–7);
  RU three-zone (`t1` peak 7–10 & 17–21, `t3` semi-peak 10–17 & 21–23, `t2` night 23–7). Generic example
  used throughout the tests: two-zone, day `10.30`, night `4.43` per kWh. Verify RU zones before shipping.
- Leave room for an optional weekday filter (foreign tariffs) later.
- Volume tiers ("consumption ranges"): RU residential tariffs sometimes price monthly household kWh in
  bands (e.g. ≤ 3900, 3901–6000, > 6000 kWh/month). The model reserves two optional fields for this,
  non-breaking to add later: `TariffPlan.volume_band_limits_kwh` (ascending upper limits of bands 1..n,
  band n+1 unbounded) and `Zone.band_prices` (prices for bands 2..n+1; band 1 is `Zone.price`). Stage 1
  uses only the first-band price (`Zone.price`) everywhere; band computation is not implemented. Future
  method (not implemented yet): compute the household's monthly bill by bands, derive a blended per-zone
  price for that month, apply it to all devices for that month.

## 4. Report output
Rows per device (+ total, + optional "untracked" if a main meter is configured):
kWh per zone, price per zone, cost per zone, totals. Groupings: hour/day/week/month/custom range.

Semantics (engine, `build_report`; details in tasks/006-pricing-and-grouping.md):
- **Zones.** `Report.zones` is the union of zone keys over the plans in force in the window, in order of
  first appearance (plans chronological, zones in declaration order), e.g. `t0` then two-zone gives
  `t0, t1, t2`. A zone's name is the one from the latest plan containing the key. Every row has one cell
  per `Report.zones` entry, in the same order.
- **Cells.** `kwh`/`cost` are exact sums over counted (measured + estimated) hours in that zone; `None` if
  there are none (a missing or not-in-force zone), never a silent `0`; a measured `0` stays `0`. `price`
  comes from the schedule: the single zone price in the bucket, `None` if several prices applied (plan
  switch with a price change inside the bucket) or the zone has no hour in the bucket.
- **Rows.** `kwh` = all counted kWh (priced + unpriced), `None` if no hour was counted. `cost` = sum of
  cell costs, `None` if no counted hour was priced (unpriced-only data means "unknown", not "free").
  `unpriced_kwh` = counted kWh before the first plan. Estimated/excluded kWh are reported separately;
  excluded kWh is not part of `kwh` or `cost`. Coverage counts measured/estimated/excluded/missing hours.
- **Total row.** Sum of the device rows, skipping `None` (`None` if all are); coverage is summed. `totals`
  is the whole-window bucket, computed independently of the other buckets.
- **Rounding.** The engine keeps exact `Decimal`s and never rounds; totals are exact sums, not sums of
  rounded cells. Rounding happens only at output (`engine/rounding.py`, `ROUND_HALF_UP`): money 2
  decimals, kWh 3, prices 4. A displayed total may therefore differ from the sum of the displayed cells
  by 0.01; this is accepted.

## 5. Known pitfalls to handle
- Engine input is hourly deltas keyed by **UTC hour start**; zones, plan switches and groupings use local
  time (IANA tz via `zoneinfo`); DST days have 23/25 hours and are handled; weeks start on Monday; months
  are local calendar months; groupings: hour/day/week/month/custom range (+ totals).
- Known limitation: **non-whole-hour UTC offsets** (e.g. `Asia/Kolkata`, UTC+05:30) are accepted, not
  rejected. Each UTC hour is attributed to the local hour and date its start falls in, so for such zones
  the local day and every zone/plan boundary effectively shift by the offset's minute remainder (e.g. a
  local day starting at `xx:30` instead of `xx:00`, and a zone boundary configured for local `07:00` is
  applied from the UTC hour whose local start is `07:30`). No error is raised; this is by design, not a bug.
- Current hour isn't compiled into LTS yet → use short-term (5-min) statistics for "today" (kept ~10 days).
- Data quality (implemented in task 007, `engine/quality.py`). Missing data is always explicit
  (missing/partial), never a silent zero. Rules, all keyed on UTC hours:
  - A gap is an **absence of keys** in the series, never a run of zeros; a `0` delta is a measured 0.
  - Every key `k` with delta `D` defines a **span**: the UTC hours `(p, k]`, where `p` is the previous key
    in sorted order (inside or outside the window), so `n = (k - p) / 1 h`. `n == 1` is a contiguous hour;
    `n > 1` is a gap of `n - 1` hours plus the catch-up hour `k`. Gap length is not capped.
  - The **earliest key** has no known predecessor: its span is just its own hour, it is measured as-is and
    spike-checked, and all earlier hours stay missing. Trailing gaps with no catch-up also stay missing.
  - `D < 0` is excluded (`EXCLUDED_NEGATIVE`; this check cannot be disabled and wins over the spike
    check). Otherwise `D > limit * n` is excluded (`EXCLUDED_SPIKE`): the limit (default 4 kWh/h ≈ a 16 A
    socket at 3.7 kW; global setting, per-device override or disable, `None` = off) is compared with the
    per-hour average after spreading, strictly. For a rejected delta only the catch-up hour is EXCLUDED;
    the gap hours stay missing.
  - An accepted delta with `n > 1` (including `D == 0`) is spread: `q = D / n` rounded down to `1E-20`
    for each gap hour, the remainder `D - (n - 1) q` goes to the catch-up hour; all `n` hours are flagged
    "estimated" and priced in their own zones. Sums stay exact.
  - Each ESTIMATED / EXCLUDED_* `QualityIssue` is clipped to the report window (start, end and kWh cover
    only in-window hours), so issues sum to the row totals. One ESTIMATED issue per spread span, one
    EXCLUDED issue per rejected in-window delta (consecutive ones are not merged).
  - The value of any hour depends only on the series, never on the window (**window independence**).
- HA recorder facts behind this (checked on core `dev` and 2025.4.0; sources:
  [sensor/recorder.py](https://github.com/home-assistant/core/blob/dev/homeassistant/components/sensor/recorder.py),
  [recorder/statistics.py](https://github.com/home-assistant/core/blob/dev/homeassistant/components/recorder/statistics.py)):
  - An unavailable `total_increasing` sensor writes **no** statistics row (not even `change 0`); hours
    without valid states have no hourly row.
  - The first row after an outage is relative to the **last stored row** (`sum` is seeded from it), so it
    carries the whole outage's consumption: that is the catch-up delta.
  - A drop to below `0.9 *` the previous state is a reset (sum continues from 0); a smaller drop appears as
    a negative change.
  - `change` is `sum - previous row's sum`; a row with a `NULL` sum has `change = None`.
- Stage 3 adapter requirement: pass, per device, at least the last key before the window and the first
  key after it (look-back / look-ahead), and drop rows with `change is None` (they become missing).
  Without the look-back key the engine cannot see a gap that started before the window.
- Known limitations: a device that restarts with a counter reset during an outage loses the energy used
  before the restart (HA counts only the new value); a sensor that stays "available" with a stale value
  yields measured `0` rows and then one large delta, which the engine cannot see as a gap (the spike
  check may exclude it).
- Known limitation: plugs that report late across a zone boundary put some kWh into the wrong zone
  (boundary misattribution). The engine cannot detect this from hourly statistics.
- Meter resets of `total_increasing` sensors are already handled by HA when it compiles the statistics
  `change`. Small drops (< 10 %) are not treated as resets and appear as negative deltas (excluded above).
- Avoid double counting when a device is nested under another meter (`included_in_stat`-style relation).
- Renamed entity_id → statistics stay on the old statistic_id.
- Recorder statistics API is internal and changes between HA releases — isolate it behind one adapter module.
- Out of stage 1: main meter / "untracked" row, nested-meter de-duplication, short-term statistics for the
  current hour (the engine accepts whatever hours it is given).

## 6. Home Assistant compatibility
Minimum supported version: **2025.4**. Tested in CI against the minimum and the latest release
(GitHub Actions matrix: py3.13/HA 2025.4.0, py3.14/latest).
The two are pinned via `pytest-homeassistant-custom-component` (which pins an exact `homeassistant`
version per release) plus version markers in `pyproject.toml`'s `ha` dependency group: `python_version < '3.14'`
resolves PHCC `0.13.232` → HA `2025.4.0`; `python_full_version >= '3.14.2'` resolves latest PHCC → latest HA.
`[tool.uv] environments` restricts resolution to that same split, so uv refuses to sync at all on
3.14.0/3.14.1 (the gap between the two markers) instead of silently installing no HA, and a CI step asserts the resolved `homeassistant.const`
version against the expected value for each matrix leg, so a silently-empty `ha` group fails loudly instead
of looking green.

| Feature we rely on | Since | Notes |
|---|---|---|
| `statistics_during_period(..., types={"change", ...})` | ≤ 2023.x | Reading side; stable. |
| Config subentries | 2025.3 | Hard floor: tariff plans are subentries. |
| `StatisticMeanType` / `mean_type` in metadata | 2025.4 | Writing external statistics (stage 2). |
| `unit_class` in statistics metadata | 2025.11 | Adapter passes it only when supported. |
| `has_mean` removed; `mean_type` + `unit_class` mandatory for writes | 2026.11 | Adapter must already comply. |

Reading metadata: ignore unknown fields (`mean_type`, `unit_class`, deprecated `has_mean`).
Reference: https://developers.home-assistant.io/blog/2025/10/16/recorder-statistics-api-changes/

## 7. Prior art (studied, don't reinvent — borrow ideas)
- `MacSiem/ha-smart-reports` — best statistics handling (local-calendar windows, DST, partial-data states,
  `included_in_stat`). Single flat price, fixed periods.
- `MacSiem/ha-energy-optimizer` — card on hourly LTS, peak/off-peak; 7/30 days only, no price history.
- `consultingtedds/ha-home-energy-advisor` — per-device cost with "Untracked" reconciliation;
  forward-only, ~13 entities per device.
- `BottlecapDave` Octopus Energy — Cost Tracker, peak/off-peak split, external statistics for Energy dashboard.
- `agustinscaz/energy-ledger-ha` — per-circuit cost from existing entities, forward-only (name taken).

Differentiator: full-history retroactive costing + versioned tariff plans + per-device zone table, zero entities.

## 8. Roadmap
0. Project setup: scaffold, devcontainer, CI, branch protection.
1. Engine + unit tests (zones, plan switching mid-period, gaps, resets, spikes, groupings, DST).
2. Config flow / options flow / tariff subentries.
3. Websocket `report` + service + integration tests.
4. Card on mocked data → then on a dev HA instance with real fixtures.
5. Stage 2: external statistics for Energy dashboard + "Recalculate" button.
