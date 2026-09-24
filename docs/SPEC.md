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
Versioned **tariff plans**; a plan is valid from `valid_from` until the next plan's `valid_from` (no end date).
Any change (even price only) = new plan (UX: "duplicate current plan").
```json
{ "valid_from": "2026-07-01", "name": "Two-zone",
  "zones": [
    { "key": "t1", "name": "Day",   "price": 0.0, "periods": [["07:00","23:00"]] },
    { "key": "t2", "name": "Night", "price": 0.0, "periods": [["23:00","07:00"]] } ] }
```
- `key` is stable (t1/t2/t3); `name` is display-only (renaming must not break statistics).
- Validation: zones cover 24h exactly once; boundaries on whole hours (hourly statistics limit).
- Presets (editable after creation): single-rate; RU two-zone (day 7–23, night 23–7);
  RU three-zone (peak 7–10 & 17–21, semi-peak 10–17 & 21–23, night 23–7). Verify RU zones before shipping.
- Leave room for an optional weekday filter (foreign tariffs) and volume-tier rules later.

## 4. Report output
Rows per device (+ total, + optional "untracked" if a main meter is configured):
kWh per zone, price per zone, cost per zone, totals. Groupings: hour/day/week/month/custom range.

## 5. Known pitfalls to handle
- Statistics are UTC; zones are local time (`hass.config.time_zone`). DST days = 23/25 h.
- Current hour isn't compiled into LTS yet → use short-term (5-min) statistics for "today" (kept ~10 days).
- Plugs report on thresholds/intervals → boundary misattribution; offline gaps dump deltas into one hour.
- Filter negative/absurd deltas; don't silently show partial data as zero — return explicit partial/missing state.
- Avoid double counting when a device is nested under another meter (`included_in_stat`-style relation).
- Renamed entity_id → statistics stay on the old statistic_id.
- Recorder statistics API is internal and changes between HA releases — isolate it behind one adapter module.

## 6. Home Assistant compatibility
Minimum supported version: **2025.4**. Tested in CI against the minimum and the latest release.

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
