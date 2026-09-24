"""Energy Cost Stats: electricity cost per device, split by tariff zones.

This module only registers the integration with Home Assistant (stage 0 scaffold).
No entities, platforms or services are set up here yet; those arrive in later stages
(see docs/SPEC.md §8).
"""

import homeassistant.helpers.config_validation as cv
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Energy Cost Stats integration (no entities, no platforms)."""
    return True
