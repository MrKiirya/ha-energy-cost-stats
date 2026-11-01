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

from .const import DOMAIN, SUBENTRY_TYPE_TARIFF_PLAN
from .engine.plan_codec import plan_from_data
from .engine.tariff import TariffPlan, TariffSchedule, TariffValidationError
from .settings import IntegrationSettings, SettingsError, settings_from_options

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


@dataclass
class RuntimeData:
    """Parsed settings and tariff schedule kept for the lifetime of a loaded entry."""

    settings: IntegrationSettings
    tzinfo: tzinfo
    schedule: TariffSchedule | None


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

    plans: list[TariffPlan] = []
    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_TYPE_TARIFF_PLAN:
            continue
        try:
            plans.append(plan_from_data(subentry.data))
        except TariffValidationError as err:
            raise ConfigEntryError(
                f"Invalid tariff plan {subentry.title!r}: {err}"
            ) from err
    try:
        schedule = TariffSchedule(tuple(plans)) if plans else None
    except TariffValidationError as err:
        raise ConfigEntryError(f"Invalid tariff schedule: {err}") from err

    entry.runtime_data = RuntimeData(settings=settings, tzinfo=tz, schedule=schedule)
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
