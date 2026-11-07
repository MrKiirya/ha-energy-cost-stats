"""Serve the Lovelace card bundle from the integration (docs/SPEC.md §2).

The bundle (``frontend/energy-cost-stats-card.js``, built from the repo's
``frontend/`` sources and committed) is exposed as a static path and, when the
``frontend`` integration is loaded, registered as an extra module so the card
works without adding a dashboard resource by hand. The URL carries a content
hash so browsers pick up a new bundle after an update.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url

# Defined here in HA 2025.4; later moved to ``http.server`` and re-exported here
# for compatibility (without ``__all__``), so pyright flags it on the latest HA.
from homeassistant.components.http import (
    StaticPathConfig,  # pyright: ignore[reportPrivateImportUsage]
)
from homeassistant.core import HomeAssistant
from homeassistant.util.hass_dict import HassKey

from .const import CARD_URL

# The versioned URL passed to ``add_extra_js_url``; the sidebar panel reuses it.
DATA_CARD_MODULE_URL: HassKey[str] = HassKey("energy_cost_stats_card_module_url")
CARD_PATH = Path(__file__).parent / "frontend" / "energy-cost-stats-card.js"


def card_version(content: bytes) -> str:
    """Short content hash used as the cache-busting ``?v=`` query."""
    return hashlib.sha256(content).hexdigest()[:12]


async def async_register_card(hass: HomeAssistant) -> None:
    """Expose the bundle and, with the frontend loaded, load it on every dashboard."""
    if hass.http is None:  # e.g. a setup without the http integration
        return
    content = await hass.async_add_executor_job(CARD_PATH.read_bytes)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(CARD_PATH), cache_headers=True)]
    )
    if "frontend" in hass.config.components:
        url = f"{CARD_URL}?v={card_version(content)}"
        hass.data[DATA_CARD_MODULE_URL] = url
        add_extra_js_url(hass, url)


def card_module_url(hass: HomeAssistant) -> str | None:
    """The versioned bundle URL, or None when the frontend is not loaded."""
    return hass.data.get(DATA_CARD_MODULE_URL)
