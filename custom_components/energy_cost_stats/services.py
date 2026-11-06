"""Service ``energy_cost_stats.get_report`` (response only; tasks/013, SPEC §2).

Returns exactly the document of the websocket command. Decimal values are strings,
so templates apply ``| float``.
"""

from __future__ import annotations

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ServiceValidationError

from .const import (
    ATTR_END,
    ATTR_ENTITIES,
    ATTR_GROUPING,
    ATTR_START,
    DOMAIN,
    SERVICE_GET_REPORT,
)
from .engine.models import Grouping
from .report_api import ReportError, async_get_report

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_START): cv.string,
        vol.Required(ATTR_END): cv.string,
        vol.Required(ATTR_GROUPING): vol.In([g.value for g in Grouping]),
        vol.Optional(ATTR_ENTITIES): cv.entity_ids,
    }
)


async def _async_get_report(call: ServiceCall) -> ServiceResponse:
    try:
        return await async_get_report(
            call.hass,
            start=call.data[ATTR_START],
            end=call.data[ATTR_END],
            grouping=call.data[ATTR_GROUPING],
            entities=call.data.get(ATTR_ENTITIES),
        )
    except ReportError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key=err.code,
            translation_placeholders=err.placeholders,
        ) from err


def async_register_services(hass: HomeAssistant) -> None:
    """Register the action (once, from ``async_setup``)."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_REPORT,
        _async_get_report,
        schema=SERVICE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
