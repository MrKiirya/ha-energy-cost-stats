"""Unit tests for engine.quality (tasks/007-data-quality.md)."""

import time
from collections.abc import Callable, Mapping
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_DOWN, Decimal
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from engine.classify import classify_hours
from engine.models import (
    Coverage,
    DataStatus,
    DeviceSeries,
    Grouping,
    IssueKind,
    QualityIssue,
    Report,
    ReportRequest,
    Row,
)
from engine.presets import ru_two_zone
from engine.quality import (
    DEFAULT_SPIKE_LIMIT,
    SPREAD_QUANTUM,
    QualitySettings,
    prepare_series,
)
from engine.report import (
    HourKind,
    HourValue,
    PreparedSeries,
    assemble_report,
    build_report,
    prepare_measured,
)
from engine.tariff import TariffSchedule
from engine.timeutil import iter_hours, local_day_start

MSK = ZoneInfo("Europe/Moscow")
BER = ZoneInfo("Europe/Berlin")

P1 = "sensor.plug_01"
P2 = "sensor.plug_02"

D = Decimal
ONE = D("1")
HOUR = timedelta(hours=1)


def default_schedule() -> TariffSchedule:
    return TariffSchedule(
        (
            ru_two_zone(
                valid_from=date(2026, 1, 1),
                day_price=D("10.30"),
                night_price=D("4.43"),
            ),
        )
    )


def request(
    first_day: date,
    end_day: date,
    tz: ZoneInfo = MSK,
    grouping: Grouping | str = Grouping.DAY,
) -> ReportRequest:
    return ReportRequest(
        start=local_day_start(first_day, tz),
        end=local_day_start(end_day, tz),
        time_zone=tz,
        grouping=grouping,
    )


def msk_day() -> ReportRequest:
    return request(date(2026, 1, 15), date(2026, 1, 16))


def series(
    device_id: str,
    req: ReportRequest,
    overrides: Mapping[int, Decimal | None] | None = None,
    *,
    default: Decimal = ONE,
) -> DeviceSeries:
    """1 kWh/h (``default``) in every window hour; ``overrides`` by window index
    (``None`` removes the key)."""
    over = overrides or {}
    deltas: dict[datetime, Decimal] = {}
    for index, hour in enumerate(iter_hours(req.start, req.end)):
        value = over.get(index, default)
        if value is not None:
            deltas[hour] = value
    return DeviceSeries(device_id, deltas)


def with_keys(base: DeviceSeries, extra: Mapping[datetime, Decimal]) -> DeviceSeries:
    return DeviceSeries(base.device_id, {**base.deltas, **extra})


def gap(first: int, last: int) -> dict[int, Decimal | None]:
    return {i: None for i in range(first, last + 1)}


def prep(
    req: ReportRequest,
    ser: DeviceSeries,
    settings: QualitySettings | None = None,
) -> tuple[PreparedSeries, tuple[QualityIssue, ...]]:
    hours = classify_hours(default_schedule(), req.start, req.end, req.time_zone)
    return prepare_series(
        ser,
        hours,
        time_zone=req.time_zone,
        settings=settings or QualitySettings(),
    )


def run(
    req: ReportRequest,
    devices: list[DeviceSeries],
    quality: QualitySettings | None = None,
) -> Report:
    return build_report(req, default_schedule(), devices, quality=quality)


def msk_at(hour: int, day: int = 15) -> datetime:
    return datetime(2026, 1, day, hour, tzinfo=MSK)


def msk_issue(
    kind: IssueKind, first: int, end: int, kwh: Decimal, device: str = P1
) -> QualityIssue:
    return QualityIssue(kind, device, msk_at(first), msk_at(end), kwh)


# --- spreading -------------------------------------------------------------------


def test_gap_spread_across_zones():
    req = msk_day()
    report = run(req, [series(P1, req, {**gap(5, 8), 9: D("10")})])

    row = report.totals.rows[0]
    assert row.kwh == 29
    assert row.estimated_kwh == 10
    assert row.coverage == Coverage(24, 19, 5, 0, 0)
    assert row.status is DataStatus.ESTIMATED
    cells = {c.key: c for c in row.zones}
    assert (cells["t1"].kwh, cells["t1"].cost) == (19, D("195.70"))
    assert (cells["t2"].kwh, cells["t2"].cost) == (10, D("44.30"))
    assert row.cost == D("240.00")
    assert report.issues == (
        QualityIssue(
            IssueKind.ESTIMATED,
            P1,
            datetime(2026, 1, 15, 5, tzinfo=MSK),
            datetime(2026, 1, 15, 10, tzinfo=MSK),
            D("10"),
        ),
    )


def test_spread_remainder_is_exact():
    req = msk_day()
    prepared, _ = prep(req, series(P1, req, {**gap(11, 12), 13: ONE}))
    values = list(prepared.values[11:14])
    assert [v.kwh if v else None for v in values] == [
        D("0.33333333333333333333"),
        D("0.33333333333333333333"),
        D("0.33333333333333333334"),
    ]
    assert sum((v.kwh for v in values if v), D(0)) == 1
    assert all(v and v.kind is HourKind.ESTIMATED for v in values)

    prepared, _ = prep(req, series(P1, req, {**gap(11, 16), 17: D("0.1")}))
    seven = [v for v in prepared.values[11:18] if v is not None]
    assert len(seven) == 7
    assert sum((v.kwh for v in seven), D(0)) == D("0.1")
    q, r = seven[0].kwh, seven[-1].kwh
    assert all(v.kwh == q for v in seven[:-1])
    assert 0 <= r - q < 7 * SPREAD_QUANTUM


# --- spike / negative ------------------------------------------------------------


@pytest.mark.parametrize("delta", [D("36"), D("40")])
def test_spike_limit_passes_after_spreading(delta: Decimal):
    req = msk_day()
    report = run(req, [series(P1, req, {**gap(10, 18), 19: delta})])
    row = report.totals.rows[0]
    assert row.coverage == Coverage(24, 14, 10, 0, 0)
    assert row.estimated_kwh == delta
    assert [i.kind for i in report.issues] == [IssueKind.ESTIMATED]


def test_spike_limit_applies_after_spreading():
    req = msk_day()
    delta = D("40.0001")
    report = run(req, [series(P1, req, {**gap(10, 18), 19: delta})])
    prepared, _ = prep(req, series(P1, req, {**gap(10, 18), 19: delta}))
    assert prepared.values[19] == HourValue(delta, HourKind.EXCLUDED)
    assert all(v is None for v in prepared.values[10:19])

    row = report.totals.rows[0]
    assert row.coverage == Coverage(24, 14, 0, 1, 9)
    assert row.status is DataStatus.PARTIAL
    assert row.kwh == 14
    assert row.excluded_kwh == delta
    assert report.issues == (msk_issue(IssueKind.EXCLUDED_SPIKE, 19, 20, delta),)


def test_contiguous_spike_excluded():
    req = msk_day()
    report = run(req, [series(P1, req, {12: D("4.5")})])
    row = report.totals.rows[0]
    assert row.coverage.excluded == 1
    assert row.kwh == 23
    assert [i.kind for i in report.issues] == [IssueKind.EXCLUDED_SPIKE]

    ok = run(req, [series(P1, req, {12: D("4")})])
    assert ok.issues == ()
    assert ok.totals.rows[0].coverage == Coverage(24, 24, 0, 0, 0)


def test_negative_delta_excluded():
    req = msk_day()
    report = run(req, [series(P1, req, {12: D("-0.05")})])
    row = report.totals.rows[0]
    assert report.issues == (
        msk_issue(IssueKind.EXCLUDED_NEGATIVE, 12, 13, D("-0.05")),
    )
    assert row.excluded_kwh == D("-0.05")
    assert row.kwh == 23

    off = run(
        req, [series(P1, req, {12: D("-0.05")})], QualitySettings(spike_limit=None)
    )
    assert [i.kind for i in off.issues] == [IssueKind.EXCLUDED_NEGATIVE]


def test_negative_catch_up_after_gap():
    req = msk_day()
    ser = series(P1, req, {**gap(10, 12), 13: D("-1")})
    prepared, _ = prep(req, ser)
    assert prepared.values[13] == HourValue(D("-1"), HourKind.EXCLUDED)
    assert all(v is None for v in prepared.values[10:13])
    assert run(req, [ser]).totals.rows[0].coverage == Coverage(24, 20, 0, 1, 3)


def test_zero_catch_up_spreads_zero_estimated():
    req = msk_day()
    report = run(req, [series(P1, req, {**gap(10, 12), 13: D("0")})])
    row = report.totals.rows[0]
    assert row.kwh == 20
    assert row.estimated_kwh == 0
    assert row.coverage.estimated == 4
    assert len(report.issues) == 1
    assert report.issues[0].kind is IssueKind.ESTIMATED
    assert report.issues[0].kwh == 0


# --- leading / trailing / window edges -------------------------------------------


def test_leading_and_trailing_gaps_stay_missing():
    req = msk_day()
    ser = series(P1, req, {**gap(0, 3), **gap(20, 23)})
    report = run(req, [ser])
    row = report.totals.rows[0]
    assert row.coverage == Coverage(24, 16, 0, 0, 8)
    assert report.issues == ()
    prepared, _ = prep(req, ser)
    assert prepared.values[4] == HourValue(ONE, HourKind.MEASURED)


def test_earliest_key_without_lookback_is_measured_and_spike_checked():
    req = msk_day()
    ser = series(P1, req, {**gap(0, 3), 4: D("14")})
    prepared, issues = prep(req, ser)
    assert all(v is None for v in prepared.values[:4])
    assert prepared.values[4] == HourValue(D("14"), HourKind.EXCLUDED)
    assert [i.kind for i in issues] == [IssueKind.EXCLUDED_SPIKE]

    with_lookback = with_keys(ser, {req.start - 3 * HOUR: ONE})
    prepared, issues = prep(req, with_lookback)
    # span (start-3h, 04:00]: n = 7, 2 kWh/h
    assert all(v == HourValue(D("2"), HourKind.ESTIMATED) for v in prepared.values[:5])
    assert issues == (msk_issue(IssueKind.ESTIMATED, 0, 5, D("10")),)


def test_gap_with_catch_up_after_window():
    req = msk_day()
    ser = with_keys(series(P1, req, gap(20, 23)), {req.end + HOUR: D("12")})
    report = run(req, [ser])
    row = report.totals.rows[0]
    assert row.estimated_kwh == 8
    assert row.coverage.estimated == 4
    cells = {c.key: c for c in row.zones}
    assert cells["t1"].kwh == 13 + 6
    assert cells["t2"].kwh == 7 + 2
    assert report.issues == (
        QualityIssue(
            IssueKind.ESTIMATED,
            P1,
            msk_at(20),
            datetime(2026, 1, 16, 0, tzinfo=MSK),
            D("8"),
        ),
    )


def test_gap_entirely_outside_window_no_effect():
    req = msk_day()
    inside = series(P1, req)
    outside = {
        req.start - 30 * HOUR: ONE,
        req.start - 20 * HOUR: ONE,  # 9 h gap before this catch-up
        req.start - 19 * HOUR: D("100"),  # spike
        req.start - 18 * HOUR: D("-1"),  # negative
        **{req.start - i * HOUR: ONE for i in range(1, 18)},
    }
    noisy = with_keys(inside, outside)
    baseline = with_keys(inside, {req.start - HOUR: ONE})
    report = run(req, [noisy])
    assert report.issues == ()
    assert report == run(req, [baseline])


def test_very_long_gap_is_spread():
    req = msk_day()
    pred = req.start - timedelta(days=400)
    delta = D("9600.5")
    ser = with_keys(
        series(P1, req, gap(0, 12)),
        {pred: ONE, req.start + 12 * HOUR: delta},
    )
    started = time.perf_counter()
    prepared, issues = prep(req, ser)
    assert time.perf_counter() - started < 1

    n = (req.start + 12 * HOUR - pred) // HOUR
    assert n == 9600 + 12
    q = (delta / n).quantize(SPREAD_QUANTUM, rounding=ROUND_DOWN)
    r = delta - (n - 1) * q
    expected = [HourValue(q, HourKind.ESTIMATED)] * 12 + [
        HourValue(r, HourKind.ESTIMATED)
    ]
    assert list(prepared.values[:13]) == expected
    assert len(issues) == 1
    assert issues[0].kwh == 12 * q + r


def test_spread_across_dst_fall_back_berlin():
    req = request(date(2026, 10, 25), date(2026, 10, 26), BER)
    assert len(list(iter_hours(req.start, req.end))) == 25
    first = req.start  # 2026-10-24T22:00Z
    ser = DeviceSeries(
        P1,
        {
            first - HOUR: ONE,
            **{first + i * HOUR: ONE for i in range(6, 25)},
            first + 5 * HOUR: D("6"),
        },
    )
    assert first + 5 * HOUR == datetime(2026, 10, 25, 3, tzinfo=UTC)
    report = run(req, [ser])
    bucket = report.buckets[0]
    assert bucket.hours == 25
    row = bucket.rows[0]
    assert row.coverage == Coverage(25, 19, 6, 0, 0)
    cells = {c.key: c for c in row.zones}
    assert cells["t2"].kwh == 9
    issue = report.issues[0]
    assert issue.kwh == 6
    assert issue.start == datetime(2026, 10, 25, 0, tzinfo=BER)


# --- window independence ---------------------------------------------------------


def _three_day_series() -> tuple[ReportRequest, DeviceSeries]:
    req = request(date(2026, 3, 28), date(2026, 3, 31), BER, Grouping.HOUR)
    hours = list(iter_hours(req.start, req.end))
    assert len(hours) == 71
    removed = set(range(10, 14)) | set(range(20, 31)) | set(range(55, 59))
    deltas = {h: D(f"1.{i % 3}") for i, h in enumerate(hours) if i not in removed}
    deltas[hours[40]] = D("9")
    deltas[hours[50]] = D("-0.2")
    return req, DeviceSeries(P1, deltas)


def test_window_independence():
    req, ser = _three_day_series()
    big = run(req, [ser])
    by_start = {b.start: b.rows[0] for b in big.buckets}
    assert big.issues

    for day in (28, 29, 30):
        day_req = request(date(2026, 3, day), date(2026, 3, day + 1), BER, "hour")
        small = run(day_req, [ser])
        assert small.buckets
        for bucket in small.buckets:
            assert bucket.rows[0] == by_start[bucket.start]
        in_day = [by_start[b.start] for b in small.buckets]
        est = sum(i.kwh for i in small.issues if i.kind is IssueKind.ESTIMATED)
        exc = sum(i.kwh for i in small.issues if i.kind is not IssueKind.ESTIMATED)
        assert est == sum((r.estimated_kwh for r in in_day), D(0))
        assert exc == sum((r.excluded_kwh for r in in_day), D(0))


# --- issue invariants ------------------------------------------------------------


def _mixed_a(req: ReportRequest) -> tuple[DeviceSeries, DeviceSeries]:
    return (
        series(P1, req, {**gap(5, 9), 10: D("7"), 30: D("-1"), 31: D("5")}),
        series(P2, req, {**gap(20, 30), 31: D("3"), 60: D("0")}),
    )


def _mixed_b(req: ReportRequest) -> tuple[DeviceSeries, DeviceSeries]:
    return (
        series(P1, req, {**gap(0, 3), 4: D("2"), **gap(40, 55), 56: D("50")}),
        series(P2, req, {**gap(10, 12), 13: D("0.1"), **gap(66, 71)}),
    )


def _mixed_c(req: ReportRequest) -> tuple[DeviceSeries, DeviceSeries]:
    return (
        series(P1, req, {i: D("-0.01") for i in range(0, 72, 7)}),
        series(P2, req, {**gap(1, 70), 71: D("100")}),
    )


@pytest.mark.parametrize("factory", [_mixed_a, _mixed_b, _mixed_c], ids=["a", "b", "c"])
def test_issue_invariants(
    factory: Callable[[ReportRequest], tuple[DeviceSeries, DeviceSeries]],
):
    req = request(date(2026, 1, 14), date(2026, 1, 17))
    devices = list(factory(req))
    report = run(req, devices)
    assert report.issues

    for device in devices:
        mine = [i for i in report.issues if i.device_id == device.device_id]
        row: Row = next(
            r for r in report.totals.rows if r.device_id == device.device_id
        )
        estimated = [i for i in mine if i.kind is IssueKind.ESTIMATED]
        excluded = [i for i in mine if i.kind is not IssueKind.ESTIMATED]
        assert sum((i.kwh for i in estimated), D(0)) == row.estimated_kwh
        assert sum((i.kwh for i in excluded), D(0)) == row.excluded_kwh
        assert len(excluded) == row.coverage.excluded
        assert (
            sum(((i.end - i.start) // HOUR for i in estimated), 0)
            == row.coverage.estimated
        )
        starts = [i.start for i in mine]
        assert starts == sorted(starts)

    order = [d.device_id for d in devices]
    positions = [order.index(i.device_id) for i in report.issues]
    assert positions == sorted(positions)
    for issue in report.issues:
        assert req.start <= issue.start < issue.end <= req.end
        assert issue.start.utcoffset() == timedelta(hours=3)
        assert issue.end.utcoffset() == timedelta(hours=3)


# --- equivalence / settings ------------------------------------------------------


def test_clean_series_equals_prepare_measured():
    req = request(date(2026, 1, 14), date(2026, 1, 16))
    ser = series(P1, req, {3: D("2.5"), 7: D("0")})
    hours = classify_hours(default_schedule(), req.start, req.end, req.time_zone)
    prepared, issues = prep(req, ser)
    assert prepared == prepare_measured(ser, hours)
    assert issues == ()
    expected = assemble_report(req, hours, [prepare_measured(ser, hours)])
    assert run(req, [ser]) == expected


def test_per_device_override_and_disable():
    req = msk_day()
    devices = [series(P1, req, {5: D("8")}), series(P2, req, {5: D("8")})]

    def excluded(report: Report) -> list[int]:
        return [r.coverage.excluded for r in report.totals.rows]

    assert excluded(run(req, devices)) == [1, 1]
    s1 = QualitySettings(device_spike_limits={P1: D("10")})
    assert excluded(run(req, devices, s1)) == [0, 1]
    s2 = QualitySettings(device_spike_limits={P2: None})
    assert excluded(run(req, devices, s2)) == [1, 0]
    assert excluded(run(req, devices, QualitySettings(spike_limit=None))) == [0, 0]
    unknown = QualitySettings(device_spike_limits={"sensor.removed": D("1")})
    assert excluded(run(req, devices, unknown)) == [1, 1]

    assert s1.limit_for(P1) == D("10")
    assert s1.limit_for(P2) == DEFAULT_SPIKE_LIMIT
    assert s2.limit_for(P2) is None


BAD_LIMITS: list[Any] = [
    D("0"),
    D("-1"),
    D("NaN"),
    D("Infinity"),
    D("-Infinity"),
    4.0,
    4,
    True,
]


@pytest.mark.parametrize("bad", BAD_LIMITS, ids=repr)
def test_quality_settings_validation(bad: Any):
    with pytest.raises(ValueError):
        QualitySettings(spike_limit=bad)
    with pytest.raises(ValueError):
        QualitySettings(device_spike_limits={P1: bad})


def test_quality_settings_misc_validation():
    with pytest.raises(ValueError):
        QualitySettings(device_spike_limits={"": D("1")})
    settings = QualitySettings(device_spike_limits={P1: D("1")})
    with pytest.raises(TypeError):
        settings.device_spike_limits[P2] = D("2")  # type: ignore[index]
    assert QualitySettings().spike_limit == D("4")


def test_build_report_quality_is_keyword_only():
    req = msk_day()
    args: Any = (req, default_schedule(), [series(P1, req)], QualitySettings())
    with pytest.raises(TypeError):
        build_report(*args)
    ser = series(P1, req, {12: D("5")})
    assert run(req, [ser], None) == run(req, [ser], QualitySettings())


def test_prepare_series_rejects_empty_hours():
    with pytest.raises(ValueError):
        prepare_series(
            series(P1, msk_day()), (), time_zone=MSK, settings=QualitySettings()
        )


def test_rejected_catch_up_after_window_has_no_effect():
    req = msk_day()
    ser = with_keys(series(P1, req, gap(20, 23)), {req.end + HOUR: D("500")})
    report = run(req, [ser])
    assert report.issues == ()
    assert report.totals.rows[0].coverage == Coverage(24, 20, 0, 0, 4)
