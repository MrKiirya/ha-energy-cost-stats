"""Energy Cost Stats: electricity cost per device, split by tariff zones.

Sets up the single config entry: parses the stored options into typed settings,
builds the tariff configuration from the ``tariff`` subentries plus the applied
history in the options, resolves the time zone and keeps all of it in
``entry.runtime_data``. Options and subentry changes reload the entry through one
update listener. Entries of version 1 (``tariff_plan`` subentries) are migrated.
The websocket command and the response-only service are registered once in
``async_setup``; they read the loaded entry. ``async_setup`` also serves the
Lovelace card bundle (``frontend.py``). No entities or platforms are created.
"""

import logging
from dataclasses import dataclass
from datetime import tzinfo
from types import MappingProxyType
from typing import Any

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .const import (
    CONF_APPLIED,
    DOMAIN,
    MIGRATED_TARIFF_ID,
    SUBENTRY_TYPE_TARIFF,
    SUBENTRY_TYPE_TARIFF_PLAN,
)
from .engine.plan_codec import format_periods, plan_from_data
from .engine.tariff import TariffSchedule, TariffValidationError
from .engine.tariff_config import TariffConfig, config_from_data, effective_schedule
from .frontend import async_register_card
from .services import async_register_services
from .settings import IntegrationSettings, SettingsError, settings_from_options
from .websocket import async_register_websocket

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


@dataclass
class RuntimeData:
    """Parsed settings and tariff schedule kept for the lifetime of a loaded entry."""

    settings: IntegrationSettings
    tzinfo: tzinfo
    tariffs: TariffConfig
    schedule: TariffSchedule | None


type EnergyCostStatsConfigEntry = ConfigEntry[RuntimeData]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the websocket command, the service and the card (no entities)."""
    async_register_websocket(hass)
    async_register_services(hass)
    await async_register_card(hass)
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

    document: dict[str, Any] = {
        "tariffs": [
            subentry.data
            for subentry in entry.subentries.values()
            if subentry.subentry_type == SUBENTRY_TYPE_TARIFF
        ],
        "applied": [
            {"from": start, "tariff": tariff} for start, tariff in settings.applied
        ],
    }
    if settings.compare is not None:
        document["compare"] = list(settings.compare)
    try:
        tariffs = config_from_data(document)
        schedule = effective_schedule(tariffs)
    except TariffValidationError as err:
        raise ConfigEntryError(f"Invalid tariff configuration: {err}") from err

    entry.runtime_data = RuntimeData(
        settings=settings, tzinfo=tz, tariffs=tariffs, schedule=schedule
    )
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


def _plan_to_version(data: Any) -> dict[str, Any]:
    """One version-1 plan as a version with explicit zones (hours as text).

    The reserved volume-band fields of version-1 plans are intentionally dropped:
    the old flow never wrote them and the engine does not price them.
    """
    plan = plan_from_data(data)
    return {
        "valid_from": plan.valid_from.isoformat(),
        "zones": [
            {
                "key": zone.key,
                "name": zone.name,
                "price": format(zone.price, "f"),
                "hours": format_periods(zone.periods),
            }
            for zone in plan.zones
        ],
    }


async def async_migrate_entry(
    hass: HomeAssistant, entry: EnergyCostStatsConfigEntry
) -> bool:
    """Migrate version 1 (``tariff_plan`` subentries) to version 2 (one tariff)."""
    if entry.version > 2:
        return False
    if entry.version == 1:
        old = sorted(
            (
                subentry
                for subentry in entry.subentries.values()
                if subentry.subentry_type == SUBENTRY_TYPE_TARIFF_PLAN
            ),
            key=lambda subentry: str(subentry.data.get("valid_from")),
        )
        options = dict(entry.options)
        new_subentry: ConfigSubentry | None = None
        if old:
            try:
                versions = [_plan_to_version(item.data) for item in old]
            except TariffValidationError as err:
                _LOGGER.error("Cannot migrate the stored tariff plans: %s", err)
                return False
            name = str(old[-1].data["name"])
            new_subentry = ConfigSubentry(
                data=MappingProxyType(
                    {"id": MIGRATED_TARIFF_ID, "name": name, "versions": versions}
                ),
                subentry_type=SUBENTRY_TYPE_TARIFF,
                title=name,
                unique_id=MIGRATED_TARIFF_ID,
            )
            options[CONF_APPLIED] = [
                {"from": versions[0]["valid_from"], "tariff": MIGRATED_TARIFF_ID}
            ]
        for item in old:
            hass.config_entries.async_remove_subentry(entry, item.subentry_id)
        if new_subentry is not None:
            hass.config_entries.async_add_subentry(entry, new_subentry)
        hass.config_entries.async_update_entry(entry, options=options, version=2)
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
