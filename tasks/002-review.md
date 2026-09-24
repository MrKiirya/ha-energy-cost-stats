# 002 — Review (round 2)

Verdict: APPROVE

## Checks run
Windows host (native):
- `uv run pytest -m unit` → `20 passed` (before and after all container runs)
- `uv run ruff check .` → `All checks passed!`; `uv run ruff format --check .` → `22 files already formatted`
- Mutation checks on a scratch copy (repo not touched):
  - drop `/home/vscode/.ha-config` from the Dockerfile `install -d` line → `1 failed, 5 passed`
    (`test_dockerfile_creates_writable_mount_points`)
  - set the launch.json `--config` value back to `${workspaceFolder}/config` → `1 failed, 5 passed` (`test_launch_json`)

Headless devcontainer:
- `docker volume rm energy-cost-stats-ha-config` first, so the HA config volume starts fresh
- `npx --yes @devcontainers/cli up --workspace-folder . --remove-existing-container` →
  `{"outcome":"success", … "remoteUser":"vscode"}`
- `id` → `uid=1000(vscode)`; `ls -ld /home/vscode/.ha-config` → `vscode vscode` on the new, empty volume (was
  `root:root` in round 1); `/home/vscode/.cache/uv` and `/opt/venv` are also `vscode vscode`
- versions → `Python 3.14.7`, `uv 0.12.18`, `v24.21.0`, npm `11.19.0`; `HA_CONFIG_DIR=/home/vscode/.ha-config`
  comes from `containerEnv` (no override given)
- **`sh script/develop` with default settings, fresh volume** → `http=200` on `:8123/manifest.json` after ~36 s;
  log contains `Setting up energy_cost_stats` and `Setup of domain energy_cost_stats took 0.00 seconds`; no
  `energy_cost_stats` error lines. `configuration.yaml` in the volume is a symlink to
  `/workspaces/ha-energy-cost-stats/config/configuration.yaml`; the DB, `.storage/` and logs are in the volume.
  `kill -TERM` → process gone in 2 s; `ps` shows no `hass`/`uv run`. Unrelated errors seen: `go2rtc` setup failed,
  so `default_config` failed too (already recorded in Implementation notes).
- Second `sh script/develop` on the populated volume (skips `ensure_config`, re-links) → `http=200` after ~6 s,
  symlink intact, clean stop in 1 s, no leftover process
- `sh script/test` → `21 passed`, `Required test coverage of 95% reached. Total coverage: 100.00%`, rc 0
- `sh script/lint` → `All checks passed!` / `22 files already formatted`, rc 0
- `uv run --group ha pyright` → `0 errors, 0 warnings, 0 informations`
- `sh script/smoke-develop` → `OK: Home Assistant answered on :8123 and energy_cost_stats set up cleanly.`, rc 0;
  no `hass`/`uv run` process afterwards
- `git status --porcelain` in the container → the same 12 entries as on the host (no mode or line-ending noise)
- Cleanup: `docker rm -f <containerId>` done; named volumes left in place; the pre-existing unrelated container
  was not touched.
- Host checkout after all runs: `config/` contains only `configuration.yaml`, no `.venv/bin/`, and `git status`
  is unchanged. The only files the container wrote into the checkout are git-ignored tool caches (`.coverage`,
  `.pytest_cache/`, `.ruff_cache/`) from `script/test`/`script/lint`, which is the 001 design and not HA runtime data.

Hygiene: grepped all tracked and untracked non-ignored files (`git ls-files -co --exclude-standard`) for
drive-letter paths, `/Users/`, non-`vscode` `/home/` paths, the host user name, email, IPv4 other than
`127.0.0.1`, token/secret/password/api key, `compose`, and the parent folder name. Only generic, explanatory hits
were found. The task file's "Cleanup performed" note now just says "an unrelated, already-stopped container from
a different local project", with no names. No junk files. `.devcontainer/devcontainer-lock.json` holds only the
public Node feature digest.

## Acceptance criteria
- [x] `uv run pytest -m unit` passes, including the new tests — verified on the host (20 passed).
- [x] ruff check / format check exit 0 — verified on the host and in the container.
- [x] `docker build` succeeds — verified implicitly by `devcontainer up`, which built the changed Dockerfile.
- [x] `devcontainer up` → success; post-create ran — verified.
- [x] Python 3.14.x / uv 0.12.18 / Node v24.x — verified.
- [x] `/opt/venv` env and interpreter — verified (`UV_PROJECT_ENVIRONMENT=/opt/venv`, owned by vscode).
- [x] `script/test` in the container — verified (21 passed, coverage gate met).
- [x] `script/lint` in the container — verified.
- [x] `pyright` in the container → 0 errors — verified.
- [x] `script/smoke-develop` → exit 0, no `hass` left — verified. The output is still a generic OK line (round-1
      Suggestion 1, deferred to Follow-ups). The HTTP 200 and the setup line were confirmed separately (see above).
- [x] Container `git status` clean of noise — verified. `safe.directory` idempotency was verified in round 1, and
      `postStartCommand` has not changed since.
- [x] Host `.venv` untouched, host unit tests pass after the container runs — verified.
- [x] Optional min-HA check — skipped, with the reason recorded. Acceptable.
- [x] `:latest` uv pin mutation fails the Dockerfile test — verified in round 1; that test has not changed.
- [x] `script/develop` drops the `$(pwd)/custom_components` form and honours `HA_CONFIG_DIR` — verified by reading
      the script and running it with the container default.
- [x] No personal or local data in committed files — verified by the grep above (round-1 Required 2 resolved).
- [x] CLAUDE.md / README updated, and every listed command works — `script/develop` (the "Run dev HA" row and the
      README's http://localhost:8123) now works out of the box on a fresh volume (round-1 Required 1 resolved).
- [ ] Exec bit for `script/smoke-develop` (`git add --chmod=+x`) — pending, main session at commit time.
- [ ] Human: VS Code "Reopen in Container", extensions, Testing panel, onboarding at :8123, breakpoint in
      `async_setup` — pending, to be checked by the human.

Round-1 required items:
1. Root-owned HA config volume — **resolved**. `.devcontainer/Dockerfile:21` pre-creates `/home/vscode/.ha-config`.
   The new test `test_dockerfile_creates_writable_mount_points` fails without the fix (mutation-checked), and a
   fresh volume mounts as `vscode:vscode`, so `script/develop` runs with default settings.
2. Other-project mention in the task file — **resolved** (`tasks/002-devcontainer.md:351-354` is now generic).

Main-session request:
3. `.vscode/launch.json` uses the same config dir as `script/develop` — **resolved**. `.vscode/launch.json:9` has
   `"--config", "${env:HA_CONFIG_DIR}"`, which resolves to the named volume through `containerEnv`.
   `test_launch_json` now checks the exact value after `--config` (mutation-checked). The debug config itself
   (breakpoint) stays a human check.

## Findings
### Required
None.

### Suggestions
1. `.vscode/launch.json:9` — the debug config relies on `script/develop` having run at least once, because only
   that script symlinks the committed `config/configuration.yaml` into the volume. If the human starts the
   debugger first on a fresh volume, HA writes its own default `configuration.yaml` there without
   `energy_cost_stats:`, so the breakpoint in `async_setup` is never hit. (A later `script/develop` run repairs this
   with `ln -sf`.) The assumption is recorded in the Implementation notes, but not where the human will look.
   Options: add a one-line note to the README/CLAUDE.md devcontainer paragraph ("run `script/develop` once before
   using the debugger"), or add a `preLaunchTask` that performs the link (this would need a `.vscode/tasks.json`,
   which decision 8 excluded, so it is the human's call).
2. `tasks/002-devcontainer.md:146-149` (decision 8) and `:196` (the `test_launch_json` row) still say
   `--config ${workspaceFolder}/config` / "a `--config` value starting with `${workspaceFolder}`", which no longer
   matches the code. Update both to `${env:HA_CONFIG_DIR}` so the spec and the tests agree.
3. `tasks/002-devcontainer.md:323` — "(see that note above)" points to the "Cleanup performed" note, which is
   *below* (line 351). Change it to "below".
4. Round-1 suggestions 1–3, 6 and 7 are still open and correctly listed in Follow-ups. Before merging, decide
   whether to commit `.devcontainer/devcontainer-lock.json` (I recommend committing it: it holds only a public
   digest and makes Node feature resolution reproducible). The shorter CLAUDE.md `config/` bullet
   (`CLAUDE.md:24-27`) is still worth doing because the bullet contradicts itself.
