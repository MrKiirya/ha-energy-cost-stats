# 002 — Devcontainer (VS Code / Dev Containers, dev HA on :8123)

Status: in-review
Roadmap: SPEC §8 stage 0 (project setup), task 2 of 3 (001-scaffold, 002-devcontainer, 003-ci)
Spec sections: SPEC §6 (HA compatibility, min HA 2025.4 / latest), §8 (roadmap); CLAUDE.md (Environment, Commands,
Public repo hygiene); `tasks/001-scaffold.md` (Decisions 2, 9, 11, 12 and "One-off container verification")

**Depends on 001-scaffold being merged** (or this branch being cut from it): it builds on `pyproject.toml`,
`uv.lock`, `.python-version` and `script/setup|test|lint|develop` from 001.

## Goal
A developer on a Windows host with Docker Desktop (Linux containers) opens the repo in VS Code, picks
"Reopen in Container", and gets a Linux environment with Python 3.14, uv, Node 24 LTS and the full `ha`
dependency group installed (via `script/setup` as post-create). In that container `script/test`, `script/lint`,
`uv run --group ha pyright` pass. `script/develop` starts a dev Home Assistant on port 8123 (forwarded to the
host) with `energy_cost_stats` loaded and debug logging for our domain. The same container can be built and
exercised headlessly by an agent (Dev Containers CLI), including a scripted smoke check that the dev HA
starts, answers on :8123 and then stops.

## Context

### Images and features (checked 2026-09-24)
- **Base image:** `mcr.microsoft.com/devcontainers/python`. The tag list has `3-3.14-trixie` and
  `3-3.14-bookworm` (the leading `3-` is the image major version; `2-…` and `dev-…` also exist)
  ([MCR tag list](https://mcr.microsoft.com/v2/devcontainers/python/tags/list)). Use **`3-3.14-trixie`**:
  Debian trixie matches the uv images 001 used (`ghcr.io/astral-sh/uv:python3.14-trixie`). The image ships a
  non-root `vscode` user, git and curl.
- **uv:** no official Astral devcontainer feature exists; the community one is
  `ghcr.io/va-h/devcontainers-features/uv:1` ([va-h/devcontainers-features](https://github.com/va-h/devcontainers-features/tree/main/src/uv),
  [astral-sh/uv#8737](https://github.com/astral-sh/uv/issues/8737)). The uv Docker guide's recommended install
  is `COPY --from=ghcr.io/astral-sh/uv:<exact version> /uv /uvx /bin/` (the docs example pins `0.12.18`)
  ([uv — Docker guide](https://docs.astral.sh/uv/guides/integration/docker/)). **Decision:** use the official
  `COPY --from` in a small Dockerfile, pinned to the exact uv version current at implementation time. No
  third-party feature for uv.
- **Node:** official feature `ghcr.io/devcontainers/features/node`, current version `2.1.0` (so major tag `:2`).
  Options: `version` (default `lts`; `"24"` accepted), `pnpmVersion` (default `latest`), `npmVersion`
  (default `none` = keep bundled npm) ([devcontainer-feature.json](https://raw.githubusercontent.com/devcontainers/features/main/src/node/devcontainer-feature.json)).
  **Decision:** `"ghcr.io/devcontainers/features/node:2": {"version": "24", "pnpmVersion": "none"}`: pin the
  major explicitly (Node 24 LTS per CLAUDE.md), we use npm, not pnpm. Note: features are applied only by the
  Dev Containers tooling, not by a plain `docker build` of the Dockerfile.
- **Reference setup:** ludeeus/integration_blueprint `.devcontainer.json` (image + python feature 3.14,
  `postCreateCommand: scripts/setup`, `forwardPorts: [8123]`, apt packages `ffmpeg,libturbojpeg0,libpcap-dev`,
  extensions ruff / python / pylance, `files.eol: "\n"`)
  ([.devcontainer.json](https://github.com/ludeeus/integration_blueprint/blob/main/.devcontainer.json)) and its
  `config/configuration.yaml` (`default_config:`, `homeassistant: debug: true`, `logger` with `default: info` and
  debug for the custom component)
  ([configuration.yaml](https://raw.githubusercontent.com/ludeeus/integration_blueprint/main/config/configuration.yaml)).
- **Dev Containers CLI:** npm package `@devcontainers/cli`; `devcontainer up --workspace-folder <path>`,
  `devcontainer exec --workspace-folder <path> <cmd>`. Installing via npm needs Node on the host. A standalone
  install script (bundles Node) exists for Linux/macOS only, so on Windows it would have to run inside WSL
  ([devcontainers/cli](https://github.com/devcontainers/cli)). `up` prints JSON that includes `containerId`,
  which is used for cleanup.

### Decisions
1. **Dockerfile + devcontainer.json in `.devcontainer/`.** Build context is `.devcontainer/` itself, so no
   `.dockerignore` is needed and the host `.venv` never enters the build context.
   Dockerfile:
   - `FROM mcr.microsoft.com/devcontainers/python:3-3.14-trixie`
   - `COPY --from=ghcr.io/astral-sh/uv:<X.Y.Z> /uv /uvx /bin/` (exact version, no `latest`)
   - `apt-get install --no-install-recommends ffmpeg libturbojpeg0 libpcap-dev` (+ clean apt lists). These are
     the runtime libraries HA's `default_config` integrations expect (blueprint precedent).
   - `ENV UV_PROJECT_ENVIRONMENT=/opt/venv UV_LINK_MODE=copy`. They go in the **image** (not only in
     `containerEnv`), so the same values apply to Dev Containers, the CLI and a plain `docker run` fallback.
   - `install -d -o vscode -g vscode /opt/venv /home/vscode/.cache/uv`: the venv dir must be writable by the
     remote user, and pre-creating the cache dir with the right owner means a new named volume mounted there
     inherits that ownership.
2. **Where things live (Windows bind-mount performance).** The repo stays a **bind mount of the Windows
   checkout** (default Dev Containers behaviour), because Claude Code and the Windows git client work on that
   checkout. Bind mounts from a Windows drive are slow for many-small-file trees, so:
   - venv → `/opt/venv` in the container filesystem (`UV_PROJECT_ENVIRONMENT`). It never touches the host's
     Windows `.venv` (same reason as in 001). It is recreated on container rebuild by `postCreateCommand`.
   - uv cache → named volume `energy-cost-stats-uv-cache` at `/home/vscode/.cache/uv`, so rebuilds re-sync
     from the cache instead of the network. `UV_LINK_MODE=copy` because cache and venv are different
     filesystems.
   - `node_modules` → **not handled now** (there is no `frontend/` yet; a volume mount target would create
     `frontend/node_modules` on the host). Stage 4 adds a named volume for `frontend/node_modules`. Record
     this in Follow-ups.
   - Dev HA runtime data (SQLite DB, `.storage/`, logs) → **named volume** (human decision), e.g.
     `energy-cost-stats-ha-config` mounted at a container path, used as `HA_CONFIG_DIR` by default in the
     container. The committed `config/configuration.yaml` stays the single source of the dev config:
     `script/develop` links (symlink) it into the volume's config dir on each start, so edits in the repo take
     effect and nothing runtime lands in the Windows checkout. Without `HA_CONFIG_DIR` set (outside the
     container), `script/develop` keeps using `config/`. The smoke script (decision 6) still uses a temp dir.
   - Document the tip that the fastest option is a checkout inside the WSL2 filesystem or "Clone Repository in
     Container Volume", but that it is not the default here because the host tools work on the Windows checkout.
3. **Line endings and exec bits.** `.gitattributes` already forces LF (`* text=auto eol=lf`), and
   `files.eol: "\n"` is set in the container VS Code settings. Scripts are invoked as `sh script/…` in
   `postCreateCommand` and docs, so they do not depend on the exec bit through the bind mount. New scripts still
   get mode `100755` in the index (main session: `git add --chmod=+x`). Git for Windows sets
   `core.fileMode=false` in `.git/config`, which the container git shares, so the bind mount's permissive modes
   do not show up as changes. The implementer verifies this with `git status` in the container.
4. **Git inside the container.** The bind-mounted repo is owned by a different uid than `vscode`, so git reports
   "dubious ownership". `postStartCommand` adds `safe.directory` for `${containerWorkspaceFolder}`
   **idempotently** (for example, only if `git config --global --get-all safe.directory` does not already
   list it). Only the container's global git config is touched, never the repo's `.git/config`.
5. **`script/develop` changes** (001's file; minimal edits):
   - Config dir from env: `CONFIG_DIR="${HA_CONFIG_DIR:-config}"`, used for `ensure_config` and `--config`.
   - Run `ensure_config` only if `"$CONFIG_DIR/configuration.yaml"` is missing. The current `[ ! -d config ]`
     check is dead once `config/configuration.yaml` is committed.
   - **Make the import path explicit:** put the **repo root** on `PYTHONPATH`
     (`export PYTHONPATH="$(pwd)${PYTHONPATH:+:$PYTHONPATH}"`), so HA's loader imports the repo's
     `custom_components` package (a regular package since 001 decision 7). The current line
     `"${PYTHONPATH:-}:$(pwd)/custom_components"` works only by accident: an empty `PYTHONPATH` gives a leading
     `:`, which Python reads as "current directory". The implementer confirms in the smoke log that HA finds the
     custom integration, and records the mechanism in Implementation notes. If HA also needs
     `<config>/custom_components` to exist or not exist, adapt and document.
   - Keep the Windows guard and `uv run --group ha`.
6. **Headless smoke script `script/smoke-develop`** (POSIX `sh`, container/CI only; 003-ci may reuse it):
   - Fail fast with a clear message if something already listens on :8123.
   - Create a temp dir (`mktemp -d`), copy `config/configuration.yaml` into it, then run
     `HA_CONFIG_DIR=<tmp> sh script/develop` in the background with output to `<tmp>/ha.log`.
   - Poll `http://127.0.0.1:8123/manifest.json` (served by `frontend`) every few seconds until HTTP 200 or
     `SMOKE_TIMEOUT` seconds (default 600; the first run installs frontend packages at runtime).
   - Then assert on the log: a line showing `energy_cost_stats` was set up, and no line matching
     `Setup failed for .*energy_cost_stats`, `Error during setup of component energy_cost_stats` or
     `Unable to (find|prepare|set up) .*energy_cost_stats` (the implementer confirms exact HA wording and records
     it in Implementation notes).
   - Always stop HA on exit (`trap`): TERM, wait, then KILL after a grace period. `uv run` forwards signals to
     its child. Afterwards no `hass` process may remain. Remove the temp dir. On failure print the last ~100 log
     lines. Exit 0 only if every check passed.
   - Errors from unrelated `default_config` integrations (for example bluetooth, go2rtc, usb in a container) do
     **not** fail the smoke. List the ones seen in Implementation notes.
7. **`config/configuration.yaml`** (committed, generic, no secrets/locations):
   ```yaml
   default_config:
   homeassistant:
     debug: true
   logger:
     default: info
     logs:
       custom_components.energy_cost_stats: debug
   energy_cost_stats:
   ```
   `energy_cost_stats:` is required because there is no config flow yet (001: `async_setup` +
   `cv.empty_config_schema`; an empty value raises no warning). Add a one-line comment above it saying it goes
   away when the config flow lands (stage 2). One comment line with a docs URL per block is fine (blueprint
   style). No `name`, `latitude`, `longitude`, `time_zone`, `!secret`, IPs or hostnames: HA defaults/onboarding
   fill those into git-ignored runtime files.
8. **VS Code, minimal.**
   - `devcontainer.json` → `customizations.vscode.extensions`: `ms-python.python`, `ms-python.vscode-pylance`,
     `ms-python.debugpy`, `charliermarsh.ruff`. Settings: `python.defaultInterpreterPath: "/opt/venv/bin/python"`,
     `python.testing.pytestEnabled: true`, `python.testing.unittestEnabled: false`,
     `python.testing.pytestArgs: ["tests"]`, `files.eol: "\n"`,
     `"[python]": {"editor.defaultFormatter": "charliermarsh.ruff", "editor.formatOnSave": true}`.
     Do **not** set `python.analysis.typeCheckingMode`: Pylance reads `[tool.pyright]` from `pyproject.toml`.
   - `.vscode/launch.json` (**included**: cheap, and useful for learning to debug HA): one debugpy config
     "Home Assistant (dev)": `"type": "debugpy"`, `"module": "homeassistant"`,
     `"args": ["--config", "${workspaceFolder}/config", "--debug"]`, `"cwd": "${workspaceFolder}"`,
     `"env": {"PYTHONPATH": "${workspaceFolder}"}`, `"justMyCode": false`. No pytest launch config: the test
     explorer covers that.
   - `.vscode/extensions.json` (host side): recommends `ms-vscode-remote.remote-containers`, so VS Code offers
     the Dev Containers extension on first open. No `.vscode/settings.json` and no `tasks.json`.
   - `.gitignore` already whitelists `.vscode/extensions.json|launch.json|tasks.json` and
     `config/configuration.yaml`. Verify this and do not duplicate it.
   - Keep `devcontainer.json` and `launch.json` **strict JSON (no comments, no trailing commas)** so the unit
     tests can parse them with `json`.
9. **devcontainer.json, other keys:** `"name": "Energy Cost Stats"`, `"build": {"dockerfile": "Dockerfile",
   "context": "."}`, `"remoteUser": "vscode"`, `"features"` (Node, decision above), `"mounts"` (uv cache named
   volume), `"postCreateCommand": "sh script/setup"`, `"postStartCommand"` (decision 4),
   `"forwardPorts": [8123]`, `"portsAttributes": {"8123": {"label": "Home Assistant", "onAutoForward": "notify"}}`.
   No `runArgs`, no `--privileged`, no host network.
10. **Python 3.13 / HA 2025.4 in the container:** not baked into the image. `uv run --python 3.13 …` downloads a
    uv-managed 3.13 when needed. The min-HA matrix is 003-ci's job. The optional check below just shows it works.

## Files
- create: `.devcontainer/Dockerfile` — decision 1.
- create: `.devcontainer/devcontainer.json` — decisions 2, 4, 8, 9 (strict JSON).
- create: `config/configuration.yaml` — decision 7.
- create: `.vscode/launch.json` — decision 8.
- create: `.vscode/extensions.json` — decision 8.
- create: `script/smoke-develop` — decision 6 (`#!/bin/sh`, `set -eu`, cd to repo root, same Windows guard as
  `script/develop`).
- modify: `script/develop` — decision 5.
- create: `tests/unit/test_devcontainer.py` — see tests (level `unit`, following 001's `test_metadata.py`
  precedent: repo metadata checks with no HA and no Docker; they run on Windows natively).
- modify: `CLAUDE.md` — **Environment**: how to enter the devcontainer (VS Code "Reopen in Container";
  headless: Dev Containers CLI), where the venv / uv cache live (one line each), and that `config/` holds the dev
  HA runtime data (git-ignored). **Commands**: the "Run dev HA" row drops "verified in 002" and says
  "devcontainer"; add a row "Smoke-test dev HA | devcontainer / CI | `script/smoke-develop`"; add a row
  "Open / check devcontainer headlessly" with the `npx @devcontainers/cli up|exec --workspace-folder .` form.
  Keep it short.
- modify: `README.md` — Development section: add a "Devcontainer (recommended for full setup)" paragraph of 3 to 6
  lines (prerequisites: Docker Desktop with Linux containers + VS Code Dev Containers; Reopen in Container;
  `script/develop` → http://localhost:8123; a one-line performance note, venv/cache inside the container).

No changes expected to `.gitignore`, `.gitattributes`, `pyproject.toml`, `uv.lock`. If one turns out to be
needed, explain why in Implementation notes.

## Tests to write first
| Level | Test | Asserts |
|---|---|---|
| unit | `tests/unit/test_devcontainer.py::test_devcontainer_json` | `.devcontainer/devcontainer.json` parses with `json.loads` (strict JSON). `build.dockerfile == "Dockerfile"`; `remoteUser == "vscode"`; `8123 in forwardPorts`; `postCreateCommand` contains `script/setup`; there is exactly one feature key starting with `ghcr.io/devcontainers/features/node:` and its `version == "24"`; the extensions list includes `ms-python.python`, `ms-python.vscode-pylance`, `charliermarsh.ruff`; there is no `runArgs` containing `--privileged` or `--network=host`. |
| unit | `tests/unit/test_devcontainer.py::test_dockerfile_matches_python_version` | `.devcontainer/Dockerfile` has a `FROM mcr.microsoft.com/devcontainers/python:` line whose tag contains the `major.minor` from `.python-version` (currently `3.14`) and `trixie`; a `COPY --from=ghcr.io/astral-sh/uv:X.Y.Z` line pinned by regex `\d+\.\d+\.\d+` (no `latest`); it sets `UV_PROJECT_ENVIRONMENT` to an absolute path that is **not** under `/workspaces` and sets `UV_LINK_MODE=copy`. |
| unit | `tests/unit/test_devcontainer.py::test_interpreter_path_matches_venv` | `customizations.vscode.settings["python.defaultInterpreterPath"]` equals `<UV_PROJECT_ENVIRONMENT from Dockerfile>/bin/python`. |
| unit | `tests/unit/test_devcontainer.py::test_dev_ha_configuration` | `config/configuration.yaml` exists; regex (multiline) finds top-level `^default_config:`, `^energy_cost_stats:\s*$` and a line `custom_components.energy_cost_stats: debug`. It contains no `!secret`, no `latitude`/`longitude`, and no IPv4-like string. `.gitignore` contains both `config/*` and `!config/configuration.yaml`. (Text checks only: PyYAML is not in the `dev` group.) |
| unit | `tests/unit/test_devcontainer.py::test_launch_json` | `.vscode/launch.json` parses with `json.loads`; exactly one configuration with `module == "homeassistant"`; its `args` contain `--debug` and a `--config` value starting with `${workspaceFolder}`; `env.PYTHONPATH == "${workspaceFolder}"`. |

The runtime behaviour (`script/develop`, `script/smoke-develop`) is tested by running the smoke script in the
container (acceptance criteria), not by pytest. `script/test` must not start HA.

## Acceptance criteria
Windows native (PowerShell, no Docker):
- [x] `uv run pytest -m unit` → all unit tests pass, including the five new ones.
- [x] `uv run ruff check .` and `uv run ruff format --check .` → exit 0.

Image build:
- [x] `docker build -f .devcontainer/Dockerfile .devcontainer` → succeeds.

Headless devcontainer (from the repo root on the Windows host; Docker Desktop, Linux containers). Record the
`containerId` from `up` and remove the container at the end (`docker rm -f <containerId>`; the uv cache volume
may stay). If Node/npx is not available on the host, stop and report it (see Open questions). Do not substitute
silently.
- [x] `npx --yes @devcontainers/cli up --workspace-folder .` → `"outcome": "success"`; `postCreateCommand`
      (`sh script/setup`) ran without error.
- [x] `… exec --workspace-folder . sh -c 'python --version && uv --version && node --version && npm --version'`
      → Python `3.14.x`, the pinned uv version, Node `v24.x`.
- [x] `… exec --workspace-folder . sh -c 'echo $UV_PROJECT_ENVIRONMENT && test -x /opt/venv/bin/python'` →
      prints `/opt/venv`, exit 0.
- [x] `… exec --workspace-folder . sh script/test` → all tests pass (integration included), coverage gate met.
- [x] `… exec --workspace-folder . sh script/lint` → exit 0.
- [x] `… exec --workspace-folder . uv run --group ha pyright` → 0 errors.
- [x] `… exec --workspace-folder . sh script/smoke-develop` → exit 0. The output shows HTTP 200 on :8123 and the
      `energy_cost_stats` setup line. Afterwards `… exec … sh -c 'pgrep -f "homeassistant|hass " || echo none'`
      prints `none`.
- [x] `… exec --workspace-folder . git status --porcelain` → no entries other than those the implementer
      created on purpose (no mass line-ending or file-mode changes). `git config --global --get-all safe.directory`
      lists the workspace folder exactly once, even after a second `up` (idempotency).
- [x] After all container runs, on the host `uv run pytest -m unit` still passes. The host `.venv` is untouched:
      no `.venv/bin/` directory appears on the host.
- [x] Optional (min HA): `… exec … sh -c 'uv run --python 3.13 --group ha python -c "import homeassistant.const as c; print(c.__version__)"'`
      → `2025.4.0`. If skipped, give the reason in Implementation notes (003-ci covers it). **Skipped** — see notes.

General:
- [x] Temporarily breaking the Dockerfile uv pin to `:latest` makes `test_dockerfile_matches_python_version` fail
      (the reviewer checks this, then reverts).
- [x] `script/develop` no longer contains the `$(pwd)/custom_components` PYTHONPATH form, and it honours
      `HA_CONFIG_DIR`.
- [x] No local absolute paths (`C:\`, `D:\`, `/home/<real user>`, `/Users/`), real entity ids, IPs, hostnames or
      secrets in committed files. (`/home/vscode` and `/opt/venv` are generic container paths and are allowed.)
      Commands in docs use `.` / `<repo>` placeholders.
- [x] CLAUDE.md Environment + Commands and the README Development section are updated as listed in Files. Every
      command they list exists and works as described.
- [ ] Main session, when committing: `git add --chmod=+x script/smoke-develop`. `git ls-files -s script/` shows
      `100755` for all five scripts. (Not the implementer's step — left for the main session at commit time.)

Human (not agent-verifiable, report as "to be checked by the human"):
- [ ] VS Code "Reopen in Container" works; the four extensions are installed; the Testing panel discovers the
      tests; `script/develop` + forwarded port opens HA onboarding at http://localhost:8123 on the host; the
      "Home Assistant (dev)" launch config stops at a breakpoint in `async_setup`.

## Out of scope
- GitHub Actions (matrix, hassfest, HACS validation, reuse of `script/smoke-develop` in CI), Dependabot for the
  uv/image pins, branch protection → **003-ci**.
- `frontend/` scaffold, `node_modules` volume, card tooling → stage 4.
- Engine logic, recorder adapter, config flow, websocket, services.
- Seeding the dev HA with statistics fixtures / golden data → a later task.
- Running HA natively on Windows; supporting Podman, GitHub Codespaces or non-VS Code editors explicitly.

## Open questions
None — resolved by the human:
1. Node on the host: Node 20 + npx are installed; use `npx @devcontainers/cli` for the headless check.
2. `default_config:` — confirmed.
3. Dev HA runtime data — **named volume**, not the bind mount (see decision 2).

<!-- Filled in by implementer -->
## Implementation notes
- **uv pin.** `0.12.18` was both the version already installed on this Windows host and the latest GitHub
  release at implementation time (checked via the GitHub releases API), so it is pinned as-is in the
  Dockerfile `COPY --from=ghcr.io/astral-sh/uv:0.12.18 …` line.
- **`HA_CONFIG_DIR` / named volume wiring.** `devcontainer.json` mounts a second named volume
  (`energy-cost-stats-ha-config`) at `/home/vscode/.ha-config` and sets `containerEnv.HA_CONFIG_DIR` to that
  path, so `script/develop` uses it by default inside the container. `script/develop` symlinks the committed
  `config/configuration.yaml` into `$HA_CONFIG_DIR/configuration.yaml` on every start whenever
  `HA_CONFIG_DIR` differs from the default `config` (native/no-volume case keeps using the repo's `config/`
  directly, no symlink). `ensure_config` still runs first if `$CONFIG_DIR/configuration.yaml` is missing, to
  generate the other default runtime files (`.storage/`, etc.) the first time the volume is used.
- **`script/develop`: `exec` fix (real bug found during verification).** The first `script/smoke-develop` run
  in the container passed the port/`energy_cost_stats` checks logic-wise but left an orphaned `hass` process
  behind after the script exited with a (transient, see next note) failure: `script/develop`'s final line was
  a plain `uv run --group ha hass …` (not `exec`), so the backgrounded `sh script/develop` process in
  `smoke-develop` was a separate process from `uv`/`hass`; sending it `TERM` did not reach the actual `hass`
  process (POSIX shells do not forward signals to a foreground child by default). Fixed by changing the final
  line to `exec uv run --group ha hass --config "$CONFIG_DIR" --debug`, which replaces the shell's process
  image, so `uv run`'s own signal forwarding (documented behaviour) now receives the `TERM`/`KILL` from
  `script/smoke-develop`'s trap directly. Verified: after the fix, `pgrep`/`ps aux` for `hass` in the container
  shows nothing left running once `script/smoke-develop` exits. Had to manually clean up the orphaned process
  from the first (pre-fix) run with `kill -TERM/-KILL <pid>` before re-testing.
- **`script/smoke-develop`: polling fix.** The exact HA log wording for a successful custom-integration setup
  is `Setting up energy_cost_stats` (there was no separate `Setup of domain energy_cost_stats` line observed,
  but the check accepts either). The first smoke run failed because the script checked the log for that line
  only once, immediately after the HTTP 200 check passed — but `http`/`frontend` come up in an early bootstrap
  stage, while `energy_cost_stats` (depends on `recorder`) is set up later. Fixed by polling for *both*
  conditions (port ready and the integration-setup log line) in the same loop until both are true or
  `SMOKE_TIMEOUT` is reached, instead of a one-shot check after the port opens.
- **Error log wording confirmed:** no `Setup failed for .*energy_cost_stats`, `Error during setup of component
  energy_cost_stats` or `Unable to (find|prepare|set up) .*energy_cost_stats` line appeared in any run; the
  patterns are kept defensively as specified.
- **Unrelated `default_config` warnings/errors seen in the smoke and `script/develop` logs** (none of these
  fail the smoke check, per decision 6): `aiohttp_fast_zlib` "zlib_ng and isal are not available, falling back
  to zlib", occasional `asyncio` "Executing … took N seconds" warnings from slow setup steps, and (in the
  round-1-review re-verification run) `Setup failed for 'go2rtc': Integration failed to initialize` /
  `Unable to set up dependencies of 'default_config'` — go2rtc needs a media/network feature this container
  image does not provide. `script/smoke-develop`'s error-pattern check is scoped to `energy_cost_stats`
  specifically, so this does not fail the check; `energy_cost_stats` itself set up cleanly in the same run.

### Review round 1 fixes (CHANGES_REQUESTED → addressed)
- **Required 1 — root-owned named volume.** `energy-cost-stats-ha-config`'s mount point
  (`/home/vscode/.ha-config`) was not pre-created in the Dockerfile, so Docker created it as `root:root 755`
  on first mount; `script/develop` (running as `vscode`) then failed to write `configuration.yaml`/symlink
  into it with the default `HA_CONFIG_DIR`. Fixed by adding `/home/vscode/.ha-config` to the
  `install -d -o vscode -g vscode …` line (same fix pattern as the pre-existing uv cache mount). Added
  `tests/unit/test_devcontainer.py::test_dockerfile_creates_writable_mount_points` first (asserts every
  `mounts[].target` in `devcontainer.json`, including `containerEnv.HA_CONFIG_DIR`, is pre-created on that
  Dockerfile line); confirmed it failed before the fix and passed after. Re-verified end to end: removed the
  stale root-owned volume (`docker volume rm energy-cost-stats-ha-config`), rebuilt the image, brought the
  devcontainer up fresh, confirmed `/home/vscode/.ha-config` is now `vscode:vscode`, ran `sh script/develop`
  with the container's default `HA_CONFIG_DIR` (no override), polled `:8123` until HTTP 200, confirmed
  `Setting up energy_cost_stats` in the log with no `energy_cost_stats`-specific errors, confirmed
  `config/configuration.yaml` was symlinked into the volume correctly, then stopped it (`TERM`, then `KILL`
  after a grace period) and confirmed no `hass` process remained.
- **Required 2 — task file named another local project.** Removed the sentence in the "Cleanup performed" note
  that named an unrelated container/image from a different local repository; replaced with a generic
  statement (see that note above).
- **Required 3 — `.vscode/launch.json` used the Windows-checkout `config/` dir.** Per the human's named-volume
  decision (also applying to the debugger, not just `script/develop`), changed the `--config` argument from
  `${workspaceFolder}/config` to `${env:HA_CONFIG_DIR}`, so an interactive VS Code debug session uses the same
  named-volume config dir and runtime data as `script/develop`, keeping the Windows checkout free of runtime
  data as intended. Tightened `test_launch_json` accordingly (asserts the exact value that follows
  `--config`, not just any arg starting with `${workspaceFolder}`, per review suggestion 5). Since this
  launch config only runs inside the devcontainer (HA does not run natively on Windows), `HA_CONFIG_DIR` is
  always set there via `containerEnv`; the launch config assumes the config dir has already been initialized
  by at least one prior `script/develop` run, consistent with the human-facing verification step in the
  Acceptance criteria (breakpoint in `async_setup`).
- **Optional min-HA (Python 3.13) check — skipped, reason recorded.** Running
  `uv run --python 3.13 --group ha python -c "import homeassistant.const as c; print(c.__version__)"` inside
  the *devcontainer* (as opposed to 001's disposable one-off `docker run` containers) failed with
  `error: failed to remove directory /opt/venv: Permission denied`, because this devcontainer has a single
  shared `UV_PROJECT_ENVIRONMENT=/opt/venv` and switching `--python` tries to recreate that same directory,
  which the running container's file ownership does not allow from inside `uv run`. This is a property of
  reusing one long-lived devcontainer for both Python versions, not a regression: 003-ci's job is to build a
  fresh 3.13 environment for the min-HA matrix leg (as the task already scopes it), so this is left to that
  task rather than reworking the devcontainer's venv strategy here.
- **`devcontainer up` warning (benign).** The very first `up` printed
  `Error fetching image details: No manifest found for mcr.microsoft.com/devcontainers/python:3-3.14-trixie.`
  before proceeding to build and start the container successfully (`"outcome":"success"`); this looks like the
  CLI's optional pre-fetch of base-image metadata for feature merging, not a fatal error — the build and every
  subsequent check passed. Not investigated further since it did not block anything on the acceptance list.
- **Idempotency of `postStartCommand`.** Verified by running `npx @devcontainers/cli up` twice (the CLI reused
  the existing container both times, same `containerId`); `git config --global --get-all safe.directory`
  printed the workspace folder exactly once after both runs.
- **Cleanup performed.** The devcontainer's container (`docker rm -f <containerId>`) was removed after
  verification. The two named volumes (`energy-cost-stats-uv-cache`, `energy-cost-stats-ha-config`) were left
  in place per the task's instructions. An unrelated, already-stopped container from a different local project
  was present on this Docker Desktop instance before this task started and was not touched.
- **Host isolation reconfirmed** after all container runs: `uv run pytest -m unit` still passes natively, no
  `.venv/bin/` appeared on the host, and `git status --porcelain` on the host shows only the files this task
  intentionally created or modified.

### Human report — HA ends in recovery mode (investigated, root cause NOT confirmed)
A human running "Reopen in Container" reported that `script/develop` starts, `energy_cost_stats` sets up, but
HA later ends up in **recovery mode**: `ModuleNotFoundError` for `turbojpeg`/`camera`, `rf_protocols`,
`infrared_protocols`, `av`/`stream`, then `default_config` fails its dependents, then
`Detected that frontend did not load. Activating recovery mode`.

**Given hypothesis (HA installs runtime requirements via `python -m uv`, and `uv` isn't installed as a Python
package in `/opt/venv`) — checked and REFUTED**, with direct evidence:
- `uv.lock` lists `uv` as a dependency of the `homeassistant` package itself (not just of PHCC/dev tooling),
  for **both** matrix legs: `uv==0.6.10` under the `python_full_version < '3.14'` resolution (→ HA 2025.4.0)
  and `uv==0.12.5` under `python_full_version >= '3.14.2'` (→ latest HA). So `uv` is always present in the
  `ha` group regardless of which HA version is locked; nothing to add there.
- Inside a real devcontainer, `/opt/venv/bin/python -m uv --version` works, and `homeassistant/util/package.py`
  (`install_package()`) does call `sys.executable -m uv pip install ...` exactly as suspected — but the calls
  themselves succeed. Manually running the exact same command HA uses
  (`python -m uv pip install rf-protocols==4.3.0 --index-strategy unsafe-first-match --upgrade --target <dir>`)
  installed the package correctly on the first try.

**Reproduction attempts — all failed to reproduce recovery mode**, i.e. the failure could not be forced on this
machine:
1. Fresh `energy-cost-stats-ha-config` volume only (uv cache still warm from earlier verification) →
   `script/develop` completed normally, only the expected/documented `go2rtc` error (no Docker socket for its
   bundled binary; unrelated to this bug, already covered by decision 6).
2. Fully fresh devcontainer: removed **both** named volumes (`energy-cost-stats-uv-cache` **and**
   `energy-cost-stats-ha-config`), rebuilt/recreated the container from scratch, ran `script/develop` with a
   cold uv cache (so every runtime requirement, including `av`, `PyTurboJPEG`, `ha-ffmpeg`, `habluetooth`, …,
   had to be downloaded fresh) → completed normally in ~88s, `Home Assistant initialized in 87.86s`, no
   recovery mode, only the same `go2rtc` error.
3. `ecs-constrained-test`: a throwaway plain `docker run` (not the devcontainer, so as not to touch
   `devcontainer.json`) from the same built image, deliberately resource-constrained to `--memory=1.2g
   --cpus=1` (this repo's normal devcontainer has no such limits; this was to test whether the human's
   failure could be a resource-contention effect of Home Assistant's highly parallel first-boot requirement
   install burst — many `SyncWorker` threads each shelling out to `python -m uv pip install <pkg>`
   concurrently against the live venv). Fresh volumes again. `script/setup` and `script/develop` both
   completed normally under this constraint too (`Home Assistant initialized in 114.80s`, peak ~67% of the
   1.2 GiB memory limit, 0 CPU% at the sampling point — never throttled hard enough to fail). Removed after
   the test; not part of the repo's normal setup.

**Conclusion: root cause not identified/reproduced.** The specific packages the human's log named
(`turbojpeg`/`PyTurboJPEG`, `av`) are genuinely part of `default_config`'s dependency chain (`stream`'s
manifest requires `PyTurboJPEG==1.8.3`, `av==17.0.1`, `numpy==2.3.2`); `rf_protocols`/`infrared_protocols`
belong to `radio_frequency`, which is **not** a `default_config` dependency and would only be pulled in by an
auto-discovered device (SSDP/DHCP/zeroconf) — something a devcontainer bridged to a real home LAN could
plausibly discover that this task's verification environment does not. Given repeated clean reproductions
(including under artificial resource pressure) and this discovery-triggered detail, the most likely
explanation is environment-specific (the human's LAN, network reliability to PyPI, or an interrupted earlier
run corrupting a partially-installed package in the persistent `/opt/venv`), not a deterministic bug fixable
by pinning a dependency in `pyproject.toml`/`uv.lock`/the Dockerfile — no such change was made, and
`pyproject.toml`, `uv.lock` and `.devcontainer/Dockerfile` are untouched by this round (`uv lock --check`
still passes).

> **Correction (follow-up round, see below):** the `rf_protocols`/`infrared_protocols` "discovery-triggered"
> guess above is wrong. Reading `homeassistant/bootstrap.py` shows `radio_frequency`/`infrared` are
> `BASE_PLATFORMS` (`homeassistant.const.Platform` members), which HA resolves and installs requirements for
> on **every** startup, unconditionally — not only when a real device is discovered. Reproduced deterministically
> in this task's own (non-LAN-bridged) container once the pre-install helper's root domains were widened to
> include `BASE_PLATFORMS`. This does not change the "root cause not identified" conclusion for the original
> report (a concurrent `uv sync` racing a live HA install remains the best-supported explanation, now with the
> `uv run` implicit-sync revert documented below as a second, related mechanism), but the LAN-discovery
> explanation specifically should not be relied on.

**Fix actually shipped this round: `script/smoke-develop` had a real, confirmed, independent bug that let
exactly this failure mode go undetected.** The script declared success as soon as (a) HTTP 200 answered on
:8123 and (b) `energy_cost_stats` appeared as "set up" in the log — both of which happen during the **first**
bootstrap attempt, well before Home Assistant's own recovery-mode decision (logged only once, at the very end
of `async_setup_hass`, as `Home Assistant initialized in ...s`, alongside
`Detected that <domain> did not load. Activating recovery mode` when a `CRITICAL_INTEGRATIONS` domain like
`frontend` failed). So the previous script could report `OK` for a run that later fell back to recovery mode.
Confirmed with a synthetic log fixture reproducing the human's exact signature (early
`Setting up energy_cost_stats` + port 200, later `Activating recovery mode`): the old check logic reported
`OK` against it; the fixed logic (poll for `Activating recovery mode` on every iteration, only declare success
after `Home Assistant initialized in ...s` appears, then re-check for recovery mode once more) correctly
fails against the same fixture, and still passes on two real, healthy `script/smoke-develop` runs in the
devcontainer (`OK: HTTP 200 on :8123; log line: ... Setting up energy_cost_stats`). This is the actionable,
verified fix for this round; it also now prints the matched HTTP code / log line (review round 1 suggestion 1
is resolved as a side effect).

### Follow-up round — `script/setup` pre-installs Home Assistant's runtime requirements
Goal: after `script/setup`, a dev HA with `default_config:` starts without any live
`python -m uv pip install` (the mechanism behind the recovery-mode report above, when it races a concurrent
`uv sync`).

- **New file `script/prefetch_ha_requirements.py`** (stdlib only, no `homeassistant` import at module level so
  its manifest-walking logic is unit-tested without Home Assistant installed; `main()` needs the `ha` group).
  Confirmed against `homeassistant/requirements.py` (`RequirementsManager._async_process_integration`) that HA
  gathers requirements by walking both `dependencies` **and** `after_dependencies`, so the helper does the
  same. Roots walked: `default_config`, `frontend` (not a `default_config` dependency, but the dev UI, and
  per this follow-up's brief "must not be optional"), our own `custom_components/energy_cost_stats/manifest.json`
  (currently just `recorder`), **and every domain in `homeassistant.const.BASE_PLATFORMS`** (see next point —
  this last group was missing in the first pass and caused two runtime installs to slip through verification).
  Requirements already satisfied (checked via `importlib.metadata.version` + `packaging.requirements.Requirement`,
  mirroring HA's own `is_installed()`) are skipped, so repeat `script/setup` runs are fast and don't hit the
  network. Installs one requirement at a time (mirroring the exact `uv pip install ... --index-strategy
  unsafe-first-match --constraint <package_constraints.txt>` flags `homeassistant.util.package.install_package()`
  uses) so one package without a wheel for the platform doesn't block the rest; a failure of a `frontend`-manifest
  requirement (`home-assistant-frontend`) aborts `script/setup` with a non-zero exit (decided "fail", since
  `script/develop` would otherwise still trigger a live install for it and the brief says frontend must not be
  optional); any other failure only warns and continues.
- **Discovery during verification: `homeassistant.const.BASE_PLATFORMS` domains are *not* discovery-triggered,
  they are always processed.** The first version of the helper only walked `default_config`'s manifest tree and
  missed two runtime installs that still happened on a clean `script/develop` run:
  `Attempting install of rf-protocols==4.3.0` / `infrared-protocols==9.0.0` (domains `radio_frequency` /
  `infrared`, `"integration_type": "entity"`). Reading `homeassistant/bootstrap.py`
  (`_async_resolve_domains_and_preload`) showed why: HA "also processes all base platforms since we do not
  require the manifest to list them as dependencies" — `BASE_PLATFORMS` is `{platform.value for platform in
  Platform}` (`homeassistant/const.py`), a fixed, version-following list of every entity-platform domain
  (`sensor`, `switch`, `camera`, `radio_frequency`, `infrared`, ...), and HA resolves/installs requirements for
  **all** of them unconditionally, independent of `default_config:` or any device discovery. This corrects the
  original "Human report" investigation's guess (further down in these notes) that `rf_protocols`/
  `infrared_protocols` were discovery-triggered by a real device on the human's LAN — they are not; every dev
  instance loads them regardless. Fixed by importing `BASE_PLATFORMS` from `homeassistant.const` in `main()`
  and adding it to the walked roots; re-verified end to end afterwards (0 "Attempting install of" lines).
- **`uv run`'s implicit sync fights this pre-install for packages pinned differently by the `ha` group itself.**
  A second, independent bug found during verification: `bleak-retry-connector` and `habluetooth` are HA runtime
  requirements (pinned `==4.7.0` / `==6.26.11` in `package_constraints.txt`) **and** transitive dependencies of
  `pytest-homeassistant-custom-component` in the `ha` dev group, pinned there to different versions
  (`4.7.1` / `7.1.2` in this `uv.lock`). `uv run` performs an implicit project sync before running its command
  unless told not to; that sync reverts the venv to the lock's versions, i.e. it silently undid this script's
  install of the HA-pinned versions right before `script/develop`'s `uv run --group ha hass ...` executed,
  so HA saw a version mismatch and reinstalled them itself at startup (`Attempting install of ...`) — this
  reproduces even in a container with no LAN and no discoverable devices, so it is a very plausible additional
  contributor to the original human recovery-mode report, on top of the confirmed-refuted and
  still-unconfirmed causes already recorded below. Fixed by adding `--no-sync` to both `uv run` invocations that
  must preserve this script's install (`script/setup`'s call to `prefetch_ha_requirements.py`, and
  `script/develop`'s final `exec uv run --group ha hass ...`); both are safe to skip syncing because
  `script/setup`'s own `uv sync --group ha "$@"` right before them already put the venv in the exact state the
  lock wants. `script/test`/`script/lint`/`pyright` still use a syncing `uv run` (unchanged, out of scope) and
  will revert this pre-install for any such overlapping package; if that happens, re-run `script/setup` before
  `script/develop` (documented as a Follow-up below, not fixed this round).
- **`--python` forwarding.** `script/setup "$@"` already forwarded extra args (e.g. `--python 3.13` for the
  min-HA leg, per `tasks/001-scaffold.md`'s precedent) to `uv sync`, but not to the new `uv run --no-sync`
  call. Without it, `uv run` defaulted to `.python-version` (`3.14`) while `--no-sync` kept the actual (3.13)
  venv, which worked but printed a `uv` warning ("Using incompatible environment ... due to --no-sync").
  Fixed by forwarding `"$@"` to that `uv run` call too (`uv run --no-sync --group ha "$@" python
  script/prefetch_ha_requirements.py`); re-verified the 3.13 leg prints no such warning afterwards.
- **Verification performed** (fresh `energy-cost-stats-ha-config` **and** `energy-cost-stats-uv-cache` volumes,
  rebuilt image, `npx @devcontainers/cli up`):
  - `script/setup` → pre-install step reports 25 requirements the first time, 0 the second (idempotent), no
    failures.
  - `script/develop` (fresh `HA_CONFIG_DIR`) → log has **zero** `Attempting install of` lines, one
    `Setting up frontend` line, `Setting up energy_cost_stats`, `Home Assistant initialized in ...s`, zero
    `recovery mode` lines.
    > **Correction (review round 3):** this "zero installs" result only held because `HA_CONFIG_DIR` already
    > had a `configuration.yaml` from an earlier run in the same volume, so `script/develop`'s `ensure_config`
    > branch (`[ ! -f "$CONFIG_DIR/configuration.yaml" ]`) was skipped. On a genuinely fresh (empty)
    > `HA_CONFIG_DIR` — the default devcontainer path on first use — that branch's `uv run --group ha hass
    > --script ensure_config …` call did not have `--no-sync`, so its implicit sync reverted the pre-installed
    > `bleak-retry-connector`/`habluetooth` versions before HA even started, producing exactly the live
    > `Attempting install of` lines this pre-install step exists to avoid (see review round 3, Required 1).
    > Fixed by adding `--no-sync` to that `uv run` call too; re-verified below with a truly empty
    > `HA_CONFIG_DIR`.
  - `script/smoke-develop` → `OK`, no leftover `hass` process afterwards (`pgrep -af hass` empty).
  - `script/test` → 32 tests pass (11 new unit tests for the helper), coverage gate met.
  - `script/lint`, `uv run --group ha pyright` → both clean.
  - 3.13 leg: `sh script/setup --python 3.13` in a one-off `ghcr.io/astral-sh/uv:python3.13-trixie` container
    (same recipe as `tasks/001-scaffold.md`'s "Docker verification") → resolves `pytest-homeassistant-custom-component==0.13.232`
    → `homeassistant==2025.4.0`, 18 requirements pre-installed, no warning, no failure.
  - Host: `uv run pytest -m unit` (31 passed), `uv run ruff check .` / `ruff format --check .` (clean),
    `uv lock --check` (unchanged, still resolves) — confirming `pyproject.toml`/`uv.lock` were not touched.
  - `git status --porcelain` inside the container showed only this round's intended files (one stray directory
    from an early manual-testing misstep with a Windows-mangled path was found and removed before the final
    check).
  - Cleanup: the devcontainer's container was removed (`docker rm -f`); both named volumes were left in place,
    as in the original task's cleanup convention.

### Review round 3 fixes (CHANGES_REQUESTED → addressed)
- **Required 1 — `script/develop`'s `ensure_config` `uv run` lacked `--no-sync`.** On a genuinely fresh
  `HA_CONFIG_DIR` (no `configuration.yaml` yet — the default devcontainer path on first use), `script/develop`
  ran `uv run --group ha hass --script ensure_config -c "$CONFIG_DIR"` *before* the final `exec uv run --no-sync
  …` line. That call still performed an implicit (syncing) `uv run`, which reverted `script/setup`'s
  pre-installed `bleak-retry-connector`/`habluetooth` versions back to the `ha` group's own pins, so HA then
  installed them live at startup — reintroducing exactly the failure mode this whole follow-up round exists to
  remove, and (per the round-2 note) rebuilding the venv entirely under `--python 3.13`. Fixed by adding
  `--no-sync` to that `uv run` call too.
- **Required 2 — no test would fail if this round's key behaviours were removed.** Added
  `test_uv_run_invocations_carry_no_sync` (`tests/unit/test_prefetch_ha_requirements.py`), which reads
  `script/setup` and `script/develop` as text and asserts every non-comment line containing `uv run` also
  contains `--no-sync`; confirmed it fails against the pre-fix `script/develop` and passes after. Also extracted
  the critical/best-effort classification out of `main()` into a new pure function
  `summarize_failures(failures, critical_requirements) -> int` in `script/prefetch_ha_requirements.py`, and added
  four unit tests for it (`test_summarize_failures_no_failures_returns_zero`,
  `..._critical_failure_aborts`, `..._best_effort_failure_continues`, plus two "fake installer" tests that go
  through `install_requirements` with a monkeypatched `subprocess.run`, no network, host-runnable, confirming
  the end-to-end classification with a frontend-critical failure vs. a non-critical one). Confirmed all five
  fail with `AttributeError` before `summarize_failures` existed.
- **Required — task file verification note corrected.** The "Follow-up round" section's "Verification performed"
  note claimed `script/develop` (fresh `HA_CONFIG_DIR`) produced zero `Attempting install of` lines; that result
  only held because the config volume already had a `configuration.yaml` from an earlier run, skipping the
  `ensure_config` branch entirely. Added an inline correction there (see above) and re-verified below with a
  truly empty `HA_CONFIG_DIR`.
- **Re-verification performed this round** (`docker volume rm energy-cost-stats-ha-config`, fresh
  `npx @devcontainers/cli up`, `energy-cost-stats-uv-cache` volume kept warm):
  - `script/setup` → pre-install step reported 25 requirements, no failures.
  - Confirmed `$HA_CONFIG_DIR` (`/home/vscode/.ha-config`) was empty (no `configuration.yaml`) before starting
    `script/develop`.
  - `script/develop` on that empty config dir → log has **zero** `Attempting install of` lines, **zero**
    `Uninstalled`/`Installed N packages` lines, `Setting up frontend`, `Setting up energy_cost_stats`,
    `Home Assistant initialized in 5.73s`, no recovery-mode line. Stopped with `TERM`; confirmed no `hass`
    process remained afterwards.
  - `script/smoke-develop` → `OK: HTTP 200 on :8123; log line: ... Setting up energy_cost_stats`; confirmed no
    `hass` process remained afterwards.
  - Host (before/after the container run): `uv run pytest -m unit` → 37 passed (5 new tests this round);
    `uv run ruff check .` / `ruff format --check .` → clean; `uv lock --check` → resolves unchanged.
  - Other long suites (`script/test`, `script/lint`, pyright in-container, the 3.13/min-HA leg) were not
    re-run this round per the review's scope (only Required 1/2 touch code that affects them, and both were
    already green in round 3's own checks); left to a future full pass if needed.
  - Cleanup: the devcontainer's container was removed (`docker rm -f`); both named volumes were left in place,
    consistent with earlier rounds' convention.

## Follow-ups
- Running `script/test` / `script/lint` / `uv run --group ha pyright` (all use a syncing `uv run`) between
  `script/setup` and `script/develop` can revert the small subset of pre-installed requirements that are also
  transitive dependencies of the `ha` group itself, pinned to a different version there (currently
  `bleak-retry-connector`, `habluetooth`). If `script/develop` then shows an `Attempting install of` line for
  one of those, re-run `script/setup` first. Not fixed this round (would need a broader decision on whether
  `script/test`/`lint`/`pyright` should also use `--no-sync`, which is out of this follow-up's scope).
- Stage 4: named volume for `frontend/node_modules` in `devcontainer.json`.
- 003-ci: the min-HA (Python 3.13) matrix leg needs its own environment (fresh container or
  `UV_PROJECT_ENVIRONMENT` override), since the devcontainer's shared `/opt/venv` cannot be recreated for a
  different Python version from inside a running container (see Implementation notes).
- Review round 1 suggestions not applied in this round (not required, left for a follow-up pass or the
  human's judgment): (2) `trap cleanup EXIT INT TERM` can double-run cleanup on INT/TERM — prefer
  `trap cleanup EXIT` + dedicated `INT`/`TERM` traps that just `exit`; (3) the `KILL` grace-period fallback
  signals `uv`, not `hass`, directly — consider `setsid`/process-group signalling for extra robustness; (6)
  whether to commit the CLI-generated `.devcontainer/devcontainer-lock.json` (currently untracked) is an open
  decision; (7) the CLAUDE.md `config/` bullet could be shortened to one sentence per the review's suggested
  wording.
- **Human recovery-mode report: root cause unconfirmed** (see the "Human report" note above). If it recurs,
  the strengthened `script/smoke-develop` will now catch it and print the full log; worth asking the human
  next time whether real devices on their LAN were discovered (check the log for `radio_frequency` /
  `rf_protocols` around the failure) and whether the devcontainer had been interrupted/force-closed during an
  earlier first boot (which could leave a partially-installed package in the persistent `/opt/venv`, since
  it lives in the container's writable layer and survives across `script/develop` runs within the same
  container). A clean fix for that specific scenario, if confirmed, would be `rm -rf /opt/venv` + re-run
  `script/setup` (rebuilding the venv from the lock) rather than a code change.
