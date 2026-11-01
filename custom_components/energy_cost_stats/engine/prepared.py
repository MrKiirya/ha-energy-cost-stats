"""Prepared per-device series types shared by `report` and `quality`.

Pure Python, stdlib only (CLAUDE.md principle 4). Split out of `report.py` so the data
quality pre-pass (tasks/007-data-quality.md) can build them without importing `report`.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


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
