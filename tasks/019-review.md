# 019 — Review (round 1)

Verdict: CHANGES_REQUESTED

## Checks run
Run in the devcontainer from the task worktree, with the shared venv (`uv run --no-sync`).
- `pytest --cov=custom_components/energy_cost_stats/engine --cov-report=term-missing --cov-fail-under=95`
  → `597 passed`; `Required test coverage of 95% reached. Total coverage: 99.86%`
  (`engine/tariff_config.py` 100 %).
- `ruff check .` → `All checks passed!`
- `ruff format --check .` → `91 files already formatted`
- `pyright` → `0 errors, 0 warnings, 0 informations`
- A throwaway probe test (not committed) set up an entry whose stored `applied` history is invalid
  (`applied` starts before the tariff's first version, so the entry ends in `SETUP_ERROR`) and then opened
  the options flow. Result: `applied` → menu shown; `compare` → unhandled `AppliedValidationError`
  (see Required 1).
- Not run locally: the HA 2025.4.0 / py3.13 leg, `hassfest`, `hacs` (CI only).

## Acceptance criteria
- [x] Unit tests green, engine coverage ≥ 95 % — verified by the coverage run above.
- [~] Integration tests green on both CI legs — green on the py3.14 / latest leg locally; the 2025.4.0 leg
      is left to CI.
- [x] Lint and pyright clean — verified above.
- [~] `hassfest` / `hacs` green — not run locally. No `menu_option_descriptions` and no `sort=` in
      `async_show_menu` (grep). Strings use only `title`, `description`, `data`, `data_description`,
      `menu_options`, `sections`.
- [x] No `homeassistant` imports in `engine/` or `settings.py` — grep, and `test_engine_isolation.py` passes.
- [x] No `OptionsFlowWithReload`; the single update listener is unchanged — grep plus reload assertions in
      the new tests.
- [x] The options menu has exactly `sensors`, `applied`, `compare`, `general` — `test_init_is_menu`.
- [x] Every saving step writes the full option set — `_save` serializes the complete `IntegrationSettings`
      re-read at submit time; covered by `test_general_saves_and_keeps_other_options`,
      `test_applied_add_change`, `test_compare_default_stores_no_key` and `test_submit_uses_current_options`.
- [x] The stored `applied` / `compare` format is unchanged — `tests/integration/test_tariff_model.py` has no
      changes and passes.
- [x] `docs/SPEC.md` §2 / §3 describe the menu, the `panel` key and the rule to validate before saving.

## Findings
### Required
1. `custom_components/energy_cost_stats/config_flow.py:695` — `async_step_compare` calls
   `self._validate(replace(current, compare=None))` outside any `try`. `_load` checks only that the options
   and the tariff subentries parse; it does not check the applied history against the tariffs. When the
   stored history is invalid, this step raises an unhandled `AppliedValidationError`, and the frontend shows
   a generic error instead of the form. The probe test above reproduced this. The state is reachable: for
   example, a tariff version's `valid_from` edited to a later date in the subentry forms (task 018), or any
   other change that makes setup fail with `ConfigEntryError`. That is when a user is most likely to open
   "Configure" to repair the entry. Fix: compute the default set defensively, either by catching
   `TariffValidationError` (fall back to the tariffs that are not referenced in `current.applied`, or abort
   with `invalid_options`) or by computing the default from the parsed tariffs and the raw history without
   validating the full document. Add an integration test that opens `compare` on an entry whose stored
   history is invalid and asserts a form or a defined abort, not an exception.

### Suggestions
1. `custom_components/energy_cost_stats/engine/tariff_config.py:300,311` — an unknown tariff id in the raw
   document still raises a plain `TariffValidationError` through `_fail` before `check_applied` runs. Through
   `config_from_data`, the flow therefore never receives `code == "unknown_tariff"`. It shows the base error
   `invalid_config` instead. The task says applied-history problems come back from `config_from_data` as
   `AppliedValidationError`. Raise `AppliedValidationError("unknown_tariff", …)` in `_applied` too (or leave
   the check to `check_applied`), and extend `test_config_from_data_raises_applied_error_subclass`.
2. `custom_components/energy_cost_stats/config_flow.py:554` — `by_id[user_input[CONF_TARIFF]]` raises
   `KeyError` if the selected tariff was deleted between showing and submitting the form. The select schema
   is the one built when the form was shown. Use `by_id.get(...)` and return the `unknown_tariff` field error.
3. `custom_components/energy_cost_stats/config_flow.py` (`async_step_applied_single`) — the `from` field is
   prefilled with the first `valid_from` of the tariff that is currently last in the history. If the user
   selects a different tariff, the prefilled date is still submitted, and the result can be a `no_version`
   error for a valid choice. `test_applied_single_replaces_history` submits without `from`, which the real
   form does not do once the field has a value. Consider leaving `from` empty by default (the description
   already says an empty date uses the tariff's first version), or say in the description that the date
   does not follow the selected tariff.
4. `custom_components/energy_cost_stats/config_flow.py:604` — `date.today()` uses the host's local date.
   Use today's date in the configured time zone (`dt_util.now(ZoneInfo(current.time_zone)).date()`), so the
   default matches the zone used for pricing.
5. `custom_components/energy_cost_stats/strings.json:107` (and `translations/en.json`) — the `applied_add`
   `data_description` for `from` contains `{first_valid_from}`, which is empty on first display, so the hint
   reads "(earliest: )". The field error `no_version` already shows the date. Drop the placeholder from the
   field description.
6. `custom_components/energy_cost_stats/config_flow.py:423` (`general`) and `:301` (`sensors`) — these steps
   save without `_check`. This is harmless today because neither changes the tariff document, but the class
   docstring and SPEC §2 say every leaf form validates. Either call `_check` there too or narrow the wording
   to the steps that change the tariff document.
7. `docs/SPEC.md` §2 — the new sentence "Applied and comparison steps abort with `no_tariffs` … Any options
   or subentry change reloads …" is on one line well past the file's usual wrap width. Re-wrap it.
8. When the stored history is invalid, an `applied_add` submit reports the existing broken entry's error at
   the `from` field, which reads as if the new date were wrong. A test for that state, together with
   Required 1, would document the intended behaviour (for example, guiding the user to `applied_pick` or
   `applied_single`).

## Notes
- The engine change is clean. `check_applied` keeps the old messages and order (unknown, duplicate,
  no version), and `AppliedValidationError` subclasses `TariffValidationError`, so the `config_from_data`
  contract is preserved.
- `settings.panel` is parsed strictly and is written only when set. `tariff_document` is shared by setup and
  the flow, so the flow validates the same document that setup loads.
- The string edits stay inside the `options` section and do not depend on task 018 code. `strings.json` and
  `translations/en.json` are identical.
- No hygiene issues: the tests use generic ids (`sensor.plug_01`, `main`, `other`, `late`), and the diff
  contains no local paths, hosts or personal data.

---

# 019 — Review (round 2)

Verdict: APPROVE

## Checks run
Run in the devcontainer from the task worktree, with the shared venv (`uv run --no-sync`).
- `pytest --cov=custom_components/energy_cost_stats/engine --cov-report=term-missing --cov-fail-under=95`
  → `603 passed`; `Required test coverage of 95% reached. Total coverage: 99.86%`
- `pytest -m unit` with the same coverage gate → `410 passed, 193 deselected`; engine coverage 99.86 %
- `ruff check .` → `All checks passed!`
- `ruff format --check .` → `92 files already formatted`
- `pyright` → `0 errors, 0 warnings, 0 informations`
- Not run locally: the HA 2025.4.0 / py3.13 leg, `hassfest`, `hacs` (CI only).
  `dt_util.async_get_time_zone`, which the new code uses, is available in the minimum HA version.

## Round 1 items
### Required
1. **Resolved.** `async_step_compare` now computes the default set from the parsed tariffs and the raw
   history (tariffs that do not appear in `applied`, in tariff order). This matches the engine's
   `default_compare`, and nothing raises on a broken history. `test_compare_with_invalid_stored_history`
   opens the step on an entry in `SETUP_ERROR` and gets the form with the expected prefill. A submit on a
   broken history returns the base error `invalid_config` from `_check` instead of raising.

### Suggestions
1. Resolved. `_applied` raises `AppliedValidationError("unknown_tariff", …)`. This is covered by
   `test_config_from_data_unknown_applied_tariff_has_code` (both the short form and the list form).
2. Resolved. `applied_single` uses `by_id.get(...)` and returns `{"tariff": "unknown_tariff"}`. In
   `applied_add` and `applied_change`, `_check` maps `unknown_tariff` to the `tariff` field;
   `test_applied_add_tariff_deleted_while_form_is_open` covers the `applied_add` path.
3. Resolved. `from` in `applied_single` is no longer prefilled; only the tariff is suggested. An empty date
   uses the chosen tariff's first `valid_from` (`test_applied_single_replaces_history` asserts the suggested
   values are `{"tariff": "other"}`). An explicit date still works (`test_applied_single_explicit_date`).
   Replacing a broken history works too (`test_applied_single_repairs_invalid_history`).
4. Resolved. `applied_add` prefills today's date in the configured time zone
   (`test_applied_add_prefills_today_in_configured_zone`).
5. Resolved. The `{first_valid_from}` placeholder was removed from the `applied_add` field description. It
   remains only in the `no_version` error, which always receives it.
6. Resolved by narrowing the wording. The class docstring and SPEC §2 now say that only the forms that change
   the tariff document validate first.
7. Not resolved, cosmetic. The `docs/SPEC.md` §2 line "comparison steps abort with `no_tariffs` while there
   is no tariff. Any options or subentry change reloads the entry through a" is still well past the file's
   wrap width.
8. Resolved. `_check(candidate, new)` puts a field error only on the entry the user just entered. It
   compares `(from, tariff)` against the offending `change`, and the stable sort keeps the appended entry
   second for `duplicate_from`. Any other history error becomes the base error `invalid_config` with the
   engine message in `{detail}` (`test_applied_add_on_invalid_history_reports_base_error`). Deleting an entry
   passes `new=None`, so any remaining problem is also reported as a base error.

## New findings
### Required
None.

### Suggestions
1. `custom_components/energy_cost_stats/config_flow.py` (`async_step_compare`) — the placeholders returned by
   `_check` are discarded (`errors, _ = self._check(candidate)`), and `_show_compare` always passes
   `"detail": ""`. On a broken history, a compare submit therefore shows "The configuration would be
   invalid: " with no reason. Pass the `detail` from `_check` through to `_show_compare`.
2. No test covers the `unknown_tariff` path in `applied_single` (tariff removed while the form is open); only
   the `applied_add` variant is tested. A short test would mirror
   `test_applied_add_tariff_deleted_while_form_is_open`.
3. Re-wrap the SPEC §2 line mentioned in round 1 item 7.
