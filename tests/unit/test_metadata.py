"""Metadata smoke tests: manifest.json, hacs.json, custom_components/ layout."""

import ast
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CUSTOM_COMPONENTS_DIR = REPO_ROOT / "custom_components"
INTEGRATION_DIR = CUSTOM_COMPONENTS_DIR / "energy_cost_stats"


def _read_domain_const_via_ast() -> str:
    """Read DOMAIN from const.py via AST, without importing the integration package."""
    source = (INTEGRATION_DIR / "const.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "DOMAIN"
        ):
            assert isinstance(node.value, ast.Constant)
            assert isinstance(node.value.value, str)
            return node.value.value
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "DOMAIN":
                    assert isinstance(node.value, ast.Constant)
                    assert isinstance(node.value.value, str)
                    return node.value.value
    raise AssertionError("DOMAIN not found in const.py")


def test_manifest_matches_domain():
    manifest = json.loads(
        (INTEGRATION_DIR / "manifest.json").read_text(encoding="utf-8")
    )
    domain = _read_domain_const_via_ast()

    assert manifest["domain"] == domain

    required_keys = {
        "domain",
        "name",
        "version",
        "documentation",
        "issue_tracker",
        "codeowners",
        "iot_class",
        "integration_type",
    }
    assert required_keys <= manifest.keys()

    assert manifest["integration_type"] == "service"
    assert manifest["iot_class"] == "calculated"
    assert not manifest.get("config_flow", False)
    assert "recorder" in manifest["dependencies"]
    assert re.match(r"^\d+\.\d+\.\d+$", manifest["version"])


def test_hacs_json():
    hacs = json.loads((REPO_ROOT / "hacs.json").read_text(encoding="utf-8"))
    assert hacs["name"]
    assert hacs["homeassistant"] == "2025.4.0"


def test_single_integration_dir():
    subdirs = [
        p.name
        for p in CUSTOM_COMPONENTS_DIR.iterdir()
        if p.is_dir() and p.name != "__pycache__"
    ]
    assert subdirs == ["energy_cost_stats"]
