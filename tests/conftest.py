"""Root test configuration: test-level marker auto-apply and the HA-harness guard.

See CLAUDE.md "Test levels" and tasks/001-scaffold.md decisions 4 and 5.
"""

import importlib.util
from pathlib import Path

_HA_HARNESS_INSTALLED = (
    importlib.util.find_spec("pytest_homeassistant_custom_component") is not None
)
_LEVELS = ("unit", "integration", "golden")

if not _HA_HARNESS_INSTALLED:
    # Integration test modules import `homeassistant.*` at module level, so a per-test
    # skip marker would come too late (collection itself would fail). Ignore the whole
    # directory.
    collect_ignore_glob = ["integration/*"]


def pytest_report_header(config):
    """Print a header line when the HA test harness is not installed."""
    if not _HA_HARNESS_INSTALLED:
        return (
            "HA test harness not installed: tests/integration ignored "
            "(run in the container: uv sync --group ha)"
        )
    return None


def pytest_collection_modifyitems(config, items):
    """Automatically apply the unit / integration / golden marker based on directory."""
    for item in items:
        parts = Path(str(item.fspath)).parts
        for level in _LEVELS:
            if level in parts:
                item.add_marker(level)
                break
