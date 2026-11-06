"""Data-quality pre-pass: gap spreading and negative/spike exclusion.

Pure Python, stdlib only (CLAUDE.md principle 4). The rules (spans, spreading, rejected
deltas, issue clipping, window independence) are specified in
tasks/007-data-quality.md and docs/SPEC.md §5.
"""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, tzinfo
from decimal import ROUND_DOWN, Decimal, localcontext
from types import MappingProxyType

from .classify import HourInfo
from .models import DeviceSeries, IssueKind, QualityIssue
from .prepared import HourKind, HourValue, PreparedSeries

DEFAULT_SPIKE_LIMIT = Decimal("4")  # kWh per hour
SPREAD_QUANTUM = Decimal("1E-20")  # kWh

_HOUR = timedelta(hours=1)
_PRECISION = 50


def _check_limit(value: object, what: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, Decimal)
        or not value.is_finite()
        or value <= 0
    ):
        raise ValueError(f"{what} must be None or a finite Decimal > 0, got {value!r}")


@dataclass(frozen=True, slots=True)
class QualitySettings:
    """Spike limits in kWh per hour. ``None`` disables the check.

    The negative-delta check is not a setting and cannot be disabled.
    """

    spike_limit: Decimal | None = DEFAULT_SPIKE_LIMIT
    device_spike_limits: Mapping[str, Decimal | None] = field(
        default_factory=dict[str, Decimal | None]
    )
    """Per-device override; a ``None`` value disables the check for that device."""

    def __post_init__(self) -> None:
        if self.spike_limit is not None:
            _check_limit(self.spike_limit, "spike_limit")
        copied: dict[str, Decimal | None] = {}
        for key, value in self.device_spike_limits.items():
            if not isinstance(key, str) or not key:  # pyright: ignore[reportUnnecessaryIsInstance]
                raise ValueError(f"override key must be a non-empty str, got {key!r}")
            if value is not None:
                _check_limit(value, f"limit for {key}")
            copied[key] = value
        object.__setattr__(self, "device_spike_limits", MappingProxyType(copied))

    def limit_for(self, device_id: str) -> Decimal | None:
        """The limit that applies to ``device_id`` (override, else the global one)."""
        if device_id in self.device_spike_limits:
            return self.device_spike_limits[device_id]
        return self.spike_limit


def prepare_series(
    series: DeviceSeries,
    hours: Sequence[HourInfo],
    *,
    time_zone: tzinfo,
    settings: QualitySettings,
) -> tuple[PreparedSeries, tuple[QualityIssue, ...]]:
    """Apply the data-quality rules to one device over the classified ``hours``.

    O(K log K + H): only the overlap of each span with the window is materialized.
    """
    if not hours:
        raise ValueError("hours must not be empty")

    limit = settings.limit_for(series.device_id)
    window_start = hours[0].utc_start
    count = len(hours)

    keys = sorted(series.deltas)
    values: list[HourValue | None] = [None] * count
    issues: list[QualityIssue] = []

    def pos(moment: datetime) -> int:
        return (moment - window_start) // _HOUR

    def issue(kind: IssueKind, first: int, last: int, kwh: Decimal) -> None:
        issues.append(
            QualityIssue(
                kind=kind,
                device_id=series.device_id,
                start=hours[first].local_start,
                end=(hours[last].utc_start + _HOUR).astimezone(time_zone),
                kwh=kwh,
            )
        )

    with localcontext(prec=_PRECISION):
        # Keys before the window end before it starts: no overlap.
        for index in range(bisect_left(keys, window_start), len(keys)):
            key = keys[index]
            n = 1 if index == 0 else (key - keys[index - 1]) // _HOUR
            span_first = pos(key) - (n - 1)
            if span_first >= count:
                break
            delta = series.deltas[key]
            catch_up = pos(key)

            kind: IssueKind | None = None
            if delta < 0:
                kind = IssueKind.EXCLUDED_NEGATIVE
            elif limit is not None and delta > limit * n:
                kind = IssueKind.EXCLUDED_SPIKE
            if kind is not None:
                if catch_up < count:
                    values[catch_up] = HourValue(delta, HourKind.EXCLUDED)
                    issue(kind, catch_up, catch_up, delta)
                continue

            if n == 1:
                values[catch_up] = HourValue(delta, HourKind.MEASURED)
                continue

            share = (delta / n).quantize(SPREAD_QUANTUM, rounding=ROUND_DOWN)
            remainder = delta - (n - 1) * share
            first = max(span_first, 0)
            last = min(catch_up, count - 1)
            total = Decimal(0)
            for i in range(first, last + 1):
                amount = remainder if i == catch_up else share
                values[i] = HourValue(amount, HourKind.ESTIMATED)
                total += amount
            issue(IssueKind.ESTIMATED, first, last, total)

    return PreparedSeries(series.device_id, tuple(values)), tuple(issues)
