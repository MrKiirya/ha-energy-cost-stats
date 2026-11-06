"""Websocket commands ``energy_cost_stats/report`` (tasks/013, docs/SPEC.md §2) and
``energy_cost_stats/compare`` (tasks/015, SPEC §4.2).

Read-only, so any authenticated user may call them (no admin requirement).
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

from .const import (
    ATTR_END,
    ATTR_ENTITIES,
    ATTR_GROUPING,
    ATTR_SCENARIOS,
    ATTR_START,
    WS_TYPE_COMPARE,
    WS_TYPE_REPORT,
)
from .engine.models import Grouping
from .report_api import ReportError, async_get_comparison, async_get_report


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


@websocket_command(
    {
        vol.Required("type"): WS_TYPE_COMPARE,
        vol.Required(ATTR_START): str,
        vol.Required(ATTR_END): str,
        vol.Optional(ATTR_ENTITIES): [cv.entity_id],
        # Scenario contents are validated by the engine (invalid_scenario).
        vol.Required(ATTR_SCENARIOS): [dict],
    }
)
@async_response
async def ws_compare(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return the configured-plan report and one report per tariff scenario."""
    try:
        result = await async_get_comparison(
            hass,
            start=msg[ATTR_START],
            end=msg[ATTR_END],
            entities=msg.get(ATTR_ENTITIES),
            scenarios=msg[ATTR_SCENARIOS],
        )
    except ReportError as err:
        connection.send_error(msg["id"], err.code, err.message)
        return
    connection.send_result(msg["id"], result)


def async_register_websocket(hass: HomeAssistant) -> None:
    """Register the commands (once, from ``async_setup``)."""
    async_register_command(hass, ws_report)
    async_register_command(hass, ws_compare)
