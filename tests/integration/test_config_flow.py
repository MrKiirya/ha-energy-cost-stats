"""Config flow, options flow and config entry setup/unload."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import voluptuous as vol
from homeassistant.components.energy.data import async_get_manager
from homeassistant.config_entries import (
    SOURCE_USER,
    ConfigEntryState,
    ConfigSubentryData,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_cost_stats import report_api
from custom_components.energy_cost_stats.const import DEFAULT_TITLE, DOMAIN

PLUG_01 = "sensor.plug_01"
PLUG_02 = "sensor.plug_02"

EXAMPLE_OPTIONS: dict[str, Any] = {
    "time_zone": "Europe/Berlin",
    "spike_limit": "4",
    "sensors": {
        "mode": "filter",
        "include": {"entity_id": [PLUG_01, PLUG_02]},
        "exclude": {},
        "overrides": {
            PLUG_01: {"spike_limit": "10"},
            PLUG_02: {"spike_limit": None},
        },
    },
}


def _register(hass: HomeAssistant, object_id: str, device_class: str) -> None:
    er.async_get(hass).async_get_or_create(
        "sensor",
        "test",
        object_id,
        suggested_object_id=object_id,
        original_device_class=device_class,  # type: ignore[arg-type]
    )


def _register_sensors(hass: HomeAssistant) -> None:
    _register(hass, "plug_01", "energy")
    _register(hass, "plug_02", "energy")
    _register(hass, "power_01", "power")


async def _call(
    func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any
) -> dict[str, Any]:
    """Run a flow manager call; results are plain dicts (loose typing for tests)."""
    return dict(await func(*args, **kwargs))


async def _add_entry(
    hass: HomeAssistant, options: dict[str, Any] | None = None
) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEFAULT_TITLE,
        data={},
        options=EXAMPLE_OPTIONS if options is None else options,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _options_step(
    hass: HomeAssistant, entry: MockConfigEntry, step: str
) -> dict[str, Any]:
    """Open the options menu and choose ``step``."""
    result = await _call(hass.config_entries.options.async_init, entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    return await _call(
        hass.config_entries.options.async_configure,
        result["flow_id"],
        {"next_step_id": step},
    )


def _markers(schema: vol.Schema) -> dict[str, Any]:
    return {str(key): key for key in schema.schema}


def _suggested(schema: vol.Schema) -> dict[str, Any]:
    return {
        name: key.description["suggested_value"]
        for name, key in _markers(schema).items()
        if key.description and "suggested_value" in key.description
    }


async def test_user_flow_defaults(hass: HomeAssistant):
    await hass.config.async_set_time_zone("Europe/Berlin")
    result = await _call(
        hass.config_entries.flow.async_init, DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    markers = _markers(result["data_schema"])
    assert markers["time_zone"].default() == "Europe/Berlin"
    assert markers["spike_limit"].default() == 4

    result = await _call(
        hass.config_entries.flow.async_configure,
        result["flow_id"],
        {"time_zone": "Europe/Berlin", "spike_check": True, "spike_limit": 4},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Energy Cost Stats"
    assert result["data"] == {}
    assert result["options"] == {
        "time_zone": "Europe/Berlin",
        "spike_limit": "4",
        "sensors": {
            "mode": "filter",
            "include": "all",
            "exclude": {},
            "overrides": {},
        },
    }
    assert "entities" not in result["options"]
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.state is ConfigEntryState.LOADED


async def test_user_flow_spike_check_off(hass: HomeAssistant):
    result = await _call(
        hass.config_entries.flow.async_init, DOMAIN, context={"source": SOURCE_USER}
    )
    result = await _call(
        hass.config_entries.flow.async_configure,
        result["flow_id"],
        {"time_zone": "UTC", "spike_check": False, "spike_limit": 7},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"]["spike_limit"] is None


async def test_user_flow_fractional_spike_limit(hass: HomeAssistant):
    result = await _call(
        hass.config_entries.flow.async_init, DOMAIN, context={"source": SOURCE_USER}
    )
    result = await _call(
        hass.config_entries.flow.async_configure,
        result["flow_id"],
        {"time_zone": "UTC", "spike_check": True, "spike_limit": 4.1},
    )
    assert result["options"]["spike_limit"] == "4.1"


async def test_user_flow_rejects_unknown_time_zone(hass: HomeAssistant):
    result = await _call(
        hass.config_entries.flow.async_init, DOMAIN, context={"source": SOURCE_USER}
    )
    with pytest.raises(InvalidData):
        await _call(
            hass.config_entries.flow.async_configure,
            result["flow_id"],
            {"time_zone": "Not/AZone", "spike_check": True, "spike_limit": 4},
        )


async def test_single_instance(hass: HomeAssistant):
    MockConfigEntry(domain=DOMAIN, data={}, options=EXAMPLE_OPTIONS).add_to_hass(hass)
    result = await _call(
        hass.config_entries.flow.async_init, DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_setup_and_unload(hass: HomeAssistant):
    await hass.config.async_set_time_zone("UTC")
    entry = await _add_entry(hass)
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.settings.sensors.mode.value == "filter"
    assert str(entry.runtime_data.tzinfo) == "Europe/Berlin"
    assert not any(DOMAIN in s.entity_id for s in hass.states.async_all())

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


@pytest.mark.parametrize(
    "changes",
    [{"spike_limit": "abc"}, {"time_zone": "Not/AZone"}],
)
async def test_setup_error_on_corrupt_options(
    hass: HomeAssistant, changes: dict[str, Any]
):
    entry = MockConfigEntry(
        domain=DOMAIN, data={}, options={**EXAMPLE_OPTIONS, **changes}
    )
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_ERROR


async def test_options_general_prefills_current_values(hass: HomeAssistant):
    entry = await _add_entry(hass)
    result = await _options_step(hass, entry, "general")
    suggested = _suggested(result["data_schema"])
    assert suggested["time_zone"] == "Europe/Berlin"
    assert suggested["spike_check"] is True
    assert suggested["spike_limit"] == 4


BAD_LIMITS = [float("nan"), float("inf"), "nan", "inf"]


def _general_input(**changes: Any) -> dict[str, Any]:
    return {
        "time_zone": "Europe/Berlin",
        "spike_check": True,
        "spike_limit": 4,
        "sidebar": {},
        **changes,
    }


@pytest.mark.parametrize("bad", BAD_LIMITS)
async def test_user_flow_rejects_non_finite_limit(hass: HomeAssistant, bad: Any):
    result = await _call(
        hass.config_entries.flow.async_init, DOMAIN, context={"source": SOURCE_USER}
    )
    result = await _call(
        hass.config_entries.flow.async_configure,
        result["flow_id"],
        {"time_zone": "UTC", "spike_check": True, "spike_limit": bad},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"spike_limit": "invalid_limit"}
    assert not hass.config_entries.async_entries(DOMAIN)


@pytest.mark.parametrize("bad", [*BAD_LIMITS, 0])
async def test_options_rejects_invalid_global_limit(hass: HomeAssistant, bad: Any):
    _register_sensors(hass)
    entry = await _add_entry(hass)
    before = dict(entry.options)
    result = await _options_step(hass, entry, "general")
    try:
        result = await _call(
            hass.config_entries.options.async_configure,
            result["flow_id"],
            _general_input(spike_limit=bad),
        )
    except InvalidData:
        return  # the selector itself rejected it (e.g. 0 < min)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"spike_limit": "invalid_limit"}
    assert dict(entry.options) == before


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), "nan"])
async def test_options_rejects_non_finite_device_limit(hass: HomeAssistant, bad: Any):
    _register_sensors(hass)
    entry = await _add_entry(hass)
    before = dict(entry.options)
    result = await _options_step(hass, entry, "sensors")
    result = await _call(
        hass.config_entries.options.async_configure,
        result["flow_id"],
        {"next_step_id": "device_limits"},
    )
    result = await _call(
        hass.config_entries.options.async_configure,
        result["flow_id"],
        {PLUG_01: bad},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "device_limits"
    assert result["errors"] == {PLUG_01: "invalid_limit"}
    assert dict(entry.options) == before


async def test_options_spike_limit_optional_when_check_off(hass: HomeAssistant):
    _register_sensors(hass)
    entry = await _add_entry(hass)
    result = await _options_step(hass, entry, "general")
    user_input = _general_input(spike_check=False)
    del user_input["spike_limit"]
    result = await _call(
        hass.config_entries.options.async_configure, result["flow_id"], user_input
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["spike_limit"] is None


async def test_options_aborts_on_corrupt_options(hass: HomeAssistant):
    entry = MockConfigEntry(
        domain=DOMAIN, data={}, options={**EXAMPLE_OPTIONS, "spike_limit": "abc"}
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_ERROR
    result = await _call(hass.config_entries.options.async_init, entry.entry_id)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "invalid_options"


TARIFF_OPTIONS: dict[str, Any] = {
    "applied": [{"from": "2026-01-01", "tariff": "main"}],
    "compare": ["other"],
}
TARIFFS = [
    {
        "id": tariff_id,
        "name": tariff_id.title(),
        "versions": [
            {
                "valid_from": "2026-01-01",
                "preset": "single_rate",
                "prices": {"t0": "7.40"},
            }
        ],
    }
    for tariff_id in ("main", "other")
]


async def _add_tariff_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEFAULT_TITLE,
        data={},
        options={**EXAMPLE_OPTIONS, **TARIFF_OPTIONS},
        version=3,
        subentries_data=[
            ConfigSubentryData(
                data=data,
                subentry_type="tariff",
                title=data["name"],
                unique_id=data["id"],
            )
            for data in TARIFFS
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_options_flow_keeps_applied_and_compare(hass: HomeAssistant):
    _register_sensors(hass)
    entry = await _add_tariff_entry(hass)
    result = await _options_step(hass, entry, "general")
    result = await _call(
        hass.config_entries.options.async_configure,
        result["flow_id"],
        _general_input(spike_limit=5),
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["spike_limit"] == "5"
    assert entry.options["applied"] == TARIFF_OPTIONS["applied"]
    assert entry.options["compare"] == TARIFF_OPTIONS["compare"]


async def test_options_flow_device_limits_keeps_applied_and_compare(
    hass: HomeAssistant,
):
    _register_sensors(hass)
    entry = await _add_tariff_entry(hass)
    result = await _options_step(hass, entry, "sensors")
    result = await _call(
        hass.config_entries.options.async_configure,
        result["flow_id"],
        {"next_step_id": "device_limits"},
    )
    assert result["step_id"] == "device_limits"
    result = await _call(
        hass.config_entries.options.async_configure, result["flow_id"], {PLUG_01: 7}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["sensors"]["overrides"] == {PLUG_01: {"spike_limit": "7"}}
    assert entry.options["applied"] == TARIFF_OPTIONS["applied"]
    assert entry.options["compare"] == TARIFF_OPTIONS["compare"]


async def test_user_flow_defaults_to_energy_dashboard(hass: HomeAssistant):
    manager = await async_get_manager(hass)
    await manager.async_update({"device_consumption": [{"stat_consumption": PLUG_01}]})
    result = await _call(
        hass.config_entries.flow.async_init, DOMAIN, context={"source": SOURCE_USER}
    )
    result = await _call(
        hass.config_entries.flow.async_configure,
        result["flow_id"],
        {"time_zone": "UTC", "spike_check": True, "spike_limit": 4},
    )
    assert result["options"]["sensors"] == {
        "mode": "energy_dashboard",
        "exclude": {},
        "overrides": {},
    }


V2_OPTIONS: dict[str, Any] = {
    "time_zone": "Europe/Berlin",
    "spike_limit": "4",
    "device_spike_limits": {PLUG_01: "10", PLUG_02: None},
    "entities": [PLUG_01, PLUG_02],
}
MIGRATED_SENSORS: dict[str, Any] = EXAMPLE_OPTIONS["sensors"]


async def _setup_old(hass: HomeAssistant, version: int, **options: Any) -> Any:
    entry = MockConfigEntry(
        domain=DOMAIN, data={}, options={**V2_OPTIONS, **options}, version=version
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_migrate_v2_to_v3(hass: HomeAssistant, seed_statistics: Any):
    start = datetime(2026, 1, 14, 22, tzinfo=UTC)
    sums = {start + timedelta(hours=i): float(i + 1) for i in range(30)}
    await seed_statistics(PLUG_01, sums)
    await seed_statistics(PLUG_02, sums)
    entry = await _setup_old(hass, 2)
    assert entry.version == 3
    assert entry.state is ConfigEntryState.LOADED
    assert entry.options["sensors"] == MIGRATED_SENSORS
    assert "entities" not in entry.options
    assert "device_spike_limits" not in entry.options
    assert entry.runtime_data.settings.sensors.include is not None
    assert entry.runtime_data.settings.sensors.include.entity_id == (PLUG_01, PLUG_02)
    doc = await report_api.async_get_report(
        hass, start="2026-01-15", end="2026-01-16", grouping="total", entities=None
    )
    assert [d["entity_id"] for d in doc["devices"]] == [PLUG_01, PLUG_02]
    assert {d["statistics"] for d in doc["devices"]} == {"ok"}


async def test_migrate_v2_empty_entities_uses_default(hass: HomeAssistant):
    entry = await _setup_old(hass, 2, entities=[], device_spike_limits={PLUG_01: "3"})
    assert entry.version == 3
    assert entry.options["sensors"] == {
        "mode": "filter",
        "include": "all",
        "exclude": {},
        "overrides": {PLUG_01: {"spike_limit": "3"}},
    }


async def test_migrate_v1_through_both_steps(hass: HomeAssistant):
    entry = await _setup_old(hass, 1)
    assert entry.version == 3
    assert entry.state is ConfigEntryState.LOADED
    assert entry.options["sensors"] == MIGRATED_SENSORS


async def test_migrate_refuses_newer_version(hass: HomeAssistant):
    entry = await _setup_old(hass, 4)
    assert entry.state is ConfigEntryState.MIGRATION_ERROR
