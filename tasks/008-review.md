# 008 — Review (round 2)

Verdict: APPROVE

Scope reviewed: the working-tree diff against `HEAD` on `task/008-dev-ha-fixes`, plus the untracked files
(`tasks/008-dev-ha-fixes.md`, `tests/fixtures/ha_storage/core.config_entries`,
`tests/integration/test_dev_env.py`). Since round 1, `pyproject.toml` and `uv.lock` have also changed. This is
fix direction (a) of round-1 Required 1, and the task file records it as a deviation. `ci.yml` and
`ha-latest-canary.yml` are unchanged.

Container checks ran in one-off containers. They used the image built from this branch's
`.devcontainer/Dockerfile` (it contains `go2rtc 1.9.14`) and `ghcr.io/astral-sh/uv:python3.13-trixie`. The
worktree was mounted read-only and copied into the container. Each container had a private `UV_CACHE_DIR`
under `/tmp` and a private `HA_CONFIG_DIR` under `/tmp`. No shared named volume was mounted. All review
containers were removed afterwards.

## Round-1 required items
1. **Resolved.** `pycares<5 ; python_version < '3.14'` was added to the `ha` group.
   - Lock fork. `uv export --frozen --all-groups` for `HEAD` and for the worktree differ in one line only:
     `pycares==5.0.1 ; python_full_version < '3.14' or >= '3.14.2'` becomes
     `pycares==4.11.0 ; python_full_version < '3.14'` plus `pycares==5.0.1 ; python_full_version >= '3.14.2'`.
     The latest-HA leg resolves exactly as before. In the container it runs HA `2026.9.3` with aiodns `4.0.4`
     and pycares `5.0.1`.
   - HA 2025.4.0's own constraints. Its `package_constraints.txt` pins `aiodns==3.2.0` and says nothing about
     pycares. aiodns 3.2.0 only requires `pycares>=4.0.0`, so `4.11.0` is consistent with both. The lock has
     a cp313 manylinux x86_64/aarch64 wheel for it.
   - Devcontainer image, py3.13 / HA 2025.4.0. This run used `UV_PYTHON_PREFERENCE=only-managed`; see
     Suggestion 4 for why. `script/setup --python 3.13` → rc 0, versions `3.13.15 2025.4.0 aiodns 3.2.0
     pycares 4.11.0`. aiohttp's `AsyncResolver().resolve("pypi.org")` succeeds, so the `getaddrinfo`
     `TypeError` is gone. A direct `script/develop` run shows `execute program '/usr/bin/go2rtc'` and
     `Home Assistant initialized in 1.58s`, with no `Setup failed`, no `Unable to set up`, no `TypeError` and
     no `recommended_version` repair.
   - `script/smoke-develop` on this leg → rc 1 with `No log line showing energy_cost_stats was set up`.
     None of the fatal patterns fired, including the new `default_config` pattern. The cause is the one
     recorded in the Follow-up: in 2025.4.0 `homeassistant/setup.py:390` logs `"Setting up %s"` at `debug`.
     See the assessment below.
   - `script/test` on the same leg (`UV_PYTHON=3.13`) → `71 passed`, coverage 100%.
     `uv run --group ha pyright` → `0 errors`. `pytest -m integration` → `3 passed`.
   - Latest-HA leg in the same image (fresh venv): `script/setup` → rc 0. `script/smoke-develop` → rc 0 with
     `OK: HTTP 200 on :8123; log line: … Setting up energy_cost_stats` and
     `Live installs during this run: no live installs`. No `hass` was left running. `script/test` →
     `71 passed`. pyright → `0 errors`.
2. **Resolved.** `config_entry_domains()` now wraps the read, the parse, the `entries` type check, the
   comprehension and `sorted()` in one `try` that catches
   `(ValueError, KeyError, TypeError, AttributeError, OSError)`. Entries must be `dict` and have a `str` domain.
   - Tests cover non-UTF-8 bytes, `entries` as an object, a non-object top level, invalid JSON and a missing
     `data.entries`. Each returns `[]` and prints exactly one warning line. Tests also cover non-object
     entries, a `null` domain next to a string domain, and a non-string domain. These skip the bad entries
     and print no warning.
   - Extra host probe with shapes the tests do not cover (`null`, `"s"`, `{"data": null}`, `{"data": []}`, a
     list domain, an empty file, a directory named `core.config_entries`): each returns `[]`. Disabled
     entries are excluded. The only shape that still raises is pathological nesting (Suggestion 3).
   - Mutations, each run on a scratch copy of the script with the repo untouched:
     - removing `isinstance(entry, dict)` → `[entries_non_objects]` fails
     - narrowing `ValueError` to `json.JSONDecodeError` → `[non_utf8_bytes]` fails
     - removing the `str` domain check → `[null_domain_next_to_string_domain]` and `[non_string_domain]` fail

## Follow-up on the smoke log level: assessment
It is acceptable as a follow-up and does not undermine the smoke check:
- The smoke check targets the devcontainer's default leg (latest HA, Python 3.14), and it is fully effective
  there.
- The fatal patterns (`default_config`, recovery mode, `energy_cost_stats` failures) are
  version-independent. They ran on every poll on the 2025.4.0 leg, and none fired.
- The failure mode is a timeout, not a false OK. A clean 2025.4.0 run shows up red, never a broken one as
  green.
- The behaviour the criterion targets was verified directly above: go2rtc and `default_config` set up on
  2025.4.0 with the pinned binary.
- The min-HA leg in the devcontainer is not a smooth workflow yet for other, pre-existing reasons
  (Suggestion 4). Neither CI nor any documented workflow runs smoke on 2025.4.0.
- The fix is small but it changes the checked-in dev config or the script's success signal. That needs a
  decision, as the Follow-up says.

The acceptance criterion "2025.4.0 with go2rtc" is still `[ ]`. The task text allows "if this is blocked,
record why", and the reason is recorded, so I treat it as satisfied by record. The human should acknowledge
it at merge (Suggestion 1).

## Checks run
Host (Windows):
- `uv run pytest -m unit` → `68 passed in 0.38s`
- `uv run ruff check .` → `All checks passed!`; `uv run ruff format --check .` → `29 files already formatted`
- `uv lock --check` → `Resolved 230 packages in 2ms`

CI `test` job, py3.13 leg, simulated in `ghcr.io/astral-sh/uv:python3.13-trixie` with `UV_PYTHON=3.13` and
the steps from `ci.yml`:
- `uv lock --check` → `Resolved 230 packages`
- `sh script/setup` → rc 0; pre-installed 18 requirements
- HA version assert → `2025.4.0`, with pycares `4.11.0` and aiodns `3.2.0`
- `uv run --group ha pyright` → `0 errors, 0 warnings, 0 informations`
- `sh script/test` → `71 passed`, `Total coverage: 100.00%`. pycares stays `4.11.0` after the syncing
  `uv run`.

Devcontainer image, both legs: see Required 1 above.

## Acceptance criteria
Most of these were verified independently in round 1. That still holds, because round 2 did not change the
code paths involved. The main session should tick the boxes the implementer left open (`:latest` mutation,
go2rtc version/arch, fresh config, config-entry, rebuild, revert, negative check, porcelain), citing
round 1.
- [x] Unit tests pass, including the new ones. Mutations confirm the new tests bite.
- [x] ruff / format / `uv lock --check` clean.
- [x] `:latest` makes `test_dockerfile_pins_go2rtc` fail (round 1).
- [x] go2rtc 1.9.14 on x86_64. Fresh config, config-entry, rebuild and revert scenarios; smoke on latest HA;
  negative check (round 1, and the latest-HA smoke again in round 2).
- [x] 2025.4.0 with go2rtc. Behaviour verified: go2rtc and `default_config` set up, no aiodns crash. The
  smoke timeout is recorded as a Follow-up (see the assessment).
- [x] Only the intended files are changed or untracked in git (`git status`). See Suggestion 2 for an
  ignored leftover.
- [x] CI workflows unchanged. The CI py3.13 leg is green with the new lock (simulated above).
- [x] Hygiene: no local paths, IPs, tokens or real entity ids in the diff or the new files.
- [x] CLAUDE.md updated: the `develop` re-run and the `pycares<5` pin note under "Bumping latest HA".

## Findings
### Required
None.

### Suggestions
1. `tasks/008-dev-ha-fixes.md:254`: the "2025.4.0 with go2rtc" criterion is still `[ ]`. Before merge, get
   the human to acknowledge that the smoke log-level gap is deferred. Then either tick the box with a pointer
   to the Follow-up, or reword the criterion. The Follow-up's preferred fix is to match `energy_cost_stats`
   in the INFO-level `Setting up stage 2: {...}` line. This avoids raising `homeassistant.setup` to debug
   for everyone.
2. The worktree root contains an untracked `C:` directory (shown by git as `"C\357\200\272/"`). It holds a
   `C:/Users/<user>/AppData/Local/Temp/uv-cache-313` uv cache and a `venv313`. A `docker exec` from an
   earlier session mangled a path argument and created it. Git ignores it only because uv writes a
   `.gitignore` containing `*` inside those directories. Delete it from the host before any broad
   `git add` or cleanup, because the path names contain the local user name.
3. `script/prefetch_ha_requirements.py:90-111`: deeply nested JSON (for example 100k `[`) raises
   `RecursionError`, which the `except` tuple does not catch. Home Assistant never writes such a file, so
   this is negligible. If full "never breaks setup" coverage is wanted, add `RecursionError`.
4. Min-HA leg inside the devcontainer (pre-existing, not caused by this diff). On a fresh uv cache,
   `script/setup --python 3.13` picks the image's system `/usr/bin/python3.13`, which has no `Python.h`. The
   run then fails building `ciso8601` (rc 1). `UV_PYTHON_PREFERENCE=only-managed` works around it. Also,
   `script/develop` on that venv warns `Using incompatible environment … due to --no-sync` because
   `.python-version` says 3.14. Worth one follow-up that makes the 3.13 devcontainer leg a documented
   workflow, together with the smoke log-level item.
5. `script/smoke-develop`: the post-loop re-scan (line ~135) checks only `Activating recovery mode`. The
   `default_config` failure pattern is checked only at the top of each poll, before the `initialized in`
   check. A failure line written between those two greps in the final poll would be missed. Adding the
   `default_config` pattern to the post-loop re-scan closes that window cheaply.
6. The Implementation notes still contain a `containerId` hash and the "another agent" narrative
   (`tasks/008-dev-ha-fixes.md:308-311`). This repeats round-1 Suggestion 4: trim them to the facts that
   matter for a public file.
