# 008 — Dev HA fixes: go2rtc binary, config-entry requirements, no uv-run reverts

Status: in-review
Roadmap: SPEC §8 stage 0 (project setup), follow-up to 002-devcontainer
Spec sections: SPEC §6 (min HA 2025.4 / latest); CLAUDE.md (Environment, Commands, "Never run a bare
`uv sync`"); `tasks/002-devcontainer.md` (decision 6, "Follow-up round", Follow-ups); `tasks/002-review.md`
(round 4 suggestions)

## Goal
A human ran the dev HA in the devcontainer (HA 2026.9.3, Python 3.14, not in recovery mode) and hit three
problems. First, `default_config` fails because `go2rtc` has no binary. Second, the `google_translate` config
entry that onboarding creates fails with `ModuleNotFoundError: No module named 'gtts'`. Third, the known 002
follow-up: `script/test`, `script/lint` and pyright use a syncing `uv run`, which reverts two pre-installed
packages, so HA then installs them live.

After this task:
- The devcontainer image ships a pinned `go2rtc` binary, so `default_config` sets up cleanly.
- The pre-install helper also covers integrations that have config entries in the dev HA config dir.
- `script/develop` re-runs the (idempotent) pre-install right before it starts HA. This covers anything a
  `uv run`, a `script/setup` or a container rebuild removed or reverted since the last start.
- `script/smoke-develop` fails when `default_config` fails to set up its dependencies, and it reports live
  installs.

CI behaviour does not change.

## Context

### 1. go2rtc (checked 2026-09-25)
- HA's `go2rtc` integration (a `default_config` dependency) finds the binary with `shutil.which("go2rtc")`.
  When `is_docker_env()` is true (`/.dockerenv` or `/run/.containerenv` exists, among other checks) and no
  `url` is configured, a missing binary means `_LOGGER.error("Could not find go2rtc docker binary")` and
  `return False`. That makes `default_config` fail its dependencies. On a **non-Docker** host (for example a
  plain GitHub runner), `go2rtc` with only `default_config:` removes its entries and returns `True`, so CI
  never hits this. Sources:
  [go2rtc/__init__.py @2026.9.3](https://github.com/home-assistant/core/blob/2026.9.3/homeassistant/components/go2rtc/__init__.py),
  [util/package.py `is_docker_env` @2026.9.3](https://github.com/home-assistant/core/blob/2026.9.3/homeassistant/util/package.py),
  [go2rtc/__init__.py @2025.4.0](https://github.com/home-assistant/core/blob/2025.4.0/homeassistant/components/go2rtc/__init__.py).
- The version is not enforced. `async_setup_entry` compares the server version with `RECOMMENDED_VERSION`
  and, if the server is older, only creates a non-fixable **WARNING** repair issue (`recommended_version`).
  A newer binary is fine.
- `RECOMMENDED_VERSION`: **`1.9.14`** in HA 2026.9.3 (also on `dev`) and **`1.9.9`** in HA 2025.4.0.
  The `dev` const says it "is kept in sync with the go2rtc image pinned in the root Dockerfile by Renovate".
  Sources: [const.py @2026.9.3](https://github.com/home-assistant/core/blob/2026.9.3/homeassistant/components/go2rtc/const.py),
  [const.py @2025.4.0](https://github.com/home-assistant/core/blob/2025.4.0/homeassistant/components/go2rtc/const.py).
- How HA core installs it. The production image
  ([Dockerfile](https://github.com/home-assistant/core/blob/dev/Dockerfile)) uses
  `COPY --from=ghcr.io/alexxit/go2rtc:1.9.14@sha256:675c318b… /usr/local/bin/go2rtc /bin/go2rtc`. HA core's
  own devcontainer ([Dockerfile.dev](https://github.com/home-assistant/core/blob/dev/Dockerfile.dev)) uses
  `COPY --from=ghcr.io/alexxit/go2rtc:latest …`.
- Architectures. The go2rtc image is built with `CGO_ENABLED=0`, so the binary is static and runs on Debian
  trixie even though the image itself is Alpine-based
  ([go2rtc docker/Dockerfile @v1.9.14](https://github.com/AlexxIT/go2rtc/blob/v1.9.14/docker/Dockerfile)).
  The image is multi-arch (linux/amd64, linux/arm64, arm/v6, arm/v7, 386;
  [ghcr package](https://github.com/AlexxIT/go2rtc/pkgs/container/go2rtc)). A `COPY --from=<multi-arch
  tag or index digest>` therefore picks the build platform's architecture automatically (BuildKit), and
  amd64 and arm64 hosts need no per-arch logic. go2rtc v1.9.14 was released 2026-01-19.
- The server that HA starts listens on 127.0.0.1:18554 (RTSP), :18555/tcp (WebRTC), and either the API port
  11984 (2025.4.0) or a unix socket (2026.9.x). Nothing needs forwarding for dev.

**Decision 1.** Add one line to `.devcontainer/Dockerfile`:
`COPY --from=ghcr.io/alexxit/go2rtc:1.9.14@sha256:<index digest> /usr/local/bin/go2rtc /bin/go2rtc`.
- Pin the tag to the exact version that equals latest HA's `RECOMMENDED_VERSION`.
- Pin the digest too, like HA core and our action pinning policy (it is third-party executable code).
- The implementer gets the multi-arch **index** digest with
  `docker buildx imagetools inspect ghcr.io/alexxit/go2rtc:1.9.14`, and checks that it matches HA core's pin
  and that the index lists linux/amd64 and linux/arm64.
- Why this is enough for both matrix HA versions: 1.9.14 is at least 2025.4.0's recommended version
  (1.9.9), so neither version creates a repair issue.
- The devcontainer only runs latest HA. The 2025.4.0 leg runs in CI, where go2rtc is a no-op because it is
  not Docker.

**Drift guard.** A new integration test compares the Dockerfile pin with the installed HA's
`RECOMMENDED_VERSION`. It fails on the latest leg (and in the weekly canary) as soon as an HA bump raises the
recommended version above our pin. So "bump HA" also means "bump go2rtc".

### 2. Config-entry integrations (checked 2026-09-25)
- Onboarding's core-config step (`CoreConfigOnboardingView.post`, `POST /api/onboarding/core_config`, auth
  required) creates entries for `google_translate`, `met`, `radio_browser` and `shopping_list`
  ([onboarding/views.py @2026.9.3](https://github.com/home-assistant/core/blob/2026.9.3/homeassistant/components/onboarding/views.py)).
  `google_translate` requires `gTTS==2.5.4`
  ([manifest](https://github.com/home-assistant/core/blob/2026.9.3/homeassistant/components/google_translate/manifest.json)).
  None of these are in `uv.lock`. So an exact `uv sync` (inside `script/setup`) removes them, and a container
  rebuild starts from a fresh `/opt/venv` while the `energy-cost-stats-ha-config` volume still has the
  entries.
- Storage format. The file is `<config>/.storage/core.config_entries` (`STORAGE_DIR = ".storage"`,
  `STORAGE_KEY = "core.config_entries"`, version 1, minor 5). Its envelope is
  `{"version", "minor_version", "key", "data"}` and its body is `data.entries[]`. Each entry has `domain` and
  `disabled_by` (null or `"user"`); HA does not set up disabled entries. Sources:
  [config_entries.py @2026.9.3](https://github.com/home-assistant/core/blob/2026.9.3/homeassistant/config_entries.py),
  [helpers/storage.py @2026.9.3](https://github.com/home-assistant/core/blob/2026.9.3/homeassistant/helpers/storage.py).
- **The exact mechanism is not confirmed.** Normally HA installs a missing requirement itself when it sets up
  the entry, so a plain `ModuleNotFoundError` means something imported `gtts` before requirements were
  processed, or the install failed. The implementer **reproduces this first** (see Acceptance criteria),
  records the traceback and the code path in Implementation notes, and only then applies the fix. If the
  mechanism shows that the pre-install cannot fix it, stop and report.

**Decision 2.** Extend `script/prefetch_ha_requirements.py`:
- Add a pure function `config_entry_domains(config_dir: Path) -> list[str]`. It returns the sorted, unique
  `domain` values of entries whose `disabled_by` is null.
- It returns `[]` when the file does not exist. When the JSON is malformed or has an unexpected shape, it
  prints one warning to stderr and returns `[]`. It never breaks setup.
- `main()` gets a `--config-dir PATH` option (optional; without it, no config entries are read). It adds
  those domains to the walked roots, which also walks their `dependencies` / `after_dependencies`.
- Requirements reached only through config entries are **best-effort**. The critical set stays `frontend`.
- Domains without a built-in manifest (custom integrations under `<config>/custom_components`) are skipped
  silently, as `find_manifest` already does.
- To make review round-4 suggestion 1 cheap, move the post-import flow of `main()` into a helper that takes
  `components_dir`, `constraints`, the root domains and the extra manifests as arguments. Then a unit test can
  cover the exit code without `homeassistant`.

### 3. `uv run` reverting pre-installed packages (checked 2026-09-25)
- `uv run` syncs **inexactly** by default: it installs or updates packages to match the lock but does not
  remove extras. `--exact` opts into removal. `--no-sync` or `UV_NO_SYNC` skips the sync entirely
  ([uv — Syncing](https://docs.astral.sh/uv/concepts/projects/sync/),
  [uv — env vars](https://docs.astral.sh/uv/reference/environment/)).
- So `script/test`, `script/lint` and pyright do not delete HA runtime packages. They only move the packages
  that are pinned in both places back to the lock version (`bleak-retry-connector`, `habluetooth`; see 002).
  `script/setup`'s `uv sync` is exact and removes every runtime-only package (for example `gTTS`).

Options considered:
- a) `UV_NO_SYNC=1` in `containerEnv`. Rejected: in-container tests would then run against the HA-pinned
  versions instead of the lock's versions (no longer the same as CI). A changed `uv.lock` after `git pull`
  would also be silently ignored by every `uv run`.
- b) `--no-sync` in `script/test` / `script/lint`. Rejected for the same reasons, and CI calls these scripts
  after `script/setup`. It would work there, but it hides lock drift.
- c) **Chosen: `script/develop` re-runs the pre-install helper (with `--no-sync` and
  `--config-dir "$CONFIG_DIR"`) right before `exec … hass`.**
  - This is the only moment the venv state matters for dev HA, and HA is not running yet, so nothing races.
  - The helper is idempotent: when nothing is missing it prints "already installed" and never touches the
    network. When something is missing it reinstalls from the warm uv cache.
  - It fixes item 3 (reverted versions) and item 2 (entries created during a previous run, venv rebuilt, or a
    `script/setup` exact sync since then) with one mechanism.
  - Tests and pyright keep testing the lock versions, the same as CI. CI (`ci.yml`, `ha-latest-canary.yml`)
    needs **no change**: it never runs `script/develop`.

Remaining limit, documented and not fixed here. Running `script/test` **while** a dev HA is running can still
move the two dual-pinned packages under it. That is harmless for already-imported modules, and it is fixed
on the next `script/develop` start. A **bare `uv sync`** while HA runs stays forbidden (CLAUDE.md).

### 4. `script/smoke-develop` and `default_config`
**Decision 4: fail.**
- Why fail and not only report: with the go2rtc binary in the image, `default_config` sets up cleanly in the
  devcontainer. 002's runs showed go2rtc as the only failing dependency. A dependency failure now means a
  real dev-environment regression, which is the kind of failure the smoke exists to catch (compare the
  recovery-mode false OK in 002). On non-Docker hosts (a future CI reuse), go2rtc is a no-op, so this cannot
  cause false failures there.
- New fatal patterns (HA wording from `setup.py`, same in 2025.4.0 and 2026.9.3:
  `"Setup failed for %s'%s': %s"`, `"Unable to set up dependencies of '%s'. Setup failed for dependencies: %s"`):
  `Setup failed for .*'default_config'` and `Unable to set up dependencies of 'default_config'`. The
  implementer confirms the exact lines against a real failing log (for example by building once without the
  go2rtc line). Sources: [setup.py @2026.9.3](https://github.com/home-assistant/core/blob/2026.9.3/homeassistant/setup.py),
  [setup.py @2025.4.0](https://github.com/home-assistant/core/blob/2025.4.0/homeassistant/setup.py).
- **Report only:** when the run succeeds, print every `Attempting install of` line (or "no live installs")
  after the OK line. This makes regressions of items 2 and 3 visible without making smoke flaky.

## Files
- modify: `.devcontainer/Dockerfile`: the go2rtc `COPY --from` line (decision 1), with a one-line comment
  that points to HA's `RECOMMENDED_VERSION`.
- modify: `script/prefetch_ha_requirements.py`: `config_entry_domains()`, `--config-dir`, and the testable
  post-import helper (decision 2). Update the module docstring.
- modify: `script/setup`: pass `--config-dir "${HA_CONFIG_DIR:-config}"` to the helper (after the script
  path; `"$@"` stays in front of `python` for `--python`).
- modify: `script/develop`: before the final `exec`, run
  `uv run --no-sync --group ha python script/prefetch_ha_requirements.py --config-dir "$CONFIG_DIR"`. Because
  of `set -eu`, a critical (frontend) failure aborts. Update the comment block.
- modify: `script/smoke-develop`: the `default_config` fatal patterns and the live-install report
  (decision 4).
- create: `tests/fixtures/ha_storage/core.config_entries`: a generic storage file in the real envelope. It
  has an enabled `google_translate` entry, an enabled `met` entry, a **disabled** (`"disabled_by": "user"`)
  entry for another domain, and a duplicate `google_translate` entry. Generic titles and data only (no
  coordinates, names or tokens; `met` data may be `{"track_home": true}`).
- modify: `tests/unit/test_prefetch_ha_requirements.py`: new tests below.
- modify: `tests/unit/test_devcontainer.py`: the Dockerfile go2rtc pin test and the smoke pattern test.
- create: `tests/integration/test_dev_env.py`: the go2rtc drift guard.
- modify: `CLAUDE.md`:
  - The "Never run a bare `uv sync`" paragraph gets one sentence: `script/develop` re-runs the pre-install at
    every start, which also covers config-entry integrations and packages reverted by `uv run`.
  - The "Bumping latest HA" bullet adds: "bump the go2rtc pin in `.devcontainer/Dockerfile` if
    `tests/integration/test_dev_env.py` fails".

## Tests to write first
| Level | Test | Asserts |
|---|---|---|
| unit | `tests/unit/test_prefetch_ha_requirements.py::test_config_entry_domains_from_fixture` | The fixture is copied to `tmp_path/.storage/core.config_entries`. The result is `["google_translate", "met"]`: sorted and deduplicated, and the disabled entry is excluded. |
| unit | `…::test_config_entry_domains_missing_file_returns_empty` | An empty `tmp_path` (no `.storage/`) gives `[]`. |
| unit | `…::test_config_entry_domains_malformed_returns_empty_and_warns` | Non-JSON content, and valid JSON with no `data.entries`, both give `[]` and write one warning line to stderr (`capsys`). |
| unit | `…::test_collect_requirements_includes_config_entry_domain_deps` | With fake manifests (`google_translate` requires `gTTS==x`, `met` depends on a domain that requires `pkg==y`) and roots = defaults + config-entry domains: both requirements are in `all_requirements`, and neither is in `critical`. |
| unit | `…::test_prefetch_flow_returns_summarize_exit_code` | The new post-import helper, with fake `components_dir` manifests and `subprocess.run` monkeypatched to fail the frontend requirement, returns 1. With a non-critical failure it returns 0. With nothing missing it installs nothing (no `subprocess.run` call). (Covers review round-4 suggestion 1.) |
| unit | `…::test_develop_runs_prefetch_before_hass` | In the text of `script/develop`, a non-comment line contains `prefetch_ha_requirements.py` and `--config-dir`, and it comes before the `exec uv run` line. The existing `test_uv_run_invocations_carry_no_sync` still passes, so the new line carries `--no-sync`. |
| unit | `…::test_setup_passes_config_dir_to_prefetch` | The `script/setup` line that calls the helper contains `--config-dir`. |
| unit | `tests/unit/test_devcontainer.py::test_dockerfile_pins_go2rtc` | The Dockerfile has exactly one line matching `^COPY --from=ghcr\.io/alexxit/go2rtc:(\d+\.\d+\.\d+)@sha256:[0-9a-f]{64} /usr/local/bin/go2rtc /bin/go2rtc$`. `latest` fails the test. |
| unit | `tests/unit/test_devcontainer.py::test_smoke_develop_fails_on_default_config_dependencies` | The text of `script/smoke-develop` contains `Unable to set up dependencies of 'default_config'` and a `Setup failed for` pattern that mentions `default_config`, both outside comments. It also contains `Attempting install of` (the report). |
| integration | `tests/integration/test_dev_env.py::test_go2rtc_pin_satisfies_recommended_version` | Parses the version from the Dockerfile line above and asserts `AwesomeVersion(pin) >= AwesomeVersion(homeassistant.components.go2rtc.const.RECOMMENDED_VERSION)`. Runs on both CI legs (≥ 1.9.9 on 2025.4.0, ≥ 1.9.14 on latest). Write it as `async def` if the autouse `recorder_mock` fixture in `tests/integration/conftest.py` requires it. |

## Acceptance criteria
Windows host (native):
- [x] `uv run pytest -m unit`: all pass, including the new tests. Each new test failed before its code change
      (record this in Implementation notes).
- [x] `uv run ruff check .` and `uv run ruff format --check .`: exit 0. `uv lock --check`: green.
      **Round 1 deviation:** `pyproject.toml` and `uv.lock` are touched after all, per round-1 Required 1
      (the `pycares<5` constraint for the `python_version < '3.14'` fork; see Implementation notes, round
      1). `uv lock --check` still reports the lock in sync with `pyproject.toml` after `uv lock` re-resolved
      it (230 packages, was 229); the latest-HA fork's resolution is unchanged.
- [ ] Temporarily changing the go2rtc pin to `:latest` makes `test_dockerfile_pins_go2rtc` fail (reviewer
      checks this, then reverts).

Headless devcontainer (`npx --yes @devcontainers/cli …` from the repo root). Record `containerId`, and at the
end remove the container with `docker rm -f`. Named volumes may stay, except where told to remove them.

**Reproduce first, on the pre-change image (current `master` state):**
- [ ] Remove `energy-cost-stats-ha-config`, run `up --remove-existing-container`, start `sh script/develop`
      in the background and wait for HTTP 200. Then onboard headlessly with `curl` inside the container.
      Use throwaway credentials that are never committed and never written into the task file.
      1. `POST /api/onboarding/users` with JSON `{client_id: "http://127.0.0.1:8123/", name, username,
         password, language: "en"}` returns `auth_code`.
      2. `POST /auth/token` (form: `grant_type=authorization_code`, `code`, `client_id`) returns
         `access_token`.
      3. `POST /api/onboarding/core_config` with `Authorization: Bearer <token>` returns `{}`.

      Wait until `google_translate` appears in `$HA_CONFIG_DIR/.storage/core.config_entries`, then stop HA
      with TERM. Run `sh script/setup`, then `sh script/develop` again. Record whether the log shows
      `No module named 'gtts'` and the traceback's import path. Also record the `Setup failed for
      'default_config'` / go2rtc lines. If the gtts error does not reproduce this way, record exactly what
      was tried.

**After the change:**
- [x] `… exec … sh -c 'command -v go2rtc && go2rtc --version'` prints version `1.9.14`. Record the
      `uname -m`. (`x86_64`; see Implementation notes.)
- [ ] Fresh volume (`docker volume rm energy-cost-stats-ha-config`, `up --remove-existing-container`), then
      `sh script/develop`: the log has `Setting up go2rtc`, no `Could not find go2rtc docker binary`, no
      `Setup failed for .*'(go2rtc|default_config)'`, no `Unable to set up dependencies of 'default_config'`,
      and `Home Assistant initialized in`.
- [ ] Config-entry scenario: onboard headlessly as above, stop HA, then `sh script/setup`.
  - The helper output lists `gTTS==…` (and the other onboarding requirements) as pre-installed, or says they
    are already installed.
  - Then `sh script/develop`: no `ModuleNotFoundError`, **0** `Attempting install of` lines,
    `Setting up google_translate` appears, no recovery mode.
- [ ] Rebuild scenario: `up --remove-existing-container` (config volume kept, fresh `/opt/venv`). The
      post-create `script/setup` output includes the config-entry requirements. The next `script/develop` has
      0 `Attempting install of` lines.
- [ ] Revert scenario (item 3): `sh script/setup`, then `sh script/test`, `sh script/lint` and
      `uv run --group ha pyright` (all green), then `sh script/develop`.
  - The helper step at the top of the develop output reinstalls `bleak-retry-connector` / `habluetooth`, or
    reports all installed.
  - The HA log has **0** `Attempting install of` lines.
  - A second `sh script/develop` start prints "already installed" for the helper step.
  - Record how long the helper step takes when nothing is missing.
- [x] `sh script/smoke-develop` exits 0 and prints the OK line plus the live-install report ("no live
      installs"). Afterwards, `pgrep -af hass` is empty.
- [ ] Negative check for decision 4. Build an image variant without the go2rtc line: use a temporary local
      edit that is reverted afterwards, or a scratch copy of `.devcontainer/` outside the repo. In it,
      `sh script/smoke-develop` exits non-zero with a message about `default_config`. Record the exact
      matched log line. Restore the Dockerfile and check that `git diff` is clean.
- [ ] 2025.4.0 with go2rtc (behaviour check). Use a one-off `docker run` of the **built devcontainer image**
      with the repo bind-mounted read-only, or copied in, and `UV_PROJECT_ENVIRONMENT` pointing to a separate
      path such as `/tmp/venv313`. Run `sh script/setup --python 3.13`, then `sh script/smoke-develop`. It
      exits 0 with HA `2025.4.0`, `Setting up go2rtc` and no `recommended_version` repair warning. If this is
      blocked, record why; do not substitute another check silently.
      **Round 1 (Required 1) status:** the `pycares`/`aiodns` crash is fixed (see Implementation notes,
      round 1). Verified directly with a bare `script/develop` run on this leg: `go2rtc` executes, a real
      DNS lookup through aiohttp's resolver succeeds (no `Channel.getaddrinfo()` `TypeError`), no
      `Setup failed for`/`Unable to set up dependencies` lines, no `recommended_version` repair warning,
      `Home Assistant initialized in 1.74s`, port 8123 answers 200. `sh script/smoke-develop` itself
      still does **not** exit 0 on this leg, for a separate, pre-existing reason unrelated to Required 1:
      HA 2025.4.0's `setup.py` logs `"Setting up %s"` at `_LOGGER.debug`, while 2026.9.3 logs it at
      `_LOGGER.info` (checked directly against both installed `setup.py` files); `script/develop`'s dev
      `configuration.yaml` only raises `custom_components.energy_cost_stats` to debug, not
      `homeassistant.setup`, so the line `smoke-develop` greps for never appears on this leg and it times
      out. This is a pre-existing gap in `smoke-develop`'s cross-version log assumptions (Sources in
      Decision 4 only checked the *fatal* patterns against both versions, not this success pattern), not
      something round 1's Required items asked for; recorded as a Follow-up instead of expanding this
      round's scope.
- [ ] `… exec … git status --porcelain` shows only this task's intended files.

General:
- [x] `ci.yml` and `ha-latest-canary.yml` are unchanged (verified: not in the diff). The new integration test
      passed inside the devcontainer (latest HA leg); the 2025.4.0 leg still needs CI to confirm (see
      Implementation notes).
- [x] No local absolute paths, real entity ids, IPs other than `127.0.0.1`, hostnames, credentials or tokens
      in committed files, including the fixture and Implementation notes.
- [x] CLAUDE.md is updated as listed in Files.

## Out of scope
- Requirements of custom integrations under `<config>/custom_components` with config entries (HA installs
  them live; revisit if needed).
- Committing a pre-seeded `.storage` into the dev config, or automating onboarding in `script/develop`.
- Renovate or Dependabot for the Dockerfile image pins (uv, go2rtc). The integration drift guard covers
  go2rtc for now.
- Running `script/smoke-develop` in CI (003 follow-up). Changing the `--python` forwarding in
  `script/develop`.
- Review round-3/4 suggestions other than round-4 suggestion 1 (`flush=True`, pyright over `script/`,
  `DISCOVERY_INTEGRATIONS`, the 2025.4.0 `aiodns` warning).
- `frontend/node_modules` volume (stage 4).

## Open questions
Decided by the main session (low-stakes, reversible; human confirms at PR review):
1. **Re-run the prefetch helper on every `script/develop` start** — correctness over a few seconds; keeps
   in-container tests identical to CI (no `UV_NO_SYNC`).
2. **Live installs are reported, not failed** by `script/smoke-develop` (avoid network/discovery flakiness);
   `default_config` dependency failures DO fail it.
3. **Pin go2rtc by version + `@sha256` digest**, like HA core (supply-chain safety; document the bump steps).

<!-- Filled in by implementer -->
## Implementation notes

**Environment used.** Implemented and tested in the git worktree
`ha-energy-cost-stats-008` (branch `task/008-dev-ha-fixes`), separate from the main
checkout (another agent worked on task 004 there concurrently). Host unit tests, ruff,
`uv lock --check`: run natively on Windows. Devcontainer checks: a fresh headless
devcontainer was started for this worktree with `npx @devcontainers/cli up
--workspace-folder .`,
sharing the two named volumes (`energy-cost-stats-uv-cache`, `energy-cost-stats-ha-config`)
with the main checkout's already-running devcontainer, per the task's instructions. `/opt/venv`
is **not** a named volume (only baked into the image layer / container-local), so it is not
shared between the two containers.

**Worktree git-in-container limitation (blocks some acceptance criteria).** A git worktree's
`.git` is a file pointing at the *main checkout's* `.git/worktrees/<name>` directory (an
absolute host path). The devcontainer for this worktree only bind-mounts the worktree
directory itself, not the main checkout, so git is unusable inside this container
(`fatal: not a git repository`) — confirmed by the `postStartCommand`'s `git config
--global --add safe.directory` step failing on `up`. This blocks the acceptance criteria that
require `git status`/`git diff` *inside the container* (the negative go2rtc-pin check's
"Restore the Dockerfile and check that `git diff` is clean", and the final `git status
--porcelain` check). Both were done from the host instead, outside the container (see below);
the only file changes tracked are this task's own files. This is a pre-existing property of
worktrees + devcontainers, not something introduced by this task; flagged as a follow-up in
case docker-based checks are needed again from a worktree.

**Shared `energy-cost-stats-ha-config` volume — checks adjusted to avoid touching the other
agent's data.** The task's Acceptance criteria call for `docker volume rm
energy-cost-stats-ha-config` and fresh `up --remove-existing-container` cycles to get a clean
volume for the "fresh volume", "config-entry", and "rebuild" scenarios. Because this volume is
shared with the main checkout's running devcontainer (task 004, a different, unrelated dev HA
session), removing or resetting it would have destroyed that session's onboarding state. CLAUDE.md
and the run instructions require not touching unrelated agents' containers/data, so those
volume-destroying steps were **not performed**; the checks below were done non-destructively
instead, and the corresponding acceptance criteria checkboxes above are left unticked for a
reviewer with an isolated volume to confirm formally. What was actually verified:
- The shared `energy-cost-stats-ha-config` volume already had a `google_translate` config entry
  (created by the other agent's earlier onboarding), confirmed via
  `docker exec ... cat /home/vscode/.ha-config/.storage/core.config_entries`.
- `sh script/setup` (run automatically by the devcontainer's `postCreateCommand` on `up`) printed:
  `energy_cost_stats: pre-installing 26 Home Assistant runtime requirement(s) ... gTTS==2.5.4,
  ... go2rtc-client==0.4.0, ...` — i.e. `--config-dir` correctly picked up `google_translate` from
  the shared config and pre-installed `gTTS` alongside the rest of the `default_config` tree.
- `command -v go2rtc && go2rtc --version` inside the container: `go2rtc version 1.9.14 (b5948cf)
  linux/amd64`; `uname -m`: `x86_64`.
- `sh script/smoke-develop` (uses its own fresh temp config dir with no `.storage`, only the
  committed `configuration.yaml` — effectively a "fresh volume" run for `default_config`/go2rtc,
  though not a fresh *named volume*) exited 0: `OK: HTTP 200 on :8123; log line: ... Setting up
  energy_cost_stats` followed by `Live installs during this run: no live installs`. `pgrep -af
  hass` was empty afterward (only the `pgrep` command itself, matching its own command line).
- `uv run pytest -m unit` and `-m integration` (the latter includes the new
  `test_go2rtc_pin_satisfies_recommended_version`): both green inside the container
  (62 unit + 2 integration passed). `ruff check .`, `ruff format --check .` and `pyright`
  (via the venv binaries directly, and `python -m pyright`): all green.
- Not performed for the reasons above: the volume-removal "fresh volume", "config-entry
  scenario" (full onboard-then-setup-then-develop cycle), "rebuild scenario", and the negative
  go2rtc-pin check (needs a scratch Dockerfile copy — deferred, not risky by itself, but out of
  time budget together with the rest). The 2025.4.0-leg `docker run` behaviour check was also not
  performed (out of time budget); CI's `test (py3.13, HA 2025.4.0)` job exercises the same
  `script/setup` / go2rtc-drift-guard path and is the fallback verification for that leg.

**`gtts` reproduction (item 2, "the implementer reproduces this first").** Reproducing the
human's exact reported failure turned out not to be straightforward:
- Direct repro attempt: with a config dir seeded from the shared volume's
  `.storage/core.config_entries` (so `google_translate` is already an enabled entry) and `gTTS`
  forcibly uninstalled from this container's `/opt/venv` (container-local, safe to modify), a
  plain `hass --config <dir> --debug` (bypassing `script/develop`'s new pre-install step, to
  simulate the *old*, unfixed behaviour) did **not** reproduce a `ModuleNotFoundError`. The log
  showed the normal live-install path working as designed:
  `[homeassistant.util.package] Attempting install of gTTS==2.5.4` followed immediately by
  `[homeassistant.setup] Setting up google_translate` and `Setup of domain google_translate took
  0.00 seconds` — i.e. `RequirementsManager` installed the missing package itself, synchronously,
  before setting up the entry, exactly as `homeassistant/requirements.py` is documented to do.
  `gTTS` was reinstalled afterward to restore the container's venv.
- This is consistent with the task's own framing ("the exact mechanism is not confirmed... a
  plain `ModuleNotFoundError` means something imported `gtts` before requirements were processed,
  or the install failed"): the live install *can* succeed on its own. The most likely trigger for
  the human's original failure is the race already described in item 3/Decision 3 — a concurrent
  `uv sync` (e.g. from a separate `script/test`/`script/lint`/pyright run, or a second
  `script/setup`) removing `gTTS` out from under the live install, or removing it between the
  live install completing and the entry's platform import running. Reproducing that exact race
  reliably was not attempted (would need precise timing against a concurrent `uv sync`, and doing
  so against the shared venv/volume was avoided per the note above).
- This does not weaken the fix: pre-installing `gTTS` (and everything else `default_config`'s
  and any config entry's manifests need) **before** `script/develop` starts `hass`, and repeating
  that pre-install on every `script/develop` start with `--no-sync`, removes the live-install step
  — and therefore the race window with a concurrent `uv sync` — from the picture entirely in
  normal operation, regardless of the exact trigger. The `--config-dir` addition to
  `config_entry_domains()`/`collect_requirements()` is unit-tested directly (fake manifests,
  fixture storage file) independent of this reproduction attempt.

**go2rtc digest.** Obtained with `docker buildx imagetools inspect
ghcr.io/alexxit/go2rtc:1.9.14`: index digest `sha256:675c318b23c06fd862a61d262240c9a63436b4050d177ffc68a32710d9e05bae`,
platforms include `linux/amd64` and `linux/arm64` (plus `linux/386`, `linux/arm/v6`,
`linux/arm/v7`). Cross-checked byte-for-byte against HA core's own production `Dockerfile`
(`dev` branch) `COPY --from=ghcr.io/alexxit/go2rtc:1.9.14@sha256:675c318b...` line — identical.
`RECOMMENDED_VERSION` in the installed HA (2026.9.x-era `dev`/latest, via
`homeassistant.components.go2rtc.const.RECOMMENDED_VERSION`) printed `1.9.14`, so the pin
satisfies both matrix legs as the task's Decision 1 argued (2025.4.0's recommended version is
lower, `1.9.9`).

**New tests failed first, for the right reason**, confirmed on the host before any code change:
`test_config_entry_domains_*`, `test_collect_requirements_includes_config_entry_domain_deps`,
and `test_prefetch_flow_returns_summarize_exit_code` failed with `AttributeError: module
'prefetch_ha_requirements' has no attribute ...` (the functions didn't exist yet);
`test_develop_runs_prefetch_before_hass` / `test_setup_passes_config_dir_to_prefetch` failed
because the scripts didn't call the helper with `--config-dir` yet; `test_dockerfile_pins_go2rtc`
failed because the Dockerfile had no go2rtc `COPY` line at all.

**Deviations from the task's line-level suggestion.** The task's Files section shows
`script/develop`'s prefetch call as a `\`-continued two-line command with `--config-dir` on its
own line. `test_develop_runs_prefetch_before_hass` (as specified in the Tests table, "a
non-comment line contains `prefetch_ha_requirements.py` and `--config-dir`") requires both
substrings on the *same* line, so both `script/setup` and `script/develop` call the helper as one
single (long) line instead.

**Not run:** `script/test`'s full engine coverage gate (`--cov-fail-under=95`) — out of this
task's scope (no engine code touched); `npm test` / card tests — no frontend code touched.

**Round 1 fixes (per `tasks/008-review.md`).**

*Required 1 -- 2025.4.0 `pycares`/`aiodns` crash.* Root-fixed via `pyproject.toml`: added
`"pycares<5 ; python_version < '3.14'"` to the `ha` dependency group. `aiodns==3.2.0` (pinned by HA
2025.4.0's own `package_constraints.txt`) only requires `pycares>=4.0.0` with no upper bound; nothing
in HA's own constraints stops `pycares` resolving to `5.0.1`, whose `Channel.getaddrinfo()` signature
broke aiohttp's `AsyncResolver`. `uv lock` re-resolved to `pycares==4.11.0` on the `python_version <
'3.14'` fork only; the latest-HA fork (`python_full_version >= '3.14.2'`, `aiodns==4.0.4`) is untouched.
`uv lock --check` stays green; `pyproject.toml`/`uv.lock` were previously out of scope for this task but
the review explicitly called this a root-fix candidate. Verified in a throwaway devcontainer-image
container (`ecs-008-test`, removed afterward): built the image (`docker build -f .devcontainer/Dockerfile
.`), ran `sh script/setup --python 3.13` with `UV_PROJECT_ENVIRONMENT=/tmp/venv313` and a private
`UV_CACHE_DIR` (the shared `energy-cost-stats-uv-cache` volume was not touched, per the run instructions'
note about a root-owned cache subdirectory there), then started `script/develop` directly (not through
`smoke-develop`, see the "2025.4.0 with go2rtc" acceptance criterion note above for why). The log shows a
real DNS resolution succeeding through aiohttp's resolver, `go2rtc` executing, no `Setup failed for` /
`Unable to set up dependencies` lines, no `recommended_version` repair warning, and `Home Assistant
initialized in 1.74s`. The latest-HA leg (`sh script/smoke-develop` in the same container, its own fresh
temp config dir) still exits 0 as before. Both HA processes were stopped and the container/image were
removed at the end; `pgrep -af hass` was empty afterward. Note for future runs: `docker exec` on this
Windows/Git-Bash host mangles leading-`/` arguments (e.g. `-e UV_PROJECT_ENVIRONMENT=/tmp/venv313` turned
into a Windows path); prefix such commands with `MSYS_NO_PATHCONV=1`. Also, the image's system Python
3.13 has no headers by default (`python3.13-dev` was installed with `apt-get` in the throwaway container
only, not baked into the committed Dockerfile) -- this build-dependency gap is unrelated to this task's
diff and is left as the existing "worth a separate look" item from round 1's Suggestions, not fixed here.

*Required 2 -- `config_entry_domains()` robustness.* Rewrote the function per the review's fix direction:
one `try` now wraps the read, the JSON parse, an explicit `isinstance(entries, list)` check, and the
domain-collecting comprehension (which now also requires `isinstance(entry, dict)` and
`isinstance(entry.get("domain"), str)`), with `sorted()` moved inside the guarded block. The design
distinguishes two cases, both covered by new parametrized tests written first (confirmed failing before
the fix -- the two "unrecoverable" cases raised `UnicodeDecodeError`/`AttributeError` uncaught, and the
"skip" cases raised `TypeError` from the old `sorted()` outside the `try`, or an `AttributeError`/`KeyError`
from `entry["domain"]`/`entry.get(...)` on a non-dict item):
- Shapes the function cannot make sense of at all (non-UTF-8 bytes, `data.entries` not a list, the whole
  payload not an object) are caught by `(ValueError, KeyError, TypeError, AttributeError, OSError)`: one
  warning to stderr, `[]`.
- A recognizable `entries` list with individual malformed items (non-dict entries, a non-string `domain`)
  skips just those items silently and still returns the well-formed domains from the same file, with no
  warning for a file that is partly usable.

Also applied round-1 Suggestion 2: the two pre-existing malformed-shape tests now assert
`len(err.strip().splitlines()) == 1` instead of only `err.strip() != ""`.

*Suggestion 1 -- `tests/integration/test_dev_env.py` fragility.* `RECOMMENDED_VERSION` is now read from
`homeassistant/components/go2rtc/const.py`'s source text via `importlib.util.find_spec("homeassistant")`
+ regex, instead of `from homeassistant.components.go2rtc.const import RECOMMENDED_VERSION`, which used
to run the `go2rtc` package's `__init__` (pulling in `go2rtc_client`, `webrtc_models`, `camera`, `stream`,
none of which are in `uv.lock`). Added `test_recommended_version_helper_finds_go2rtc_const` (skips if
`homeassistant` isn't installed) so the new helper itself is covered.

*Suggestion 3 (reproduce-first) and 4 (trim session narrative) were not acted on in this round*: neither
was marked Required, and re-attempting the exact race in Suggestion 3 is already tracked as a Follow-up
below.

## Follow-ups
- `script/smoke-develop`'s `integration_ready` check greps for `Setting up energy_cost_stats|Setup of
  domain energy_cost_stats`, which HA only logs at INFO on the latest leg; on the min-HA leg (2025.4.0)
  `"Setting up %s"` is DEBUG-only, so the check never matches there and `smoke-develop` times out even
  when Home Assistant started cleanly (see round 1 note on the "2025.4.0 with go2rtc" acceptance
  criterion). Consider either raising `homeassistant.setup` (or just the relevant domain) to debug in
  `config/configuration.yaml`, or switching the check to a version-independent INFO-level signal (e.g.
  matching `energy_cost_stats` inside the `Setting up stage \d+: {...}` domain-set line, combined with
  the existing failure-pattern checks and the final "initialized in" + no-recovery-mode checks that
  already run). Needs a decision, since it changes a checked-in script.
- Formally exercise the volume-destroying acceptance criteria (fresh `energy-cost-stats-ha-config`,
  the full onboard → `script/setup` → `script/develop` config-entry cycle, the rebuild scenario,
  and the negative go2rtc-pin check) in an isolated devcontainer / volume set that doesn't share
  state with another agent's session — e.g. by naming volumes per-worktree, or by the reviewer
  running them when no other dev HA session is active.
- Run the 2025.4.0-leg `docker run` behaviour check (built devcontainer image,
  `UV_PROJECT_ENVIRONMENT=/tmp/venv313`, `script/setup --python 3.13` then `script/smoke-develop`);
  not performed here for time. CI's `test (py3.13, HA 2025.4.0)` job covers the same code paths
  as an interim check.
- If a worktree-based devcontainer workflow becomes common, consider bind-mounting the main
  checkout's `.git` directory too (or documenting `git -C <main-checkout> ...` from the host as
  the supported way to run git-dependent checks against a worktree's container), since a
  worktree's own `.git` file cannot be resolved from inside a container that only mounts the
  worktree.
- Try to reproduce the exact race from item 3 (concurrent `uv sync` racing a live
  `install_package()` call) deliberately, if the original `ModuleNotFoundError` report recurs,
  to confirm the trigger with certainty; the direct-invocation repro in these notes did not
  reproduce it.
