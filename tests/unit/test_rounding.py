"""Unit tests for engine.rounding (tasks/006-pricing-and-grouping.md)."""

from decimal import Decimal, localcontext

import pytest

from engine.rounding import (
    KWH_QUANTUM,
    MONEY_QUANTUM,
    PRICE_QUANTUM,
    round_kwh,
    round_money,
    round_price,
)


def test_quanta():
    assert Decimal("0.01") == MONEY_QUANTUM
    assert Decimal("0.001") == KWH_QUANTUM
    assert Decimal("0.0001") == PRICE_QUANTUM


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0.005", "0.01"),
        ("0.0049", "0.00"),
        ("-0.005", "-0.01"),
        ("-0.004", "0.00"),
        ("200.24", "200.24"),
        ("1E+2", "100.00"),
        ("164.8", "164.80"),
    ],
)
def test_round_money(value, expected):
    assert str(round_money(Decimal(value))) == expected


def test_round_kwh_and_price():
    assert str(round_kwh(Decimal("0.0005"))) == "0.001"
    assert str(round_kwh(Decimal("12"))) == "12.000"
    assert str(round_kwh(Decimal("-0.0004"))) == "0.000"
    assert str(round_price(Decimal("10.30"))) == "10.3000"
    assert str(round_price(Decimal("10.7"))) == "10.7000"
    assert str(round_price(Decimal("4.43005"))) == "4.4301"


@pytest.mark.parametrize("helper", [round_money, round_kwh, round_price])
@pytest.mark.parametrize(
    "bad", [Decimal("NaN"), Decimal("Infinity"), 1.0, 1, True], ids=repr
)
def test_rounding_rejects_bad_input(helper, bad):
    with pytest.raises(ValueError):
        helper(bad)


def test_rounding_large_values_independent_of_context():
    with localcontext(prec=5):
        result = round_money(Decimal("12345678901234567890123456789.005"))
    assert str(result) == "12345678901234567890123456789.01"
