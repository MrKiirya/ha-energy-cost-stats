"""Malformed-document edge cases for engine/tariff_config.py (tasks/017)."""

from datetime import date, datetime

import pytest

from engine.tariff import TariffValidationError
from engine.tariff_config import config_from_data

VERSION = {"valid_from": "2026-01-01", "preset": "single_rate", "prices": {"t0": "7"}}
TARIFF = {"id": "single", "name": "Single", "versions": [VERSION]}


def with_version(**changes):
    return {"tariffs": [{**TARIFF, "versions": [{**VERSION, **changes}]}]}


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ([], "must be an object"),
        ({"tariffs": "x"}, "must be a list"),
        ({"tariffs": ["x"]}, "must be an object"),
        ({"tariffs": [{"id": "a", "name": "A"}]}, "missing keys versions"),
        ({"tariffs": [{**TARIFF, "id": 5}]}, "must be a string"),
        (
            {"tariffs": [{**TARIFF, "versions": [{"preset": "single_rate"}]}]},
            "valid_from",
        ),
        (with_version(valid_from="01.01.2026"), "YYYY-MM-DD"),
        (with_version(valid_from="2026-13-45"), "invalid valid_from"),
        (with_version(prices={"t0": "1,5"}), "decimal string"),
        (with_version(prices={"t0": "-1"}), "invalid price"),
        (with_version(prices=None), "must be an object"),
        (with_version(hours={"t9": "00:00-24:00"}), "unknown zones"),
        (with_version(hours={"t0": 5}), "must be a string"),
        (with_version(preset=3), "must be a string"),
        (with_version(zones=[], preset="x"), "either preset or zones"),
        (
            {
                "tariffs": [
                    {
                        **TARIFF,
                        "versions": [
                            {"valid_from": "2026-01-01", "zones": [{"key": "t1"}]}
                        ],
                    }
                ]
            },
            "missing keys",
        ),
        (
            {
                "tariffs": [
                    {
                        **TARIFF,
                        "versions": [
                            {
                                "valid_from": "2026-01-01",
                                "zones": [
                                    {
                                        "key": "t1",
                                        "name": "A",
                                        "price": "1",
                                        "hours": "00:00-24:00",
                                    }
                                ],
                                "prices": {"t1": "2"},
                            }
                        ],
                    }
                ]
            },
            "not allowed together",
        ),
        ({**with_version(), "applied": 5}, "must be a list"),
        ({**with_version(), "applied": [5]}, "must be an object"),
        ({**with_version(), "applied": [{"from": "2026-01-01"}]}, "missing keys"),
        ({**with_version(), "applied": "nope"}, "unknown tariff"),
        ({**with_version(), "compare": "single"}, "must be a list"),
        ({**with_version(), "compare": [3]}, "must be a string"),
    ],
)
def test_malformed(data, message):
    with pytest.raises(TariffValidationError, match=message):
        config_from_data(data)


def test_missing_prices_for_inherited_version():
    data = {
        "tariffs": [
            {**TARIFF, "versions": [VERSION, {"valid_from": "2026-07-01"}]},
        ]
    }
    with pytest.raises(TariffValidationError, match="needs prices"):
        config_from_data(data)


def test_unknown_tariff_lookup_and_date_objects():
    config = config_from_data(with_version(valid_from=date(2026, 1, 1)))
    assert config.tariff("single").versions[0].valid_from == date(2026, 1, 1)
    with pytest.raises(KeyError):
        config.tariff("nope")


def test_datetime_is_not_a_date():
    with pytest.raises(TariffValidationError, match="valid_from must be a date"):
        config_from_data(with_version(valid_from=datetime(2026, 1, 1, 12, 0)))
