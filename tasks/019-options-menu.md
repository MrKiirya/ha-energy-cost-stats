# 019 — Options menu: applied tariff history, comparison list, general settings

Status: in-review (round 1: CHANGES_REQUESTED; round 2: APPROVE)
Roadmap: stage 4 follow-up (configuration v2, docs/CONFIG-DESIGN.md "Tasks" row 019)
Spec sections: SPEC §2 (settings / options flow), §3 (applied, compare, storage), §6 (compatibility);
docs/CONFIG-DESIGN.md "Configure (options)", "Applied history and comparison", "Full configuration (YAML)"

## Goal
"Configure" on the integration opens a **menu** instead of a single form. The user can edit the **applied
tariff history** (use one tariff for everything, add a change, re-date / re-assign / delete a change) with a table
of the history in the step description; choose which tariffs are **compared** (default: every tariff never
applied); and edit the **general** settings (time zone, spike limit, the "show in sidebar" flag with title and
icon). The energy sensor selection and per-device spike limits stay available unchanged under a "Sensors" entry.
Every change is checked by the engine before it is stored, so a saved configuration always sets up, and every
change re-prices all past hours through the existing reload.

## Dependencies
- **Stacked on 017** (merged into this stack): tariff subentries, `applied` / `compare` in `entry.options`,
  `engine/tariff_config.py`, `settings.py` with `applied` / `compare`.
- **Task 018 (tariff subentry forms) is a soft dependency.** 019 does not need 018's code: it only *reads* the
  `tariff` subentries, and its tests seed them with `MockConfigEntry(subentries_data=[ConfigSubentryData(...)])`
  as `tests/integration/test_tariff_model.py` already does. Without 018 a user simply cannot create tariffs in
  the UI yet, so the applied / compare steps abort with `no_tariffs`.
- **Shared files with 018:** `strings.json` and `translations/en.json` (018 edits `config_subentries`, 019 edits
  `options`), possibly `const.py`. Branch 019 from the 018 branch once 018 is in review, or rebase onto it;
  keep the edits to the `options` section to avoid conflicts.
- **Contract 019 relies on from 018:** renaming a tariff ID updates `applied` / `compare` in `entry.options`, and
  deleting a tariff is reconciled afterwards (task 018, D-10): an applied tariff leaves the history (the previous
  entry continues), a deleted id is dropped from an explicit `compare` list. 019 keeps the stored option format
  of 017 unchanged so 018 can rewrite it.

## Context
### Current state (on this branch)
- `config_flow.py::EnergyCostStatsOptionsFlow.async_step_init` is one form (time zone, spike check, spike limit,
  entities, "edit per-device limits") plus `async_step_device_limits`. Both already carry `applied` /
  `compare` through (`dataclasses.replace`), covered by `test_options_flow_keeps_applied_and_compare` and
  `test_options_flow_device_limits_keeps_applied_and_compare`.
- `__init__.py::async_setup_entry` builds the configuration document from the `tariff` subentries plus
  `settings.applied` / `settings.compare` and calls `config_from_data`; a `TariffValidationError` raises
  `ConfigEntryError`. One update listener reloads the entry on any options or subentry change (kept; see below).
- `engine/tariff_config.py::_applied` validates the history (unknown tariff, duplicate `from`, no version valid on
  `from`) but only with free-text messages, so a form cannot map a failure to a field error.

### Menu layout (this task)
`init` = `async_show_menu(step_id="init", menu_options=["sensors", "applied", "compare", "general"])`, order as in
CONFIG-DESIGN. **No** menu entries for "Export to YAML" (021) or a YAML-mode read-only view (021); 021 adds them.
"Sensors" hosts the *existing* entity picker and per-device limits unchanged until task 020 replaces it, so no
current setting becomes unreachable.

| Step | Kind | Content | Saves |
|---|---|---|---|
| `init` | menu | `sensors`, `applied`, `compare`, `general` | — |
| `sensors` | form | `entities` (energy sensors, multiple), `edit_device_limits` → `device_limits` | yes (as today) |
| `device_limits` | form | unchanged | yes |
| `general` | form | `time_zone`, `spike_check`, `spike_limit`, collapsed section `sidebar`: `show`, `title`, `icon` | yes |
| `applied` | menu | description: history table; options `applied_single`, `applied_add`, `applied_pick` (only when the history is non-empty) | — |
| `applied_single` | form | `tariff` (select), `from` (date, prefilled with the tariff's first `valid_from`) → replaces the whole history with one entry | yes |
| `applied_add` | form | `from` (date), `tariff` (select) → adds one change | yes |
| `applied_pick` | form | `change` (select: one option per entry, label `YYYY-MM-DD · <tariff name>`) | — |
| `applied_change` | form | `from`, `tariff` prefilled from the picked entry, `delete` (boolean) → re-date / re-assign / delete | yes |
| `compare` | form | `use_default` (boolean), `tariffs` (multi-select); description lists the default set | yes |

- **Saving model:** every leaf form validates and then ends the flow with `async_create_entry(data=<full
  options>)` (an options flow's `data` *replaces* `entry.options`, so all keys must be merged in). Options are
  re-read from `self.config_entry.options` at submit time, not cached when the flow starts, so a change made
  meanwhile (e.g. a rename in 018) is not overwritten. No in-flow "draft" of the history (see open questions).
- **Strict validation via the engine:** before saving, the candidate document (tariff subentry data + candidate
  `applied` + `compare`) is passed to `config_from_data`. Applied-history problems come back as a new
  `AppliedValidationError` with a machine-readable `code` and are shown at the `from` field:
  `duplicate_from` (another change already starts on that date), `no_version` (the tariff has no version valid
  on that date; placeholder `{first_valid_from}` gives the earliest allowed date), `unknown_tariff` (defensive,
  the select offers only existing ids). Any other `TariffValidationError` (should not happen for a loaded entry)
  shows the base error `invalid_config` with the engine message in a `{detail}` placeholder.
- **Empty history** is allowed (deleting the last change = nothing applied = every hour unpriced, SPEC §3); the
  `applied_change` description warns about this.
- **History table:** the `applied` menu description in `strings.json` contains the Markdown table header
  (`| From | Tariff |` + separator); the `{history}` placeholder holds only the rows (sorted by date, tariff
  *name* with `|` escaped, followed by the id in backticks), or one `| — | — |` row when empty. Flow
  descriptions are rendered as Markdown by the frontend.
- **Compare:** `use_default = true` stores **no** `compare` key (`settings.compare = None` → default = never
  applied, recomputed after every history change). `use_default = false` stores the selected ids as a list in the
  order of the tariffs (deterministic), an empty list meaning "compare nothing". Prefill: `use_default` = stored
  `compare is None`; `tariffs` = the stored list, or the current default set. Select options are
  `{value: id, label: name}`.
- **Panel settings** (CONFIG-DESIGN puts "show in sidebar (title, icon)" into General): new optional option key
  `panel: {show: bool, title: str, icon: str}`, parsed strictly by `settings.py` into a frozen `PanelSettings`
  (`None` when absent). Form defaults when absent: `show = false`, `title = "Energy cost"`,
  `icon = "mdi:cash-multiple"`. The key is written once the General form is saved. **The setting has no effect
  yet**; the sidebar panel itself is task 023 (see open questions).
- **Steps without tariffs:** `applied` and `compare` abort with `no_tariffs` ("Add a tariff first") when the entry
  has no `tariff` subentry. Corrupt stored options keep aborting with `invalid_options` (all steps).
- **Shared document builder:** move the document construction out of `__init__.py::async_setup_entry` into a
  pure helper `settings.py::tariff_document(settings, tariff_data)` (no HA imports; `tariff_data` = iterable of
  subentry data mappings) used by both setup and the options flow, so the flow validates exactly what setup
  will load.

### Engine change (pure Python)
`engine/tariff_config.py`:
```python
class AppliedValidationError(TariffValidationError):
    code: Literal["unknown_tariff", "duplicate_from", "no_version"]
    change: AppliedChange | None        # the offending entry (the later one for duplicate_from)
    first_valid_from: date | None       # for no_version: earliest date the tariff can start

def check_applied(tariffs: Sequence[Tariff], applied: Sequence[AppliedChange]) -> tuple[AppliedChange, ...]
    """Sort and validate; raise AppliedValidationError; return the sorted history."""
```
`_applied` parses the raw items and delegates to `check_applied`; existing messages and the
`TariffValidationError` contract of `config_from_data` stay as they are (subclass).

### Home Assistant APIs checked (minimum 2025.4.0 and current `dev`, 2026-11-06)
- `FlowHandler.async_show_menu` @2025.4.0: keyword-only `step_id`, `menu_options: Container[str]` (list or dict),
  `description_placeholders`; **no `sort` parameter** (added later on `dev`: `sort: bool = False`). → Use a
  list, do **not** pass `sort`. Source: [data_entry_flow.py @2025.4.0](https://github.com/home-assistant/core/blob/2025.4.0/homeassistant/data_entry_flow.py),
  [data_entry_flow.py @dev](https://github.com/home-assistant/core/blob/dev/homeassistant/data_entry_flow.py).
  On `dev`, omitting `step_id` is reported as an error (breaks in 2027.5) → always pass `step_id`.
- `section(schema, {"collapsed": True})` exists @2025.4.0 (`SectionConfig.collapsed`); input arrives nested under
  the section key; sections cannot be nested. Strings go under the step's `sections` key. Source: same files and
  [flow steps docs](https://contributors.home-assistant.io/core/integrations/flow-steps/).
- Menu labels: `options.step.<menu step>.menu_options.<option>` in `strings.json` (allowed by hassfest
  @2025.4.0: step keys `title`, `description`, `data`, `data_description`, `menu_options`, `submit`, `sections`).
  `menu_option_descriptions` is documented on current HA but **not** in the 2025.4.0 hassfest schema → do not use
  it; put explanations into the menu step `description`. Source:
  [hassfest translations.py @2025.4.0](https://github.com/home-assistant/core/blob/2025.4.0/script/hassfest/translations.py).
- `OptionsFlowWithReload` is not available in 2025.4.0 (introduced mid-2025, adopted by core integrations from
  July 2025), and it raises if the entry also has an update listener. → Keep `OptionsFlow` + the single update
  listener (already documented in SPEC §2). Source:
  [options flow docs](https://contributors.home-assistant.io/core/integrations/options-flow/),
  [2025.10 changelog](https://www.home-assistant.io/changelogs/core-2025.10/) (integrations still migrating).
- `self.config_entry` is available in steps, not in `__init__` (current flow already follows this).
- Selectors used, all present in 2025.4.0: `SelectSelector` (`options` as `SelectOptionDict` value/label,
  `multiple=True`, `mode=DROPDOWN`/`LIST`), `DateSelector` (value `"YYYY-MM-DD"` string, matching the stored
  `from` format), `BooleanSelector`, `TextSelector`, `IconSelector`, `NumberSelector`, `EntitySelector`.

## Files
- modify: `custom_components/energy_cost_stats/engine/tariff_config.py` — `AppliedValidationError`,
  `check_applied`; `_applied` delegates to it.
- modify: `custom_components/energy_cost_stats/settings.py` — `PanelSettings`, `panel` option key (strict
  parse / serialize, written only when set), `tariff_document(settings, tariff_data)`.
- modify: `custom_components/energy_cost_stats/__init__.py` — use `tariff_document` (no behaviour change).
- modify: `custom_components/energy_cost_stats/const.py` — `CONF_PANEL`, form-only keys (`use_default`,
  `tariffs`, `change`, `delete`, `from`, `tariff`, section `sidebar`), panel defaults, menu step ids.
- modify: `custom_components/energy_cost_stats/config_flow.py` — options flow as described above (menu, sensors,
  general, applied menu + 4 forms, compare). Config flow (`async_step_user`) unchanged.
- modify: `custom_components/energy_cost_stats/strings.json`, `translations/en.json` — `options` section: menu
  titles / descriptions / `menu_options`, new steps, the `sidebar` section, errors `duplicate_from`,
  `no_version`, `unknown_tariff`, `invalid_config`, abort `no_tariffs`.
- create: `tests/integration/test_options_menu.py` — new options flow tests.
- modify: `tests/integration/test_config_flow.py` — existing options tests navigate `init` → `sensors` /
  `general` instead of submitting `init` directly; assertions unchanged.
- modify: `tests/integration/test_settings.py` — panel and `tariff_document` tests.
- modify: `tests/unit/test_tariff_config.py` — `check_applied` tests.
- modify: `docs/SPEC.md` — §2 (options menu, `panel` key, saving/validation model), §3 (replace "The `tariff`
  forms and the options menu come in task 018" with the actual split: forms 018, options menu 019).

## Tests to write first
| Level | Test | Asserts |
|---|---|---|
| unit | `tests/unit/test_tariff_config.py::test_check_applied_sorts_valid_history` | unsorted valid changes come back sorted by `from_date` |
| unit | `tests/unit/test_tariff_config.py::test_check_applied_duplicate_from` | `AppliedValidationError`, `code == "duplicate_from"`, `change` is the second entry |
| unit | `tests/unit/test_tariff_config.py::test_check_applied_no_version_on_date` | `code == "no_version"`, `first_valid_from` = the tariff's first `valid_from` |
| unit | `tests/unit/test_tariff_config.py::test_check_applied_unknown_tariff` | `code == "unknown_tariff"` |
| unit | `tests/unit/test_tariff_config.py::test_config_from_data_raises_applied_error_subclass` | `config_from_data` with a bad history raises `AppliedValidationError`, which `isinstance(..., TariffValidationError)`; existing message tests still pass |
| integration | `tests/integration/test_settings.py::test_panel_round_trip` | `settings_to_options(settings_from_options(o)) == o` with a `panel` block |
| integration | `tests/integration/test_settings.py::test_panel_absent_is_none_and_not_written` | no `panel` key → `settings.panel is None`, serializing writes no `panel` key |
| integration | `tests/integration/test_settings.py::test_panel_rejects_malformed` | parametrized: not a mapping, unknown key, `show` not bool, blank `title`, blank `icon` → `SettingsError` |
| integration | `tests/integration/test_settings.py::test_tariff_document` | builds `{tariffs, applied}` (+ `compare` only when set) from subentry data + settings, same as setup did before |
| integration | `tests/integration/test_options_menu.py::test_init_is_menu` | `type is MENU`, `step_id == "init"`, `menu_options == ["sensors", "applied", "compare", "general"]` |
| integration | `test_options_menu.py::test_general_saves_and_keeps_other_options` | time zone + spike limit saved; `entities`, `device_spike_limits`, `applied`, `compare` unchanged; entry reloaded (`state is LOADED`, `runtime_data.settings` updated) |
| integration | `test_options_menu.py::test_general_prefills_current_values` | suggested values = stored time zone, spike check / limit, panel (or defaults when absent) |
| integration | `test_options_menu.py::test_general_saves_panel` | `{"sidebar": {"show": True, "title": "...", "icon": "mdi:..."}}` → `options["panel"]` |
| integration | `test_options_menu.py::test_general_rejects_invalid_limit` | `errors == {"spike_limit": "invalid_limit"}`, options unchanged |
| integration | `test_options_menu.py::test_applied_aborts_without_tariffs` | `applied` and `compare` → abort `no_tariffs` |
| integration | `test_options_menu.py::test_applied_menu_shows_history` | menu options `["applied_single", "applied_add", "applied_pick"]`; `description_placeholders["history"]` has one row per change, sorted, with tariff names |
| integration | `test_options_menu.py::test_applied_menu_empty_history` | no `applied_pick` option; history placeholder is the single `| — | — |` row |
| integration | `test_options_menu.py::test_applied_add_change` | adding a later change to another tariff stores both sorted; `runtime_data.schedule` prices hours after the switch with the new tariff |
| integration | `test_options_menu.py::test_applied_add_duplicate_date` | `errors == {"from": "duplicate_from"}`, options unchanged |
| integration | `test_options_menu.py::test_applied_add_before_first_version` | `errors == {"from": "no_version"}`, `description_placeholders["first_valid_from"]` set |
| integration | `test_options_menu.py::test_applied_single_replaces_history` | two-entry history → one entry; default `from` prefilled with the chosen tariff's first `valid_from` |
| integration | `test_options_menu.py::test_applied_change_redate` | pick an entry, change `from` → stored with the new date, still sorted |
| integration | `test_options_menu.py::test_applied_change_tariff` | pick an entry, change `tariff` → stored |
| integration | `test_options_menu.py::test_applied_change_delete` | `delete: True` removes the entry; deleting the last entry stores no `applied` key and the entry still loads (`schedule is None`) |
| integration | `test_options_menu.py::test_applied_change_validation_error` | re-dating onto another entry's date → `duplicate_from` |
| integration | `test_options_menu.py::test_compare_default_stores_no_key` | `use_default: True` → no `compare` key; existing `applied` kept |
| integration | `test_options_menu.py::test_compare_explicit_subset_in_tariff_order` | selection given in reverse order is stored in tariff order |
| integration | `test_options_menu.py::test_compare_empty_list` | `use_default: False`, no tariffs → `compare == []`; `runtime_data.tariffs.compare == ()` |
| integration | `test_options_menu.py::test_compare_prefill` | stored `None` → `use_default` true and `tariffs` = never-applied ids; stored list → `use_default` false and that list |
| integration | `test_options_menu.py::test_submit_uses_current_options` | options changed via `async_update_entry` after the menu was shown are preserved by a later `general` submit |
| integration | `test_options_menu.py::test_corrupt_options_abort` | corrupt `entry.options` → `invalid_options` from the menu's sub-steps |
| integration | `test_options_menu.py::test_options_strings_complete` | every step id, menu option, section, error and abort key used by the options flow exists in `strings.json` and `translations/en.json` |
| integration | `tests/integration/test_config_flow.py` (existing options tests) | same assertions as today, reached via `init` → `sensors` / `general` |

## Acceptance criteria
- [x] `uv run pytest -m unit` → green; engine coverage ≥ 95 % (`script/test`).
- [x] `uv run --group ha pytest -m integration` → green on both CI legs (py3.13 / HA 2025.4.0, py3.14 / HA latest).
- [x] `script/lint` → clean; `uv run --group ha pyright` → 0 errors.
- [x] `hassfest` and `hacs` CI jobs green (translation schema accepts the new `options` strings; no
      `menu_option_descriptions`, no `sort=` in `async_show_menu`).
- [x] `grep -rn "homeassistant" custom_components/energy_cost_stats/engine/` → no imports
      (`tests/unit/test_engine_isolation.py` green); `settings.py` stays free of HA imports.
- [x] `grep -n "OptionsFlowWithReload" -r custom_components/` → no match; a single update listener still reloads.
- [x] Options menu has exactly `sensors`, `applied`, `compare`, `general` (no export / YAML entries).
- [x] Every saving step writes the full option set (no key lost), verified by the "keeps other options" tests.
- [x] Stored option format for `applied` / `compare` is unchanged from 017 (existing 017 tests untouched and green).
- [x] `docs/SPEC.md` §2 / §3 describe the options menu, the `panel` key and the validation-before-save rule.

## Out of scope
- Sensor selection modes, include / exclude, overrides, preview (task 020); the "Sensors" entry keeps today's form.
- YAML mode, read-only steps, `reload` action, repairs, "Export to YAML" menu entry (task 021).
- The sidebar panel itself (task 023): 019 only stores `panel`.
- Tariff subentry forms, rename with reference update, deletion guard (task 018).
- Card comparison section (022), Russian translations (024).
- An in-flow draft of several history changes saved at once (see open questions).

## Open questions
- **Sidebar flag before the panel exists.** CONFIG-DESIGN puts "show in sidebar (title, icon)" into General, so
  this task stores it, but it does nothing until task 023. Ship the fields now (as planned here), or hide the
  `sidebar` section until 023 lands? Default `show` — off (planned) or on?
- **Saving model for the history.** Planned: each add / change / delete is validated and saved immediately (the
  flow closes, the entry reloads). Alternative: edits collect in the flow and a "Save" menu option commits them
  (several changes, one reload, but unsaved edits are lost if the dialog is closed). Which is preferred?
- **"Use one tariff" date.** Planned: prefilled with the tariff's first `valid_from`, editable. Should it instead be
  fixed (always the short form `applied: <id>`), hiding the date?
- **Compare containing an applied tariff.** The engine allows an explicit `compare` list to include a tariff that is
  also applied. Offer all tariffs in the multi-select (planned), or only never-applied ones?
- **Deleting a tariff listed only in `compare`** (resolved in task 018): the id is dropped from `compare`
  automatically; 019 adds no repair.

## Implementation notes
- Open questions took the planner defaults: sidebar fields shipped with `show` off; each history change is saved
  immediately; "use one tariff" has an editable date; the compare multi-select offers all tariffs.
- `applied_single`: the `from` field is optional and not prefilled; when left empty, the chosen tariff's first
  `valid_from` is used (a prefilled date could not follow the selected tariff and would cause false `no_version`
  errors).
- The picked change in `applied_pick` is identified by its date (not an index) so a concurrent edit cannot point
  at another entry; a vanished entry returns to the `applied` menu.
- A blank sidebar title or icon falls back to the previous value (or the default) instead of failing validation.
- Config entry corruption (`SettingsError` or tariff subentries that do not parse) aborts every step with
  `invalid_options`; the `compare` step description lists the default set in `{default}`.
- Final run: unit 409 passed (engine coverage 99.9 %), integration 188 passed, ruff and
  pyright clean.
- Review round 1: the compare default set is computed from the raw history (a broken history cannot block the
  step); an error in an entry the user did not just edit is shown as the form error `invalid_config`; an unknown
  tariff id carries code `unknown_tariff` from `config_from_data` and is shown at the `tariff` field; the add
  default date is today in the configured time zone.
- After rebasing onto task 018: 018 allows deleting an applied tariff and reconciles the options, so no 019 code
  assumes a refusal. The setup document is built from 018's `_tariff_subentries` helper through
  `tariff_document`.
