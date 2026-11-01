"""Pricing and grouping: hourly deltas + schedule -> full ``Report``.

Pure Python, stdlib only (CLAUDE.md principle 4). The rules implemented here (cell and
row semantics, zone union, ``None`` vs ``0``, exactness) are specified in
tasks/006-pricing-and-grouping.md and docs/SPEC.md §4.

Pipeline: classify the window once -> prepare each device (task 007 replaces
`prepare_measured` with its quality pre-pass) -> `assemble_report`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, localcontext
from enum import StrEnum

from . import classify as _classify
from .models import (
    Bucket,
    Coverage,
    DeviceSeries,
    Grouping,
    QualityIssue,
    Report,
    ReportRequest,
    Row,
    ZoneCell,
    ZoneLabel,
)
from .tariff import TariffPlan, TariffSchedule

_HOUR = timedelta(hours=1)
_PRECISION = 50


class HourKind(StrEnum):
    """How an hour's kWh value came about."""

    MEASURED = "measured"
    ESTIMATED = "estimated"
    EXCLUDED = "excluded"


@dataclass(frozen=True, slots=True)
class HourValue:
    """One device-hour's kWh and its kind."""

    kwh: Decimal
    kind: HourKind


@dataclass(frozen=True, slots=True)
class PreparedSeries:
    """A device's values aligned to the classified hours: ``values[i]`` is for
    ``hours[i]``; ``None`` means missing."""

    device_id: str
    values: tuple[HourValue | None, ...]


def prepare_measured(
    series: DeviceSeries, hours: Sequence[_classify.HourInfo]
) -> PreparedSeries:
    """Every window hour present in ``series`` becomes MEASURED, absent ones ``None``.

    Keys outside the window are ignored (task 007 uses them as look-back).
    """
    values: list[HourValue | None] = []
    for info in hours:
        delta = series.deltas.get(info.utc_start)
        values.append(None if delta is None else HourValue(delta, HourKind.MEASURED))
    return PreparedSeries(device_id=series.device_id, values=tuple(values))


class _Acc:
    """Per device x bucket accumulator."""

    __slots__ = (
        "counted",
        "estimated",
        "estimated_kwh",
        "excluded",
        "excluded_kwh",
        "kwh",
        "measured",
        "missing",
        "unpriced_kwh",
        "zone_cost",
        "zone_kwh",
    )

    def __init__(self) -> None:
        self.counted = 0
        self.measured = 0
        self.estimated = 0
        self.excluded = 0
        self.missing = 0
        self.kwh = Decimal(0)
        self.unpriced_kwh = Decimal(0)
        self.estimated_kwh = Decimal(0)
        self.excluded_kwh = Decimal(0)
        self.zone_kwh: dict[str, Decimal] = {}
        self.zone_cost: dict[str, Decimal] = {}


def _zero() -> Decimal:
    return Decimal(0)


def assemble_report(
    request: ReportRequest,
    hours: Sequence[_classify.HourInfo],
    prepared: Sequence[PreparedSeries],
    issues: Sequence[QualityIssue] = (),
) -> Report:
    """Pure aggregation of classified hours and prepared series into a `Report`."""
    if not hours:
        raise ValueError("hours must not be empty")
    seen: set[str] = set()
    for series in prepared:
        if len(series.values) != len(hours):
            raise ValueError(
                f"{series.device_id}: {len(series.values)} values for "
                f"{len(hours)} hours"
            )
        if series.device_id in seen:
            raise ValueError(f"duplicate device_id: {series.device_id}")
        seen.add(series.device_id)

    with localcontext(prec=_PRECISION):
        return _assemble(request, hours, prepared, tuple(issues))


def _assemble(
    request: ReportRequest,
    hours: Sequence[_classify.HourInfo],
    prepared: Sequence[PreparedSeries],
    issues: tuple[QualityIssue, ...],
) -> Report:
    grouping = Grouping(request.grouping)
    tz = request.time_zone

    # Plans in force and the zone union (decision 8).
    plans: list[TariffPlan] = []
    unpriced_hours = 0
    for info in hours:
        if info.plan is None:
            unpriced_hours += 1
        elif not plans or plans[-1] is not info.plan:
            plans.append(info.plan)
    names: dict[str, str] = {}
    for plan in plans:
        for zone in plan.zones:
            names[zone.key] = zone.name
    zone_labels = tuple(ZoneLabel(key, name) for key, name in names.items())
    zone_keys = tuple(names)

    # Bucket assignment, once per hour. Slot n_buckets is the whole-window bucket.
    bucket_index: dict[_classify.BucketKey, int] = {}
    bucket_of: list[int] = []
    first_hour: list[int] = []
    last_hour: list[int] = []
    for i, info in enumerate(hours):
        key = _classify.bucket_key(info, grouping)
        idx = bucket_index.get(key)
        if idx is None:
            idx = len(first_hour)
            bucket_index[key] = idx
            first_hour.append(i)
            last_hour.append(i)
        else:
            last_hour[idx] = i
        bucket_of.append(idx)
    n_buckets = len(first_hour)
    n_slots = n_buckets + 1
    total_slot = n_buckets

    # Per slot x zone price; None marks differing prices (decision 9).
    slot_prices: list[dict[str, Decimal | None]] = [{} for _ in range(n_slots)]
    for i, info in enumerate(hours):
        if info.zone is None:
            continue
        for slot in (bucket_of[i], total_slot):
            prices = slot_prices[slot]
            current = prices.get(info.zone.key, info.zone.price)
            prices[info.zone.key] = (
                current if current is not None and current == info.zone.price else None
            )

    zone_of = [None if info.zone is None else info.zone.key for info in hours]
    price_of = [None if info.zone is None else info.zone.price for info in hours]

    # Single aggregation pass: O(devices x hours).
    accs: list[list[_Acc]] = []
    for series in prepared:
        per_slot = [_Acc() for _ in range(n_slots)]
        for i, value in enumerate(series.values):
            targets = (per_slot[bucket_of[i]], per_slot[total_slot])
            if value is None:
                for acc in targets:
                    acc.missing += 1
                continue
            if value.kind is HourKind.EXCLUDED:
                for acc in targets:
                    acc.excluded += 1
                    acc.excluded_kwh += value.kwh
                continue
            zone_key = zone_of[i]
            price = price_of[i]
            for acc in targets:
                acc.counted += 1
                acc.kwh += value.kwh
                if value.kind is HourKind.ESTIMATED:
                    acc.estimated += 1
                    acc.estimated_kwh += value.kwh
                else:
                    acc.measured += 1
                if zone_key is None or price is None:
                    acc.unpriced_kwh += value.kwh
                else:
                    acc.zone_kwh[zone_key] = (
                        acc.zone_kwh.get(zone_key, _zero()) + value.kwh
                    )
                    acc.zone_cost[zone_key] = (
                        acc.zone_cost.get(zone_key, _zero()) + value.kwh * price
                    )
        accs.append(per_slot)

    def device_row(device_id: str, acc: _Acc, slot: int, expected: int) -> Row:
        prices = slot_prices[slot]
        zone_cells = tuple(
            ZoneCell(
                key=key,
                kwh=acc.zone_kwh.get(key),
                cost=acc.zone_cost.get(key),
                price=prices.get(key),
            )
            for key in zone_keys
        )
        return Row(
            device_id=device_id,
            zones=zone_cells,
            kwh=acc.kwh if acc.counted else None,
            cost=sum(acc.zone_cost.values(), _zero()) if acc.zone_cost else None,
            unpriced_kwh=acc.unpriced_kwh,
            estimated_kwh=acc.estimated_kwh,
            excluded_kwh=acc.excluded_kwh,
            coverage=Coverage(
                expected=expected,
                measured=acc.measured,
                estimated=acc.estimated,
                excluded=acc.excluded,
                missing=acc.missing,
            ),
        )

    def sum_optional(values: Sequence[Decimal | None]) -> Decimal | None:
        present = [v for v in values if v is not None]
        return sum(present, _zero()) if present else None

    def total_row(rows: tuple[Row, ...], slot: int) -> Row:
        prices = slot_prices[slot]
        zone_cells = tuple(
            ZoneCell(
                key=key,
                kwh=sum_optional([r.zones[j].kwh for r in rows]),
                cost=sum_optional([r.zones[j].cost for r in rows]),
                price=prices.get(key),
            )
            for j, key in enumerate(zone_keys)
        )
        coverage = Coverage.empty()
        for r in rows:
            coverage = coverage + r.coverage
        return Row(
            device_id=None,
            zones=zone_cells,
            kwh=sum_optional([r.kwh for r in rows]),
            cost=sum_optional([r.cost for r in rows]),
            unpriced_kwh=sum((r.unpriced_kwh for r in rows), _zero()),
            estimated_kwh=sum((r.estimated_kwh for r in rows), _zero()),
            excluded_kwh=sum((r.excluded_kwh for r in rows), _zero()),
            coverage=coverage,
        )

    def make_bucket(slot: int, first: int, last: int) -> Bucket:
        count = last - first + 1
        rows = tuple(
            device_row(series.device_id, accs[d][slot], slot, count)
            for d, series in enumerate(prepared)
        )
        return Bucket(
            start=hours[first].local_start,
            end=(hours[last].utc_start + _HOUR).astimezone(tz),
            hours=count,
            rows=rows,
            total=total_row(rows, slot),
        )

    totals = make_bucket(total_slot, 0, len(hours) - 1)
    if grouping is Grouping.TOTAL:
        buckets = (totals,)
    else:
        buckets = tuple(
            make_bucket(slot, first_hour[slot], last_hour[slot])
            for slot in range(n_buckets)
        )

    return Report(
        request=request,
        zones=zone_labels,
        plans=tuple(plans),
        buckets=buckets,
        totals=totals,
        unpriced_hours=unpriced_hours,
        issues=issues,
    )


def build_report(
    request: ReportRequest,
    schedule: TariffSchedule,
    devices: Sequence[DeviceSeries],
) -> Report:
    """Build the full report for ``request`` from ``schedule`` and ``devices``.

    Every hour is re-priced from the schedule on each call (CLAUDE.md principle 3).
    """
    seen: set[str] = set()
    for device in devices:
        if device.device_id in seen:
            raise ValueError(f"duplicate device_id: {device.device_id}")
        seen.add(device.device_id)

    hours = _classify.classify_hours(
        schedule, request.start, request.end, request.time_zone
    )
    prepared = [prepare_measured(device, hours) for device in devices]
    return assemble_report(request, hours, prepared)
