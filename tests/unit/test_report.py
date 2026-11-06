"""Unit tests for engine.report (tasks/006-pricing-and-grouping.md)."""

from collections.abc import Callable, Iterable
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, localcontext
from itertools import pairwise
from zoneinfo import ZoneInfo

import pytest

from engine.classify import classify_hours
from engine.models import (
    Bucket,
    Coverage,
    DataStatus,
    DeviceSeries,
    Grouping,
    IssueKind,
    QualityIssue,
    Report,
    ReportRequest,
    Row,
    ZoneLabel,
)
from engine.presets import ru_three_zone, ru_two_zone, single_rate
from engine.report import (
    HourKind,
    HourValue,
    PreparedSeries,
    assemble_report,
    build_report,
    prepare_measured,
)
from engine.rounding import round_money
from engine.serialize import DeviceInfo, report_to_json
from engine.tariff import TariffPlan, TariffSchedule
from engine.timeutil import iter_hours, local_day_start

MSK = ZoneInfo("Europe/Moscow")
BER = ZoneInfo("Europe/Berlin")

P1 = "sensor.plug_01"
P2 = "sensor.plug_02"
P3 = "sensor.plug_03"

D = Decimal
ONE = D("1")


def default_plan(valid_from: date = date(2026, 1, 1)) -> TariffPlan:
    return ru_two_zone(
        valid_from=valid_from, day_price=D("10.30"), night_price=D("4.43")
    )


def default_schedule() -> TariffSchedule:
    return TariffSchedule((default_plan(),))


def window(first_day: date, end_day: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    return local_day_start(first_day, tz), local_day_start(end_day, tz)


def request(
    first_day: date,
    end_day: date,
    tz: ZoneInfo = MSK,
    grouping: Grouping | str = Grouping.DAY,
) -> ReportRequest:
    start, end = window(first_day, end_day, tz)
    return ReportRequest(start=start, end=end, time_zone=tz, grouping=grouping)


def series(
    device_id: str,
    req: ReportRequest,
    value: Decimal | Callable[[int], Decimal | None] = ONE,
    *,
    skip: Iterable[int] = (),
) -> DeviceSeries:
    skipped = set(skip)
    deltas: dict[datetime, Decimal] = {}
    for index, hour in enumerate(iter_hours(req.start, req.end)):
        if index in skipped:
            continue
        item = value(index) if callable(value) else value
        if item is not None:
            deltas[hour] = item
    return DeviceSeries(device_id, deltas)


def msk_day() -> ReportRequest:
    return request(date(2026, 1, 15), date(2026, 1, 16))


def cells(row: Row) -> dict[str, tuple[Decimal | None, Decimal | None, Decimal | None]]:
    return {c.key: (c.kwh, c.cost, c.price) for c in row.zones}


# --- basics ---------------------------------------------------------------------


def test_single_device_two_zone_day_msk():
    req = msk_day()
    report = build_report(req, default_schedule(), [series(P1, req)])

    assert len(report.buckets) == 1
    bucket = report.buckets[0]
    assert bucket.hours == 24
    assert bucket.start == datetime(2026, 1, 15, 0, tzinfo=MSK)
    assert bucket.end == datetime(2026, 1, 16, 0, tzinfo=MSK)
    assert report.zones == (ZoneLabel("t1", "Day"), ZoneLabel("t2", "Night"))

    row = bucket.rows[0]
    assert row.device_id == P1
    assert cells(row) == {
        "t1": (D("16"), D("164.80"), D("10.30")),
        "t2": (D("8"), D("35.44"), D("4.43")),
    }
    assert row.kwh == 24
    assert row.cost == D("200.24")
    assert row.unpriced_kwh == 0
    assert row.coverage == Coverage(24, 24, 0, 0, 0)
    assert row.status is DataStatus.COMPLETE
    assert report.totals == bucket
    assert report.unpriced_hours == 0
    assert report.issues == ()


def test_total_row_sums_devices_in_input_order():
    req = msk_day()
    report = build_report(
        req,
        default_schedule(),
        [series(P2, req, D("0.5")), series(P1, req, ONE)],
    )
    rows = report.buckets[0].rows
    assert rows[0].device_id == P2
    assert cells(rows[0]) == {
        "t1": (D("8"), D("82.40"), D("10.30")),
        "t2": (D("4"), D("17.72"), D("4.43")),
    }
    assert rows[0].kwh == 12
    assert rows[0].cost == D("100.12")

    total = report.buckets[0].total
    assert total.device_id is None
    assert cells(total) == {
        "t1": (D("24"), D("247.20"), D("10.30")),
        "t2": (D("12"), D("53.16"), D("4.43")),
    }
    assert total.kwh == 36
    assert total.cost == D("300.36")
    assert total.coverage == Coverage(48, 48, 0, 0, 0)


def test_missing_hours_are_not_zero():
    req = msk_day()
    report = build_report(req, default_schedule(), [series(P1, req, skip=range(0, 4))])
    row = report.buckets[0].rows[0]
    assert row.coverage == Coverage(24, 20, 0, 0, 4)
    assert row.status is DataStatus.PARTIAL
    assert row.kwh == 20
    assert cells(row)["t2"] == (D("4"), D("17.72"), D("4.43"))


def test_device_without_data_is_none_not_zero():
    req = msk_day()
    report = build_report(
        req,
        default_schedule(),
        [DeviceSeries(P1, {}), series(P2, req, D("0"))],
    )
    empty, zero = report.buckets[0].rows
    assert empty.kwh is None
    assert empty.cost is None
    for cell in empty.zones:
        assert cell.kwh is None
        assert cell.cost is None
    assert [c.price for c in empty.zones] == [D("10.30"), D("4.43")]
    assert empty.coverage == Coverage(24, 0, 0, 0, 24)
    assert empty.status is DataStatus.MISSING

    assert zero.kwh == 0
    assert zero.kwh is not None
    assert zero.cost == 0
    assert zero.cost is not None
    assert zero.status is DataStatus.COMPLETE

    total = report.buckets[0].total
    assert total.kwh == 0
    assert total.kwh is not None
    assert total.coverage == Coverage(48, 24, 0, 0, 24)
    assert total.status is DataStatus.PARTIAL


def test_zone_without_counted_hours_is_none():
    req = msk_day()
    # Local day hours 07..22 are indexes 7..22.
    report = build_report(
        req,
        default_schedule(),
        [series(P1, req, skip=[*range(0, 7), 23])],
    )
    row = report.buckets[0].rows[0]
    night = row.zones[1]
    assert night.kwh is None
    assert night.cost is None
    assert night.price == D("4.43")
    assert row.cost == D("164.80")
    assert row.status is DataStatus.PARTIAL


# --- unpriced hours -------------------------------------------------------------


def test_unpriced_hours_before_first_plan():
    req = request(date(2025, 12, 31), date(2026, 1, 2))
    schedule = default_schedule()
    report = build_report(req, schedule, [series(P1, req)])
    assert report.unpriced_hours == 24
    assert report.plans == schedule.plans

    dec31, jan1 = report.buckets
    row = dec31.rows[0]
    assert row.kwh == 24
    assert row.unpriced_kwh == 24
    assert row.cost is None
    for cell in row.zones:
        assert cell.kwh is None
        assert cell.cost is None
        assert cell.price is None
    assert row.coverage == Coverage(24, 24, 0, 0, 0)

    assert jan1.rows[0].cost == D("200.24")
    total = report.totals.total
    assert total.kwh == 48
    assert total.unpriced_kwh == 24
    assert total.cost == D("200.24")


def test_window_entirely_before_first_plan():
    req = request(date(2025, 12, 31), date(2026, 1, 1))
    report = build_report(req, default_schedule(), [series(P1, req)])
    assert report.zones == ()
    assert report.plans == ()
    assert report.unpriced_hours == 24
    for row in (report.buckets[0].rows[0], report.totals.total):
        assert row.zones == ()
        assert row.cost is None
        assert row.kwh == 24
        assert row.unpriced_kwh == 24


# --- zone union -----------------------------------------------------------------


def test_single_rate_then_two_zone_union():
    schedule = TariffSchedule(
        (
            single_rate(valid_from=date(2026, 1, 1), price=D("7.00")),
            default_plan(date(2026, 7, 1)),
        )
    )
    req = request(date(2026, 6, 30), date(2026, 7, 2))
    report = build_report(req, schedule, [series(P1, req)])
    assert [z.key for z in report.zones] == ["t0", "t1", "t2"]
    assert len(report.plans) == 2
    assert report.plans == schedule.plans

    jun30, jul1 = report.buckets
    assert cells(jun30.rows[0]) == {
        "t0": (D("24"), D("168.00"), D("7.00")),
        "t1": (None, None, None),
        "t2": (None, None, None),
    }
    assert cells(jul1.rows[0]) == {
        "t0": (None, None, None),
        "t1": (D("16"), D("164.80"), D("10.30")),
        "t2": (D("8"), D("35.44"), D("4.43")),
    }
    total = report.totals.total
    assert total.kwh == 48
    assert total.cost == D("368.24")
    assert [c.price for c in total.zones] == [D("7.00"), D("10.30"), D("4.43")]


def test_zone_union_order_and_window_scope():
    schedule = TariffSchedule(
        (
            single_rate(valid_from=date(2026, 1, 1), price=D("7.00")),
            ru_three_zone(
                valid_from=date(2026, 2, 1),
                peak_price=D("12"),
                semi_peak_price=D("9"),
                night_price=D("5"),
            ),
            default_plan(date(2026, 3, 1)),
        )
    )
    req = request(date(2026, 1, 31), date(2026, 3, 2), grouping=Grouping.TOTAL)
    report = build_report(req, schedule, [series(P1, req)])
    assert [z.key for z in report.zones] == ["t0", "t1", "t2", "t3"]
    assert len(report.plans) == 3
    # The latest plan containing the key wins the name.
    assert dict((z.key, z.name) for z in report.zones)["t1"] == "Day"

    req = request(date(2026, 2, 5), date(2026, 2, 10), grouping=Grouping.TOTAL)
    report = build_report(req, schedule, [series(P1, req)])
    assert [z.key for z in report.zones] == ["t1", "t2", "t3"]
    assert len(report.plans) == 1


# --- prices inside a bucket -----------------------------------------------------


def _price_change_schedule(day_price: str, night_price: str, renamed: bool = False):
    plan_b = ru_two_zone(
        valid_from=date(2026, 1, 15),
        day_price=D(day_price),
        night_price=D(night_price),
    )
    if renamed:
        plan_b = replace(
            plan_b,
            zones=tuple(
                replace(z, name="Peak day") if z.key == "t1" else z
                for z in plan_b.zones
            ),
        )
    return TariffSchedule((default_plan(), plan_b))


def test_price_none_on_mid_bucket_price_change():
    schedule = _price_change_schedule("11.00", "4.80")
    req = request(date(2026, 1, 12), date(2026, 1, 19), grouping=Grouping.WEEK)
    report = build_report(req, schedule, [series(P1, req)])
    assert len(report.buckets) == 1
    assert report.buckets[0].hours == 168
    t1, t2 = report.buckets[0].rows[0].zones
    assert t1.price is None
    assert t1.kwh == 112
    assert t1.cost == D("1198.40")
    assert t1.effective_price == D("10.7")
    assert t2.price is None
    assert t2.kwh == 56
    assert t2.cost == D("259.92")

    req_day = request(date(2026, 1, 12), date(2026, 1, 19), grouping=Grouping.DAY)
    report = build_report(req_day, schedule, [series(P1, req_day)])
    by_start = {b.start.date(): b for b in report.buckets}
    assert by_start[date(2026, 1, 14)].rows[0].zones[0].price == D("10.30")
    assert by_start[date(2026, 1, 15)].rows[0].zones[0].price == D("11.00")
    assert all(c.price is not None for b in report.buckets for c in b.total.zones)


def test_same_price_switch_keeps_price_and_latest_name():
    schedule = _price_change_schedule("10.3", "4.430", renamed=True)
    req = request(date(2026, 1, 12), date(2026, 1, 19), grouping=Grouping.WEEK)
    report = build_report(req, schedule, [series(P1, req)])
    t1, t2 = report.buckets[0].rows[0].zones
    assert t1.price == D("10.30")
    assert t2.price == D("4.43")
    assert report.zones[0] == ZoneLabel("t1", "Peak day")


# --- grouping -------------------------------------------------------------------


def test_hour_grouping():
    start = datetime(2026, 1, 15, 3, tzinfo=UTC)
    end = datetime(2026, 1, 15, 6, tzinfo=UTC)
    req = ReportRequest(start=start, end=end, time_zone=MSK, grouping=Grouping.HOUR)
    report = build_report(req, default_schedule(), [series(P1, req)])
    assert len(report.buckets) == 3
    assert all(b.hours == 1 for b in report.buckets)
    first, second, _ = report.buckets
    assert first.start == datetime(2026, 1, 15, 6, tzinfo=MSK)
    t1, t2 = first.rows[0].zones
    assert t1.kwh is None
    assert t1.price is None
    assert t2.kwh == 1
    assert t2.price == D("4.43")
    assert second.rows[0].zones[0].price == D("10.30")
    assert second.rows[0].zones[0].kwh == 1


def test_dst_buckets_spring_berlin():
    schedule = default_schedule()
    kwargs = (date(2026, 3, 1), date(2026, 4, 1), BER)

    req = request(*kwargs, grouping=Grouping.MONTH)
    report = build_report(req, schedule, [series(P1, req)])
    assert len(report.buckets) == 1
    assert report.buckets[0].hours == 743
    assert report.buckets[0].total.kwh == 743

    req = request(*kwargs, grouping=Grouping.DAY)
    report = build_report(req, schedule, [series(P1, req)])
    assert len(report.buckets) == 31
    mar29 = report.buckets[28]
    assert mar29.hours == 23
    assert mar29.start == datetime(2026, 3, 29, 0, tzinfo=BER)
    assert mar29.start.utcoffset() == timedelta(hours=1)
    assert mar29.end == datetime(2026, 3, 30, 0, tzinfo=BER)
    assert mar29.end.utcoffset() == timedelta(hours=2)
    assert cells(mar29.rows[0])["t1"][0] == 16
    assert cells(mar29.rows[0])["t2"][0] == 7

    req = request(*kwargs, grouping=Grouping.WEEK)
    report = build_report(req, schedule, [series(P1, req)])
    assert [b.hours for b in report.buckets] == [24, 168, 168, 168, 167, 48]


def test_dst_buckets_fall_berlin():
    schedule = default_schedule()
    kwargs = (date(2026, 10, 1), date(2026, 11, 1), BER)

    req = request(*kwargs, grouping=Grouping.MONTH)
    report = build_report(req, schedule, [series(P1, req)])
    assert report.buckets[0].hours == 745

    req = request(*kwargs, grouping=Grouping.DAY)
    report = build_report(req, schedule, [series(P1, req)])
    oct25 = report.buckets[24]
    assert oct25.hours == 25
    assert oct25.start == datetime(2026, 10, 25, 0, tzinfo=BER)
    assert oct25.start.utcoffset() == timedelta(hours=2)
    assert oct25.end == datetime(2026, 10, 26, 0, tzinfo=BER)
    assert oct25.end.utcoffset() == timedelta(hours=1)
    assert cells(oct25.rows[0])["t1"][0] == 16
    assert cells(oct25.rows[0])["t2"][0] == 9

    req = request(*kwargs, grouping=Grouping.WEEK)
    report = build_report(req, schedule, [series(P1, req)])
    week = next(b for b in report.buckets if b.start.date() == date(2026, 10, 19))
    assert week.hours == 169


def test_total_grouping_single_bucket():
    req = request(date(2026, 1, 15), date(2026, 1, 17), grouping=Grouping.TOTAL)
    report = build_report(req, default_schedule(), [series(P1, req)])
    assert report.buckets == (report.totals,)
    assert report.totals.hours == 48


def test_grouping_accepts_string():
    by_string = request(date(2026, 1, 15), date(2026, 1, 18), grouping="day")
    by_enum = request(date(2026, 1, 15), date(2026, 1, 18), grouping=Grouping.DAY)
    first = build_report(by_string, default_schedule(), [series(P1, by_string)])
    second = build_report(by_enum, default_schedule(), [series(P1, by_enum)])
    assert first.buckets == second.buckets
    assert len(first.buckets) == 3


def _sum(values: Iterable[Decimal | None]) -> Decimal:
    # Same precision as the engine, so the comparison is exact.
    with localcontext(prec=50):
        return sum((v for v in values if v is not None), D("0"))


def _all_sums(bucket_rows: list[Row]) -> tuple[object, ...]:
    keys = [c.key for c in bucket_rows[0].zones]
    return (
        _sum(r.kwh for r in bucket_rows),
        _sum(r.cost for r in bucket_rows),
        _sum(r.unpriced_kwh for r in bucket_rows),
        _sum(r.estimated_kwh for r in bucket_rows),
        _sum(r.excluded_kwh for r in bucket_rows),
        tuple(
            (
                _sum(r.zones[i].kwh for r in bucket_rows),
                _sum(r.zones[i].cost for r in bucket_rows),
            )
            for i in range(len(keys))
        ),
    )


@pytest.mark.parametrize("grouping", list(Grouping))
def test_bucket_invariants_across_groupings(grouping: Grouping):
    schedule = TariffSchedule(
        (
            default_plan(),
            ru_two_zone(
                valid_from=date(2026, 4, 1),
                day_price=D("11.10"),
                night_price=D("4.70"),
            ),
        )
    )
    req = request(date(2026, 3, 20), date(2026, 5, 4), BER, grouping)
    devices = [
        series(P1, req, lambda i: D(i % 7) / 10, skip=[3, 100, 101, 500, 1000]),
        series(P2, req, lambda i: D(i % 11) / 7, skip=range(200, 230)),
    ]
    report = build_report(req, schedule, devices)

    buckets = report.buckets
    assert buckets[0].start == req.start
    assert buckets[-1].end == req.end
    for left, right in pairwise(buckets):
        assert left.end == right.start
    assert sum(b.hours for b in buckets) == report.totals.hours

    totals = report.totals
    assert sum((b.total.coverage for b in buckets), Coverage.empty()) == (
        totals.total.coverage
    )
    assert _all_sums([b.total for b in buckets]) == _all_sums([totals.total])
    for idx in range(len(devices)):
        assert _all_sums([b.rows[idx] for b in buckets]) == _all_sums(
            [totals.rows[idx]]
        )

    keys = [z.key for z in report.zones]
    for bucket in (*buckets, totals):
        for row in (*bucket.rows, bucket.total):
            assert [c.key for c in row.zones] == keys
    assert totals.total.coverage.expected == totals.hours * 2


# --- inputs and exactness -------------------------------------------------------


def test_lookback_keys_ignored():
    req = msk_day()
    base = series(P1, req)
    extra = dict(base.deltas)
    extra[req.start - timedelta(hours=48)] = D("999999")
    extra[req.start - timedelta(hours=1)] = D("999999")
    extra[req.end] = D("999999")
    extra[req.end + timedelta(hours=5)] = D("999999")
    report = build_report(req, default_schedule(), [DeviceSeries(P1, extra)])
    assert report == build_report(req, default_schedule(), [base])


def test_exact_sums_independent_of_caller_context():
    req = msk_day()
    value = D("0.12345678901234567890123456789012345")
    devices = [series(P1, req, value)]
    with localcontext(prec=60):
        expected = sum((value for _ in range(24)), D("0"))
    report = build_report(req, default_schedule(), devices)
    assert report.totals.total.kwh == expected
    with localcontext(prec=5):
        in_small_context = build_report(req, default_schedule(), devices)
    assert in_small_context == report


def test_totals_are_exact_not_sums_of_rounded_cells():
    req = msk_day()
    # Local hour 10 is a day hour.
    devices = [
        DeviceSeries(
            device_id,
            {req.start + timedelta(hours=10): D("0.0005")},
        )
        for device_id in (P1, P2, P3)
    ]
    report = build_report(req, default_schedule(), devices)
    bucket = report.buckets[0]
    for row in bucket.rows:
        assert row.cost == D("0.005150")
    total_cost = bucket.total.cost
    assert total_cost is not None
    assert total_cost == D("0.015450")
    assert round_money(total_cost) == D("0.02")
    row_costs = [r.cost for r in bucket.rows if r.cost is not None]
    assert len(row_costs) == len(bucket.rows)
    assert sum(round_money(c) for c in row_costs) == D("0.03")


def test_empty_devices():
    req = request(date(2026, 1, 15), date(2026, 1, 17))
    report = build_report(req, default_schedule(), [])
    for bucket in report.buckets:
        assert bucket.rows == ()
        assert bucket.total.kwh is None
        assert bucket.total.cost is None
        assert bucket.total.coverage == Coverage.empty()
        assert bucket.total.status is DataStatus.MISSING
        assert [c.kwh for c in bucket.total.zones] == [None, None]
        assert [c.price for c in bucket.total.zones] == [D("10.30"), D("4.43")]


def test_duplicate_device_id_rejected():
    req = msk_day()
    devices = [series(P1, req), series(P1, req)]
    with pytest.raises(ValueError):
        build_report(req, default_schedule(), devices)
    hours = classify_hours(default_schedule(), req.start, req.end, req.time_zone)
    prepared = [prepare_measured(d, hours) for d in devices]
    with pytest.raises(ValueError):
        assemble_report(req, hours, prepared)


def test_prepare_measured():
    req = msk_day()
    hours = classify_hours(default_schedule(), req.start, req.end, req.time_zone)
    deltas = {
        req.start: D("1.5"),
        req.start + timedelta(hours=2): D("0"),
        req.start - timedelta(hours=1): D("9"),
        req.end: D("9"),
    }
    prepared = prepare_measured(DeviceSeries(P1, deltas), hours)
    assert prepared.device_id == P1
    assert len(prepared.values) == len(hours) == 24
    assert prepared.values[0] == HourValue(D("1.5"), HourKind.MEASURED)
    assert prepared.values[2] == HourValue(D("0"), HourKind.MEASURED)
    assert prepared.values[1] is None
    assert sum(v is not None for v in prepared.values) == 2


def test_assemble_estimated_and_excluded():
    req = msk_day()
    hours = classify_hours(default_schedule(), req.start, req.end, req.time_zone)
    values: list[HourValue | None] = [HourValue(ONE, HourKind.MEASURED)] * 24
    for i in (7, 8):
        values[i] = HourValue(D("1.5"), HourKind.ESTIMATED)
    for i in (0, 1):
        values[i] = HourValue(D("50"), HourKind.EXCLUDED)
    only_excluded = PreparedSeries(P2, (HourValue(D("2"), HourKind.EXCLUDED),) * 24)
    issue = QualityIssue(
        kind=IssueKind.EXCLUDED_SPIKE,
        device_id=P1,
        start=req.start,
        end=req.start + timedelta(hours=1),
        kwh=D("50"),
    )
    report = assemble_report(
        req,
        hours,
        [PreparedSeries(P1, tuple(values)), only_excluded],
        issues=(issue,),
    )
    row, excluded_row = report.buckets[0].rows
    assert row.kwh == 23
    assert row.cost == D("201.68")
    assert row.estimated_kwh == 3
    assert row.excluded_kwh == 100
    assert row.zones[0].kwh == 17
    assert row.zones[1].kwh == 6
    assert row.coverage == Coverage(24, 20, 2, 2, 0)
    assert row.status is DataStatus.PARTIAL

    assert excluded_row.kwh is None
    assert excluded_row.cost is None
    assert all(c.kwh is None and c.cost is None for c in excluded_row.zones)
    assert excluded_row.excluded_kwh == 48
    assert excluded_row.status is DataStatus.MISSING
    assert report.issues == (issue,)


def test_assemble_rejects_bad_input():
    req = msk_day()
    hours = classify_hours(default_schedule(), req.start, req.end, req.time_zone)
    short = PreparedSeries(P1, (HourValue(ONE, HourKind.MEASURED),) * 23)
    with pytest.raises(ValueError):
        assemble_report(req, hours, [short])
    with pytest.raises(ValueError):
        assemble_report(req, (), [PreparedSeries(P1, ())])


def test_report_is_report_type():
    req = msk_day()
    report = build_report(req, default_schedule(), [series(P1, req)])
    assert isinstance(report, Report)
    assert isinstance(report.totals, Bucket)


def test_build_report_without_schedule():
    req = request(date(2026, 1, 15), date(2026, 1, 16))
    hours = list(iter_hours(req.start, req.end))
    clean = DeviceSeries(P1, {h: ONE for h in hours})
    report = build_report(req, None, [clean])
    assert report.zones == ()
    assert report.plans == ()
    assert report.unpriced_hours == 24
    row = report.totals.rows[0]
    assert row.kwh == 24
    assert row.cost is None
    assert row.unpriced_kwh == 24
    assert row.zones == ()
    assert report.totals.total.cost is None

    gapped = DeviceSeries(
        P1,
        {
            h: (D("5") if i == 4 else ONE)
            for i, h in enumerate(hours)
            if i not in (1, 2, 3)
        },
    )
    spread = build_report(req, None, [gapped])
    assert [i.kind for i in spread.issues] == [IssueKind.ESTIMATED]
    assert spread.totals.rows[0].coverage.estimated == 4

    doc = report_to_json(
        report,
        devices=[DeviceInfo(P1, "Plug 01", "ok")],
        time_zone="Europe/Moscow",
        currency=None,
    )
    row_doc = doc["totals"]["rows"][0]
    assert doc["zones"] == []
    assert doc["plans"] == []
    assert row_doc["cost"] is None
    assert row_doc["unpriced_kwh"] == "24.000"
    assert row_doc["zones"] == []
