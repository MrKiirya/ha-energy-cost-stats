# 012 — Review (round 2)

Verdict: APPROVE

Scope: `git diff task/011-recorder-adapter` plus the untracked `engine/serialize.py`, `tests/unit/test_serialize.py`
and `tasks/012-report-serializer.md` (`tasks/013-*` ignored). Planner decisions D-1 … D-4 accepted.

## Round 1 items
- **Required 1 (issue `hours` wrong on DST days): resolved.** `serialize.py:89-95` adds `_elapsed_hours`, which
  does `divmod(end.astimezone(UTC) - start.astimezone(UTC), _HOUR)` and raises `ValueError` on a non-whole-hour
  remainder. `_issue` uses it (line 104). My round 1 probe (Berlin, a 4-hour gap across each transition) now gives
  `"hours": 4` on both 2026-10-25 and 2026-03-29 (round 1: 3 and 5).
- Suggestion 2 (nested key order): done, in `test_nested_key_order`.
- Suggestion 3 (whole-hour check): done, in `test_issue_span_must_be_whole_hours`.
- Suggestion 1 (`time_zone` vs the tzinfo): not done, by the coordinator's decision. It stays a suggestion for 013.
- SPEC §4 Issues bullet now says "real elapsed hours of the issue span (not wall-clock, so correct across DST
  changes)".

## Do the new tests catch the old code?
I patched `engine.serialize._elapsed_hours` in memory back to the round 1 formula `(b - a) // _HOUR` and ran
`tests/unit/test_serialize.py` (no files changed) → `4 failed, 12 passed`:
- `test_issue_hours_across_dst[...-25]` (fall-back) failed.
- `test_issue_hours_across_dst[...-23]` (spring-forward) failed.
- `test_issue_hours_spike_in_fall_back_fold` failed: the start is `02:00+02:00`, the end `02:00+01:00`, and the old
  formula gave 0.
- `test_issue_span_must_be_whole_hours` failed.

So the tests are meaningful. They also check the issue `hours` against `coverage.estimated`/`excluded` and against
the window's 25/23 hours.

## Other same-zone aware-datetime arithmetic in `engine/`
I grepped every datetime `-` / `+ timedelta` / `// _HOUR` in `engine/`:
- `quality.py:93` `pos()`: `moment - window_start`. `window_start` is `hours[0].utc_start` (UTC), and `moment`
  is a series key. `DeviceSeries.__post_init__` normalises every key to UTC. OK.
- `quality.py:110` catch-up span `(key - keys[index - 1]) // _HOUR`: both are normalised UTC keys. OK.
- Issue clipping (`quality.py:111-135`: `span_first`, `min(catch_up, count - 1)`) works on integer hour indices,
  not datetimes. OK.
- `quality.py:101` issue `end`, `report.py:273` bucket `end`: `(utc_start + _HOUR).astimezone(tz)`, so the
  arithmetic happens in UTC before the conversion. OK.
- Bucket `hours` = `last - first + 1` (index count). OK.
- `timeutil.py:55` candidates: `guess` is UTC. OK.
- `classify.py:90`: `date - timedelta(days=...)` on a `date`, not a datetime. OK.
- `serialize.py` top-level `start`/`end`: `request.start/end.astimezone(tz).isoformat()`, a conversion only, no
  subtraction. Bucket and issue times are `isoformat()` of the engine values. OK.
- `serialize.py:92` is now the only datetime subtraction in the serializer, and it runs in UTC.

No other cases found.

## Checks run (devcontainer)
- `sh script/test` → `450 passed in 28.08s`; `Required test coverage of 95% reached. Total coverage: 100.00%`
  (`serialize.py` 47/47 statements, 8/8 branches).
- `uv run --group ha pytest -m unit --cov=custom_components/energy_cost_stats/engine --cov-branch --cov-report=term-missing --cov-fail-under=95`
  → `344 passed, 106 deselected`; `Total coverage: 99.82%`. The only miss is `plan_codec.py:41`. That line is from
  task 010, is covered by the integration tests, and does not matter for 012.
- HA 2025.4.0 leg (`.venv-313`, `--no-sync`) `pytest -m integration` → `106 passed, 344 deselected in 19.81s`.
- `uv run --group ha pyright` → `0 errors, 0 warnings, 0 informations`.
- `uv run --group ha ruff check .` → `All checks passed!`; `ruff format --check .` → `75 files already formatted`.
- `rg` rounding helpers → only `engine/serialize.py` and `engine/rounding.py`; `rg float serialize.py` → none.
- `test_classify.py`/`test_report.py` diff vs 011 → 0 removed lines.

## Acceptance criteria
- [x] Tests first: recorded in the Implementation notes, including the round 1 fix. I confirmed independently that
  the new tests fail on the old formula (above).
- [x] `pytest -m unit` all pass; existing classify/report tests unchanged.
- [x] Coverage gate passes; `serialize.py` 100 % line+branch.
- [x] ruff check / format clean.
- [x] `test_engine_isolation.py` passes. `serialize.py` is stdlib + relative imports only (`UTC` from `datetime`).
- [x] Rounding helpers only in `serialize.py`.
- [x] No `float` in `serialize.py`.
- [x] SPEC §4 contract subsection and no-plan bullet present; no other section changed.
- [x] Only files from "Files" touched; generic ids only.
- [x] pyright 0 errors.
- [ ] Required PR checks green: pending PR (not verifiable here).

## Contract check (unchanged since round 1, re-verified)
- Keys, order (top-level and nested, both now asserted), types (`str`/`int`/`None` only), null rules, ISO times
  with offset, `plans` unrounded, totals rounded from exact sums, and the `Report` is not mutated.
- `schedule=None` behaviour: no change with plans.
- SPEC additions (`devices[].statistics` = 011 `StatisticsStatus` values; consumers ignore unknown keys) are
  consistent with the 011 adapter.

## Findings
### Required
None.

### Suggestions
1. `serialize.py:122-123` (carried over, deferred to 013): consider checking the `time_zone` string against
   `report.request.time_zone` (e.g. a `ZoneInfo.key`), so the document's name cannot disagree with its offsets.
