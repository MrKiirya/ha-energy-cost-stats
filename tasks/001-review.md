# 001 — Review (round 2)

Verdict: APPROVE

## Checks run
Windows native (Git Bash, uv 0.12.18, CPython 3.14.7):
- `uv sync` → `Resolved 229 packages` / `Checked 15 packages`, exit 0. `uv pip list` has no `homeassistant` and
  no PHCC.
- `uv lock --check` → `Resolved 229 packages`, exit 0. The lock header now has
  `supported-markers = ["python_full_version < '3.14'", "python_full_version >= '3.14.2'"]`.
- `uv run pytest -m unit` → `14 passed in 0.05s`.
- `uv run pytest -m integration` → header `HA test harness not installed: tests/integration ignored (run in the
  container: uv sync --group ha)`, `14 deselected`, exit 5.
- `uv run pytest -m golden` → `14 deselected`, exit 5, no unknown-marker error.
- `uv run pytest --markers` → `unit`, `integration`, `golden` listed with descriptions.
- `uv run ruff check .` → `All checks passed!`; `uv run ruff format --check .` → `20 files already formatted`.

Linux container, `ghcr.io/astral-sh/uv:python3.14-trixie` (the task's command plus `sh script/lint` and
`uv lock --check`):
- `sh script/setup` → OK. `uv run --group ha pytest -m integration` → `1 passed, 14 deselected`.
- `uv run --group ha pyright` → `0 errors, 0 warnings, 0 informations`. This also covers the new `ConfigType`
  annotation.
- `sh script/test` → `15 passed`. The coverage table lists only `engine/__init__.py`, and the output shows
  `Required test coverage of 95% reached. Total coverage: 100.00%`.
- `sh script/lint` → `All checks passed!` / `20 files already formatted`.
- The container reports Python `3.14.7`, HA `2026.9.3`. `uv lock --check` passes in the container too.

Linux container, `ghcr.io/astral-sh/uv:python3.13-trixie`:
- `uv sync --group ha --python 3.13` → `uv run --group ha --python 3.13 pytest -m integration` → `1 passed`.
  The printed version is `3.13.15 2025.4.0`.

`environments` constraint probes (3.14 image, `--managed-python`):
- `uv sync --group ha --python 3.14.1` → `error: The current Python platform is not compatible with the
  lockfile's supported environments: …`. It now fails loudly as intended.
- Plain `uv sync --python 3.14.1` (no `ha` group) → the same error. See Suggestion 1.
- `uv sync --group ha --python 3.14.2` → installs, HA `2026.9.3`. The boundary is correct.

Host isolation:
- The mtimes of `.venv/pyvenv.cfg` and `.venv/Lib/site-packages` and the site-packages entry count are
  identical before and after the container runs. The SHA-1 of `uv.lock` and `pyproject.toml` is unchanged.

Hygiene:
- I grepped every committable file (`git ls-files --cached --others --exclude-standard`, 33 files) for:
  drive-letter paths, `/home/`, `/Users/`, `AppData`, `USERPROFILE`, the host user name, email, IPv4, secret
  assignments and non-generic entity ids.
  - No hits in the task-001 files.
  - The remaining hits are rule text (CLAUDE.md, acceptance-criteria wording) and generic container paths or a
    loopback URL in `tasks/002-devcontainer.md`, which is out of scope.
  - `uv.lock` has no local paths.
- `git status --porcelain --ignored`: only `.venv/`, `.coverage`, `.pytest_cache/`, `.ruff_cache/`,
  `__pycache__/` and `CLAUDE.local.md` are ignored. No junk would be committed, and no `config/` was created.

## Round 1 required items
1. Local machine paths in `tasks/001-scaffold.md`: **resolved.** The Implementation notes and the Follow-ups
   now describe the `UV_PYTHON_INSTALL_DIR` workaround generically. They contain no paths, no example value
   and no user-profile location. The only machine-related detail left is the public `install.ps1` one-liner,
   which is fine.
2. `async_setup` config type: **resolved.** `custom_components/energy_cost_stats/__init__.py:10,17` imports
   `ConfigType` from `homeassistant.helpers.typing` and annotates `config: ConfigType`. The unused `ConfigEntry`
   import is gone, and pyright passes in the container.

## Acceptance criteria
Windows native:
- [x] `uv sync` exit 0, no PHCC/HA — verified above.
- [x] `uv run pytest -m unit` all pass — 14 passed.
- [x] `-m integration` exit 5 + header line — verified.
- [x] `-m golden` exit 5, no unknown marker — verified.
- [x] `--markers` lists the three levels with descriptions — verified.
- [x] ruff check + format check exit 0 — verified.

Linux container:
- [x] `sh script/setup` exit 0 — verified (3.14 image).
- [x] integration `test_async_setup` passes — verified.
- [x] pyright 0 errors — verified.
- [x] `sh script/test` passes, coverage lists only `engine/`, gate met — verified.
- [x] `sh script/lint` exit 0 — verified.
- [x] 3.13 variant passes, HA `2025.4.0` — verified.
- [x] Host `.venv` unchanged — verified by the mtime/entry-count snapshot.

General:
- [x] `uv lock --check` exit 0 — verified on Windows and in the 3.14 container.
- [x] TID251 on a temporary recorder import — verified in round 1. The ruff config is unchanged since then, so
  I did not repeat it.
- [x] Engine guard and unit-test guard fail on temporary violations — verified in round 1. The guard code is
  unchanged, so I did not repeat it.
- [x] `tests/conftest.py` has no `sys.modules` manipulation — unchanged.
- [x] No entities; `engine/` holds only `__init__.py` — unchanged, and the integration test passes.
- [x] No local absolute paths or real entity ids in committed files — verified by grep (see Hygiene).
- [x] The CLAUDE.md Commands table has no "Planned" and documents both setups — unchanged since round 1.
- [ ] Scripts have mode `100755` after staging — **pending (main session)**. This happens at commit time with
  `git add --chmod=+x script/*`. It is not an implementer failure.

## Findings
### Required
None.

### Suggestions
1. `pyproject.toml:10-13` — the comment says the `environments` constraint makes "`uv sync --group ha` refuse
   to run on 3.14.0/3.14.1". In fact it blocks **every** `uv sync` / `uv run` on those interpreters, including
   the Windows-native `uv sync` without the `ha` group. I verified this: plain `uv sync --python 3.14.1` fails
   with the same error. This is acceptable because `.python-version` = `3.14` makes uv pick the latest 3.14
   patch (3.14.7 here), and CI's `setup-python 3.14` does the same. Fix direction: reword the comment to "uv
   refuses to sync or run on 3.14.0/3.14.1 at all". Also consider one line in CLAUDE.md Environment or
   SPEC §6 saying that Python 3.14.0–3.14.1 is unsupported for development.
2. `docs/SPEC.md:61-63` and `tasks/001-scaffold.md:30-31` (round 1 Suggestion 2, still open) — the text still
   says "`python_version` markers" and "`--python 3.14` resolves latest PHCC". This is now slightly more
   misleading: `--python 3.14` pointing at a 3.14.0/3.14.1 interpreter fails. Fix direction: mention the
   `python_full_version >= '3.14.2'` floor and the `[tool.uv] environments` split, and say that "latest" means
   the PHCC version in the lock. This can be done in 003-ci, where the matrix is defined.
3. `tasks/001-scaffold.md:298-301` (round 1 Suggestion 4, still open) — the Implementation notes still say
   pyright only ran in the container because it "needs the `ha` group (bundles the `nodejs` extra …)". That's
   inaccurate. `pyright[nodejs]` is in `dev`. Pyright needs the container because the `homeassistant` imports
   have to resolve.
4. Round 1 Suggestions 3 (`tests/conftest.py` marker derived from absolute path parts / legacy `item.fspath`)
   and 6 (direct tests for `find_integration_package_imports`) are still open. The task's Follow-ups record
   both, which is fine for a scaffold. Pick them up before real engine tests arrive.
5. `CLAUDE.md` Environment rewrite and the "Subagents always run in the background" line are main-session
   edits, per the orchestrator. They are out of scope for this review and were not assessed.
