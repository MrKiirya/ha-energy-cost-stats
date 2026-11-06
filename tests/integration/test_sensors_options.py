"""Options flow: sensor selection, preview and per-sensor limits (task 020)."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from homeassistant.config_entries import ConfigEntryState, ConfigSubentryData
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_cost_stats import config_flow
from custom_components.energy_cost_stats.const import DEFAULT_TITLE, DOMAIN

SeedStatistics = Callable[..., Awaitable[None]]
SetDashboard = Callable[[list[dict[str, Any]]], Awaitable[None]]
PLUG_01 = "sensor.plug_01"
PLUG_02 = "sensor.plug_02"
START = datetime(2026, 1, 15, tzinfo=UTC)
SUMS = {START: 1.0, START + timedelta(hours=1): 2.0}
FILTER_ALL: dict[str, Any] = {
    "mode": "filter",
    "include": "all",
    "exclude": {},
    "overrides": {},
}
DASHBOARD: dict[str, Any] = {
    "mode": "energy_dashboard",
    "exclude": {},
    "overrides": {},
}


async def _call(func: Callable[..., Awaitable[Any]], *args: Any) -> dict[str, Any]:
    return dict(await func(*args))


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


async def add_entry(
    hass: HomeAssistant, sensors: dict[str, Any], *, tariffs: bool = False
) -> MockConfigEntry:
    options: dict[str, Any] = {
        "time_zone": "Europe/Berlin",
        "spike_limit": "4",
        "sensors": sensors,
        "panel": {"show": True, "title": "Cost", "icon": "mdi:cash"},
    }
    if tariffs:
        options["applied"] = [{"from": "2026-01-01", "tariff": "main"}]
        options["compare"] = ["other"]
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEFAULT_TITLE,
        data={},
        options=options,
        version=3,
        subentries_data=[
            ConfigSubentryData(
                data=data,
                subentry_type="tariff",
                title=data["name"],
                unique_id=data["id"],
            )
            for data in TARIFFS
        ]
        if tariffs
        else [],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def energy_sensor(
    hass: HomeAssistant, seed: SeedStatistics, entity_id: str, **update: Any
) -> None:
    name = entity_id.split(".")[1]
    er.async_get(hass).async_get_or_create(
        "sensor",
        "test",
        name,
        suggested_object_id=name,
        original_device_class="energy",  # type: ignore[arg-type]
    )
    if update:
        er.async_get(hass).async_update_entity(entity_id, **update)
    await seed(entity_id, SUMS)


async def open_menu(hass: HomeAssistant, entry: MockConfigEntry) -> dict[str, Any]:
    result = await _call(hass.config_entries.options.async_init, entry.entry_id)
    return await _next(hass, result, "sensors")


async def _next(hass: HomeAssistant, result: dict[str, Any], step: str) -> Any:
    assert result["type"] is FlowResultType.MENU
    return await _call(
        hass.config_entries.options.async_configure,
        result["flow_id"],
        {"next_step_id": step},
    )


async def _submit(
    hass: HomeAssistant, result: dict[str, Any], data: dict[str, Any]
) -> dict[str, Any]:
    return await _call(
        hass.config_entries.options.async_configure, result["flow_id"], data
    )


def _form_input(mode: str = "filter", **changes: Any) -> dict[str, Any]:
    return {
        "mode": mode,
        "include": {"all": False},
        "exclude": {},
        **changes,
    }


def _suggested(schema: Any) -> dict[str, Any]:
    found: dict[str, Any] = {}
    for key, value in schema.schema.items():
        if hasattr(value, "schema") and hasattr(value.schema, "schema"):
            found[str(key)] = _suggested(value.schema)
        elif key.description and "suggested_value" in key.description:
            found[str(key)] = key.description["suggested_value"]
    return found


async def test_sensors_menu_shows_count_and_list(
    hass: HomeAssistant, seed_statistics: SeedStatistics
) -> None:
    await energy_sensor(hass, seed_statistics, PLUG_01)
    await energy_sensor(hass, seed_statistics, PLUG_02)
    entry = await add_entry(hass, FILTER_ALL)
    result = await open_menu(hass, entry)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "sensors"
    assert result["menu_options"] == ["sensors_select", "device_limits"]
    placeholders = result["description_placeholders"]
    assert placeholders["count"] == "2"
    assert placeholders["sensors"].splitlines() == [
        f"- `{PLUG_01}` — {PLUG_01}",
        f"- `{PLUG_02}` — {PLUG_02}",
    ]


async def test_sensors_menu_nested_and_capped(
    hass: HomeAssistant, set_dashboard: SetDashboard
) -> None:
    ids = [f"sensor.meter_{i:02d}_energy" for i in range(32)]
    devices: list[dict[str, Any]] = [{"stat_consumption": ids[0]}]
    devices += [
        {"stat_consumption": entity_id, "included_in_stat": ids[0]}
        for entity_id in ids[1:]
    ]
    await set_dashboard(devices)
    entry = await add_entry(hass, DASHBOARD)
    result = await open_menu(hass, entry)
    placeholders = result["description_placeholders"]
    assert placeholders["count"] == "32"
    lines = placeholders["sensors"].splitlines()
    assert len(lines) == 31
    assert lines[0] == f"- `{ids[0]}` — {ids[0]}"
    assert lines[1] == f"- `{ids[1]}` — {ids[1]} (inside `{ids[0]}`)"
    assert lines[-1] == "- … and 2 more"


async def test_select_filter_preview_then_save(
    hass: HomeAssistant, seed_statistics: SeedStatistics
) -> None:
    area = ar.async_get(hass).async_create("Kitchen")
    await energy_sensor(hass, seed_statistics, PLUG_01, area_id=area.id)
    await energy_sensor(hass, seed_statistics, PLUG_02)
    await energy_sensor(hass, seed_statistics, "sensor.heater_energy")
    overrides = {PLUG_01: {"spike_limit": "7"}}
    entry = await add_entry(hass, {**FILTER_ALL, "overrides": overrides})
    result = await _next(hass, await open_menu(hass, entry), "sensors_select")
    assert result["step_id"] == "sensors_select"
    result = await _submit(
        hass,
        result,
        _form_input(
            include={
                "all": False,
                "target": {"area_id": [area.id]},
                "entity_globs": ["sensor.heater_*", "sensor.heater_*"],
            },
            exclude={"target": {"entity_id": [PLUG_02]}},
        ),
    )
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "sensors_preview"
    assert result["menu_options"] == ["sensors_save", "sensors_select"]
    assert result["description_placeholders"]["count"] == "2"
    assert entry.options["sensors"]["include"] == "all"  # nothing saved yet

    before = dict(entry.options)
    result = await _next(hass, result, "sensors_save")
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["sensors"] == {
        "mode": "filter",
        "include": {
            "area_id": [area.id],
            "entity_globs": ["sensor.heater_*"],
        },
        "exclude": {"entity_id": [PLUG_02]},
        "overrides": overrides,
    }
    for key in ("panel", "time_zone", "spike_limit"):
        assert entry.options[key] == before[key]
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.settings.sensors.include is not None


async def test_preview_back_to_edit_prefills_candidate(
    hass: HomeAssistant, seed_statistics: SeedStatistics
) -> None:
    await energy_sensor(hass, seed_statistics, PLUG_01)
    entry = await add_entry(hass, FILTER_ALL)
    result = await _next(hass, await open_menu(hass, entry), "sensors_select")
    assert _suggested(result["data_schema"])["mode"] == "filter"
    assert _suggested(result["data_schema"])["include"]["all"] is True
    result = await _submit(
        hass,
        result,
        _form_input(
            include={"all": False, "target": {"entity_id": [PLUG_01]}},
            exclude={"entity_globs": ["sensor.x_*"]},
        ),
    )
    result = await _next(hass, result, "sensors_select")
    assert result["step_id"] == "sensors_select"
    suggested = _suggested(result["data_schema"])
    assert suggested["include"]["all"] is False
    assert suggested["include"]["target"] == {"entity_id": [PLUG_01]}
    assert suggested["exclude"]["entity_globs"] == ["sensor.x_*"]
    assert entry.options["sensors"]["include"] == "all"


async def test_select_energy_dashboard_mode(
    hass: HomeAssistant, set_dashboard: SetDashboard
) -> None:
    await set_dashboard([{"stat_consumption": PLUG_01}])
    entry = await add_entry(
        hass,
        {
            **FILTER_ALL,
            "exclude": {"entity_id": [PLUG_02]},
            "include": {"entity_id": [PLUG_01]},
        },
    )
    result = await _next(hass, await open_menu(hass, entry), "sensors_select")
    result = await _submit(
        hass,
        result,
        _form_input(
            "energy_dashboard",
            exclude={"target": {"entity_id": [PLUG_02]}},
        ),
    )
    assert result["step_id"] == "sensors_preview"
    assert result["description_placeholders"]["count"] == "1"
    result = await _next(hass, result, "sensors_save")
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["sensors"] == {
        "mode": "energy_dashboard",
        "exclude": {"entity_id": [PLUG_02]},
        "overrides": {},
    }


async def test_select_errors(hass: HomeAssistant) -> None:
    entry = await add_entry(hass, FILTER_ALL)
    before = dict(entry.options)
    result = await _next(hass, await open_menu(hass, entry), "sensors_select")

    result = await _submit(hass, result, _form_input("energy_dashboard"))
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"mode": "no_dashboard_devices"}

    result = await _submit(hass, result, _form_input())
    assert result["errors"] == {"base": "nothing_included"}

    result = await _submit(
        hass,
        result,
        _form_input(include={"all": False, "entity_globs": ["Sensor.*"]}),
    )
    assert result["errors"] == {"base": "invalid_glob"}
    assert result["description_placeholders"]["glob"] == "Sensor.*"
    assert dict(entry.options) == before


async def test_device_limits_fields_and_save(
    hass: HomeAssistant, seed_statistics: SeedStatistics
) -> None:
    await energy_sensor(hass, seed_statistics, PLUG_01)
    await energy_sensor(hass, seed_statistics, PLUG_02)
    entry = await add_entry(
        hass,
        {
            **FILTER_ALL,
            "exclude": {"entity_id": [PLUG_02]},
            "overrides": {
                PLUG_02: {"spike_limit": "2"},
                "sensor.gone": {"spike_limit": None},
                "sensor.other": {"spike_limit": "9"},
            },
        },
    )
    result = await _next(hass, await open_menu(hass, entry), "device_limits")
    assert result["step_id"] == "device_limits"
    fields = {str(key) for key in result["data_schema"].schema}
    assert fields == {PLUG_01, PLUG_02, "sensor.gone", "sensor.other"}
    assert _suggested(result["data_schema"]) == {
        PLUG_02: 2,
        "sensor.gone": 0,
        "sensor.other": 9,
    }
    result = await _submit(hass, result, {PLUG_01: 10, PLUG_02: 0, "sensor.other": 9})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["sensors"]["overrides"] == {
        PLUG_01: {"spike_limit": "10"},
        PLUG_02: {"spike_limit": None},
        "sensor.other": {"spike_limit": "9"},
    }


async def test_device_limits_invalid_value(
    hass: HomeAssistant, seed_statistics: SeedStatistics
) -> None:
    await energy_sensor(hass, seed_statistics, PLUG_01)
    entry = await add_entry(hass, FILTER_ALL)
    before = dict(entry.options)
    result = await _next(hass, await open_menu(hass, entry), "device_limits")
    result = await _submit(hass, result, {PLUG_01: float("nan")})
    assert result["errors"] == {PLUG_01: "invalid_limit"}
    assert dict(entry.options) == before


async def test_device_limits_no_sensors_aborts(hass: HomeAssistant) -> None:
    entry = await add_entry(hass, FILTER_ALL)
    result = await _next(hass, await open_menu(hass, entry), "device_limits")
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_sensors"


async def test_save_uses_current_options(
    hass: HomeAssistant, seed_statistics: SeedStatistics
) -> None:
    await energy_sensor(hass, seed_statistics, PLUG_01)
    entry = await add_entry(hass, FILTER_ALL)
    result = await _next(hass, await open_menu(hass, entry), "sensors_select")
    result = await _submit(
        hass,
        result,
        _form_input(include={"all": False, "target": {"entity_id": [PLUG_01]}}),
    )
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, "spike_limit": "5"}
    )
    await hass.async_block_till_done()
    assert result["step_id"] == "sensors_preview"
    result = await _next(hass, result, "sensors_save")
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["spike_limit"] == "5"
    assert entry.options["sensors"]["include"] == {"entity_id": [PLUG_01]}


async def test_preview_and_save_keep_applied_and_compare(
    hass: HomeAssistant, seed_statistics: SeedStatistics
) -> None:
    await energy_sensor(hass, seed_statistics, PLUG_01)
    entry = await add_entry(hass, FILTER_ALL, tariffs=True)
    result = await _next(hass, await open_menu(hass, entry), "sensors_select")
    result = await _submit(
        hass,
        result,
        _form_input(include={"all": False, "target": {"entity_id": [PLUG_01]}}),
    )
    result = await _next(hass, result, "sensors_save")
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["applied"] == [{"from": "2026-01-01", "tariff": "main"}]
    assert entry.options["compare"] == ["other"]
    assert entry.options["sensors"]["include"] == {"entity_id": [PLUG_01]}


async def test_select_prefills_stored_target_and_exclude(
    hass: HomeAssistant, seed_statistics: SeedStatistics
) -> None:
    await energy_sensor(hass, seed_statistics, PLUG_01)
    stored = {
        "mode": "filter",
        "include": {
            "entity_id": [PLUG_01],
            "area_id": ["kitchen"],
            "entity_globs": ["sensor.p*"],
        },
        "exclude": {"label_id": ["meter"], "entity_globs": ["sensor.sub_*"]},
        "overrides": {},
    }
    entry = await add_entry(hass, stored)
    result = await _next(hass, await open_menu(hass, entry), "sensors_select")
    assert _suggested(result["data_schema"]) == {
        "mode": "filter",
        "include": {
            "all": False,
            "target": {"entity_id": [PLUG_01], "area_id": ["kitchen"]},
            "entity_globs": ["sensor.p*"],
        },
        "exclude": {
            "target": {"label_id": ["meter"]},
            "entity_globs": ["sensor.sub_*"],
        },
    }


def _resolve(value: str) -> str | None:
    return {"uuid-1": PLUG_01}.get(value, value if "." in value else None)


def test_target_normalization() -> None:
    target = config_flow._target_from_input(
        {
            "target": {
                "area_id": "kitchen",
                "device_id": ["d1", "d1"],
                "entity_id": ["uuid-1", PLUG_01],
            },
            "entity_globs": [" sensor.a* ", "sensor.a*", ""],
        },
        _resolve,
    )
    assert target.area_id == ("kitchen",)
    assert target.device_id == ("d1",)
    assert target.entity_id == (PLUG_01,)
    assert target.entity_globs == ("sensor.a*",)


@pytest.mark.parametrize(
    "target",
    [
        {"area_id": 5},
        {"area_id": ["kitchen", {"template": "x"}]},
        {"area_id": "all"},
        {"entity_id": ["none"]},
        {"entity_id": ["unknown-uuid"]},
    ],
)
def test_target_rejects_unsupported_values(target: dict[str, Any]) -> None:
    with pytest.raises(config_flow._InvalidTarget):
        config_flow._target_from_input({"target": target}, _resolve)
    with pytest.raises(config_flow._InvalidTarget):
        config_flow._target_from_input({"target": "all"}, _resolve)


async def test_select_resolves_registry_ids_and_rejects_keywords(
    hass: HomeAssistant, seed_statistics: SeedStatistics
) -> None:
    await energy_sensor(hass, seed_statistics, PLUG_01)
    registry_id = er.async_get(hass).async_get(PLUG_01).id  # type: ignore[union-attr]
    entry = await add_entry(hass, FILTER_ALL)
    result = await _next(hass, await open_menu(hass, entry), "sensors_select")
    result = await _submit(
        hass,
        result,
        _form_input(include={"all": False, "target": {"entity_id": ["all"]}}),
    )
    assert result["errors"] == {"base": "invalid_target"}
    result = await _submit(
        hass,
        result,
        _form_input(include={"all": False, "target": {"entity_id": [registry_id]}}),
    )
    assert result["step_id"] == "sensors_preview"
    result = await _next(hass, result, "sensors_save")
    assert entry.options["sensors"]["include"] == {"entity_id": [PLUG_01]}


async def test_empty_selection_lists_nothing(hass: HomeAssistant) -> None:
    entry = await add_entry(hass, FILTER_ALL)
    result = await open_menu(hass, entry)
    assert result["description_placeholders"] == {"count": "0", "sensors": ""}
