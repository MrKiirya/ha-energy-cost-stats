"""Recorder adapter: hourly ``change`` long-term statistics as engine series.

This is the only module that imports ``homeassistant.components.recorder``
(CLAUDE.md principle 5). The design is in tasks/011-recorder-adapter.md.

For every statistic id the adapter returns the in-window hourly keys plus the last key
before the window and the first key after it (however far away), so the engine's gap
rules give window-independent results. Rows with ``change is None`` are dropped.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from homeassistant.components.recorder.statistics import (
    get_metadata,
    statistics_during_period,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.recorder import get_instance
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import EnergyConverter

from .engine.models import DeviceSeries
from .engine.timeutil import to_utc_hour

NEAR = timedelta(days=1)
FAR = timedelta(days=31)
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)

# (start, sum, change, first): ``first`` marks the first non-null row of a query, whose
# ``change`` HA computes against a baseline that may be a NULL-sum row (so it can be the
# full cumulative sum).
_Rows = list[tuple[datetime, float, float, bool]]


class StatisticsStatus(StrEnum):
    """Whether a statistic id can be read as hourly energy."""

    OK = "ok"  # sum statistics in an energy unit
    NO_STATISTICS = "no_statistics"  # no metadata for this statistic id
    UNSUPPORTED = "unsupported"  # has_sum is not True, or the unit is not energy


@dataclass(frozen=True, slots=True)
class HourlySeries:
    """The result for one statistic id."""

    statistic_id: str
    status: StatisticsStatus
    series: DeviceSeries
    """``device_id == statistic_id``; empty deltas unless ``status`` is OK."""
    name: str | None
    """Metadata ``name`` (display fallback), ``None`` if absent."""


def classify_metadata(metadata: Mapping[str, Any]) -> StatisticsStatus:
    """Classify statistic metadata. Reads only ``has_sum`` and ``unit_of_measurement``;
    every other key (``mean_type``, ``unit_class``, ``has_mean``, ...) is ignored."""
    if (
        metadata.get("has_sum") is True
        and metadata.get("unit_of_measurement") in EnergyConverter.VALID_UNITS
    ):
        return StatisticsStatus.OK
    return StatisticsStatus.UNSUPPORTED


async def async_read_hourly_changes(
    hass: HomeAssistant,
    statistic_ids: Sequence[str],
    start: datetime,
    end: datetime,
) -> tuple[HourlySeries, ...]:
    """Read hourly kWh ``change`` series for ``statistic_ids`` over ``[start, end)``.

    Results keep input order. Raises ``ValueError`` for duplicate or empty ids, naive
    or off-hour bounds, and ``end <= start``. Recorder errors propagate.
    """
    ids = tuple(statistic_ids)
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate statistic ids")
    if any(not statistic_id for statistic_id in ids):
        raise ValueError("statistic id must not be empty")
    start = to_utc_hour(start)
    end = to_utc_hour(end)
    if end <= start:
        raise ValueError(f"end ({end}) must be after start ({start})")
    if not ids:
        return ()
    return await get_instance(hass).async_add_executor_job(_read, hass, ids, start, end)


def _query(
    hass: HomeAssistant,
    ids: set[str],
    start: datetime,
    end: datetime | None,
) -> dict[str, _Rows]:
    """One statistics query; rows with a NULL sum (``change is None``) are dropped."""
    raw = statistics_during_period(
        hass=hass,
        start_time=start,
        end_time=end,
        statistic_ids=ids,
        period="hour",
        units={"energy": "kWh"},
        types={"sum", "change"},
    )
    result: dict[str, _Rows] = {}
    for statistic_id, rows in raw.items():
        usable: _Rows = []
        for row in rows:
            row_start = row.get("start")
            change = row.get("change")
            total = row.get("sum")
            if row_start is None or change is None or total is None:
                continue
            usable.append(
                (datetime.fromtimestamp(row_start, UTC), total, change, not usable)
            )
        result[statistic_id] = usable
    return result


def _change(ordered: list[tuple[datetime, float, float, bool]], index: int) -> float:
    """The key's ``change``. Only the first non-null row of a query can have a bad HA
    baseline (a NULL-sum row taken as 0), so only that row is recomputed, against the
    previous fetched non-null row; every other row keeps HA's ``change``."""
    _, total, change, first = ordered[index]
    if first and index > 0:
        return total - ordered[index - 1][1]
    return change


def _read(
    hass: HomeAssistant,
    ids: tuple[str, ...],
    start: datetime,
    end: datetime,
) -> tuple[HourlySeries, ...]:
    metadata = get_metadata(hass, statistic_ids=set(ids))
    statuses: dict[str, StatisticsStatus] = {}
    names: dict[str, str | None] = {}
    for statistic_id in ids:
        entry = metadata.get(statistic_id)
        if entry is None:
            statuses[statistic_id] = StatisticsStatus.NO_STATISTICS
            names[statistic_id] = None
            continue
        meta: Mapping[str, Any] = entry[1]
        statuses[statistic_id] = classify_metadata(meta)
        name = meta.get("name")
        names[statistic_id] = name if isinstance(name, str) else None

    ok_ids = {i for i in ids if statuses[i] is StatisticsStatus.OK}
    fetched: dict[str, dict[datetime, tuple[datetime, float, float, bool]]] = {
        i: {} for i in ok_ids
    }
    has_before: set[str] = set()
    has_after: set[str] = set()

    def absorb(rows_by_id: dict[str, _Rows]) -> None:
        for statistic_id, rows in rows_by_id.items():
            for row in rows:
                fetched[statistic_id][row[0]] = row
                if row[0] < start:
                    has_before.add(statistic_id)
                elif row[0] >= end:
                    has_after.add(statistic_id)

    if ok_ids:
        absorb(_query(hass, ok_ids, start - NEAR, end + NEAR))

        for low, high in ((start - FAR, start - NEAR), (EPOCH, start - FAR)):
            need = ok_ids - has_before
            if not need:
                break
            absorb(_query(hass, need, low, high))

        now = dt_util.utcnow()
        for low, high in ((end + NEAR, end + FAR), (end + FAR, None)):
            need = ok_ids - has_after
            if not need or low > now:
                break
            absorb(_query(hass, need, low, high))

    results: list[HourlySeries] = []
    for statistic_id in ids:
        deltas: dict[datetime, float] = {}
        if statistic_id in ok_ids:
            ordered = sorted(fetched[statistic_id].values(), key=lambda row: row[0])
            # Keep the window keys plus the last key before and the first key after.
            before_idx = [i for i, row in enumerate(ordered) if row[0] < start]
            after_idx = [i for i, row in enumerate(ordered) if row[0] >= end]
            window_idx = [i for i, row in enumerate(ordered) if start <= row[0] < end]
            kept = before_idx[-1:] + window_idx + after_idx[:1]
            for index in kept:
                deltas[ordered[index][0]] = _change(ordered, index)
        results.append(
            HourlySeries(
                statistic_id=statistic_id,
                status=statuses[statistic_id],
                series=DeviceSeries.from_floats(statistic_id, deltas),
                name=names[statistic_id],
            )
        )
    return tuple(results)
