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
- Card (Lit + TypeScript): renders the table; served by the integration itself (static path + extra JS),
  so users install one HACS repo.
- Stage 2 (optional): write **4 external statistics** series for the Energy dashboard:
  `energy_cost_stats:<zone>_kwh` and `energy_cost_stats:<zone>_cost` per zone (day/night → 4 series).
  Optional toggle (off by default) for per-device cost series. External statistics are not entities.

## 3. Tariff data model
Versioned **tariff plans**. `valid_from` is a *local* calendar date; the plan applies from local midnight
of that date until the next plan's `valid_from`; there is no end date. Any change, even price only, is a
new plan (UX: "duplicate current plan"). Two plans with the same `valid_from` are invalid.
```json
{ "valid_from": "2026-07-01", "name": "Two-zone",
  "zones": [
    { "key": "t1", "name": "Day",   "price": 0.0, "periods": [["07:00","23:00"]] },
    { "key": "t2", "name": "Night", "price": 0.0, "periods": [["23:00","07:00"]] } ] }
```
- Periods are half-open whole-hour intervals `[start, end)`; `end < start` crosses midnight (e.g.
  `["23:00","07:00"]` = hours 23, 0, 1, ..., 6); `00:00`/`24:00` as **end** means end of day; the full
  day is `00:00–24:00`. Boundaries are whole hours only (hourly statistics limit).
- `key` is stable (used in statistics and reports) and follows the labels on Russian multi-tariff meters:
  `t0` = single-rate (a distinct key, never mixed with the two-zone `t1` in multi-plan reports), `t1` =
  day/peak, `t2` = night, `t3` = semi-peak. `name` is display-only (renaming must not break statistics).
- Prices are `Decimal` and must be `>= 0` (0 = free hours is allowed); money is `Decimal` everywhere in
  the engine, never `float`; rounding to 2 decimals happens only at report output.
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
- Data quality (implemented in task 007): an offline gap followed by a catch-up delta is spread evenly over
  the gap hours plus the catch-up hour, each hour priced in its own zone, flagged "estimated". Negative
  deltas and deltas above a per-device limit (default 4 kWh/h ≈ a 16 A socket at 3.7 kW; global setting;
  per-device override or disable) are excluded and reported (count, kWh, when), flagged "excluded".
  Missing data is always explicit (missing/partial), never a silent zero.
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
