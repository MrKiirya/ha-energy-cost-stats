"""Sensor resolution against registries, states, statistics and the Energy dashboard."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.components.energy.data import async_get_manager
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import floor_registry as fr
from homeassistant.helpers import label_registry as lr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_cost_stats import sensor_resolver
from custom_components.energy_cost_stats.engine.sensors import (
    DashboardDevice,
    SensorMode,
    SensorSettings,
    SensorTarget,
)

SeedStatistics = Callable[..., Awaitable[None]]
START = datetime(2026, 1, 15, tzinfo=UTC)
SUMS = {START: 1.0, START + timedelta(hours=1): 2.0}


async def set_dashboard(hass: HomeAssistant, devices: list[dict[str, Any]]) -> None:
    manager = await async_get_manager(hass)
    await manager.async_update({"device_consumption": devices})


def register(
    hass: HomeAssistant,
    name: str,
    *,
    device_class: str | None = "energy",
    **kwargs: Any,
) -> er.RegistryEntry:
    return er.async_get(hass).async_get_or_create(
        "sensor",
        "test",
        name,
        suggested_object_id=name,
        original_device_class=device_class,
        **kwargs,
    )


async def test_dashboard_devices(hass: HomeAssistant) -> None:
    assert await sensor_resolver.async_dashboard_devices(hass) == ()
    await set_dashboard(
        hass,
        [
            {"stat_consumption": "sensor.a_energy"},
            {
                "stat_consumption": "sensor.b_energy",
                "included_in_stat": "sensor.a_energy",
            },
        ],
    )
    assert await sensor_resolver.async_dashboard_devices(hass) == (
        DashboardDevice("sensor.a_energy", None),
        DashboardDevice("sensor.b_energy", "sensor.a_energy"),
    )


async def test_default_settings(hass: HomeAssistant) -> None:
    without = await sensor_resolver.async_default_sensor_settings(hass)
    assert without == {
        "mode": "filter",
        "include": "all",
        "exclude": {},
        "overrides": {},
    }
    await set_dashboard(hass, [{"stat_consumption": "sensor.a_energy"}])
    with_devices = await sensor_resolver.async_default_sensor_settings(hass)
    assert with_devices == {"mode": "energy_dashboard", "exclude": {}, "overrides": {}}


async def test_candidates_from_registries(
    hass: HomeAssistant, seed_statistics: SeedStatistics
) -> None:
    config = MockConfigEntry(domain="test")
    config.add_to_hass(hass)
    floor = fr.async_get(hass).async_create("Ground")
    area_reg = ar.async_get(hass)
    hall = area_reg.async_create("Hall")
    area_reg.async_update(hall.id, floor_id=floor.floor_id, labels={"area_label"})
    kitchen = area_reg.async_create("Kitchen")
    label_reg = lr.async_get(hass)
    for label in ("entity_label", "device_label"):
        label_reg.async_create(label)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=config.entry_id, identifiers={("test", "d1")}
    )
    dr.async_get(hass).async_update_device(
        device.id, area_id=hall.id, labels={"device_label"}
    )
    register(hass, "on_device", device_id=device.id)
    own_area = register(hass, "own_area", device_id=device.id)
    er.async_get(hass).async_update_entity(
        own_area.entity_id, area_id=kitchen.id, labels={"entity_label"}
    )
    register(hass, "no_stats")
    register(hass, "not_energy", device_class="power")
    hass.states.async_set("sensor.state_only", "1", {"device_class": "energy"})
    for name in ("on_device", "own_area", "not_energy", "state_only"):
        await seed_statistics(f"sensor.{name}", SUMS)
    await seed_statistics("sensor.orphan", SUMS)

    energy_ids = {
        f"sensor.{n}"
        for n in ("on_device", "own_area", "not_energy", "state_only", "orphan")
    }
    candidates = {
        c.entity_id: c for c in sensor_resolver.build_candidates(hass, energy_ids)
    }
    on_device = candidates["sensor.on_device"]
    assert on_device.eligible
    assert (on_device.device_id, on_device.area_id) == (device.id, hall.id)
    assert on_device.floor_id == floor.floor_id
    assert on_device.labels == {"device_label", "area_label"}
    own = candidates["sensor.own_area"]
    assert own.area_id == kitchen.id
    assert own.floor_id is None
    assert own.labels == {"entity_label", "device_label"}
    assert candidates["sensor.state_only"].eligible
    assert not candidates["sensor.no_stats"].eligible
    assert not candidates["sensor.not_energy"].eligible
    assert not candidates["sensor.orphan"].eligible


async def test_resolve_filter_by_area_and_label(
    hass: HomeAssistant, seed_statistics: SeedStatistics
) -> None:
    area = ar.async_get(hass).async_create("Kitchen")
    lr.async_get(hass).async_create("Tracked")
    one = register(hass, "plug_01")
    er.async_get(hass).async_update_entity(one.entity_id, area_id=area.id)
    two = register(hass, "plug_02")
    er.async_get(hass).async_update_entity(two.entity_id, labels={"tracked"})
    register(hass, "plug_03")
    for entry in (one, two):
        await seed_statistics(entry.entity_id, SUMS)
    await seed_statistics("sensor.plug_03", SUMS)

    def settings(include: SensorTarget | None) -> SensorSettings:
        return SensorSettings(mode=SensorMode.FILTER, include=include)

    resolve = sensor_resolver.async_resolve_sensors
    assert (await resolve(hass, settings(None))).sensors == (
        "sensor.plug_01",
        "sensor.plug_02",
        "sensor.plug_03",
    )
    by_area = await resolve(hass, settings(SensorTarget(area_id=(area.id,))))
    assert by_area.sensors == ("sensor.plug_01",)
    by_label = await resolve(hass, settings(SensorTarget(label_id=("tracked",))))
    assert by_label.sensors == ("sensor.plug_02",)


async def test_new_sensor_picked_up_dynamically(
    hass: HomeAssistant, seed_statistics: SeedStatistics
) -> None:
    settings = SensorSettings(mode=SensorMode.FILTER)
    register(hass, "plug_01")
    await seed_statistics("sensor.plug_01", SUMS)
    first = await sensor_resolver.async_resolve_sensors(hass, settings)
    assert first.sensors == ("sensor.plug_01",)
    register(hass, "plug_02")
    await seed_statistics("sensor.plug_02", SUMS)
    second = await sensor_resolver.async_resolve_sensors(hass, settings)
    assert second.sensors == ("sensor.plug_01", "sensor.plug_02")


async def test_resolve_dashboard_mode_with_parents(
    hass: HomeAssistant, seed_statistics: SeedStatistics
) -> None:
    await set_dashboard(
        hass,
        [
            {
                "stat_consumption": "sensor.b_energy",
                "included_in_stat": "sensor.a_energy",
            },
            {"stat_consumption": "sensor.a_energy"},
        ],
    )
    selection = await sensor_resolver.async_resolve_sensors(
        hass, SensorSettings(mode=SensorMode.ENERGY_DASHBOARD)
    )
    assert selection.sensors == ("sensor.b_energy", "sensor.a_energy")
    assert dict(selection.parents) == {"sensor.b_energy": "sensor.a_energy"}
    count, text = sensor_resolver.describe_selection(hass, selection)
    assert count == 2
    assert "- `sensor.b_energy` — sensor.b_energy (inside `sensor.a_energy`)" in text
