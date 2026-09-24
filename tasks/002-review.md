# 002 — Review (round 4)

Verdict: APPROVE

Scope: the uncommitted working tree vs `HEAD`, focused on the two round-3 required items. The changes are
`script/develop` (`--no-sync` on the `ensure_config` `uv run`), `script/prefetch_ha_requirements.py`
(`summarize_failures()` extracted), `tests/unit/test_prefetch_ha_requirements.py` (six new tests) and the task
file's "Review round 3 fixes" notes. The rest of the prefetch work was reviewed in round 3 and is not re-reviewed
here. Untracked `tasks/003`–`007` and the `.claude/agents/implementer.md` edit are out of scope.

## Checks run
Windows host (native):
- `uv run pytest -m unit` → `37 passed`
- `uv run ruff check .` → `All checks passed!`; `uv run ruff format --check .` → `28 files already formatted`
- `uv lock --check` → `Resolved 229 packages` (lock unchanged)

Mutation checks. I ran these on a scratch copy of `script/` plus the new test file, outside the repo, so the
working tree was never modified (`git status` is identical before and after). The scratch copy also held one
unrelated test that fails there because `.devcontainer/` was not copied. The counts below are relative to that
baseline.
- Removed `--no-sync` from `script/develop`'s `ensure_config` line → `test_uv_run_invocations_carry_no_sync` fails.
- Removed `--no-sync` from `script/develop`'s final `exec uv run` line → the same test fails.
- Removed `--no-sync` from `script/setup`'s `uv run` line → the same test fails.
- Made the critical branch in `summarize_failures` `return 0` → 2 tests fail (`..._critical_failure_aborts` and
  `..._via_fake_installer_frontend_failure_aborts`).
- Replaced `critical_failures` with `[]` → the same 2 tests fail.
- Made `summarize_failures` always `return 0` → 3 tests fail.
- Made `main()` ignore `summarize_failures`'s return value → no test fails (see Suggestion 1).

Fresh devcontainer (`docker volume rm energy-cost-stats-ha-config`, then
`npx @devcontainers/cli up --remove-existing-container`, latest HA 2026.9.3 on Python 3.14):
- `up` → `{"outcome":"success"}`. Post-create `script/setup` printed `pre-installing 25 …`.
- `sh script/setup` again → rc 0, `pre-installing 25 …`. `$HA_CONFIG_DIR` was confirmed **empty** afterwards.
  The venv has `bleak-retry-connector 4.7.0`, `habluetooth 6.26.11` and `home-assistant-frontend`.
- `sh script/develop` on the empty volume → the log starts with `Unable to find configuration. Creating default
  one`. It has **0** `Attempting install of` lines and **0** `Uninstalled/Installed N packages` lines. It shows
  `Setting up frontend`, `Setting up energy_cost_stats` and `Home Assistant initialized in 5.80s`, with no
  recovery mode. Stopped with `TERM`. No `hass` process was left.
- `sh script/smoke-develop` → rc 0, `OK: HTTP 200 on :8123; log line: … Setting up energy_cost_stats`, and no
  `hass` process afterwards.

3.13 / min-HA leg (one-off `ghcr.io/astral-sh/uv:python3.13-trixie`, repo copied into the container,
`UV_PROJECT_ENVIRONMENT=/opt/venv`, empty `HA_CONFIG_DIR`). I ran it twice, with the same results:
- `sh script/setup --python 3.13` → rc 0, `pre-installing 18 …`, venv `3.13.15` / `homeassistant 2025.4.0`.
- `sh script/develop` on the empty config dir → `Creating default one`, **0** `Attempting install of`, **0**
  `Uninstalled/Installed N packages`, `Setting up stage frontend: {'frontend'}` and `initialized in 3.5s`.
  Afterwards the venv is still `3.13.15` / `2025.4.0`, and the `pyvenv.cfg` mtime is unchanged, so the venv
  was **not rebuilt**. The only noise is the known `Using incompatible environment … due to --no-sync` warning
  (round-3 Suggestion 5). The expected environment errors were logged: go2rtc (decision 6), plus
  ffmpeg/turbojpeg, which the bare image lacks. See also Suggestion 3.

Hygiene: I grepped the diff and both new files for drive-letter paths, `/Users/`, the host user name, email, IPv4
addresses other than 127.0.0.1, token/secret/password and the other local project's name. There were no hits.

Cleanup: the devcontainer was removed with `docker rm -f`. The 3.13 containers ran with `--rm`. The named volumes
were left in place. The unrelated pre-existing container was not touched. Host `git status` is unchanged.

## Acceptance criteria (follow-up round goal and round-3 required items)
- [x] After `script/setup`, a dev HA with `default_config:` starts without any live install, **including on a
      fresh, empty config volume**. Verified on 3.14/latest and on 3.13/2025.4.0 (round-3 Required 1 resolved).
- [x] A `--python 3.13` venv is no longer rebuilt by `script/develop`. Verified: the venv stays 2025.4.0.
- [x] The critical vs best-effort failure policy has unit tests that fail when the logic is neutralized
      (round-3 Required 2a resolved).
- [x] The `--no-sync` flags in `script/setup` and `script/develop` are guarded by a test that fails when any one
      of them is removed (round-3 Required 2b resolved).
- [x] The task file's incorrect verification claim now has an inline correction (line ~501), and the round is
      re-verified with a truly empty `HA_CONFIG_DIR`.
- [x] `script/smoke-develop` passes in the container. Host unit tests, ruff and `uv lock --check` pass.
- [x] No personal or local data.

## Findings
### Required
None.

### Suggestions
1. `script/prefetch_ha_requirements.py:261-262` — `main()` returning `summarize_failures(...)` has no test.
   Replacing it with `return 0` leaves the suite green. `main()` imports `homeassistant`, so the fix could be a
   small test that monkeypatches `collect_requirements`, `missing_requirements`, `install_requirements` and a
   stub `homeassistant` module. Alternatively, move the post-import flow into a helper that takes those values
   as arguments.
2. Round-3 suggestions that are still open: 1 (`flush=True` on the `print`s), 2 (pyright does not cover
   `script/`), 3 (`tasks/002-devcontainer.md:496` still says "0 the second (idempotent)", but a second
   `script/setup` actually re-installs the 25 after the exact sync), 4 (`DISCOVERY_INTEGRATIONS` rule) and 5
   (`--python` forwarding / the missing `Setting up energy_cost_stats` log line on 2025.4.0, for 003-ci).
3. For 003-ci / the min-HA leg: on 2025.4.0, `homeassistant_alerts` logged
   `TypeError: Channel.getaddrinfo() takes 3 positional arguments but 4 …`. This looks like an
   `aiodns`/`pycares` version mismatch between the lock and HA 2025.4.0's constraints. It does not block startup
   and is unrelated to this task. It is worth recording in the 003 follow-ups if that leg asserts on
   `ERROR` lines.
