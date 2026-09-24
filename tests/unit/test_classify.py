"""Unit tests for engine.classify (tasks/005-time-and-zones.md)."""

from collections import Counter
from datetime import UTC, date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from engine.classify import HourInfo, bucket_key, classify_hours
from engine.models import Grouping
from engine.presets import ru_two_zone, single_rate
from engine.tariff import TariffSchedule
from engine.timeutil import local_day_start

MSK = ZoneInfo("Europe/Moscow")
BER = ZoneInfo("Europe/Berlin")


def _zone_key(info: HourInfo) -> str:
    assert info.zone is not None
    return info.zone.key


def _two_zone_schedule(valid_from: date = date(2026, 1, 1)) -> TariffSchedule:
    plan = ru_two_zone(
        valid_from=valid_from,
        day_price=Decimal("10.30"),
        night_price=Decimal("4.43"),
    )
    return TariffSchedule((plan,))


# --- bucket_key -----------------------------------------------------------------


def _info(local_start: datetime) -> HourInfo:
    utc_start = local_start.astimezone(UTC)
    return HourInfo(utc_start=utc_start, local_start=local_start, plan=None, zone=None)


@pytest.mark.parametrize(
    ("local_dt", "grouping", "expected"),
    [
        (datetime(2026, 1, 15, 23, 0, tzinfo=MSK), Grouping.DAY, date(2026, 1, 15)),
        (datetime(2026, 1, 15, 12, 0, tzinfo=MSK), Grouping.WEEK, date(2026, 1, 12)),
        (datetime(2026, 1, 18, 23, 0, tzinfo=MSK), Grouping.WEEK, date(2026, 1, 12)),
        (datetime(2026, 1, 19, 0, 0, tzinfo=MSK), Grouping.WEEK, date(2026, 1, 19)),
        (datetime(2026, 1, 31, 23, 0, tzinfo=MSK), Grouping.MONTH, date(2026, 1, 1)),
    ],
)
def test_bucket_key(local_dt, grouping, expected):
    info = _info(local_dt)
    assert bucket_key(info, grouping) == expected


def test_bucket_key_hour_and_total():
    local_dt = datetime(2026, 1, 15, 23, 0, tzinfo=MSK)
    info = _info(local_dt)
    assert bucket_key(info, Grouping.HOUR) == info.utc_start
    assert bucket_key(info, Grouping.TOTAL) is None


# --- classify_hours: DST bucket counts -------------------------------------------


def test_bucket_hour_counts_dst_berlin():
    schedule = _two_zone_schedule(date(2025, 1, 1))
    start = local_day_start(date(2026, 3, 1), BER)
    end = local_day_start(date(2026, 5, 1), BER)
    infos = classify_hours(schedule, start, end, BER)

    month_counts = Counter(bucket_key(info, Grouping.MONTH) for info in infos)
    assert month_counts[date(2026, 3, 1)] == 743
    assert month_counts[date(2026, 4, 1)] == 720

    week_start = local_day_start(date(2026, 3, 23), BER)
    week_end = local_day_start(date(2026, 3, 30), BER)
    week_infos = classify_hours(schedule, week_start, week_end, BER)
    assert len(week_infos) == 167

    oct_start = local_day_start(date(2026, 10, 1), BER)
    oct_end = local_day_start(date(2026, 11, 1), BER)
    oct_infos = classify_hours(schedule, oct_start, oct_end, BER)
    oct_month_counts = Counter(bucket_key(info, Grouping.MONTH) for info in oct_infos)
    assert oct_month_counts[date(2026, 10, 1)] == 745

    oct_week_start = local_day_start(date(2026, 10, 19), BER)
    oct_week_end = local_day_start(date(2026, 10, 26), BER)
    oct_week_infos = classify_hours(schedule, oct_week_start, oct_week_end, BER)
    assert len(oct_week_infos) == 169


# --- classify_hours: zones -------------------------------------------------------


def test_two_zone_day_msk():
    schedule = _two_zone_schedule()
    start = local_day_start(date(2026, 1, 15), MSK)
    end = local_day_start(date(2026, 1, 16), MSK)
    infos = classify_hours(schedule, start, end, MSK)
    assert len(infos) == 24

    zone_counts = Counter(_zone_key(info) for info in infos)
    assert zone_counts["t1"] == 16
    assert zone_counts["t2"] == 8

    by_utc = {info.utc_start: info for info in infos}
    info_2000 = by_utc[datetime(2026, 1, 15, 20, 0, tzinfo=UTC)]
    assert info_2000.local_start.hour == 23
    assert info_2000.local_start.date() == date(2026, 1, 15)
    assert _zone_key(info_2000) == "t2"

    info_0300 = by_utc[datetime(2026, 1, 15, 3, 0, tzinfo=UTC)]
    assert info_0300.local_start.hour == 6
    assert _zone_key(info_0300) == "t2"

    info_0400 = by_utc[datetime(2026, 1, 15, 4, 0, tzinfo=UTC)]
    assert info_0400.local_start.hour == 7
    assert _zone_key(info_0400) == "t1"


def test_plan_switch_at_local_midnight_msk():
    plan_a = ru_two_zone(
        valid_from=date(2026, 1, 1),
        day_price=Decimal("10.30"),
        night_price=Decimal("4.43"),
        name="A",
    )
    plan_b = ru_two_zone(
        valid_from=date(2026, 7, 1),
        day_price=Decimal("11.00"),
        night_price=Decimal("5.00"),
        name="B",
    )
    schedule = TariffSchedule((plan_a, plan_b))

    start = datetime(2026, 6, 30, 20, 0, tzinfo=UTC)
    end = datetime(2026, 6, 30, 22, 0, tzinfo=UTC)
    infos = classify_hours(schedule, start, end, MSK)
    by_utc = {info.utc_start: info for info in infos}

    before = by_utc[datetime(2026, 6, 30, 20, 0, tzinfo=UTC)]
    assert before.local_start.hour == 23
    assert before.plan is plan_a

    after = by_utc[datetime(2026, 6, 30, 21, 0, tzinfo=UTC)]
    assert after.local_start.hour == 0
    assert after.local_start.date() == date(2026, 7, 1)
    assert after.plan is plan_b


def test_plan_switch_on_dst_day_berlin():
    plan_a = ru_two_zone(
        valid_from=date(2026, 1, 1),
        day_price=Decimal("10.30"),
        night_price=Decimal("4.43"),
        name="A",
    )
    plan_b = ru_two_zone(
        valid_from=date(2026, 10, 25),
        day_price=Decimal("11.00"),
        night_price=Decimal("5.00"),
        name="B",
    )
    schedule = TariffSchedule((plan_a, plan_b))

    start = datetime(2026, 10, 24, 21, 0, tzinfo=UTC)
    end = datetime(2026, 10, 24, 23, 0, tzinfo=UTC)
    infos = classify_hours(schedule, start, end, BER)
    by_utc = {info.utc_start: info for info in infos}

    before = by_utc[datetime(2026, 10, 24, 21, 0, tzinfo=UTC)]
    assert before.local_start.hour == 23
    assert before.plan is plan_a

    after = by_utc[datetime(2026, 10, 24, 22, 0, tzinfo=UTC)]
    assert after.local_start.hour == 0
    assert after.local_start.date() == date(2026, 10, 25)
    assert after.plan is plan_b


def test_dst_zone_counts_berlin():
    schedule = _two_zone_schedule(date(2025, 1, 1))

    start = local_day_start(date(2026, 3, 29), BER)
    end = local_day_start(date(2026, 3, 30), BER)
    infos = classify_hours(schedule, start, end, BER)
    zone_counts = Counter(_zone_key(info) for info in infos)
    assert zone_counts["t1"] == 16
    assert zone_counts["t2"] == 7

    start = local_day_start(date(2026, 10, 25), BER)
    end = local_day_start(date(2026, 10, 26), BER)
    infos = classify_hours(schedule, start, end, BER)
    zone_counts = Counter(_zone_key(info) for info in infos)
    assert zone_counts["t1"] == 16
    assert zone_counts["t2"] == 9

    start = local_day_start(date(2026, 1, 15), BER)
    end = local_day_start(date(2026, 1, 16), BER)
    infos = classify_hours(schedule, start, end, BER)
    zone_counts = Counter(_zone_key(info) for info in infos)
    assert zone_counts["t1"] == 16
    assert zone_counts["t2"] == 8


def test_before_first_plan_is_unclassified():
    schedule = _two_zone_schedule(date(2026, 1, 1))
    start = local_day_start(date(2025, 12, 31), MSK)
    end = local_day_start(date(2026, 1, 2), MSK)
    infos = classify_hours(schedule, start, end, MSK)

    dec31 = [info for info in infos if info.local_start.date() == date(2025, 12, 31)]
    assert dec31
    for info in dec31:
        assert info.plan is None
        assert info.zone is None

    first_local_hour = min(
        (info for info in infos if info.local_start.date() == date(2026, 1, 1)),
        key=lambda info: info.utc_start,
    )
    assert first_local_hour.plan is not None
    assert first_local_hour.zone is not None


def test_single_rate_then_two_zone():
    plan_a = single_rate(valid_from=date(2026, 1, 1), price=Decimal("7.50"))
    plan_b = ru_two_zone(
        valid_from=date(2026, 7, 1),
        day_price=Decimal("10.30"),
        night_price=Decimal("4.43"),
    )
    schedule = TariffSchedule((plan_a, plan_b))

    start = local_day_start(date(2026, 6, 30), MSK)
    end = local_day_start(date(2026, 7, 2), MSK)
    infos = classify_hours(schedule, start, end, MSK)

    jun30 = [info for info in infos if info.local_start.date() == date(2026, 6, 30)]
    assert len(jun30) == 24
    for info in jun30:
        assert _zone_key(info) == "t0"

    jul1 = [info for info in infos if info.local_start.date() == date(2026, 7, 1)]
    zone_counts = Counter(_zone_key(info) for info in jul1)
    assert zone_counts["t1"] == 16
    assert zone_counts["t2"] == 8


def test_classify_rejects_bad_window():
    schedule = _two_zone_schedule()
    with pytest.raises(ValueError):
        classify_hours(
            schedule,
            datetime(2026, 1, 15, 0, 0),
            datetime(2026, 1, 15, 3, 0, tzinfo=UTC),
            MSK,
        )
    with pytest.raises(ValueError):
        classify_hours(
            schedule,
            datetime(2026, 1, 15, 0, 30, tzinfo=UTC),
            datetime(2026, 1, 15, 3, 0, tzinfo=UTC),
            MSK,
        )
    with pytest.raises(ValueError):
        classify_hours(
            schedule,
            datetime(2026, 1, 15, 3, 0, tzinfo=UTC),
            datetime(2026, 1, 15, 3, 0, tzinfo=UTC),
            MSK,
        )
