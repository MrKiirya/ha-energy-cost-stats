"""Optional sidebar panel (docs/SPEC.md §4.1).

A custom-element panel (no iframe) whose element ``energy-cost-stats-panel`` lives in
the card bundle, loaded from the same versioned URL as the extra module, so the bundle
runs once. The panel follows the config entry: it is registered on setup when the
``panel`` option asks for it and removed on unload, so option changes and the YAML
reload (both reload the entry) update the sidebar without a restart. This is the only
module that touches ``panel_custom`` / ``async_remove_panel``.
"""

from __future__ import annotations

import logging

from homeassistant.components.frontend import async_remove_panel
from homeassistant.components.panel_custom import async_register_panel
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import PANEL_ELEMENT, PANEL_URL_PATH
from .frontend import card_module_url
from .settings import IntegrationSettings

_LOGGER = logging.getLogger(__name__)


async def async_setup_panel(
    hass: HomeAssistant, entry: ConfigEntry, settings: IntegrationSettings
) -> None:
    """Register the sidebar panel when it is shown; remove it when the entry unloads."""
    panel = settings.panel
    if panel is None or not panel.show:
        return
    module_url = card_module_url(hass)
    if module_url is None or "frontend" not in hass.config.components:
        return
    try:
        # Keyword arguments only: newer Home Assistant versions add parameters.
        await async_register_panel(
            hass,
            frontend_url_path=PANEL_URL_PATH,
            webcomponent_name=PANEL_ELEMENT,
            sidebar_title=panel.title,
            sidebar_icon=panel.icon,
            module_url=module_url,
            embed_iframe=False,
            require_admin=False,
        )
    except ValueError as err:
        _LOGGER.warning(
            "Cannot add the sidebar panel at /%s (%s); continuing without it",
            PANEL_URL_PATH,
            err,
        )
        return

    @callback
    def _remove() -> None:
        async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)

    entry.async_on_unload(_remove)
