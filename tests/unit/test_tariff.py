"""Unit tests for the tariff data model (tasks/004-tariff-model.md)."""

import dataclasses
from datetime import date
from decimal import Decimal

import pytest

from engine.tariff import (
    Period,
    TariffPlan,
    TariffSchedule,
    TariffValidationError,
    Zone,
)


def _two_zone_plan(valid_from: date = date(2026, 1, 1)) -> TariffPlan:
    return TariffPlan(
        valid_from=valid_from,
        name="Two-zone",
        zones=(
            Zone(
                key="t1",
                name="Day",
                price=Decimal("10.30"),
                periods=(Period(7, 23),),
            ),
            Zone(
                key="t2",
                name="Night",
                price=Decimal("4.43"),
                periods=(Period(23, 7),),
            ),
        ),
    )


# --- Period ---------------------------------------------------------------


def test_period_hours_simple():
    assert Period(7, 23).hours() == tuple(range(7, 23))


def test_period_crossing_midnight():
    assert Period(23, 7).hours() == (23, 0, 1, 2, 3, 4, 5, 6)


def test_period_full_day():
    assert Period(0, 24).hours() == tuple(range(24))


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (24, 5),
        (-1, 5),
        (5, 5),
        (5, 0),
        (5, 25),
        (True, 5),
    ],
)
def test_period_invalid(start, end):
    with pytest.raises(TariffValidationError):
        Period(start, end)


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        ("07:00", "23:00", (7, 23)),
        ("23:00", "00:00", (23, 24)),
        ("00:00", "00:00", (0, 24)),
        ("00:00", "24:00", (0, 24)),
        ("23:00", "07:00", (23, 7)),
    ],
)
def test_period_parse_valid(start, end, expected):
    period = Period.parse(start, end)
    assert (period.start_hour, period.end_hour) == expected


@pytest.mark.parametrize(
    ("start", "end"),
    [
        ("07:30", "23:00"),
        ("7", "23:00"),
        ("25:00", "07:00"),
        ("24:00", "07:00"),
        ("ab:cd", "07:00"),
        ("07:00", "07:00"),
        ("07:00\n", "23:00"),
    ],
)
def test_period_parse_invalid(start, end):
    with pytest.raises(TariffValidationError):
        Period.parse(start, end)


# --- Zone -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("key", "name", "price", "periods"),
    [
        ("", "Day", Decimal("1"), (Period(0, 24),)),
        ("T 1", "Day", Decimal("1"), (Period(0, 24),)),
        ("a" * 33, "Day", Decimal("1"), (Period(0, 24),)),
        ("t1", "  ", Decimal("1"), (Period(0, 24),)),
        ("t1", "Day", Decimal("-0.01"), (Period(0, 24),)),
        ("t1", "Day", Decimal("NaN"), (Period(0, 24),)),
        ("t1", "Day", Decimal("Infinity"), (Period(0, 24),)),
        ("t1", "Day", 10.3, (Period(0, 24),)),
        ("t1", "Day", Decimal("1"), ()),
        ("t1\n", "Day", Decimal("1"), (Period(0, 24),)),
    ],
)
def test_zone_invalid(key, name, price, periods):
    with pytest.raises(TariffValidationError):
        Zone(key=key, name=name, price=price, periods=periods)


# --- TariffPlan ---------------------------------------------------------------


def test_plan_zone_for_hour_two_zone():
    plan = _two_zone_plan()
    assert plan.zone_keys() == ("t1", "t2")
    for hour in (0, 1, 2, 3, 4, 5, 6, 23):
        assert plan.zone_for_hour(hour).key == "t2"
    for hour in range(7, 23):
        assert plan.zone_for_hour(hour).key == "t1"
    with pytest.raises(ValueError, match="24"):
        plan.zone_for_hour(24)
    with pytest.raises(ValueError, match="-1"):
        plan.zone_for_hour(-1)


def test_plan_multiple_periods_per_zone():
    plan = TariffPlan(
        valid_from=date(2026, 1, 1),
        name="Three-zone",
        zones=(
            Zone(
                key="t1",
                name="Peak",
                price=Decimal("1"),
                periods=(Period(7, 10), Period(17, 21)),
            ),
            Zone(
                key="t3",
                name="Rest",
                price=Decimal("1"),
                periods=(Period(10, 17), Period(21, 24), Period(0, 7)),
            ),
        ),
    )
    for hour in (7, 8, 9, 17, 18, 19, 20):
        assert plan.zone_for_hour(hour).key == "t1"


def test_plan_coverage_gap():
    with pytest.raises(TariffValidationError) as exc_info:
        TariffPlan(
            valid_from=date(2026, 1, 1),
            name="Broken",
            zones=(
                Zone(
                    key="t1",
                    name="Day",
                    price=Decimal("1"),
                    periods=(Period(7, 23),),
                ),
            ),
        )
    message = str(exc_info.value)
    assert "23" in message
    assert "0" in message


def test_plan_coverage_overlap():
    with pytest.raises(TariffValidationError, match="22"):
        TariffPlan(
            valid_from=date(2026, 1, 1),
            name="Broken",
            zones=(
                Zone(
                    key="t1",
                    name="Day",
                    price=Decimal("1"),
                    periods=(Period(7, 23),),
                ),
                Zone(
                    key="t2",
                    name="Night",
                    price=Decimal("1"),
                    periods=(Period(22, 7),),
                ),
            ),
        )


def test_plan_duplicate_zone_key_and_empty():
    with pytest.raises(TariffValidationError):
        TariffPlan(
            valid_from=date(2026, 1, 1),
            name="Dup",
            zones=(
                Zone(key="t1", name="A", price=Decimal("1"), periods=(Period(0, 12),)),
                Zone(key="t1", name="B", price=Decimal("1"), periods=(Period(12, 24),)),
            ),
        )
    with pytest.raises(TariffValidationError):
        TariffPlan(valid_from=date(2026, 1, 1), name="Empty", zones=())


def test_plan_volume_bands_reserved():
    plan = TariffPlan(
        valid_from=date(2026, 1, 1),
        name="Tiered",
        zones=(
            Zone(
                key="t1",
                name="Day",
                price=Decimal("10"),
                periods=(Period(7, 23),),
                band_prices=(Decimal("12"), Decimal("15")),
            ),
            Zone(
                key="t2",
                name="Night",
                price=Decimal("4"),
                periods=(Period(23, 7),),
                band_prices=(Decimal("5"), Decimal("6")),
            ),
        ),
        volume_band_limits_kwh=(Decimal("3900"), Decimal("6000")),
    )
    assert plan.zone_for_hour(12).price == Decimal("10")


@pytest.mark.parametrize(
    ("limits", "band_prices"),
    [
        ((Decimal("3900"), Decimal("6000")), (Decimal("1"),)),
        ((), (Decimal("1"), Decimal("2"))),
        ((Decimal("6000"), Decimal("3900")), (Decimal("1"), Decimal("2"))),
        ((Decimal("0"),), (Decimal("1"),)),
        ((Decimal("3900"),), (Decimal("-1"),)),
        ((Decimal("3900"), Decimal("3900")), (Decimal("1"), Decimal("2"))),
        ((Decimal("NaN"),), (Decimal("1"),)),
        ((Decimal("Infinity"),), (Decimal("1"),)),
        ((3900.0,), (Decimal("1"),)),
    ],
)
def test_plan_volume_bands_invalid(limits, band_prices):
    with pytest.raises(TariffValidationError):
        TariffPlan(
            valid_from=date(2026, 1, 1),
            name="Tiered",
            zones=(
                Zone(
                    key="t1",
                    name="Day",
                    price=Decimal("10"),
                    periods=(Period(0, 24),),
                    band_prices=band_prices,
                ),
            ),
            volume_band_limits_kwh=limits,
        )


def test_replace_revalidates():
    plan = _two_zone_plan()
    overlapping = (
        Zone(key="t1", name="Day", price=Decimal("1"), periods=(Period(7, 23),)),
        Zone(key="t2", name="Night", price=Decimal("1"), periods=(Period(22, 7),)),
    )
    with pytest.raises(TariffValidationError):
        dataclasses.replace(plan, zones=overlapping)

    new_plan = dataclasses.replace(plan, valid_from=date(2026, 7, 1))
    assert new_plan.valid_from == date(2026, 7, 1)
    assert plan.valid_from == date(2026, 1, 1)


def test_models_frozen():
    plan = _two_zone_plan()
    with pytest.raises(dataclasses.FrozenInstanceError):
        plan.name = "x"  # type: ignore[misc]


# --- TariffSchedule ---------------------------------------------------------------


def test_schedule_sorts_and_rejects_duplicates():
    plan_a = _two_zone_plan(date(2026, 7, 1))
    plan_b = _two_zone_plan(date(2026, 1, 1))
    schedule = TariffSchedule((plan_a, plan_b))
    assert [p.valid_from for p in schedule.plans] == [
        date(2026, 1, 1),
        date(2026, 7, 1),
    ]

    with pytest.raises(TariffValidationError):
        TariffSchedule((plan_a, _two_zone_plan(date(2026, 7, 1))))

    with pytest.raises(TariffValidationError):
        TariffSchedule(())


def test_schedule_plan_for():
    plan_a = _two_zone_plan(date(2026, 1, 1))
    plan_b = _two_zone_plan(date(2026, 7, 1))
    schedule = TariffSchedule((plan_a, plan_b))

    assert schedule.plan_for(date(2025, 12, 31)) is None
    assert schedule.plan_for(date(2026, 1, 1)) is plan_a
    assert schedule.plan_for(date(2026, 6, 30)) is plan_a
    assert schedule.plan_for(date(2026, 7, 1)) is plan_b
    assert schedule.plan_for(date(2030, 1, 1)) is plan_b


def test_schedule_price_only_change():
    plan_a = _two_zone_plan(date(2026, 1, 1))
    plan_b = dataclasses.replace(
        plan_a,
        valid_from=date(2026, 7, 1),
        zones=(
            dataclasses.replace(plan_a.zones[0], price=Decimal("11.00")),
            dataclasses.replace(plan_a.zones[1], price=Decimal("5.00")),
        ),
    )
    schedule = TariffSchedule((plan_a, plan_b))

    before = schedule.plan_for(date(2026, 6, 30))
    after = schedule.plan_for(date(2026, 7, 1))
    assert before is not None
    assert after is not None
    assert before.zone_for_hour(12).price == Decimal("10.30")
    assert after.zone_for_hour(12).price == Decimal("11.00")


def test_schedule_plans_between():
    plan_a = _two_zone_plan(date(2026, 1, 1))
    plan_b = _two_zone_plan(date(2026, 7, 1))
    schedule = TariffSchedule((plan_a, plan_b))

    assert schedule.plans_between(date(2026, 6, 15), date(2026, 7, 15)) == (
        plan_a,
        plan_b,
    )
    assert schedule.plans_between(date(2026, 7, 2), date(2026, 8, 1)) == (plan_b,)
    assert schedule.plans_between(date(2025, 6, 1), date(2025, 7, 1)) == ()
    assert schedule.plans_between(date(2026, 7, 1), date(2026, 7, 1)) == ()
    # end equals the next plan's valid_from: the range [start, end) is half-open,
    # so plan_b (valid_from == end) is not in effect on any date in the range.
    assert schedule.plans_between(date(2026, 6, 15), date(2026, 7, 1)) == (plan_a,)


def test_plan_hour_lookup_not_leaked():
    plan = _two_zone_plan()
    as_dict = dataclasses.asdict(plan)
    assert set(as_dict.keys()) == {
        "valid_from",
        "name",
        "zones",
        "volume_band_limits_kwh",
    }
    assert "_hour_lookup" not in repr(plan)

    # equality and hashing must not be affected by any internal lookup cache
    other = _two_zone_plan()
    assert plan == other
    assert hash(plan) == hash(other)

    # zone_for_hour still works after asdict()/repr()/hash() were called
    assert plan.zone_for_hour(12).key == "t1"
