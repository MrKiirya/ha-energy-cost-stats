# 001 — Project scaffold (uv, scripts, integration skeleton, smoke tests)

Status: in-review
Roadmap: SPEC §8 stage 0 (project setup), task 1 of 3 (001-scaffold, 002-devcontainer, 003-ci)
Spec sections: SPEC §2 (architecture / layout), §6 (HA compatibility), §8 (roadmap); CLAUDE.md (principles, commands, test levels)

## Goal
After this task a developer can clone the repo and get a working uv-managed environment in one of two
setups:
- **Windows native:** `uv sync` → cross-platform tooling only (pytest, ruff, pyright, …), no Home Assistant.
  Engine unit tests and lint run here.
- **Linux container / CI:** `script/setup` (= `uv sync --group ha`) → everything, including the Home
  Assistant test harness. Integration tests, pyright and the dev HA instance run here.

The integration `custom_components/energy_cost_stats/` exists as a loadable skeleton (manifest,
`const.DOMAIN`, a minimal `async_setup`, an empty pure-Python `engine/` package), HACS metadata is present,
and smoke tests at the `unit` and `integration` levels prove the tooling works. The CLAUDE.md Commands table
becomes real instead of "planned".

## Context

### Versions and compatibility (checked 2026-09-24)
- `pytest-homeassistant-custom-component` (PHCC) pins **one exact `homeassistant` version per release**
  and is released daily. Latest checked: `0.13.366` → `homeassistant==2026.9.3`, `requires_python >=3.14`
  ([PyPI JSON](https://pypi.org/pypi/pytest-homeassistant-custom-component/json)).
- The release matching our minimum HA is **`0.13.232` → `homeassistant==2025.4.0`, `requires_python >=3.13`**
  (`0.13.230`/`.231` pin 2025.4 betas)
  ([0.13.232 JSON](https://pypi.org/pypi/pytest-homeassistant-custom-component/0.13.232/json)).
- So latest HA needs Python 3.14 and min HA 2025.4 runs on Python 3.13. The Python version and the HA version
  move together. `python_version` markers on the two PHCC pins encode this pairing, so 003-ci picks the HA
  version by picking the Python version (`--python 3.13` → HA 2025.4.0, `--python 3.14` → latest).
  uv resolves marker-split requirements into one universal `uv.lock` ("forked resolution").
- PHCC pins exact versions of `pytest`, `pytest-asyncio`, `pytest-cov`, `syrupy`, `coverage` etc.
  (latest pins e.g. `pytest==9.0.3`, `pytest-cov==7.1.0`, `syrupy==6.0.0`, `pytest-asyncio==1.4.0`).
  The `dev` group lives in the same lock, so its entries must be **unpinned, or have loose lower bounds
  that both the 0.13.232 and the latest PHCC pins satisfy**. Otherwise the lock fails.
- PHCC README ([GitHub](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component)):
  requires `asyncio_mode = "auto"`, the `enable_custom_integrations` fixture, and a
  `custom_components/__init__.py` (or a sys.path tweak). `recorder_mock` must be requested **before**
  `enable_custom_integrations`.
- **Windows:** PHCC registers itself as a pytest plugin (entry point) and imports `homeassistant.runner`,
  which imports the POSIX-only `fcntl`. Just *installing* PHCC on Windows breaks collection of every test
  (see e.g. [denara/ha-roller-shutter-suite#5](https://github.com/denara/ha-roller-shutter-suite/pull/5)).
  That is why HA lives in a separate, opt-in dependency group.
- pytest config: use `[tool.pytest.ini_options]`, which works with the pytest 8 pinned by the 2025.4 fork
  and with pytest 9. Do not use pytest 9's native `[tool.pytest]` table.
- uv Docker images: the uv docs list Debian **trixie** based tags such as `ghcr.io/astral-sh/uv:python3.14-trixie`
  and `ghcr.io/astral-sh/uv:python3.13-trixie`, plus `-trixie-slim` and `-alpine`
  ([uv — Docker guide](https://docs.astral.sh/uv/guides/integration/docker/)).
  The `-bookworm` tag from the original request is not listed there, so this task uses `-trixie`.

### Home Assistant manifest / HACS (checked 2026-09-24)
- Custom integration manifest: `version` is required (AwesomeVersion-compatible). Valid `integration_type` /
  `iot_class` values are listed in
  [HA dev docs — manifest](https://developers.home-assistant.io/docs/creating_integration_manifest/).
- HACS requirements for an integration repo: exactly one subdirectory under `custom_components/`; manifest keys
  `domain`, `documentation`, `issue_tracker`, `codeowners`, `name`, `version`; README and `hacs.json` at repo
  root; brand assets (`brand/icon.png`) to publish
  ([HACS — integration](https://www.hacs.xyz/docs/publish/integration/)).
- `hacs.json`: `name` required; optional `homeassistant` (minimum HA version)
  ([HACS — general](https://www.hacs.xyz/docs/publish/start/)).
- `script/develop` follows the pattern of
  [ludeeus/integration_blueprint `scripts/develop`](https://github.com/ludeeus/integration_blueprint/blob/main/scripts/develop).

### Decisions (human-confirmed where marked)
1. **uv project, not a package.** `pyproject.toml` has `[project]` (name `energy-cost-stats`,
   `version = "0.1.0"`, `requires-python = ">=3.13"`, `dependencies = []`) and `[tool.uv] package = false`.
   `.python-version` = `3.14`. `uv.lock` is committed.
2. **Two dependency groups** (PEP 735 `[dependency-groups]`) *(human-confirmed)*:
   - `dev` (a default group, so plain `uv sync` installs it): cross-platform tooling only: `pytest`,
     `pytest-asyncio`, `pytest-cov`, `syrupy`, `ruff`, `pyright[nodejs]` (the `nodejs` extra bundles Node
     for pyright). No platform markers.
   - `ha` (opt-in, never a default group):
     - `pytest-homeassistant-custom-component==0.13.232 ; python_version < '3.14'`
     - `pytest-homeassistant-custom-component>=0.13.366 ; python_version >= '3.14'`
     - `homeassistant` comes in transitively through PHCC. Do not list it.
   - Windows native: `uv sync` → no HA. Container / CI: `uv sync --group ha`.
   - `--strict-config` must stay valid in **both** setups. `asyncio_mode` and
     `asyncio_default_fixture_loop_scope` are pytest-asyncio options, and pytest-asyncio is in `dev`, so both
     setups know them. Verify that no option is set that only PHCC's plugins define.
   - **Keeping the `ha` group installed:** a later `uv sync` without `--group ha` removes it (exact sync).
     So every Linux script and documented container command that needs HA uses
     `uv run --group ha …` (for example `script/test` and the pyright command). The implementer checks
     this behaviour and records it in Implementation notes.
3. **Engine imported as top-level `engine` in unit tests** *(human-confirmed)*:
   - pytest `pythonpath = [".", "custom_components/energy_cost_stats"]`, so `import engine` works without
     running the integration `__init__.py` (which imports `homeassistant`). No `sys.modules` stubs.
   - pyright: `extraPaths = ["custom_components/energy_cost_stats"]` so `import engine` resolves in tests.
   - ruff isort: `known-first-party = ["custom_components", "engine"]`.
   - Code inside `engine/` uses **relative imports only** (`from .x import y`). No absolute `engine…` imports,
     no `custom_components…` imports, no `from ..` that leaves `engine/`.
   - **Known caveat (document in `engine/__init__.py` docstring and CLAUDE.md test-level notes):** the same
     files can be imported under two names: `engine.*` (unit tests) and
     `custom_components.energy_cost_stats.engine.*` (integration runtime). Those are two distinct module
     objects, so classes differ, `isinstance` checks and module-level state do not cross over, and
     monkeypatching one name does not affect the other. Rule: **unit tests import only `engine…` and never
     `custom_components.energy_cost_stats…`.** Integration tests go through the integration package.
     The guard test enforces the unit-test side.
   - Coverage uses a file path (`--cov=custom_components/energy_cost_stats/engine`), so it counts the files
     whichever name imports them.
4. **Integration tests are skipped cleanly without HA** (the one small, documented guard). The root
   `tests/conftest.py` sets `collect_ignore_glob = ["integration/*"]` when
   `importlib.util.find_spec("pytest_homeassistant_custom_component") is None`. It also implements
   `pytest_report_header` to print one line such as
   "HA test harness not installed: tests/integration ignored (run in the container: uv sync --group ha)".
   On Windows, `uv run pytest -m integration` then ends with exit code 5 ("no tests ran") and no errors.
   A conftest-level guard is used because test modules import `homeassistant.*` at the top, so a per-test
   skip marker would come too late.
5. **Test level markers** `unit`, `integration`, `golden` are registered, with `--strict-markers --strict-config`.
   The root conftest applies the marker automatically from the directory (`tests/unit/` → `unit`, etc.)
   in `pytest_collection_modifyitems`. No golden tests yet. `tests/fixtures/private/` is already
   git-ignored (check, do not duplicate).
6. **Integration skeleton.** `manifest.json`: `"domain": "energy_cost_stats"`, `"name": "Energy Cost Stats"`,
   `"config_flow": false` (config flow comes in stage 2), `"dependencies": ["recorder"]`,
   `"iot_class": "calculated"`, **`"integration_type": "service"`** *(human-confirmed)*,
   `"requirements": []`, `"version": "0.1.0"`, `"codeowners": ["@MrKiirya"]`, documentation = repo URL,
   issue_tracker = repo issues URL. `__init__.py` defines `CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)`
   (hassfest wants a config schema when `async_setup` exists) and `async def async_setup(hass, config) -> bool`
   returning `True`. Nothing else: no entities, platforms or services.
7. **Commit an empty `custom_components/__init__.py`** *(human-confirmed)*. PHCC recommends it. It is a file,
   not a subdirectory, so the HACS "one subdirectory" rule still holds.
8. **Minimum HA is exactly `2025.4.0`** *(human-confirmed)*: PHCC `==0.13.232`, `hacs.json`
   `"homeassistant": "2025.4.0"`.
9. **`script/setup` = `uv sync --group ha` only** *(human-confirmed)*: no npm, no git hooks. Scripts are
   POSIX `sh`, for Linux / container / CI. Native Windows uses the uv commands directly (see CLAUDE.md
   update below).
10. **Recorder principle enforced by lint.** Ruff `flake8-tidy-imports` banned-api (`TID251`) bans
    `homeassistant.components.recorder` everywhere, with `per-file-ignores` for
    `custom_components/energy_cost_stats/recorder_adapter.py` (the future adapter, CLAUDE.md principle 5)
    and `tests/**`.
11. **Coverage gate** is in `script/test`:
    `uv run --group ha pytest --cov=custom_components/energy_cost_stats/engine --cov-report=term-missing --cov-fail-under=95 "$@"`.
    `uv run pytest -m unit` stays fast and has no gate.
12. **`script/develop`** is written now following the integration_blueprint pattern (create `config/` via
    `hass --script ensure_config`, add `custom_components` to `PYTHONPATH`, run `hass --config config --debug`,
    all through `uv run --group ha`). It is only *verified* in 002-devcontainer. If `uname` reports a Windows
    environment (MINGW/MSYS/CYGWIN), it exits 1 with "Home Assistant does not run natively on Windows; use
    the devcontainer". It must not produce committed files. `config/` is git-ignored except
    `config/configuration.yaml`, and creating that file is 002's job.

### One-off container verification (implementer runs on a Windows host with Docker Desktop, Linux containers)
The devcontainer itself is 002. For this task, the implementer checks the Linux side once. Replace
`<repo>` with the local checkout path, and do **not** write that path into any committed file:

```sh
docker run --rm -v "<repo>:/work" -w /work \
  -e UV_PROJECT_ENVIRONMENT=/opt/venv -e UV_LINK_MODE=copy \
  ghcr.io/astral-sh/uv:python3.14-trixie \
  sh -c "sh script/setup && uv run --group ha pytest -m integration && uv run --group ha pyright && sh script/test"
```
Variant for min HA (Python 3.13 → HA 2025.4.0):
```sh
docker run --rm -v "<repo>:/work" -w /work \
  -e UV_PROJECT_ENVIRONMENT=/opt/venv -e UV_LINK_MODE=copy \
  ghcr.io/astral-sh/uv:python3.13-trixie \
  sh -c "uv sync --group ha --python 3.13 && uv run --group ha --python 3.13 pytest -m integration && uv run --python 3.13 python -c 'import homeassistant.const as c; print(c.__version__)'"
```
Why the extra flags:
- `UV_PROJECT_ENVIRONMENT=/opt/venv` keeps the Linux venv out of the bind mount, so the host's Windows
  `.venv` is not overwritten.
- `UV_LINK_MODE=copy` avoids hardlink warnings across filesystems.
- `sh script/…` avoids depending on the executable bit through the Windows bind mount.
- `.gitattributes` already forces LF, so the scripts run in the container.

Pyright must therefore **not** hardcode `venvPath`/`venv` in `pyproject.toml`. It picks up the interpreter
from the environment `uv run` activates, which works both on the host and in the container.

## Files
- create: `pyproject.toml` — uv project (decision 1); `[dependency-groups]` `dev` + `ha` (decision 2);
  `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `pythonpath` per decision 3, markers with one-line
  descriptions, `addopts = "--strict-markers --strict-config"`, `asyncio_mode = "auto"`,
  `asyncio_default_fixture_loop_scope = "function"`); `[tool.coverage.run] branch = true`;
  `[tool.ruff]` (`target-version = "py313"`, rule set e.g. `E, W, F, I, UP, B, SIM, RUF, PT, ASYNC, TID`,
  isort `known-first-party`, banned-api + per-file-ignores per decision 10); `[tool.pyright]`
  (`pythonVersion = "3.13"`, `include = ["custom_components", "tests"]`, `typeCheckingMode = "standard"`,
  `strict = ["custom_components/energy_cost_stats/engine"]`, `extraPaths` per decision 3, no `venvPath`/`venv`).
- create: `.python-version` — `3.14`.
- create: `uv.lock` — generated by `uv lock`, committed.
- create: `script/setup` — `#!/bin/sh`, `set -eu`, cd to repo root, check that `uv` exists (otherwise print
  an install hint and exit 1), then `uv sync --group ha "$@"`.
- create: `script/test` — decision 11.
- create: `script/lint` — `uv run ruff check .` then `uv run ruff format --check .` (no HA needed).
- create: `script/develop` — decision 12.
- create: `custom_components/__init__.py` — empty (decision 7).
- create: `custom_components/energy_cost_stats/manifest.json` — decision 6.
- create: `custom_components/energy_cost_stats/const.py` — only `DOMAIN: Final = "energy_cost_stats"`.
- create: `custom_components/energy_cost_stats/__init__.py` — decision 6, with a module docstring.
- create: `custom_components/energy_cost_stats/engine/__init__.py` — docstring: purity rule (no
  `homeassistant`, relative imports only) and the dual-name caveat (decision 3).
- create: `hacs.json` — `{"name": "Energy Cost Stats", "homeassistant": "2025.4.0"}`.
- create: `tests/conftest.py` — decisions 4 and 5 only (marker auto-apply, integration ignore + report header).
- create: `tests/integration/conftest.py` — autouse fixture that requests `recorder_mock` first, then
  `enable_custom_integrations`.
- create: `tests/unit/test_engine_isolation.py`, `tests/unit/test_metadata.py`, `tests/integration/test_setup.py`.
  Add `__init__.py` files in `tests/` only if needed. Do **not** add `tests/unit/__init__.py` if it would make
  pytest's rootdir insertion shadow the `engine` name. The implementer decides and notes it.
- modify: `CLAUDE.md` — **Commands table only** (the main session rewrites the Environment wording). Remove
  the "Planned" note and describe both setups, for example with a "Where" column:
  - Windows native: `uv sync` (install, no HA); `uv run pytest -m unit`; `uv run ruff check .` and
    `uv run ruff format --check .` (the `script/lint` equivalent).
  - Linux container / CI: `script/setup`, `script/test`, `script/lint`, `uv run --group ha pytest -m integration`,
    `uv run --group ha pyright`, `script/develop` (verified in 002).
  - Card rows stay, marked "stage 4".
  - Add one line under "Test levels" → `unit`: unit tests import `engine…` only, never
    `custom_components.energy_cost_stats…` (dual-name caveat).
- modify: `README.md` — short "Development" section: the two setups in two or three lines each, and a pointer
  to CLAUDE.md. Keep the "work in progress" status.
- modify (only if needed): `docs/SPEC.md` §6 — one line on how min/latest HA are pinned (PHCC + python_version markers).

## Tests to write first
| Level | Test | Asserts |
|---|---|---|
| unit | `tests/unit/test_engine_isolation.py::test_engine_importable_as_top_level` | `import engine` succeeds; `engine.__file__` is inside `custom_components/energy_cost_stats/engine/`; on a host without HA (`find_spec("homeassistant") is None`), `"homeassistant"` is not in `sys.modules` after the import. |
| unit | `tests/unit/test_engine_isolation.py::test_engine_has_no_forbidden_imports` | An AST scan of every `*.py` under `engine/` finds none of: `import homeassistant…` / `from homeassistant…`; absolute imports of `engine…` or `custom_components…`; relative imports with level ≥ 2. Also asserts that at least one file was scanned, so the test is not vacuous. |
| unit | `tests/unit/test_engine_isolation.py::test_guard_detects_violations` | Parametrized synthetic sources in `tmp_path`: `import homeassistant`, `from homeassistant.core import HomeAssistant`, `from .. import const`, `import custom_components.energy_cost_stats.const`, `from engine import x`. The same checker helper flags each one. A clean source (`import math`, `from . import x`, `from .sub import y`) is not flagged. |
| unit | `tests/unit/test_engine_isolation.py::test_unit_tests_do_not_import_integration_package` | An AST scan of every `*.py` under `tests/unit/` finds no import of `custom_components…` (dual-name rule). String literals are not flagged. |
| unit | `tests/unit/test_metadata.py::test_manifest_matches_domain` | `manifest.json` parses as JSON. `domain` equals the `DOMAIN` value read from `const.py` **via AST** (no import of the integration package). Keys `domain, name, version, documentation, issue_tracker, codeowners, iot_class, integration_type` are present; `integration_type == "service"`; `iot_class == "calculated"`; `config_flow` is false or absent; `"recorder" in dependencies`; `version` matches `^\d+\.\d+\.\d+$`. |
| unit | `tests/unit/test_metadata.py::test_hacs_json` | `hacs.json` parses; `name` is non-empty; `homeassistant == "2025.4.0"`. |
| unit | `tests/unit/test_metadata.py::test_single_integration_dir` | `custom_components/` has exactly one subdirectory, `energy_cost_stats` (ignoring `__pycache__`). |
| integration | `tests/integration/test_setup.py::test_async_setup` | With `recorder_mock` + `enable_custom_integrations`: `await async_setup_component(hass, DOMAIN, {})` is `True`; `DOMAIN in hass.config.components`; `"recorder" in hass.config.components`; `hass.states.async_all()` has no state whose entity_id contains `energy_cost_stats`. |

## Acceptance criteria
Windows native (PowerShell, no Docker):
- [x] `uv sync` → exit 0. `uv pip list` shows neither `pytest-homeassistant-custom-component` nor `homeassistant`.
- [x] `uv run pytest -m unit` → all unit tests pass.
- [x] `uv run pytest -m integration` → exit code 5 ("no tests ran"), no collection errors. The report header shows the "HA test harness not installed" line.
- [x] `uv run pytest -m golden` → exit code 5, no "unknown marker" error.
- [x] `uv run pytest --markers` lists `unit`, `integration`, `golden` with descriptions.
- [x] `uv run ruff check .` and `uv run ruff format --check .` → exit 0.

Linux container (one-off `docker run` from Context; 3.14 image):
- [x] `sh script/setup` → exit 0.
- [x] `uv run --group ha pytest -m integration` → `test_async_setup` passes.
- [x] `uv run --group ha pyright` → 0 errors.
- [x] `sh script/test` → all tests pass; the coverage report lists only `engine/` files; the `--cov-fail-under=95` gate is met.
- [x] `sh script/lint` → exit 0.
- [x] 3.13 variant: `pytest -m integration` passes and the printed HA version is `2025.4.0`. If this cannot be run, the reason goes in Implementation notes and 003-ci covers it.
- [x] The host `.venv` is unchanged by the container runs (thanks to `UV_PROJECT_ENVIRONMENT`).

General:
- [x] `uv lock --check` → exit 0 (lockfile up to date).
- [x] Temporarily adding `from homeassistant.components.recorder import get_instance` to `custom_components/energy_cost_stats/__init__.py` makes `uv run ruff check .` fail with `TID251` (the reviewer checks this, then reverts).
- [x] Temporarily adding `import homeassistant` to `engine/__init__.py` makes `test_engine_has_no_forbidden_imports` fail. Temporarily adding `import custom_components.energy_cost_stats.const` to a unit test makes `test_unit_tests_do_not_import_integration_package` fail. (The reviewer checks both, then reverts.)
- [x] `tests/conftest.py` has no `sys.modules` manipulation.
- [x] No entities are created (only `async_setup`). `engine/` contains only `__init__.py`.
- [x] No local absolute paths (`C:\`, `D:\`, `/home/`, `/Users/`) and no real entity ids in committed files (grep outside `.venv`). The `docker run` example uses the `<repo>` placeholder.
- [x] The CLAUDE.md Commands table no longer contains "Planned" and documents both setups. Every listed command exists and behaves as described.
- [ ] After staging, `git ls-files -s script/` shows mode `100755` for all four scripts. The implementer cannot stage, so the **main session** runs `git add --chmod=+x script/*` when committing.

## Out of scope
- Devcontainer, `.vscode/` launch/tasks, committed `config/configuration.yaml`, and verifying `script/develop` → **002-devcontainer**.
- GitHub Actions (matrix 3.13 / HA 2025.4.0 and 3.14 / latest, ruff, pyright, hassfest, HACS validation), branch protection, automated PHCC bumps → **003-ci**.
- Brand assets (`brand/icon.png`) needed to publish on HACS → a later task.
- Frontend / card (`frontend/`, npm) → stage 4.
- Any engine logic, recorder adapter, config/options flow, subentries, websocket, services.
- Running integration tests natively on Windows.

## Open questions
- None blocking. The previous questions (integration_type, `custom_components/__init__.py`, exact min HA,
  scope of `script/setup`) were answered and moved to Decisions 6–9.

<!-- Filled in by implementer -->
## Implementation notes
- **uv install.** Not present on the host; installed for the current user via the official
  `irm https://astral.sh/uv/install.ps1 | iex` one-liner (per-user install, no admin rights needed).
- **`UV_PYTHON_INSTALL_DIR` workaround (host-only, not in any repo file).** On this Windows host, `uv sync`
  failed with "Missing expected target directory for Python minor version link" under uv's default Python
  install directory — on some Windows hosts that directory is redirected in a way that breaks the
  minor-version symlink `uv` creates there. Workaround: pointing the `UV_PYTHON_INSTALL_DIR` environment
  variable at a plain directory outside the default location makes `uv python install` / `uv sync` work
  normally. This is a local environment quirk, not a project requirement — nothing in the repo hardcodes it.
  Machine-specific details (if any) belong in the git-ignored `CLAUDE.local.md`, not in this task file.
- **`uv lock` / `uv sync --group ha` on Windows — real fix needed.** The `ha` group's marker for the latest
  PHCC pin was originally `python_version >= '3.14'` (task Decision 2). `uv lock` failed universal
  resolution: `pytest-homeassistant-custom-component>=0.13.366` currently resolves to
  `homeassistant==2026.9.3`, which requires `python_full_version >= '3.14.2'`. For the marker slice
  `3.14.0 <= python_full_version < 3.14.2` (still `python_version >= '3.14'`), no available `homeassistant`
  release satisfies both constraints, so uv's universal ("forked") resolution had no solution. Fixed by
  tightening the marker to `python_full_version >= '3.14.2'` in `pyproject.toml`'s `ha` group (instead of
  `python_version >= '3.14'`). `.python-version` (`3.14`) resolved to CPython `3.14.7` here, which satisfies
  `>=3.14.2`, so `uv sync --group ha` on 3.14 picks the intended latest-PHCC branch; the narrow
  `3.14.0`–`3.14.1` slice simply has no `ha` group member, which is fine since no PHCC release targets it.
  `uv lock --check` and `uv sync` (Windows, no `ha`) both pass; `uv sync --group ha` verified in the 3.14 and
  3.13 containers (see below).
- **Review round 1, Suggestion 1 applied.** Added `[tool.uv] environments = ["python_full_version < '3.14'",
  "python_full_version >= '3.14.2'"]`. Before this, `uv sync --group ha` on a 3.14.0/3.14.1 interpreter
  silently resolved with no `ha`-group package at all (no error), so `pytest -m integration` would just
  print the "not installed" header and exit 5 instead of failing loudly — verified this gap in a container
  with `uv sync --group ha --python 3.14.1 --managed-python` before the fix. With the `environments`
  constraint, the same command now fails at sync time with "the current Python platform is not compatible
  with the lockfile's supported environments", which is the desired loud failure. Re-verified the full
  matrix afterwards (Windows unit tests + ruff, 3.14 container setup/integration/pyright/test/lint, 3.14.1
  gap probe) — all as expected.
- **Docker verification (3.14 image).** `sh script/setup && uv run --group ha pytest -m integration &&
  uv run --group ha pyright && sh script/test && sh script/lint` all passed: 1 integration test, pyright
  "0 errors", `script/test` "15 passed" with engine coverage 100% (only file is the empty
  `engine/__init__.py`, gate is ≥95%), lint clean. Had to fix two `pyright` `reportReturnType` errors in
  `tests/unit/test_metadata.py::_read_domain_const_via_ast` (narrowing `ast.Constant.value` from `object` to
  `str` with an explicit `isinstance` assert) — not caught by the local Windows setup because `pyright`
  needs the `ha` group (bundles the `nodejs` extra `pyright` pulls in) and only runs in the container per the
  task's setup split.
- **Docker verification (3.13 image, min HA).** `uv sync --group ha --python 3.13` resolved PHCC `0.13.232`
  → `homeassistant==2025.4.0` (printed via `python -c 'import homeassistant.const as c; print(c.__version__)'`),
  integration test passed. Ran successfully, so no follow-up needed for 003-ci on this point.
  Used `MSYS_NO_PATHCONV=1` before `docker run` so Git Bash does not mangle the `/work` container paths.
- **Host `.venv` isolation confirmed.** `UV_PROJECT_ENVIRONMENT=/opt/venv` + `UV_LINK_MODE=copy` kept the
  container's venv out of the bind mount; after both container runs, `git status --porcelain` on the host
  still shows no `.venv` changes and `uv lock --check` / `uv pip list` (host) are unaffected.
- **`tests/unit/__init__.py` / `tests/integration/__init__.py`: not added.** Per decision, adding
  `tests/unit/__init__.py` risked pytest inserting the `tests/unit` directory itself onto `sys.path` in a
  way that could shadow the top-level `engine` name; the `pythonpath` ini option already makes `import
  engine` work without it, and plain rootdir-relative collection (no `__init__.py`) is enough for unique
  test module names here. `tests/conftest.py` and `tests/integration/conftest.py` don't need one either.
- **Marker auto-apply implementation.** `pytest_collection_modifyitems` in `tests/conftest.py` inspects
  `Path(item.fspath).parts` for `"unit"` / `"integration"` / `"golden"` (first match wins) rather than
  string-matching the path, to be OS-path-separator-agnostic (this was exercised on both Windows and Linux
  during verification).
- **Acceptance criterion 243 (guard tests), reviewer note.** Temporarily adding
  `import custom_components.energy_cost_stats.const` to `tests/unit/test_metadata.py` and running
  `uv run pytest -m unit` on Windows (no HA installed) fails at **collection** with
  `ModuleNotFoundError: No module named 'homeassistant'` (raised while importing
  `custom_components.energy_cost_stats.__init__`, which imports `homeassistant.helpers.config_validation`),
  rather than at the guard test's own `assert not all_violations`. This still proves the violation is caught
  (the whole module fails to collect because of it), but through Python's real import machinery rather than
  the AST-based guard — the AST-only assertion failure only reproduces exactly as worded when HA *is*
  installed (verified separately: the AST checker function itself is covered directly, without any import,
  by `test_guard_detects_violations`, which parametrizes exactly this source line as a string). Reverted
  after checking. Same technique verified for the `TID251` ruff criterion and for adding
  `import homeassistant` to `engine/__init__.py` (that one does fail via the guard test's own assertion, as
  worded, since it doesn't trigger a real import of `homeassistant.helpers.config_validation`).

## Follow-ups
- `CLAUDE.local.md` (git-ignored, out of scope for this task) could record the `UV_PYTHON_INSTALL_DIR`
  workaround for this machine so future sessions don't have to rediscover it.
- 002-devcontainer should double-check whether the same uv Python-install-directory redirection issue
  affects the devcontainer's own Python install step, or whether it's specific to this bare-Windows-host
  setup (the devcontainer runs Linux, so it is very unlikely to reproduce there, but worth a one-line check).
- Review suggestion 2 (`docs/SPEC.md` §6 / task Decision 2 wording: describe the `python_full_version >=
  '3.14.2'` floor precisely, and note that "latest" means the locked PHCC version) — not yet applied.
- Review suggestion 3 (`tests/conftest.py` marker auto-apply: derive the level from the path relative to
  `tests/`, e.g. `item.path.relative_to(config.rootpath / "tests").parts[0]`, instead of scanning all parts
  of the absolute path, and stop using the legacy `item.fspath`) — not yet applied.
- Review suggestion 4 (this file's Docker-verification bullet: fix the inaccurate claim that pyright "needs
  the `ha` group" for the `nodejs` extra — `pyright[nodejs]` is in `dev` and installs on Windows; pyright
  only needs the container because it must resolve `homeassistant` imports) — not yet applied.
- Review suggestion 6 (`tests/unit/test_engine_isolation.py`: add direct parametrized positive/negative
  tests for `find_integration_package_imports`, mirroring the ones already covering
  `find_forbidden_engine_imports`) — not yet applied.
