"""Tests for the CI configuration: workflows, ruleset, dependabot, README badge.

See tasks/003-ci.md "Tests to write first". PyYAML parses the bare key `on` as boolean
``True``, so triggers are read via ``wf.get("on", wf.get(True))``.
"""

import json
import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[2]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
RULESET_PATH = REPO_ROOT / ".github" / "rulesets" / "master.json"
DEPENDABOT_PATH = REPO_ROOT / ".github" / "dependabot.yml"
README_PATH = REPO_ROOT / "README.md"
HACS_JSON_PATH = REPO_ROOT / "hacs.json"

# Actions whose ref is intentionally a floating branch, not a SHA (see tasks/003-ci.md
# decision 3: their images float anyway; validation must track upstream rules).
UNPINNED_ALLOWLIST = {
    "hacs/action@main",
    "home-assistant/actions/hassfest@master",
}

SHA_PIN_RE = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}\s+#\s*v\d+(\.\d+){0,2}$")

USES_LINE_RE = re.compile(r"^\s*uses:\s*(\S+)\s*(#.*)?$", re.MULTILINE)


def _load_workflows() -> dict[str, dict]:
    workflows = {}
    for path in sorted(WORKFLOWS_DIR.glob("*.yml")):
        with path.open(encoding="utf-8") as f:
            workflows[path.name] = yaml.safe_load(f)
    return workflows


def _triggers(wf: dict):
    return wf.get("on", wf.get(True))


def _is_pinned(uses_line: str) -> bool:
    """Check a raw `uses:` value (without the `uses:` prefix and trailing comment)."""
    if uses_line in UNPINNED_ALLOWLIST:
        return True
    return bool(SHA_PIN_RE.match(uses_line))


def test_workflows_parse_and_are_safe():
    workflows = _load_workflows()
    assert len(workflows) >= 3, "expected at least 3 workflow files"

    for name, wf in workflows.items():
        assert wf is not None, f"{name} failed to parse"
        assert "permissions" in wf, f"{name} is missing top-level permissions"

        triggers = _triggers(wf)
        assert triggers is not None, f"{name} has no triggers"
        assert "pull_request_target" not in triggers, (
            f"{name} must not use pull_request_target"
        )

        jobs = wf.get("jobs", {})
        assert jobs, f"{name} has no jobs"
        for job_id, job in jobs.items():
            assert "timeout-minutes" in job, (
                f"{name}: job {job_id} is missing timeout-minutes"
            )


def _iter_uses_lines():
    for path in sorted(WORKFLOWS_DIR.glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("uses:") or stripped.startswith("- uses:"):
                value = stripped.split("uses:", 1)[1].strip()
                yield path.name, value


def test_actions_pinned_by_sha():
    lines = list(_iter_uses_lines())
    assert lines, "no uses: lines found in workflows"
    for filename, value in lines:
        assert _is_pinned(value), f"{filename}: unpinned/unsafe uses line: {value!r}"


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("actions/checkout@v7", False),
        ("hacs/action@main", True),
        ("home-assistant/actions/hassfest@master", True),
        ("some-org/some-action@main", False),
        (
            "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
            False,
        ),
        (
            "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1",
            True,
        ),
    ],
)
def test_pin_checker_rejects_unpinned_and_accepts_sha_with_comment(line, expected):
    assert _is_pinned(line) is expected


def _ci_workflow() -> dict:
    with (WORKFLOWS_DIR / "ci.yml").open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _hacs_json() -> dict:
    with HACS_JSON_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def test_test_matrix_pairs_python_with_ha():
    ci = _ci_workflow()
    test_job = ci["jobs"]["test"]
    strategy = test_job["strategy"]
    assert strategy["fail-fast"] is False

    include = strategy["matrix"]["include"]
    assert include == [
        {"python": "3.13", "ha": "2025.4.0"},
        {"python": "3.14", "ha": "latest"},
    ]

    hacs = _hacs_json()
    min_entry = next(e for e in include if e["ha"] != "latest")
    assert min_entry["ha"] == hacs["homeassistant"]


def test_test_job_runs_gate_and_asserts_ha_version():
    ci = _ci_workflow()
    test_job = ci["jobs"]["test"]
    steps = test_job["steps"]
    run_lines = "\n".join(s.get("run", "") for s in steps)

    assert "script/setup" in run_lines
    assert "pyright" in run_lines
    assert "script/test" in run_lines

    ha_version_step = next(
        (
            s
            for s in steps
            if "homeassistant.const" in s.get("run", "")
            and "matrix.ha" in s.get("run", "")
        ),
        None,
    )
    assert ha_version_step is not None, (
        "no step asserting the HA version against matrix.ha"
    )

    env = {**ci.get("env", {}), **test_job.get("env", {})}
    assert env.get("UV_LOCKED") in ("1", 1, True, "true"), (
        "UV_LOCKED must be set for ci.yml/test"
    )
    assert env.get("UV_PYTHON_PREFERENCE") == "only-managed"


def _render_job_names(workflows: dict[str, dict]) -> set[str]:
    """Render every job `name:` across the workflows, substituting matrix values."""
    rendered = set()
    matrix_expr_re = re.compile(r"\$\{\{\s*matrix\.(\w+)\s*\}\}")

    for wf in workflows.values():
        for job in wf.get("jobs", {}).values():
            name = job.get("name")
            if not name:
                continue
            strategy = job.get("strategy")
            matrix = (strategy or {}).get("matrix", {})
            include = matrix.get("include")
            if include:
                for entry in include:

                    def _sub(m, entry=entry):
                        return str(entry.get(m.group(1), m.group(0)))

                    rendered.add(matrix_expr_re.sub(_sub, name))
            else:
                rendered.add(name)
    return rendered


def _canary_job_names(workflows: dict[str, dict]) -> set[str]:
    names = set()
    canary = workflows.get("ha-latest-canary.yml")
    if canary:
        for job in canary.get("jobs", {}).values():
            name = job.get("name")
            if name:
                names.add(name)
    return names


def test_ruleset_contexts_match_job_names():
    workflows = _load_workflows()
    rendered = _render_job_names(workflows)
    canary_names = _canary_job_names(workflows)
    non_canary_rendered = rendered - canary_names

    with RULESET_PATH.open(encoding="utf-8") as f:
        ruleset = json.load(f)

    required_checks = next(
        rule["parameters"]["required_status_checks"]
        for rule in ruleset["rules"]
        if rule["type"] == "required_status_checks"
    )
    contexts = {c["context"] for c in required_checks}

    for context in contexts:
        assert context in rendered, (
            f"ruleset context {context!r} not produced by any job"
        )

    assert contexts == non_canary_rendered, (
        "required checks must exactly match the non-canary rendered job names"
    )


def test_ruleset_protects_default_branch():
    with RULESET_PATH.open(encoding="utf-8") as f:
        ruleset = json.load(f)

    assert ruleset["target"] == "branch"
    assert ruleset["enforcement"] == "active"
    assert ruleset["conditions"]["ref_name"]["include"] == ["~DEFAULT_BRANCH"]

    rule_types = {rule["type"] for rule in ruleset["rules"]}
    assert rule_types >= {
        "deletion",
        "non_fast_forward",
        "pull_request",
        "required_status_checks",
    }

    required_checks_rule = next(
        rule for rule in ruleset["rules"] if rule["type"] == "required_status_checks"
    )
    assert (
        required_checks_rule["parameters"]["strict_required_status_checks_policy"]
        is True
    )


def test_hacs_ignores_only_brands():
    with (WORKFLOWS_DIR / "validate.yml").open(encoding="utf-8") as f:
        validate = yaml.safe_load(f)

    jobs = validate["jobs"]
    assert "hassfest" in jobs

    hacs_job = jobs["hacs"]
    hacs_step = next(s for s in hacs_job["steps"] if "hacs/action" in s.get("uses", ""))
    inputs = hacs_step["with"]

    assert inputs["category"] == "integration"
    assert inputs["ignore"].split() == ["brands"]


def test_dependabot_github_actions():
    with DEPENDABOT_PATH.open(encoding="utf-8") as f:
        dependabot = yaml.safe_load(f)

    assert dependabot["version"] == 2

    entry = next(
        e for e in dependabot["updates"] if e["package-ecosystem"] == "github-actions"
    )
    assert entry["directory"] == "/"
    assert "interval" in entry["schedule"]


def test_readme_has_ci_badge():
    text = README_PATH.read_text(encoding="utf-8")
    assert "actions/workflows/ci.yml/badge.svg" in text
