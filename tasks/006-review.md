# 006 — Review (round 1)

Verdict: APPROVE

## Checks run
- `uv run pytest -m unit --cov=custom_components/energy_cost_stats/engine --cov-branch --cov-report=term-missing --cov-fail-under=95`
  → `227 passed`; `Required test coverage of 95% reached. Total coverage: 100.00%` (`report.py` 160 stmts /
  56 branches, 100%; `rounding.py` 21 stmts / 6 branches, 100%).
- `uv run ruff check .` → `All checks passed!`
- `uv run ruff format --check .` → `48 files already formatted`
- `rg`-equivalent `grep -rn "quantize|round(" engine/` → matches only in `rounding.py`.
- `grep -n "zone_for_hour|classify_hours" engine/report.py` → no `zone_for_hour`; one `classify_hours`
  (the call in `build_report`, line 337).
- `git status` / `git diff --stat origin/master` (local ref, no network needed; `origin/master` == `HEAD`
  `61de311`) → tracked changes: `docs/SPEC.md`, `tests/unit/test_models.py`; untracked: `engine/report.py`,
  `engine/rounding.py`, `tests/unit/test_report.py`, `tests/unit/test_rounding.py`,
  `tasks/006-pricing-and-grouping.md`. `git diff --stat origin/master -- custom_components/energy_cost_stats/engine`
  is empty, so `models.py`, `classify.py`, `tariff.py`, `timeutil.py` are unchanged.
- Pyright: **not run** (needs the HA environment; verified by CI). Read-through found no obvious strict-mode
  problem in `report.py`/`rounding.py` (the one `isinstance` guard copies the pattern already passing in
  `models.py`); tests are in `standard` mode.

## Acceptance criteria
- [~] Tests written first — `test_report.py` was run red before `report.py` existed (implementation notes).
  `rounding.py` was written before its tests were run red, so for `rounding.py` the box is not strictly met.
  The deviation is disclosed in the notes; see suggestion 1.
- [x] `uv run pytest -m unit` all pass — 227 passed, re-run by reviewer.
- [x] Coverage gate, `report.py`/`rounding.py` each ≥ 95% line+branch — both 100%.
- [x] `ruff check` / `ruff format --check` exit 0 — re-run by reviewer.
- [x] Engine isolation — `test_engine_isolation.py` is part of the green run; both modules import only stdlib
  and relative modules (read).
- [x] `quantize|round(` only in `rounding.py` — grep above.
- [x] No `zone_for_hour`, exactly one `classify_hours` call in `report.py` — grep above.
- [x] Diff touches only the "Files" list; the four frozen engine modules are unchanged — verified by the
  reviewer with `git status` + `git diff --stat origin/master` (the implementer had not run it).
- [x] SPEC §4 documents decisions 8–11, rounding (2/3/4 decimals, `ROUND_HALF_UP`, output only) and the
  accepted 0.01 display difference; §3 now points to §4 — read the diff.
- [x] Public-repo hygiene — only `sensor.plug_0N`, generic prices, `Europe/Moscow`/`Europe/Berlin`; grep for
  IPs, hostnames and local paths in all changed/new files found nothing.
- [ ] CI: `uv run --group ha pyright` — not verifiable here (CI).
- [ ] CI: required checks green — not verifiable here (CI).

## Human decisions and focus areas
- **Exact Decimal, no rounding in the engine.** All aggregation is inside `localcontext(prec=50)`
  (`report.py:132`); no `quantize`/`round` outside `rounding.py`. Cost is computed per hour
  (`kwh * price`), and totals are independent exact sums. `test_exact_sums_independent_of_caller_context` shows
  that a caller's `prec=5` context has no effect.
- **Rounding only through the helper, half-up.** `rounding.py` quantizes with `ROUND_HALF_UP` at prec 50,
  normalizes `-0.00`, rejects non-Decimal/bool/non-finite values. The 0.01 display difference is pinned by
  `test_totals_are_exact_not_sums_of_rounded_cells` and documented in SPEC §4.
- **Missing never a silent zero.** Missing hours only increment `coverage.missing`. Cells use `dict.get` →
  `None` when no counted hour. Row `kwh` is `None` iff `counted == 0`. Row `cost` is `None` iff no priced
  counted hour. Total row uses `sum_optional`. A measured `0` stays `Decimal("0")` (tested).
- **DST buckets.** `start = local_start` of the first hour, `end = (utc_start + 1h).astimezone(tz)` of the
  last. 23/25-h days, 743/745-h months, 167/169-h weeks and the offsets on both edges are asserted for Berlin.
  The parametrized invariant test checks contiguity and the window edges for all five groupings across DST and
  month ends.
- **Plan switch inside a bucket.** Prices are tracked per slot × zone. A differing value flips the slot to `None`
  and it stays `None`. Equal-by-value prices (`10.3` vs `10.30`) keep the first one met. Both the price-change
  and the rename-only WEEK cases are tested, and `effective_price == 10.7` is checked. Switches only happen at
  local midnight, so DAY and HOUR buckets can never mix plans. This is correct.
- **Hook for task 007.** `build_report(request, schedule, devices)` stays positional, and `prepare_measured`
  is the only call 007 needs to replace. `assemble_report` already handles ESTIMATED (counted, plus
  `estimated_kwh`/`coverage.estimated`) and EXCLUDED (only `excluded_kwh`/`coverage.excluded`, not in `kwh`,
  cells or cost). `issues` pass through unchanged. Input validation covers length mismatch, duplicate ids
  and empty hours. Look-back keys are ignored by `prepare_measured` and remain available to 007 through
  `series.deltas`.

## Findings
### Required
None.

### Suggestions
1. `tasks/006-pricing-and-grouping.md` acceptance criteria — the "tests first" box is ticked although the
   implementation notes say `rounding.py` was written before its tests were run red. Annotate the box, e.g.
   "(rounding.py: tests written first but not run red, see notes)", so the ticked list stays truthful.
2. `tasks/006-pricing-and-grouping.md` implementation notes — "`git diff --stat origin/master` not checked
   (no git network)" is stale. `origin/master` is a local ref and the reviewer has now verified the criterion.
   Reword the note.
3. `tests/unit/test_report.py:536-546` — `0.1234567890123456789 × 24` (and × 10.30) is exact even in the
   default 28-digit context. The first assertion therefore cannot tell `prec=50` apart from the default, and
   only the `prec=5` part proves the engine uses its own context. A value with about 35 significant digits would
   also pin "more than the default precision".
4. `tests/unit/test_report.py:610-646` — `test_assemble_estimated_and_excluded` asserts kWh but not cost.
   Add `row.cost == Decimal("201.68")` (17 × 10.30 + 6 × 4.43) to prove that estimated kWh are priced and
   excluded kWh are not. That is the exact contract 007 relies on.
5. `report.py:132` / `rounding.py:25` — exactness beyond 50 digits is silently rounded, because `Inexact` is
   not trapped. Consider `localcontext(prec=50, traps=[Inexact])` in the engine, so an impossible-to-represent
   input fails loudly instead of quietly breaking the "exact sums" promise. Also, `round_*` on a value with
   more than ~48 integer digits raises `decimal.InvalidOperation` rather than `ValueError`. That input is
   unrealistic, but either document it or map it to `ValueError`.
6. `tests/unit/test_report.py:221` — `test_unpriced_hours_before_first_plan` checks only `len(report.plans) == 1`.
   `report.plans == schedule.plans` would pin which plan. The Dec 31 cells could also assert `cost is None`.
7. Optional: no test pins the lowercase `HourKind` values (`"measured"`, `"estimated"`, `"excluded"`) required
   by decision 2. Add a one-liner if 007 or stage 3 will serialize them.
