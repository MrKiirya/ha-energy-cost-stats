"""YAML mode: the ``energy_cost_stats:`` block is imported into the config entry.

When the block is present it is the single source of truth: it is validated strictly
(``yaml_config``), written into the single config entry (options plus one ``tariff``
subentry per tariff) and the options flow becomes read-only. The block is applied at
startup and by the admin action ``energy_cost_stats.reload``. An invalid block never
takes the integration down: the entry keeps its last valid configuration and the error
is shown as a repair issue, in the log and, for a reload, as the action error.
See docs/SPEC.md §2.
"""

import copy
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.issue_registry import (
    IssueSeverity,
    async_create_issue,
    async_delete_issue,
)
from homeassistant.helpers.reload import async_integration_yaml_config
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util
from homeassistant.util.hass_dict import HassKey
from homeassistant.util.yaml import dump

from .const import (
    CONF_SENSORS,
    CONF_TIME_ZONE,
    DOMAIN,
    ERR_YAML_INVALID,
    ISSUE_INVALID_YAML,
    SERVICE_RELOAD,
    SUBENTRY_TYPE_TARIFF,
)
from .sensor_resolver import async_default_sensor_settings
from .yaml_config import (
    YamlConfigError,
    YamlDocument,
    document_from_yaml,
    export_document,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class YamlState:
    """The outcome of the last load of the YAML block."""

    present: bool
    document: YamlDocument | None = None
    error: str | None = None


DATA_YAML: HassKey[YamlState] = HassKey(f"{DOMAIN}_yaml")
# Entries whose configuration was already written from YAML in this process.
DATA_SYNCED: HassKey[set[str]] = HassKey(f"{DOMAIN}_yaml_synced")


def get_yaml_state(hass: HomeAssistant) -> YamlState:
    """The current state (no block until the first load)."""
    return hass.data.get(DATA_YAML, YamlState(present=False))


def is_yaml_mode(hass: HomeAssistant) -> bool:
    """Whether the YAML block was present at the last load."""
    return get_yaml_state(hass).present


def render_yaml(
    options: Mapping[str, Any], tariff_data: list[Mapping[str, Any]]
) -> str:
    """The configuration as a ready-to-copy ``energy_cost_stats:`` block."""
    return dump({DOMAIN: export_document(options, tariff_data)})


def _entry(hass: HomeAssistant) -> ConfigEntry | None:
    entries = hass.config_entries.async_entries(DOMAIN)
    return entries[0] if entries else None


async def _async_state_from_block(hass: HomeAssistant, raw: Any) -> YamlState:
    """Validate the block content; errors become ``YamlState.error``."""
    entry = _entry(hass)
    default_time_zone = (
        str(entry.options.get(CONF_TIME_ZONE) or hass.config.time_zone)
        if entry is not None
        else hass.config.time_zone
    )
    wants_default_sensors = not isinstance(raw, Mapping) or CONF_SENSORS not in raw
    default_sensors = (
        await async_default_sensor_settings(hass) if wants_default_sensors else {}
    )
    try:
        document = document_from_yaml(
            raw, default_time_zone=default_time_zone, default_sensors=default_sensors
        )
    except YamlConfigError as err:
        return YamlState(present=True, error=str(err))
    time_zone = document.options[CONF_TIME_ZONE]
    if await dt_util.async_get_time_zone(time_zone) is None:
        return YamlState(
            present=True, error=f"time_zone: unknown time zone {time_zone!r}"
        )
    return YamlState(present=True, document=document)


async def async_load_yaml_state(hass: HomeAssistant, config: ConfigType) -> YamlState:
    """Read the block from a processed Home Assistant configuration."""
    if DOMAIN not in config:
        return YamlState(present=False)
    return await _async_state_from_block(hass, config[DOMAIN])


def _report(hass: HomeAssistant, message: str) -> None:
    _LOGGER.error("Invalid %s configuration: %s", DOMAIN, message)
    async_create_issue(
        hass,
        DOMAIN,
        ISSUE_INVALID_YAML,
        is_fixable=False,
        severity=IssueSeverity.ERROR,
        translation_key=ISSUE_INVALID_YAML,
        translation_placeholders={"error": message},
    )


async def async_apply_yaml_state(
    hass: HomeAssistant, state: YamlState, *, startup: bool = False
) -> None:
    """Make the loaded state current: issue, entry import or reload.

    At startup the entry is set up after ``async_setup`` anyway, so an existing entry
    is not reloaded, and the import flow runs as a task (the entry setup waits for the
    component setup that is still running).
    """
    previous = get_yaml_state(hass)
    hass.data[DATA_YAML] = state
    entry = _entry(hass)
    if not state.present:
        async_delete_issue(hass, DOMAIN, ISSUE_INVALID_YAML)
        # The entry is editable in the UI again; a later block replaces those edits.
        hass.data.get(DATA_SYNCED, set()).clear()
        if previous.present and entry is not None and not startup:
            await hass.config_entries.async_reload(entry.entry_id)
        return
    if state.document is None:
        _report(hass, state.error or "unknown error")
        return
    async_delete_issue(hass, DOMAIN, ISSUE_INVALID_YAML)
    if entry is not None:
        if not startup:
            await hass.config_entries.async_reload(entry.entry_id)
        return
    flow = hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_IMPORT}, data=dict(state.document.options)
    )
    if startup:
        hass.async_create_task(flow, f"{DOMAIN} YAML import")
    else:
        await flow


def _tariff_subentries(entry: ConfigEntry) -> dict[str, ConfigSubentry]:
    return {
        str(subentry.unique_id or subentry.data.get("id")): subentry
        for subentry in entry.subentries.values()
        if subentry.subentry_type == SUBENTRY_TYPE_TARIFF
    }


@callback
def async_sync_entry(
    hass: HomeAssistant, entry: ConfigEntry, document: YamlDocument
) -> None:
    """Write the YAML document into the entry: options and the tariff subentries."""
    existing = _tariff_subentries(entry)
    wanted = {str(tariff["id"]): tariff for tariff in document.tariffs}
    changed = dict(entry.options) != document.options or any(
        key not in wanted
        or dict(existing[key].data) != wanted[key]
        or existing[key].title != wanted[key]["name"]
        for key in existing
    )
    changed = changed or any(key not in existing for key in wanted)
    synced = hass.data.setdefault(DATA_SYNCED, set())
    # A fresh import has equal options and no subentries yet; anything else that
    # differs is a configuration made elsewhere (the UI) that is about to be replaced.
    has_content = bool(existing) or dict(entry.options) != document.options
    if changed and has_content and entry.entry_id not in synced:
        _LOGGER.warning(
            "The YAML configuration replaces the configuration made in the UI; "
            "use Export to YAML in the options to keep a copy"
        )
    synced.add(entry.entry_id)

    if dict(entry.options) != document.options:
        hass.config_entries.async_update_entry(entry, options=document.options)
    for key, subentry in existing.items():
        if key not in wanted:
            hass.config_entries.async_remove_subentry(entry, subentry.subentry_id)
    for key, tariff in wanted.items():
        name = str(tariff["name"])
        if key in existing:
            subentry = existing[key]
            if dict(subentry.data) != tariff or subentry.title != name:
                hass.config_entries.async_update_subentry(
                    entry, subentry, data=tariff, title=name
                )
        else:
            hass.config_entries.async_add_subentry(
                entry,
                ConfigSubentry(
                    data=MappingProxyType(copy.deepcopy(tariff)),
                    subentry_type=SUBENTRY_TYPE_TARIFF,
                    title=name,
                    unique_id=key,
                ),
            )


@callback
def async_register_reload_service(hass: HomeAssistant) -> None:
    """Register ``energy_cost_stats.reload`` (admin only)."""

    async def reload_yaml(call: ServiceCall) -> None:
        state: YamlState
        try:
            config = await async_integration_yaml_config(hass, DOMAIN)
        except HomeAssistantError as err:
            state = YamlState(present=True, error=str(err))
        else:
            state = (
                YamlState(
                    present=True,
                    error="the configuration could not be loaded, see the log",
                )
                if config is None
                else await async_load_yaml_state(hass, config)
            )
        await async_apply_yaml_state(hass, state)
        if state.error is not None:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=ERR_YAML_INVALID,
                translation_placeholders={"error": state.error},
            )

    async_register_admin_service(hass, DOMAIN, SERVICE_RELOAD, reload_yaml)
