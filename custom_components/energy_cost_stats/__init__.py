"""Energy Cost Stats: electricity cost per device, split by tariff zones.

Sets up the single config entry: parses the stored options into typed settings,
builds the tariff configuration from the ``tariff`` subentries plus the applied
history in the options, resolves the time zone and keeps all of it in
``entry.runtime_data``. Options and subentry changes reload the entry through one
update listener, which first reconciles the tariff subentries with the options (see
``_async_reconcile``). Entries of version 1 (``tariff_plan`` subentries) are migrated.
The websocket command and the response-only service are registered once in
``async_setup``; they read the loaded entry. ``async_setup`` also serves the
Lovelace card bundle (``frontend.py``). No entities or platforms are created.
"""

import asyncio
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
    CONF_COMPARE,
    DOMAIN,
    MIGRATED_TARIFF_ID,
    SUBENTRY_TYPE_TARIFF,
    SUBENTRY_TYPE_TARIFF_PLAN,
)
from .engine.plan_codec import format_periods, plan_from_data
from .engine.tariff import TariffSchedule, TariffValidationError
from .engine.tariff_config import TariffConfig, config_from_data, effective_schedule
from .engine.tariff_edit import remove_from_applied
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
        "tariffs": [subentry.data for subentry in _tariff_subentries(entry)],
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
        settings=settings,
        tzinfo=tz,
        tariffs=tariffs,
        schedule=schedule,
    )
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


def _tariff_subentries(entry: ConfigEntry) -> list[ConfigSubentry]:
    """The ``tariff`` subentries in creation order."""
    return [
        subentry
        for subentry in entry.subentries.values()
        if subentry.subentry_type == SUBENTRY_TYPE_TARIFF
    ]


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


def _async_reconcile(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Repair the options after subentry changes; True if something changed.

    Home Assistant lets users delete any subentry, so the options are brought in line
    afterwards. Every change fires the update listener again, which then reloads.
    1. A deleted tariff is removed from the applied history: the previous item
       continues, equal neighbours merge, and when the first item goes the next one
       takes over its start if that tariff has a version then. If nothing remains
       applied but tariffs do, the first remaining tariff is applied from its first
       version.
    2. A deleted tariff is dropped from an explicit compare list.
    3. The first tariff added to an entry without tariffs is applied from its first
       version, so a fresh installation prices its history without further setup.
    """
    runtime: RuntimeData | None = getattr(entry, "runtime_data", None)
    if runtime is None:
        return False
    subentries = _tariff_subentries(entry)
    first_versions = {
        str(subentry.data.get("id")): min(
            str(version["valid_from"]) for version in subentry.data["versions"]
        )
        for subentry in subentries
    }
    options = dict(entry.options)
    pairs = tuple(
        (str(item["from"]), str(item["tariff"]))
        for item in options.get(CONF_APPLIED, [])
    )
    cleaned = remove_from_applied(pairs, first_versions)
    removed_something = any(tariff not in first_versions for _, tariff in pairs)
    if removed_something and not cleaned and first_versions:
        first_id, first_start = next(iter(first_versions.items()))
        cleaned = ((first_start, first_id),)
    elif not runtime.tariffs.tariffs and first_versions and not pairs:
        first_id, first_start = next(iter(first_versions.items()))
        cleaned = ((first_start, first_id),)
        removed_something = True
    if removed_something:
        if cleaned:
            options[CONF_APPLIED] = [
                {"from": start, "tariff": tariff} for start, tariff in cleaned
            ]
        else:
            options.pop(CONF_APPLIED, None)

    compare = options.get(CONF_COMPARE)
    if compare is not None:
        kept = [item for item in compare if item in first_versions]
        if kept != list(compare):
            options[CONF_COMPARE] = kept

    if options == dict(entry.options):
        return False
    hass.config_entries.async_update_entry(entry, options=options)
    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: EnergyCostStatsConfigEntry
) -> None:
    """Reconcile the tariffs, then reload after options (or subentry) changes.

    Newer Home Assistant versions start update listeners eagerly, i.e. in the middle of
    the caller's update. The flows change the options and the subentry in two
    consecutive synchronous calls, so the listener yields once first and then always
    sees both changes.
    """
    await asyncio.sleep(0)
    if _async_reconcile(hass, entry):
        return
    await hass.config_entries.async_reload(entry.entry_id)
