"""Unit tests for script/prefetch_ha_requirements.py: pure manifest-walk and
requirement-filtering logic only (no `homeassistant` import), plus a text
check that script/setup runs the pre-install step after `uv sync`.

See tasks/002-devcontainer.md follow-up ("HA ends in recovery mode").
"""

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "script" / "prefetch_ha_requirements.py"
SETUP_SCRIPT = REPO_ROOT / "script" / "setup"
DEVELOP_SCRIPT = REPO_ROOT / "script" / "develop"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "prefetch_ha_requirements", SCRIPT_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prefetch = _load_module()


def _write_manifest(components_dir: Path, domain: str, manifest: dict) -> None:
    domain_dir = components_dir / domain
    domain_dir.mkdir(parents=True, exist_ok=True)
    (domain_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


@pytest.fixture
def components_dir(tmp_path: Path) -> Path:
    return tmp_path / "components"


def test_find_manifest_missing_domain_returns_none(components_dir: Path):
    assert prefetch.find_manifest(components_dir, "does_not_exist") is None


def test_find_manifest_reads_json(components_dir: Path):
    _write_manifest(
        components_dir,
        "recorder",
        {"domain": "recorder", "requirements": ["SQLAlchemy==2.0.52"]},
    )

    manifest = prefetch.find_manifest(components_dir, "recorder")

    assert manifest == {"domain": "recorder", "requirements": ["SQLAlchemy==2.0.52"]}


def test_collect_requirements_walks_dependencies(components_dir: Path):
    _write_manifest(
        components_dir,
        "default_config",
        {"domain": "default_config", "dependencies": ["stream"], "requirements": []},
    )
    _write_manifest(
        components_dir,
        "stream",
        {
            "domain": "stream",
            "dependencies": ["camera"],
            "requirements": ["av==17.0.1"],
        },
    )
    _write_manifest(
        components_dir,
        "camera",
        {"domain": "camera", "requirements": ["PyTurboJPEG==1.8.3"]},
    )
    _write_manifest(
        components_dir,
        "frontend",
        {"domain": "frontend", "requirements": ["home-assistant-frontend==1.0.0"]},
    )

    all_requirements, critical = prefetch.collect_requirements(components_dir)

    assert all_requirements == [
        "PyTurboJPEG==1.8.3",
        "av==17.0.1",
        "home-assistant-frontend==1.0.0",
    ]
    assert critical == ["home-assistant-frontend==1.0.0"]


def test_collect_requirements_walks_after_dependencies_too(components_dir: Path):
    # Home Assistant's requirements manager installs requirements for
    # after_dependencies, not only dependencies (verified against
    # homeassistant/requirements.py at implementation time).
    _write_manifest(
        components_dir,
        "default_config",
        {
            "domain": "default_config",
            "dependencies": [],
            "after_dependencies": ["cloud"],
            "requirements": [],
        },
    )
    _write_manifest(
        components_dir,
        "cloud",
        {"domain": "cloud", "requirements": ["hass-nabucasa==1.2.3"]},
    )

    all_requirements, _critical = prefetch.collect_requirements(components_dir)

    assert "hass-nabucasa==1.2.3" in all_requirements


def test_collect_requirements_includes_extra_manifests(components_dir: Path):
    _write_manifest(
        components_dir,
        "default_config",
        {"domain": "default_config", "requirements": []},
    )
    _write_manifest(
        components_dir, "frontend", {"domain": "frontend", "requirements": []}
    )
    _write_manifest(
        components_dir,
        "recorder",
        {"domain": "recorder", "requirements": ["SQLAlchemy==2.0.52"]},
    )
    own_manifest = {
        "domain": "energy_cost_stats",
        "dependencies": ["recorder"],
        "requirements": [],
    }

    all_requirements, _critical = prefetch.collect_requirements(
        components_dir, extra_manifests=[own_manifest]
    )

    assert all_requirements == ["SQLAlchemy==2.0.52"]


def test_collect_requirements_handles_missing_domain_gracefully(components_dir: Path):
    _write_manifest(
        components_dir,
        "default_config",
        {
            "domain": "default_config",
            "dependencies": ["ghost_domain"],
            "requirements": [],
        },
    )

    # Should not raise even though "ghost_domain" has no manifest on disk.
    all_requirements, _critical = prefetch.collect_requirements(components_dir)

    assert all_requirements == []


def test_collect_requirements_deduplicates_diamond_dependencies(components_dir: Path):
    _write_manifest(
        components_dir,
        "default_config",
        {"domain": "default_config", "dependencies": ["a", "b"], "requirements": []},
    )
    _write_manifest(
        components_dir,
        "a",
        {"domain": "a", "dependencies": ["shared"], "requirements": []},
    )
    _write_manifest(
        components_dir,
        "b",
        {"domain": "b", "dependencies": ["shared"], "requirements": []},
    )
    _write_manifest(
        components_dir,
        "shared",
        {"domain": "shared", "requirements": ["packaging==24.0"]},
    )
    _write_manifest(
        components_dir, "frontend", {"domain": "frontend", "requirements": []}
    )

    all_requirements, _critical = prefetch.collect_requirements(components_dir)

    assert all_requirements == ["packaging==24.0"]


def test_missing_requirements_filters_out_installed_packages():
    # "pytest" is a real installed package in this test environment (dev group).
    installed_name = "pytest"
    from importlib.metadata import version

    installed_version = version(installed_name)

    result = prefetch.missing_requirements(
        [
            f"{installed_name}=={installed_version}",
            "definitely-not-a-real-package-xyz==1.0.0",
        ]
    )

    assert result == ["definitely-not-a-real-package-xyz==1.0.0"]


def test_missing_requirements_treats_unparseable_requirement_as_missing():
    result = prefetch.missing_requirements(["not a valid requirement string!!"])

    assert result == ["not a valid requirement string!!"]


def test_install_requirements_reports_failures_without_stopping(monkeypatch):
    calls = []

    class FakeResult:
        def __init__(self, returncode):
            self.returncode = returncode

    def fake_run(cmd, check):
        calls.append(cmd)
        # Fail only the second package, to prove the loop doesn't stop early.
        return FakeResult(1 if "b==2" in cmd else 0)

    monkeypatch.setattr(prefetch.subprocess, "run", fake_run)

    failures = prefetch.install_requirements(
        ["a==1", "b==2", "c==3"], Path("/tmp/constraints.txt")
    )

    assert failures == ["b==2"]
    assert len(calls) == 3


def test_setup_runs_prefetch_step_after_uv_sync():
    """script/setup is a POSIX sh script (not run natively on Windows), but
    this only reads its text, so it runs on any host, including Windows."""
    content = SETUP_SCRIPT.read_text(encoding="utf-8")

    sync_index = content.index("uv sync --group ha")
    prefetch_index = content.index("script/prefetch_ha_requirements.py")

    assert sync_index < prefetch_index


def _uv_run_lines(script_path: Path) -> list[str]:
    """Every non-comment line of a POSIX sh script that invokes `uv run`."""
    content = script_path.read_text(encoding="utf-8")
    return [
        line
        for line in content.splitlines()
        if "uv run" in line and not line.strip().startswith("#")
    ]


def test_uv_run_invocations_carry_no_sync():
    """Every `uv run` in script/setup and script/develop, other than the
    initial exact `uv sync`, must pass --no-sync. Otherwise its implicit sync
    silently reverts the HA runtime requirements script/setup pre-installs
    (see tasks/002-devcontainer.md follow-up round), which is exactly the
    live-install/recovery-mode failure mode this pre-install step exists to
    avoid -- including on script/develop's ensure_config branch, which only
    runs on a completely fresh config volume."""
    uv_run_lines = _uv_run_lines(SETUP_SCRIPT) + _uv_run_lines(DEVELOP_SCRIPT)

    assert uv_run_lines, "expected at least one `uv run` line to check"
    for line in uv_run_lines:
        assert "--no-sync" in line, f"missing --no-sync: {line!r}"


def test_summarize_failures_no_failures_returns_zero():
    assert (
        prefetch.summarize_failures(
            [], critical_requirements=["home-assistant-frontend==1.0.0"]
        )
        == 0
    )


def test_summarize_failures_critical_failure_aborts(capsys):
    exit_code = prefetch.summarize_failures(
        ["home-assistant-frontend==1.0.0"],
        critical_requirements=["home-assistant-frontend==1.0.0"],
    )

    assert exit_code == 1
    assert "aborting" in capsys.readouterr().err


def test_summarize_failures_best_effort_failure_continues(capsys):
    exit_code = prefetch.summarize_failures(
        ["some-optional-package==1.0.0"],
        critical_requirements=["home-assistant-frontend==1.0.0"],
    )

    assert exit_code == 0
    assert "continuing despite" in capsys.readouterr().err


def test_summarize_failures_via_fake_installer_frontend_failure_aborts(monkeypatch):
    """End-to-end through install_requirements with a monkeypatched
    subprocess (no network, host-runnable): a frontend requirement failing
    to install must abort (non-zero exit), a non-critical one must not."""

    class FakeResult:
        def __init__(self, returncode):
            self.returncode = returncode

    def fake_run(cmd, check):
        req = cmd[cmd.index("--quiet") + 1]
        return FakeResult(1 if req.startswith("home-assistant-frontend") else 0)

    monkeypatch.setattr(prefetch.subprocess, "run", fake_run)

    failures = prefetch.install_requirements(
        ["home-assistant-frontend==1.0.0", "optional-pkg==2.0.0"],
        Path("/tmp/constraints.txt"),
    )
    exit_code = prefetch.summarize_failures(
        failures, critical_requirements=["home-assistant-frontend==1.0.0"]
    )

    assert exit_code == 1


def test_summarize_failures_via_fake_installer_non_critical_failure_continues(
    monkeypatch,
):
    class FakeResult:
        def __init__(self, returncode):
            self.returncode = returncode

    def fake_run(cmd, check):
        req = cmd[cmd.index("--quiet") + 1]
        return FakeResult(1 if req == "optional-pkg==2.0.0" else 0)

    monkeypatch.setattr(prefetch.subprocess, "run", fake_run)

    failures = prefetch.install_requirements(
        ["home-assistant-frontend==1.0.0", "optional-pkg==2.0.0"],
        Path("/tmp/constraints.txt"),
    )
    exit_code = prefetch.summarize_failures(
        failures, critical_requirements=["home-assistant-frontend==1.0.0"]
    )

    assert exit_code == 0
