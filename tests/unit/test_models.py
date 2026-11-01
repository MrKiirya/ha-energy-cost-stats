"""Unit tests for engine.models (tasks/005-time-and-zones.md)."""

from collections.abc import Iterator, Mapping
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from types import MappingProxyType

import pytest

from engine.models import (
    Coverage,
    DataStatus,
    DeviceSeries,
    Grouping,
    IssueKind,
    ReportRequest,
    Row,
    ZoneCell,
)


def _h(hour: int, tz: timezone = UTC) -> datetime:
    return datetime(2026, 1, 15, hour, 0, tzinfo=tz)


MSK = timezone(timedelta(hours=3))


class _DupMapping(Mapping[datetime, Decimal]):
    """A minimal read-only Mapping that keeps duplicate-instant keys distinct.

    A plain ``dict`` literal cannot hold two entries for datetimes that compare
    equal (aware datetime equality/hash is instant-based), so it cannot exercise
    `DeviceSeries`'s same-instant duplicate check. This stand-in preserves both
    entries by storing them as a list of pairs.
    """

    def __init__(self, pairs: list[tuple[datetime, Decimal]]) -> None:
        self._pairs = pairs

    def items(self) -> Iterator[tuple[datetime, Decimal]]:  # type: ignore[override]
        return iter(self._pairs)

    def __getitem__(self, key: datetime) -> Decimal:
        for pair_key, value in self._pairs:
            if pair_key == key:
                return value
        raise KeyError(key)

    def __iter__(self) -> Iterator[datetime]:
        return (key for key, _ in self._pairs)

    def __len__(self) -> int:
        return len(self._pairs)


# --- ReportRequest ----------------------------------------------------------


def test_report_request_validation():
    with pytest.raises(ValueError):
        ReportRequest(
            start=datetime(2026, 1, 15, 0, 0),  # naive
            end=_h(3),
            time_zone=UTC,
            grouping=Grouping.HOUR,
        )
    with pytest.raises(ValueError):
        ReportRequest(start=_h(3), end=_h(3), time_zone=UTC, grouping=Grouping.HOUR)
    with pytest.raises(ValueError):
        ReportRequest(
            start=_h(3),
            end=datetime(2026, 1, 15, 4, 30, tzinfo=UTC),
            time_zone=UTC,
            grouping=Grouping.HOUR,
        )

    request = ReportRequest(
        start=datetime(2026, 1, 15, 3, 0, tzinfo=MSK),
        end=datetime(2026, 1, 15, 6, 0, tzinfo=MSK),
        time_zone=UTC,
        grouping=Grouping.HOUR,
    )
    assert request.start == datetime(2026, 1, 15, 0, 0, tzinfo=UTC)
    assert request.end == datetime(2026, 1, 15, 3, 0, tzinfo=UTC)


def test_report_request_grouping_accepts_enum_or_value_string():
    from_enum = ReportRequest(
        start=_h(0), end=_h(3), time_zone=UTC, grouping=Grouping.WEEK
    )
    assert from_enum.grouping is Grouping.WEEK

    from_string = ReportRequest(start=_h(0), end=_h(3), time_zone=UTC, grouping="week")
    assert from_string.grouping is Grouping.WEEK
    assert isinstance(from_string.grouping, Grouping)


def test_report_request_grouping_rejects_unknown_value():
    with pytest.raises(ValueError, match="unknown grouping"):
        ReportRequest(start=_h(0), end=_h(3), time_zone=UTC, grouping="fortnight")


# --- DeviceSeries -------------------------------------------------------------


def test_device_series_normalizes_and_validates():
    series = DeviceSeries(
        device_id="plug_01",
        deltas={datetime(2026, 1, 15, 3, 0, tzinfo=MSK): Decimal("1.5")},
    )
    assert series.deltas == {_h(0): Decimal("1.5")}
    assert isinstance(series.deltas, MappingProxyType)
    with pytest.raises(TypeError):
        series.deltas[_h(1)] = Decimal("1")  # type: ignore[index]

    with pytest.raises(ValueError):
        DeviceSeries(
            device_id="plug_01",
            deltas={datetime(2026, 1, 15, 0, 0): Decimal("1")},
        )
    with pytest.raises(ValueError):
        DeviceSeries(
            device_id="plug_01",
            deltas={datetime(2026, 1, 15, 0, 30, tzinfo=UTC): Decimal("1")},
        )
    with pytest.raises(ValueError):
        DeviceSeries(device_id="plug_01", deltas={_h(0): Decimal("NaN")})
    with pytest.raises(ValueError):
        DeviceSeries(device_id="plug_01", deltas={_h(0): 1.5})  # type: ignore[dict-item]
    with pytest.raises(ValueError):
        DeviceSeries(device_id="", deltas={_h(0): Decimal("1")})
    with pytest.raises(ValueError):
        DeviceSeries(
            device_id="plug_01",
            deltas=_DupMapping(
                [
                    (_h(0), Decimal("1")),
                    (datetime(2026, 1, 15, 3, 0, tzinfo=MSK), Decimal("2")),
                ]
            ),
        )


def test_device_series_from_floats():
    series = DeviceSeries.from_floats("plug_01", {_h(0): 0.1})
    value = series.deltas[_h(0)]
    assert isinstance(value, Decimal)
    assert value == Decimal("0.1")


# --- Coverage -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("expected", "measured", "estimated", "excluded", "missing", "status"),
    [
        (24, 24, 0, 0, 0, DataStatus.COMPLETE),
        (24, 20, 4, 0, 0, DataStatus.ESTIMATED),
        (24, 20, 0, 0, 4, DataStatus.PARTIAL),
        (24, 20, 2, 1, 1, DataStatus.PARTIAL),
        (24, 0, 0, 0, 24, DataStatus.MISSING),
        (24, 0, 0, 24, 0, DataStatus.MISSING),
        (0, 0, 0, 0, 0, DataStatus.MISSING),
    ],
)
def test_coverage_status(expected, measured, estimated, excluded, missing, status):
    coverage = Coverage(
        expected=expected,
        measured=measured,
        estimated=estimated,
        excluded=excluded,
        missing=missing,
    )
    assert coverage.status == status


def test_coverage_invariant_and_add():
    with pytest.raises(ValueError):
        Coverage(expected=24, measured=1, estimated=0, excluded=0, missing=0)
    with pytest.raises(ValueError):
        Coverage(expected=-1, measured=0, estimated=0, excluded=0, missing=0)

    total = Coverage(24, 24, 0, 0, 0) + Coverage(24, 20, 0, 0, 4)
    assert total == Coverage(48, 44, 0, 0, 4)
    assert Coverage.empty() == Coverage(0, 0, 0, 0, 0)

    with pytest.raises(TypeError):
        Coverage(24, 24, 0, 0, 0) + 1  # type: ignore[operator]


# --- ZoneCell -------------------------------------------------------------------


def test_zone_cell_effective_price():
    zero_kwh = ZoneCell(key="t1", kwh=Decimal("0"), cost=Decimal("0"), price=None)
    assert zero_kwh.effective_price is None

    cell = ZoneCell(
        key="t1", kwh=Decimal("2"), cost=Decimal("8.86"), price=Decimal("4.43")
    )
    assert cell.effective_price == Decimal("4.43")

    # Human decision (missing data is None, not 0): a cell with no data at all.
    missing = ZoneCell(key="t1", kwh=None, cost=None, price=None)
    assert missing.effective_price is None


# --- Row -----------------------------------------------------------------------


def test_row_status_from_coverage():
    row = Row(
        device_id="plug_01",
        zones=(),
        kwh=Decimal("5"),
        cost=Decimal("50"),
        unpriced_kwh=Decimal("0"),
        estimated_kwh=Decimal("0"),
        excluded_kwh=Decimal("0"),
        coverage=Coverage(expected=24, measured=24, estimated=0, excluded=0, missing=0),
    )
    assert row.status == DataStatus.COMPLETE


# --- Enums -------------------------------------------------------------------


def test_enums_serialize_as_lowercase_strings():
    assert str(Grouping.WEEK) == "week"
    assert DataStatus.MISSING == "missing"
    assert IssueKind.EXCLUDED_SPIKE == "excluded_spike"
