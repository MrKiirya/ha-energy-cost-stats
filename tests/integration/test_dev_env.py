"""Drift guard for the devcontainer's pinned go2rtc binary (tasks/008-dev-ha-fixes.md
decision 1): the pinned version must stay at or above the Home Assistant version's
`RECOMMENDED_VERSION`, on both CI matrix legs (2025.4.0 and latest). Runs as
`async def` because `tests/integration/conftest.py`'s autouse `_auto_enable`
fixture (`recorder_mock`, `enable_custom_integrations`) is async.

`RECOMMENDED_VERSION` is read from the source text of
`homeassistant/components/go2rtc/const.py` with a regex, not via
`from homeassistant.components.go2rtc.const import RECOMMENDED_VERSION`:
importing the `go2rtc` package runs its `__init__`, which pulls in
`go2rtc_client`, `webrtc_models`, `camera`, `stream` and more -- none of which
are in `uv.lock` (they are only present when the prefetch helper's best-effort
`default_config` install happened to succeed). Reading the source text avoids
that dependency (review round-1 suggestion 1).
"""

import importlib.util
import re
from pathlib import Path

import pytest
from awesomeversion import AwesomeVersion

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = REPO_ROOT / ".devcontainer" / "Dockerfile"


def _recommended_version() -> str:
    ha_spec = importlib.util.find_spec("homeassistant")
    assert ha_spec is not None
    assert ha_spec.origin is not None
    const_path = (
        Path(ha_spec.origin).resolve().parent / "components" / "go2rtc" / "const.py"
    )
    content = const_path.read_text(encoding="utf-8")
    match = re.search(r'^RECOMMENDED_VERSION\s*=\s*"([^"]+)"', content, re.MULTILINE)
    assert match, f"could not find RECOMMENDED_VERSION in {const_path}"
    return match.group(1)


async def test_go2rtc_pin_satisfies_recommended_version():
    content = DOCKERFILE.read_text(encoding="utf-8")

    match = re.search(
        r"^COPY --from=ghcr\.io/alexxit/go2rtc:(\d+\.\d+\.\d+)@sha256:[0-9a-f]{64} "
        r"/usr/local/bin/go2rtc /bin/go2rtc$",
        content,
        re.MULTILINE,
    )
    assert match, "no pinned go2rtc COPY line found in .devcontainer/Dockerfile"
    pinned_version = match.group(1)

    recommended_version = _recommended_version()
    assert AwesomeVersion(pinned_version) >= AwesomeVersion(recommended_version), (
        f"go2rtc pin {pinned_version!r} in .devcontainer/Dockerfile is older than "
        f"this Home Assistant's RECOMMENDED_VERSION {recommended_version!r}; bump "
        "the pin (see CLAUDE.md 'Bumping latest HA')."
    )


def test_recommended_version_helper_finds_go2rtc_const():
    # Guards the regex/path above against silently returning nothing useful
    # if homeassistant's layout ever changes.
    if importlib.util.find_spec("homeassistant") is None:
        pytest.skip("homeassistant not installed")
    assert re.match(r"^\d+\.\d+\.\d+$", _recommended_version())
