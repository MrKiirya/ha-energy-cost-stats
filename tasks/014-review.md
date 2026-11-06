# 014 — Review (round 1)

Verdict: APPROVE

Reviewed: `git diff 8c399dd..HEAD` on `task/014-cost-card` (5 commits, base = task 013 tip).

## Checks run
- `sh script/test` (container `ecs-dev`, py3.14, HA latest) → `504 passed in 82.32s`; engine coverage `TOTAL 816 0 278 0 100%`.
- `sh script/lint` → `All checks passed!`, `83 files already formatted`.
- `uv run --group ha pyright` → `0 errors, 0 warnings, 0 informations`.
- `npx vitest run` (frontend/) → `Test Files 3 passed (3)`, `Tests 75 passed (75)`.
- `npx tsc --noEmit` → no errors.
- `npm run check-bundle` → `Card bundle is up to date.` (committed bundle matches the sources).
- Bundle content: no Lit dev-mode string (production build), contains `whenDefined("home-assistant")`.
- `node --version` / `npm --version` in the devcontainer → `v24.22.2` / `11.19.1`; base image and node image are both Debian trixie (glibc / libstdc++ match).
- Node image digest: Docker Hub index digest of `node:24.22.2-trixie-slim` = `sha256:0820eaa8…3812d`, same as the Dockerfile.
- `git ls-remote actions/setup-node refs/tags/v7.1.0` → `949feb24…`, same as the pinned SHA in `ci.yml`.
- HA 2025.4.0 sources: `homeassistant/components/http/__init__.py` defines `StaticPathConfig` (line 148);
  `frontend.add_extra_js_url(hass, url, es5=False)` exists; `frontend/__init__.py` imports `hass_frontend` only
  lazily, so the top-level import in `frontend.py` is safe on the minimum version.
- HA frontend `src/html/index.html.template` (dev): `<home-assistant></home-assistant>` (line 143) precedes the
  `import("{{ extra_module }}")` loop (line 185), so `document.querySelector("home-assistant")` is non-null when the
  extra module runs and the deferred-define branch is the one taken.
- Privacy: all 36 statistic ids from `tests/fixtures/private/ha_energy_statistics.csv` grepped against the full diff
  (`--text`, incl. bundle) → no match; `tests/fixtures/private/` is git-ignored and untracked; no local paths, IPs or
  personal names in the diff (only generic `sensor.plug_0N` test ids).
- Not run: actionlint (not in the container), 3.13 / HA 2025.4.0 leg (CI), `podman build` (container already built
  from this Dockerfile and running).

## Acceptance criteria
- [x] `podman build .devcontainer` succeeds; node v24.22.2, npm 11 — verified in the running `ecs-dev` container
      (built from this Dockerfile): `v24.22.2`, `11.19.1`.
- [x] `npm test` → 75 passed; typecheck clean; `check-bundle` up to date — re-run above.
- [x] `script/test` all passed, engine coverage 100 %; `script/lint` clean; pyright 0 errors — re-run above.
- [ ] actionlint clean — not re-run (tool not available here); workflow change read by hand, looks valid.
- [x] Dev HA with real statistics, Playwright — not reproducible by the reviewer; trusted from the implementer.
      The registration fix it found is consistent with the HA page template (see Checks).
- [ ] CI green on the PR — pending (human / `workflow_dispatch`).

## Findings
### Required
None.

### Suggestions
1. `frontend/src/card.ts:132-134`, `:183-197` — **first request uses HA's time zone, not the integration's.**
   `_timeZone` falls back to `hass.config.time_zone` until a report arrives; the integration has its own
   `time_zone` option (`settings.py`). If they differ, the first request's naive "current hour" end is read by the
   backend in the other zone (future hours shown as missing, or finished hours dropped) and "today" for the initial
   preset can be off by a day near midnight; nothing re-fetches when `report.time_zone` turns out different, so
   it stays wrong until the 10-minute refresh. Direction: after a report arrives, if `report.time_zone` differs from
   the zone used for the request, recompute the initial period (if still the configured preset) and reload once.
2. `frontend/src/period.ts:244-263` — **DST fall-back hour.** During the repeated local hour (e.g. 02:xx CET
   after 03:00 CEST → 02:00 CET), the card sends `T02:00:00`; `parse_bound` reads it with `fold=0`, i.e. one hour
   earlier than the start of the current hour, so the finished hour is omitted for that hour. Self-heals, but worth
   a comment + test, or send an explicit offset (`T02:00:00+01:00`, which `parse_bound` already accepts via
   `parse_datetime`) to remove the ambiguity entirely. The backend has no test for a naive bound inside the fold
   either. (Spring-forward is fine: the current local hour always exists.)
3. `frontend/src/card.ts:151-155` — **the last hour of a period is never fetched on an open dashboard.** The
   refresh stops as soon as the period no longer contains today, so "today" left open over midnight keeps the
   23:00-ended report (and a "partial" badge) until a manual refresh. Direction: one more load on the first tick
   where `containsDate` turns false (or at the next hour boundary after the period end).
4. `frontend/src/card.ts:305-318` — **preset `<select>` shows a stale choice.** `.value=${preset}` is dirty-checked
   against the last committed value, not the live DOM: after choosing "Custom period…" and then applying a range
   equal to the current preset (or just leaving the panel open), the select keeps showing "Custom period…". Use
   Lit's `live()` directive for `.value` (same for the grouping select at `:523`). There is also no way to close
   the custom panel without applying a range or choosing a preset; a cancel/close button would help.
5. `frontend/src/card.ts:523-533` — **grouping select can show a disabled option as selected.** With
   `grouping: hour` and a period > 31 days, the request silently falls back to auto (tested), but the select still
   shows the disabled "Hours: up to 31 days". Bind the select to the effective choice (`"auto"` when the stored
   choice is not allowed) so the UI matches the request.
6. `frontend/src/card.ts:554-559` — **week bucket label for a clipped last bucket.** `addDays(end.date, -1)`
   assumes `bucket.end` is local midnight; for a period containing today the last bucket ends at the current hour
   (e.g. `…T14:00`), so the label ends on yesterday although the bucket includes today. Subtract a day only when
   the end time is `00:00`.
7. `frontend/src/card.ts:171-181`, `:188` — `_load()` sets `_loading = true` synchronously from `updated()`, which
   triggers Lit's "change-in-update" warning seen in the test output and an extra render per load. Start the load
   from `willUpdate` (set `_loading` there) or defer with `await this.updateComplete`/microtask.
8. `frontend/src/index.ts:319-328` — the deferred define relies on the boot-time registry's `whenDefined` resolving
   after the polyfill swap (confirmed by the implementer's Playwright run on 2026.9). If a future frontend breaks
   that, the card silently never appears. Cheap safety net: a `console.warn` (or a define attempt on the then-current
   `window.customElements`) if `whenDefined` has not resolved after e.g. 10 s.
9. `custom_components/energy_cost_stats/frontend.py:38-40` — the static path uses `cache_headers=True` (long cache).
   Fine for the `?v=` extra-module URL; users who also add `/energy_cost_stats/energy-cost-stats-card.js` as a manual
   resource without `?v=` will get a stale bundle after updates. Worth one line in the README/SPEC §4.1 ("no
   dashboard resource needed; if you add one, include `?v=`").
10. `frontend/src/card.ts:497-498` — breakdown rows are picked by index into `bucket.rows`; correct today (the
    serializer enforces device order = row order), but looking the row up by `entity_id` would make the card
    independent of that invariant and avoid falling back to the *total* row under a device label.

### Notes on the focus areas
- Period arithmetic matches the described HA `shiftDateRange` semantics: whole-month ranges shift by month count
  (month 1, quarter 3, year / 12 months 12, month-end preserved incl. Feb / leap years), everything else by day
  count; "now" keeps the kind; weeks Monday-based as documented. Pure calendar math on UTC-midnight dates, no DST
  exposure. On Sundays `this_week` and `now-7d` coincide; the picker shows `this_week` (harmless).
- `requestEnd` → `parse_bound`: naive `YYYY-MM-DDTHH:00:00` is accepted (read in the settings zone, fold 0, must be a
  whole UTC hour); the non-whole-hour-offset fallback (`minute !== getUTCMinutes()`) is correct for +05:30 / +05:45
  zones; the `max(hour, 1)` first-hour rule avoids an empty range. Only the fold edge (suggestion 2) and the zone
  mismatch (suggestion 1) remain.
- Dockerfile: both COPY lines identical ref, tag and digest verified, npm/npx symlinks relative and working;
  `/usr/local` Python untouched.
- CI `card` job: pinned actions, `npm ci` from the lock, typecheck/test/check-bundle; the ruleset context `card`
  matches the job `name:`. Re-applying the ruleset on GitHub is left to the human (out of scope, as stated).
