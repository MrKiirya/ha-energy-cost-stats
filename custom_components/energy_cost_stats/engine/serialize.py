"""Report -> JSON-ready ``dict``, the stage 4 card's contract.

See tasks/012-report-serializer.md. Pure Python, stdlib and relative imports only
(CLAUDE.md principle 4). This is the only place where the engine's exact ``Decimal``
values are rounded (`rounding.py`). The document shape, versioning rule and number
format are specified in docs/SPEC.md §4 ("JSON contract"). The output has only
``dict``, ``list``, ``str``, ``int`` and ``None``, so ``json.dumps`` works without a
custom encoder.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from .models import Bucket, Grouping, QualityIssue, Report, Row, ZoneCell
from .plan_codec import plan_to_data
from .rounding import round_kwh, round_money, round_price

SCHEMA_VERSION = 1

_HOUR = timedelta(hours=1)


@dataclass(frozen=True, slots=True)
class DeviceInfo:
    """Per-device metadata supplied by the integration (names, adapter status)."""

    device_id: str
    name: str
    statistics: str
    """Adapter status value, e.g. ``"ok"``, ``"no_statistics"``, ``"unsupported"``."""


def _num(value: Decimal | None, rounder: Callable[[Decimal], Decimal]) -> str | None:
    """Round and format as a plain decimal string; ``None`` stays ``None``."""
    if value is None:
        return None
    return format(rounder(value), "f")


def _req(value: Decimal, rounder: Callable[[Decimal], Decimal]) -> str:
    return format(rounder(value), "f")


def _cell(cell: ZoneCell) -> dict[str, Any]:
    return {
        "key": cell.key,
        "kwh": _num(cell.kwh, round_kwh),
        "cost": _num(cell.cost, round_money),
        "price": _num(cell.price, round_price),
    }


def _row(row: Row) -> dict[str, Any]:
    cov = row.coverage
    return {
        "entity_id": row.device_id,
        "kwh": _num(row.kwh, round_kwh),
        "cost": _num(row.cost, round_money),
        "unpriced_kwh": _req(row.unpriced_kwh, round_kwh),
        "estimated_kwh": _req(row.estimated_kwh, round_kwh),
        "excluded_kwh": _req(row.excluded_kwh, round_kwh),
        "status": row.status.value,
        "coverage": {
            "expected": cov.expected,
            "measured": cov.measured,
            "estimated": cov.estimated,
            "excluded": cov.excluded,
            "missing": cov.missing,
        },
        "zones": [_cell(c) for c in row.zones],
    }


def _bucket(bucket: Bucket) -> dict[str, Any]:
    return {
        "start": bucket.start.isoformat(),
        "end": bucket.end.isoformat(),
        "hours": bucket.hours,
        "rows": [_row(r) for r in bucket.rows],
        "total": _row(bucket.total),
    }


def _elapsed_hours(start: datetime, end: datetime) -> int:
    """Real elapsed hours; subtract in UTC, since same-zone aware datetimes would be
    subtracted by wall clock (wrong across DST transitions)."""
    hours, remainder = divmod(end.astimezone(UTC) - start.astimezone(UTC), _HOUR)
    if remainder:
        raise ValueError(f"span {start}..{end} is not a whole number of hours")
    return hours


def _issue(issue: QualityIssue) -> dict[str, Any]:
    return {
        "kind": issue.kind.value,
        "entity_id": issue.device_id,
        "start": issue.start.isoformat(),
        "end": issue.end.isoformat(),
        "hours": _elapsed_hours(issue.start, issue.end),
        "kwh": _req(issue.kwh, round_kwh),
    }


def report_to_json(
    report: Report,
    *,
    devices: Sequence[DeviceInfo],
    time_zone: str,
    currency: str | None,
) -> dict[str, Any]:
    """Serialize ``report`` to the versioned JSON document (SPEC §4).

    ``devices`` must list the report's devices in row order; ``ValueError`` otherwise
    or if ``time_zone`` is empty. The report itself is never modified: rounding only
    touches the output copy.
    """
    if not time_zone:
        raise ValueError("time_zone must not be empty")
    expected = [r.device_id for r in report.totals.rows]
    if [d.device_id for d in devices] != expected:
        raise ValueError(
            f"devices {[d.device_id for d in devices]} do not match "
            f"report rows {expected}"
        )

    tz = report.request.time_zone
    start: datetime = report.request.start.astimezone(tz)
    end: datetime = report.request.end.astimezone(tz)
    return {
        "schema_version": SCHEMA_VERSION,
        "time_zone": time_zone,
        "currency": currency,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "grouping": Grouping(report.request.grouping).value,
        "zones": [{"key": z.key, "name": z.name} for z in report.zones],
        "plans": [plan_to_data(p) for p in report.plans],
        "devices": [
            {"entity_id": d.device_id, "name": d.name, "statistics": d.statistics}
            for d in devices
        ],
        "buckets": [_bucket(b) for b in report.buckets],
        "totals": _bucket(report.totals),
        "unpriced_hours": report.unpriced_hours,
        "issues": [_issue(i) for i in report.issues],
    }
