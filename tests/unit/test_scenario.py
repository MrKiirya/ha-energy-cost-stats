"""Unit tests for tariff comparison scenarios (tasks/015-tariff-comparison.md)."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from engine.models import DeviceSeries, Grouping, ReportRequest
from engine.report import build_report
from engine.scenario import MAX_SCENARIOS, scenario_from_data
from engine.tariff import TariffValidationError

MSK = ZoneInfo("Europe/Moscow")


def test_single_rate_scenario():
    scenario = scenario_from_data({"preset": "single_rate", "prices": {"t0": "7.50"}})
    assert scenario.name == "Single-rate"
    assert scenario.preset == "single_rate"
    (zone,) = scenario.plan.zones
    assert (zone.key, zone.price) == ("t0", Decimal("7.50"))
    assert scenario.plan.valid_from <= date(1970, 1, 1)


def test_three_zone_scenario_with_name_and_period_override():
    scenario = scenario_from_data(
        {
            "name": " Three-zone 2027 ",
            "preset": "ru_three_zone",
            "prices": {"t1": "12,10", "t3": "9.80", "t2": "5"},
            "periods": {
                "t1": "08:00-11:00, 17:00-21:00",
                "t3": "11:00-17:00, 21:00-23:00",
                "t2": "23:00-08:00",
            },
        }
    )
    assert scenario.name == "Three-zone 2027"
    zones = {zone.key: zone for zone in scenario.plan.zones}
    assert zones["t1"].price == Decimal("12.10")
    assert zones["t2"].price == Decimal("5")
    assert scenario.plan.zone_for_hour(7).key == "t2"
    assert scenario.plan.zone_for_hour(8).key == "t1"
    assert scenario.plan.zone_for_hour(11).key == "t3"


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"prices": {"t0": "1"}}, "preset is required"),
        ({"preset": "four_zone", "prices": {}}, "unknown preset"),
        ({"preset": "single_rate"}, "prices must be a mapping"),
        ({"preset": "ru_two_zone", "prices": {"t1": "1"}}, "exactly the zones"),
        ({"preset": "single_rate", "prices": {"t0": 1.5}}, "decimal string"),
        ({"preset": "single_rate", "prices": {"t0": "-1"}}, "price of t0"),
        ({"preset": "single_rate", "prices": {"t0": "abc"}}, "price of t0"),
        (
            {
                "preset": "ru_two_zone",
                "prices": {"t1": "1", "t2": "1"},
                "periods": {"t3": "x"},
            },
            "unknown zones",
        ),
        (
            {
                "preset": "ru_two_zone",
                "prices": {"t1": "1", "t2": "1"},
                "periods": {"t1": "7-23"},
            },
            "periods of t1",
        ),
        (
            {
                "preset": "ru_two_zone",
                "prices": {"t1": "1", "t2": "1"},
                "periods": {"t1": "08:00-23:00"},
            },
            "not covered",
        ),
        (
            {"preset": "single_rate", "prices": {"t0": "1"}, "periods": {"t0": 7}},
            "must be text",
        ),
        ({"preset": "single_rate", "prices": {"t0": "1"}, "name": "  "}, "name"),
        ({"preset": "single_rate", "prices": {"t0": "1"}, "colour": "red"}, "unknown"),
        ({"preset": "single_rate", "prices": {"t0": "1"}, "periods": ["x"]}, "periods"),
    ],
)
def test_invalid_scenarios(data, message):
    with pytest.raises(TariffValidationError, match=message):
        scenario_from_data(data)


def test_max_scenarios_is_small():
    assert 1 <= MAX_SCENARIOS <= 10


def test_scenario_prices_the_same_consumption():
    """Same hours, same quality rules: only the prices and zones change."""
    start = datetime(2026, 1, 14, 21, tzinfo=UTC)  # 2026-01-15 00:00 MSK
    deltas = {start + timedelta(hours=h): Decimal("1") for h in range(-1, 24)}
    series = DeviceSeries(device_id="sensor.plug_01", deltas=deltas)
    request = ReportRequest(start, start + timedelta(days=1), MSK, Grouping.TOTAL)

    flat = scenario_from_data({"preset": "single_rate", "prices": {"t0": "7.50"}})
    report = build_report(request, flat.schedule, [series])
    total = report.totals.total
    assert total.kwh == Decimal("24")
    assert total.cost == Decimal("180.00")

    two = scenario_from_data(
        {"preset": "ru_two_zone", "prices": {"t1": "10.30", "t2": "4.43"}}
    )
    report = build_report(request, two.schedule, [series])
    total = report.totals.total
    # 16 day hours at 10.30 + 8 night hours at 4.43.
    assert total.cost == Decimal("16") * Decimal("10.30") + Decimal("8") * Decimal(
        "4.43"
    )
    assert report.unpriced_hours == 0
