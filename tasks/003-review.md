# 003 — Review (round 1)

Verdict: APPROVE

Scope reviewed: working-tree diff vs `HEAD` (`CLAUDE.md`, `README.md`, `docs/SPEC.md`, `pyproject.toml`, `uv.lock`)
plus untracked `.github/` (3 workflows, `dependabot.yml`, `rulesets/master.json`), `tests/unit/test_ci_config.py`,
`tasks/003-ci.md`.

## Checks run
- `docker run --rm -v "<repo>:/repo" --workdir /repo rhysd/actionlint:latest -color` (actionlint 1.7.12) → exit 0, no findings.
- `uv lock --check` → `Resolved 229 packages`, exit 0.
- `uv run pytest -m unit` (Windows native) → `29 passed`.
- `uv run pytest -m integration` (Windows native) → `29 deselected`, exit code 5 (Windows guard unchanged).
- `uv run ruff check .` → `All checks passed!`; `uv run ruff format --check .` → `20 files already formatted`.
- The `test` job steps run in one-off containers (`UV_PROJECT_ENVIRONMENT=/opt/venv UV_LINK_MODE=copy UV_LOCKED=1
  UV_PYTHON_PREFERENCE=only-managed`, repo mounted at `/repo`, same `bash -eo pipefail` shell as GitHub):
  - `ghcr.io/astral-sh/uv:python3.13-trixie`, `UV_PYTHON=3.13`, matrix.ha `2025.4.0`: `sh script/setup` OK →
    Assert HA version `Home Assistant version: 2025.4.0` (CPython 3.13.15) → pyright `0 errors, 0 warnings,
    0 informations` → `sh script/test` `30 passed`, `Required test coverage of 95% reached. Total coverage: 100.00%`.
  - `ghcr.io/astral-sh/uv:python3.14-trixie`, `UV_PYTHON=3.14`, matrix.ha `latest`: setup OK → `Home Assistant
    version: 2026.9.3` (CPython 3.14.7, managed) → pyright `0 errors` → `script/test` `30 passed`, coverage 100.00%.
- Silent-green guard:
  - `bash --noprofile --norc -eo pipefail -c 'version="$(python3 -c "import nonexistent")"; echo reached'` → exit 1,
    so an import failure in the assignment aborts the step.
  - `UV_PYTHON=3.14.0 uv sync --group ha` (UV_LOCKED) → `error: The current Python platform is not compatible with
    the lockfile's supported environments`, so the 3.14.0/3.14.1 gap fails loudly, not silently.
- Action pins verified with `git ls-remote`: `actions/checkout` `refs/tags/v7.0.1` = `3d3c42e5aac5ba805825da76410c181273ba90b1`
  (latest v7), `astral-sh/setup-uv` `refs/tags/v10.2.0` = `c18668ad3cf93ea998bef934396af7bb5c839dc7` (latest v10).
  Both are lightweight tags, so the SHA is the commit. `hacs/action` `action.yml` (read-only `gh api`) has inputs
  `category`, `ignore`, `comment`, `github_token` (default `${{ github.token }}`). `hassfest` is a composite that
  runs `docker run ... ghcr.io/home-assistant/hassfest`.
- Mutation checks, run on a temp copy of `.github/` + the test file (the worktree was not touched):
  - baseline → `15 passed`.
  - `actions/checkout@v7` → `test_actions_pinned_by_sha` FAILED.
  - job `name: lint` → `ruff` → `test_ruleset_contexts_match_job_names` FAILED.
  - removing a `timeout-minutes` → `test_workflows_parse_and_are_safe` FAILED.
  - adding `pull_request_target` → `test_workflows_parse_and_are_safe` FAILED.
  - `ignore: brands images` → `test_hacs_ignores_only_brands` FAILED.
  - matrix `ha: "2025.4.1"` → `test_test_matrix_pairs_python_with_ha` + `test_ruleset_contexts_match_job_names` FAILED.
  - removing `UV_LOCKED` → `test_test_job_runs_gate_and_asserts_ha_version` FAILED.
- Hygiene grep of all changed/new files (drive paths, `/Users/`, `/home/`, IPv4, `ghp_`/`github_pat_`, `token:`,
  `secret`, entity-id patterns, user name) → only pre-existing policy text in `CLAUDE.md` and the task's
  "no secrets beyond `GITHUB_TOKEN`" sentence. No hits in the new files.
- `docker ps` after the run: none of my containers (`rev003-*`) left running.

## Acceptance criteria
Local:
- [x] actionlint → exit 0, no findings. Verified by the run above.
- [x] `uv lock --check` → exit 0. Verified.
- [x] `uv run pytest -m unit` → all pass (29, including the 15 `test_ci_config.py` cases). Verified.
- [x] `uv run pytest -m integration` → exit code 5. Verified.
- [x] `ruff check` / `ruff format --check` → exit 0. Verified.
- [x] 3.13 container: setup, HA `2025.4.0`, pyright 0 errors, `script/test` green. Verified independently.
- [x] 3.14 container: setup, HA `2026.9.3` (locked latest), pyright 0 errors, `script/test` green. Verified independently.
- [x] Mutation checks (`checkout@v7`, `lint`→`ruff`) fail the intended tests. Verified on a scratch copy, plus 5 extra mutations.
- [x] Hygiene: no local paths, IPs, tokens or real entity ids. Docker examples use `${PWD}` (CLAUDE.md) and
      `<repo>` (task file). Verified by grep.
- [x] `hacs` job has the inline `brands` comment (`validate.yml:40-41`). `ci.yml:88` has the card-job comment. Verified.

After the PR is opened (pending, for the main session):
- [ ] All six required checks green on the PR head. The step summaries show `2025.4.0` / the locked latest. **Pending.**
- [ ] setup-uv cache hit on the second run. **Pending.**
- [ ] Canary run once via `gh workflow run` (ask first). Result noted. **Pending.**
- [ ] M1 (repo description/topics for HACS `description`/`topics` checks), M2 (check-run names and app id `15368`,
      then apply the ruleset), M3 (`rules/branches/master`). **Pending, need human approval.**
- [ ] README badge renders. Dependabot config accepted. hassfest and HACS results. **Pending.**

## Principles and design
- Least privilege: all three workflows set top-level `permissions: contents: read`. No `pull_request_target`.
  No secrets: `hacs/action` uses its default `github.token`, and `comment: "false"` means no write scope is needed.
- Pinning: the only unpinned refs are the two allowlisted validation actions. Each has a reason comment
  (`validate.yml:26-27`, `36`).
- Required-check names: the rendered job names (`lint`, `unit (windows, no HA)`, `test (py3.13, HA 2025.4.0)`,
  `test (py3.14, HA latest)`, `hassfest`, `hacs`) match `.github/rulesets/master.json` exactly. The ruleset
  matches the task body verbatim: squash-only, no bypass actors, strict policy (Open questions 1 and 3).
- `UV_LOCKED` is set in `ci.yml` only, not in the canary. `UV_PYTHON_PREFERENCE: only-managed` is set in both.
  Timeouts are 20/30. Concurrency is on ci/validate.
- Windows pwsh guard: the explicit `exit 0` / `exit 1` overrides the runner's trailing `exit $LASTEXITCODE`. Correct.
- Scope: the CLAUDE.md "Light path" rewrite and the SPEC §6 fix are both explicitly requested (Open question 3 and
  the "Extra scope" note). CLAUDE.md edits stay inside Commands (one row), Git & GitHub and Agent workflow.
  README only adds the badge. `pyyaml>=6` is in `dev`. `types-PyYAML` is not needed (pyright 0 errors on both legs).

## Findings
### Required
None.

### Suggestions
1. `docs/SPEC.md:66-67`: "(3.14.0/3.14.1 fall in the gap between the two markers and resolve the `ha` group to
   nothing)" reads as if the gap still resolves silently. With `[tool.uv] environments`, uv actually **refuses**:
   `uv sync --group ha` on CPython 3.14.0 fails with "not compatible with the lockfile's supported environments"
   (verified above). The `pyproject.toml` comment already says "refuse to run". Suggested wording: "…restricts
   resolution to that same split, so `uv sync` refuses to run on 3.14.0/3.14.1 (which would otherwise match
   neither marker and install no Home Assistant)".
2. `tests/unit/test_ci_config.py:176-178` (`_render_job_names`): jobs without `name:` are skipped. GitHub then uses
   the job id as the check context, so a future required job added without `name:` would not be caught. Fall back
   to the job id (`name = job.get("name", job_id)`).
3. `.github/workflows/ci.yml:81`: the `latest` leg only proves that HA imports. Optionally also compare the version
   with the `homeassistant` version locked for the 3.14 fork in `uv.lock`. That turns "some HA" into "the HA we
   locked", which the step summary shows today only for a human to read.
4. `tasks/003-ci.md:3`: `Status: planned` should move to `in-review` (lifecycle in `tasks/README.md`). The main
   session can do this when it commits.
5. Worth a CLAUDE.md or follow-up note: GitHub disables `schedule` triggers after 60 days without repository
   activity, so the weekly canary and the weekly validate run can silently stop during a quiet period.
   Re-enable them from the Actions tab if that happens.
