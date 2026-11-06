"""Tariff subentry flow: add a tariff, add/edit/delete versions, rename (tasks/018)."""

import copy
import logging
import re
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from homeassistant.config_entries import ConfigEntryState, ConfigSubentryData
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, section
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_cost_stats.config_flow import EnergyCostStatsConfigFlow
from custom_components.energy_cost_stats.const import DOMAIN
from custom_components.energy_cost_stats.tariff_flow import TariffSubentryFlow

TWO_ZONE: dict[str, Any] = {
    "id": "two_zone",
    "name": "Two-zone",
    "versions": [
        {
            "valid_from": "2026-01-01",
            "preset": "ru_two_zone",
            "prices": {"t1": "10.30", "t2": "4.43"},
        }
    ],
}
TWO_ZONE_V2: dict[str, Any] = {
    **TWO_ZONE,
    "versions": [
        *TWO_ZONE["versions"],
        {"valid_from": "2026-07-01", "prices": {"t1": "11.00", "t2": "4.60"}},
    ],
}
OTHER: dict[str, Any] = {
    "id": "other",
    "name": "Other",
    "versions": [
        {"valid_from": "2026-01-01", "preset": "single_rate", "prices": {"t0": "7.40"}}
    ],
}
APPLIED = [{"from": "2026-01-01", "tariff": "two_zone"}]
ID_RE = re.compile(r"[a-z0-9_]{1,32}")


def zone_input(name: str, price: str, hours: str) -> dict[str, str]:
    return {"name": name, "price": price, "hours": hours}


FIRST_VERSION = {
    "valid_from": "2026-01-01",
    "zone_1": zone_input("Day", "10,30", "07:00-23:00"),
    "zone_2": zone_input("Night", "4.43", "23:00-07:00"),
}


async def setup_entry(
    hass: HomeAssistant, tariffs: list[dict[str, Any]], **opts: Any
) -> MockConfigEntry:
    options: dict[str, Any] = {
        "time_zone": "Europe/Moscow",
        "spike_limit": "4",
        "sensors": {
            "mode": "filter",
            "include": "all",
            "exclude": {},
            "overrides": {},
        },
        **opts,
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options=options,
        version=3,
        subentries_data=[
            ConfigSubentryData(
                data=copy.deepcopy(t),
                subentry_type="tariff",
                title=t["name"],
                unique_id=t["id"],
            )
            for t in tariffs
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def start(
    hass: HomeAssistant, entry: MockConfigEntry, source: str = "user"
) -> dict[str, Any]:
    context: Any = {"source": source}
    if source == "reconfigure":
        (subentry_id,) = list(entry.subentries)[:1]
        context["subentry_id"] = subentry_id
    return dict(
        await hass.config_entries.subentries.async_init(
            (entry.entry_id, "tariff"), context=context
        )
    )


async def send(
    hass: HomeAssistant, result: dict[str, Any], user_input: dict[str, Any]
) -> dict[str, Any]:
    return dict(
        await hass.config_entries.subentries.async_configure(
            result["flow_id"], user_input
        )
    )


def suggested(result: dict[str, Any]) -> dict[str, Any]:
    """Suggested values of a form, sections nested."""
    out: dict[str, Any] = {}
    for key, value in result["data_schema"].schema.items():
        if isinstance(value, section):
            out[str(key)] = {
                str(inner): (inner.description or {}).get("suggested_value")
                for inner in value.schema.schema
            }
        else:
            out[str(key)] = (key.description or {}).get("suggested_value")
    return out


def field_names(result: dict[str, Any]) -> list[str]:
    return [str(key) for key in result["data_schema"].schema]


def section_fields(result: dict[str, Any], name: str) -> list[str]:
    for key, value in result["data_schema"].schema.items():
        if str(key) == name:
            return [str(inner) for inner in value.schema.schema]
    raise AssertionError(name)


def price_at(entry: MockConfigEntry, day: str, hour: int = 12) -> Decimal:
    plan = entry.runtime_data.schedule.plan_for(date.fromisoformat(day))
    assert plan is not None
    return plan.zone_for_hour(hour).price


def tariff_data(entry: MockConfigEntry, tariff_id: str) -> dict[str, Any]:
    for subentry in entry.subentries.values():
        if subentry.unique_id == tariff_id:
            return dict(subentry.data)
    raise AssertionError(tariff_id)


async def to_first_version(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    name: str = "Two-zone",
    base: str = "ru_two_zone",
    tariff_id: str | None = None,
) -> dict[str, Any]:
    result = await start(hass, entry)
    result = await send(hass, result, {"name": name, "base": base})
    assert result["step_id"] == "tariff_id", result
    result = await send(hass, result, {"id": tariff_id or suggested(result)["id"]})
    assert result["step_id"] == "first_version", result
    return result


async def open_step(
    hass: HomeAssistant, entry: MockConfigEntry, step: str
) -> dict[str, Any]:
    result = await start(hass, entry, "reconfigure")
    assert result["type"] is FlowResultType.MENU
    return await send(hass, result, {"next_step_id": step})


async def open_version(
    hass: HomeAssistant, entry: MockConfigEntry, valid_from: str
) -> dict[str, Any]:
    result = await open_step(hass, entry, "select_version")
    assert result["step_id"] == "select_version"
    return await send(hass, result, {"version": valid_from})


def later_input(
    day: str, price_1: str, price_2: str, hours: tuple[str, str] | None = None
) -> dict[str, Any]:
    return {
        "valid_from": day,
        "price_1": price_1,
        "price_2": price_2,
        "hours": {
            "hours_1": hours[0] if hours else "07:00-23:00",
            "hours_2": hours[1] if hours else "23:00-07:00",
        },
    }


def first_input(
    day: str, price_1: str, price_2: str, *, delete: bool = False
) -> dict[str, Any]:
    return {
        "valid_from": day,
        "zone_1": zone_input("Day", price_1, "07:00-23:00"),
        "zone_2": zone_input("Night", price_2, "23:00-07:00"),
        "delete": delete,
    }


# ---- registration ----------------------------------------


async def test_subentry_type_registered(hass: HomeAssistant):
    entry = await setup_entry(hass, [])
    assert EnergyCostStatsConfigFlow.async_get_supported_subentry_types(entry) == {
        "tariff": TariffSubentryFlow
    }
    assert hasattr(TariffSubentryFlow, "async_step_reconfigure")


# ---- add a tariff ----------------------------------------


async def test_add_two_zone_tariff(hass: HomeAssistant):
    entry = await setup_entry(hass, [])
    result = await start(hass, entry)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    base_key = next(k for k in result["data_schema"].schema if str(k) == "base")
    assert base_key.default() == "ru_two_zone"
    selector_config = result["data_schema"].schema[base_key].config
    assert "copy" not in selector_config["options"]

    result = await send(hass, result, {"name": "Two-zone", "base": "ru_two_zone"})
    assert result["step_id"] == "tariff_id"
    assert suggested(result)["id"] == "two_zone"
    result = await send(hass, result, {"id": "two_zone"})
    assert result["step_id"] == "first_version"
    assert field_names(result)[0] == "valid_from"
    assert section_fields(result, "zone_1") == ["name", "price", "hours"]
    values = suggested(result)
    assert values["zone_1"] == {"name": "Day", "price": None, "hours": "07:00-23:00"}
    assert values["zone_2"]["name"] == "Night"
    assert values["zone_2"]["hours"] == "23:00-07:00"
    assert values["valid_from"] is None
    assert "Zone 1: Day (t1)" in result["description_placeholders"]["zones"]

    result = await send(hass, result, FIRST_VERSION)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    (subentry,) = entry.subentries.values()
    assert subentry.unique_id == "two_zone"
    assert subentry.title == "Two-zone"
    assert dict(subentry.data) == {
        "id": "two_zone",
        "name": "Two-zone",
        "versions": [
            {
                "valid_from": "2026-01-01",
                "preset": "ru_two_zone",
                "prices": {"t1": "10.30", "t2": "4.43"},
            }
        ],
    }
    assert entry.state is ConfigEntryState.LOADED
    assert entry.options["applied"] == [{"from": "2026-01-01", "tariff": "two_zone"}]
    assert price_at(entry, "2026-01-02") == Decimal("10.30")


async def test_id_slug_and_errors(hass: HomeAssistant):
    entry = await setup_entry(hass, [TWO_ZONE])
    result = await start(hass, entry)
    blank = await send(hass, result, {"name": "   ", "base": "single_rate"})
    assert blank["step_id"] == "user"
    assert blank["errors"] == {"name": "blank_name"}

    result = await send(hass, result, {"name": "Тариф День", "base": "single_rate"})
    assert result["step_id"] == "tariff_id"
    assert ID_RE.fullmatch(suggested(result)["id"])
    assert suggested(result)["id"].isascii()

    bad = await send(hass, result, {"id": "Bad Id"})
    assert bad["step_id"] == "tariff_id"
    assert bad["errors"] == {"id": "invalid_id"}
    taken = await send(hass, result, {"id": "two_zone"})
    assert taken["errors"] == {"id": "id_taken"}
    ok = await send(hass, result, {"id": "day"})
    assert ok["step_id"] == "first_version"


async def test_single_rate_and_three_zone_forms(hass: HomeAssistant):
    entry = await setup_entry(hass, [])
    single = await to_first_version(hass, entry, "Flat", "single_rate")
    assert section_fields(single, "zone_1") == ["name", "price", "hours"]
    assert "zone_2" not in field_names(single)
    assert suggested(single)["zone_1"]["hours"] == "00:00-24:00"
    three = await to_first_version(hass, entry, "Triple", "ru_three_zone")
    values = suggested(three)
    assert values["zone_1"]["hours"] == "07:00-10:00, 17:00-21:00"
    assert values["zone_3"]["name"] == "Semi-peak"


async def test_custom_zones(hass: HomeAssistant):
    entry = await setup_entry(hass, [])
    result = await start(hass, entry)
    result = await send(hass, result, {"name": "Custom", "base": "custom"})
    assert result["step_id"] == "custom_zones"
    result = await send(hass, result, {"count": 3})
    assert result["step_id"] == "tariff_id"
    result = await send(hass, result, {"id": "custom"})
    assert result["step_id"] == "first_version"
    assert section_fields(result, "zone_1") == ["key", "name", "price", "hours"]
    assert [suggested(result)[f"zone_{i}"]["key"] for i in (1, 2, 3)] == [
        "t1",
        "t2",
        "t3",
    ]

    def zone(key: str, hours: str) -> dict[str, str]:
        return {"key": key, "name": key.upper(), "price": "1.5", "hours": hours}

    duplicate = {
        "valid_from": "2026-01-01",
        "zone_1": zone("a", "00:00-08:00"),
        "zone_2": zone("a", "08:00-16:00"),
        "zone_3": zone("c", "16:00-24:00"),
    }
    failed = await send(hass, result, duplicate)
    assert failed["step_id"] == "first_version"
    assert failed["errors"]["zone_2"] == "duplicate_zone_key"
    assert "zone_3" not in failed["errors"]

    valid = {**duplicate, "zone_2": zone("b", "08:00-16:00")}
    created = await send(hass, failed, valid)
    assert created["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    data = tariff_data(entry, "custom")
    assert data["versions"] == [
        {
            "valid_from": "2026-01-01",
            "zones": [
                {"key": "a", "name": "A", "price": "1.5", "hours": "00:00-08:00"},
                {"key": "b", "name": "B", "price": "1.5", "hours": "08:00-16:00"},
                {"key": "c", "name": "C", "price": "1.5", "hours": "16:00-24:00"},
            ],
        }
    ]
    assert entry.state is ConfigEntryState.LOADED


async def test_renamed_zone_is_stored_explicitly(hass: HomeAssistant):
    entry = await setup_entry(hass, [])
    result = await to_first_version(hass, entry)
    renamed = {**FIRST_VERSION, "zone_1": zone_input("Peak day", "10", "07:00-23:00")}
    created = await send(hass, result, renamed)
    assert created["type"] is FlowResultType.CREATE_ENTRY
    (version,) = tariff_data(entry, "two_zone")["versions"]
    assert "preset" not in version
    assert version["zones"][0]["name"] == "Peak day"


async def test_copy_tariff(hass: HomeAssistant):
    entry = await setup_entry(hass, [OTHER, TWO_ZONE_V2])
    result = await start(hass, entry)
    base_key = next(k for k in result["data_schema"].schema if str(k) == "base")
    assert "copy" in result["data_schema"].schema[base_key].config["options"]
    result = await send(hass, result, {"name": "Two-zone copy", "base": "copy"})
    assert result["step_id"] == "copy"
    source_key = next(k for k in result["data_schema"].schema if str(k) == "source")
    assert source_key.default() == "two_zone"
    result = await send(hass, result, {"source": "two_zone"})
    assert result["step_id"] == "tariff_id"
    assert suggested(result)["id"] == "two_zone_copy"
    result = await send(hass, result, {"id": "two_zone_copy"})
    assert result["step_id"] == "first_version"
    values = suggested(result)
    assert values["zone_1"]["price"] == "11.00"
    assert values["zone_2"]["price"] == "4.60"
    assert values["valid_from"] is None

    created = await send(
        hass,
        result,
        {
            "valid_from": "2026-08-01",
            "zone_1": zone_input("Day", "12", "07:00-23:00"),
            "zone_2": zone_input("Night", "5", "23:00-07:00"),
        },
    )
    assert created["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert tariff_data(entry, "two_zone_copy")["versions"] == [
        {
            "valid_from": "2026-08-01",
            "preset": "ru_two_zone",
            "prices": {"t1": "12", "t2": "5"},
        }
    ]
    assert "applied" not in entry.options
    assert "two_zone_copy" in entry.runtime_data.tariffs.compare


@pytest.mark.parametrize(
    ("zone_1", "errors", "hours"),
    [
        ({"price": "abc"}, {"zone_1": "invalid_price"}, None),
        ({"hours": "7-23"}, {"zone_1": "invalid_hours"}, None),
        ({"hours": "07:00-22:00"}, {"base": "hours_uncovered"}, "22:00-23:00"),
        (
            {"hours": "06:00-23:00"},
            {"zone_1": "hours_overlap", "zone_2": "hours_overlap"},
            None,
        ),
        ({"name": " "}, {"zone_1": "blank_name"}, None),
    ],
)
async def test_first_version_errors(
    hass: HomeAssistant,
    zone_1: dict[str, str],
    errors: dict[str, str],
    hours: str | None,
):
    entry = await setup_entry(hass, [])
    result = await to_first_version(hass, entry)
    submitted = {
        **FIRST_VERSION,
        "zone_1": {**FIRST_VERSION["zone_1"], **zone_1},
    }
    failed = await send(hass, result, submitted)
    assert failed["type"] is FlowResultType.FORM
    assert failed["step_id"] == "first_version"
    assert failed["errors"] == errors
    if hours is not None:
        assert hours in failed["description_placeholders"]["hours"]
    assert suggested(failed)["zone_1"] == submitted["zone_1"]
    assert not entry.subentries


# ---- the tariff menu -------------------------------------


async def test_menu_shows_versions(hass: HomeAssistant):
    entry = await setup_entry(hass, [TWO_ZONE_V2], applied=APPLIED)
    result = await start(hass, entry, "reconfigure")
    assert result["type"] is FlowResultType.MENU
    assert result["menu_options"] == ["new_version", "select_version", "rename"]
    placeholders = result["description_placeholders"]
    assert placeholders["name"] == "Two-zone"
    assert placeholders["id"] == "two_zone"
    assert "2026-01-01" in placeholders["versions"]
    assert "2026-07-01" in placeholders["versions"]
    assert "t1 10.30" in placeholders["versions"]
    assert "2026-01-01" in placeholders["applied"]


async def test_new_version_reprices(hass: HomeAssistant):
    entry = await setup_entry(hass, [TWO_ZONE], applied=APPLIED)
    result = await open_step(hass, entry, "new_version")
    assert result["step_id"] == "new_version"
    values = suggested(result)
    assert values["price_1"] == "10.30"
    assert values["price_2"] == "4.43"
    assert values["hours"] == {"hours_1": "07:00-23:00", "hours_2": "23:00-07:00"}
    assert "Day (t1)" in result["description_placeholders"]["zone_1"]

    created = await send(hass, result, later_input("2026-07-01", "11.00", "4.60"))
    assert created["type"] is FlowResultType.ABORT
    assert created["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    assert tariff_data(entry, "two_zone")["versions"][1] == {
        "valid_from": "2026-07-01",
        "prices": {"t1": "11.00", "t2": "4.60"},
    }
    assert entry.state is ConfigEntryState.LOADED
    assert price_at(entry, "2026-07-02") == Decimal("11.00")
    assert price_at(entry, "2026-06-30") == Decimal("10.30")

    again = await open_step(hass, entry, "new_version")
    duplicate = await send(hass, again, later_input("2026-07-01", "1", "1"))
    assert duplicate["errors"] == {"valid_from": "valid_from_taken"}
    bad_price = await send(hass, again, later_input("2026-08-01", "x", "1"))
    assert bad_price["errors"] == {"price_1": "invalid_price"}
    bad_hours = await send(
        hass, again, later_input("2026-08-01", "1", "1", ("7-23", "23:00-07:00"))
    )
    assert bad_hours["errors"] == {"hours": "invalid_hours"}
    gap = await send(
        hass, again, later_input("2026-08-01", "1", "1", ("07:00-22:00", "23:00-07:00"))
    )
    assert gap["errors"] == {"base": "hours_uncovered"}


async def test_new_version_before_the_first_version(hass: HomeAssistant):
    entry = await setup_entry(hass, [TWO_ZONE], applied=APPLIED)
    result = await open_step(hass, entry, "new_version")
    created = await send(hass, result, later_input("2025-12-01", "9", "4"))
    assert created["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    earlier, former = tariff_data(entry, "two_zone")["versions"]
    assert earlier == {
        "valid_from": "2025-12-01",
        "zones": [
            {"key": "t1", "name": "Day", "price": "9", "hours": "07:00-23:00"},
            {"key": "t2", "name": "Night", "price": "4", "hours": "23:00-07:00"},
        ],
    }
    assert former == TWO_ZONE["versions"][0]
    assert entry.state is ConfigEntryState.LOADED
    assert entry.options["applied"] == APPLIED
    assert price_at(entry, "2026-01-02") == Decimal("10.30")
    tariff = entry.runtime_data.tariffs.tariff("two_zone")
    assert [v.valid_from.isoformat() for v in tariff.versions] == [
        "2025-12-01",
        "2026-01-01",
    ]


async def test_new_version_hours_override(hass: HomeAssistant):
    entry = await setup_entry(hass, [TWO_ZONE], applied=APPLIED)
    result = await open_step(hass, entry, "new_version")
    created = await send(
        hass,
        result,
        later_input("2026-07-01", "11", "4.6", ("06:00-23:00", "23:00-06:00")),
    )
    assert created["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    assert tariff_data(entry, "two_zone")["versions"][1]["hours"] == {
        "t1": "06:00-23:00",
        "t2": "23:00-06:00",
    }
    assert "hours" not in tariff_data(entry, "two_zone")["versions"][0]

    unchanged = await open_step(hass, entry, "new_version")
    await send(
        hass,
        unchanged,
        later_input("2026-09-01", "12", "5", ("06:00-23:00", "23:00-06:00")),
    )
    await hass.async_block_till_done()
    assert "hours" not in tariff_data(entry, "two_zone")["versions"][2]


async def test_edit_version_retroactive(hass: HomeAssistant):
    entry = await setup_entry(hass, [TWO_ZONE_V2], applied=APPLIED)
    result = await open_step(hass, entry, "select_version")
    assert result["step_id"] == "select_version"
    options = next(iter(result["data_schema"].schema.values())).config["options"]
    assert [o if isinstance(o, str) else o["value"] for o in options] == [
        "2026-07-01",
        "2026-01-01",
    ]
    edit = await send(hass, result, {"version": "2026-07-01"})
    assert edit["step_id"] == "edit_version"
    assert suggested(edit)["price_1"] == "11.00"
    assert suggested(edit)["valid_from"] == "2026-07-01"
    done = await send(
        hass, edit, {**later_input("2026-07-01", "11.20", "4.60"), "delete": False}
    )
    assert done["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    assert price_at(entry, "2026-07-10") == Decimal("11.20")
    assert price_at(entry, "2026-02-10") == Decimal("10.30")

    first = await open_version(hass, entry, "2026-01-01")
    assert first["step_id"] == "edit_first_version"
    assert section_fields(first, "zone_1") == ["name", "price", "hours"]
    assert suggested(first)["zone_1"]["price"] == "10.30"


async def test_edit_first_version_moves_applied(hass: HomeAssistant):
    entry = await setup_entry(hass, [TWO_ZONE], applied=APPLIED)
    edit = await open_version(hass, entry, "2026-01-01")
    done = await send(hass, edit, first_input("2025-12-01", "10.30", "4.43"))
    assert done["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert entry.options["applied"][0]["from"] == "2025-12-01"
    assert price_at(entry, "2025-12-15") == Decimal("10.30")


async def test_edit_version_applied_without_version(hass: HomeAssistant):
    applied = [
        {"from": "2026-01-01", "tariff": "other"},
        {"from": "2026-03-01", "tariff": "two_zone"},
    ]
    entry = await setup_entry(hass, [TWO_ZONE, OTHER], applied=applied)
    before = tariff_data(entry, "two_zone")
    edit = await open_version(hass, entry, "2026-01-01")
    failed = await send(hass, edit, first_input("2026-04-01", "10.30", "4.43"))
    assert failed["type"] is FlowResultType.FORM
    assert failed["errors"] == {"valid_from": "applied_without_version"}
    assert tariff_data(entry, "two_zone") == before
    assert entry.options["applied"] == applied


LATER_OTHER = [
    {"from": "2026-01-01", "tariff": "two_zone"},
    {"from": "2026-05-01", "tariff": "other"},
]


async def test_moving_first_version_must_not_reorder_applied(hass: HomeAssistant):
    entry = await setup_entry(hass, [TWO_ZONE, OTHER], applied=LATER_OTHER)
    before = tariff_data(entry, "two_zone")
    edit = await open_version(hass, entry, "2026-01-01")
    failed = await send(hass, edit, first_input("2026-07-01", "10.30", "4.43"))
    assert failed["type"] is FlowResultType.FORM
    assert failed["errors"] == {"valid_from": "applied_order"}
    assert tariff_data(entry, "two_zone") == before
    assert entry.options["applied"] == LATER_OTHER


async def test_deleting_first_version_must_not_reorder_applied(hass: HomeAssistant):
    entry = await setup_entry(hass, [TWO_ZONE_V2, OTHER], applied=LATER_OTHER)
    before = tariff_data(entry, "two_zone")
    edit = await open_version(hass, entry, "2026-01-01")
    failed = await send(
        hass, edit, first_input("2026-01-01", "10.30", "4.43", delete=True)
    )
    assert failed["errors"] == {"delete": "applied_order"}
    assert tariff_data(entry, "two_zone") == before
    assert entry.options["applied"] == LATER_OTHER


async def test_deleting_first_version_without_version_for_applied(hass: HomeAssistant):
    applied = [
        {"from": "2026-01-01", "tariff": "other"},
        {"from": "2026-03-01", "tariff": "two_zone"},
    ]
    entry = await setup_entry(hass, [TWO_ZONE_V2, OTHER], applied=applied)
    edit = await open_version(hass, entry, "2026-01-01")
    failed = await send(
        hass, edit, first_input("2026-01-01", "10.30", "4.43", delete=True)
    )
    assert failed["errors"] == {"delete": "applied_without_version"}
    assert entry.options["applied"] == applied


async def test_edit_first_version_renaming_a_zone(hass: HomeAssistant):
    entry = await setup_entry(hass, [TWO_ZONE], applied=APPLIED)
    edit = await open_version(hass, entry, "2026-01-01")
    submitted = {
        **first_input("2026-01-01", "10.30", "4.43"),
        "zone_1": zone_input("Daytime", "10.30", "07:00-23:00"),
    }
    await send(hass, edit, submitted)
    await hass.async_block_till_done()
    (version,) = tariff_data(entry, "two_zone")["versions"]
    assert [z["name"] for z in version["zones"]] == ["Daytime", "Night"]


async def test_delete_version(hass: HomeAssistant):
    entry = await setup_entry(hass, [TWO_ZONE_V2], applied=APPLIED)
    edit = await open_version(hass, entry, "2026-07-01")
    done = await send(
        hass, edit, {**later_input("2026-07-01", "11.00", "4.60"), "delete": True}
    )
    assert done["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    assert len(tariff_data(entry, "two_zone")["versions"]) == 1
    assert price_at(entry, "2026-07-10") == Decimal("10.30")

    only = await open_version(hass, entry, "2026-01-01")
    refused = await send(
        hass, only, first_input("2026-01-01", "10.30", "4.43", delete=True)
    )
    assert refused["type"] is FlowResultType.FORM
    assert refused["errors"] == {"delete": "last_version"}


async def test_delete_first_version_keeps_prices(hass: HomeAssistant):
    entry = await setup_entry(hass, [TWO_ZONE_V2], applied=APPLIED)
    edit = await open_version(hass, entry, "2026-01-01")
    done = await send(
        hass, edit, first_input("2026-01-01", "10.30", "4.43", delete=True)
    )
    assert done["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    assert tariff_data(entry, "two_zone")["versions"] == [
        {
            "valid_from": "2026-07-01",
            "preset": "ru_two_zone",
            "prices": {"t1": "11.00", "t2": "4.60"},
        }
    ]
    assert entry.state is ConfigEntryState.LOADED
    assert entry.options["applied"] == [{"from": "2026-07-01", "tariff": "two_zone"}]
    assert price_at(entry, "2026-07-10") == Decimal("11.00")


# ---- rename ----------------------------------------------


async def test_rename_name_only(hass: HomeAssistant):
    entry = await setup_entry(hass, [TWO_ZONE], applied=APPLIED)
    result = await open_step(hass, entry, "rename")
    assert result["step_id"] == "rename"
    assert suggested(result) == {"name": "Two-zone", "id": "two_zone"}
    blank = await send(hass, result, {"name": " ", "id": "two_zone"})
    assert blank["errors"] == {"name": "blank_name"}
    done = await send(hass, result, {"name": "Day and night", "id": "two_zone"})
    assert done["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    (subentry,) = entry.subentries.values()
    assert subentry.title == "Day and night"
    assert subentry.data["name"] == "Day and night"
    assert subentry.unique_id == "two_zone"
    assert entry.options["applied"] == APPLIED


async def test_rename_id_updates_references(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
):
    caplog.set_level(logging.WARNING)
    entry = await setup_entry(
        hass, [TWO_ZONE, OTHER], applied=APPLIED, compare=["two_zone"]
    )
    result = await open_step(hass, entry, "rename")
    invalid = await send(hass, result, {"name": "Two-zone", "id": "Bad Id"})
    assert invalid["errors"] == {"id": "invalid_id"}
    taken = await send(hass, result, {"name": "Two-zone", "id": "other"})
    assert taken["errors"] == {"id": "id_taken"}

    done = await send(hass, result, {"name": "Day and night", "id": "day_night"})
    assert done["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    data = tariff_data(entry, "day_night")
    assert data["id"] == "day_night"
    assert data["name"] == "Day and night"
    assert entry.options["applied"] == [{"from": "2026-01-01", "tariff": "day_night"}]
    assert entry.options["compare"] == ["day_night"]
    assert entry.state is ConfigEntryState.LOADED
    assert "Invalid tariff configuration" not in caplog.text

    own = await open_step(hass, entry, "rename")
    same = await send(hass, own, {"name": "Day and night", "id": "day_night"})
    assert same["reason"] == "reconfigure_successful"


async def test_no_entities(hass: HomeAssistant):
    entry = await setup_entry(hass, [])
    result = await to_first_version(hass, entry)
    await send(hass, result, FIRST_VERSION)
    await hass.async_block_till_done()
    assert not [s for s in hass.states.async_all() if DOMAIN in s.entity_id]
    assert not er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
