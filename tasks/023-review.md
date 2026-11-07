# 023 — Review (round 1)

Verdict: APPROVE

## Checks run
Run in the devcontainer (latest HA leg, HA 2026.9.3 / Python 3.14):
- `uv run --no-sync pytest --cov=custom_components/energy_cost_stats/engine --cov-fail-under=95` →
  `926 passed`; `Required test coverage of 95% reached. Total coverage: 99.89%`
- `uv run --no-sync ruff check .` → `All checks passed!`
- `uv run --no-sync ruff format --check .` → `118 files already formatted`
- `uv run --no-sync pyright` → `0 errors, 0 warnings, 0 informations`
- `npm test` (frontend) → `Test Files 5 passed (5)`, `Tests 135 passed (135)`
- `npm run typecheck` → no errors
- `npm run check-bundle` → `Card bundle is up to date.`
- HA 2025.4.0 API checked against the tagged source (`homeassistant/components/panel_custom/__init__.py`,
  `homeassistant/components/frontend/__init__.py` at tag `2025.4.0`): `async_register_panel` is `async def` with
  the keyword parameters used here (no `handle_safe_area`); `async_remove_panel(hass, frontend_url_path, *,
  warn_if_unknown=True)` is a `@callback`; `DATA_PANELS` is the same `HassKey`. On the latest HA,
  `inspect.iscoroutinefunction(async_register_panel)` is `True` and the signature only adds `handle_safe_area`
  at the end. The `await` with keyword arguments is therefore correct on both legs.

## Acceptance criteria
- [x] Tests written and green — `tests/integration/test_panel.py` (8 tests incl. parametrised cases) and
  `frontend/test/panel.test.ts`, `register.test.ts`, `card.test.ts` pass; each would fail without the code
  (no panel registered / no panel element / title still rendered).
- [ ] `script/test` and both CI legs green — the latest-HA leg is verified locally (above); the
  `py3.13, HA 2025.4.0` leg was not run locally. The source comparison above shows no signature risk, but the
  checkbox can only be confirmed by CI.
- [x] Unit tests, ruff check/format, pyright pass — verified above.
- [x] `npm run typecheck` clean; bundle rebuilt; `npm run check-bundle` passes — verified above.
- [x] `panel_custom` / `async_remove_panel` only in `panel.py` and `manifest.json` — verified by grep.
- [x] No `async_register_built_in_panel` in `custom_components/` — verified by grep.
- [x] No new entity or platform — `git diff` contains no `PLATFORMS` / `async_forward_entry_setups` lines.
- [ ] `hassfest` / `hacs` green — CI only; `panel_custom` is declared in `after_dependencies`, which is what
  hassfest's import check expects.
- [x] `strings.json` and `translations/en.json` identical for the General step; "not available yet" removed.
- [x] SPEC §2 and §4.1 "Sidebar panel" describe path, element, same module URL, not admin-only, entry
  lifecycle, conflict handling, YAML mode; CONFIG-DESIGN row 023 reworded.
- [ ] Manual dev-HA check — not done (recorded as such in the implementation notes).
- [x] Implementation notes record the hassfest status (declared; confirmation pending on CI).

## Lifecycle review
- Setup: registration is the last step of `async_setup_entry`, after every `ConfigEntryError` path, so a failed
  setup never leaves a panel behind.
- Unload / reload / removal: removal is attached with `entry.async_on_unload` only after a successful
  registration, so option changes and the YAML `reload` action (both reload the entry) remove and re-register
  exactly once; the options test asserts exactly one custom panel after a title/icon change.
- Conflict: `ValueError` is logged as a warning, no unload callback is attached, so the foreign panel is neither
  overwritten nor removed (covered by `test_path_conflict_is_not_fatal`).
- Without `frontend`: `DATA_CARD_MODULE_URL` is only set when the frontend is loaded, and `panel.py` checks both.
- Same bundle URL: `module_url` is the stored value passed to `add_extra_js_url`; tests assert equality and a
  single `add_extra_js_url` call across a reload.
- Panel element: `hass` uses `noAccessor` with a custom accessor that always forwards to the card and requests an
  update only under `hassChanged`; Lit's instance-property save/restore also covers pre-upgrade property sets
  (tested with a late-defined subclass). The card is created in `willUpdate` and rebuilt only when its config
  changes; `route` / `narrow` changes do not rebuild it. `defineCard()` guards both elements separately and the
  panel is not added to `window.customCards`.

## Findings
### Required
None.

### Suggestions
1. `tests/integration/test_panel.py` `test_unload_and_remove_drop_panel` — the "unknown panel" assertion cannot
   fail as written: our panel is always present when the unload callback runs, so `warn_if_unknown=True` would
   not log either. To make `warn_if_unknown=False` observable, remove the panel externally (pop it from
   `DATA_PANELS`) before `async_unload` and then assert no "Removing unknown panel" warning.
2. `tests/integration/test_panel.py` `test_path_conflict_is_not_fatal` — `any(r.levelno == logging.WARNING ...)`
   accepts any warning; match the logger name or the "Cannot add the sidebar panel" message so an unrelated
   warning does not satisfy the test.
3. `tasks/023-sidebar-panel.md` — the second acceptance box (both CI legs green) is ticked although the
   implementation notes state the CI legs were not run; tick it once CI confirms. The `Status:` line still reads
   `planned`.
4. `frontend/src/panel.ts` `willUpdate` — `panel.config.card` is spread after the defaults, so it can also
   override `type`; consider spreading it first and forcing `type` afterwards (the backend sends no card config
   yet, so this is only relevant for the follow-up that adds it).
