"""Websocket command ``energy_cost_stats/report`` (tasks/013, docs/SPEC.md §2).

Read-only, so any authenticated user may call it (no admin requirement).
"""

from __future__ import annotations

from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.websocket_api import async_register_command
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.decorators import (
    async_response,
    websocket_command,
)
from homeassistant.core import HomeAssistant

from .const import ATTR_END, ATTR_ENTITIES, ATTR_GROUPING, ATTR_START, WS_TYPE_REPORT
from .engine.models import Grouping
from .report_api import ReportError, async_get_report


@websocket_command(
    {
        vol.Required("type"): WS_TYPE_REPORT,
        vol.Required(ATTR_START): str,
        vol.Required(ATTR_END): str,
        vol.Required(ATTR_GROUPING): vol.In([g.value for g in Grouping]),
        vol.Optional(ATTR_ENTITIES): [cv.entity_id],
    }
)
@async_response
async def ws_report(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return the cost report document."""
    try:
        result = await async_get_report(
            hass,
            start=msg[ATTR_START],
            end=msg[ATTR_END],
            grouping=msg[ATTR_GROUPING],
            entities=msg.get(ATTR_ENTITIES),
        )
    except ReportError as err:
        connection.send_error(msg["id"], err.code, err.message)
        return
    connection.send_result(msg["id"], result)


def async_register_websocket(hass: HomeAssistant) -> None:
    """Register the command (once, from ``async_setup``)."""
    async_register_command(hass, ws_report)
