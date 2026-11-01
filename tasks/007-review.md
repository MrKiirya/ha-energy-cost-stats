# 007 — Review (round 1)

Verdict: APPROVE

Reviewed: working tree on `task/007-data-quality` against `task/006-pricing-and-grouping` (HEAD == 006 tip
`4089833`; modified `engine/report.py`, `docs/SPEC.md`; untracked `engine/prepared.py`, `engine/quality.py`,
`tests/unit/test_quality.py`, `tasks/007-data-quality.md`). Untracked `tasks/009-*`/`010-*` belong to other
tasks and were ignored.

## Checks run
All commands ran inside the project devcontainer with `--group ha`.
- `uv run --group ha pytest -m unit --cov=custom_components/energy_cost_stats/engine --cov-branch --cov-report=term-missing --cov-fail-under=95`
  → `260 passed, 3 deselected in 5.94s`; `Required test coverage of 95% reached. Total coverage: 100.00%`
  (`quality.py` 83 stmts / 30 branches 100 %, `prepared.py` 16 stmts 100 %)
- `uv run --group ha pytest -m integration -q` → `3 passed, 260 deselected in 1.12s`
- `uv run --group ha pyright` → `0 errors, 0 warnings, 0 informations`
- `uv run --group ha ruff check .` → `All checks passed!`
- `uv run --group ha ruff format --check .` → `55 files already formatted`

## Acceptance criteria
- [x] Tests written first — recorded in the implementation notes (`ModuleNotFoundError: engine.quality`).
  The files are untracked, so the order cannot be seen in git history; I accepted the note.
- [x] `pytest -m unit` passes, including every 006 test. `tests/unit/test_report.py` is unchanged: verified,
  it does not appear in `git diff --stat task/006-pricing-and-grouping`.
- [x] Coverage gate ≥ 95 %; `quality.py` and `prepared.py` are each at 100 % line+branch (see above).
- [x] `ruff check` / `ruff format --check` → exit 0 (see above).
- [x] Engine isolation: `test_engine_isolation.py` is part of the passing unit run. Imports in `quality.py` and
  `prepared.py` are stdlib plus relative `.classify`/`.models`/`.prepared` only. `grep -rn homeassistant
  engine/` matches only the docstring in `engine/__init__.py`. `quality.py` does not import `report`.
- [x] `grep -rn quantize engine/`: one code line in `quality.py:132`, everything else in `rounding.py`.
  `grep -rn "round(" engine/`: matches only in `rounding.py`.
- [x] `grep -n "classify_hours|zone_for_hour" quality.py` → no matches; `report.py` has exactly one
  `classify_hours(` call (line 317).
- [x] `grep -n "^def build_report" -A 7 report.py`: the three positional parameters are unchanged, followed by
  `*, quality: QualitySettings | None = None`.
- [x] Scope: compared with the 006 branch (the correct base for a stacked branch; `git diff --stat master`
  still includes all of 006 because 006 is not merged), the diff touches only `report.py` and `SPEC.md`, plus
  the four new files listed under "Files". `models.py`, `classify.py`, `tariff.py`, `timeutil.py`,
  `rounding.py` and `test_report.py` have empty diffs.
- [x] SPEC §5 documents the span/predecessor rule, the earliest key, the average-after-spreading spike check,
  the rejected catch-up (only that hour excluded, gap stays missing), zero catch-up, the 1E-20 remainder on
  the catch-up hour, issue clipping and window independence. It also covers the HA recorder facts with
  source links, including the claim that an unavailable sensor writes no row
  (`sensor/recorder.py`, `recorder/statistics.py`), the 0.9 reset ratio and the `NULL`-sum
  `change = None`. The stage 3 neighbour-key and `change is None` requirement and both known limitations
  are there too.
- [x] Hygiene: only `sensor.plug_01`/`sensor.plug_02` and the generic `sensor.removed` (an unknown-override
  id), the prices `10.30`/`4.43`, and the zones `Europe/Moscow`/`Europe/Berlin`. A grep for IPs, home or mount
  paths, `.local`, tokens and passwords found nothing in the new or changed files.
- [x] Pyright → 0 errors (run locally in the HA env). The CI-green box is left to the PR, as expected.

## Human-confirmed rules verified in code and tests
- No maximum gap length: `quality.py` has no cap. `test_very_long_gap_is_spread` covers n = 9612 in < 1 s.
  The loop starts at `bisect_left(keys, window_start)`, breaks once `span_first >= count`, and materialises
  only `[max(span_first,0), min(catch_up,count-1)]`, so a long gap outside the window costs nothing.
- Even spread with an exact sum: `q = (D/n).quantize(1E-20, ROUND_DOWN)` and `r = D − (n−1)q` on the catch-up
  hour, inside `localcontext(prec=50)`. `test_spread_remainder_is_exact` checks the n = 3 and n = 7 cases.
- Spike check on the per-hour average after spreading: `delta > limit * n` (strict, multiplication only).
  36 and 40 pass, 40.0001 is excluded.
- Negative excluded and checked first: there is no setting that skips it. It stays excluded with
  `spike_limit=None`.
- Missing is never a silent zero: the values start as `None`; leading, trailing and rejected-gap hours stay
  `None`. Tested in the leading/trailing, earliest-key, negative-catch-up and spike-exclusion tests.
- Issues sum to the row's estimated/excluded kWh: `test_issue_invariants` (3 parametrized fixtures, two
  devices) checks all four invariants, the device-then-start order and the in-window bounds and tz offset of
  every issue.

## The two test expectations the implementer changed — recomputed by hand
1. `test_gap_with_catch_up_after_window`. Window: MSK local 2026-01-15. Local 20–23 have no keys and the key
   `12` sits at `end + 1h` = local 2026-01-16 01:00. Its predecessor is local 19:00, so the span is
   20, 21, 22, 23, 00(+1), 01(+1): n = 6, 2 kWh/h. The in-window estimated hours are 20–23 = 8 kWh: t1 gets
   20–22 = 6 and t2 gets 23 = 2, which is exactly what the task table says. The test asserts whole-cell
   totals, which also include the measured hours. Measured are 00–19 at 1 kWh: day 07–19 = 13 h, night
   00–06 = 7 h. So `t1 == 13 + 6 = 19` and `t2 == 7 + 2 = 9` are correct. **The engine is right, and so was
   the task table** (6 and 2 are the estimated shares). The test only asserts a superset quantity. The
   "16/8" the notes call wrong does not appear in the task file (see suggestion 1).
2. `test_gap_entirely_outside_window_no_effect`. The task's baseline is "in-window keys plus `start − 1h`".
   For the noisy report to equal that baseline, the noisy series must also have a key at `start − 1h`.
   Otherwise the first in-window key's predecessor is an earlier outside key, its span reaches into the
   window and it gets spread (rule a). So this is a fixture clarification forced by rule a, not a changed
   value. The fixture keeps a 9 h gap (n = 10), a spike (100, n = 1) and a negative (−1), all outside, then
   contiguous keys from `start − 17h` to `start − 1h`. `issues == ()` and full `Report` equality hold. **The
   engine is right.**

## Other correctness checks
- Hour boundaries: rule f is implemented correctly, including a key exactly at `request.end` and a rejected
  catch-up after the window (`test_rejected_catch_up_after_window_has_no_effect`: gap hours stay missing and
  no issue is produced).
- DST: in the Berlin fall-back test the span covers both local 02:00 hours (n = 6, all night/t2,
  `t2 == 3 measured + 6 = 9`). The window-independence test crosses spring-forward 2026-03-29 (a 23 h day),
  with a gap across a midnight, a spike and a negative. Single-day HOUR rows equal the 3-day rows, and the
  per-day issue sums match.
- `test_gap_spread_across_zones` recomputed by hand: t1 = 13 measured + 3×2 = 19 → 195.70; t2 = 6 measured
  + 2×2 = 10 → 44.30; total 240.00.

## Findings
### Required
None.

### Suggestions
1. `tasks/007-data-quality.md:330-333` — the note says "the task's 16/8 counts were off", but the task
   table's values (t1 estimated 6, t2 estimated 2) are correct. The test just asserts whole-cell totals
   (13+6 / 7+2). Reword it, for example: "the test asserts cell totals including measured hours; the
   task's estimated shares 6/2 are unchanged", so nobody later thinks the spec was wrong. Do the same for
   the second test: it was a fixture clarification forced by rule a, not a wrong expectation.
2. `tests/unit/test_quality.py:297-315` — `test_gap_with_catch_up_after_window` checks the zone split only
   through cell totals. Asserting `prepared.values[20:24] == [HourValue(D("2"), ESTIMATED)] * 4` would
   pin down the per-hour share, and so the rule-f behaviour (the remainder goes to the out-of-window
   catch-up hour, the in-window hours all get `q`), directly.
3. `docs/SPEC.md` §5, recorder-facts bullet — the text says the behaviour was checked on `dev` and 2025.4.0,
   but it links only the `dev` blobs. Add the `blob/2025.4.0/...` links from the task file, since 2025.4 is
   the minimum version in §6 and `dev` links drift.
4. `engine/quality.py:132` — for |D| ≥ ~1E30, `quantize` to 1E-20 at prec 50 raises `InvalidOperation`.
   That is far beyond realistic values, and the task's exactness note already bounds magnitudes. A one-line
   comment there would document the bound where it bites.
