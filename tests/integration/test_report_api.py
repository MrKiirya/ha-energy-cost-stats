"""Report websocket command and service (tasks/013-report-websocket-and-service.md)."""

import asyncio
import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState, ConfigSubentryData
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_cost_stats import report_api
from custom_components.energy_cost_stats.const import DOMAIN

SeedStatistics = Callable[..., Awaitable[None]]
HOUR = timedelta(hours=1)
PLUG_01 = "sensor.plug_01"
PLUG_02 = "sensor.plug_02"
LOOK_BACK = datetime(2026, 1, 14, 20, tzinfo=UTC)
LAST = datetime(2026, 1, 15, 21, tzinfo=UTC)
STRINGS = json.loads(
    (
        Path(__file__).parents[2] / "custom_components/energy_cost_stats/strings.json"
    ).read_text(encoding="utf-8")
)

PLAN: dict[str, Any] = {
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
DAY = {"start": "2026-01-15", "end": "2026-01-16", "grouping": "day"}


def options(**changes: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "time_zone": "Europe/Moscow",
        "spike_limit": "4",
        "device_spike_limits": {},
        "entities": [PLUG_01, PLUG_02],
    }
    return {**base, **changes}


def plan_subentry(data: dict[str, Any] = PLAN) -> ConfigSubentryData:
    return ConfigSubentryData(
        data=data,
        subentry_type="tariff_plan",
        title=f"{data['valid_from']} · {data['name']}",
        unique_id=data["valid_from"],
    )


async def setup_entry(
    hass: HomeAssistant,
    *,
    opts: dict[str, Any] | None = None,
    plans: bool = True,
) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options=opts or options(),
        subentries_data=[plan_subentry()] if plans else [],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def ramp(per_hour: dict[datetime, float] | float) -> dict[datetime, float]:
    """Cumulative sums from LOOK_BACK through LAST for a constant or per-hour change."""
    sums: dict[datetime, float] = {}
    total = 0.0
    current = LOOK_BACK
    while current <= LAST:
        step = per_hour.get(current, 2.0) if isinstance(per_hour, dict) else per_hour
        total += step
        sums[current] = total
        current += HOUR
    return sums


@pytest.fixture
async def seeded(hass: HomeAssistant, seed_statistics: SeedStatistics) -> None:
    await seed_statistics(PLUG_01, ramp(1.0))
    await seed_statistics(PLUG_02, ramp(2.0))
    hass.states.async_set(PLUG_01, "0", {"friendly_name": "Plug 01"})


async def ws_call(hass: HomeAssistant, hass_ws_client, **fields: Any) -> dict[str, Any]:
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "energy_cost_stats/report", **fields})
    return await client.receive_json()


async def ws_report(hass: HomeAssistant, hass_ws_client, **fields: Any) -> Any:
    msg = await ws_call(hass, hass_ws_client, **{**DAY, **fields})
    assert msg["success"], msg
    return msg["result"]


async def service_report(hass: HomeAssistant, **fields: Any) -> Any:
    return await hass.services.async_call(
        DOMAIN,
        "get_report",
        {**DAY, **fields},
        blocking=True,
        return_response=True,
    )


def device_row(bucket: dict[str, Any], entity_id: str) -> dict[str, Any]:
    return next(r for r in bucket["rows"] if r["entity_id"] == entity_id)


def cell(row: dict[str, Any], key: str) -> dict[str, Any]:
    return next(c for c in row["zones"] if c["key"] == key)


@pytest.mark.usefixtures("seeded")
async def test_ws_report_two_zone_day(hass: HomeAssistant, hass_ws_client):
    await setup_entry(hass)
    doc = await ws_report(hass, hass_ws_client)
    assert doc["schema_version"] == 1
    assert doc["time_zone"] == "Europe/Moscow"
    assert doc["start"] == "2026-01-15T00:00:00+03:00"
    assert doc["currency"] == hass.config.currency
    assert doc["issues"] == []
    assert doc["devices"] == [
        {"entity_id": PLUG_01, "name": "Plug 01", "statistics": "ok"},
        {"entity_id": PLUG_02, "name": PLUG_02, "statistics": "ok"},
    ]
    assert len(doc["buckets"]) == 1
    bucket = doc["buckets"][0]
    one = device_row(bucket, PLUG_01)
    assert (cell(one, "t1")["kwh"], cell(one, "t1")["cost"]) == ("16.000", "164.80")
    assert (cell(one, "t2")["kwh"], cell(one, "t2")["cost"]) == ("8.000", "35.44")
    assert (one["cost"], one["kwh"]) == ("200.24", "24.000")
    two = device_row(bucket, PLUG_02)
    assert (cell(two, "t1")["cost"], cell(two, "t2")["cost"]) == ("329.60", "70.88")
    assert two["cost"] == "400.48"
    assert (bucket["total"]["cost"], bucket["total"]["kwh"]) == ("600.72", "72.000")
    assert {r["status"] for r in bucket["rows"]} == {"complete"}


@pytest.mark.usefixtures("seeded")
async def test_service_returns_same_document(hass: HomeAssistant, hass_ws_client):
    await setup_entry(hass)
    via_ws = await ws_report(hass, hass_ws_client)
    via_service = await service_report(hass)
    assert via_service == via_ws
    json.dumps(via_service)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "get_report", DAY, blocking=True)


@pytest.mark.usefixtures("seeded")
async def test_hour_grouping(hass: HomeAssistant, hass_ws_client):
    await setup_entry(hass)
    doc = await ws_report(hass, hass_ws_client, grouping="hour")
    assert len(doc["buckets"]) == 24
    by_start = {b["start"]: b for b in doc["buckets"]}
    seven = device_row(by_start["2026-01-15T07:00:00+03:00"], PLUG_01)
    assert (cell(seven, "t1")["kwh"], cell(seven, "t1")["cost"]) == ("1.000", "10.30")
    assert cell(seven, "t2")["kwh"] is None
    six = device_row(by_start["2026-01-15T06:00:00+03:00"], PLUG_01)
    assert cell(six, "t2")["cost"] == "4.43"


@pytest.mark.usefixtures("seeded")
async def test_entities_subset_and_order(hass: HomeAssistant, hass_ws_client):
    await setup_entry(hass)

    async def ids(**fields: Any) -> list[str]:
        doc = await ws_report(hass, hass_ws_client, **fields)
        return [d["entity_id"] for d in doc["devices"]]

    assert await ids(entities=[PLUG_02]) == [PLUG_02]
    assert await ids(entities=[PLUG_02, PLUG_01, PLUG_02]) == [PLUG_02, PLUG_01]
    assert await ids(entities=[]) == [PLUG_01, PLUG_02]
    assert await ids() == [PLUG_01, PLUG_02]


ERROR_CASES = [
    ({"start": "2026-13-01"}, "invalid_period"),
    ({"start": "yesterday"}, "invalid_period"),
    ({"start": "2026-01-15T07:30:00+03:00", "end": "2026-01-16"}, "invalid_period"),
    ({"start": "2026-1-15"}, "invalid_period"),
    ({"end": "2026-01-15"}, "invalid_period"),
    ({"end": "2026-01-14"}, "invalid_period"),
    (
        {"start": "2026-01-01", "end": "2026-02-02", "grouping": "hour"},
        "period_too_long",
    ),
    (
        {"start": "2016-01-01", "end": "2026-01-16", "grouping": "day"},
        "period_too_long",
    ),
    ({"start": "0001-01-01"}, "invalid_period"),
    ({"end": "9999-12-30"}, "invalid_period"),
    ({"end": "9999-12-31T23:30:00-05:00"}, "invalid_period"),
    ({"start": "1969-12-31"}, "invalid_period"),
    ({"entities": ["sensor.other_01"]}, "unknown_entity"),
]


@pytest.mark.usefixtures("seeded")
@pytest.mark.parametrize(("fields", "code"), ERROR_CASES)
async def test_ws_errors(hass: HomeAssistant, hass_ws_client, fields, code):
    await setup_entry(hass)
    msg = await ws_call(hass, hass_ws_client, **{**DAY, **fields})
    assert msg["success"] is False
    assert msg["error"]["code"] == code
    assert msg["error"]["message"]


@pytest.mark.usefixtures("seeded")
@pytest.mark.parametrize(
    "fields",
    [
        {"grouping": "year"},
        {"start": 20260115},
        {"entities": "sensor.plug_01"},
        {"entities": ["not an id"]},
    ],
)
async def test_ws_schema_errors(hass: HomeAssistant, hass_ws_client, fields):
    await setup_entry(hass)
    msg = await ws_call(hass, hass_ws_client, **{**DAY, **fields})
    assert msg["success"] is False
    assert msg["error"]["code"] == "invalid_format"


@pytest.mark.usefixtures("seeded")
@pytest.mark.parametrize(("fields", "code"), ERROR_CASES)
async def test_service_errors(hass: HomeAssistant, fields, code):
    await setup_entry(hass)
    with pytest.raises(ServiceValidationError) as err:
        await service_report(hass, **fields)
    assert err.value.translation_domain == DOMAIN
    assert err.value.translation_key == code
    assert code in STRINGS["exceptions"]
    assert STRINGS["exceptions"][code]["message"]
    with pytest.raises(vol.Invalid):
        await service_report(hass, grouping="year")


def test_all_error_codes_translated():
    assert set(STRINGS["exceptions"]) == {
        "not_loaded",
        "invalid_period",
        "period_too_long",
        "unknown_entity",
    }
    service = STRINGS["services"]["get_report"]
    assert {"name", "description"} <= set(service)
    assert set(service["fields"]) == {"start", "end", "grouping", "entities"}
    assert "string" in service["description"]
    assert set(STRINGS["selector"]["grouping"]["options"]) == {
        "hour",
        "day",
        "week",
        "month",
        "total",
    }


async def test_not_loaded(hass: HomeAssistant, hass_ws_client):
    assert await async_setup_component(hass, DOMAIN, {})
    assert hass.services.has_service(DOMAIN, "get_report")
    msg = await ws_call(hass, hass_ws_client, **DAY)
    assert msg["error"]["code"] == "not_loaded"
    with pytest.raises(ServiceValidationError) as err:
        await service_report(hass)
    assert err.value.translation_key == "not_loaded"

    entry = await setup_entry(hass)
    assert entry.state is ConfigEntryState.LOADED
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.services.has_service(DOMAIN, "get_report")
    msg = await ws_call(hass, hass_ws_client, **DAY)
    assert msg["error"]["code"] == "not_loaded"
    with pytest.raises(ServiceValidationError) as err:
        await service_report(hass)
    assert err.value.translation_key == "not_loaded"


@pytest.mark.usefixtures("seeded")
@pytest.mark.parametrize(
    "start",
    [
        "2026-01-15T07:00:00",
        "2026-01-15T07:00:00+03:00",
        "2026-01-15 07:00:00",
        "2026-01-15T04:00:00Z",
    ],
)
async def test_naive_and_offset_datetimes(hass: HomeAssistant, hass_ws_client, start):
    await setup_entry(hass)
    doc = await ws_report(
        hass, hass_ws_client, start=start, end="2026-01-15T23:00:00", grouping="total"
    )
    assert doc["start"] == "2026-01-15T07:00:00+03:00"
    assert doc["end"] == "2026-01-15T23:00:00+03:00"


@pytest.mark.usefixtures("seeded")
async def test_half_hour_time_zone_date_bounds(hass: HomeAssistant, hass_ws_client):
    await setup_entry(hass, opts=options(time_zone="Asia/Kolkata"))
    doc = await ws_report(hass, hass_ws_client)
    assert doc["time_zone"] == "Asia/Kolkata"
    assert doc["start"] == "2026-01-15T00:30:00+05:30"
    assert doc["end"] == "2026-01-16T00:30:00+05:30"


@pytest.mark.usefixtures("seeded")
async def test_no_plan_reports_unpriced(hass: HomeAssistant, hass_ws_client):
    await setup_entry(hass, plans=False)
    doc = await ws_report(hass, hass_ws_client)
    assert doc["zones"] == []
    assert doc["plans"] == []
    row = device_row(doc["buckets"][0], PLUG_01)
    assert row["cost"] is None
    assert row["unpriced_kwh"] == "24.000"
    assert doc["unpriced_hours"] == 24


@pytest.mark.usefixtures("seeded")
async def test_retroactive_reprice(hass: HomeAssistant, hass_ws_client):
    entry = await setup_entry(hass)
    before = await ws_report(hass, hass_ws_client)
    assert device_row(before["buckets"][0], PLUG_01)["cost"] == "200.24"
    subentry = next(iter(entry.subentries.values()))
    repriced = {
        **PLAN,
        "zones": [{**PLAN["zones"][0], "price": "11.00"}, PLAN["zones"][1]],
    }
    hass.config_entries.async_update_subentry(entry, subentry, data=repriced)
    await hass.async_block_till_done()
    after = await ws_report(hass, hass_ws_client)
    row = device_row(after["buckets"][0], PLUG_01)
    assert cell(row, "t1")["cost"] == "176.00"
    assert row["cost"] == "211.44"
    assert row["kwh"] == "24.000"


async def test_quality_settings_applied(
    hass: HomeAssistant, hass_ws_client, seed_statistics: SeedStatistics
):
    spike_hour = datetime(2026, 1, 15, 9, tzinfo=UTC)  # local 12:00
    gap = {datetime(2026, 1, 15, 2, tzinfo=UTC) + i * HOUR for i in range(3)}
    plug_01 = {k: v for k, v in ramp(1.0).items() if k not in gap}
    await seed_statistics(PLUG_01, plug_01)
    await seed_statistics(PLUG_02, ramp({spike_hour: 5.0}))
    entry = await setup_entry(hass)
    doc = await ws_report(hass, hass_ws_client)
    two = device_row(doc["buckets"][0], PLUG_02)
    assert two["excluded_kwh"] == "5.000"
    assert two["status"] == "partial"
    spikes = [i for i in doc["issues"] if i["kind"] == "excluded_spike"]
    assert len(spikes) == 1
    assert spikes[0]["hours"] == 1
    one = device_row(doc["buckets"][0], PLUG_01)
    assert one["status"] == "estimated"
    assert any(i["kind"] == "estimated" for i in doc["issues"])

    hass.config_entries.async_update_entry(
        entry, options=options(device_spike_limits={PLUG_02: None})
    )
    await hass.async_block_till_done()
    doc = await ws_report(hass, hass_ws_client)
    two = device_row(doc["buckets"][0], PLUG_02)
    assert two["status"] == "complete"
    assert not [
        i
        for i in doc["issues"]
        if i["kind"] == "excluded_spike" and i["entity_id"] == PLUG_02
    ]


async def test_device_without_statistics(
    hass: HomeAssistant, hass_ws_client, seed_statistics: SeedStatistics
):
    await seed_statistics(PLUG_01, ramp(1.0))
    await seed_statistics(PLUG_02, ramp(1.0))
    await seed_statistics("sensor.plug_04", ramp(1.0), unit="W")
    await setup_entry(
        hass,
        opts=options(entities=[PLUG_01, PLUG_02, "sensor.plug_03", "sensor.plug_04"]),
    )
    doc = await ws_report(hass, hass_ws_client)
    assert [d["statistics"] for d in doc["devices"]] == [
        "ok",
        "ok",
        "no_statistics",
        "unsupported",
    ]
    rows = doc["buckets"][0]["rows"]
    assert rows[2]["kwh"] is None
    assert rows[2]["status"] == "missing"
    assert rows[3]["kwh"] is None
    assert rows[0]["status"] == "complete"
    assert rows[0]["kwh"] == "24.000"


@pytest.mark.usefixtures("seeded")
async def test_non_admin_may_call_ws(
    hass: HomeAssistant, hass_ws_client, hass_read_only_access_token
):
    await setup_entry(hass)
    client = await hass_ws_client(hass, hass_read_only_access_token)
    await client.send_json_auto_id({"type": "energy_cost_stats/report", **DAY})
    assert (await client.receive_json())["success"]


@pytest.mark.usefixtures("seeded")
async def test_engine_runs_in_executor(hass: HomeAssistant, hass_ws_client):
    await setup_entry(hass)
    real = report_api.build_report
    calls: list[bool] = []

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        with pytest.raises(RuntimeError):
            asyncio.get_running_loop()
        calls.append(True)
        return real(*args, **kwargs)

    with patch.object(report_api, "build_report", wrapper):
        await ws_report(hass, hass_ws_client)
    assert calls == [True]


@pytest.mark.usefixtures("seeded")
async def test_time_zone_name_matches_report_zone(hass: HomeAssistant):
    entry = await setup_entry(hass)
    doc = await service_report(hass)
    assert doc["time_zone"] == entry.runtime_data.settings.time_zone
    # A runtime zone that disagrees with the configured name is refused.
    entry.runtime_data.tzinfo = ZoneInfo("Europe/Berlin")
    with pytest.raises(RuntimeError):
        await service_report(hass)


@pytest.mark.usefixtures("seeded")
async def test_no_entities_created(hass: HomeAssistant, hass_ws_client):
    await setup_entry(hass)
    await ws_report(hass, hass_ws_client)
    # Only the state seeded by the fixture exists; the integration added none.
    assert {s.entity_id for s in hass.states.async_all()} == {PLUG_01}
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    assert not [e for e in registry.entities.values() if e.platform == DOMAIN]
