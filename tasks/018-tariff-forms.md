# 018 — Tariff forms: add a tariff, its versions and rename

Status: in-review (round 1: CHANGES_REQUESTED; round 2: APPROVE)
Roadmap: stage 4 follow-up (configuration v2, task 2 of the split in `docs/CONFIG-DESIGN.md`; stacked on 017)
Spec sections: SPEC §2 (storage, reload), §3 (tariff model, rules, storage), §6 (min HA 2025.4);
`docs/CONFIG-DESIGN.md` (on `master`) "Add tariff", "Tariff (⚙ on its row)", "Validation rules", task split 018

> Planner decisions are marked **(D-n)**. The ones that are product choices are repeated under
> "Open questions" so they can be confirmed in PR review.

## Goal
On the integration page in *Settings → Devices & services*, users can **add a tariff** ("Add tariff"): a name,
a base (single-rate, two-zone, three-zone, custom zones, or a copy of an existing tariff), an id prefilled
from the name, and a first version with prices and hours. Each tariff is one config subentry of type `tariff`
(017 storage). The ⚙ on a tariff row opens a **tariff menu** with three actions: add a new version, edit or
delete a version, and rename the tariff (display name and id). Every change is validated strictly with
`engine/tariff_config.py` against the **whole** configuration, so the stored `applied`/`compare` options stay
valid too. Errors are shown at the zone or field that caused them. Any change reloads the entry, which
re-prices all past hours (principle 3). Deleting a tariff uses Home Assistant's built-in subentry delete; the options are reconciled afterwards
(D-10): a deleted applied tariff is removed from the applied history.

## Context

### Current state (after 017)
- `engine/tariff_config.py`: `config_from_data(document)` parses `{tariffs, applied, compare}` strictly and
  raises `TariffValidationError`. `Tariff(id, name, versions: tuple[TariffPlan, ...])` holds resolved plans, so
  every version has its full zones (key, name, price, periods). `default_compare`, `effective_schedule`.
- `engine/presets.py::PRESET_ZONES`: `single_rate` (`t0`), `ru_two_zone` (`t1` Day, `t2` Night),
  `ru_three_zone` (`t1` Peak, `t2` Night, `t3` Semi-peak). A preset version can override **prices and hours
  only**. It cannot override zone names.
- `engine/plan_codec.py`: `parse_price` (accepts `,` as the decimal separator, rejects signs, exponents and
  NaN; `MAX_PRICE`), `parse_periods` / `format_periods` (`"07:00-10:00, 17:00-21:00"`).
- `__init__.py`: `async_setup_entry` builds the document from all `tariff` subentries plus
  `settings.applied`/`settings.compare`, and raises `ConfigEntryError` if it is invalid. `RuntimeData(settings,
  tzinfo, tariffs, schedule)`. One update listener reloads the entry on any options or subentry change.
- `config_flow.py`: `VERSION = 2`. No subentry types are registered yet (017 removed the `tariff_plan` flow), so
  the integration page has no "Add tariff" action today.
- `settings.py`: `applied` is a tuple of `(iso_date, tariff_id)`; `compare` is `tuple[str, ...] | None`;
  `settings_to_options` writes both only when they are set.

### HA API checked (2026-11-06)
Core [config_entries.py @2025.4.0](https://github.com/home-assistant/core/blob/2025.4.0/homeassistant/config_entries.py),
[data_entry_flow.py @2025.4.0](https://github.com/home-assistant/core/blob/2025.4.0/homeassistant/data_entry_flow.py),
[components/config/config_entries.py @dev](https://github.com/home-assistant/core/blob/dev/homeassistant/components/config/config_entries.py);
frontend [show-dialog-sub-config-flow.ts @20250401.0](https://github.com/home-assistant/frontend/blob/20250401.0/src/dialogs/config-flow/show-dialog-sub-config-flow.ts)
(the frontend release for HA 2025.4), [ha-form-expandable.ts @20250401.0 and @dev](https://github.com/home-assistant/frontend/blob/dev/src/components/ha-form/ha-form-expandable.ts),
[ha-form.ts @dev](https://github.com/home-assistant/frontend/blob/dev/src/components/ha-form/ha-form.ts).
Background: [config subentries (2025-02-16)](https://developers.home-assistant.io/blog/2025/02/16/config-subentries),
[subentry flow changes (2025-03-24)](https://developers.home-assistant.io/blog/2025/03/24/config-subentry-flow-changes).
The API facts that task 010 checked still hold (see `tasks/010-tariff-plan-subentries.md` "HA API checked").
- `ConfigFlow.async_get_supported_subentry_types(cls, config_entry)` (`@classmethod @callback`) registers the
  flow. The row's ⚙ / "reconfigure" action appears because `async_step_reconfigure` exists.
- `ConfigSubentryFlow.async_create_entry(*, title, data, unique_id, ...)` works only with source `user`.
  `async_update_and_abort(entry, subentry, *, unique_id=, title=, data=)` calls
  `ConfigEntries.async_update_subentry` and aborts with `reconfigure_successful`. 2025.4.0 has **no** `reason=`
  parameter and **no** `async_update_reload_and_abort`, so use only `async_update_and_abort` without `reason=`.
  Also available: `_get_entry()`, `_get_reconfigure_subentry()`, `self.source`.
- `async_update_subentry` with a new `unique_id` rejects duplicates (`_raise_if_subentry_unique_id_exists`).
  `async_add_subentry` does the same. The flow checks ids itself first, so users get a field error, not an abort.
- `FlowHandler.async_show_menu(*, step_id, menu_options, description_placeholders)` is inherited by
  `ConfigSubentryFlow`. The 2025.4 sub-flow dialog renders menus (`config_subentries.<type>.step.<step>.title`,
  `.description` as **markdown**, `.menu_options.<option>`). A markdown table in the description therefore works.
- Sections: `data_entry_flow.section(schema, {"collapsed": bool})` exists in 2025.4.0. Submitted values are
  nested: `{section_key: {field: value}}`. `add_suggested_values_to_schema` recurses into sections **and mutates
  the section object in place**, so build a fresh schema on every call. Translations:
  `step.<step>.sections.<section>.name` / `.description` and nested `data` / `data_description`.
- **Errors inside sections are not shown at the field.** In 2025.4 and dev, `ha-form-expandable` passes no
  `error` to its inner form. `ha-form` shows an error keyed by a **top-level** name (a section key counts) as
  an alert above that item, and `errors["base"]` at the top. So per-zone errors are keyed by the **section key**
  (D-6). Error strings and regular-field helpers are localized **with** `description_placeholders`. Field
  **labels** and section **names** are localized **without** them (2025.4 frontend), so they cannot name a zone
  dynamically.
- **No veto on subentry deletion.** `config_entries/subentries/delete` calls
  `ConfigEntries.async_remove_subentry` directly. That removes the subentry, fires the update listeners, and
  calls no integration hook (2025.4.0 and dev). See D-10 for how deletion of an applied tariff is handled.
- Update listeners: `_async_update_entry` (used by `async_update_entry`, `async_add_subentry` and
  `async_remove_subentry`) and `async_update_subentry` start each listener as a task. On HA 2025.4 the task is
  scheduled lazily; on the latest HA it is started **eagerly**, in the middle of the caller's update. A flow that
  writes the options and then the subentry in two synchronous calls is therefore only safe if the listener yields
  once before it reads the configuration. D-8 and D-9 rely on that yield (`await asyncio.sleep(0)` in the listener),
  and tests pin it.
- `homeassistant.util.slugify(text, separator="_")` (available in 2025.4) transliterates non-Latin names, for
  example Cyrillic. It is used only in the flow module. The engine stays stdlib-only.

### Design decisions
- **D-1 Module layout.** Pure editing logic goes in a new engine module, `engine/tariff_edit.py` (stdlib
  only, unit-tested, counts toward the 95 % gate). The HA flow goes in a new `tariff_flow.py`
  (`TariffSubentryFlow`). `config_flow.py` registers `{SUBENTRY_TYPE_TARIFF: TariffSubentryFlow}`.
- **D-2 Engine helpers** (`engine/tariff_edit.py`; names are binding, exact signatures are up to the
  implementer):
  - `ZoneInput(key, name, price: Decimal, periods: tuple[Period, ...])` (frozen dataclass).
  - `normalize_price(text) -> str`: `parse_price`, then `format(value, "f")` (`"10,30"` → `"10.30"`).
  - `unique_tariff_id(base: str, taken: Collection[str]) -> str`: keeps only `[a-z0-9_]`, falls back to
    `tariff` when the result is empty, truncates to 32 characters, and adds `_2`, `_3`, … within the 32-char
    limit when the id is taken.
  - `first_version_doc(valid_from, zones: Sequence[ZoneInput], preset: str | None) -> dict`: when `preset` is
    given and the zone keys **and names** equal the preset's, it writes `{valid_from, preset, prices, hours?}`.
    `hours` lists only the zones whose periods differ from the preset. Otherwise it writes explicit `zones` (D-4).
  - `later_version_doc(valid_from, prices: Mapping[str, Decimal], periods: Mapping[str, tuple[Period, ...]],
    inherited: Sequence[Zone]) -> dict`: `{valid_from, prices, hours?}`. `hours` lists only the zones whose
    periods differ from the inherited zones.
  - `replace_version(tariff_doc, old_valid_from: str | None, version_doc) -> dict`: inserts (`None`) or
    replaces a version and keeps the versions sorted. It does not mutate its input.
  - `delete_version(tariff_doc, valid_from) -> dict`: raises `TariffValidationError` for the only version. When
    the **first** version is deleted, the next one becomes self-contained: if the deleted version used a preset,
    it gets that preset plus its own prices and its resolved hours overrides. Otherwise it gets explicit zones
    with its resolved names, prices and hours. The resolved zones of every remaining version do not change.
  - `diagnose_hours(zones: Sequence[tuple[str, tuple[Period, ...]]]) -> HoursProblems(uncovered:
    tuple[int, ...], overlapping: frozenset[str])`: lists the hours that no zone covers and the zone keys that
    share an hour with another zone.
  - `rename_references(applied, compare, old_id, new_id)`: returns `applied` (`(from, id)` pairs) and `compare`
    (or `None`) with `old_id` replaced.
  - `versions_table(tariff: Tariff) -> str`: a markdown table with the columns *Valid from* and *Prices*, one row
    per version, prices written as `t1 10.30 · t2 4.43` (zone keys in version order).
- **D-3 Add-tariff steps** (source `user`):
  1. `user` (form): `name` (text, required, not blank → `blank_name`) and `base` (select, `translation_key`
     `tariff_base`): `single_rate`, `ru_two_zone`, `ru_three_zone`, `custom` and `copy`. `copy` is offered only
     when a tariff exists. The default is `ru_two_zone`.
  2. `copy` (form, only for `copy`): `source` (select; value = tariff id, label = tariff name). The default is
     the last tariff in creation order.
  3. `custom_zones` (form, only for `custom`): `count` (number box, 1 to `MAX_ZONES` = 6, default 2).
  4. `tariff_id` (form): `id`, suggested as `unique_tariff_id(slugify(name), existing ids)`. Errors:
     `invalid_id` (not `^[a-z0-9_]{1,32}$`) and `id_taken`. The ids are shown on their own step because a form
     cannot update one field while the user types in another (design doc).
  5. `first_version` (form): `valid_from` (`DateSelector`, required, no default) and one **expanded** section
     per zone, `zone_1` … `zone_N`, in zone order. Each section has `name`, `price` and `hours` (text), plus
     `key` for `custom` only. Suggested values:
     - preset base: the preset's names and hours, with empty prices;
     - `copy`: the source's **latest** version, resolved (names, prices, hours), with the same base as the
       source's first version (its preset if it has one, otherwise explicit zones);
     - `custom`: keys `t1` … `tN`, empty names, prices and hours.

     On success, `async_create_entry(title=name, data={id, name, versions: [first_version_doc(...)]},
     unique_id=id)`.
- **D-4 Presets and renamed zones.** The preset form of a version cannot express changed zone names. If the
  user changes a zone name of a preset-based first version, it is stored with explicit `zones` instead of the
  preset. Prices and hours alone keep the preset form (`hours` overrides).
- **D-5 Tariff menu** (source `reconfigure`). `reconfigure` shows a menu with `new_version`, `select_version`
  and `rename`. Its description placeholders are `name`, `id` and `versions` (D-2 `versions_table`), plus
  `applied`, a sentence such as "Applied from 2026-01-01" or "Not applied" taken from the options.
  - `new_version` (form): `valid_from` (`DateSelector`; suggested = today in the integration time zone if that
    is after the latest version, otherwise no suggestion). Top-level `price_1` … `price_N` are prefilled from
    the latest version. Their helper text (`data_description`) uses placeholders `zone_1` … `zone_N` =
    `"<name> (<key>)"`. A **collapsed** section `hours` holds `hours_1` … `hours_N`, prefilled from the latest
    version's resolved hours. Errors: `valid_from_taken`. A date before the first version is allowed (D-12). Stored with `later_version_doc`, where the
    inherited zones are those of the version in force on the day before `valid_from`.
  - `select_version` (form): `version` (select of `valid_from` dates, newest first). It continues to
    `edit_first_version` for the first version, otherwise to `edit_version`.
  - `edit_first_version` (form): the `first_version` form without `key` (zone keys never change, SPEC §3),
    prefilled from the stored version, plus `delete` (boolean, default off).
  - `edit_version` (form): the `new_version` form prefilled from that version, plus `delete`.
  - When `delete` is on, all other fields are ignored and `delete_version` is applied. Deleting the only
    version → error `last_version` (delete the tariff instead).
  - `rename` (form): `name` (`blank_name`) and `id` (`invalid_id`, `id_taken`; the tariff's own id is allowed).
  - Every successful action ends with `async_update_and_abort(entry, subentry, title=, data=, unique_id=)`.
- **D-6 Validation and errors.** Field parsing first: `price` → `invalid_price`, `hours` → `invalid_hours`,
  `name` → `blank_name`, `key` → `invalid_zone_key` / `duplicate_zone_key`. A problem inside a section is
  reported under the **section key** (`errors["zone_2"] = "invalid_price"`, `errors["hours"] =
  "invalid_hours"`); top-level fields use their own key. Next, `diagnose_hours`: every overlapping zone's
  section gets `hours_overlap`, and uncovered hours give `errors["base"] = "hours_uncovered"` with the
  placeholder `hours` (for example `22:00-23:00`). Last, the **whole** document goes through
  `config_from_data`: all tariff subentries with this one replaced, plus `applied` and `compare` from the
  options. An applied `from` with no version → `errors["valid_from"] = "applied_without_version"`. Any other
  `TariffValidationError` → `errors["base"] = "invalid_tariff"` with the placeholder `detail` (the engine
  message). Always pass every placeholder that the step's strings use (as an empty string when unused), and keep
  the submitted values in the form after an error. Prices are text fields, never `NumberSelector`, so money
  never passes through `float`.
- **D-7 Positional zone labels.** Section keys are `zone_1` … `zone_6` and are translated as "Zone 1" …
  "Zone 6". The field labels inside them are generic (Name, Price, Hours, Key). Labels cannot carry
  placeholders in 2025.4 (see API notes). The step description lists the zones as a placeholder `zones`, for
  example `Zone 1: Day (t1) · Zone 2: Night (t2)`.
- **D-8 Rename with an id change.** In one step, with no `await` between the two calls:
  `hass.config_entries.async_update_entry(entry, options=...)` with `rename_references` applied, then
  `async_update_and_abort(..., unique_id=new_id, title=name, data={..., "id": new_id})`. The first reload sees
  both changes.
- **D-9 First-version date and `applied`.** When the first version's `valid_from` changes, every `applied`
  item for this tariff whose `from` equals the old date moves with it (same atomic pattern as D-8). Other
  `applied` items are not touched. If the result is invalid, the form shows `applied_without_version`. A moved
  start must stay strictly between its neighbouring `applied` items; otherwise the form shows `applied_order`
  (on the `delete` field for a deletion). Deleting the first version moves a matching `applied` start the same way.
- **D-10 Reconcile on reload** (`__init__.py`). The update listener first yields once, then runs
  `_async_reconcile(hass, entry)`. When reconcile changes the options, the listener returns without reloading,
  because that change fires the listener again. Otherwise it reloads. Rules (nothing is done when the entry is
  not loaded; it just reloads):
  1. **Tariff deleted:** ids in `options.applied` with no `tariff` subentry are removed from the history. The
     previous item continues over the freed period; adjacent items with the same tariff merge; when the first
     item is removed, the next item's `from` moves to the removed `from` if that tariff has a version valid on that
     date, otherwise it keeps its own date (hours before it stay unpriced). If nothing remains applied but tariffs
     do, the first remaining tariff (subentry order) is applied from its first version. With no tariffs left,
     `applied` is removed (nothing priced, as on a fresh install).
  2. **Compared tariff deleted:** an explicit `compare` list that names a missing id → drop that id from the
     options.
  3. **First tariff:** the previous load had no tariffs, a tariff now exists, and `applied` is empty →
     `applied = [{from: <its first valid_from>, tariff: <id>}]`. If several exist, use the first in creation
     order. Without this rule nothing could be priced until the options menu (019) exists.
- **D-12 Version before the first one.** A new version may be dated before the current first version. It becomes
  the first version and gets explicit `zones` resolved from the former first version (names, keys, the entered
  prices and hours); the former first version is unchanged. `applied` items are not moved by this.
- **D-11 No new entities or platforms** (principle 1). Recorder access is unchanged (principle 5).

## Files
- create: `custom_components/energy_cost_stats/engine/tariff_edit.py` — D-2.
- create: `custom_components/energy_cost_stats/tariff_flow.py` — `TariffSubentryFlow` (D-3 … D-9).
- modify: `custom_components/energy_cost_stats/config_flow.py` — `async_get_supported_subentry_types`.
- modify: `custom_components/energy_cost_stats/const.py` — `MAX_ZONES = 6`, the form keys, the base ids.
- modify: `custom_components/energy_cost_stats/__init__.py` — `_async_reconcile` (D-10).
- modify: `custom_components/energy_cost_stats/strings.json` — `config_subentries.tariff` (`entry_type`
  "Tariff"; `initiate_flow.user` "Add tariff", `initiate_flow.reconfigure` "Edit tariff"; all steps of D-3/D-5
  with `sections` for `zone_1` … `zone_6` and `hours`; menu options; the errors of D-3/D-5/D-6; abort
  `reconfigure_successful` written as literal text). Also `selector.tariff_base.options`.
- modify: `custom_components/energy_cost_stats/translations/en.json` — identical to `strings.json`.
- create: `tests/unit/test_tariff_edit.py`
- create: `tests/integration/test_tariff_flow.py`
- modify: `tests/integration/test_tariff_model.py` — reconcile tests (D-10).
- modify: `docs/SPEC.md` — §3 storage paragraph (the forms exist: steps in brief, D-4, D-9, D-10), §2 one line on
  reconcile. Replace "The `tariff` forms and the options menu come in task 018" with the accurate state (the
  options menu is task 019).

11 files.

## Tests to write first
Generic data only: tariff "Two-zone" (`two_zone`), day `10.30`, night `4.43`; a second version from 2026-07-01
with day `11.00`, night `4.60`; dates in 2026; sensor `sensor.plug_01` where statistics are needed.

| Level | Test | Asserts |
|---|---|---|
| unit | `tests/unit/test_tariff_edit.py::test_normalize_price` | `"10,30"` → `"10.30"`, `" 4.43 "` → `"4.43"`, `"0"` → `"0"`; `"-1"`, `"1e3"`, `"abc"` → `TariffValidationError`. |
| unit | `::test_unique_tariff_id` | `("two_zone", {})` → `two_zone`; taken → `two_zone_2`, then `_3`; `""` → `tariff`; a 40-char base → 32 chars, also with a suffix; result always matches `^[a-z0-9_]{1,32}$`. |
| unit | `::test_first_version_doc_keeps_preset` | Two-zone keys and names unchanged → `{valid_from, preset: ru_two_zone, prices}` with no `hours`; `t1` hours `06:00-23:00` and `t2` `23:00-06:00` → `hours` lists both, not unchanged ones; `config_from_data` accepts the tariff. |
| unit | `::test_first_version_doc_renamed_zone_is_explicit` | Preset with `t1` renamed "Peak day" → explicit `zones` with all keys, names, prices and hours; no `preset` key (D-4). |
| unit | `::test_first_version_doc_custom` | `preset=None`, three custom zones → explicit `zones` in the given order. |
| unit | `::test_later_version_doc` | Same hours as inherited → only `prices`; one zone changed → `hours` for that zone only. |
| unit | `::test_replace_version` | Insert keeps the versions sorted; replacing by old date (also with a date change) replaces exactly one; the input dict is unchanged. |
| unit | `::test_delete_version` | Middle/last deletion removes it; deleting the only version raises; deleting the first version of a preset tariff → the next version has `preset` and the resolved zones of every remaining version are unchanged (compare `config_from_data` output); the same for an explicit-zones tariff (next gets `zones`). |
| unit | `::test_diagnose_hours` | Full coverage → no problems; `t1 07:00-22:00` + `t2 23:00-07:00` → uncovered `(22,)`; `t1 06:00-23:00` + `t2 23:00-07:00` → overlapping `{t1, t2}`. |
| unit | `::test_rename_references` | `applied` and an explicit `compare` renamed; `compare=None` stays `None`; other ids untouched. |
| unit | `::test_versions_table` | Two versions → header plus two rows, `2026-01-01`, `t1 10.30 · t2 4.43`. |
| integration | `tests/integration/test_tariff_flow.py::test_subentry_type_registered` | `async_get_supported_subentry_types(entry) == {"tariff": TariffSubentryFlow}`; the class has `async_step_reconfigure`. |
| integration | `::test_add_two_zone_tariff` | `user` (`name "Two-zone"`, `base ru_two_zone`; no `copy` option with no tariffs) → `tariff_id` with suggested `two_zone` → `first_version` with sections `zone_1`, `zone_2`, suggested names `Day`/`Night`, hours `07:00-23:00`/`23:00-07:00`, no prices → submit `10,30` / `4.43`, `valid_from 2026-01-01` → `CREATE_ENTRY`; subentry `unique_id == "two_zone"`, `title == "Two-zone"`, data `{id, name, versions: [{valid_from, preset: ru_two_zone, prices: {t1: "10.30", t2: "4.43"}}]}`; after reload the entry is `LOADED`, `options["applied"] == [{"from": "2026-01-01", "tariff": "two_zone"}]` (D-10 rule 3) and `runtime_data.schedule` prices hour 12 of 2026-01-02 at `10.30`. |
| integration | `::test_id_slug_and_errors` | Name `"Тариф День"` → suggested id is ASCII and matches the id pattern; `id "Bad Id"` → `invalid_id`; an existing id → `id_taken`; blank name → `blank_name` on `user`. |
| integration | `::test_custom_zones` | `custom`, `count 3` → sections with a `key` field (suggested `t1`..`t3`); duplicate keys → `duplicate_zone_key` on the section; valid → explicit `zones` stored. |
| integration | `::test_copy_tariff` | With `two_zone` (two versions): `copy` offered, default source is the last tariff; `first_version` prefilled from the **latest** version (`11.00`/`4.60`); stored with `preset: ru_two_zone`; the new tariff is not applied (rule 3 does not fire) and appears in `runtime_data.tariffs.compare`. |
| integration | `::test_first_version_errors` | Parametrized: `zone_1.price "abc"` → `errors == {"zone_1": "invalid_price"}`; `zone_1.hours "7-23"` → `invalid_hours`; `zone_1.hours "07:00-22:00"` → `base: hours_uncovered`, placeholder `hours` contains `22:00`; `zone_1.hours "06:00-23:00"` → `zone_1` and `zone_2` both `hours_overlap`; no subentry created; submitted values kept. |
| integration | `::test_menu_shows_versions` | Reconfigure `two_zone` → `MENU` with options `["new_version", "select_version", "rename"]`; `description_placeholders["versions"]` contains both dates and `t1 10.30`. |
| integration | `::test_new_version_reprices` | `new_version` prefilled with `10.30`/`4.43`; submit `2026-07-01`, `11.00`/`4.60` → `ABORT reconfigure_successful`; stored version has only `valid_from` + `prices`; after reload hour 12 of 2026-07-02 costs `11.00` and of 2026-06-30 `10.30`. Duplicate date → `valid_from_taken`; a date before the first version is accepted and stored as the new first version (see `::test_new_version_before_the_first_version`). |
| integration | `::test_new_version_hours_override` | Changing `hours.hours_1` to `06:00-23:00` and `hours_2` to `23:00-06:00` → stored `hours` for both; leaving them unchanged → no `hours` key. |
| integration | `::test_edit_version_retroactive` | `select_version` → `edit_version` for 2026-07-01, price `11.20` → after reload past hours in July cost `11.20` (principle 3). Editing the first version → `edit_first_version` without `key` fields. |
| integration | `::test_edit_first_version_moves_applied` | Auto-applied `two_zone` from 2026-01-01; move the first version to 2025-12-01 → `applied[0]["from"] == "2025-12-01"` and the entry is `LOADED` (D-9). |
| integration | `::test_edit_version_applied_without_version` | Options seeded with `applied: [{2026-01-01, other}, {2026-03-01, two_zone}]` (`two_zone` first version 2026-01-01; `other` a second tariff from 2026-01-01); moving `two_zone`'s first version to 2026-04-01 → `errors == {"valid_from": "applied_without_version"}`; subentry data and options unchanged. |
| integration | `::test_delete_version` | Delete 2026-07-01 → one version left, July re-priced at `10.30`; delete the only version → `last_version`; delete the first of two (preset) → the remaining version is self-contained and prices are unchanged. |
| integration | `::test_rename_name_only` | `rename` with a new name → subentry title and data `name` change, `id` and `applied` unchanged. |
| integration | `::test_rename_id_updates_references` | Options with `applied` on `two_zone` and `compare: ["two_zone"]`; rename id to `day_night` → subentry `unique_id`/data id `day_night`, `applied` and `compare` reference `day_night`; after `async_block_till_done()` the entry is `LOADED` and no `ConfigEntryError` was logged (D-8 atomicity). Existing id → `id_taken`; own id accepted. |
| integration | `::test_no_entities` | After adding a tariff, `hass.states.async_all()` holds no entity of this domain. |
| integration | `tests/integration/test_tariff_model.py::test_deleting_*applied*` | Deleting an applied tariff: the previous item continues; the first item is taken over by the next tariff (moved start, or its own later start); neighbours merge; the only applied tariff → the next remaining tariff is applied from its first version; the last tariff → no `applied`, no schedule. |
| integration | `tests/integration/test_tariff_flow.py::test_*must_not_reorder_applied` | Moving or deleting the first version so that the applied history would be reordered → `applied_order`; subentry data and options unchanged. |
| integration | `::test_deleting_unapplied_tariff` | Deleting a tariff that is not applied removes it; when it was in an explicit `compare`, the id is dropped from `options["compare"]`; the entry is `LOADED`. |
| integration | `::test_first_tariff_auto_applied_only_once` | First tariff added → `applied` set; a second tariff → `applied` unchanged; an entry that already has tariffs and an empty `applied` stays unapplied after reload. |

## Acceptance criteria
Linux devcontainer / CI:
- [x] `script/test` → all levels pass; engine coverage ≥ 95 % with `engine/tariff_edit.py` listed.
- [x] `script/lint` → exit 0; `uv run --group ha pyright` → 0 errors.
- [ ] CI green on both matrix legs (HA 2025.4.0 / latest), plus `hassfest` (validates
  `config_subentries.tariff`, its `sections` and `selector.tariff_base`) and `hacs`.

Either environment:
- [x] `uv run pytest -m unit` → passes, including `test_engine_has_no_forbidden_imports` and
  `test_strings_match_en_translation`.
- [x] `uv run ruff check .` and `uv run ruff format --check .` → exit 0.

Mechanical checks:
- [x] `rg -n "async_update_reload_and_abort" custom_components/` → no matches; `rg -n "async_update_and_abort\(.*reason="
  custom_components/` → no matches.
- [x] `rg -n "NumberSelector|float\(" custom_components/energy_cost_stats/tariff_flow.py` → only the `count`
  selector of `custom_zones` (no price passes through a number or `float`).
- [x] `rg -n "homeassistant" custom_components/energy_cost_stats/engine/tariff_edit.py` → no matches.
- [x] `rg -n "components.recorder" custom_components/energy_cost_stats` → only `recorder_adapter.py`.
- [x] No new entity platforms: `rg -n "async_forward_entry_setups|PLATFORMS" custom_components/` → no matches.
- [ ] No files touched outside "Files"; generic examples only (no real entity ids, prices, paths or hosts).
- [ ] Manual (optional, human): in `script/develop`, add a two-zone tariff, add a version, edit and delete it,
  rename the id, and delete the applied tariff (it leaves the applied history as described in D-10). The log shows
  only reloads.

## Out of scope
- Options menu: applied tariff / history, compare list, general settings (task 019). Until then `applied` is set
  only by D-10 rule 3, D-9 and the 017 migration.
- Sensor selection (020), YAML mode, read-only UI and export (021), the card's comparison section (022), the
  sidebar panel (023), and Russian translations (024).
- Changing a tariff's zone set from the forms (a later version with its own `preset`/`zones`, adding or removing
  zones of an existing tariff). The model supports it, and YAML (021) will expose it.
- Richer integration-page rows (type label, version count, current prices): HA shows only the subentry title.
- Weekday-dependent hours and volume bands (reserved).

## Open questions
Product choices made by the planner, to confirm in PR review:
- **D-10 rule 3:** auto-apply the first tariff from its first version, so a fresh install prices immediately
  without the 019 options menu. Alternative: leave it unpriced until 019.
- **D-10 rule 1 (resolved by the author):** deleting an applied tariff is allowed and removes it from the applied
  history as described in D-10 (no restore, no notification).
- **D-9:** an `applied` start equal to the old first-version date follows that date when it moves. Alternative:
  never touch `applied` from the tariff forms.
- **D-3 copy:** copy only the source's latest version, as the first version of the new tariff, with an empty
  date. Alternative: copy the full version history.
- **D-4:** renaming a zone of a preset-based version stores explicit zones (the YAML export then shows `zones`
  instead of `preset`).
- **D-3/D-7:** custom tariffs are limited to 6 zones, default keys `t1`…`tN`, and zone sections have positional
  labels ("Zone 1").
- **D-12 (resolved by the author):** a new version may be dated before the first version and becomes the new first
  version.

## Implementation notes
- All eleven files of the list were touched, plus `docs/SPEC.md`; the unit and integration suites pass (607 tests),
  `engine/tariff_edit.py` has 100 % coverage, `ruff` and `pyright` are clean. CI on both matrix legs, `hassfest`
  and `hacs` are not run locally.
- Home Assistant limitations versus `docs/CONFIG-DESIGN.md`, as the task already planned: errors inside a section are
  keyed by the section name (`zone_1`, `hours`); a subentry deletion cannot be refused, so the options are
  reconciled after it (D-10).
- **Deviation from D-8/D-9 (listener timing).** The task assumed update listeners are scheduled as tasks. On the
  latest HA they start eagerly, in the middle of the caller's first update, so the first reload saw the new options
  but the old subentry (setup error "applied: tariff has no version valid on ..."). The update listener now yields
  once (`await asyncio.sleep(0)`) before reconciling and reloading; the flows still write options and subentry in two
  synchronous calls. The rename and first-version-date tests pin this.
- Deleting the first version also moves an `applied` item that started on the old first date to the new first date
  (same rule as D-9), asserted in `test_delete_first_version_keeps_prices`. A move (edit or delete) that would
  reorder the applied history is rejected with `applied_order`; the delete path reports `applied_order` and
  `applied_without_version` on the `delete` field. The check lives in `engine/tariff_edit.py`
  (`move_applied_start`), as does `remove_from_applied` for deletions.
- The double reload of two-write actions is not coalesced: the invariant is that all writes of one action happen in one
  synchronous run, and a second reload is harmless. The `_store` docstring says so.
- Editing a later version that carries its own zone set (`preset` or `zones`) keeps that form (zones and names are
  not editable there). New or edited versions whose inherited zones differ from the latest version's zone keys are
  rejected with `invalid_tariff`.
- Extra engine helper `format_hours` (the `hours_uncovered` placeholder, for example `22:00-23:00`).
- Extra abort `invalid_stored_tariff` when a stored tariff cannot be parsed. The error `last_version` is attached to
  the `delete` field.
- `voluptuous_serialize` is not installed in the test environment, so frontend serialization of the schemas is not
  tested; the section/schema shapes follow HA's own sections examples.
- Reconcile keeps no snapshot: rule 3 fires only when the previous load (`runtime_data.tariffs`) had no tariffs, so
  an entry loaded with tariffs and no `applied` stays unapplied.

## Follow-ups
- Run the min-HA leg (2025.4.0) in CI; the new flow only uses 2025.4 API (`async_update_and_abort` without `reason`).
- Manual check in `script/develop` of the real frontend rendering of sections and the markdown version table.
- `remove_from_applied`: when several leading applied items are deleted, try the earliest deleted start where the
  next tariff has a version (fewer unpriced hours), not only the first one.
- Test editing an existing prices-only later version to a date before the first version.
