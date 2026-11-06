# Configuration design (v2)

Status: agreed design for tasks 017–024. `docs/SPEC.md` describes what is implemented; this document describes
where the configuration is going, why, and how the work is split. When a task lands, SPEC is updated and the
matching section here may be trimmed.

## Goals
- Tariffs are named and **versioned**: prices (and sometimes zone hours) change over time, and every past hour is
  priced with the version in force at that hour.
- Which tariff is **applied** is a separate history, so switching tariffs on a date is a first-class operation.
- Any other tariff can be **compared** over the same consumption ("would single-rate have been cheaper?").
- **One model, two front ends:** everything configurable in the UI is configurable in YAML with exactly the same
  shape, and the UI can export it as YAML.

## Full configuration (YAML)
```yaml
energy_cost_stats:
  time_zone: Europe/Moscow            # optional; default: HA's time zone at first setup (stored explicitly)
  spike_limit: "4"                    # kWh per hour; null disables the spike check

  panel:                              # optional sidebar entry with the date picker and the card
    show: true
    title: Energy cost
    icon: mdi:cash-multiple

  sensors:
    mode: energy_dashboard            # energy_dashboard | filter
    # mode: filter only
    include: all                      # `all` (every eligible sensor) or a target:
    # include:
    #   entity_id: [sensor.plug_01_energy]
    #   device_id: [...]
    #   area_id: [kitchen]
    #   floor_id: [...]
    #   label_id: [cost_tracking]
    #   entity_globs: ["sensor.*_plug_*_energy"]
    exclude:                          # both modes; exclude wins over include
      entity_id: [sensor.main_meter_t1, sensor.main_meter_t2]
      entity_globs: ["sensor.sub_meter_*"]
      label_id: [meter]
    overrides:
      sensor.water_heater_energy:
        spike_limit: "6"              # null = no spike check for this sensor

  tariffs:
    - id: two_zone                    # ^[a-z0-9_]{1,32}$, stable, referenced elsewhere
      name: Two-zone                  # display name, any language, may change
      versions:
        - valid_from: 2026-01-01
          preset: ru_two_zone         # single_rate | ru_two_zone | ru_three_zone
          prices: { t1: "8.10", t2: "3.20" }
          # hours: { t1: "07:00-23:00", t2: "23:00-07:00" }   # per-zone override of preset hours
        - valid_from: 2026-07-01      # inherits zones (keys, names, hours) from the previous version
          prices: { t1: "8.75", t2: "3.45" }
    - id: three_zone
      name: Three-zone
      versions:
        - valid_from: 2026-07-01
          zones:                      # explicit zones instead of a preset
            - { key: t1, name: Peak,      price: "10.20", hours: "07:00-10:00, 17:00-21:00" }
            - { key: t3, name: Semi-peak, price: "8.75",  hours: "10:00-17:00, 21:00-23:00" }
            - { key: t2, name: Night,     price: "3.45",  hours: "23:00-07:00" }
    - id: single_rate
      name: Single-rate
      versions:
        - valid_from: 2026-07-01
          preset: single_rate
          prices: { t0: "7.40" }

  applied:                            # short form: `applied: two_zone`
    - { from: 2026-01-01, tariff: two_zone }
    # - { from: 2027-03-01, tariff: three_zone }

  compare: [single_rate, three_zone]  # optional; default: every tariff never applied
```

### Tariffs
- `id` is the stable key used by `applied`, `compare`, the card and (stage 5) statistic ids; `name` is display
  only. Zones follow the same split: `key` (`t0` single-rate, `t1` day/peak, `t2` night, `t3` semi-peak — the
  registers of multi-tariff meters) and `name`.
- A **preset** is a shortcut that fills zones: `single_rate` (one zone, all day), `ru_two_zone` (day 07–23,
  night 23–07), `ru_three_zone` (peak 07–10 & 17–21, semi-peak 10–17 & 21–23, night 23–07). Regional variants
  override `hours`; anything else uses explicit `zones`. A preset without hours cannot exist — the hours are what
  defines the zones.
- **Versions** are sorted by `valid_from` with distinct dates. The first version needs `preset` or `zones`; a
  later version without either inherits the previous zones and gives `prices` for exactly those keys (and may
  override `hours`). `preset` and `zones` are mutually exclusive.
- **Hours** are `"HH:MM-HH:MM, ..."` in whole hours (`24:00` = end of day); a version covers each hour of the day
  exactly once.
- **Prices** are decimal strings (money never passes through a float). The YAML layer also accepts numbers and
  converts them; quoting is recommended.

### Applied history and comparison
- `applied` entries are sorted with distinct `from` dates; each tariff must have a version valid on its `from`
  date. Hours before the first `from` are unpriced; no `applied` means every hour is unpriced.
- The real cost uses, for each applied interval, the version in force at its start (re-dated to that start) and
  the later versions inside the interval.
- A compared tariff is priced with its own versions only. `compare` defaults to every tariff that never appears
  in `applied`.

### Sensors
- **Eligible** sensors (for `all`, globs, areas, …): `device_class: energy`, unit Wh/kWh/MWh, cumulative
  (`total` / `total_increasing`), with long-term statistics.
- `mode: energy_dashboard` takes the individual devices from the Energy dashboard settings and respects their
  "upstream device" (`included_in_stat`) to avoid double counting. It is the default at first setup when the
  Energy dashboard has individual devices; otherwise the default is `filter` with `include: all`.
- `mode: filter`: `include` is `all` or a target (`entity_id`, `device_id`, `area_id`, `floor_id`, `label_id`, as
  resolved by Home Assistant's target helpers) plus `entity_globs`; `exclude` has the same keys and wins.
  Matching is dynamic: a new eligible sensor is picked up without editing the configuration.
- `overrides` holds per-sensor parameters (currently `spike_limit`), independent of how sensors are selected.

### Modes
- **YAML mode:** the `energy_cost_stats:` block is present in `configuration.yaml` (or a package). The UI shows
  the configuration read-only; edits go to the file and are applied with `energy_cost_stats.reload` (no
  restart). Validation errors are reported as repairs and in the log.
- **UI mode:** no YAML block; everything is configured through the forms below. "Export to YAML" produces the
  block above for moving to YAML mode.
- Mixing both sources is not supported (one source of truth).

## UI
### Integration page
One config subentry per tariff, versions inside:
```
Energy Cost Stats                                            ⋮   ⚙ Configure
 ├ Two-zone      Tariff · 2 versions · now 8.75 / 3.45 · applied         ⚙
 ├ Three-zone    Tariff · 1 version  · now 10.20 / 8.75 / 3.45           ⚙
 └ Single-rate   Tariff · 1 version  · now 7.40                          ⚙
⋮ → "Add tariff"
```
Home Assistant lists subentries in one list (creation order) with the type label under the title; a subentry's
type cannot change, which is why "applied" is a setting and not a subentry type.

### Add tariff
1. **New tariff:** name; base: single-rate / two-zone (RU) / three-zone (RU) / custom zones / copy of an existing
   tariff. Custom zones asks for the number of zones and their keys and names.
2. **ID:** prefilled from the name (transliterated slug), editable. Forms cannot update one field while another is
   typed, so the ID is shown on the second step.
3. **First version:** `valid_from`; one collapsible section per zone with name, price and hours (prefilled from
   the preset). Errors are shown at the field (uncovered hour, overlap, invalid price).

### Tariff (⚙ on its row)
Menu: **New version** (date + prices prefilled from the latest version; hours in a collapsed section) ·
**Edit version** (choose a version → same form + "delete this version") · **Rename** (name; ID with automatic
update of references in `applied` / `compare`). The menu description shows a table of versions. Deleting a tariff
uses Home Assistant's own action and is refused while the tariff is applied.

### Configure (options)
Menu:
- **Sensors** — mode, include / exclude (Home Assistant's target and entity selectors, globs as text), overrides,
  and a preview "N sensors in the calculation".
- **Applied tariff** — one tariff, or "changed over time": add / delete changes (date + tariff), with a table of
  the history in the description.
- **Compare** — tariffs to compare (default: all never applied).
- **General** — time zone, spike limit, "show in sidebar" (title, icon).
- **Export to YAML** — the generated block in the step description, ready to copy.

In YAML mode every step shows the current values read-only with a hint to edit the file and reload.

## Decisions and rejected alternatives
- **A tab inside the built-in Energy panel** — not possible cleanly: the panel is generated by a hard-coded
  strategy (overview / electricity / gas / water / now) and only `hidden_cards` is configurable. Patching the
  frontend's internal strategy would break on updates. A sidebar panel of the integration is used instead.
- **Tariff scenarios in the card's YAML** (`compare:` on the card) — withdrawn: prices would be duplicated in
  every dashboard and automations could not see them. Tariffs and comparison live in the integration.
- **"Tariff grid"** (one record per period with the prices of all variants) — rejected: it would replace the
  per-tariff model with a region-specific one.
- **Automatic exclusion of Energy dashboard sources** — dropped: the `energy_dashboard` mode covers that case and
  `filter` mode excludes explicitly.
- **`domains` in the sensor filter** — not needed: eligible sensors are energy sensors.
- **Card-only implementation** (no integration) — rejected: the engine, the action for automations and the
  stage 5 statistics need the backend.

## Reserved extensions (not implemented)
- **Weekday-dependent hours:** `hours` becomes either a string (all days, valid as today) or a mapping
  `{mon-fri: "07:00-23:00", sat-sun: "00:00-24:00"}` (`mon`…`sun` and ranges). Existing configurations stay valid;
  the engine's hour-to-zone lookup becomes a day-and-hour lookup. Risk: low. Until then the mapping form is
  rejected with a clear message.
- **Volume bands** (monthly consumption tiers): a zone price becomes a string or a list per band, plus
  `volume_band_limits_kwh` on the version and a `sensors.main_meter` for the household total. The cost of a day
  depends on the whole month's consumption, so a running month is provisional. Risk: medium (engine work); the
  model already reserves `volume_band_limits_kwh` / `band_prices`.

## Tasks
| Task | Scope |
|---|---|
| 017 | Tariff model: tariffs with versions, `applied`, `compare`; effective and comparison schedules; storage as `tariff` subentries; migration from `tariff_plan`; `energy_cost_stats/compare` |
| 018 | Tariff forms: add tariff (presets, custom zones, copy), new / edit / delete version, rename with ID |
| 019 | Options menu: applied tariff (with history), compare, general (incl. sidebar flag) |
| 020 | Sensor selection: modes, include / exclude with targets and globs, overrides, dynamic matching, preview |
| 021 | YAML mode: schema (numbers → decimal strings), read-only UI, `reload` action, repairs, export to YAML |
| 022 | Card: comparison section using the integration's tariffs; full-width default in sections views |
| 023 | Sidebar panel: integration panel with Home Assistant's energy date picker and the card |
| 024 | Russian translations of the forms |
