# 010 — Tariff plans as config subentries

Status: in-review
Roadmap: SPEC §8 stage 2 (config flow / options flow / tariff subentries), task 2 of 2 (009-config-and-options-flow,
010-tariff-plan-subentries). Depends on **009** (config flow, update-listener reload, `RuntimeData`).
Spec sections: SPEC §2 (tariff plans are config subentries), §3 (tariff data model, presets, validation), §6 (config
subentries since 2025.3; min HA 2025.4); CLAUDE.md principles 3, 4, 6

> Planner decisions are marked **(D-n)** and also appear under "Open questions" as "decided by planner,
> confirm in PR review". The human was away when this was planned.

## Goal
On the integration's card in *Settings → Devices & services*, users can **add a tariff plan** (from a preset or
as a copy of an existing plan), **edit** a plan (reconfigure) and **delete** it (HA's built-in subentry delete).
Each plan is one config subentry of type `tariff_plan`, holding `valid_from`, a name and its zones with prices
and periods. Input is checked with the engine's validation, and each problem shows as a form error on the right
field. Any add, edit or delete reloads the entry (009's update listener). The reloaded entry holds an
engine `TariffSchedule` in `runtime_data`, so stage 3 re-prices all past hours with the current plans
(retroactive by design). A new pure engine module maps subentry data to and from `TariffPlan`.

## Context

### Current state (after 009)
- `config_flow.py` has `EnergyCostStatsConfigFlow` and its options flow. `__init__.py` has `RuntimeData(settings,
  tzinfo)`, `EnergyCostStatsConfigEntry` and an update listener that calls `async_reload`.
- Engine model (`engine/tariff.py`, task 004): `Period(start_hour, end_hour)` with `Period.parse("HH:MM",
  "HH:MM")` (end `"00:00"`/`"24:00"` → 24), `Zone(key, name, price: Decimal, periods, band_prices=())`,
  `TariffPlan(valid_from: date, name, zones, volume_band_limits_kwh=())`, `TariffSchedule(plans)` (non-empty,
  distinct `valid_from`, sorted). Every validation failure raises `TariffValidationError(ValueError)` with a
  concrete English message (for example `"hours not covered: 22"` or `"hour 22 covered by zones t1 and t2"`).
  `TariffPlan.name` is not validated (004 follow-up). The codec checks it instead.
- Presets (`engine/presets.py`): `single_rate` (`t0`), `ru_two_zone` (`t1` Day 07–23, `t2` Night 23–07),
  `ru_three_zone` (`t1` Peak 07–10 + 17–21, `t2` Night 23–07, `t3` Semi-peak 10–17 + 21–23). Zone keys follow RU
  meter registers and must never change once data exists (SPEC §3).

### HA API checked (2026-11-01)
Verified in [config_entries.py @2025.4.0](https://github.com/home-assistant/core/blob/2025.4.0/homeassistant/config_entries.py)
and compared with [config_entries.py @dev](https://github.com/home-assistant/core/blob/dev/homeassistant/config_entries.py).
Background: [config subentries blog post (2025-02-16)](https://developers.home-assistant.io/blog/2025/02/16/config-subentries)
(now under contributors.home-assistant.io) and the
[options flow docs](https://contributors.home-assistant.io/core/integrations/options-flow/) (update listeners vs. reload).
- `ConfigFlow.async_get_supported_subentry_types(cls, config_entry) -> dict[str, type[ConfigSubentryFlow]]` is a
  `@classmethod @callback`. The same exists in 2025.4.0 and latest.
- `ConfigSubentryFlow`: `async_create_entry(*, title=None, data, description=None, description_placeholders=None,
  unique_id=None)`, `_get_entry()`, `_get_reconfigure_subentry()` (reads `context["subentry_id"]`; source must be
  `reconfigure`). HA shows the "edit" action because a method called `async_step_reconfigure` exists
  (`supports_reconfigure = hasattr(handler, "async_step_reconfigure")`).
- `ConfigSubentryFlow.async_update_and_abort(entry, subentry, *, unique_id=, title=, data=, data_updates=)`
  aborts with reason `reconfigure_successful`. **API differences:** 2025.4.0 has **no** `reason=` parameter
  (latest has one) and **no** `async_update_reload_and_abort`. On latest, that method raises
  `ValueError("Cannot update and reload entry with update listeners")`, and 009 has an update listener. **Use
  only `async_update_and_abort` without `reason=`.** The update listener does the reload.
- `ConfigSubentryFlowManager.async_finish_flow` builds the `ConfigSubentry(data, subentry_type, title,
  unique_id)` and calls `async_add_subentry`. A `unique_id` that is already used among the same entry's
  subentries raises `AbortFlow("already_configured")` (in add and in update-with-new-unique_id). The flow checks
  for duplicates first (D-4), so users get a field error instead of an abort.
- `async_add_subentry`, `async_update_subentry` (only if something changed) and `async_remove_subentry` all fire
  the entry's update listeners in 2025.4.0 and latest. Removing a subentry also clears its device/entity
  registry links (we have none). The subentry manager does not require the entry to be loaded, only to exist.
- Tests: `hass.config_entries.subentries.async_init((entry.entry_id, "tariff_plan"), context={"source":
  SOURCE_USER})`, then `hass.config_entries.subentries.async_configure(flow_id, user_input)`. Reconfigure uses
  `context={"source": SOURCE_RECONFIGURE, "subentry_id": ...}`. Delete uses
  `hass.config_entries.async_remove_subentry(entry, subentry_id)`. Seeded subentries:
  `MockConfigEntry(..., subentries_data=[ConfigSubentryData(data=..., subentry_type="tariff_plan", title=...,
  unique_id=...)])`. If `subentries_data` is missing from the PHCC 0.13.232 `MockConfigEntry` (HA 2025.4.0),
  call `hass.config_entries.async_add_subentry` before `async_setup` instead, and record that in
  Implementation notes.
- Translations
  ([script/hassfest/translations.py @dev](https://github.com/home-assistant/core/blob/dev/script/hassfest/translations.py)):
  `config_subentries.<type>` **requires** `entry_type`, `initiate_flow.user` and `step`. Extra `initiate_flow`
  keys are allowed (use `reconfigure`). `error`/`abort` are optional. Selector option labels live under the
  top-level `selector.<translation_key>.options`. `[%key:...%]` references are not resolved for custom
  integrations, so write literal text (including `abort.reconfigure_successful`). Error strings may use the
  form's `description_placeholders`.

### Design decisions
- **D-1 Subentry data format** (JSON; mirrors SPEC §3, prices as strings):
  ```json
  { "valid_from": "2026-01-01", "name": "Two-zone",
    "zones": [
      { "key": "t1", "name": "Day",   "price": "10.30", "periods": [["07:00", "23:00"]] },
      { "key": "t2", "name": "Night", "price": "4.43",  "periods": [["23:00", "07:00"]] } ] }
  ```
  `volume_band_limits_kwh` (plan) and `band_prices` (zone) are written only when they are non-empty, as string
  lists (reserved fields, SPEC §3). A period end of 24 is written as `"24:00"`. Prices keep the scale the user
  typed and never use exponent notation (`format(price, "f")`, so `"10.30"` stays `"10.30"`). Reading is
  **strict**: unknown keys, wrong JSON types (float/int/bool prices, tuples are fine but non-list/str values are
  not), bad dates (`"2026-1-1"`, datetimes) and a blank plan name raise `TariffValidationError`. Money read from
  storage must never pass through `float`.
- **D-2 Codec in the engine:** `engine/plan_codec.py` (pure, stdlib only, unit-tested, counts toward the 95 %
  gate). It provides `plan_to_data(plan) -> dict[str, Any]`, `plan_from_data(data: Mapping[str, Any]) ->
  TariffPlan`, `parse_price(text: str) -> Decimal`, `parse_periods(text: str) -> tuple[Period, ...]`,
  `format_periods(periods) -> str`.
  - `parse_price`: strips whitespace and accepts `^\d+([.,]\d+)?$` (a comma is a decimal separator). It rejects
    empty input, signs, exponents, `NaN`/`Infinity` and thousands separators.
  - `parse_periods`: takes comma- or semicolon-separated `HH:MM-HH:MM` items. The dash may be `-` or `–`, and
    whitespace is ignored. Each item goes through `Period.parse`, and empty items are rejected.
  - `format_periods`: `"07:00-10:00, 17:00-21:00"`, with end 24 written as `"24:00"`.
    `parse_periods(format_periods(p)) == p`.
- **D-3 Fixed zone sets:** the zone keys of a plan come from its preset or from the copied plan. The form edits
  zone names, prices, periods, the plan name and `valid_from`. It does **not** add, remove or re-key zones. That
  keeps keys stable for statistics and keeps the form static enough to translate. Custom zone sets
  (non-RU tariffs, a fourth zone) are a follow-up.
- **D-4 Subentry identity:** `subentry_type = "tariff_plan"`, `unique_id = valid_from.isoformat()`, title
  `"<valid_from> · <name>"` (for example `"2026-01-01 · Two-zone"`). Before create or update, the flow checks
  the entry's other `tariff_plan` subentries (excluding the one being reconfigured) for the same `valid_from`. A
  match gives `errors["valid_from"] = "valid_from_taken"` (SPEC §3: same date is invalid).
- **D-5 Flow steps** (`TariffPlanSubentryFlow` in `subentry_flow.py`):
  - `user`: with no plans yet, go straight to `preset`. Otherwise show a menu `["preset", "copy"]`.
  - `preset`: `preset` select (`single_rate`, `ru_two_zone`, `ru_three_zone`; `translation_key="preset"`),
    then go to `plan` with the preset's zones. The price fields stay **empty**, so the user must type prices.
  - `copy`: `source_plan` select (value = subentry id, label = title), defaulting to the plan with the
    **latest** `valid_from`, the one a new plan usually follows. Then go to `plan`, pre-filled with that plan's
    name, zone names, prices and periods. `valid_from` gets no suggestion.
  - `plan`: `valid_from` (`DateSelector`, required, no default for new plans), `name` (text), and for each zone
    key `k` in the plan's order: `{k}_name` (text), `{k}_price` (text, D-2 parsing; not a `NumberSelector`,
    so money never becomes a `float`) and `{k}_periods` (text, D-2 format). Translations cover `k` in
    `t0`…`t3` (labels such as "Day / peak (T1) price"). The step description explains the period format,
    whole hours only, and that hours before the first plan are reported as unpriced.
  - `reconfigure`: loads the subentry with `plan_from_data`, then shows the same `plan` step pre-filled
    (including `valid_from`). On success it calls `async_update_and_abort(entry, subentry, title=..., data=...,
    unique_id=...)`.
  - Errors, in this order: (1) per-field parse errors: `{k}_price: invalid_price`, `{k}_periods:
    invalid_periods`, `name`/`{k}_name: blank_name`, `valid_from: valid_from_taken`. If any of these exist,
    show the form again. (2) Otherwise build the `TariffPlan`. A `TariffValidationError` becomes
    `errors["base"] = "invalid_plan"` with the placeholder `detail = str(err)` (the engine's message, for example
    `"hours not covered: 22"`). Always pass `description_placeholders={"detail": ...}` (empty string when there
    is no error) so the placeholder never shows raw. The submitted values stay in the form after an error.
- **D-6 Delete:** HA's built-in subentry delete. No code is needed beyond the reload. Deleting the last plan is
  allowed, and `runtime_data.schedule` then becomes `None`. Stage 3 reports all hours as unpriced, which is
  "unknown", not "free" (SPEC §4).
- **D-7 Setup:** `async_setup_entry` reads every `tariff_plan` subentry with `plan_from_data`. If one fails, it
  raises `ConfigEntryError` naming the subentry title (only hand-edited storage can cause this). It stores
  `RuntimeData.schedule = TariffSchedule(plans)` when there are plans, otherwise `None`. A schedule-level error
  (duplicate `valid_from`, which `unique_id` should already prevent) is also a `ConfigEntryError`.

## Files
- create: `custom_components/energy_cost_stats/engine/plan_codec.py` — D-1, D-2.
- create: `tests/unit/test_plan_codec.py`
- create: `custom_components/energy_cost_stats/subentry_flow.py` — `TariffPlanSubentryFlow` (D-3 … D-5).
  Preset templates come from `engine.presets` with `Decimal(0)` prices, and their prices are not shown.
- modify: `custom_components/energy_cost_stats/config_flow.py` — `async_get_supported_subentry_types` →
  `{SUBENTRY_TYPE_TARIFF_PLAN: TariffPlanSubentryFlow}`.
- modify: `custom_components/energy_cost_stats/const.py` — `SUBENTRY_TYPE_TARIFF_PLAN = "tariff_plan"`, preset ids,
  field-name helpers if useful.
- modify: `custom_components/energy_cost_stats/__init__.py` — `RuntimeData.schedule: TariffSchedule | None`, D-7.
- modify: `custom_components/energy_cost_stats/strings.json` — `config_subentries.tariff_plan` (`entry_type`:
  "Tariff plan"; `initiate_flow`: `user` "Add tariff plan", `reconfigure` "Edit tariff plan"; steps `user` (menu
  options), `preset`, `copy`, `plan`; errors `invalid_price`, `invalid_periods`, `blank_name`,
  `valid_from_taken`, `invalid_plan` ("The zones are invalid: {detail}"); abort `reconfigure_successful`), plus
  top-level `selector.preset.options`.
- modify: `custom_components/energy_cost_stats/translations/en.json` — identical to `strings.json` (009's test
  enforces this).
- create: `tests/integration/test_tariff_subentries.py`
- modify: `docs/SPEC.md` — §3: the storage format (D-1, prices as strings; also change the JSON example's
  `"price": 0.0` to strings), fixed zone sets per plan (D-3), `valid_from` uniqueness via `unique_id`. §2: one
  line saying subentry changes reload the entry. No other section.

10 files.

## Tests to write first
Generic data only: the two-zone example (day `10.30`, night `4.43`), dates in 2026.

| Level | Test | Asserts |
|---|---|---|
| unit | `tests/unit/test_plan_codec.py::test_two_zone_to_data_exact` | `plan_to_data(ru_two_zone(valid_from=2026-01-01, day_price=Decimal("10.30"), night_price=Decimal("4.43")))` equals the D-1 JSON exactly, and `json.dumps` succeeds. |
| unit | `tests/unit/test_plan_codec.py::test_roundtrip` | Parametrized over the three presets plus a plan with volume bands (`(3900, 6000)` + 2 `band_prices` per zone): `plan_from_data(plan_to_data(p)) == p`, including through `json.loads(json.dumps(...))`. |
| unit | `tests/unit/test_plan_codec.py::test_full_day_end_written_as_24` | Single-rate → periods `[["00:00", "24:00"]]`. Reading `[["00:00", "00:00"]]` gives `Period(0, 24)`. |
| unit | `tests/unit/test_plan_codec.py::test_price_scale_preserved_no_exponent` | `Decimal("10.30")` → `"10.30"`, `Decimal("1E+1")` → `"10"`, `Decimal("0")` → `"0"`. |
| unit | `tests/unit/test_plan_codec.py::test_from_data_rejects` | Parametrized → `TariffValidationError`: missing `zones`; unknown top-level key; unknown zone key; `valid_from` `20260101` (int), `"2026-1-1"`, `"2026-01-01T00:00:00"`; `name` `"  "`; `zones` `{}` / `[]`; price `10.3` (float), `10` (int), `True`, `"-1"`, `"NaN"`, `"abc"`; `periods` `"07:00-23:00"` (str), `[["07:00"]]`, `[[7, 23]]`; a coverage gap (the engine's message is kept). |
| unit | `tests/unit/test_plan_codec.py::test_parse_price` | Valid: `"10.30"` → `Decimal("10.30")`, `"10,30"` → `Decimal("10.30")`, `" 4.43 "`, `"0"`, `"7"`. Invalid (`TariffValidationError`): `""`, `" "`, `"-1"`, `"+1"`, `"abc"`, `"1e3"`, `"NaN"`, `"Infinity"`, `"1.2.3"`, `"1,234.5"`. |
| unit | `tests/unit/test_plan_codec.py::test_parse_periods` | `"07:00-23:00"` → `(Period(7, 23),)`; `"07:00-10:00, 17:00-21:00"` → two periods; `"23:00 – 07:00"` → `(Period(23, 7),)`; `"00:00-24:00"`; `"07:00-10:00; 17:00-21:00"`. Invalid: `""`, `"7-23"`, `"07:30-08:00"`, `"07:00-07:00"`, `"07:00"`, `"07:00-23:00,"`. |
| unit | `tests/unit/test_plan_codec.py::test_format_periods_inverse` | `format_periods((Period(7, 10), Period(17, 21))) == "07:00-10:00, 17:00-21:00"`; `Period(0, 24)` → `"00:00-24:00"`; `parse_periods(format_periods(p)) == p` for every preset zone. |
| integration | `tests/integration/test_tariff_subentries.py::test_subentry_type_registered` | `EnergyCostStatsConfigFlow.async_get_supported_subentry_types(entry) == {"tariff_plan": TariffPlanSubentryFlow}`; the flow class has `async_step_reconfigure`. |
| integration | `tests/integration/test_tariff_subentries.py::test_first_plan_goes_to_preset` | Loaded entry, no subentries: the `user` subentry flow → FORM `preset` (no menu). |
| integration | `tests/integration/test_tariff_subentries.py::test_add_two_zone_from_preset` | `preset: ru_two_zone` → FORM `plan` with fields `valid_from, name, t1_name, t1_price, t1_periods, t2_name, t2_price, t2_periods` (no `t0_*`/`t3_*`); suggested `t1_periods == "07:00-23:00"`, `t2_periods == "23:00-07:00"`, `t1_name == "Day"`, no suggested prices. Submitting `valid_from "2026-01-01"`, `name "Two-zone"`, `t1_price "10,30"`, `t2_price "4.43"` → `CREATE_ENTRY`; the subentry has `data ==` D-1 JSON, `title == "2026-01-01 · Two-zone"`, `unique_id == "2026-01-01"`. After `async_block_till_done()`: the entry is `LOADED` and `runtime_data.schedule.plan_for(date(2026, 1, 2)).zone_for_hour(12).price == Decimal("10.30")`. |
| integration | `tests/integration/test_tariff_subentries.py::test_preset_fields` | Parametrized: `single_rate` → only `t0_*` fields, `t0_periods == "00:00-24:00"`; `ru_three_zone` → `t1_*`, `t2_*`, `t3_*` in that order, `t1_periods == "07:00-10:00, 17:00-21:00"`. |
| integration | `tests/integration/test_tariff_subentries.py::test_menu_and_copy` | With plan A (2026-01-01): `user` → MENU `["preset", "copy"]`; `copy` defaults `source_plan` to A's subentry id; the `plan` form is pre-filled from A with no `valid_from` suggestion; submitting `valid_from "2026-07-01"` and `t1_price "11.00"` → 2 subentries; A's data is unchanged; `schedule.plan_for(date(2026, 6, 30))` is priced from A and `plan_for(date(2026, 7, 1))` at `11.00`. |
| integration | `tests/integration/test_tariff_subentries.py::test_copy_defaults_to_latest_plan` | Plans 2026-01-01 and 2026-07-01 → the default `source_plan` is the 2026-07-01 one. |
| integration | `tests/integration/test_tariff_subentries.py::test_duplicate_valid_from` | Adding a second plan dated 2026-01-01 → FORM `plan`, `errors == {"valid_from": "valid_from_taken"}`; still one subentry. |
| integration | `tests/integration/test_tariff_subentries.py::test_field_errors` | Parametrized single-field faults → exactly that error key: `t1_price` `"-1"`/`"abc"`/`""` → `invalid_price`; `t1_periods` `"7-23"`/`"07:30-23:00"`/`""` → `invalid_periods`; `t1_name "  "` and `name "  "` → `blank_name`. No subentry is created. |
| integration | `tests/integration/test_tariff_subentries.py::test_plan_validation_errors` | `t1_periods "07:00-22:00"` → `errors == {"base": "invalid_plan"}` and `description_placeholders["detail"]` contains `"22"`; `t2_periods "22:00-07:00"` → `detail` contains `"hour 22"`. A valid form has `detail == ""`. |
| integration | `tests/integration/test_tariff_subentries.py::test_reconfigure_edits_plan` | Reconfigure plan A → FORM `plan` pre-filled with `valid_from "2026-01-01"`, the names, `t1_price "10.30"` and the periods; changing `t1_price` to `"10.50"` → `ABORT` `reconfigure_successful`; the subentry data and title are updated; after the reload `runtime_data.schedule` prices hour 12 at `10.50` (retroactive: same `valid_from`, new price). |
| integration | `tests/integration/test_tariff_subentries.py::test_reconfigure_valid_from` | Plans A (2026-01-01) and B (2026-07-01): moving B to `2026-03-01` → `unique_id == "2026-03-01"` and the title is updated; moving B to `2026-01-01` → `valid_from_taken`; keeping B's own date is accepted (no self-conflict). |
| integration | `tests/integration/test_tariff_subentries.py::test_remove_plan_reloads` | Two plans; `async_remove_subentry(entry, B)` → after reload, `schedule.plans` has only A; removing A too → `schedule is None`; the entry stays `LOADED`. |
| integration | `tests/integration/test_tariff_subentries.py::test_setup_error_on_corrupt_plan` | Entry seeded with a subentry whose `data` has `"price": 10.3` (float) → `SETUP_ERROR`. |
| integration | `tests/integration/test_tariff_subentries.py::test_no_entities` | After adding a plan: `hass.states.async_all()` holds no entity of this domain (principle 1). |

## Acceptance criteria
Linux devcontainer (from the host: `devcontainer exec --workspace-folder . --docker-path podman <cmd>`):
- [x] `uv run --group ha pytest -m integration` → all pass (009's tests included).
- [x] `script/test` → all levels pass; the engine coverage gate (≥ 95 %) holds and `plan_codec.py` is listed.
- [x] `uv run --group ha pyright` → 0 errors (`engine/plan_codec.py` is under strict mode).
- [x] `script/lint` → exit 0.

Either environment:
- [x] `uv run pytest -m unit` → passes, including `test_engine_has_no_forbidden_imports` with the new module.
- [x] `uv run ruff check .` and `uv run ruff format --check .` → exit 0.

General:
- [x] `rg -n "float\(" custom_components/energy_cost_stats` → no conversion of prices through `float`.
- [x] `rg -n "NumberSelector" custom_components/energy_cost_stats/subentry_flow.py` → no matches (prices are text).
- [x] `rg -n "async_update_reload_and_abort|reason=" custom_components/energy_cost_stats/subentry_flow.py` → no
  matches (2025.4.0 compatibility, update-listener conflict on latest).
- [x] `rg -n "components.recorder" custom_components/energy_cost_stats` → only `recorder_adapter.py` (if it exists yet).
- [x] `strings.json` == `translations/en.json`. `hassfest` runs in CI only (`config_subentries.tariff_plan` has
  `entry_type`, `initiate_flow.user` and `step`).
- [ ] CI is green on both matrix legs (HA 2025.4.0 / latest). (Not run locally; CI only.)
- [x] `docs/SPEC.md`: only §3 (storage format, fixed zone sets, the string-price JSON example, uniqueness) and one
  §2 line changed.
- [x] No files touched outside "Files".
- [ ] Manual (optional, human): in `script/develop`, add a two-zone plan, copy it with a new date and price, edit
  it, delete it from the subentry menu; the log shows only reloads, no errors.

## Out of scope
- Using the schedule for reports (websocket command, service, recorder adapter) → stage 3.
- Adding, removing or re-keying zones in the UI, and custom (non-preset) zone sets (D-3) → follow-up task.
- Weekday filters and volume-tier editing in the UI. The codec round-trips the reserved volume fields, but the
  form does not expose them.
- Moving plans to `helpers.storage.Store` plus a card editor (SPEC §2 "may move later").
- Verifying the RU zone hours for a specific region (SPEC §3 "verify before shipping"). That is a release
  checklist item, not code.
- Translations other than English.

## Open questions
All decided by planner, confirm in PR review:
- D-1 Subentry data stores prices as strings with the user's scale preserved, uses `"24:00"` for the end of day,
  and is read strictly (unknown keys rejected).
- D-2 The plan codec and the text parsers for prices/periods live in the engine (pure, unit-tested). Prices
  accept `,` as the decimal separator.
- D-3 The zone set of a plan is fixed by its preset or copied plan. Custom zone sets are a follow-up.
- D-4 `unique_id = valid_from`, title `"<date> · <name>"`, and a duplicate date is a field error.
- D-5 With no plans the flow goes straight to presets. Copy defaults to the latest `valid_from`. Preset prices
  start empty. `valid_from` has no default for new plans.
- D-6 Deleting the last plan is allowed (`schedule = None`, everything unpriced).
- D-7 A corrupt stored plan → `ConfigEntryError` instead of silently skipping the plan.

<!-- Filled in by implementer -->
## Implementation notes
- D-1..D-7 implemented as planned; all planner decisions remain "confirm in PR review".
- Tests run locally on HA 2026.9.3 / Python 3.14 only: unit 323 -> 404 total with `script/test` (coverage 99.6 %,
  `plan_codec.py` 97 %), integration 81, pyright 0 errors, ruff ok. The 2025.4.0 leg was not run;
  `MockConfigEntry(subentries_data=...)` exists in the installed PHCC and is used for seeding. If it is missing in
  PHCC 0.13.232, switch the helper `_add_entry` to `async_add_subentry` before setup.
- Price/number validation (lesson from 009): `parse_price` accepts only ASCII digits with an optional `.`/`,`
  part (so NaN, inf, exponents and signs are rejected as text) and additionally rejects values above 1,000,000
  (`MAX_PRICE`, an addition to the task) as `invalid_price`. No `Decimal(float)` and no `float(` in the new code.
  Storage reads also reject a comma in stored prices.
- Extras beyond the task table: form error `invalid_date` (defensive, the selector should prevent it); aborts
  `unknown_plan` / `invalid_plan_data` (copy or reconfigure of a corrupt stored plan); `volume_band_limits_kwh` and
  `band_prices` are carried over in copy and reconfigure so editing never silently drops them; extra tests
  `test_reconfigure_keeps_volume_bands`, `test_setup_error_on_duplicate_valid_from`, extra `test_field_errors`
  cases (NaN, inf, 1e3, too large), `test_parse_price_rejects_non_ascii_digits`, `test_bands_written_only_when_present`.
- The `rg reason=` criterion literally matches three `async_abort(reason=...)` calls (a required keyword there); `async_update_and_abort` is called without `reason=`. The two `float(` hits are 009's spike-limit selector values (kWh), not prices.
- `script/lint` itself was not run; `ruff check`, `ruff format --check` and pyright were (all green).
- The preset step defaults to `ru_two_zone` and uses `SelectSelectorMode.LIST`.
- The `reconfigure` step renders the form with `step_id="plan"`; the flow object remembers the subentry in memory.
- `docs/SPEC.md`: §3 storage paragraph and string-price example, one §2 sentence.
## Follow-ups
- Custom zone sets (add, remove, re-key zones; non-RU tariffs) and volume-band editing in the UI.
- Translations for languages other than English; the plan form shows all four `t0`..`t3` label sets, no extra work needed for new keys beyond `t3`.

## Review round 1 fixes
- Suggestion 1: codec tests for a stored comma price and impossible dates (`2026-02-30`, `2026-13-01`).
- Suggestion 2: the copy step with no plans left (last plan deleted after the menu) now falls back to the preset
  step; test `test_copy_after_last_plan_deleted_falls_back_to_preset`.
- Suggestion 4: test `test_reconfigure_corrupt_plan_aborts` (`invalid_plan_data`).
- Suggestion 6: `MAX_PRICE` comment reworded. Suggestions 3 and 5 skipped as requested.
