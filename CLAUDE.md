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
- **Hybrid setup.** Engine unit tests and ruff run natively on any OS (incl. Windows): `uv sync` installs
  tooling only, no Home Assistant. Anything that needs HA — integration tests, pyright, dev HA — runs in the
  Linux **devcontainer** / CI, where `uv sync --group ha` adds Home Assistant.
- **Entering the devcontainer.** VS Code: "Reopen in Container" (needs Docker Desktop with Linux containers).
  Headless: `npx @devcontainers/cli up|exec --workspace-folder .` (needs Node/npx on the host).
- Inside the container: the uv-managed venv lives at `/opt/venv`, the uv package cache in the named Docker
  volume `energy-cost-stats-uv-cache` — neither ever touches the Windows checkout.
- `config/` holds the dev Home Assistant runtime data (SQLite DB, `.storage/`, logs); it is git-ignored except
  the committed `config/configuration.yaml`. In the devcontainer this runtime data actually lives in the named
  volume `energy-cost-stats-ha-config` (`HA_CONFIG_DIR`), which `script/develop` links to `config/configuration.yaml`
  on every start so repo edits take effect without polluting the Windows checkout.
- Python **3.14** (dev, latest HA); CI also runs minimum HA **2025.4** on Python **3.13**.
- Python deps via **uv**; card via **npm** (Node 24 LTS).

## Commands
Two setups (see Environment above): Windows native has no Home Assistant; Linux container / CI has it via
the opt-in `ha` dependency group.

| Purpose | Where | Command |
|---|---|---|
| Install deps (no HA) | Windows native | `uv sync` |
| Install deps (with HA) | Linux container / CI | `script/setup` (= `uv sync --group ha`) |
| Unit tests (engine, fast) | either | `uv run pytest -m unit` |
| Integration tests (HA harness) | Linux container / CI | `uv run --group ha pytest -m integration` |
| All tests + coverage gate | Linux container / CI | `script/test` |
| Lint + format check | either | `uv run ruff check .` / `uv run ruff format --check .` (Windows), `script/lint` (Linux container / CI) |
| Type check | Linux container / CI | `uv run --group ha pyright` |
| Card tests / build | stage 4 | `npm test` / `npm run build` (in `frontend/`) |
| Run dev HA | devcontainer | `script/develop` |
| Smoke-test dev HA | devcontainer / CI | `script/smoke-develop` |
| Open / check devcontainer headlessly | Windows host (Node/npx) | `npx @devcontainers/cli up --workspace-folder .` / `npx @devcontainers/cli exec --workspace-folder . <cmd>` |

On Windows native, `uv run pytest -m integration` and `-m golden` exit with code 5 ("no tests ran";
`tests/integration` is ignored because the HA test harness isn't installed) instead of failing.

**Never run a bare `uv sync` in the container while a dev HA (`script/develop`) is running.** `uv sync` is an
exact sync: it removes any package not in `uv.lock`, including the runtime requirements Home Assistant (or
`script/setup`, see below) installed into the venv outside the lock. Racing a live HA startup with a concurrent
`uv sync` can strip a package HA just installed and push the instance into recovery mode. Use `script/setup`
instead — besides syncing, it pre-installs `default_config:`'s runtime requirements once, up front (see
`script/prefetch_ha_requirements.py`), so `script/develop` normally needs no runtime installs at all.

## Test levels
- `unit` — engine only, pure pytest, no HA. Coverage gate ≥ 95% for `engine/`. Unit tests import `engine…`
  only, never `custom_components.energy_cost_stats…` (dual-name caveat: the same files are also importable
  as `custom_components.energy_cost_stats.engine…` at integration runtime, but that is a distinct module
  object — see `custom_components/energy_cost_stats/engine/__init__.py`).
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
- Split a task branch into **several logical commits** (tests, implementation, docs, task/review files) so the
  PR reads commit by commit; PRs are opened as drafts and squash-merged after the human's review.
- No local git pre-commit hooks (commits may be made from a Windows GUI client); formatting is enforced
  by Claude Code hooks and CI.
- Personal, machine-local instructions go to the git-ignored `CLAUDE.local.md`.

## Language
Everything in the repo — code, comments, docs, task files, commit messages, PRs — is **English**.

## Agent workflow
- **Main session = orchestrator.** Talks to the human, runs agents, does not read code deeply.
- **Subagents always run in the background** (never blocking), so the chat stays responsive;
  the main session relays the result when the agent completes.
- `planner` (opus): writes `tasks/NNN-name.md` — goal, spec sections, files, tests to write,
  acceptance criteria, out of scope.
- `implementer` (sonnet): reads CLAUDE.md + the task file (+ referenced spec sections); tests first;
  returns a one-line status.
- `reviewer` (opus, fresh context): checks the diff against the task file, runs tests and lint,
  writes `tasks/NNN-review.md` with verdict `APPROVE` / `CHANGES_REQUESTED`.
- Max 2 review iterations, then escalate to the human.
- **Light path:** trivial changes (typos, version bumps, one-line config) are done directly by the
  main session without planner/reviewer.
