"""Config flow, options flow and config entry setup/unload."""

from collections.abc import Awaitable, Callable
from typing import Any

import pytest
import voluptuous as vol
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_cost_stats.const import DEFAULT_TITLE, DOMAIN

PLUG_01 = "sensor.plug_01"
PLUG_02 = "sensor.plug_02"

EXAMPLE_OPTIONS: dict[str, Any] = {
    "time_zone": "Europe/Berlin",
    "spike_limit": "4",
    "device_spike_limits": {PLUG_01: "10", PLUG_02: None},
    "entities": [PLUG_01, PLUG_02],
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
        "device_spike_limits": {},
        "entities": [],
    }
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
    assert entry.runtime_data.settings.entities == (PLUG_01, PLUG_02)
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


async def test_options_select_entities_and_reload(hass: HomeAssistant):
    _register_sensors(hass)
    entry = await _add_entry(hass, {**EXAMPLE_OPTIONS, "entities": []})
    assert entry.runtime_data.settings.entities == ()

    result = await _call(hass.config_entries.options.async_init, entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    result = await _call(
        hass.config_entries.options.async_configure,
        result["flow_id"],
        {
            "time_zone": "Europe/Berlin",
            "spike_check": True,
            "spike_limit": 4,
            "entities": [PLUG_01, PLUG_02],
            "edit_device_limits": False,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["entities"] == [PLUG_01, PLUG_02]
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.settings.entities == (PLUG_01, PLUG_02)


async def test_options_init_prefills_current_values(hass: HomeAssistant):
    _register_sensors(hass)
    entry = await _add_entry(hass)
    result = await _call(hass.config_entries.options.async_init, entry.entry_id)
    suggested = _suggested(result["data_schema"])
    assert suggested["time_zone"] == "Europe/Berlin"
    assert suggested["spike_check"] is True
    assert suggested["spike_limit"] == 4
    assert suggested["entities"] == [PLUG_01, PLUG_02]


async def test_options_rejects_non_energy_entity(hass: HomeAssistant):
    _register_sensors(hass)
    entry = await _add_entry(
        hass, {**EXAMPLE_OPTIONS, "entities": [], "device_spike_limits": {}}
    )
    user_input = {
        "time_zone": "Europe/Berlin",
        "spike_check": True,
        "spike_limit": 4,
        "entities": ["sensor.power_01"],
        "edit_device_limits": False,
    }
    result = await _call(hass.config_entries.options.async_init, entry.entry_id)
    result = await _call(
        hass.config_entries.options.async_configure, result["flow_id"], user_input
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"entities": "not_energy_entity"}
    assert entry.options["entities"] == []

    hass.states.async_set("sensor.plug_03", "1", {"device_class": "energy"})
    result = await _call(
        hass.config_entries.options.async_configure,
        result["flow_id"],
        {**user_input, "entities": ["sensor.plug_03"]},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["entities"] == ["sensor.plug_03"]


async def test_options_keeps_missing_previous_entity(hass: HomeAssistant):
    entry = await _add_entry(
        hass,
        {**EXAMPLE_OPTIONS, "entities": ["sensor.plug_old"], "device_spike_limits": {}},
    )
    result = await _call(hass.config_entries.options.async_init, entry.entry_id)
    result = await _call(
        hass.config_entries.options.async_configure,
        result["flow_id"],
        {
            "time_zone": "UTC",
            "spike_check": True,
            "spike_limit": 5,
            "entities": ["sensor.plug_old"],
            "edit_device_limits": False,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["entities"] == ["sensor.plug_old"]
    assert entry.options["time_zone"] == "UTC"
    assert entry.options["spike_limit"] == "5"


async def test_options_device_limits(hass: HomeAssistant):
    _register_sensors(hass)
    entry = await _add_entry(
        hass, {**EXAMPLE_OPTIONS, "entities": [], "device_spike_limits": {}}
    )
    result = await _call(hass.config_entries.options.async_init, entry.entry_id)
    result = await _call(
        hass.config_entries.options.async_configure,
        result["flow_id"],
        {
            "time_zone": "Europe/Berlin",
            "spike_check": True,
            "spike_limit": 4,
            "entities": [PLUG_01, PLUG_02],
            "edit_device_limits": True,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "device_limits"
    markers = _markers(result["data_schema"])
    assert set(markers) == {PLUG_01, PLUG_02}
    assert all(isinstance(m, vol.Optional) for m in markers.values())

    result = await _call(
        hass.config_entries.options.async_configure,
        result["flow_id"],
        {PLUG_01: 10, PLUG_02: 0},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["device_spike_limits"] == {PLUG_01: "10", PLUG_02: None}
    await hass.async_block_till_done()

    # Reopen: suggested values reflect the stored overrides (null shown as 0).
    result = await _call(hass.config_entries.options.async_init, entry.entry_id)
    result = await _call(
        hass.config_entries.options.async_configure,
        result["flow_id"],
        {
            "time_zone": "Europe/Berlin",
            "spike_check": True,
            "spike_limit": 4,
            "entities": [PLUG_01, PLUG_02],
            "edit_device_limits": True,
        },
    )
    assert _suggested(result["data_schema"]) == {PLUG_01: 10, PLUG_02: 0}

    # An omitted field means "use the global limit": the key is absent.
    result = await _call(
        hass.config_entries.options.async_configure, result["flow_id"], {PLUG_02: 2.5}
    )
    assert entry.options["device_spike_limits"] == {PLUG_02: "2.5"}


async def test_options_drops_overrides_of_deselected(hass: HomeAssistant):
    _register_sensors(hass)
    entry = await _add_entry(hass)
    result = await _call(hass.config_entries.options.async_init, entry.entry_id)
    result = await _call(
        hass.config_entries.options.async_configure,
        result["flow_id"],
        {
            "time_zone": "Europe/Berlin",
            "spike_check": True,
            "spike_limit": 4,
            "entities": [PLUG_01],
            "edit_device_limits": False,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["device_spike_limits"] == {PLUG_01: "10"}


BAD_LIMITS = [float("nan"), float("inf"), "nan", "inf"]


def _init_input(**changes: Any) -> dict[str, Any]:
    return {
        "time_zone": "Europe/Berlin",
        "spike_check": True,
        "spike_limit": 4,
        "entities": [PLUG_01, PLUG_02],
        "edit_device_limits": False,
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
    result = await _call(hass.config_entries.options.async_init, entry.entry_id)
    try:
        result = await _call(
            hass.config_entries.options.async_configure,
            result["flow_id"],
            _init_input(spike_limit=bad),
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
    result = await _call(hass.config_entries.options.async_init, entry.entry_id)
    result = await _call(
        hass.config_entries.options.async_configure,
        result["flow_id"],
        _init_input(edit_device_limits=True),
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
    result = await _call(hass.config_entries.options.async_init, entry.entry_id)
    user_input = _init_input(spike_check=False)
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


async def test_options_device_limits_without_entities_saves_directly(
    hass: HomeAssistant,
):
    entry = await _add_entry(
        hass, {**EXAMPLE_OPTIONS, "entities": [], "device_spike_limits": {}}
    )
    result = await _call(hass.config_entries.options.async_init, entry.entry_id)
    result = await _call(
        hass.config_entries.options.async_configure,
        result["flow_id"],
        _init_input(entities=[], edit_device_limits=True),
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
