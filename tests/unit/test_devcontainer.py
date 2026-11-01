"""Devcontainer metadata smoke tests: devcontainer.json, Dockerfile, dev HA config,
launch.json. No Docker, no Home Assistant; these run natively on Windows (tasks/001
precedent: tests/unit/test_metadata.py)."""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEVCONTAINER_DIR = REPO_ROOT / ".devcontainer"
DEVCONTAINER_JSON = DEVCONTAINER_DIR / "devcontainer.json"
DOCKERFILE = DEVCONTAINER_DIR / "Dockerfile"
CONFIGURATION_YAML = REPO_ROOT / "config" / "configuration.yaml"
LAUNCH_JSON = REPO_ROOT / ".vscode" / "launch.json"
PYTHON_VERSION_FILE = REPO_ROOT / ".python-version"
SMOKE_DEVELOP_SCRIPT = REPO_ROOT / "script" / "smoke-develop"


def _load_devcontainer_json() -> dict:
    return json.loads(DEVCONTAINER_JSON.read_text(encoding="utf-8"))


def test_devcontainer_json():
    data = _load_devcontainer_json()

    assert data["build"]["dockerfile"] == "Dockerfile"
    assert data["remoteUser"] == "vscode"
    assert 8123 in data["forwardPorts"]
    assert "script/setup" in data["postCreateCommand"]

    features = data.get("features", {})
    node_feature_keys = [
        key
        for key in features
        if key.startswith("ghcr.io/devcontainers/features/node:")
    ]
    assert len(node_feature_keys) == 1, (
        f"expected exactly one node feature key, found {node_feature_keys}"
    )
    assert features[node_feature_keys[0]]["version"] == "24"

    extensions = data["customizations"]["vscode"]["extensions"]
    for expected in (
        "ms-python.python",
        "ms-python.vscode-pylance",
        "charliermarsh.ruff",
    ):
        assert expected in extensions

    run_args = data.get("runArgs", [])
    assert "--privileged" not in run_args
    assert "--network=host" not in run_args


def test_dockerfile_matches_python_version():
    content = DOCKERFILE.read_text(encoding="utf-8")
    major_minor = (
        PYTHON_VERSION_FILE.read_text(encoding="utf-8").strip().rsplit(".", 1)[0]
    )

    from_match = re.search(
        r"^FROM mcr\.microsoft\.com/devcontainers/python:(\S+)$", content, re.MULTILINE
    )
    assert from_match, "no FROM mcr.microsoft.com/devcontainers/python: line found"
    tag = from_match.group(1)
    assert major_minor in tag
    assert "trixie" in tag

    copy_match = re.search(
        r"^COPY --from=ghcr\.io/astral-sh/uv:(\S+) /uv /uvx /bin/",
        content,
        re.MULTILINE,
    )
    assert copy_match, "no COPY --from=ghcr.io/astral-sh/uv: line found"
    uv_version = copy_match.group(1)
    assert re.fullmatch(r"\d+\.\d+\.\d+", uv_version), (
        f"uv version must be pinned exactly (no 'latest'), got {uv_version!r}"
    )

    env_match = re.search(r"^ENV .*UV_PROJECT_ENVIRONMENT=(\S+)", content, re.MULTILINE)
    assert env_match, "no ENV line setting UV_PROJECT_ENVIRONMENT found"
    venv_path = env_match.group(1)
    assert venv_path.startswith("/"), "UV_PROJECT_ENVIRONMENT must be an absolute path"
    assert not venv_path.startswith("/workspaces"), (
        "UV_PROJECT_ENVIRONMENT must not live under /workspaces (the bind mount)"
    )

    assert re.search(r"UV_LINK_MODE=copy", content)


def test_dockerfile_creates_writable_mount_points():
    """Every named-volume mount target must be pre-created with vscode ownership,
    otherwise Docker creates the mount point as root:root and processes running as
    vscode (e.g. script/develop) cannot write to it (review round 1, Required 1)."""
    data = _load_devcontainer_json()

    mount_targets = []
    for mount in data.get("mounts", []):
        match = re.search(r"target=([^,]+)", mount)
        assert match, f"mount entry has no target=: {mount!r}"
        mount_targets.append(match.group(1))
    assert mount_targets, "no mounts found in devcontainer.json"

    ha_config_dir = data.get("containerEnv", {}).get("HA_CONFIG_DIR")
    assert ha_config_dir, "containerEnv.HA_CONFIG_DIR must be set in devcontainer.json"
    assert ha_config_dir in mount_targets, (
        "HA_CONFIG_DIR must point at one of the mounted named-volume targets"
    )

    content = DOCKERFILE.read_text(encoding="utf-8")
    install_match = re.search(
        r"^RUN install -d -o vscode -g vscode (.+)$", content, re.MULTILINE
    )
    assert install_match, (
        "no 'RUN install -d -o vscode -g vscode ...' line in Dockerfile"
    )
    created_dirs = install_match.group(1).split()

    for target in mount_targets:
        assert target in created_dirs, (
            f"{target} is mounted but not pre-created with vscode ownership"
        )


def test_interpreter_path_matches_venv():
    dockerfile_content = DOCKERFILE.read_text(encoding="utf-8")
    env_match = re.search(
        r"^ENV .*UV_PROJECT_ENVIRONMENT=(\S+)", dockerfile_content, re.MULTILINE
    )
    assert env_match
    venv_path = env_match.group(1)

    data = _load_devcontainer_json()
    interpreter_path = data["customizations"]["vscode"]["settings"][
        "python.defaultInterpreterPath"
    ]
    assert interpreter_path == f"{venv_path}/bin/python"


def test_dev_ha_configuration():
    assert CONFIGURATION_YAML.exists()
    content = CONFIGURATION_YAML.read_text(encoding="utf-8")

    assert re.search(r"^default_config:\s*$", content, re.MULTILINE)
    assert re.search(r"^energy_cost_stats:\s*$", content, re.MULTILINE)
    assert re.search(
        r"custom_components\.energy_cost_stats:\s*debug\s*$", content, re.MULTILINE
    )

    assert "!secret" not in content
    assert not re.search(r"\blatitude\b", content)
    assert not re.search(r"\blongitude\b", content)
    assert not re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", content), (
        "configuration.yaml must not contain an IPv4-like string"
    )

    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "config/*" in gitignore
    assert "!config/configuration.yaml" in gitignore


def test_launch_json():
    data = json.loads(LAUNCH_JSON.read_text(encoding="utf-8"))
    configurations = data["configurations"]

    ha_configs = [c for c in configurations if c.get("module") == "homeassistant"]
    assert len(ha_configs) == 1, (
        f"expected exactly one 'homeassistant' configuration, found {len(ha_configs)}"
    )
    ha_config = ha_configs[0]

    args = ha_config["args"]
    assert "--debug" in args
    assert "--config" in args, "expected a --config argument"
    # Same config dir as script/develop (the named volume in the devcontainer,
    # not config/ in the Windows checkout bind mount) so debugging uses the same
    # runtime data and nothing lands in the checkout (review round 1, Required 3).
    config_value = args[args.index("--config") + 1]
    assert config_value == "${env:HA_CONFIG_DIR}"

    assert ha_config["env"]["PYTHONPATH"] == "${workspaceFolder}"


def test_dockerfile_pins_go2rtc():
    content = DOCKERFILE.read_text(encoding="utf-8")

    pattern = re.compile(
        r"^COPY --from=ghcr\.io/alexxit/go2rtc:(\d+\.\d+\.\d+)@sha256:[0-9a-f]{64} "
        r"/usr/local/bin/go2rtc /bin/go2rtc$",
        re.MULTILINE,
    )
    matches = pattern.findall(content)
    assert len(matches) == 1, (
        f"expected exactly one pinned go2rtc COPY line, found {len(matches)}"
    )

    assert not re.search(
        r"^COPY --from=ghcr\.io/alexxit/go2rtc:latest", content, re.MULTILINE
    ), "go2rtc must be pinned to an exact version, not 'latest'"


def _non_comment_lines(script_path: Path) -> list[str]:
    return [
        line
        for line in script_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def test_smoke_develop_fails_on_default_config_dependencies():
    lines = _non_comment_lines(SMOKE_DEVELOP_SCRIPT)
    content = "\n".join(lines)

    assert "Unable to set up dependencies of 'default_config'" in content
    assert re.search(r"Setup failed for .*default_config", content)
    assert "Attempting install of" in content
