"""Tariff model v2: migration, applied history and the compare command (tasks/017)."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from types import MappingProxyType
from typing import Any

import pytest
from homeassistant.config_entries import (
    ConfigEntryState,
    ConfigSubentry,
    ConfigSubentryData,
)
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_cost_stats.const import DOMAIN

SeedStatistics = Callable[..., Awaitable[None]]
HOUR = timedelta(hours=1)
PLUG_01 = "sensor.plug_01"
FIRST = datetime(2026, 1, 14, 20, tzinfo=UTC)
LAST = datetime(2026, 1, 16, 21, tzinfo=UTC)

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
THREE_ZONE: dict[str, Any] = {
    "id": "three_zone",
    "name": "Three-zone",
    "versions": [
        {
            "valid_from": "2026-01-01",
            "preset": "ru_three_zone",
            "prices": {"t1": "10.20", "t2": "3.45", "t3": "8.75"},
        }
    ],
}
SINGLE: dict[str, Any] = {
    "id": "single",
    "name": "Single-rate",
    "versions": [
        {
            "valid_from": "2026-01-01",
            "preset": "single_rate",
            "prices": {"t0": "7.40"},
        }
    ],
}


def options(**changes: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "time_zone": "Europe/Moscow",
        "spike_limit": "4",
        "device_spike_limits": {},
        "entities": [PLUG_01],
    }
    return {**base, **changes}


def tariff_subentry(data: dict[str, Any]) -> ConfigSubentryData:
    return ConfigSubentryData(
        data=data, subentry_type="tariff", title=data["name"], unique_id=data["id"]
    )


async def setup_v2(
    hass: HomeAssistant, tariffs: list[dict[str, Any]], **opts: Any
) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options=options(**opts),
        version=2,
        subentries_data=[tariff_subentry(t) for t in tariffs],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.fixture
async def seeded(seed_statistics: SeedStatistics) -> None:
    sums: dict[datetime, float] = {}
    current, total = FIRST, 0.0
    while current <= LAST:
        total += 1.0
        sums[current] = total
        current += HOUR
    await seed_statistics(PLUG_01, sums)


async def ws(hass: HomeAssistant, hass_ws_client, type_: str, **fields: Any) -> Any:
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": f"energy_cost_stats/{type_}", **fields})
    return await client.receive_json()


def total_cost(document: dict[str, Any]) -> str:
    return document["buckets"][0]["total"]["cost"]


# ---- migration -----------------------------------------------------------------


def old_plan(valid_from: str, name: str, day: str) -> dict[str, Any]:
    return {
        "valid_from": valid_from,
        "name": name,
        "zones": [
            {"key": "t1", "name": "Day", "price": day, "periods": [["07:00", "23:00"]]},
            {
                "key": "t2",
                "name": "Night",
                "price": "4.43",
                "periods": [["23:00", "07:00"]],
            },
        ],
    }


def old_subentry(data: dict[str, Any]) -> ConfigSubentryData:
    return ConfigSubentryData(
        data=data,
        subentry_type="tariff_plan",
        title=f"{data['valid_from']} · {data['name']}",
        unique_id=data["valid_from"],
    )


async def test_migration_v1_to_v2(hass: HomeAssistant):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options=options(),
        version=1,
        subentries_data=[
            old_subentry(old_plan("2026-07-01", "Two-zone 2026-H2", "11.00")),
            old_subentry(old_plan("2026-01-01", "Two-zone", "10.30")),
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.version == 2
    (subentry,) = entry.subentries.values()
    assert subentry.subentry_type == "tariff"
    assert subentry.unique_id == "main"
    assert subentry.title == "Two-zone 2026-H2"
    assert subentry.data["id"] == "main"
    assert subentry.data["name"] == "Two-zone 2026-H2"
    first, second = subentry.data["versions"]
    assert first == {
        "valid_from": "2026-01-01",
        "zones": [
            {"key": "t1", "name": "Day", "price": "10.30", "hours": "07:00-23:00"},
            {"key": "t2", "name": "Night", "price": "4.43", "hours": "23:00-07:00"},
        ],
    }
    assert second["valid_from"] == "2026-07-01"
    assert second["zones"][0]["price"] == "11.00"
    assert entry.options["applied"] == [{"from": "2026-01-01", "tariff": "main"}]
    schedule = entry.runtime_data.schedule
    assert [p.valid_from.isoformat() for p in schedule.plans] == [
        "2026-01-01",
        "2026-07-01",
    ]


async def test_migration_without_plans(hass: HomeAssistant):
    entry = MockConfigEntry(domain=DOMAIN, data={}, options=options(), version=1)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert entry.version == 2
    assert not entry.subentries
    assert "applied" not in entry.options
    assert entry.runtime_data.schedule is None


async def test_migration_of_a_broken_plan_fails(hass: HomeAssistant):
    broken = old_plan("2026-01-01", "Two-zone", "10.30")
    broken["zones"][0]["periods"] = [["07:00", "22:00"]]
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options=options(),
        version=1,
        subentries_data=[old_subentry(broken)],
    )
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.MIGRATION_ERROR


# ---- report across an applied switch -------------------------------------------


@pytest.mark.usefixtures("seeded")
async def test_report_follows_the_applied_history(hass: HomeAssistant, hass_ws_client):
    await setup_v2(
        hass,
        [TWO_ZONE, SINGLE],
        applied=[
            {"from": "2026-01-01", "tariff": "two_zone"},
            {"from": "2026-01-16", "tariff": "single"},
        ],
    )
    msg = await ws(
        hass,
        hass_ws_client,
        "report",
        start="2026-01-15",
        end="2026-01-17",
        grouping="day",
    )
    assert msg["success"], msg
    doc = msg["result"]
    day_15, day_16 = doc["buckets"]
    assert day_15["total"]["cost"] == "200.24"  # 16 h * 10.30 + 8 h * 4.43
    assert day_16["total"]["cost"] == "177.60"  # 24 h * 7.40
    assert [p["name"] for p in doc["plans"]] == ["Two-zone", "Single-rate"]
    assert doc["unpriced_hours"] == 0


@pytest.mark.usefixtures("seeded")
async def test_applied_change_reprices_after_reload(
    hass: HomeAssistant, hass_ws_client
):
    entry = await setup_v2(
        hass, [TWO_ZONE, SINGLE], applied=[{"from": "2026-01-01", "tariff": "single"}]
    )
    fields = {"start": "2026-01-15", "end": "2026-01-16", "grouping": "total"}
    before = await ws(hass, hass_ws_client, "report", **fields)
    assert total_cost(before["result"]) == "177.60"
    hass.config_entries.async_update_entry(
        entry,
        options=options(applied=[{"from": "2026-01-01", "tariff": "two_zone"}]),
    )
    await hass.async_block_till_done()
    after = await ws(hass, hass_ws_client, "report", **fields)
    assert total_cost(after["result"]) == "200.24"


# ---- compare -------------------------------------------------------------------

COMPARE = {"start": "2026-01-15", "end": "2026-01-16"}


@pytest.mark.usefixtures("seeded")
async def test_compare_default_list(hass: HomeAssistant, hass_ws_client):
    await setup_v2(
        hass,
        [TWO_ZONE, THREE_ZONE, SINGLE],
        applied=[{"from": "2026-01-01", "tariff": "two_zone"}],
    )
    msg = await ws(hass, hass_ws_client, "compare", **COMPARE)
    assert msg["success"], msg
    result = msg["result"]
    assert total_cost(result["actual"]) == "200.24"
    assert [(t["id"], t["name"]) for t in result["tariffs"]] == [
        ("three_zone", "Three-zone"),
        ("single", "Single-rate"),
    ]
    costs = {t["id"]: total_cost(t["report"]) for t in result["tariffs"]}
    # 7 h * 10.20 + 9 h * 8.75 + 8 h * 3.45 and 24 h * 7.40.
    assert costs == {"three_zone": "177.75", "single": "177.60"}
    kwh = {total_kwh(t["report"]) for t in result["tariffs"]}
    assert kwh == {total_kwh(result["actual"])} == {"24.000"}


def total_kwh(document: dict[str, Any]) -> str:
    return document["buckets"][0]["total"]["kwh"]


@pytest.mark.usefixtures("seeded")
async def test_compare_subset_and_configured_list(hass: HomeAssistant, hass_ws_client):
    await setup_v2(
        hass,
        [TWO_ZONE, THREE_ZONE, SINGLE],
        applied=[{"from": "2026-01-01", "tariff": "two_zone"}],
        compare=["single"],
    )
    configured = await ws(hass, hass_ws_client, "compare", **COMPARE)
    assert [t["id"] for t in configured["result"]["tariffs"]] == ["single"]
    subset = await ws(
        hass, hass_ws_client, "compare", **COMPARE, tariffs=["two_zone", "single"]
    )
    assert [t["id"] for t in subset["result"]["tariffs"]] == ["two_zone", "single"]
    # The applied tariff compared with itself equals the actual cost.
    assert total_cost(subset["result"]["tariffs"][0]["report"]) == "200.24"


@pytest.mark.usefixtures("seeded")
async def test_compare_explicit_empty_list_compares_nothing(
    hass: HomeAssistant, hass_ws_client
):
    await setup_v2(
        hass,
        [TWO_ZONE, THREE_ZONE, SINGLE],
        applied=[{"from": "2026-01-01", "tariff": "two_zone"}],
    )
    msg = await ws(hass, hass_ws_client, "compare", **COMPARE, tariffs=[])
    assert msg["success"], msg
    assert msg["result"]["tariffs"] == []
    assert total_cost(msg["result"]["actual"]) == "200.24"


@pytest.mark.usefixtures("seeded")
async def test_compare_errors(hass: HomeAssistant, hass_ws_client):
    await setup_v2(
        hass, [TWO_ZONE], applied=[{"from": "2026-01-01", "tariff": "two_zone"}]
    )
    unknown = await ws(hass, hass_ws_client, "compare", **COMPARE, tariffs=["nope"])
    assert unknown["success"] is False
    assert unknown["error"]["code"] == "unknown_tariff"
    bad_period = await ws(
        hass, hass_ws_client, "compare", start="2026-01-16", end="2026-01-15"
    )
    assert bad_period["error"]["code"] == "invalid_period"
    empty = await ws(hass, hass_ws_client, "compare", **COMPARE)
    assert empty["result"]["tariffs"] == []


async def test_compare_not_loaded(hass: HomeAssistant, hass_ws_client):
    from homeassistant.setup import async_setup_component

    assert await async_setup_component(hass, DOMAIN, {})
    msg = await ws(hass, hass_ws_client, "compare", **COMPARE)
    assert msg["error"]["code"] == "not_loaded"


# ---- reconcile after subentry changes (task 018) ----------------------------------


def tariff_subentries(entry: MockConfigEntry) -> dict[str | None, Any]:
    return {
        s.unique_id: s for s in entry.subentries.values() if s.subentry_type == "tariff"
    }


def later_single(valid_from: str) -> dict[str, Any]:
    return {
        **SINGLE,
        "versions": [{**SINGLE["versions"][0], "valid_from": valid_from}],
    }


async def delete_tariff(
    hass: HomeAssistant, entry: MockConfigEntry, tariff_id: str
) -> None:
    hass.config_entries.async_remove_subentry(
        entry, tariff_subentries(entry)[tariff_id].subentry_id
    )
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED


async def test_deleting_an_applied_tariff_lets_the_previous_continue(
    hass: HomeAssistant,
):
    entry = await setup_v2(
        hass,
        [TWO_ZONE, SINGLE],
        applied=[
            {"from": "2026-01-01", "tariff": "single"},
            {"from": "2026-05-01", "tariff": "two_zone"},
        ],
    )
    await delete_tariff(hass, entry, "two_zone")
    assert set(tariff_subentries(entry)) == {"single"}
    assert entry.options["applied"] == [{"from": "2026-01-01", "tariff": "single"}]


async def test_deleting_the_first_applied_tariff(hass: HomeAssistant):
    applied = [
        {"from": "2026-03-01", "tariff": "two_zone"},
        {"from": "2026-05-01", "tariff": "single"},
    ]
    entry = await setup_v2(hass, [TWO_ZONE, SINGLE], applied=applied)
    await delete_tariff(hass, entry, "two_zone")
    # The next tariff has a version on the deleted start, so it takes over the period.
    assert entry.options["applied"] == [{"from": "2026-03-01", "tariff": "single"}]


async def test_deleting_the_first_applied_tariff_keeps_a_later_start(
    hass: HomeAssistant,
):
    applied = [
        {"from": "2026-03-01", "tariff": "two_zone"},
        {"from": "2026-05-01", "tariff": "single"},
    ]
    entry = await setup_v2(
        hass, [TWO_ZONE, later_single("2026-04-01")], applied=applied
    )
    await delete_tariff(hass, entry, "two_zone")
    assert entry.options["applied"] == [{"from": "2026-05-01", "tariff": "single"}]


async def test_deleting_an_applied_tariff_merges_neighbours(hass: HomeAssistant):
    entry = await setup_v2(
        hass,
        [TWO_ZONE, SINGLE],
        applied=[
            {"from": "2026-01-01", "tariff": "single"},
            {"from": "2026-03-01", "tariff": "two_zone"},
            {"from": "2026-05-01", "tariff": "single"},
        ],
    )
    await delete_tariff(hass, entry, "two_zone")
    assert entry.options["applied"] == [{"from": "2026-01-01", "tariff": "single"}]


async def test_deleting_the_only_applied_tariff_applies_the_next(
    hass: HomeAssistant,
):
    entry = await setup_v2(
        hass,
        [TWO_ZONE, later_single("2026-02-01"), THREE_ZONE],
        applied=[{"from": "2026-03-01", "tariff": "two_zone"}],
    )
    await delete_tariff(hass, entry, "two_zone")
    assert entry.options["applied"] == [{"from": "2026-02-01", "tariff": "single"}]
    assert entry.runtime_data.schedule is not None


async def test_deleting_the_last_tariff_leaves_nothing_applied(hass: HomeAssistant):
    entry = await setup_v2(
        hass, [TWO_ZONE], applied=[{"from": "2026-01-01", "tariff": "two_zone"}]
    )
    await delete_tariff(hass, entry, "two_zone")
    assert not tariff_subentries(entry)
    assert "applied" not in entry.options
    assert entry.runtime_data.schedule is None


async def test_deleting_unapplied_tariff(hass: HomeAssistant):
    entry = await setup_v2(
        hass,
        [TWO_ZONE, THREE_ZONE, SINGLE],
        applied=[{"from": "2026-01-01", "tariff": "two_zone"}],
        compare=["three_zone", "single"],
    )
    hass.config_entries.async_remove_subentry(
        entry, tariff_subentries(entry)["three_zone"].subentry_id
    )
    await hass.async_block_till_done()
    assert set(tariff_subentries(entry)) == {"two_zone", "single"}
    assert entry.options["compare"] == ["single"]
    assert entry.state is ConfigEntryState.LOADED


async def test_first_tariff_auto_applied_only_once(hass: HomeAssistant):
    entry = await setup_v2(hass, [])
    assert "applied" not in entry.options
    hass.config_entries.async_add_subentry(
        entry,
        ConfigSubentry(
            data=MappingProxyType(dict(TWO_ZONE)),
            subentry_type="tariff",
            title="Two-zone",
            unique_id="two_zone",
        ),
    )
    await hass.async_block_till_done()
    assert entry.options["applied"] == [{"from": "2026-01-01", "tariff": "two_zone"}]
    assert entry.state is ConfigEntryState.LOADED

    hass.config_entries.async_add_subentry(
        entry,
        ConfigSubentry(
            data=MappingProxyType(dict(SINGLE)),
            subentry_type="tariff",
            title="Single-rate",
            unique_id="single",
        ),
    )
    await hass.async_block_till_done()
    assert entry.options["applied"] == [{"from": "2026-01-01", "tariff": "two_zone"}]


async def test_existing_tariffs_stay_unapplied_after_reload(hass: HomeAssistant):
    entry = await setup_v2(hass, [SINGLE])
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert "applied" not in entry.options
    assert entry.runtime_data.schedule is None
