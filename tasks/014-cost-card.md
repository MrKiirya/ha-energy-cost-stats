# 014 — Cost card with an Energy-style period picker

Status: in-review
Roadmap: stage 4 (card on mocked data, then on a dev HA instance with real statistics)
Spec sections: SPEC §2 (card serving), §4 (JSON contract), §4.1 (card, new)

## Goal
Users get `custom:energy-cost-stats-card`, served by the integration itself: a table of kWh and cost per device
and tariff zone for a chosen period, with a period picker that behaves like the Energy dashboard's (presets,
arrows that step by the period's own size, "now", custom range). The devcontainer gets Node 24 so the card can be
built and tested there, also on SELinux-enforcing rootless podman hosts.

## Context
- **Node in the devcontainer.** The devcontainers `node` feature installs through `RUN --mount`, which SELinux
  denies on rootless podman (Fedora Atomic), so the stock config did not build there. Node 24 (+ bundled npm) is
  now copied from the official `node:24.x-trixie-slim` image (tag + multi-arch index digest), like `uv` and
  `go2rtc`; the feature and its lock file are removed. Only `node` and `lib/node_modules/npm` are copied: the base
  image keeps Python in `/usr/local`.
- **Period picker reference.** Home Assistant frontend `hui-energy-period-selector.ts` and
  `common/datetime/calc_date.ts::shiftDateRange` (checked on `dev`, 2026-11-06): a range of whole months shifts by
  its month count, any other range by its day count; "now" keeps the kind (day / week / month / quarter / year /
  n months / n days). Presets there: today, yesterday, this week/month/quarter/year, now-7d, now-30d, now-365d,
  now-12m. We add last week / last month (asked for by the author) and drop now-365d. Weeks start on Monday
  here (engine grouping, SPEC §5) instead of the locale's first weekday.
- **Extra module vs. scoped registry.** `frontend.add_extra_js_url` modules are imported by `index.html` before the
  frontend's `core.js` installs the scoped custom element registry polyfill, which replaces
  `window.customElements`; an element defined earlier is invisible ("Configuration error"). Found on dev HA
  2026.9 (frontend 20260826.7) with Playwright; community threads report the same symptom for cards listed in
  `extra_module_url`. Fix: define after `customElements.whenDefined("home-assistant")`.
- **Bundle in git.** HACS installs the repository as is; the bundle is built by `npm run build` and committed,
  marked `linguist-generated` / `-diff`; CI checks it is up to date.

## Files
- modify: `.devcontainer/Dockerfile` — Node 24 + npm from the official image (pinned by tag and digest).
- modify: `.devcontainer/devcontainer.json` — drop the node feature; add the Vitest extension.
- delete: `.devcontainer/devcontainer-lock.json` — only locked the removed feature.
- create: `frontend/` — `package.json` / lock, `tsconfig.json`, `vitest.config.ts`, `build.mjs`,
  `src/{index,card,period,report,i18n}.ts`, `test/*.test.ts`.
- create: `custom_components/energy_cost_stats/frontend/energy-cost-stats-card.js` — built bundle.
- create: `custom_components/energy_cost_stats/frontend.py` — static path + extra module (content-hash URL).
- modify: `custom_components/energy_cost_stats/__init__.py`, `const.py` (`CARD_URL`), `manifest.json`
  (`http` dependency, `frontend` after-dependency).
- modify: `.github/workflows/ci.yml` — `card` job; `.github/rulesets/master.json` — `card` required (the
  repo convention: every non-canary job is required; re-applying the ruleset on GitHub is left to the human);
  `.gitattributes` — bundle as generated.
- modify: `docs/SPEC.md` (§2, new §4.1), `CLAUDE.md` (Node, podman note, card commands, card job).

## Tests to write first
| Level | Test | Asserts |
|---|---|---|
| unit | `tests/unit/test_devcontainer.py::test_devcontainer_json` | no `features` key |
| unit | `tests/unit/test_devcontainer.py::test_dockerfile_pins_node` | node COPY lines: `node:24.*`, digest-pinned, identical; npm link |
| integration | `tests/integration/test_card_resource.py` | bundle served at `CARD_URL` (200, same bytes); extra module URL with content hash when `frontend` is loaded; not added without it |
| card | `frontend/test/period.test.ts` | presets, kinds, shifts (day/week/month/quarter/year/custom, leap/Feb, year wrap), "now", time zones, request end at the current hour, auto grouping, 31-day hour limit |
| card | `frontend/test/card.test.ts` | request fields (exclusive end, entities, grouping), arrows/presets/now/custom range, table cells and totals, `null` → "—", badges, Russian, breakdown per device, grouping change, warnings, issues, errors, stale-response race |
| card | `frontend/test/register.test.ts` | defines only after `<home-assistant>` boots, in the final registry; immediate otherwise; no double define |

## Acceptance criteria
- [x] `podman build .devcontainer` (rootless, SELinux enforcing) succeeds; `node --version` → v24.22.2, npm 11.
- [x] `npm test` (in `frontend/`) → 75 passed; `npm run typecheck` → no errors; `npm run check-bundle` → up to date.
- [x] `script/test` → all passed, engine coverage 100 %; `script/lint` → clean; `uv run --group ha pyright` → 0 errors.
- [x] actionlint → clean.
- [x] Dev HA (2026.9) with a copy of real long-term statistics (27 energy sensors, months of history, kept
      outside the repo): the card renders on a dashboard, arrows/presets work, "by period" and data-quality
      sections render, no console errors (checked with Playwright screenshots).
- [ ] CI green on the PR (stacked on task 013; run via `workflow_dispatch`).

## Out of scope
- Tariff comparison ("what would this period cost on another plan") — next task.
- Visual card editor, design polish / theming, hiding retired sensors, charts.
- Re-applying the updated ruleset on GitHub (`gh api --method PUT ...`, human).
- Golden fixtures from real statistics (anonymized) and a Playwright e2e test in the devcontainer.

## Open questions
- Should rows of sensors with no data in the period (retired plugs) be hidden by default? They make every
  total row "partial".

<!-- Filled in by implementer -->
## Implementation notes
- Calendar logic works on `YYYY-MM-DD` strings with UTC-midnight `Date`s only, so it is free of DST; local
  instants are left to the backend (date bounds = local midnight in the settings time zone).
- For a period containing today the request `end` is the current local hour as a naive datetime (SPEC §2 allows
  it; must be a whole UTC hour, so zones with non-whole-hour offsets fall back to the date). Otherwise every
  future hour of "this month" was reported as missing and every row showed a "partial" badge.
- Lit with `static properties` (no decorators), `useDefineForClassFields: false`; icons are inline MDI paths and
  controls are native `<select>`/`<input type="date">`, so the card does not depend on HA's lazily loaded
  internal elements (`ha-select`, `ha-date-range-picker`), which custom cards cannot rely on.
- The frontend integration is not set up in integration tests (it needs `home-assistant-frontend`, not in the
  lock); the test marks `frontend` as loaded and patches `add_extra_js_url`.
- `StaticPathConfig` is imported from `homeassistant.components.http` (defined there in 2025.4, re-exported in
  later versions); pyright's private-import warning on latest HA is silenced on that line.

## Follow-ups
- Tariff comparison scenarios (task 015).
- Decide on hiding no-data sensors; design pass (HA-native styling first, see review notes).
- Optional Playwright e2e smoke test inside the devcontainer.
