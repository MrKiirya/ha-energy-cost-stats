# 004 — Review (round 2)

Verdict: APPROVE

Scope reviewed: working-tree changes vs `HEAD` on `task/004-tariff-model`: `docs/SPEC.md` and
`tasks/004-tariff-model.md` (modified), plus the untracked `engine/tariff.py`, `engine/presets.py`,
`tests/unit/test_tariff.py` and `tests/unit/test_presets.py`.

## Checks run
- `uv run pytest -m unit --cov=custom_components/energy_cost_stats/engine --cov-branch --cov-report=term-missing --cov-fail-under=95`
  → `109 passed in 0.57s`. Coverage: `presets.py 100%`, `tariff.py 100%` (165 stmts, 92 branches),
  `Total coverage: 100.00%`.
- `uv run ruff check .` → `All checks passed!`
- `uv run ruff format --check .` → `35 files already formatted`
- `uv lock --check` → `Resolved 229 packages in 2ms`
- Pyright ran in a one-off `ghcr.io/astral-sh/uv:python3.14-trixie` container. The repo was mounted
  read-only and copied inside the container. Settings: `UV_PROJECT_ENVIRONMENT=/opt/venv`,
  `uv sync --frozen --group ha`, `uv run --no-sync --group ha pyright`. Engine is strict.
  Result: `0 errors, 0 warnings, 0 informations`. The container was started with `--rm` and has exited.
- Mutation check: the round-1 script, extended with the new mutants below, runs against a temp copy of
  the engine and the two test files. All 16 mutants are killed. The two that survived round 1 are now killed:
  - equal band limits → 1 failed;
  - `plans_between` with an inclusive end → 1 failed.

  New mutants:
  - `re.match` instead of `fullmatch` for the key → 2 failed;
  - old `^...$` + `re.match` for the key → 1 failed;
  - old `^...$` + `re.match` for `HH:MM` → 1 failed;
  - limit `isinstance` check removed → 1 failed;
  - limit `is_finite` check removed → 2 failed;
  - limit `> 0` changed to `>= 0` → 1 failed;
  - limit validation skipped entirely → 4 failed;
  - hour lookup built from the first zone only → 3 failed.
- Direct probes:
  - Rejected with `TariffValidationError`:
    - limits `NaN`, `sNaN`, `Infinity`, `-Infinity` and `3900.5` (a `float`);
    - keys `"t1\n"`, `"t1\r"` and `"\nt1"`;
    - `Period.parse` start values `"07:00\n"`, `"\n07:00"` and `"07:00 "`.
  - `dataclasses.asdict(plan)` keys are exactly `valid_from`, `name`, `zones` and `volume_band_limits_kwh`.
    `__slots__` holds the same four names.
- Hygiene grep over the changed and new files (local paths, personal data, real entity ids, secrets) → no matches.

## Previous required items
1. **Trailing newline accepted by `$` + `re.match`: resolved.**
   - `tariff.py:21-22`: both patterns dropped `^`/`$`.
   - `tariff.py:78` and `:106`: both use `fullmatch`.
   - `test_tariff.py:94` adds `("07:00\n", "23:00")` and `test_tariff.py:117` adds key `"t1\n"`.
   - Both new cases fail with the old code, confirmed by mutants M9b and M10.
2. **Band limits not checked for type, finiteness or `> 0`: resolved.** `_validate_volume_limit`
   (`tariff.py:130-143`) checks `isinstance(Decimal)`, then `is_finite()`, then `> 0`, and runs before the
   ordering comparison, so `NaN` no longer reaches `<=`. `test_tariff.py:252-255` adds the cases for equal
   limits, `NaN`, `Infinity` and `3900.0`.

## Implementer's extra changes
- **`_hour_lookup` removed; `_build_hour_lookup(zones)` is rebuilt on every `zone_for_hour` call.**
  - **Why:** the implementer notes that `asdict()` ignores `repr=False, compare=False`. That is correct,
    and `test_plan_hour_lookup_not_leaked` pins it down.
  - **Performance:** measured 2.7 µs per `zone_for_hour` call, against 0.05 µs for indexing a
    precomputed tuple (about 60×). `plan_for` is 0.4 µs.
  - **Expected load:** task 006 (`tasks/006-pricing-and-grouping.md:30`, `:165`) classifies each hour
    **once per request**, not once per device. So the cost is about 44k calls for 5 years ≈ 120 ms on a
    dev machine, and perhaps up to about 1 s on a Raspberry-class host. That is fine for stage 1 and does
    not block this task.
  - **Risk:** it would become a real problem only if 005/006 called `zone_for_hour` per (device, hour).
    That would be ≈ 6 s for 50 devices × 5 years on a dev machine.
  - **Caching options:** `functools.cached_property` is not usable here, because the class uses
    `slots=True` and has no `__dict__`. A plain `lru_cache` on `_build_hour_lookup` would hash the whole
    zones tuple, including the `Decimal`s, on every call. Suggestion 1 below gives a cheap way to cache it.
- **New boundary tests**, all meaningful and all failing on the relevant mutants:
  - `plans_between(2026-06-15, 2026-07-01) == (plan_a,)`;
  - equal band limits;
  - `NaN` / `Infinity` / `float` limits;
  - the no-leak test for `asdict`, `repr` and `eq`/`hash`.

## Acceptance criteria
- [x] `uv run pytest -m unit` passes, including `test_engine_has_no_forbidden_imports`. Verified: 109 passed.
- [x] Coverage ≥ 95 %, with `tariff.py` and `presets.py` listed. Verified: 100 %.
- [x] `ruff check` / `ruff format --check` exit 0. Verified.
- [x] Pyright 0 errors, engine strict. Verified in the container.
- [x] No `float` as a price type in `engine/`. Verified: `float` is now also rejected at runtime for band limits.
- [x] No `homeassistant|zoneinfo|timezone` in `tariff.py` / `presets.py`. Verified: stdlib imports only.
- [x] SPEC §3 and §5 contain the "SPEC edits" decisions and no other section changed. Verified: unchanged since round 1.
- [x] No files outside the "Files" list. Verified. The task file changes are the status (`in-review`),
  the implementation notes and the round-1 fix notes.

## Findings
### Required
None.

### Suggestions
1. **Precompute the hour lookup once per plan.**
   - **Where:** `tariff.py:146-153` and `:232-236`.
   - **Problem:** the docstring says the lookup "does not need caching". That is only true while
     callers classify each hour once per request (≈ 60× slower than indexing a tuple, see above).
   - **Fix, option (a):** expose a public `hour_zones() -> tuple[Zone, ...]` (24 entries). Task 005's
     `classify_hours` can then build it once per plan in a local dict.
   - **Fix, option (b):** add `field(init=False, repr=False, compare=False)` back and give stage 3 an
     explicit `to_dict()` instead of `asdict`.
   - **Also:** soften the docstring either way. This fits naturally in task 005. Add a note to the 005
     task file so the planner or implementer does not call `zone_for_hour` per (device, hour).
2. **Weak gap-message assertion.** `test_tariff.py:180`: `assert "0" in message` is still weak (round-1
   suggestion 3). Assert the exact message `"hours not covered: 0, 23"`.
3. **Round-1 suggestions 5–7, 9 and 10** are deferred in the task's Follow-ups: self-overlap wording,
   the date in the duplicate-`valid_from` message, `list`/`datetime`/non-`str` robustness, blank plan name,
   and the SPEC JSON `0.0`. Deferring them is acceptable. The `datetime`-as-`valid_from` case is worth
   handling before task 005, because 005 feeds `local_start.date()` and a stray `datetime` would break `bisect`.

All round-1 required items are resolved, with tests that fail without the fix. No new blocking issues.
