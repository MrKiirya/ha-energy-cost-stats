"""Engine public I/O types (tasks/005-time-and-zones.md).

Pure Python, stdlib only (CLAUDE.md principle 4). These are the stable request/response
shapes used by task 006 (pricing and grouping), task 007 (data quality) and the stage 3
websocket/service layer.

Human decision (2026-09-25, overrides earlier body text): missing data is explicit
``None``, never a silent zero. A cell/row with no measured or estimated kWh for its
window carries ``kwh = None`` / ``cost = None`` (not ``Decimal("0")``); its
``status`` (via ``Coverage.status``) reports ``missing`` or ``partial``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, tzinfo
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType

from .tariff import TariffPlan
from .timeutil import to_utc_hour


class Grouping(StrEnum):
    """How hours are bucketed into report rows."""

    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    TOTAL = "total"


@dataclass(frozen=True, slots=True)
class ReportRequest:
    """A report window, time zone and grouping. Engine input, task 006 consumes it."""

    start: datetime
    end: datetime
    time_zone: tzinfo
    grouping: Grouping

    def __post_init__(self) -> None:
        start = to_utc_hour(self.start)
        end = to_utc_hour(self.end)
        if end <= start:
            raise ValueError(f"end ({end}) must be after start ({start})")
        object.__setattr__(self, "start", start)
        object.__setattr__(self, "end", end)


@dataclass(frozen=True, slots=True)
class DeviceSeries:
    """Hourly energy deltas (kWh) for one device, keyed by UTC hour start."""

    device_id: str
    deltas: Mapping[datetime, Decimal]

    def __post_init__(self) -> None:
        if not self.device_id:
            raise ValueError("device_id must not be empty")

        normalized: dict[datetime, Decimal] = {}
        for key, value in self.deltas.items():
            utc_key = to_utc_hour(key)
            if utc_key in normalized:
                raise ValueError(f"duplicate delta key for the same instant: {utc_key}")
            if isinstance(value, bool) or not isinstance(value, Decimal):  # pyright: ignore[reportUnnecessaryIsInstance]
                raise ValueError(
                    f"delta value must be a Decimal, got {type(value).__name__}"
                )
            if not value.is_finite():
                raise ValueError(f"delta value must be finite, got {value}")
            normalized[utc_key] = value

        object.__setattr__(self, "deltas", MappingProxyType(normalized))

    @classmethod
    def from_floats(
        cls, device_id: str, deltas: Mapping[datetime, float]
    ) -> DeviceSeries:
        """Build a series from float deltas (the only float entry point, stage 3
        adapter).

        Each value is converted via ``Decimal(repr(x))``, so ``0.1`` becomes
        ``Decimal("0.1")`` rather than its binary-float expansion.
        """
        return cls(
            device_id=device_id,
            deltas={key: Decimal(repr(value)) for key, value in deltas.items()},
        )


class DataStatus(StrEnum):
    """Data completeness of a report row or cell, derived from a `Coverage`."""

    COMPLETE = "complete"
    ESTIMATED = "estimated"
    PARTIAL = "partial"
    MISSING = "missing"


@dataclass(frozen=True, slots=True)
class Coverage:
    """Hour-count breakdown of a row/cell's window.

    Task 007 fills ``estimated``/``excluded``.
    """

    expected: int
    measured: int
    estimated: int
    excluded: int
    missing: int

    def __post_init__(self) -> None:
        for name in ("expected", "measured", "estimated", "excluded", "missing"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative int, got {value!r}")
        total = self.measured + self.estimated + self.excluded + self.missing
        if self.expected != total:
            raise ValueError(
                "expected must equal measured + estimated + excluded + missing: "
                f"{self.expected} != {total}"
            )

    def __add__(self, other: Coverage) -> Coverage:
        if not isinstance(other, Coverage):  # pyright: ignore[reportUnnecessaryIsInstance]
            return NotImplemented
        return Coverage(
            expected=self.expected + other.expected,
            measured=self.measured + other.measured,
            estimated=self.estimated + other.estimated,
            excluded=self.excluded + other.excluded,
            missing=self.missing + other.missing,
        )

    @classmethod
    def empty(cls) -> Coverage:
        return cls(expected=0, measured=0, estimated=0, excluded=0, missing=0)

    @property
    def status(self) -> DataStatus:
        if self.measured + self.estimated == 0:
            return DataStatus.MISSING
        if self.excluded + self.missing > 0:
            return DataStatus.PARTIAL
        if self.estimated > 0:
            return DataStatus.ESTIMATED
        return DataStatus.COMPLETE


@dataclass(frozen=True, slots=True)
class ZoneLabel:
    """A zone key + display name, as it appears in `Report.zones`."""

    key: str
    name: str


@dataclass(frozen=True, slots=True)
class ZoneCell:
    """One device/total row's numbers for one zone in one bucket.

    ``kwh``/``cost`` are ``None`` when there is no data at all for this cell (human
    decision: missing data is explicit, never a silent zero).
    """

    key: str
    kwh: Decimal | None
    cost: Decimal | None
    price: Decimal | None
    """The single price applied to this zone in this bucket.

    ``None`` if several prices applied (a plan switch inside the bucket) or the zone
    was not in force.
    """

    @property
    def effective_price(self) -> Decimal | None:
        if self.kwh is None or self.cost is None or self.kwh == 0:
            return None
        return self.cost / self.kwh


@dataclass(frozen=True, slots=True)
class Row:
    """A device row or the total row within one bucket."""

    device_id: str | None
    """``None`` marks the total row."""

    zones: tuple[ZoneCell, ...]
    """One cell per `Report.zones` entry, in the same order."""

    kwh: Decimal | None
    """All counted kWh (priced + unpriced, measured + estimated).

    ``None`` if missing.
    """

    cost: Decimal | None
    """Cost of priced kWh only. ``None`` if missing."""

    unpriced_kwh: Decimal
    estimated_kwh: Decimal
    excluded_kwh: Decimal
    """Not part of `kwh`."""

    coverage: Coverage

    @property
    def status(self) -> DataStatus:
        return self.coverage.status


@dataclass(frozen=True, slots=True)
class Bucket:
    """One time bucket of a report: a set of rows plus their total."""

    start: datetime
    end: datetime
    hours: int
    rows: tuple[Row, ...]
    """In input device order."""

    total: Row


class IssueKind(StrEnum):
    """The kind of data-quality issue recorded by task 007."""

    ESTIMATED = "estimated"
    EXCLUDED_NEGATIVE = "excluded_negative"
    EXCLUDED_SPIKE = "excluded_spike"


@dataclass(frozen=True, slots=True)
class QualityIssue:
    """A single data-quality issue, filled in by task 007."""

    kind: IssueKind
    device_id: str
    start: datetime
    end: datetime
    kwh: Decimal


@dataclass(frozen=True, slots=True)
class Report:
    """The full engine output for one `ReportRequest`."""

    request: ReportRequest
    zones: tuple[ZoneLabel, ...]
    plans: tuple[TariffPlan, ...]
    buckets: tuple[Bucket, ...]
    totals: Bucket
    unpriced_hours: int
    issues: tuple[QualityIssue, ...] = field(default_factory=tuple)


# Re-exported for callers that need the tariff types alongside the report types.
__all__ = [
    "Bucket",
    "Coverage",
    "DataStatus",
    "DeviceSeries",
    "Grouping",
    "IssueKind",
    "QualityIssue",
    "Report",
    "ReportRequest",
    "Row",
    "TariffPlan",
    "ZoneCell",
    "ZoneLabel",
]
