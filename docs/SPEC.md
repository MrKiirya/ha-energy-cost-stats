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
- `custom_components/energy_cost_stats/engine/` — pure logic: hourly deltas + tariff schedule → report table.
  No `homeassistant` imports.
- `custom_components/energy_cost_stats/recorder_adapter.py` — the **only** module that touches
  the recorder statistics API (see §6). It returns one engine `DeviceSeries` per statistic id (hourly kWh
  `change`, with neighbour keys, see §5) plus a per-id status (`ok` / `no_statistics` / `unsupported`).
- Integration layer:
  - config flow (setup) + options flow (sensor selection by Energy dashboard devices or include / exclude rules,
    previewed before saving);
  - tariffs stored as **config subentries** (one per tariff, §3); the applied history and the comparison list live
    in `entry.options`;
  - websocket command `energy_cost_stats/report` (period, grouping, entities) → aggregated table;
  - service `energy_cost_stats.get_report` with `SupportsResponse.ONLY` (for automations/scripts);
  - websocket command `energy_cost_stats/compare` (period, optional entities and tariffs) → the actual report
    plus the same consumption priced with other tariffs (§4.2).
  - `report` and `get_report` are registered once in `async_setup` and take the same fields: `start` and `end`
    (required; a local date `YYYY-MM-DD` = local midnight, or an ISO datetime; a datetime without offset is read in
    the settings time zone and must fall on a whole UTC hour; `end` is **exclusive**), `grouping` (`hour` / `day` /
    `week` / `month` / `total`) and optional `entities` (omitted or empty = all selected sensors, see below; otherwise a
    subset of the selected ones, in the order given, duplicates dropped). There is no time-zone field: the time
    zone comes from the settings. A date bound in a time zone with a non-whole-hour offset is rounded up to the
    first UTC hour starting on or after local midnight (§5). Hourly reports are limited to 31 days (745 buckets),
    other groupings to 3660 days.
  - Both return the same JSON document as §4 (decimals are strings; use `| float` in templates). Errors:
    `not_loaded` (no loaded entry), `invalid_period`, `period_too_long`, `unknown_entity`, plus `unknown_tariff` for
    `compare` (websocket error codes; the service raises a translated `ServiceValidationError` with the same key);
    malformed fields are rejected by the schema (`invalid_format` / `vol.Invalid`). The websocket command needs no
    admin rights (read-only).
- Settings (single instance, `single_config_entry`): all settings live in `entry.options` (`entry.data` is empty):
  `time_zone`, `spike_limit` (decimal string, `null` = check off), `sensors` (the selection, below), `applied` (list of
  `{from, tariff}`, §3; omitted = nothing applied), optional `compare` (list of tariff ids, §3) and optional
  `panel` (`{show, title, icon}`, the planned sidebar entry; stored only, it has no effect yet). Decimals are
  strings without exponent. The time zone is stored explicitly (default: the Home Assistant time zone at setup) and does
  not follow later Home Assistant changes, so retroactive prices never move silently. The config flow asks for
  time zone and spike limit. "Configure" opens an options menu: **Sensors** (selection and per-sensor spike limits,
  below), **Applied tariffs** (a table of the history; use one tariff
  for everything, add a change, re-date / re-assign / delete a change), **Tariff comparison** (default set or an
  explicit list) and **General settings** (time zone, spike limit, sidebar options). Every leaf form re-reads
  the current options on submit and saves the full option set. The forms that change the tariff document
  (applied history, comparison) first check the candidate with the same document the setup builds
  (`settings.tariff_document` + `config_from_data`), so a stored configuration always sets up; applied-history
  problems surface as field errors `duplicate_from`, `no_version`, `unknown_tariff`, and a problem in an entry
  the user did not just edit (a broken stored history) as a form error with the engine message. The applied and
  comparison steps abort with `no_tariffs` while there is no tariff.
  Any options or subentry change reloads the entry through a single update listener (not
  `OptionsFlowWithReload`, which is missing in the minimum HA version). The
  reloaded entry holds the parsed tariff configuration and the effective schedule (`None` when nothing is
  applied), so adding, editing or deleting a tariff or changing the applied history re-prices all past hours.
  The config entry has `VERSION` 3. Version 1 (one `tariff_plan` subentry per plan) is migrated at startup (§3);
  version 2 (`entities` + `device_spike_limits`) becomes `sensors`: a non-empty `entities` list becomes a `filter`
  selection of exactly those ids (`include.entity_id`), an empty one the first-setup default, every per-device
  limit an override (a major bump, because the old keys are removed). An entry with a newer version fails to set up.
  Before reloading, the update listener reconciles the options with the tariff subentries (Home Assistant lets users
  delete any subentry): a deleted tariff is removed from `applied` (the previous item continues over the freed
  period, equal neighbours merge; when the first item is removed the next one takes over its start if that tariff
  has a version valid then, otherwise it keeps its own date and earlier hours stay unpriced; if nothing remains
  applied but tariffs do, the first remaining tariff is applied from its first version; no tariffs left means
  nothing applied) and from an explicit `compare` list; the first tariff added to an entry without tariffs is applied
  from its first version.
- **YAML mode** (task 021). An `energy_cost_stats:` block in `configuration.yaml` (or a package, or a file pulled
  in with `!include`) with exactly the document shape the UI edits (docs/CONFIG-DESIGN.md "Full configuration
  (YAML)") makes YAML the single source of truth. The block is **imported into the config entry**, not read beside
  it: it is validated strictly (`yaml_config.document_from_yaml`, which normalizes and then runs
  `settings_from_options` and `config_from_data`), then written as the entry options and one `tariff` subentry per
  tariff (matched by tariff id: updated, added, removed), so reports, websocket, service and card keep one code
  path and the integration page lists the YAML tariffs. There is no entry version bump. YAML mode is a runtime
  flag (block present at the last load), not stored.
  - Top-level keys: `time_zone` (default: the existing entry's, else the Home Assistant time zone), `spike_limit`
    (default `4`, `null` = off), `panel`, `sensors` (default: the first-setup rule evaluated at each load; in
    `filter` mode a missing `include` means `all`, `exclude` / `overrides` default to empty), `tariffs`, `applied`
    (list, or `applied: <id>` = from that tariff's first version), `compare`. Unknown keys are errors. An empty
    block is valid (all defaults, no tariffs).
  - **Applying.** At startup (`async_setup`) and by the admin action `energy_cost_stats.reload` (no fields; also
    listed in Developer tools, YAML; registered even without a block, so a block added later is picked up without a
    restart; it re-reads `configuration.yaml` with `async_integration_yaml_config`). A new block with no entry
    starts an `import` config flow (`async_step_import` creates the entry with the options); an existing entry is
    synced in `async_setup_entry` before its options are parsed (and reloaded after a reload action). The first
    replacement of a configuration made in the UI logs a warning; use **Export to YAML** first to keep a copy.
    Removing the block and reloading leaves the last YAML values in the entry and makes it editable in the UI.
  - **Invalid block** (syntax, unknown key, failed validation, unknown time zone). `CONFIG_SCHEMA` is deliberately
    lenient (`{Optional(DOMAIN): object}`, extra keys allowed): when it raises, Home Assistant skips `async_setup`
    and the config entries of the domain altogether (§6). The integration keeps running with the last valid
    configuration; the error is shown as the repair issue `invalid_yaml` (not fixable, re-created on every failed
    load), in the log, in the options flow, and for a reload as the action error (`yaml_invalid`). Fixing the block
    and running the action clears the issue. While the block is invalid the update listener keeps the usual options
    reconciliation, so deleting a tariff on the integration page does not break the entry; the next valid load
    restores the tariff from YAML.
  - **Read-only UI.** `async_step_user` and the tariff subentry flows abort with `yaml_mode`; the options flow opens
    the menu `yaml_mode` (time zone, spike limit, compared tariffs, sidebar and the last load error in the
    description) with `sensors_view`, `applied_view` (the resolved selection and the history table) and
    `export_yaml`; no step writes options. The update listener skips the options reconciliation in YAML mode and
    only reloads, so a tariff subentry deleted from the integration page comes back.
  - **Export to YAML** (options menu in both modes): `yaml_config.export_document` + `homeassistant.util.yaml.dump`
    render the stored configuration as an `energy_cost_stats:` block in the step description (key order
    `time_zone`, `spike_limit`, `panel`, `sensors`, `tariffs`, `applied`, `compare`; dates unquoted, prices and
    limits quoted strings). The block loads back to identical options and tariffs.
- **Sensor selection** (`entry.options["sensors"]`, `engine/sensors.py` + `sensor_resolver.py`), resolved on every
  request, so new eligible sensors need no reconfiguration:

  ```json
  "sensors": {
    "mode": "filter",
    "include": { "entity_id": ["sensor.plug_01_energy"], "area_id": ["kitchen"], "label_id": ["cost_tracking"],
                 "entity_globs": ["sensor.*_plug_*_energy"] },
    "exclude": { "entity_id": ["sensor.main_meter_t1"], "entity_globs": ["sensor.sub_meter_*"] },
    "overrides": { "sensor.water_heater_energy": { "spike_limit": "6" } }
  }
  ```

  - `mode` is `energy_dashboard` or `filter`. `include` exists only in `filter` mode: the string `"all"` or a target
    (`entity_id`, `device_id`, `area_id`, `floor_id`, `label_id`, `entity_globs`; non-empty, unique strings, at
    least one entry). `exclude` (same keys, both modes, `{}` when empty) wins over include. `overrides` maps an entity
    id to `{"spike_limit": "<decimal>" | null}` (`null` = no spike check; no entry = the global limit) and is kept
    when a sensor leaves the selection. Globs use `fnmatch.fnmatchcase` on the entity id and must match
    `^[a-z0-9_.*?\[\]!-]+$`.
  - An **eligible** sensor has recorder sum statistics in an energy unit (Wh / kWh / MWh) and `device_class: energy`
    (entity registry `device_class` or `original_device_class`, else the state attribute). `include: all` takes every
    eligible sensor; device, area, floor, label and glob rules match eligible sensors only; ids listed in `entity_id`
    are selected even when not eligible (the report then shows their `no_statistics` / `unsupported` status). A
    sensor's area is its own, else its device's; its labels are the union of entity, device and area labels. Hidden
    and categorized entities are not skipped. Exclude matches any id, regardless of eligibility. Filter mode sorts by
    entity id.
  - `energy_dashboard` mode takes the `stat_consumption` ids of the Energy dashboard's individual devices
    (`device_consumption`, electricity only), in dashboard order, duplicates dropped, minus `exclude`; external
    statistics are kept.
  - **Nesting.** In both modes the dashboard's `included_in_stat` gives a parent map. For the ids of one report a
    sensor's *upstream* is the nearest ancestor that is also in the report **and has readable statistics** (status
    `ok`); members of a cycle have none. Nested sensors keep their own row, but in every `total` row (buckets and
    `totals`) an hour of a nested sensor is left out **only where one of its ancestors (the whole chain of
    upstreams) has a counted value for that same hour** (a measured or estimated one, not a missing or excluded
    hour). Where no ancestor has a value (it started later, has gaps, was excluded as a spike) the nested sensor's
    energy counts, so in a chain `a` inside `b` inside `c` each hour is counted once, by the outermost device that
    has a value. A report for a subset of the sensors counts a child whose parent is not in the subset.
  - **Options flow.** `sensors` is a menu ("N sensors in the calculation" and a list of at most 30 sensors, nested
    ones marked; nothing is listed for an empty selection) with `sensors_select` and `device_limits`.
    `sensors_select` takes the mode and, in sections, include (`all`, a target selector limited to energy sensors,
    glob list) and exclude (target, globs); errors
    `no_dashboard_devices`, `nothing_included`, `invalid_glob`, `invalid_target`. A valid submission opens
    `sensors_preview` (the candidate's count and list; save or edit again); `sensors_save` re-reads the current
    options and replaces mode / include / exclude only. `device_limits` has one optional field per selected sensor
    and per sensor that already has an override (empty = global, `0` = off) and aborts with `no_sensors` when
    there is nothing to show.
  - **First setup** stores `energy_dashboard` when the Energy dashboard has individual devices, otherwise `filter` with
    `include: all`.
- Card (Lit + TypeScript, `frontend/`): renders the table; served by the integration itself (static path + extra JS),
  so users install one HACS repo. Details in §4.1.
- Stage 2 (optional): write **4 external statistics** series for the Energy dashboard:
  `energy_cost_stats:<zone>_kwh` and `energy_cost_stats:<zone>_cost` per zone (day/night → 4 series).
  Optional toggle (off by default) for per-device cost series. External statistics are not entities.

## 3. Tariff data model
**Tariffs** are named, versioned objects. A tariff has a stable `id` (`^[a-z0-9_]{1,32}$`), a display `name` and
**versions**. A version has a `valid_from` (a *local* calendar date; it applies from local midnight until the next
version of the same tariff, there is no end date) and its zones with prices and hours. Which tariff was actually
used, and from which date, is a separate list, `applied`, so a household can switch tariffs over time; any other
tariff can be priced over the same consumption for comparison (§4.2).

The configuration document has exactly the shape of the planned YAML configuration (task 021), so the forms
(task 018) and YAML write and read the same thing:
```yaml
energy_cost_stats:
  tariffs:
    - id: two_zone                       # stable
      name: Two-zone                     # display name, any language
      versions:
        - valid_from: 2026-01-01
          preset: ru_two_zone            # single_rate | ru_two_zone | ru_three_zone
          prices: { t1: "8.10", t2: "3.20" }
          hours: { t1: "07:00-23:00" }   # optional per-zone override of the preset hours
        - valid_from: 2026-07-01         # zones (keys, names, hours) inherited from the previous version
          prices: { t1: "8.75", t2: "3.45" }
    - id: three_zone
      name: Three-zone
      versions:
        - valid_from: 2026-07-01
          zones:                         # explicit zones instead of a preset
            - { key: t1, name: Peak,      price: "10.20", hours: "07:00-10:00, 17:00-21:00" }
            - { key: t3, name: Semi-peak, price: "8.75",  hours: "10:00-17:00, 21:00-23:00" }
            - { key: t2, name: Night,     price: "3.45",  hours: "23:00-07:00" }
  applied:                               # or the short form: applied: two_zone
    - { from: 2026-01-01, tariff: two_zone }
  compare: [three_zone]                  # optional; default: every tariff that is never applied
```
Rules (parsing is strict: unknown keys, wrong types and bad dates raise `TariffValidationError`):
- **Versions** are sorted by `valid_from`; dates are distinct. The first version needs `preset` or `zones`. A later
  version may omit both: it inherits the previous version's zones and must give `prices` for exactly those keys;
  `hours` may override the hours of inherited zones. A version with `preset` or `zones` starts a new zone set.
  With a preset, `prices` must name exactly the preset's keys; `zones` and `preset` are mutually exclusive.
- **Hours** are text `"HH:MM-HH:MM, ..."` (whole hours, `24:00` = end of day); every version covers each hour of
  the day exactly once. A mapping form for weekday-dependent hours (`{mon-fri: "...", sat-sun: "..."}`) is
  reserved: it is rejected with a clear message for now.
- **Applied.** Sorted, distinct `from` dates; each `tariff` must exist and must have a version valid on its `from`
  date (no unpriced gap inside the applied history). Hours before the first `from` are unpriced. The short form
  `applied: <id>` means "from the first version of that tariff". No `applied` (or no tariffs) → every hour
  unpriced (`cost` is `null`).
- **Effective schedule** (the real cost): for each applied interval `[from_i, from_i+1)`, the version of the
  applied tariff in force at `from_i` (re-dated to `from_i`) plus its later versions inside the interval. The
  engine consumes it as an ordinary `TariffSchedule` of plans (one `TariffPlan` per version, named like the tariff).
- **Comparison.** A compared tariff is priced with its own versions only (hours before its first version are
  unpriced). `compare` lists tariff ids; default = all tariffs that never appear in `applied`.
- **Prices** are decimal strings in the document (scale kept, no exponent; money never passes through `float`);
  numbers are accepted only by the YAML layer (task 021), which converts them.
- **YAML conversions** (`yaml_config.py`). Decimal fields (`spike_limit`, override `spike_limit`, version `prices`,
  zone `price`) accept `int` / `float` (not `bool`) and become decimal strings (`8.1` -> `"8.1"`, `1e-05` ->
  `"0.00001"`); strings are kept. Date fields (`valid_from`, `applied[].from`) accept a `datetime.date` (what the
  Home Assistant YAML loader returns for an unquoted `2026-01-01`) or a `YYYY-MM-DD` string and are stored as ISO
  strings; a `datetime` is an error. Nothing else is coerced.

Storage: one config subentry of type `tariff` per tariff, with `unique_id` = `id`, title = `name` and data = the
tariff's document (presets kept as written, so the forms and the YAML export show what the user entered).
`entry.options` gains `applied` (list of `{from, tariff}`) and optional `compare` (list of ids). The applied
history and the comparison list are edited in the options menu (task 019); with an explicit empty `compare` list
nothing is compared, without the key the default set is used.

Forms (subentry flow, task 018): "Add tariff" asks for a name and a base (single-rate, two-zone, three-zone, custom
zones of 1 to 6, or a copy of the latest version of an existing tariff), then the id (prefilled from the name) and
the first version (date and one section per zone with name, price and hours). The gear on a tariff row opens a menu:
add a version (prices, hours only when they change; a version dated before the first one becomes the new first
version with explicit zones, the former first version keeps its zones; it prices hours only once the applied history
starts on or before it), edit or delete a version, rename the tariff (name and id; the id also updates `applied` and
`compare`). Every change is validated against the **whole** configuration and reloads the entry, so edits re-price
past hours. Prices are typed as text (a comma is accepted) and stored with a dot. A preset first version stays in
preset form (`prices`, plus `hours` for changed zones) until a zone is renamed, then it is stored as explicit
`zones`. Moving the first version of a tariff, or deleting it, also moves an `applied` item that started on the old
first date (to the new first date); a move that would change the order of the applied history is rejected
(`applied_order`), and an applied start left without a version is rejected too (`applied_without_version`). Deleting
the first version makes the next one self-contained. 

Migration (config entry version 1 → 2): existing `tariff_plan` subentries become one tariff `id: main` (name of
the latest plan) whose versions are the old plans with explicit zones; `applied: [{from: <first valid_from>, tariff:
main}]`; the old subentries are removed. No plans → no tariff and no `applied`. A stored plan that fails
validation makes the migration fail (the entry shows a migration error).

Zone model (shared by all versions and presets):
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
- Leave room for an optional weekday filter (foreign tariffs) later (the reserved `hours` mapping form).
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

- **No tariff plan.** No tariff plan → every hour unpriced; `cost` is `null` (task 012). `build_report` and
  `classify_hours` accept `schedule=None`: `zones` and `plans` are empty and `unpriced_hours` equals the
  window's hours. Counted kWh still appear in `kwh` and `unpriced_kwh`, and data quality still applies.

### JSON contract (schema_version 1)
`engine/serialize.py::report_to_json` turns a `Report` into the document below. The websocket `report`
command and the service return it unchanged; the stage 4 card consumes it. This is the only place where
values are rounded (see Rounding above).

```json
{
  "schema_version": 1,
  "time_zone": "Europe/Moscow",
  "currency": "EUR",
  "start": "2026-01-15T00:00:00+03:00",
  "end": "2026-01-16T00:00:00+03:00",
  "grouping": "day",
  "zones": [ { "key": "t1", "name": "Day" }, { "key": "t2", "name": "Night" } ],
  "plans": [ { "valid_from": "2026-01-01", "name": "Two-zone", "zones": [ "...see below" ] } ],
  "devices": [ { "entity_id": "sensor.plug_01", "name": "Plug 01", "statistics": "ok", "upstream": null } ],
  "buckets": [ "<bucket>" ],
  "totals": "<bucket>",
  "unpriced_hours": 0,
  "issues": [ { "kind": "estimated", "entity_id": "sensor.plug_01",
                "start": "2026-01-15T05:00:00+03:00", "end": "2026-01-15T10:00:00+03:00",
                "hours": 5, "kwh": "10.000" } ]
}
```

`<bucket>` is `{ "start", "end", "hours", "rows": [<row>, ...], "total": <row> }`. `<row>` is:

```json
{ "entity_id": "sensor.plug_01", "kwh": "29.000", "cost": "240.00",
  "unpriced_kwh": "0.000", "estimated_kwh": "10.000", "excluded_kwh": "0.000",
  "status": "estimated",
  "coverage": { "expected": 24, "measured": 19, "estimated": 5, "excluded": 0, "missing": 0 },
  "zones": [ { "key": "t1", "kwh": "19.000", "cost": "195.70", "price": "10.3000" },
             { "key": "t2", "kwh": "10.000", "cost": "44.30", "price": "4.4300" } ] }
```

- **Numbers are decimal strings** in plain notation, after rounding: kWh 3 decimals, money 2, prices 4
  (`ROUND_HALF_UP`, never `-0`), e.g. `"240.00"`, `"29.000"`, `"10.3000"`. Hour counts (`hours`,
  `unpriced_hours`, `coverage.*`) are JSON integers. No floats are ever produced; automations apply
  `| float` in templates.
- **`null` vs `"0.000"`.** `kwh`/`cost` of a row or zone cell are `null` when there is no data (the "unknown"
  state of the semantics above); a measured zero is `"0.000"` / `"0.00"`. `unpriced_kwh`, `estimated_kwh`
  and `excluded_kwh` are always strings. A zone cell `price` is `null` when several prices applied in the
  bucket (plan switch) or the zone was not in force.
- **Times** are ISO 8601 with the UTC offset, in the report time zone (`datetime.isoformat()`), for the
  top-level `start`/`end`, bucket and issue times. `time_zone` is the IANA name and `currency` the code
  passed by the integration (HA's currency), or `null`.
- **Alignment.** `zones` lists `Report.zones` in order; every row's `zones` has one entry per zone in the
  same order, each repeating its `key`. `devices` is in row order; the total row has `"entity_id": null`.
  With grouping `total`, `buckets` is `[totals]`.
- **Rows.** `status` is `complete` / `estimated` / `partial` / `missing`. Totals are rounded from exact
  sums, not summed from rounded cells.
- **Plans** are the versions of the effective schedule in force in the window, serialized with `plan_to_data`
  (`valid_from`, `name` = tariff name, `zones` with `key`, `name`, `price` and `periods`), unrounded. With an
  applied switch, the first version of the new tariff is re-dated to the switch date (§3).
- **Issues.** `kind` is `estimated` / `excluded_negative` / `excluded_spike`; `hours` is the number of
  real elapsed hours of the issue span (not wall-clock, so correct across DST changes) and `kwh` its rounded energy.
- **`devices[].upstream`** is the entity id of the sensor this one is measured inside of (see sensor selection in
  §2), or `null`. A device with an upstream keeps its row, but its hours are left out of the `total` rows where an
  ancestor has a counted value (see §2). Additive; `schema_version` stays 1.
- **`devices[].statistics`** is the recorder adapter's status string (e.g. `ok`, `no_statistics`,
  `unsupported`).
- **Versioning.** New keys may be added without a version bump (consumers must ignore unknown keys);
  removing or renaming a key, or changing a value's meaning or format, bumps `schema_version`.
  `effective_price` is intentionally not serialized (the card derives it from `cost` / `kwh`).

### 4.1 Card (`custom:energy-cost-stats-card`)
Implemented in task 014. Sources in `frontend/` (Lit 3, TypeScript, Vitest + happy-dom, esbuild); the minified
bundle `custom_components/energy_cost_stats/frontend/energy-cost-stats-card.js` is **committed** (HACS installs
the repo as is, with no build step) and CI fails when it does not match the sources (`npm run check-bundle`).
- **Serving.** `async_setup` registers the bundle as a static path `/energy_cost_stats/energy-cost-stats-card.js`
  and, when the `frontend` integration is loaded, as an extra module with a content-hash `?v=` query, so no
  dashboard resource has to be added. Extra modules are imported before the frontend boots, and recent frontends
  replace `window.customElements` with a scoped-registry polyfill while booting; the bundle therefore waits for
  the `<home-assistant>` element to be defined before it defines the card (else dashboards show "Configuration
  error"). Loaded later (e.g. as a dashboard resource) it defines the card at once; if the frontend has not booted
  after 30 s it defines the card anyway and logs a warning. The static path is served with long cache headers:
  a manually added dashboard resource must carry a version query (`?v=...`) to pick up updates; the automatic
  extra module does this by itself.
- **Config.** `title`, `entities` (subset of the selected sensors; default all), `period` (initial preset,
  default `this_month`), `grouping` (`auto` / `hour` / `day` / `week` / `month` for the "by period" table,
  default `auto`), `show_breakdown` (bool). No visual editor yet.
- **Period picker** (modelled on the Energy dashboard's period selector). A period is a closed range of local
  dates. Presets: today, yesterday, this/last week, this/last month, this quarter, this year, last 7 / 30 days,
  last 12 months, or a custom range. Arrows move by the period's own size: a range of whole calendar months
  by its number of months (month 1, quarter 3, year 12), any other range by its number of days (day 1,
  week 7). Weeks start on Monday (like the engine). "Now" moves to the same kind of period that contains today;
  "next" is disabled when the next period would start after today.
- **Request.** `start` = first date; `end` = the day after the last date, except for a period that contains today:
  then the start of the current local hour as an ISO datetime with the zone's UTC offset (unambiguous in a DST
  fall-back hour; zones with non-whole-hour offsets use the date), so hours that have not happened yet are not
  shown as missing. "Today" and the current hour use the integration's time zone (the report's `time_zone`) once
  known, else HA's; if the first report reveals a different zone for a running period, the card asks again. Auto grouping: ≤ 2 days hour, ≤ 45 days day, ≤ 120 days week, else month; hour is offered only
  up to 31 days. While the last request was cut at the current hour the card re-fetches every 10 minutes (so also once after
  the period has ended, to pick up its last hour); stale responses are dropped.
- **Table.** One row per device with kWh and cost per zone (zone header shows the period price when it is a single
  price), total kWh, total cost and the average price (`cost / kWh`, display only), plus the total row. `null`
  shows as "—", never 0. Rows that are not `complete` get a badge (≈ estimated, ! partial/missing) with the
  coverage in the tooltip. A collapsible "by period" table shows the buckets for all devices or one device.
  Notes: no tariff plan, unpriced hours; a collapsible "data quality" list shows the issues.
- **Tariff comparison** (task 022). A plain "Tariff comparison" block after the device table and before "by
  period": a first "Actual" row (subtitle: the actual schedule's plan names joined with " → ") and one row per
  compared tariff, in the integration's order: cost, difference (compared − actual, money and percent of actual;
  positive = the compared tariff would have cost more; "—" when either cost is `null`, percent "—" when actual is
  0) and average price. Data: a second request, `energy_cost_stats/compare`, with the same `start` / `end` /
  `entities` as the report and no `tariffs` (the list is the integration's `compare` setting; the card has no
  `compare` option). It is re-sent with the report except on a grouping change; stale responses are dropped.
  A tariff with unpriced hours gets a warning badge. An empty list shows a hint; `unknown_command` (older
  integration) hides the section; any other compare error is shown inside the section only.
- **Layout.** `getGridOptions()` returns `{columns: "full", min_columns: 6}` (no `rows`: height follows the
  content), so in sections views the card spans its section by default; a user `grid_options` overrides it. A card
  cannot be wider than its section: wider layouts are the section's `column_span`. Masonry and panel views use
  `getCardSize`. Each zone and the Total group start with a `group-start` cell (left separator on every row) under
  a centred zone header; the sticky name column has an end shadow. Name cells wrap (`overflow-wrap: anywhere`, at
  most about a third of the card width) and carry the full name as `title`; numbers never wrap.
- **Nested devices.** A device with `devices[].upstream` in the report is shown directly after its upstream
  (depth-first, report order among siblings), indented, prefixed with "↳", and a note explains that its energy is
  counted in the total only for hours where the upstream has no data. The "by period" device list keeps the
  report order.
- **`hass` update gate.** Home Assistant replaces `hass` on every entity state change. The property's `hasChanged`
  (`hassChanged`, `frontend/src/hass.ts`) is true only for the first value or when the language, the locale
  language or the time zone changes, so unrelated updates neither re-render the card nor touch an open native
  dropdown. The newest `hass` is still stored for `callWS`.
- **Language.** English and Russian strings in the card (`hass.locale.language`); numbers, money (HA currency) and
  dates via `Intl` in that locale.

### 4.2 Tariff comparison (`energy_cost_stats/compare`)
Read-only websocket command (no admin rights). Fields: `start`, `end` (as in §2), optional `entities` (as in §2) and
optional `tariffs` (tariff ids; default = the configured `compare` list, which defaults to every tariff that is
never applied; an explicit empty list compares nothing). There is no `grouping`: the documents are grouped as
`total`. The statistics are read once and the same counted kWh (with the same data-quality handling) is priced by
the actual schedule and by each compared tariff separately, using that tariff's own versions only (§3); hours before
its first version are unpriced.
```json
{ "actual": "<§4 document>",
  "tariffs": [ { "id": "three_zone", "name": "Three-zone", "report": "<§4 document>" } ] }
```
`tariffs` follows the requested (or configured) order, duplicates dropped. A tariff that is also applied may be
requested; its report then equals the actual one over the period it covers. Errors as for `report`
(`not_loaded`, `invalid_period`, `period_too_long`, `unknown_entity`) plus `unknown_tariff`.

## 5. Known pitfalls to handle
- Engine input is hourly deltas keyed by **UTC hour start**; zones, plan switches and groupings use local
  time (IANA tz via `zoneinfo`); DST days have 23/25 hours and are handled; weeks start on Monday; months
  are local calendar months; groupings: hour/day/week/month/custom range (+ totals).
- Known limitation: **non-whole-hour UTC offsets** (e.g. `Asia/Kolkata`, UTC+05:30) are accepted, not
  rejected. Each UTC hour is attributed to the local hour and date its start falls in, so for such zones
  the local day and every zone/plan boundary effectively shift by the offset's minute remainder (e.g. a
  local day starting at `xx:30` instead of `xx:00`, and a zone boundary configured for local `07:00` is
  applied from the UTC hour whose local start is `07:30`). No error is raised; this is by design, not a bug.
- The current hour isn't compiled into LTS yet. In stage 3 the not-yet-compiled hour (and the last hour until the
  recorder compiles it, a few seconds after the hour) is **missing**, like any trailing gap, never zero. Using
  short-term (5-min) statistics for "today" (kept ~10 days) is a follow-up.
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
  Implemented in task 011 (`recorder_adapter.py`): per id it returns every in-window key plus exactly one key
  before and one after the window (trimmed, however far away they are). Query plan: one query for
  `[start - 1 day, end + 1 day)`; ids still lacking a neighbour are re-queried only for themselves in
  widening ranges (31 days, then unbounded back to 1970 / forward to now). Worst case is O(history) for an id
  with a hole of more than 31 days next to the window, because the recorder has no public "last row before t"
  query. HA's `change` is relative to the previous non-null row only inside a query. The baseline of a
  query is the last row before its start, even with a `NULL` sum (taken as 0), so the first non-null row of
  a query can carry its full cumulative sum. The adapter therefore requests `sum` too and recomputes that row's
  `change` as `sum` minus the previous fetched non-null sum.
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
| `get_metadata(statistic_ids=...)` | ≤ 2023.x | Adapter reads only `has_sum` and `unit_of_measurement`. |
| Config subentries | 2025.3 | Hard floor: tariffs are subentries. |
| Energy preferences `device_consumption[].included_in_stat` | 2025.4 | Read with `.get()` through `energy.data.async_get_manager(hass).data` (`None` = never saved); only `sensor_resolver.py` imports it. |
| `get_metadata(statistic_type="sum", statistic_source="recorder")` | ≤ 2023.x | Lists the energy sum statistics (adapter, keyword arguments, recorder executor). |
| Target resolution helper | moved | `helpers.service.async_extract_referenced_entity_ids` (2025.4) became `helpers.target...` on `dev`; devices / areas / floors / labels are resolved from the registries by ourselves instead. |
| `StatisticMeanType` / `mean_type` in metadata | 2025.4 | Writing external statistics (stage 2). |
| `unit_class` in statistics metadata | 2025.11 | Adapter passes it only when supported. |
| `has_mean` removed; `mean_type` + `unit_class` mandatory for writes | 2026.11 | Adapter must already comply. |
| Invalid `CONFIG_SCHEMA` aborts the integration | ≤ 2025.4 | `setup.py` returns before `async_setup` and before the config entries are set up when the processed config is `None`, hence the lenient schema and our own validation (§2, YAML mode). |
| `helpers.reload.async_integration_yaml_config` | ≤ 2025.4 | Re-reads `configuration.yaml` through the integration's `CONFIG_SCHEMA`; identical at 2025.4.0 and `dev`. Used by the `reload` action (`async_setup_reload_service` is for platform integrations and is not used). |
| `helpers.service.async_register_admin_service` | ≤ 2025.4 | The `reload` action; raises `Unauthorized` for non-admin users. |
| Issue registry (`async_create_issue` / `async_delete_issue`) | ≤ 2025.4 | The `invalid_yaml` repair (informational, not persistent). |
| `homeassistant.util.yaml` (`dump`, `parse_yaml`) | ≤ 2025.4 | Export renders and tests parse; the loader returns `date` for unquoted dates and `float` for unquoted prices (asserted by a test). |

Reading metadata: ignore unknown fields (`mean_type`, `unit_class`, deprecated `has_mean`).
The `statistics_during_period` and `get_metadata` parameters were verified identical at 2025.4.0 and `dev` on
2026-11-01 (`dev` only adds `period="year"`): [statistics.py @2025.4.0](https://github.com/home-assistant/core/blob/2025.4.0/homeassistant/components/recorder/statistics.py),
[statistics.py @dev](https://github.com/home-assistant/core/blob/dev/homeassistant/components/recorder/statistics.py).
The adapter calls them with keyword arguments.
Reference: https://developers.home-assistant.io/blog/2025/10/16/recorder-statistics-api-changes/

### 6.1 JSON Schema of the YAML block
`schema/energy_cost_stats.schema.json` (repository root, committed, not shipped inside `custom_components/`) is a
hand-written **draft-07** JSON Schema of the **content** of the `energy_cost_stats:` block, so it applies directly to
a file pulled in with `!include`. `$id` is the raw URL on `master`; for a schema matching an installed release use
the tag instead: `https://raw.githubusercontent.com/MrKiirya/ha-energy-cost-stats/v<version>/schema/energy_cost_stats.schema.json`.

To use it in an editor with the YAML extension (yaml-language-server; Studio Code Server), keep the block in its own
file, because a modeline applies to the whole file:

```yaml
# configuration.yaml
energy_cost_stats: !include energy_cost_stats.yaml
```
```yaml
# energy_cost_stats.yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/MrKiirya/ha-energy-cost-stats/master/schema/energy_cost_stats.schema.json
time_zone: Europe/Berlin
tariffs: []
```

`!secret` / `!include` inside the file need the editor setting `yaml.customTags` (for example `"!secret scalar"`)
or the extension reports unknown tags. The schema checks **structure only** (keys, types, required keys, enums,
patterns for tariff ids, dates, globs and hours, `include` only in `filter` mode, `preset` xor `zones`); rules that
need the whole document stay in the engine and are reported as a repair at load time. Prices and limits accept
numbers and strings, dates are strings (unquoted dates are strings in YAML 1.2).
It is written by hand because the real rules live in imperative parsers and `CONFIG_SCHEMA` is lenient; drift is
prevented by tests: a shared fixture corpus (`tests/fixtures/yaml_config/{valid,invalid_structure,invalid_semantic}`)
that must be accepted / rejected by both the schema and `document_from_yaml`, a key-coverage test comparing
`yaml_config.ACCEPTED_KEYS` with the schema in both directions, enum coverage (modes, presets), and a check that
every Export validates (`tests/integration/test_yaml_schema_sync.py`, `tests/unit/test_config_schema.py`).

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
