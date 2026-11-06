"""Resolve the stored sensor selection against Home Assistant (tasks/020-sensors.md).

The HA-facing half of ``engine/sensors.py``: it reads the Energy dashboard
preferences (the only module importing ``homeassistant.components.energy``), turns the
entity / device / area registries and the state machine into engine candidates, asks
the recorder adapter which ids have energy statistics and lets the engine decide.
Resolution runs on every request, so new sensors need no reconfiguration.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_EXCLUDE,
    CONF_INCLUDE,
    CONF_MODE,
    CONF_OVERRIDES,
    INCLUDE_ALL,
    MODE_ENERGY_DASHBOARD,
    MODE_FILTER,
    PREVIEW_LIMIT,
)
from .engine.sensors import (
    Candidate,
    DashboardDevice,
    Selection,
    SensorSettings,
    select_sensors,
    upstreams,
)
from .recorder_adapter import async_energy_statistic_ids

_ENERGY = "energy"


async def async_dashboard_devices(hass: HomeAssistant) -> tuple[DashboardDevice, ...]:
    """The individual devices of the Energy dashboard, in dashboard order."""
    from homeassistant.components.energy.data import (
        async_get_manager,
    )

    manager = await async_get_manager(hass)
    preferences: Any = manager.data
    if not preferences:
        return ()
    devices: list[DashboardDevice] = []
    for item in preferences.get("device_consumption") or []:
        statistic_id = item.get("stat_consumption")
        if not isinstance(statistic_id, str) or not statistic_id:
            continue
        parent = item.get("included_in_stat")
        devices.append(
            DashboardDevice(
                statistic_id, parent if isinstance(parent, str) and parent else None
            )
        )
    return tuple(devices)


async def async_default_sensor_settings(hass: HomeAssistant) -> dict[str, Any]:
    """The first-setup selection in the stored format."""
    if await async_dashboard_devices(hass):
        return {CONF_MODE: MODE_ENERGY_DASHBOARD, CONF_EXCLUDE: {}, CONF_OVERRIDES: {}}
    return {
        CONF_MODE: MODE_FILTER,
        CONF_INCLUDE: INCLUDE_ALL,
        CONF_EXCLUDE: {},
        CONF_OVERRIDES: {},
    }


def build_candidates(
    hass: HomeAssistant,
    energy_ids: Collection[str],
    extra_ids: Iterable[str] = (),
) -> list[Candidate]:
    """Candidates for every sensor entity, state, statistic id and ``extra_ids``."""
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    area_registry = ar.async_get(hass)

    ids: dict[str, None] = {}
    for entry in entity_registry.entities.values():
        if entry.domain == "sensor":
            ids[entry.entity_id] = None
    for state in hass.states.async_all("sensor"):
        ids[state.entity_id] = None
    for entity_id in (*energy_ids, *extra_ids):
        ids[entity_id] = None

    candidates: list[Candidate] = []
    for entity_id in ids:
        entry = entity_registry.async_get(entity_id)
        state = hass.states.get(entity_id)
        if entry is None and state is None:
            candidates.append(Candidate(entity_id, eligible=False))
            continue
        device_class: Any = None
        device_id = area_id = None
        labels: set[str] = set()
        if entry is not None:
            device_class = entry.device_class or entry.original_device_class
            device_id = entry.device_id
            area_id = entry.area_id
            labels.update(entry.labels)
        if device_class is None and state is not None:
            device_class = state.attributes.get("device_class")
        if device_id is not None and (device := device_registry.async_get(device_id)):
            labels.update(device.labels)
            area_id = area_id or device.area_id
        floor_id = None
        if area_id is not None and (area := area_registry.async_get_area(area_id)):
            floor_id = area.floor_id
            labels.update(area.labels)
        candidates.append(
            Candidate(
                entity_id=entity_id,
                device_id=device_id,
                area_id=area_id,
                floor_id=floor_id,
                labels=frozenset(labels),
                eligible=entity_id in energy_ids and str(device_class) == _ENERGY,
            )
        )
    return candidates


async def async_resolve_sensors(
    hass: HomeAssistant, sensors: SensorSettings
) -> Selection:
    """The sensors selected by ``sensors`` right now."""
    dashboard = await async_dashboard_devices(hass)
    energy_ids = await async_energy_statistic_ids(hass)
    candidates = build_candidates(
        hass, energy_ids, (item.statistic_id for item in dashboard)
    )
    return select_sensors(sensors, candidates, dashboard)


def display_name(
    hass: HomeAssistant, entity_id: str, fallback: str | None = None
) -> str:
    """Name of a sensor: state name, registry name, ``fallback``, else the id."""
    if (state := hass.states.get(entity_id)) is not None:
        return state.name
    registered = er.async_get(hass).async_get(entity_id)
    if registered is not None:
        registered_name = registered.name or registered.original_name
        if registered_name:
            return str(registered_name)
    return fallback or entity_id


def describe_selection(hass: HomeAssistant, selection: Selection) -> tuple[int, str]:
    """``(count, markdown bullets)`` for an options description."""
    nested = upstreams(selection.sensors, selection.parents)
    lines: list[str] = []
    for entity_id in selection.sensors[:PREVIEW_LIMIT]:
        line = f"- `{entity_id}` — {display_name(hass, entity_id)}"
        if (parent := nested.get(entity_id)) is not None:
            line += f" (inside `{parent}`)"
        lines.append(line)
    extra = len(selection.sensors) - PREVIEW_LIMIT
    if extra > 0:
        lines.append(f"- … and {extra} more")
    return len(selection.sensors), "\n".join(lines)
