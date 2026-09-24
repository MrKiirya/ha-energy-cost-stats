"""Guard tests for the engine purity rule (CLAUDE.md principle 4) and the
dual-name caveat (tasks/001-scaffold.md decision 3)."""

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_DIR = REPO_ROOT / "custom_components" / "energy_cost_stats" / "engine"
UNIT_TESTS_DIR = REPO_ROOT / "tests" / "unit"


def _iter_python_files(directory: Path) -> list[Path]:
    return sorted(directory.rglob("*.py"))


def find_forbidden_engine_imports(source: str) -> list[str]:
    """Return a list of human-readable violations found in engine source code.

    Flags:
    - any import of `homeassistant` (absolute or `from homeassistant... import ...`);
    - absolute imports of `engine...` or `custom_components...`;
    - relative imports with level >= 2 (i.e. `from .. import x`, leaving the package).
    """
    violations: list[str] = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "homeassistant" or alias.name.startswith(
                    "homeassistant."
                ):
                    violations.append(f"import {alias.name}")
                if alias.name == "engine" or alias.name.startswith("engine."):
                    violations.append(f"import {alias.name}")
                if alias.name == "custom_components" or alias.name.startswith(
                    "custom_components."
                ):
                    violations.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level == 0:
                if module == "homeassistant" or module.startswith("homeassistant."):
                    violations.append(f"from {module} import ...")
                if module == "engine" or module.startswith("engine."):
                    violations.append(f"from {module} import ...")
                if module == "custom_components" or module.startswith(
                    "custom_components."
                ):
                    violations.append(f"from {module} import ...")
            elif node.level >= 2:
                violations.append(
                    f"from {'.' * node.level}{module} import ... (level {node.level})"
                )
    return violations


def test_engine_importable_as_top_level():
    ha_installed_before = importlib.util.find_spec("homeassistant") is not None

    import engine

    assert Path(engine.__file__).resolve().parent == ENGINE_DIR.resolve()

    if not ha_installed_before:
        assert "homeassistant" not in sys.modules


def test_engine_has_no_forbidden_imports():
    files = _iter_python_files(ENGINE_DIR)
    assert files, "no Python files found under engine/, test would be vacuous"

    all_violations: dict[str, list[str]] = {}
    for path in files:
        violations = find_forbidden_engine_imports(path.read_text(encoding="utf-8"))
        if violations:
            all_violations[str(path.relative_to(REPO_ROOT))] = violations

    assert not all_violations, f"forbidden imports found: {all_violations}"


@pytest.mark.parametrize(
    "source",
    [
        "import homeassistant",
        "from homeassistant.core import HomeAssistant",
        "from .. import const",
        "import custom_components.energy_cost_stats.const",
        "from engine import x",
    ],
)
def test_guard_detects_violations(source):
    assert find_forbidden_engine_imports(source)


@pytest.mark.parametrize(
    "source",
    [
        "import math",
        "from . import x",
        "from .sub import y",
    ],
)
def test_guard_allows_clean_sources(source):
    assert not find_forbidden_engine_imports(source)


def find_integration_package_imports(source: str) -> list[str]:
    """Return violations: imports of `custom_components...` in unit test source."""
    violations: list[str] = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "custom_components" or alias.name.startswith(
                    "custom_components."
                ):
                    violations.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level == 0 and (
                module == "custom_components" or module.startswith("custom_components.")
            ):
                violations.append(f"from {module} import ...")
    return violations


def test_unit_tests_do_not_import_integration_package():
    files = _iter_python_files(UNIT_TESTS_DIR)
    assert files, "no Python files found under tests/unit/, test would be vacuous"

    all_violations: dict[str, list[str]] = {}
    for path in files:
        violations = find_integration_package_imports(path.read_text(encoding="utf-8"))
        if violations:
            all_violations[str(path.relative_to(REPO_ROOT))] = violations

    assert not all_violations, (
        f"integration package imports found in unit tests: {all_violations}"
    )
