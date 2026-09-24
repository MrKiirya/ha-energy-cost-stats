# Energy Cost Stats — agent guide

Home Assistant custom integration (HACS) + Lovelace card: electricity cost **per device, split by tariff zones**,
retroactively, from recorder long-term statistics. Domain `energy_cost_stats`.
Full product spec: [docs/SPEC.md](docs/SPEC.md) — read the sections your task references, not the whole file.

## Core principles (do not violate)
1. **No per-device entities.** Per-device data only via websocket API, service with response, and the card.
   Max ~3 global entities (Recalculate button, current zone, current price).
2. **Read, don't duplicate.** Source of truth is recorder long-term statistics (hourly `change`).
3. **Retroactive by design.** Any tariff plan change must correctly re-price all past hours.
4. **Engine is pure Python** (`custom_components/energy_cost_stats/engine/`): no `homeassistant` imports.
5. **Recorder API behind one adapter module.** Nothing else imports `homeassistant.components.recorder`.
6. **Tests first.** Write the failing test, then the code.

## Environment
- Develop inside the **devcontainer** (HA does not run natively on Windows; the engine's unit tests do).
- Python **3.14** (dev, latest HA); CI also runs minimum HA **2025.4** on Python **3.13**.
- Python deps via **uv**; card via **npm** (Node 24 LTS).

## Commands
> Planned — created by the scaffold task. Update this section when they change.

| Purpose | Command |
|---|---|
| Install deps | `script/setup` |
| Unit tests (engine, fast) | `uv run pytest -m unit` |
| Integration tests (HA harness) | `uv run pytest -m integration` |
| All tests + coverage | `script/test` |
| Lint + format check | `script/lint` (`ruff check`, `ruff format --check`) |
| Type check | `uv run pyright` |
| Card tests / build | `npm test` / `npm run build` (in `frontend/`) |
| Run dev HA | `script/develop` |

## Test levels
- `unit` — engine only, pure pytest, no HA. Coverage gate ≥ 95% for `engine/`.
- `integration` — `pytest-homeassistant-custom-component`, in-memory recorder, statistics seeded via
  `async_import_statistics`; config flow, websocket, service.
- `golden` — real statistics fixtures → report snapshots (syrupy). Raw exports live in the git-ignored
  `tests/fixtures/private/` (tests skip if absent); only **anonymized** fixtures are committed
  (generic entity ids like `sensor.plug_01`, shifted dates, no names/areas/locations).

## Public repo hygiene
Never commit: real entity ids/device names from the author's home, raw statistics exports, HA `config/`
runtime data, secrets, tokens, IPs/hostnames, local absolute paths (`C:\Users\...`, `D:\...`).
Task and review files are public too — use generic examples.
- Card — Vitest with mocked `hass.callWS`.

## Definition of done
- New behaviour covered by tests written first; all test levels touched by the change are green.
- `ruff check`, `ruff format --check`, `pyright` pass.
- `docs/SPEC.md` / this file updated if behaviour, commands or conventions changed.
- Task file acceptance criteria all checked.

## Git & GitHub
- Default branch: **`master`**. Repo: `MrKiirya/ha-energy-cost-stats` (public).
- One branch per task: `task/NNN-short-name` → PR → green CI → merge.
- Only the main session runs git write operations; subagents never commit, push or open PRs.
- Never rewrite published history (`push --force`, `rebase`/`reset` of pushed commits) without being asked.
- Commit messages: Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`, `ci:`, `refactor:`).
- No local git pre-commit hooks (commits may be made from a Windows GUI client); formatting is enforced
  by Claude Code hooks and CI.
- Personal, machine-local instructions go to the git-ignored `CLAUDE.local.md`.

## Language
Everything in the repo — code, comments, docs, task files, commit messages, PRs — is **English**.

## Agent workflow
- **Main session = orchestrator.** Talks to the human, runs agents, does not read code deeply.
- `planner` (opus): writes `tasks/NNN-name.md` — goal, spec sections, files, tests to write,
  acceptance criteria, out of scope.
- `implementer` (sonnet): reads CLAUDE.md + the task file (+ referenced spec sections); tests first;
  returns a one-line status.
- `reviewer` (opus, fresh context): checks the diff against the task file, runs tests and lint,
  writes `tasks/NNN-review.md` with verdict `APPROVE` / `CHANGES_REQUESTED`.
- Max 2 review iterations, then escalate to the human.
- **Light path:** trivial changes (typos, version bumps, one-line config) are done directly by the
  main session without planner/reviewer.
