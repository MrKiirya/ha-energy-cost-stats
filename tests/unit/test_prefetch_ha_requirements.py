"""Unit tests for script/prefetch_ha_requirements.py: pure manifest-walk and
requirement-filtering logic only (no `homeassistant` import), plus a text
check that script/setup runs the pre-install step after `uv sync`.

See tasks/002-devcontainer.md follow-up ("HA ends in recovery mode").
"""

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "script" / "prefetch_ha_requirements.py"
SETUP_SCRIPT = REPO_ROOT / "script" / "setup"
DEVELOP_SCRIPT = REPO_ROOT / "script" / "develop"
CONFIG_ENTRIES_FIXTURE = (
    REPO_ROOT / "tests" / "fixtures" / "ha_storage" / "core.config_entries"
)


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


def test_config_entry_domains_from_fixture(tmp_path: Path):
    storage_dir = tmp_path / ".storage"
    storage_dir.mkdir(parents=True)
    shutil.copy(CONFIG_ENTRIES_FIXTURE, storage_dir / "core.config_entries")

    domains = prefetch.config_entry_domains(tmp_path)

    assert domains == ["google_translate", "met"]


def test_config_entry_domains_missing_file_returns_empty(tmp_path: Path):
    assert prefetch.config_entry_domains(tmp_path) == []


def test_config_entry_domains_malformed_returns_empty_and_warns(tmp_path: Path, capsys):
    storage_dir = tmp_path / ".storage"
    storage_dir.mkdir(parents=True)
    (storage_dir / "core.config_entries").write_text(
        "not json at all", encoding="utf-8"
    )

    domains = prefetch.config_entry_domains(tmp_path)

    assert domains == []
    err = capsys.readouterr().err
    assert len(err.strip().splitlines()) == 1


def test_config_entry_domains_missing_data_entries_returns_empty_and_warns(
    tmp_path: Path, capsys
):
    storage_dir = tmp_path / ".storage"
    storage_dir.mkdir(parents=True)
    (storage_dir / "core.config_entries").write_text(
        json.dumps({"version": 1, "key": "core.config_entries"}), encoding="utf-8"
    )

    domains = prefetch.config_entry_domains(tmp_path)

    assert domains == []
    err = capsys.readouterr().err
    assert len(err.strip().splitlines()) == 1


@pytest.mark.parametrize(
    "content_bytes",
    [
        pytest.param(b"\xff\xfe\x00not-utf8", id="non_utf8_bytes"),
        pytest.param(
            json.dumps({"data": {"entries": {"domain": "x"}}}).encode(),
            id="entries_is_object_not_list",
        ),
        pytest.param(
            json.dumps(["not", "an", "object"]).encode(), id="top_level_not_object"
        ),
    ],
)
def test_config_entry_domains_unrecoverable_shapes_return_empty_and_warn_once(
    tmp_path: Path, capsys, content_bytes: bytes
):
    """Shapes the function cannot make sense of at all: one warning, `[]`."""
    storage_dir = tmp_path / ".storage"
    storage_dir.mkdir(parents=True)
    (storage_dir / "core.config_entries").write_bytes(content_bytes)

    domains = prefetch.config_entry_domains(tmp_path)

    assert domains == []
    err = capsys.readouterr().err
    assert len(err.strip().splitlines()) == 1


@pytest.mark.parametrize(
    ("entries", "expected_domains"),
    [
        pytest.param([1, 2], [], id="entries_non_objects"),
        pytest.param(
            [
                {"domain": None, "disabled_by": None},
                {"domain": "met", "disabled_by": None},
            ],
            ["met"],
            id="null_domain_next_to_string_domain",
        ),
        pytest.param([{"domain": 1, "disabled_by": None}], [], id="non_string_domain"),
    ],
)
def test_config_entry_domains_skips_malformed_entries_without_warning(
    tmp_path: Path, capsys, entries: list, expected_domains: list[str]
):
    """A recognizable `entries` list with some bad entries: skip those entries
    silently and still return the domains of the well-formed ones, without
    breaking setup and without a spurious warning for a partly-usable file."""
    storage_dir = tmp_path / ".storage"
    storage_dir.mkdir(parents=True)
    (storage_dir / "core.config_entries").write_text(
        json.dumps({"data": {"entries": entries}}), encoding="utf-8"
    )

    domains = prefetch.config_entry_domains(tmp_path)

    assert domains == expected_domains
    assert capsys.readouterr().err == ""


def test_collect_requirements_includes_config_entry_domain_deps(
    components_dir: Path,
):
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
        "google_translate",
        {"domain": "google_translate", "requirements": ["gTTS==2.5.4"]},
    )
    _write_manifest(
        components_dir,
        "met",
        {"domain": "met", "dependencies": ["met_backend"], "requirements": []},
    )
    _write_manifest(
        components_dir,
        "met_backend",
        {"domain": "met_backend", "requirements": ["pymetno==1.0.0"]},
    )

    root_domains = (
        *prefetch.ROOT_DOMAINS,
        "google_translate",
        "met",
    )
    all_requirements, critical = prefetch.collect_requirements(
        components_dir, root_domains=root_domains
    )

    assert "gTTS==2.5.4" in all_requirements
    assert "pymetno==1.0.0" in all_requirements
    assert "gTTS==2.5.4" not in critical
    assert "pymetno==1.0.0" not in critical


def test_prefetch_flow_returns_summarize_exit_code(components_dir: Path, monkeypatch):
    _write_manifest(
        components_dir,
        "default_config",
        {"domain": "default_config", "requirements": []},
    )
    _write_manifest(
        components_dir,
        "frontend",
        {"domain": "frontend", "requirements": ["home-assistant-frontend==1.0.0"]},
    )

    calls = []

    class FakeResult:
        def __init__(self, returncode):
            self.returncode = returncode

    def fake_run(cmd, check):
        calls.append(cmd)
        req = cmd[cmd.index("--quiet") + 1]
        return FakeResult(1 if req.startswith("home-assistant-frontend") else 0)

    monkeypatch.setattr(prefetch.subprocess, "run", fake_run)
    monkeypatch.setattr(
        prefetch,
        "missing_requirements",
        lambda reqs: list(reqs),
    )

    exit_code = prefetch.run_prefetch(
        components_dir,
        constraints=Path("/tmp/constraints.txt"),
        root_domains=("default_config", "frontend"),
    )

    assert exit_code == 1
    assert calls

    # Non-critical failure only: exit code stays 0.
    calls.clear()
    _write_manifest(
        components_dir,
        "frontend",
        {"domain": "frontend", "requirements": []},
    )
    _write_manifest(
        components_dir,
        "default_config",
        {
            "domain": "default_config",
            "dependencies": ["optional_thing"],
            "requirements": [],
        },
    )
    _write_manifest(
        components_dir,
        "optional_thing",
        {"domain": "optional_thing", "requirements": ["optional-pkg==2.0.0"]},
    )

    def fake_run_non_critical(cmd, check):
        calls.append(cmd)
        return FakeResult(1)

    monkeypatch.setattr(prefetch.subprocess, "run", fake_run_non_critical)

    exit_code = prefetch.run_prefetch(
        components_dir,
        constraints=Path("/tmp/constraints.txt"),
        root_domains=("default_config", "frontend"),
    )

    assert exit_code == 0
    assert calls

    # Nothing missing: no subprocess.run call at all.
    calls.clear()
    monkeypatch.setattr(prefetch, "missing_requirements", lambda reqs: [])

    exit_code = prefetch.run_prefetch(
        components_dir,
        constraints=Path("/tmp/constraints.txt"),
        root_domains=("default_config", "frontend"),
    )

    assert exit_code == 0
    assert calls == []


def test_develop_runs_prefetch_before_hass():
    content = DEVELOP_SCRIPT.read_text(encoding="utf-8")
    lines = content.splitlines()

    prefetch_lines = [
        line
        for line in lines
        if "prefetch_ha_requirements.py" in line and not line.strip().startswith("#")
    ]
    assert prefetch_lines, "no non-comment line invoking prefetch_ha_requirements.py"
    assert any("--config-dir" in line for line in prefetch_lines)

    prefetch_index = next(
        i
        for i, line in enumerate(lines)
        if "prefetch_ha_requirements.py" in line and not line.strip().startswith("#")
    )
    exec_index = next(
        i for i, line in enumerate(lines) if line.strip().startswith("exec uv run")
    )
    assert prefetch_index < exec_index


def test_setup_passes_config_dir_to_prefetch():
    content = SETUP_SCRIPT.read_text(encoding="utf-8")
    prefetch_lines = [
        line
        for line in content.splitlines()
        if "prefetch_ha_requirements.py" in line and not line.strip().startswith("#")
    ]
    assert prefetch_lines
    assert any("--config-dir" in line for line in prefetch_lines)
