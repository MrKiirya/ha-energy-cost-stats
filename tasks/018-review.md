# 018 — Review (round 1)

Verdict: CHANGES_REQUESTED

## Checks run
Devcontainer (Python 3.14, HA 2026.9.3), `uv run --no-sync`:
- `pytest --cov=custom_components/energy_cost_stats/engine --cov-report=term-missing --cov-fail-under=95` →
  `596 passed`; `Required test coverage of 95% reached. Total coverage: 99.87%`; `engine/tariff_edit.py` 100 %.
- `ruff check .` → `All checks passed!`
- `ruff format --check .` → `95 files already formatted`
- `pyright` → `0 errors, 0 warnings, 0 informations`
- Listener yield: in a throwaway copy of the tree with `await asyncio.sleep(0)` removed from
  `_async_update_listener`, `test_edit_first_version_moves_applied` and `test_rename_id_updates_references` fail
  (`2 failed, 36 passed`). The tests pin the deviation.
- Applied-history reorder (Required 1): reproduced with a throwaway test in the same copy (see below).
- Not run locally: the HA 2025.4.0 / Python 3.13 leg, `hassfest`, `hacs` (CI only).

## Acceptance criteria
- [x] `script/test` equivalent: all levels pass; engine coverage ≥ 95 % with `engine/tariff_edit.py` listed. Verified by
  running it.
- [x] Lint and `pyright` clean. Verified by running them.
- [ ] CI green on both matrix legs plus `hassfest` and `hacs`. Pending; cannot be verified locally.
- [x] Unit tests pass, including `test_engine_has_no_forbidden_imports` and `test_strings_match_en_translation`
  (part of the full run).
- [x] `ruff check` / `ruff format --check`. Verified.
- [x] `async_update_reload_and_abort` and `async_update_and_abort(... reason=` → no matches.
- [x] `NumberSelector|float(` in `tariff_flow.py` → only the `count` selector of `custom_zones`.
- [x] `homeassistant` in `engine/tariff_edit.py` → no matches.
- [x] `components.recorder` → only `recorder_adapter.py`.
- [x] `async_forward_entry_setups|PLATFORMS` → no matches.
- [x] No files touched outside "Files" (`git status`: the 11 listed files plus the task file); examples are generic.
- [ ] Manual check in `script/develop`: optional, for the human.

## Deviations examined
- **Listener yield (`__init__.py:285`).** Robust. The guarantee comes from the flows, not from timing: `_store` and
  `_async_reconcile` make all their writes in one synchronous run, with no `await` in between. Any listener task,
  eager or not, can get past `await asyncio.sleep(0)` only after that run returns to the event loop. By then every
  write of the sequence has been applied. The behaviour is the same on HA 2025.4 and on the latest HA. In the
  installed HA, `hass.async_create_task` defaults to `eager_start=True`. If 2025.4 still scheduled lazily, the yield
  would only delay more. HA has no public API that writes options and a subentry at once (`async_update_entry` takes
  no `subentries`), so a single write is not possible. A flag or a debounce would add state without adding safety.
  Two costs remain: the invariant "multi-write sequences are synchronous" is now load-bearing, and each two-write
  action reloads the entry twice (see Suggestion 1).
- **`persistent_notification` without a manifest dependency.** Acceptable. It is one of HA's `CORE_INTEGRATIONS`
  (`bootstrap.py`: `{"homeassistant", "persistent_notification"}`), so it is always set up before any integration.
  hassfest's dependency check allows it in the same way as `websocket_api`, which `websocket.py` already imports
  without a manifest entry and which passes hassfest on `master`. CI confirms it.
- **Deleting the first version moves a matching `applied` start.** Reasonable, and consistent with D-9. Without it,
  deleting the first version of an auto-applied tariff could never succeed. The rule shares the defect in
  Required 1, though, and it is a product choice the task did not list (Suggestion 2).
- **`format_hours`, abort `invalid_stored_tariff`, `last_version` on the `delete` field.** Fine. `format_hours` is
  unit-tested (`test_format_hours`, including the merge across midnight). The abort has translated text.

## Findings
### Required
1. `custom_components/energy_cost_stats/tariff_flow.py:260` (`_move_applied`, called at lines 823 and 840): moving an
   `applied` start can **reorder the applied history** and silently change which tariff prices later hours.
   Reproduction: tariffs `two_zone` (one version from 2026-01-01; for the delete case a second version from
   2026-07-01) and `other`. `applied = [{2026-01-01, two_zone}, {2026-05-01, other}]`. Either move `two_zone`'s
   first version to 2026-07-01, or delete its first version. Both end with `reconfigure_successful` and leave
   `applied == [{2026-07-01, two_zone}, {2026-05-01, other}]`. `config_from_data` sorts this into
   "`other` from May, `two_zone` from July", whereas before it meant "`two_zone` until May, `other` afterwards".
   Every hour from July on is re-priced with a different tariff, and January to April loses its price, without any
   warning. Principle 3 requires that past hours be re-priced correctly, and this re-prices them with the wrong
   tariff. Fix direction: a moved start must stay strictly before the next `applied` item's `from` (and after the
   previous one). Otherwise reject with `errors["valid_from"] = "applied_without_version"` (or a dedicated error),
   for the date edit and for the delete. Add integration tests for both cases with a later applied item of another
   tariff, and assert that the options are unchanged after the error.

### Suggestions
1. `__init__.py:285`: a rename with an id change or a first-version date move writes twice, so two listener tasks
   run and the entry is reloaded twice. The second reconcile can even run while the first reload is in progress.
   This is harmless today, because reconcile returns `False` when `runtime_data` is gone or unchanged. A small guard
   would coalesce the two reloads into one: skip the reload when one is already pending for this entry (or use a
   short `Debouncer`). Also, the `_store` docstring (`tariff_flow.py:235`) says "both updates are applied before the
   first update listener runs". On eager HA the listener *starts* in between, so a better wording is "before any
   update listener gets past its first yield".
2. Move the new rule "deleting the first version moves a matching `applied` start" into "Open questions" in the task
   file, and add it to SPEC §3. The Forms paragraph now covers only the date move. Also assert the moved start in
   `tests/integration/test_tariff_flow.py::test_delete_first_version_keeps_prices`
   (`entry.options["applied"] == [{"from": "2026-07-01", "tariff": "two_zone"}]`). Today only `LOADED` is checked.
3. `tasks/018-tariff-forms.md`, "HA API checked", the update-listeners bullet: it still says that listeners are
   scheduled as tasks and are therefore safe across two synchronous updates. Correct it so that it matches the
   implementation note (eager start; the listener yields once). The public task file then does not contradict
   itself.
4. `_save_first_version` with `delete` on: an `applied_without_version` error (for example, a later applied start of
   this tariff that falls between the deleted version and the next one) is attached to `valid_from`, which the user
   did not change. Consider attaching it to `delete` or `base` for the delete path.
5. `tests/integration/test_tariff_model.py::test_deleting_applied_tariff_restores_it` finds the restored subentry by
   `unique_id`, which checks the `unique_id` only implicitly. An explicit `assert restored.unique_id == "two_zone"`
   would state it.

---

# 018 — Review (round 2)

Verdict: APPROVE

## Checks run
Devcontainer (Python 3.14, HA 2026.9.3), `uv run --no-sync`:
- `pytest --cov=custom_components/energy_cost_stats/engine --cov-report=term-missing --cov-fail-under=95` →
  `607 passed`; `Required test coverage of 95% reached. Total coverage: 99.87%`; `engine/tariff_edit.py` 100 %.
- `ruff check .` → `All checks passed!`
- `ruff format --check .` → `96 files already formatted`
- `pyright` → `0 errors, 0 warnings, 0 informations`
- Not run locally: the HA 2025.4.0 / Python 3.13 leg, `hassfest`, `hacs` (CI only).

## Round 1 Required items
1. **Resolved.** `engine/tariff_edit.py::move_applied_start` accepts a new start only when it lies strictly between
   the neighbouring `applied` items. It returns `None` otherwise, and the flow then shows `applied_order`: on
   `valid_from` for a date edit, on `delete` for a deletion (`tariff_flow.py` `_save_first_version`). These tests
   cover the round 1 reproduction: `test_moving_first_version_must_not_reorder_applied` and
   `test_deleting_first_version_must_not_reorder_applied`, both of which also check that the subentry and the
   options are unchanged. `test_move_applied_start` covers the boundary cases (equal to the next start, past the
   previous one, absent item, unchanged date). Round 1 Suggestions 2 (assert the moved start after a first-version
   delete) and 4 (delete-path errors on `delete`) are also addressed.

## Author decisions B and C
- **B: deleting an applied tariff (`remove_from_applied`, `_async_reconcile`).** Correct. I checked it against
  `effective_schedule`:
  - When a middle or last item is dropped, the previous tariff continues over the freed period. Because the version
    in force at a later `from` is the same version the earlier item would reach on that date, merging equal
    neighbours (`[A, B, A]` → `[A]`) changes no price. The merge is cosmetic and safe.
  - When the first item is dropped, the next item takes over the earlier start only if its tariff has a version on
    that date. This never creates an `applied` start without a version.
  - When nothing remains applied, the first remaining tariff is applied from its first version. When no tariff
    remains, `applied` is removed.
  - Sorting by `(from, tariff)` is safe because `from` dates are unique.
  - The restore, the snapshot and the notification are fully removed. `rg` finds no `persistent_notification`,
    `TariffSnapshot` or snapshot code, and no `before_first_version` string is left.
  - Rule 3 now keys off `runtime_data.tariffs.tariffs`, which is equivalent to the previous snapshot check.
  - Because reconcile now *removes* applied items whose tariff is missing, the rename's two-write sequence must stay
    atomic. Otherwise the renamed id would be stripped from `applied`. The yield before reconcile guarantees this,
    and `test_rename_id_updates_references` pins it.
  - Integration tests in `test_tariff_model.py` cover every rule. `test_remove_from_applied` covers them at unit
    level.
- **C: a new version dated before the first one.** Correct. The new version gets explicit `zones` (keys and names
  of the former first version, the entered prices and hours), and the former first version is kept verbatim.
  Versions after the former first one therefore resolve exactly as before. A zone-key mismatch is still rejected
  with `invalid_tariff`. `applied` is not moved (D-12, as decided). `test_new_version_before_the_first_version`
  asserts the stored documents, the unchanged `applied` and the unchanged January price.

## Findings
### Required
None.

### Suggestions
1. `tasks/018-tariff-forms.md`, acceptance criteria, "Manual (optional, human)": the criterion still says that a
   deleted applied tariff "comes back with a notification". That behaviour was removed by decision B. Replace it
   with the new expectation (the applied history is repaired as in D-10 rule 1) before merge, so the manual check
   does not report a false failure.
2. D-12: because `applied` is not moved, a version dated before the first one prices nothing until the applied
   history starts earlier. That will be possible with the 019 options menu. Editing the first version's date to an
   earlier day *does* move a matching `applied` start (D-9). Users may find it surprising that these two ways of
   extending a tariff backwards behave differently. Consider saying this in the `new_version` step description and
   in SPEC §3 ("`applied` is not changed"), or revisit the choice when 019 lands.
3. `remove_from_applied`: when several leading items are deleted, the next kept item takes over the first deleted
   start only if it has a version then. Otherwise it keeps its own date, even when it has a version on the date of
   a later deleted item (for example, `[x Jan, y Mar, c May]` with `c` valid from Feb ends as `[c May]`, not
   `[c Mar]`). This matches D-10 as written, so it is not a defect. Taking over the earliest deleted start on which
   the tariff has a version would leave fewer hours unpriced.
4. `_save_later_version` has no integration test for editing an existing later version (prices only) to a date
   before the first version, which takes the `earlier` branch with `editing` set. A short test would pin it.
5. `docs/SPEC.md` lines 128 and 132 exceed the line width used in the rest of the paragraph. Reflow them.
