"""Unit tests for tariffs with versions, applied history and comparison (tasks/017)."""

from datetime import date
from decimal import Decimal

import pytest

from engine.tariff import TariffValidationError
from engine.tariff_config import (
    AppliedChange,
    comparison_schedule,
    config_from_data,
    default_compare,
    effective_schedule,
)

TWO_ZONE = {
    "id": "two_zone",
    "name": "Two-zone",
    "versions": [
        {
            "valid_from": "2026-01-01",
            "preset": "ru_two_zone",
            "prices": {"t1": "8.10", "t2": "3.20"},
        },
        {"valid_from": "2026-07-01", "prices": {"t1": "8.75", "t2": "3.45"}},
    ],
}
THREE_ZONE = {
    "id": "three_zone",
    "name": "Three-zone",
    "versions": [
        {
            "valid_from": "2026-07-01",
            "zones": [
                {
                    "key": "t1",
                    "name": "Peak",
                    "price": "10.20",
                    "hours": "07:00-10:00, 17:00-21:00",
                },
                {
                    "key": "t3",
                    "name": "Semi-peak",
                    "price": "8.75",
                    "hours": "10:00-17:00, 21:00-23:00",
                },
                {"key": "t2", "name": "Night", "price": "3.45", "hours": "23:00-07:00"},
            ],
        }
    ],
}
SINGLE = {
    "id": "single",
    "name": "Single-rate",
    "versions": [
        {"valid_from": "2026-01-01", "preset": "single_rate", "prices": {"t0": "7.40"}}
    ],
}


def doc(**changes):
    base = {
        "tariffs": [TWO_ZONE, THREE_ZONE, SINGLE],
        "applied": [{"from": "2026-01-01", "tariff": "two_zone"}],
    }
    return {**base, **changes}


def prices(plan):
    return {zone.key: zone.price for zone in plan.zones}


# ---- parsing -------------------------------------------------------------------


def test_preset_versions_and_inheritance():
    config = config_from_data(doc())
    tariff = config.tariff("two_zone")
    assert tariff.name == "Two-zone"
    first, second = tariff.versions
    assert first.valid_from == date(2026, 1, 1)
    assert prices(first) == {"t1": Decimal("8.10"), "t2": Decimal("3.20")}
    # The second version inherits keys, names and hours; only prices change.
    assert prices(second) == {"t1": Decimal("8.75"), "t2": Decimal("3.45")}
    assert [z.name for z in second.zones] == [z.name for z in first.zones]
    assert second.zone_for_hour(6).key == "t2"
    assert second.zone_for_hour(7).key == "t1"
    assert second.name == "Two-zone"


def test_explicit_zones():
    plan = config_from_data(doc()).tariff("three_zone").versions[0]
    assert [z.key for z in plan.zones] == ["t1", "t3", "t2"]
    assert plan.zone_for_hour(8).name == "Peak"
    assert plan.zone_for_hour(12).key == "t3"


def test_hours_override_on_preset_and_inherited_version():
    data = doc(
        tariffs=[
            {
                "id": "two_zone",
                "name": "Two-zone",
                "versions": [
                    {
                        "valid_from": "2026-01-01",
                        "preset": "ru_two_zone",
                        "prices": {"t1": "8", "t2": "3"},
                        "hours": {"t1": "08:00-23:00", "t2": "23:00-08:00"},
                    },
                    {
                        "valid_from": "2026-07-01",
                        "prices": {"t1": "9", "t2": "4"},
                        "hours": {"t1": "07:00-22:00", "t2": "22:00-07:00"},
                    },
                ],
            }
        ]
    )
    first, second = config_from_data(data).tariff("two_zone").versions
    assert first.zone_for_hour(7).key == "t2"
    assert second.zone_for_hour(22).key == "t2"
    assert second.zone_for_hour(7).key == "t1"


def test_version_with_preset_starts_a_new_zone_set():
    data = doc(
        tariffs=[
            {
                "id": "home",
                "name": "Home",
                "versions": [
                    {
                        "valid_from": "2026-01-01",
                        "preset": "single_rate",
                        "prices": {"t0": "7"},
                    },
                    {
                        "valid_from": "2026-07-01",
                        "preset": "ru_two_zone",
                        "prices": {"t1": "9", "t2": "4"},
                    },
                ],
            }
        ],
        applied="home",
    )
    first, second = config_from_data(data).tariff("home").versions
    assert [z.key for z in first.zones] == ["t0"]
    assert [z.key for z in second.zones] == ["t1", "t2"]


def test_versions_are_sorted():
    data = doc(
        tariffs=[{**TWO_ZONE, "versions": list(reversed(TWO_ZONE["versions"]))}],
    )
    # Inheritance follows date order even when written out of order.
    versions = config_from_data(data).tariff("two_zone").versions
    assert [v.valid_from for v in versions] == [date(2026, 1, 1), date(2026, 7, 1)]
    assert prices(versions[1]) == {"t1": Decimal("8.75"), "t2": Decimal("3.45")}


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"tariffs": [{**TWO_ZONE, "id": "Two Zone"}]}, "id"),
        ({"tariffs": [TWO_ZONE, {**SINGLE, "id": "two_zone"}]}, "duplicate tariff id"),
        ({"tariffs": [{**TWO_ZONE, "name": " "}]}, "name"),
        ({"tariffs": [{**TWO_ZONE, "versions": []}]}, "at least one version"),
        (
            {
                "tariffs": [
                    {
                        **TWO_ZONE,
                        "versions": [TWO_ZONE["versions"][0], TWO_ZONE["versions"][0]],
                    }
                ]
            },
            "duplicate valid_from",
        ),
        (
            {
                "tariffs": [
                    {
                        **TWO_ZONE,
                        "versions": [
                            {"valid_from": "2026-01-01", "prices": {"t1": "1"}}
                        ],
                    }
                ]
            },
            "preset or zones",
        ),
        (
            {
                "tariffs": [
                    {
                        **TWO_ZONE,
                        "versions": [
                            {
                                "valid_from": "2026-01-01",
                                "preset": "ru_two_zone",
                                "prices": {"t1": "1"},
                            }
                        ],
                    }
                ]
            },
            "prices",
        ),
        (
            {
                "tariffs": [
                    {
                        **TWO_ZONE,
                        "versions": [
                            {
                                "valid_from": "2026-01-01",
                                "preset": "ru_two_zone",
                                "prices": {"t1": "1", "t2": "1"},
                                "zones": THREE_ZONE["versions"][0]["zones"],
                            }
                        ],
                    }
                ]
            },
            "either preset or zones",
        ),
        (
            {
                "tariffs": [
                    {
                        **TWO_ZONE,
                        "versions": [
                            {
                                "valid_from": "2026-01-01",
                                "preset": "ru_two_zone",
                                "prices": {"t1": "1", "t2": "1"},
                                "hours": {"t1": "08:00-23:00"},
                            }
                        ],
                    }
                ]
            },
            "not covered",
        ),
        (
            {
                "tariffs": [
                    {
                        **TWO_ZONE,
                        "versions": [
                            {
                                "valid_from": "2026-01-01",
                                "preset": "ru_two_zone",
                                "prices": {"t1": "1", "t2": "1"},
                                "hours": {"t1": "06:00-23:00"},
                            }
                        ],
                    }
                ]
            },
            "covered by zones",
        ),
        (
            {
                "tariffs": [
                    {
                        **TWO_ZONE,
                        "versions": [
                            {
                                "valid_from": "2026-01-01",
                                "preset": "ru_two_zone",
                                "prices": {"t1": "1", "t2": "1"},
                                "hours": {"t1": {"mon-fri": "07:00-23:00"}},
                            }
                        ],
                    }
                ]
            },
            "weekday",
        ),
        (
            {
                "tariffs": [
                    {
                        **TWO_ZONE,
                        "versions": [
                            {
                                "valid_from": "2026-01-01",
                                "preset": "four_zone",
                                "prices": {},
                            }
                        ],
                    }
                ]
            },
            "unknown preset",
        ),
        ({"tariffs": [{**TWO_ZONE, "colour": "red"}]}, "unknown keys"),
        (
            {
                "tariffs": [
                    {
                        **SINGLE,
                        "versions": [{**SINGLE["versions"][0], "prices": {"t0": 7.4}}],
                    }
                ]
            },
            "decimal string",
        ),
        ({"applied": [{"from": "2026-01-01", "tariff": "nope"}]}, "unknown tariff"),
        (
            {
                "applied": [
                    {"from": "2026-07-01", "tariff": "two_zone"},
                    {"from": "2026-07-01", "tariff": "single"},
                ]
            },
            "duplicate",
        ),
        ({"applied": [{"from": "2026-06-01", "tariff": "three_zone"}]}, "no version"),
        ({"compare": ["nope"]}, "unknown tariff"),
        ({"surprise": 1}, "unknown keys"),
    ],
)
def test_invalid_documents(change, message):
    with pytest.raises(TariffValidationError, match=message):
        config_from_data(doc(**change))


def test_empty_document():
    config = config_from_data({})
    assert config.tariffs == ()
    assert config.applied == ()
    assert effective_schedule(config) is None


def test_short_applied_form():
    config = config_from_data(doc(applied="three_zone"))
    assert config.applied == (AppliedChange(date(2026, 7, 1), "three_zone"),)


def test_applied_is_sorted():
    config = config_from_data(
        doc(
            applied=[
                {"from": "2026-09-01", "tariff": "single"},
                {"from": "2026-01-01", "tariff": "two_zone"},
            ]
        )
    )
    assert [c.tariff for c in config.applied] == ["two_zone", "single"]


# ---- schedules -----------------------------------------------------------------


def test_effective_schedule_across_a_switch():
    config = config_from_data(
        doc(
            applied=[
                {"from": "2026-01-01", "tariff": "two_zone"},
                {"from": "2026-09-01", "tariff": "three_zone"},
            ]
        )
    )
    schedule = effective_schedule(config)
    assert schedule is not None
    assert [p.valid_from for p in schedule.plans] == [
        date(2026, 1, 1),
        date(2026, 7, 1),
        date(2026, 9, 1),
    ]
    assert prices(schedule.plan_for(date(2026, 8, 31))) == {
        "t1": Decimal("8.75"),
        "t2": Decimal("3.45"),
    }
    # The three-zone version valid since July is re-dated to the switch date.
    switched = schedule.plan_for(date(2026, 9, 1))
    assert switched is not None
    assert [z.key for z in switched.zones] == ["t1", "t3", "t2"]
    assert switched.name == "Three-zone"
    assert schedule.plan_for(date(2025, 12, 31)) is None


def test_effective_schedule_drops_versions_outside_the_applied_interval():
    config = config_from_data(
        doc(
            applied=[
                {"from": "2026-01-01", "tariff": "single"},
                {"from": "2026-03-01", "tariff": "two_zone"},
            ]
        )
    )
    schedule = effective_schedule(config)
    assert schedule is not None
    assert [(p.valid_from, p.name) for p in schedule.plans] == [
        (date(2026, 1, 1), "Single-rate"),
        (date(2026, 3, 1), "Two-zone"),  # 2026-01-01 version re-dated
        (date(2026, 7, 1), "Two-zone"),
    ]


def test_no_applied_means_unpriced():
    assert effective_schedule(config_from_data(doc(applied=[]))) is None


def test_comparison_schedule_and_default_compare():
    config = config_from_data(doc())
    schedule = comparison_schedule(config.tariff("three_zone"))
    assert [p.valid_from for p in schedule.plans] == [date(2026, 7, 1)]
    assert default_compare(config) == ("three_zone", "single")
    assert config_from_data(doc(compare=["single"])).compare == ("single",)
    # A tariff applied at some point is not compared by default.
    switched = config_from_data(
        doc(
            applied=[
                {"from": "2026-01-01", "tariff": "two_zone"},
                {"from": "2026-09-01", "tariff": "three_zone"},
            ]
        )
    )
    assert default_compare(switched) == ("single",)


def test_compare_defaults_when_absent():
    assert config_from_data(doc()).compare == ("three_zone", "single")
