# 011 — Review (round 2)

Verdict: APPROVE

## Checks run
All commands ran in the devcontainer.
- `sh script/test` (latest HA, py3.14) → `432 passed in 24.35s`, `Total coverage: 100.00%`
- `uv run --group ha pyright` → `0 errors, 0 warnings, 0 informations`
- `uv run --group ha ruff check .` → `All checks passed!`
- `uv run --group ha ruff format --check .` → `72 files already formatted`
- `sh script/lint` → exit 0
- HA 2025.4.0 (py3.13 venv, `--no-sync`) `pytest -m integration` → `106 passed, 326 deselected`
- `pytest tests/integration/test_recorder_adapter.py -rw` (latest) → `23 passed`, no warnings
- Throwaway probe tests (written to the container's `/tmp`, deleted afterwards, not in the repo) → `4 passed` on
  both legs. They cover:
  - a NULL baseline before the unbounded look-ahead step `[end+31d, None)`;
  - an id with no rows in the main range, NULL rows before every query start on both sides, and neighbours found
    only by the far steps;
  - `Wh` with a NULL baseline before the main query;
  - two ids where only one has a NULL baseline.

## Previous required items
1. NULL-sum baseline (round 1 Required 1) — **resolved.** `_query` requests `{"sum", "change"}` and marks the
   first usable row of each query. `_change` recomputes that row as `sum − previous fetched non-null sum`. The
   round 1 probes are now regression tests (`test_null_sum_row_before_main_query_start`,
   `..._before_lookahead_query_start`, plus `..._before_lookback_step_start` as a guard). SPEC §5 and the task
   notes now describe the real HA behaviour.

### Is recomputing only the first row of each query fully correct?
Yes. Each point below was checked against the code and the HA source (`_augment_result_with_change`, the same at
2025.4.0 and latest):
- **NULL rows inside a query.** HA does not advance `prev_sum` over a NULL row. So every non-first row of a query
  already has the right baseline: the previous non-null row of the same query. Only the first row's baseline comes
  from `_statistics_at_time`, which may be a NULL row (taken as 0). That is exactly the row the adapter recomputes.
  A leading NULL row inside the query does not matter either: HA skips it, and the next row is the one marked
  first.
- **Is the "previous fetched non-null row" the true predecessor?** Yes. For each id, the ranges queried are always
  contiguous: main `[s−1d, e+1d)`, and only if still needed `[s−31d, s−1d)`, then `[EPOCH, s−31d)`; on the other
  side `[e+1d, e+31d)`, then `[e+31d, None)`. A fallback step runs only when the steps before it found no usable
  row on that side. So all rows between the earliest queried bound and any kept key have been fetched, and the row
  just before a query's first row in the merged, sorted list is its true previous non-null row. This holds across
  every look-back/main/look-ahead boundary, including an id whose main range is empty (probe 2).
- **Index 0 (no earlier fetched row).** HA's `change` is kept. Either there is no non-null row earlier in history
  (then HA's baseline of 0 is the same rule as "first row ever"), or it is a look-back key that is not the first in
  the merged list (then it is recomputed). The engine's spike limit is a fixed per-hour value (`quality.py`), so a
  look-back key's own value cannot affect in-window hours.
- **Units.** The recomputed difference uses converted sums, the same arithmetic HA performs (probe 3: `Wh` →
  exactly `1`).

## Acceptance criteria
- [x] Tests first — recorded in the Implementation notes (round 1 collection error; round 2 regression tests
  failed before the fix on both legs). I accept the note.
- [x] `pytest tests/integration/test_recorder_adapter.py` → 23 passed (latest; the 2025.4.0 integration run
  includes them).
- [x] `script/test` → all levels pass, engine coverage 100 %.
- [x] pyright → 0 errors.
- [x] `script/lint` → exit 0.
- [x] Unit tests pass. No unit test changed.
- [x] `homeassistant.components.recorder` appears only in `recorder_adapter.py`. `get_instance` comes from the
  public `homeassistant.helpers.recorder`, which exists at 2025.4.0 and on latest. Accepted.
- [x] No `_statistics_at_time` or `db_schema` in `custom_components/`.
- [x] `statistics_during_period` is called with keyword arguments only.
- [x] No `float(` / `Decimal(` in the adapter. Floats reach the engine only through `DeviceSeries.from_floats`.
- [x] SPEC §2/§5/§6 updated as listed, and no other section changed. The §5 text is now accurate.
- [x] Only the listed files are touched (012/013 ignored as instructed). Hygiene: generic ids only, no paths or
  secrets.
- [ ] CI legs — not run yet (PR not opened). Expected to be open at this point.

Round 1 suggestions 1, 2 and 4 were done: the executor test also wraps `get_metadata` and checks for exactly one
`async_add_executor_job`, `test_future_lookahead_steps_are_skipped` was added, and the seed fixture maps `W`/`kW`
to `power`. Suggestion 3 (an optional guard on `helpers.recorder`) was not done. That is acceptable.

## Findings
### Required
None.

### Suggestions
1. `tasks/011-recorder-adapter.md` Implementation notes ("Non-first rows keep HA's `change` (computed before unit
   conversion, so no float noise for Wh)") and the docstring of `_change` — the reason given is wrong. HA converts
   `sum` first (`_build_sum_converted_stats`). `_augment_result_with_change` then runs on the converted sums and
   converts the baseline too. So HA's `change` is the same float subtraction on kWh values that the adapter does.
   Recomputing every row except index 0 would give bit-identical results and a simpler rule (no `first` flag).
   The current hybrid is correct, so this is optional. Either simplify it, or reword the note to say that HA's
   values are kept for non-first rows because they are already right.
2. `recorder_adapter.py:196-199` — three passes over `ordered` to build the index lists. This is fine at report
   sizes. A single `bisect` on `start`/`end` would be clearer if the module is touched again.
