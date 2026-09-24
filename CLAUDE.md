# Energy Cost Stats — project context

Home Assistant custom integration (HACS) + Lovelace card.
Repo: `ha-energy-cost-stats` · Domain: `energy_cost_stats` · Card: `custom:energy-cost-stats-card`

## What it does
Calculates electricity **cost per device, split by tariff zones** (day/night, peak/semi-peak/off-peak),
for **any period**, using Home Assistant's **existing long-term statistics** — retroactively,
over the whole recorded history, **without creating per-device entities**.

Primary use case: ~20 Zigbee2MQTT smart plugs with energy monitoring (`total_increasing`, kWh),
Russian multi-zone tariffs (Moscow region), tariff prices change over time.

## Core principles (do not violate)
1. **No per-device entities.** Per-device data is exposed only via websocket API, a service with response,
   and the card. Allowed global entities: "Recalculate" button, current zone, current price (max ~3 total).
2. **Read, don't duplicate.** Source of truth is recorder long-term statistics (`statistics`, hourly `change`).
3. **Retroactive by design.** Any change to tariff plans must correctly re-price all past hours.
4. **Calculation engine is pure Python** (`engine/`), no `homeassistant` imports. Fully unit-tested.
5. **Tests first** for every feature. A task is done when tests are green and lint passes.

## Architecture
- `custom_components/energy_cost_stats/engine/` — pure logic: hourly deltas + tariff plans → report table.
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

## Tariff data model
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

## Report output
Rows per device (+ total, + optional "untracked" if a main meter is configured):
kWh per zone, price per zone, cost per zone, totals. Groupings: hour/day/week/month/custom range.

## Known pitfalls to handle
- Statistics are UTC; zones are local time (`hass.config.time_zone`). DST days = 23/25 h.
- Current hour isn't compiled into LTS yet → use short-term (5-min) statistics for "today" (kept ~10 days).
- Plugs report on thresholds/intervals → boundary misattribution; offline gaps dump deltas into one hour.
- Filter negative/absurd deltas; don't silently show partial data as zero — return explicit partial/missing state.
- Avoid double counting when a device is nested under another meter (`included_in_stat`-style relation).
- Renamed entity_id → statistics stay on the old statistic_id.
- Recorder statistics API is internal and changes between HA releases — isolate it behind one adapter module.

## Prior art (studied, don't reinvent — borrow ideas)
- `MacSiem/ha-smart-reports` — best statistics handling (local-calendar windows, DST, partial-data states,
  `included_in_stat`). Single flat price, fixed periods.
- `MacSiem/ha-energy-optimizer` — card on hourly LTS, peak/off-peak; 7/30 days only, no price history.
- `consultingtedds/ha-home-energy-advisor` — per-device cost with "Untracked" reconciliation;
  forward-only, ~13 entities per device.
- `BottlecapDave` Octopus Energy — Cost Tracker, peak/off-peak split, external statistics for Energy dashboard.
- `agustinscaz/energy-ledger-ha` — per-circuit cost from existing entities, forward-only (name taken).
Differentiator: full-history retroactive costing + versioned tariff plans + per-device zone table, zero entities.

## Tooling (planned)
- Scaffold from `ludeeus/integration_blueprint` (devcontainer, CI).
- CI: hassfest, HACS action, ruff, pytest.
- Tests: `pytest-homeassistant-custom-component`; seed statistics via `async_import_statistics`.
- Fixtures: real JSON exported from the author's HA via `recorder/statistics_during_period`.
- Card: Vite/Rollup build, Vitest with mocked `hass.callWS`.

## Roadmap
1. Engine + unit tests (zones, plan switching mid-period, gaps, resets, spikes, groupings, DST).
2. Config flow / options flow / tariff subentries.
3. Websocket `report` + service + integration tests.
4. Card on mocked data → then on a dev HA instance with real fixtures.
5. Stage 2: external statistics for Energy dashboard + "Recalculate" button.

## Agent workflow
- Main session = orchestrator (does not read code deeply).
- `planner` (opus): writes task spec to `tasks/NNN-name.md` — goal, files, tests to write, done criteria, out of scope.
- `implementer` (sonnet): reads only CLAUDE.md + task file; tests first; returns one-line status.
- `reviewer` (fresh context): checks `git diff` against the task spec and runs tests; writes `tasks/NNN-review.md`.
- Max 2 review iterations, then escalate to planner/human.