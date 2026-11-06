"""Energy Cost Stats: electricity cost per device, split by tariff zones.

Sets up the single config entry: parses the stored options into typed settings,
resolves the time zone and keeps both in ``entry.runtime_data``. Options changes
(and, later, tariff-plan subentry changes) reload the entry through one update
listener. No entities, platforms or services are set up here yet; those arrive in
later stages (see docs/SPEC.md §8).
"""

from dataclasses import dataclass
from datetime import tzinfo

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .settings import IntegrationSettings, SettingsError, settings_from_options

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


@dataclass
class RuntimeData:
    """Parsed settings kept for the lifetime of a loaded entry."""

    settings: IntegrationSettings
    tzinfo: tzinfo


type EnergyCostStatsConfigEntry = ConfigEntry[RuntimeData]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Energy Cost Stats integration (no entities, no platforms)."""
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: EnergyCostStatsConfigEntry
) -> bool:
    """Set up the config entry from its options."""
    try:
        settings = settings_from_options(entry.options)
    except SettingsError as err:
        raise ConfigEntryError(f"Invalid stored options: {err}") from err

    tz = await dt_util.async_get_time_zone(settings.time_zone)
    if tz is None:
        raise ConfigEntryError(f"Unknown time zone: {settings.time_zone!r}")

    entry.runtime_data = RuntimeData(settings=settings, tzinfo=tz)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: EnergyCostStatsConfigEntry
) -> bool:
    """Unload the config entry (there are no platforms)."""
    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: EnergyCostStatsConfigEntry
) -> None:
    """Reload after options (or subentry) changes."""
    await hass.config_entries.async_reload(entry.entry_id)
