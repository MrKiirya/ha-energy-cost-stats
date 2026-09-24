"""Unit tests for engine.timeutil (tasks/005-time-and-zones.md)."""

from datetime import UTC, date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from engine.timeutil import iter_hours, local_day_start, to_utc_hour

MSK = ZoneInfo("Europe/Moscow")
BER = ZoneInfo("Europe/Berlin")
KOLKATA = ZoneInfo("Asia/Kolkata")
SANTIAGO = ZoneInfo("America/Santiago")


# --- to_utc_hour --------------------------------------------------------------


def test_to_utc_hour_normalizes():
    value = datetime(2026, 1, 15, 23, 0, tzinfo=timezone(timedelta(hours=3)))
    result = to_utc_hour(value)
    assert result == datetime(2026, 1, 15, 20, 0, tzinfo=UTC)
    assert result.tzinfo is UTC


@pytest.mark.parametrize(
    "value",
    [
        datetime(2026, 1, 15, 20, 0),  # naive
        datetime(2026, 1, 15, 20, 30, tzinfo=UTC),
        datetime(2026, 1, 15, 20, 0, 1, tzinfo=UTC),
        datetime(2026, 1, 15, 20, 0, tzinfo=UTC) + timedelta(microseconds=1),
        # local midnight in Asia/Kolkata (+05:30) is 18:30 UTC, not on the hour
        datetime(2026, 1, 15, 0, 0, tzinfo=KOLKATA),
    ],
)
def test_to_utc_hour_rejects(value):
    with pytest.raises(ValueError):
        to_utc_hour(value)


# --- iter_hours -----------------------------------------------------------------


def test_iter_hours():
    start = datetime(2026, 1, 15, 0, 0, tzinfo=UTC)
    end = datetime(2026, 1, 15, 3, 0, tzinfo=UTC)
    assert list(iter_hours(start, end)) == [
        datetime(2026, 1, 15, 0, 0, tzinfo=UTC),
        datetime(2026, 1, 15, 1, 0, tzinfo=UTC),
        datetime(2026, 1, 15, 2, 0, tzinfo=UTC),
    ]
    assert list(iter_hours(start, start)) == []


# --- local_day_start -----------------------------------------------------------


def test_local_day_normal_msk():
    start = local_day_start(date(2026, 1, 15), MSK)
    assert start == datetime(2026, 1, 14, 21, 0, tzinfo=UTC)
    next_start = local_day_start(date(2026, 1, 16), MSK)
    assert (next_start - start) == timedelta(hours=24)


def test_local_day_spring_forward_berlin():
    day = date(2026, 3, 29)
    start = local_day_start(day, BER)
    next_start = local_day_start(date(2026, 3, 30), BER)
    assert start == datetime(2026, 3, 28, 23, 0, tzinfo=UTC)
    assert next_start == datetime(2026, 3, 29, 22, 0, tzinfo=UTC)
    hour_count = int((next_start - start) / timedelta(hours=1))
    assert hour_count == 23
    for hour in iter_hours(start, next_start):
        assert hour.astimezone(BER).hour != 2


def test_local_day_fall_back_berlin():
    day = date(2026, 10, 25)
    start = local_day_start(day, BER)
    next_start = local_day_start(date(2026, 10, 26), BER)
    assert start == datetime(2026, 10, 24, 22, 0, tzinfo=UTC)
    assert next_start == datetime(2026, 10, 25, 23, 0, tzinfo=UTC)
    hour_count = int((next_start - start) / timedelta(hours=1))
    assert hour_count == 25

    local_hours_2 = [
        hour for hour in iter_hours(start, next_start) if hour.astimezone(BER).hour == 2
    ]
    assert len(local_hours_2) == 2
    offsets = [hour.astimezone(BER).utcoffset() for hour in local_hours_2]
    assert offsets == [timedelta(hours=2), timedelta(hours=1)]


@pytest.mark.parametrize("tz", [BER, MSK, SANTIAGO, KOLKATA])
def test_local_day_start_property(tz):
    day = date(2026, 1, 1)
    one_day = timedelta(days=1)
    for _ in range(365):
        start = local_day_start(day, tz)
        assert start.astimezone(tz).date() == day
        before = start - timedelta(hours=1)
        assert before.astimezone(tz).date() != day
        day = day + one_day
