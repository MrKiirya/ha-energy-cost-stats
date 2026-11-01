# 010 — Review (round 1)

Verdict: APPROVE

## Checks run
All checks ran in the devcontainer (HA 2026.9.3, Python 3.14.10). The HA 2025.4.0 leg was not run here; the main
session reports it separately.
- `sh script/test` → `404 passed in 29.53s`; `Required test coverage of 95% reached. Total coverage: 99.62%`;
  `plan_codec.py 99 stmts, 3 miss, 97%` (missing 124, 140-141).
- `uv run --group ha pytest -m integration -q` → `81 passed, 323 deselected`.
- `uv run --group ha pyright` → `0 errors, 0 warnings, 0 informations` (`engine/` is in `strict`, so
  `plan_codec.py` is covered).
- `uv run --group ha ruff check .` → `All checks passed!`
- `uv run --group ha ruff format --check .` → `65 files already formatted`
- `cmp strings.json translations/en.json` → identical.
- Greps: `float(` → only 009's spike-limit lines in `config_flow.py:106,172` (kWh, not prices).
  `NumberSelector` → none. `async_update_reload_and_abort` → none. `reason=` → only the three
  `async_abort(reason=...)` calls at `subentry_flow.py:156,160,193`. `async_update_and_abort` gets no `reason=`.
  `homeassistant` in `engine/` → docstring mentions only. `components.recorder` → none.
- `script/lint` was not run as written: it calls `uv run` without `--group ha`, which would re-sync the shared
  container venv. Its two commands were run with `--group ha` above.

## Acceptance criteria
- [x] Integration tests pass, 009's included. Verified above (81 passed).
- [x] `script/test`: all levels pass, gate holds, `plan_codec.py` is listed. Verified above.
- [x] pyright 0 errors with `plan_codec.py` under strict. Verified above and in `pyproject.toml` `[tool.pyright] strict`.
- [x] Lint: ruff check and format check exit 0. Verified with the `--group ha` equivalents.
- [x] Unit tests pass, including `test_engine_has_no_forbidden_imports`, which scans all of `engine/` (new module included).
- [x] Ruff is clean. Verified above.
- [x] No price goes through `float`. The codec uses only regex + `Decimal(str)`, and storage reads reject
  float/int/bool through `_read_str`.
- [x] No `NumberSelector` in `subentry_flow.py`.
- [x] `async_update_reload_and_abort` / `reason=`: the only literal hits are required `async_abort(reason=)`
  keywords, and `async_update_and_abort(entry, subentry, title=, data=, unique_id=)` matches the 2025.4.0
  signature quoted in the task.
- [x] `components.recorder` is not imported anywhere.
- [x] `strings.json` == `en.json`. `config_subentries.tariff_plan` has `entry_type`, `initiate_flow.user`
  (+ `reconfigure`) and `step`. `error`/`abort` are plain literals (no `[%key%]`), and `selector.preset.options`
  is at the top level. Translation keys are lowercase snake case. hassfest itself runs in CI only.
- [ ] CI green on both legs. Not verifiable locally (CI only; 2025.4.0 leg pending from the main session).
- [x] `docs/SPEC.md`: only the §2 sentence and the §3 storage paragraph + string-price example changed.
- [x] No files outside "Files": the diff touches only the 10 listed files plus the task file itself.
- [ ] Manual check (optional, human). Not done.

## Findings
### Required
None.

### Suggestions
1. `engine/plan_codec.py:124` and `:140-141` are uncovered. Both are real behaviours, not dead code: line 124
   rejects a stored price with a comma (stated in Implementation notes), and 140-141 reject a well-shaped but
   impossible date such as `"2026-02-30"` or `"2026-13-01"`. Add two cases to `test_from_data_rejects`
   (`_set(["zones", 0, "price"], "10,30")`, `_set(["valid_from"], "2026-02-30")`). This brings the codec to 100 %.
2. `subentry_flow.py:164`: `max(plans, ...)` raises `ValueError` on an empty list. The menu only offers `copy`
   when plans exist, but if the last plan is deleted between the menu and the copy step, the user gets a 500
   instead of a clean result. Guard with `if not plans: return await self.async_step_preset()` (or abort
   `unknown_plan`).
3. `strings.json` `step.plan.description` ends with `\n\n{detail}`. The frontend already interpolates
   `description_placeholders` into the `base` error ("The zones are invalid: {detail}"), so the engine message
   appears twice on an invalid plan. Consider dropping `{detail}` from the description. The placeholder must still
   be passed, which the code already does. Low priority: this is cosmetic.
4. The new aborts `invalid_plan_data` (copy and reconfigure of a corrupt stored plan) have no test. They can be
   reached: a corrupt plan puts the entry in `SETUP_ERROR`, but the subentry manager still runs flows, and the
   user's way out is reconfigure or delete. Add one integration test that seeds a float price and opens a
   reconfigure flow, expecting `ABORT invalid_plan_data`. `unknown_plan` and `invalid_date` are effectively
   unreachable through the schema (the `SelectSelector` and `DateSelector` validate first), so leaving them as
   untested defensive code is fine.
5. `test_setup_error_on_corrupt_plan` could also assert that the error names the subentry title (D-7). For example,
   use `caplog` or check `entry.reason` where the HA version provides it. Optional.
6. `engine/plan_codec.py:22`: the comment says "a price or a volume limit typed into a form", but volume limits
   are never typed into a form. They are only read from storage. Reword it to "a price or volume limit (sanity range)".

## Notes on extras and decisions
- `MAX_PRICE = 1,000,000`: a sensible sanity bound for price per kWh in any currency, enforced both in the form and
  in storage. It also caps stored volume-band limits at 1,000,000 kWh, which is harmless. A programmatic plan
  above the cap would serialize but not deserialize. This cannot happen through the UI, so it is acceptable.
- `invalid_date`, `unknown_plan`, `invalid_plan_data`: reasonable defensive additions, translated in both files.
- Volume bands and band prices carried through copy and reconfigure: correct (otherwise editing a price would
  silently drop reserved data), and tested for reconfigure.
- Flow correctness checked by reading:
  - The first plan goes straight to `preset`; otherwise the flow shows a menu.
  - The copy step defaults to the latest ISO `valid_from` (string order equals date order for `YYYY-MM-DD`).
  - Reconfigure renders `step_id="plan"`, so its submit goes to `async_step_plan` with `_editing` set.
  - The duplicate check excludes the subentry being edited.
  - Errors appear in the D-5 order.
  - Submitted values are kept on error.
  - `detail` is always passed and is empty unless `base` is set.
- Setup (D-7): a corrupt plan and a duplicate schedule both raise `ConfigEntryError`, and both paths are tested.
  The schedule is `None` when there are no plans.
- Planner decisions D-1 to D-7 accepted.
- Repo hygiene: generic data only (`Europe/Berlin`, 2026 dates, `10.30`/`4.43`). No entity ids, paths or secrets.
