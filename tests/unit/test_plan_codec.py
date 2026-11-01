"""Unit tests for the tariff plan codec (tasks/010-tariff-plan-subentries.md)."""

import json
from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from engine.plan_codec import (
    format_periods,
    parse_periods,
    parse_price,
    plan_from_data,
    plan_to_data,
)
from engine.presets import ru_three_zone, ru_two_zone, single_rate
from engine.tariff import Period, TariffPlan, TariffValidationError, Zone

START = date(2026, 1, 1)


def _two_zone() -> TariffPlan:
    return ru_two_zone(
        valid_from=START, day_price=Decimal("10.30"), night_price=Decimal("4.43")
    )


def _banded() -> TariffPlan:
    return TariffPlan(
        valid_from=START,
        name="Banded",
        zones=(
            Zone(
                "t1",
                "Day",
                Decimal("10.30"),
                (Period(7, 23),),
                (Decimal("11.00"), Decimal("12.50")),
            ),
            Zone(
                "t2",
                "Night",
                Decimal("4.43"),
                (Period(23, 7),),
                (Decimal("5"), Decimal("6")),
            ),
        ),
        volume_band_limits_kwh=(Decimal("3900"), Decimal("6000")),
    )


def _valid_data() -> dict[str, Any]:
    return plan_to_data(_two_zone())


def test_two_zone_to_data_exact():
    data = plan_to_data(_two_zone())
    assert data == {
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
    json.dumps(data)


@pytest.mark.parametrize(
    "plan",
    [
        single_rate(valid_from=START, price=Decimal("7.50")),
        _two_zone(),
        ru_three_zone(
            valid_from=START,
            peak_price=Decimal("12.1"),
            semi_peak_price=Decimal("9"),
            night_price=Decimal("4.43"),
        ),
        _banded(),
    ],
)
def test_roundtrip(plan: TariffPlan):
    data = plan_to_data(plan)
    assert plan_from_data(data) == plan
    assert plan_from_data(json.loads(json.dumps(data))) == plan


def test_bands_written_only_when_present():
    data = plan_to_data(_banded())
    assert data["volume_band_limits_kwh"] == ["3900", "6000"]
    assert data["zones"][0]["band_prices"] == ["11.00", "12.50"]
    plain = plan_to_data(_two_zone())
    assert "volume_band_limits_kwh" not in plain
    assert "band_prices" not in plain["zones"][0]


def test_full_day_end_written_as_24():
    data = plan_to_data(single_rate(valid_from=START, price=Decimal("7")))
    assert data["zones"][0]["periods"] == [["00:00", "24:00"]]
    data["zones"][0]["periods"] = [["00:00", "00:00"]]
    assert plan_from_data(data).zones[0].periods == (Period(0, 24),)


def test_price_scale_preserved_no_exponent():
    def written(price: str) -> str:
        plan = single_rate(valid_from=START, price=Decimal(price))
        return plan_to_data(plan)["zones"][0]["price"]

    assert written("10.30") == "10.30"
    assert written("1E+1") == "10"
    assert written("0") == "0"


def _mutated(mutate: Any) -> dict[str, Any]:
    data = _valid_data()
    mutate(data)
    return data


def _set(path: list[Any], value: Any) -> dict[str, Any]:
    def mutate(data: dict[str, Any]) -> None:
        target: Any = data
        for part in path[:-1]:
            target = target[part]
        target[path[-1]] = value

    return _mutated(mutate)


def _delete(key: str) -> dict[str, Any]:
    return _mutated(lambda data: data.pop(key))


@pytest.mark.parametrize(
    "data",
    [
        _delete("zones"),
        _set(["extra"], 1),
        _set(["zones", 0, "extra"], 1),
        _set(["valid_from"], 20260101),
        _set(["valid_from"], "2026-1-1"),
        _set(["valid_from"], "2026-01-01T00:00:00"),
        _set(["name"], "  "),
        _set(["zones"], {}),
        _set(["zones"], []),
        _set(["zones", 0, "price"], 10.3),
        _set(["zones", 0, "price"], 10),
        _set(["zones", 0, "price"], True),
        _set(["zones", 0, "price"], "-1"),
        _set(["zones", 0, "price"], "NaN"),
        _set(["zones", 0, "price"], "abc"),
        _set(["zones", 0, "price"], "10,30"),
        _set(["valid_from"], "2026-02-30"),
        _set(["valid_from"], "2026-13-01"),
        _set(["zones", 0, "periods"], "07:00-23:00"),
        _set(["zones", 0, "periods"], [["07:00"]]),
        _set(["zones", 0, "periods"], [[7, 23]]),
        _set(["zones", 0, "periods"], [["07:00", "22:00"]]),
        _set(["zones", 0, "key"], 1),
        _set(["zones", 0, "name"], 1),
        _set(["name"], 1),
        _set(["zones", 0, "band_prices"], [10.3]),
        _set(["volume_band_limits_kwh"], [3900]),
    ],
)
def test_from_data_rejects(data: dict[str, Any]):
    with pytest.raises(TariffValidationError):
        plan_from_data(data)


def test_from_data_rejects_non_mapping_and_zone():
    with pytest.raises(TariffValidationError):
        plan_from_data([])  # type: ignore[arg-type]
    with pytest.raises(TariffValidationError):
        plan_from_data(_set(["zones"], ["x"]))


def test_from_data_keeps_engine_message():
    data = _set(["zones", 0, "periods"], [["07:00", "22:00"]])
    with pytest.raises(TariffValidationError, match="22"):
        plan_from_data(data)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("10.30", Decimal("10.30")),
        ("10,30", Decimal("10.30")),
        (" 4.43 ", Decimal("4.43")),
        ("0", Decimal("0")),
        ("7", Decimal("7")),
    ],
)
def test_parse_price(text: str, expected: Decimal):
    result = parse_price(text)
    assert result == expected
    assert str(result) == str(expected)


@pytest.mark.parametrize(
    "text",
    ["", " ", "-1", "+1", "abc", "1e3", "NaN", "Infinity", "1.2.3", "1,234.5"],
)
def test_parse_price_invalid(text: str):
    with pytest.raises(TariffValidationError):
        parse_price(text)


def test_parse_price_rejects_non_ascii_digits():
    with pytest.raises(TariffValidationError):
        parse_price("\u0661\u0660")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("07:00-23:00", (Period(7, 23),)),
        ("07:00-10:00, 17:00-21:00", (Period(7, 10), Period(17, 21))),
        ("23:00 \u2013 07:00", (Period(23, 7),)),
        ("00:00-24:00", (Period(0, 24),)),
        ("07:00-10:00; 17:00-21:00", (Period(7, 10), Period(17, 21))),
    ],
)
def test_parse_periods(text: str, expected: tuple[Period, ...]):
    assert parse_periods(text) == expected


@pytest.mark.parametrize(
    "text",
    ["", "7-23", "07:30-08:00", "07:00-07:00", "07:00", "07:00-23:00,"],
)
def test_parse_periods_invalid(text: str):
    with pytest.raises(TariffValidationError):
        parse_periods(text)


def test_format_periods_inverse():
    assert format_periods((Period(7, 10), Period(17, 21))) == "07:00-10:00, 17:00-21:00"
    assert format_periods((Period(0, 24),)) == "00:00-24:00"
    for plan in (
        single_rate(valid_from=START, price=Decimal("1")),
        _two_zone(),
        ru_three_zone(
            valid_from=START,
            peak_price=Decimal("1"),
            semi_peak_price=Decimal("1"),
            night_price=Decimal("1"),
        ),
    ):
        for zone in plan.zones:
            assert parse_periods(format_periods(zone.periods)) == zone.periods
