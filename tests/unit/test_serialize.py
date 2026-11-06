"""Unit tests for engine.serialize (tasks/012-report-serializer.md)."""

import json
from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from engine.models import (
    DeviceSeries,
    Grouping,
    IssueKind,
    Report,
    ReportRequest,
)
from engine.plan_codec import plan_to_data
from engine.presets import ru_two_zone, single_rate
from engine.report import build_report
from engine.serialize import SCHEMA_VERSION, DeviceInfo, report_to_json
from engine.tariff import TariffPlan, TariffSchedule
from engine.timeutil import iter_hours, local_day_start

MSK = ZoneInfo("Europe/Moscow")
BER = ZoneInfo("Europe/Berlin")

P1 = "sensor.plug_01"
P2 = "sensor.plug_02"

D = Decimal
ONE = D("1")
HOUR = timedelta(hours=1)

DEV1 = DeviceInfo(P1, "Plug 01", "ok")
DEV2 = DeviceInfo(P2, "Plug 02", "ok")


def two_zone(
    valid_from: date = date(2026, 1, 1), day_price: str = "10.30"
) -> TariffPlan:
    return ru_two_zone(
        valid_from=valid_from, day_price=D(day_price), night_price=D("4.43")
    )


def schedule(*plans: TariffPlan) -> TariffSchedule:
    return TariffSchedule(plans or (two_zone(),))


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


def msk_day(grouping: Grouping | str = Grouping.DAY) -> ReportRequest:
    return request(date(2026, 1, 15), date(2026, 1, 16), grouping=grouping)


def series(
    device_id: str,
    req: ReportRequest,
    overrides: Mapping[int, Decimal | None] | None = None,
    *,
    default: Decimal = ONE,
) -> DeviceSeries:
    over = overrides or {}
    deltas: dict[datetime, Decimal] = {}
    for index, hour in enumerate(iter_hours(req.start, req.end)):
        value = over.get(index, default)
        if value is not None:
            deltas[hour] = value
    return DeviceSeries(device_id, deltas)


def gap(first: int, last: int) -> dict[int, Decimal | None]:
    return {i: None for i in range(first, last + 1)}


def one_hour_report(
    plan: TariffPlan, kwh: Decimal, device_id: str = P1
) -> tuple[Report, ReportRequest]:
    start = datetime(2026, 1, 15, 0, tzinfo=MSK)
    req = ReportRequest(
        start=start, end=start + HOUR, time_zone=MSK, grouping=Grouping.TOTAL
    )
    ser = DeviceSeries(device_id, {req.start: kwh})
    return build_report(req, schedule(plan), [ser]), req


def to_json(report: Report, devices: list[DeviceInfo]) -> dict[str, Any]:
    return report_to_json(
        report, devices=devices, time_zone="Europe/Moscow", currency="EUR"
    )


def device_ids(report: Report) -> list[DeviceInfo]:
    return [
        DeviceInfo(r.device_id or "", r.device_id or "", "ok")
        for r in report.totals.rows
    ]


EXPECTED_ROW: dict[str, Any] = {
    "entity_id": P1,
    "kwh": "29.000",
    "cost": "240.00",
    "unpriced_kwh": "0.000",
    "estimated_kwh": "10.000",
    "excluded_kwh": "0.000",
    "status": "estimated",
    "coverage": {
        "expected": 24,
        "measured": 19,
        "estimated": 5,
        "excluded": 0,
        "missing": 0,
    },
    "zones": [
        {"key": "t1", "kwh": "19.000", "cost": "195.70", "price": "10.3000"},
        {"key": "t2", "kwh": "10.000", "cost": "44.30", "price": "4.4300"},
    ],
}


def gap_report(grouping: Grouping | str = Grouping.DAY) -> Report:
    req = msk_day(grouping)
    ser = series(P1, req, {**gap(5, 8), 9: D("10")})
    ser = DeviceSeries(P1, {**ser.deltas, req.start - HOUR: ONE})
    return build_report(req, schedule(), [ser])


def test_full_document_two_zone_day():
    report = gap_report()
    doc = to_json(report, [DEV1])

    bucket = {
        "start": "2026-01-15T00:00:00+03:00",
        "end": "2026-01-16T00:00:00+03:00",
        "hours": 24,
        "rows": [EXPECTED_ROW],
        "total": {**EXPECTED_ROW, "entity_id": None},
    }
    assert SCHEMA_VERSION == 1
    assert doc == {
        "schema_version": 1,
        "time_zone": "Europe/Moscow",
        "currency": "EUR",
        "start": "2026-01-15T00:00:00+03:00",
        "end": "2026-01-16T00:00:00+03:00",
        "grouping": "day",
        "zones": [{"key": "t1", "name": "Day"}, {"key": "t2", "name": "Night"}],
        "plans": [plan_to_data(two_zone())],
        "devices": [{"entity_id": P1, "name": "Plug 01", "statistics": "ok"}],
        "buckets": [bucket],
        "totals": bucket,
        "unpriced_hours": 0,
        "issues": [
            {
                "kind": "estimated",
                "entity_id": P1,
                "start": "2026-01-15T05:00:00+03:00",
                "end": "2026-01-15T10:00:00+03:00",
                "hours": 5,
                "kwh": "10.000",
            }
        ],
    }
    assert list(doc) == [
        "schema_version",
        "time_zone",
        "currency",
        "start",
        "end",
        "grouping",
        "zones",
        "plans",
        "devices",
        "buckets",
        "totals",
        "unpriced_hours",
        "issues",
    ]


def _walk(node: Any) -> None:
    if isinstance(node, dict):
        for key, value in node.items():  # pyright: ignore[reportUnknownVariableType]
            assert isinstance(key, str)
            _walk(value)
    elif isinstance(node, list):
        for item in node:  # pyright: ignore[reportUnknownVariableType]
            _walk(item)
    else:
        assert node is None or type(node) in (str, int), repr(node)


def test_json_types_only():
    for grouping in (Grouping.DAY, Grouping.HOUR):
        doc = to_json(gap_report(grouping), [DEV1])
        _walk(doc)
        assert json.loads(json.dumps(doc)) == doc


def test_rounding_half_up_at_output_only():
    report, _ = one_hour_report(
        single_rate(valid_from=date(2026, 1, 1), price=ONE), D("0.0005")
    )
    row = to_json(report, [DEV1])["totals"]["rows"][0]
    assert row["kwh"] == "0.001"
    assert row["cost"] == "0.00"
    assert row["zones"][0]["kwh"] == "0.001"
    assert report.totals.rows[0].kwh == D("0.0005")
    assert report.totals.rows[0].cost == D("0.0005")

    report, _ = one_hour_report(
        single_rate(valid_from=date(2026, 1, 1), price=D("0.00005")), ONE
    )
    cell = to_json(report, [DEV1])["totals"]["rows"][0]["zones"][0]
    assert cell["price"] == "0.0001"
    assert report.totals.rows[0].zones[0].price == D("0.00005")

    report, _ = one_hour_report(
        single_rate(valid_from=date(2026, 1, 1), price=ONE), D("0.0015")
    )
    assert to_json(report, [DEV1])["totals"]["rows"][0]["kwh"] == "0.002"
    assert report.totals.rows[0].kwh == D("0.0015")


def test_total_rounded_from_exact_sum():
    start = datetime(2026, 1, 15, 0, tzinfo=MSK)
    req = ReportRequest(
        start=start, end=start + HOUR, time_zone=MSK, grouping=Grouping.TOTAL
    )
    devices = [DeviceSeries(d, {req.start: D("0.005")}) for d in (P1, P2)]
    plan = single_rate(valid_from=date(2026, 1, 1), price=ONE)
    report = build_report(req, schedule(plan), devices)
    doc = to_json(report, [DEV1, DEV2])
    rows = doc["totals"]["rows"]
    assert [r["cost"] for r in rows] == ["0.01", "0.01"]
    assert doc["totals"]["total"]["cost"] == "0.01"
    assert doc["totals"]["total"]["kwh"] == "0.010"


def test_none_vs_zero():
    req = msk_day()
    report = build_report(
        req,
        schedule(),
        [DeviceSeries(P1, {}), series(P2, req, default=D("0"))],
    )
    doc = to_json(report, [DEV1, DEV2])
    empty, zero = doc["totals"]["rows"]
    assert empty["kwh"] is None
    assert empty["cost"] is None
    assert empty["unpriced_kwh"] == "0.000"
    assert empty["status"] == "missing"
    assert empty["zones"][0] == {
        "key": "t1",
        "kwh": None,
        "cost": None,
        "price": "10.3000",
    }
    assert zero["kwh"] == "0.000"
    assert zero["cost"] == "0.00"
    assert zero["zones"][0]["kwh"] == "0.000"
    assert zero["zones"][0]["cost"] == "0.00"


def test_no_negative_zero():
    req = msk_day()
    report = build_report(req, schedule(), [series(P1, req, {12: D("-0.0001")})])
    doc = to_json(report, [DEV1])
    assert doc["totals"]["rows"][0]["excluded_kwh"] == "0.000"
    assert doc["totals"]["total"]["excluded_kwh"] == "0.000"
    assert [i["kind"] for i in doc["issues"]] == ["excluded_negative"]
    assert doc["issues"][0]["kwh"] == "0.000"

    report = build_report(req, schedule(), [series(P1, req, {12: D("-0.05")})])
    doc = to_json(report, [DEV1])
    assert doc["totals"]["rows"][0]["excluded_kwh"] == "-0.050"
    assert doc["issues"][0]["kwh"] == "-0.050"


def test_plan_switch_price_null():
    plans = (two_zone(), two_zone(date(2026, 1, 16), "11.00"))
    sched = schedule(*plans)
    req = request(date(2026, 1, 1), date(2026, 2, 1), grouping=Grouping.MONTH)
    devices = [series(P1, req)]

    doc = to_json(build_report(req, sched, devices), [DEV1])
    cells = {c["key"]: c for c in doc["buckets"][0]["rows"][0]["zones"]}
    assert cells["t1"]["price"] is None
    assert cells["t2"]["price"] == "4.4300"
    assert doc["plans"] == [plan_to_data(p) for p in plans]

    req = request(date(2026, 1, 1), date(2026, 2, 1), grouping=Grouping.DAY)
    doc = to_json(build_report(req, sched, [series(P1, req)]), [DEV1])
    prices = [b["rows"][0]["zones"][0]["price"] for b in doc["buckets"]]
    assert prices[0] == "10.3000"
    assert prices[14] == "10.3000"
    assert prices[15] == "11.0000"
    assert prices[-1] == "11.0000"


def test_groupings_and_total():
    req = msk_day(Grouping.HOUR)
    doc = to_json(build_report(req, schedule(), [series(P1, req)]), [DEV1])
    starts = [b["start"] for b in doc["buckets"]]
    assert len(starts) == 24
    assert starts == sorted(starts)
    assert {b["hours"] for b in doc["buckets"]} == {1}

    req = msk_day(Grouping.TOTAL)
    doc = to_json(build_report(req, schedule(), [series(P1, req)]), [DEV1])
    assert doc["buckets"] == [doc["totals"]]
    assert doc["grouping"] == "total"

    req = request(date(2026, 1, 15), date(2026, 1, 21), grouping=Grouping.WEEK)
    doc = to_json(build_report(req, schedule(), [series(P1, req)]), [DEV1])
    assert [b["start"] for b in doc["buckets"]] == [
        "2026-01-15T00:00:00+03:00",
        "2026-01-19T00:00:00+03:00",
    ]

    req = request(date(2026, 10, 25), date(2026, 10, 26), BER)
    doc = report_to_json(
        build_report(req, schedule(), [series(P1, req)]),
        devices=[DEV1],
        time_zone="Europe/Berlin",
        currency=None,
    )
    assert doc["buckets"][0]["hours"] == 25
    assert doc["start"] == "2026-10-25T00:00:00+02:00"
    assert doc["end"] == "2026-10-26T00:00:00+01:00"
    assert doc["buckets"][0]["end"] == "2026-10-26T00:00:00+01:00"


def test_devices_must_match_rows():
    req = msk_day()
    report = build_report(req, schedule(), [series(P1, req), series(P2, req)])
    with pytest.raises(ValueError):
        to_json(report, [DEV1])
    with pytest.raises(ValueError):
        to_json(report, [DEV1, DEV2, DeviceInfo("sensor.plug_03", "Plug 03", "ok")])
    with pytest.raises(ValueError):
        to_json(report, [DEV2, DEV1])
    with pytest.raises(ValueError):
        report_to_json(report, devices=[DEV1, DEV2], time_zone="", currency="EUR")

    doc = report_to_json(
        report, devices=[DEV1, DEV2], time_zone="Europe/Moscow", currency=None
    )
    assert doc["currency"] is None


def test_issue_kinds_and_hours():
    req = msk_day()
    report = build_report(
        req,
        schedule(),
        [series(P1, req, {12: D("4.5004"), 14: D("-0.0505")})],
    )
    doc = to_json(report, [DEV1])
    assert [i["kind"] for i in doc["issues"]] == [i.kind.value for i in report.issues]
    assert {i["kind"] for i in doc["issues"]} == {
        IssueKind.EXCLUDED_SPIKE.value,
        IssueKind.EXCLUDED_NEGATIVE.value,
    }
    assert [i["hours"] for i in doc["issues"]] == [1, 1]
    by_kind = {i["kind"]: i["kwh"] for i in doc["issues"]}
    assert by_kind == {"excluded_spike": "4.500", "excluded_negative": "-0.051"}


def test_utc_inputs_are_converted_to_report_zone():
    req = ReportRequest(
        start=datetime(2026, 1, 14, 21, tzinfo=UTC),
        end=datetime(2026, 1, 15, 21, tzinfo=UTC),
        time_zone=MSK,
        grouping=Grouping.DAY,
    )
    doc = to_json(build_report(req, schedule(), [series(P1, req)]), [DEV1])
    assert doc["start"] == "2026-01-15T00:00:00+03:00"
    assert doc["end"] == "2026-01-16T00:00:00+03:00"


@pytest.mark.parametrize(
    ("day", "next_day", "window_hours"),
    [
        (date(2026, 10, 25), date(2026, 10, 26), 25),
        (date(2026, 3, 29), date(2026, 3, 30), 23),
    ],
)
def test_issue_hours_across_dst(day: date, next_day: date, window_hours: int):
    req = request(day, next_day, BER)
    ser = series(P1, req, {**gap(1, 3), 4: D("4")})
    report = build_report(req, schedule(), [ser])
    doc = report_to_json(
        report, devices=[DEV1], time_zone="Europe/Berlin", currency=None
    )
    row = doc["totals"]["rows"][0]
    assert doc["totals"]["hours"] == window_hours
    assert row["coverage"]["estimated"] == 4
    assert [i["hours"] for i in doc["issues"]] == [4]


def test_issue_hours_spike_in_fall_back_fold():
    req = request(date(2026, 10, 25), date(2026, 10, 26), BER)
    report = build_report(req, schedule(), [series(P1, req, {2: D("4.5")})])
    doc = report_to_json(
        report, devices=[DEV1], time_zone="Europe/Berlin", currency=None
    )
    (issue,) = doc["issues"]
    assert issue["kind"] == "excluded_spike"
    assert issue["start"] == "2026-10-25T02:00:00+02:00"
    assert issue["end"] == "2026-10-25T02:00:00+01:00"
    assert issue["hours"] == 1
    assert doc["totals"]["rows"][0]["coverage"]["excluded"] == 1


def test_nested_key_order():
    doc = to_json(gap_report(), [DEV1])
    bucket = doc["totals"]
    row = bucket["rows"][0]
    assert list(bucket) == ["start", "end", "hours", "rows", "total"]
    assert list(row) == list(EXPECTED_ROW)
    assert list(row["coverage"]) == [
        "expected",
        "measured",
        "estimated",
        "excluded",
        "missing",
    ]
    assert list(row["zones"][0]) == ["key", "kwh", "cost", "price"]
    assert list(doc["issues"][0]) == [
        "kind",
        "entity_id",
        "start",
        "end",
        "hours",
        "kwh",
    ]
    assert list(doc["devices"][0]) == ["entity_id", "name", "statistics"]
    assert list(doc["zones"][0]) == ["key", "name"]


def test_issue_span_must_be_whole_hours():
    report = gap_report()
    bad = replace(report.issues[0], end=report.issues[0].end + timedelta(minutes=30))
    with pytest.raises(ValueError, match="whole number of hours"):
        to_json(replace(report, issues=(bad,)), [DEV1])
