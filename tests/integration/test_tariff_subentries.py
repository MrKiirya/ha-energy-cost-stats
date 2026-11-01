"""Tariff plans as config subentries (tasks/010-tariff-plan-subentries.md)."""

from collections.abc import Awaitable, Callable
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
import voluptuous as vol
from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    SOURCE_USER,
    ConfigEntryState,
    ConfigSubentryData,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_cost_stats.config_flow import (
    EnergyCostStatsConfigFlow,
)
from custom_components.energy_cost_stats.const import DEFAULT_TITLE, DOMAIN
from custom_components.energy_cost_stats.subentry_flow import TariffPlanSubentryFlow

OPTIONS: dict[str, Any] = {
    "time_zone": "Europe/Berlin",
    "spike_limit": "4",
    "device_spike_limits": {},
    "entities": [],
}

PLAN_A: dict[str, Any] = {
    "valid_from": "2026-01-01",
    "name": "Two-zone",
    "zones": [
        {
            "key": "t1",
            "name": "Day",
            "price": "10.30",
            "periods": [["07:00", "23:00"]],
        },
        {
            "key": "t2",
            "name": "Night",
            "price": "4.43",
            "periods": [["23:00", "07:00"]],
        },
    ],
}


def _plan_b() -> dict[str, Any]:
    data = {**PLAN_A, "valid_from": "2026-07-01"}
    data["zones"] = [{**zone} for zone in PLAN_A["zones"]]
    data["zones"][0]["price"] = "11.00"
    return data


def _subentry(data: dict[str, Any]) -> ConfigSubentryData:
    return ConfigSubentryData(
        data=data,
        subentry_type="tariff_plan",
        title=f"{data['valid_from']} · {data['name']}",
        unique_id=data["valid_from"],
    )


async def _add_entry(
    hass: HomeAssistant, plans: list[dict[str, Any]] | None = None
) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEFAULT_TITLE,
        data={},
        options=OPTIONS,
        subentries_data=[_subentry(plan) for plan in plans or []],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _call(
    func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any
) -> dict[str, Any]:
    result = dict(await func(*args, **kwargs))
    return result


async def _init(
    hass: HomeAssistant, entry: MockConfigEntry, **context: Any
) -> dict[str, Any]:
    return await _call(
        hass.config_entries.subentries.async_init,
        (entry.entry_id, "tariff_plan"),
        context=context or {"source": SOURCE_USER},
    )


async def _configure(
    hass: HomeAssistant, result: dict[str, Any], user_input: dict[str, Any]
) -> dict[str, Any]:
    return await _call(
        hass.config_entries.subentries.async_configure, result["flow_id"], user_input
    )


def _fields(result: dict[str, Any]) -> list[str]:
    schema: vol.Schema = result["data_schema"]
    return [str(key) for key in schema.schema]


def _suggested(result: dict[str, Any]) -> dict[str, Any]:
    schema: vol.Schema = result["data_schema"]
    return {
        str(key): key.description["suggested_value"]
        for key in schema.schema
        if key.description and "suggested_value" in key.description
    }


async def _plan_form(
    hass: HomeAssistant, entry: MockConfigEntry, preset: str
) -> dict[str, Any]:
    result = await _init(hass, entry)
    assert result["step_id"] == "preset"
    return await _configure(hass, result, {"preset": preset})


TWO_ZONE_INPUT = {
    "valid_from": "2026-01-01",
    "name": "Two-zone",
    "t1_name": "Day",
    "t1_price": "10,30",
    "t1_periods": "07:00-23:00",
    "t2_name": "Night",
    "t2_price": "4.43",
    "t2_periods": "23:00-07:00",
}


def _subentries(entry: MockConfigEntry) -> list[Any]:
    return sorted(entry.subentries.values(), key=lambda s: s.unique_id or "")


def _schedule(entry: MockConfigEntry) -> Any:
    return entry.runtime_data.schedule


async def test_subentry_type_registered(hass: HomeAssistant):
    entry = await _add_entry(hass)
    assert EnergyCostStatsConfigFlow.async_get_supported_subentry_types(entry) == {
        "tariff_plan": TariffPlanSubentryFlow
    }
    assert hasattr(TariffPlanSubentryFlow, "async_step_reconfigure")


async def test_first_plan_goes_to_preset(hass: HomeAssistant):
    entry = await _add_entry(hass)
    result = await _init(hass, entry)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "preset"


async def test_add_two_zone_from_preset(hass: HomeAssistant):
    entry = await _add_entry(hass)
    assert _schedule(entry) is None
    form = await _plan_form(hass, entry, "ru_two_zone")
    assert form["type"] is FlowResultType.FORM
    assert form["step_id"] == "plan"
    assert _fields(form) == [
        "valid_from",
        "name",
        "t1_name",
        "t1_price",
        "t1_periods",
        "t2_name",
        "t2_price",
        "t2_periods",
    ]
    suggested = _suggested(form)
    assert suggested["t1_periods"] == "07:00-23:00"
    assert suggested["t2_periods"] == "23:00-07:00"
    assert suggested["t1_name"] == "Day"
    assert "t1_price" not in suggested
    assert "t2_price" not in suggested

    result = await _configure(hass, form, TWO_ZONE_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    [subentry] = entry.subentries.values()
    assert subentry.subentry_type == "tariff_plan"
    assert dict(subentry.data) == PLAN_A
    assert subentry.title == "2026-01-01 · Two-zone"
    assert subentry.unique_id == "2026-01-01"
    assert entry.state is ConfigEntryState.LOADED
    plan = _schedule(entry).plan_for(date(2026, 1, 2))
    assert plan.zone_for_hour(12).price == Decimal("10.30")


@pytest.mark.parametrize(
    ("preset", "fields", "periods"),
    [
        ("single_rate", ["t0"], {"t0_periods": "00:00-24:00"}),
        (
            "ru_three_zone",
            ["t1", "t2", "t3"],
            {"t1_periods": "07:00-10:00, 17:00-21:00"},
        ),
    ],
)
async def test_preset_fields(
    hass: HomeAssistant, preset: str, fields: list[str], periods: dict[str, str]
):
    entry = await _add_entry(hass)
    form = await _plan_form(hass, entry, preset)
    expected = ["valid_from", "name"]
    for key in fields:
        expected += [f"{key}_name", f"{key}_price", f"{key}_periods"]
    assert _fields(form) == expected
    suggested = _suggested(form)
    for field, value in periods.items():
        assert suggested[field] == value


async def test_menu_and_copy(hass: HomeAssistant):
    entry = await _add_entry(hass, [PLAN_A])
    [plan_a] = entry.subentries.values()
    result = await _init(hass, entry)
    assert result["type"] is FlowResultType.MENU
    assert result["menu_options"] == ["preset", "copy"]

    copy = await _call(
        hass.config_entries.subentries.async_configure,
        result["flow_id"],
        {"next_step_id": "copy"},
    )
    assert copy["step_id"] == "copy"
    [key] = list(copy["data_schema"].schema)
    assert key.default() == plan_a.subentry_id

    form = await _configure(hass, copy, {"source_plan": plan_a.subentry_id})
    assert form["step_id"] == "plan"
    suggested = _suggested(form)
    assert "valid_from" not in suggested
    assert suggested["name"] == "Two-zone"
    assert suggested["t1_price"] == "10.30"
    assert suggested["t2_periods"] == "23:00-07:00"

    created = await _configure(
        hass,
        form,
        {
            **TWO_ZONE_INPUT,
            "valid_from": "2026-07-01",
            "t1_price": "11.00",
        },
    )
    assert created["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert len(entry.subentries) == 2
    assert dict(entry.subentries[plan_a.subentry_id].data) == PLAN_A
    schedule = _schedule(entry)
    assert schedule.plan_for(date(2026, 6, 30)).zone_for_hour(12).price == Decimal(
        "10.30"
    )
    assert schedule.plan_for(date(2026, 7, 1)).zone_for_hour(12).price == Decimal(
        "11.00"
    )


async def test_copy_defaults_to_latest_plan(hass: HomeAssistant):
    entry = await _add_entry(hass, [_plan_b(), PLAN_A])
    latest = next(s for s in entry.subentries.values() if s.unique_id == "2026-07-01")
    result = await _init(hass, entry)
    copy = await _call(
        hass.config_entries.subentries.async_configure,
        result["flow_id"],
        {"next_step_id": "copy"},
    )
    [key] = list(copy["data_schema"].schema)
    assert key.default() == latest.subentry_id


async def test_duplicate_valid_from(hass: HomeAssistant):
    entry = await _add_entry(hass, [PLAN_A])
    result = await _init(hass, entry)
    preset = await _configure(hass, result, {"next_step_id": "preset"})
    form = await _configure(hass, preset, {"preset": "ru_two_zone"})
    result = await _configure(hass, form, TWO_ZONE_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "plan"
    assert result["errors"] == {"valid_from": "valid_from_taken"}
    assert len(entry.subentries) == 1


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("t1_price", "-1", "invalid_price"),
        ("t1_price", "abc", "invalid_price"),
        ("t1_price", "", "invalid_price"),
        ("t1_price", "NaN", "invalid_price"),
        ("t1_price", "inf", "invalid_price"),
        ("t1_price", "Infinity", "invalid_price"),
        ("t1_price", "1e3", "invalid_price"),
        ("t1_price", "99999999999", "invalid_price"),
        ("t1_periods", "7-23", "invalid_periods"),
        ("t1_periods", "07:30-23:00", "invalid_periods"),
        ("t1_periods", "", "invalid_periods"),
        ("t1_name", "  ", "blank_name"),
        ("name", "  ", "blank_name"),
    ],
)
async def test_field_errors(hass: HomeAssistant, field: str, value: str, error: str):
    entry = await _add_entry(hass)
    form = await _plan_form(hass, entry, "ru_two_zone")
    result = await _configure(hass, form, {**TWO_ZONE_INPUT, field: value})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {field: error}
    assert not entry.subentries


async def test_plan_validation_errors(hass: HomeAssistant):
    entry = await _add_entry(hass)
    form = await _plan_form(hass, entry, "ru_two_zone")
    assert form["description_placeholders"] == {"detail": ""}

    gap = await _configure(hass, form, {**TWO_ZONE_INPUT, "t1_periods": "07:00-22:00"})
    assert gap["errors"] == {"base": "invalid_plan"}
    assert "22" in gap["description_placeholders"]["detail"]

    overlap = await _configure(
        hass, gap, {**TWO_ZONE_INPUT, "t2_periods": "22:00-07:00"}
    )
    assert overlap["errors"] == {"base": "invalid_plan"}
    assert "hour 22" in overlap["description_placeholders"]["detail"]
    assert _suggested(overlap)["t2_periods"] == "22:00-07:00"
    assert not entry.subentries


async def test_reconfigure_edits_plan(hass: HomeAssistant):
    entry = await _add_entry(hass, [PLAN_A])
    [plan_a] = entry.subentries.values()
    form = await _init(
        hass, entry, source=SOURCE_RECONFIGURE, subentry_id=plan_a.subentry_id
    )
    assert form["type"] is FlowResultType.FORM
    assert form["step_id"] == "plan"
    suggested = _suggested(form)
    assert suggested["valid_from"] == "2026-01-01"
    assert suggested["name"] == "Two-zone"
    assert suggested["t1_name"] == "Day"
    assert suggested["t1_price"] == "10.30"
    assert suggested["t1_periods"] == "07:00-23:00"

    result = await _configure(hass, form, {**TWO_ZONE_INPUT, "t1_price": "10.50"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()

    updated = entry.subentries[plan_a.subentry_id]
    assert updated.data["zones"][0]["price"] == "10.50"
    assert updated.title == "2026-01-01 · Two-zone"
    assert entry.state is ConfigEntryState.LOADED
    plan = _schedule(entry).plan_for(date(2026, 3, 1))
    assert plan.zone_for_hour(12).price == Decimal("10.50")


async def test_reconfigure_keeps_volume_bands(hass: HomeAssistant):
    banded = {**PLAN_A, "volume_band_limits_kwh": ["3900"]}
    banded["zones"] = [{**zone, "band_prices": ["12.00"]} for zone in PLAN_A["zones"]]
    entry = await _add_entry(hass, [banded])
    [plan_a] = entry.subentries.values()
    form = await _init(
        hass, entry, source=SOURCE_RECONFIGURE, subentry_id=plan_a.subentry_id
    )
    result = await _configure(hass, form, TWO_ZONE_INPUT)
    assert result["type"] is FlowResultType.ABORT
    data = entry.subentries[plan_a.subentry_id].data
    assert data["volume_band_limits_kwh"] == ["3900"]
    assert data["zones"][0]["band_prices"] == ["12.00"]


async def test_reconfigure_valid_from(hass: HomeAssistant):
    entry = await _add_entry(hass, [PLAN_A, _plan_b()])
    plan_b = next(s for s in entry.subentries.values() if s.unique_id == "2026-07-01")

    async def reconfigure(valid_from: str) -> dict[str, Any]:
        form = await _init(
            hass, entry, source=SOURCE_RECONFIGURE, subentry_id=plan_b.subentry_id
        )
        return await _configure(
            hass, form, {**TWO_ZONE_INPUT, "valid_from": valid_from}
        )

    taken = await reconfigure("2026-01-01")
    assert taken["errors"] == {"valid_from": "valid_from_taken"}

    same = await reconfigure("2026-07-01")
    assert same["type"] is FlowResultType.ABORT

    moved = await reconfigure("2026-03-01")
    assert moved["type"] is FlowResultType.ABORT
    await hass.async_block_till_done()
    updated = entry.subentries[plan_b.subentry_id]
    assert updated.unique_id == "2026-03-01"
    assert updated.title == "2026-03-01 · Two-zone"
    assert updated.data["valid_from"] == "2026-03-01"


async def test_remove_plan_reloads(hass: HomeAssistant):
    entry = await _add_entry(hass, [PLAN_A, _plan_b()])
    plan_a = next(s for s in entry.subentries.values() if s.unique_id == "2026-01-01")
    plan_b = next(s for s in entry.subentries.values() if s.unique_id == "2026-07-01")

    hass.config_entries.async_remove_subentry(entry, plan_b.subentry_id)
    await hass.async_block_till_done()
    assert [p.valid_from for p in _schedule(entry).plans] == [date(2026, 1, 1)]

    hass.config_entries.async_remove_subentry(entry, plan_a.subentry_id)
    await hass.async_block_till_done()
    assert _schedule(entry) is None
    assert entry.state is ConfigEntryState.LOADED


async def test_setup_error_on_corrupt_plan(hass: HomeAssistant):
    corrupt = {**PLAN_A, "zones": [{**z} for z in PLAN_A["zones"]]}
    corrupt["zones"][0]["price"] = 10.3
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEFAULT_TITLE,
        data={},
        options=OPTIONS,
        subentries_data=[_subentry(corrupt)],
    )
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_ERROR


async def test_setup_error_on_duplicate_valid_from(hass: HomeAssistant):
    first = _subentry(PLAN_A)
    second = ConfigSubentryData(
        data=PLAN_A,
        subentry_type="tariff_plan",
        title="other",
        unique_id="other",
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEFAULT_TITLE,
        data={},
        options=OPTIONS,
        subentries_data=[first, second],
    )
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_ERROR


async def test_no_entities(hass: HomeAssistant):
    entry = await _add_entry(hass)
    form = await _plan_form(hass, entry, "ru_two_zone")
    await _configure(hass, form, TWO_ZONE_INPUT)
    await hass.async_block_till_done()
    assert not any(DOMAIN in s.entity_id for s in hass.states.async_all())


async def test_copy_after_last_plan_deleted_falls_back_to_preset(
    hass: HomeAssistant,
):
    entry = await _add_entry(hass, [PLAN_A])
    [plan_a] = entry.subentries.values()
    menu = await _init(hass, entry)
    assert menu["type"] is FlowResultType.MENU
    hass.config_entries.async_remove_subentry(entry, plan_a.subentry_id)
    await hass.async_block_till_done()
    result = await _configure(hass, menu, {"next_step_id": "copy"})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "preset"


async def test_reconfigure_corrupt_plan_aborts(hass: HomeAssistant):
    corrupt = {**PLAN_A, "zones": [{**z} for z in PLAN_A["zones"]]}
    corrupt["zones"][0]["price"] = 10.3
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEFAULT_TITLE,
        data={},
        options=OPTIONS,
        subentries_data=[_subentry(corrupt)],
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    [subentry] = entry.subentries.values()
    result = await _init(
        hass, entry, source=SOURCE_RECONFIGURE, subentry_id=subentry.subentry_id
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "invalid_plan_data"
