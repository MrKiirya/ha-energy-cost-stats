"""Sensor selection: which energy sensors a report covers (tasks/020-sensors.md).

Pure Python (CLAUDE.md principle 4). The integration layer describes every sensor as
a `Candidate` and the Energy dashboard devices as `DashboardDevice`; `select_sensors`
applies the stored `SensorSettings` and returns the ordered ids plus the dashboard's
parent map, `upstreams` derives the nesting for the ids of one report.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from fnmatch import fnmatchcase
from types import MappingProxyType

_LOGGER = logging.getLogger(__name__)
_GLOB_RE = re.compile(r"^[a-z0-9_.*?\[\]!-]+$")


def is_valid_glob(pattern: str) -> bool:
    """Whether ``pattern`` is an acceptable entity id glob."""
    return _GLOB_RE.match(pattern) is not None


class SensorMode(StrEnum):
    """How the sensors of a report are chosen."""

    ENERGY_DASHBOARD = "energy_dashboard"
    FILTER = "filter"


@dataclass(frozen=True, slots=True)
class SensorTarget:
    """A set of references; an entity matches when any of them applies."""

    entity_id: tuple[str, ...] = ()
    device_id: tuple[str, ...] = ()
    area_id: tuple[str, ...] = ()
    floor_id: tuple[str, ...] = ()
    label_id: tuple[str, ...] = ()
    entity_globs: tuple[str, ...] = ()

    @property
    def is_empty(self) -> bool:
        """True when nothing is referenced."""
        return not (
            self.entity_id
            or self.device_id
            or self.area_id
            or self.floor_id
            or self.label_id
            or self.entity_globs
        )

    def matches_id(self, entity_id: str) -> bool:
        """Match by entity id or glob only (needs no registry data)."""
        return entity_id in self.entity_id or any(
            fnmatchcase(entity_id, glob) for glob in self.entity_globs
        )

    def matches_attributes(self, candidate: Candidate) -> bool:
        """Match by device, area, floor or label of ``candidate``."""
        return bool(
            (candidate.device_id and candidate.device_id in self.device_id)
            or (candidate.area_id and candidate.area_id in self.area_id)
            or (candidate.floor_id and candidate.floor_id in self.floor_id)
            or candidate.labels.intersection(self.label_id)
        )


@dataclass(frozen=True, slots=True)
class SensorOverride:
    """Per-sensor settings; ``spike_limit=None`` disables the spike check."""

    spike_limit: Decimal | None


@dataclass(frozen=True, slots=True)
class SensorSettings:
    """The stored sensor selection.

    ``include`` is only meaningful in filter mode, where ``None`` means "all eligible
    sensors".
    """

    mode: SensorMode
    include: SensorTarget | None = None
    exclude: SensorTarget = field(default_factory=SensorTarget)
    overrides: Mapping[str, SensorOverride] = field(
        default_factory=dict[str, SensorOverride]
    )

    def __post_init__(self) -> None:
        """Make the overrides read-only."""
        object.__setattr__(self, "overrides", MappingProxyType(dict(self.overrides)))

    def spike_limits(self) -> Mapping[str, Decimal | None]:
        """Entity id -> spike limit (``None`` = no check), read-only."""
        return MappingProxyType(
            {key: item.spike_limit for key, item in self.overrides.items()}
        )


@dataclass(frozen=True, slots=True)
class Candidate:
    """What the selection needs to know about one sensor."""

    entity_id: str
    device_id: str | None = None
    area_id: str | None = None
    floor_id: str | None = None
    labels: frozenset[str] = frozenset()
    eligible: bool = True


@dataclass(frozen=True, slots=True)
class DashboardDevice:
    """An individual device of the Energy dashboard."""

    statistic_id: str
    included_in: str | None = None


@dataclass(frozen=True, slots=True)
class Selection:
    """The selected ids in report order and the dashboard parent map."""

    sensors: tuple[str, ...]
    parents: Mapping[str, str]


def _excluded(
    target: SensorTarget, entity_id: str, candidate: Candidate | None
) -> bool:
    if target.matches_id(entity_id):
        return True
    return candidate is not None and target.matches_attributes(candidate)


def select_sensors(
    settings: SensorSettings,
    candidates: Iterable[Candidate],
    dashboard: Sequence[DashboardDevice],
) -> Selection:
    """Resolve ``settings`` against the known sensors and the dashboard devices."""
    by_id = {candidate.entity_id: candidate for candidate in candidates}
    parents = {
        device.statistic_id: device.included_in
        for device in dashboard
        if device.included_in
    }
    chosen: list[str]
    if settings.mode is SensorMode.ENERGY_DASHBOARD:
        chosen = list(dict.fromkeys(device.statistic_id for device in dashboard))
    else:
        include = settings.include
        picked: set[str] = set()
        for entity_id, candidate in by_id.items():
            if not candidate.eligible:
                continue
            if (
                include is None
                or include.matches_id(entity_id)
                or include.matches_attributes(candidate)
            ):
                picked.add(entity_id)
        if include is not None:
            picked.update(include.entity_id)
        chosen = sorted(picked)
    sensors = tuple(
        entity_id
        for entity_id in chosen
        if not _excluded(settings.exclude, entity_id, by_id.get(entity_id))
    )
    return Selection(sensors=sensors, parents=MappingProxyType(parents))


def upstreams(ids: Collection[str], parents: Mapping[str, str]) -> dict[str, str]:
    """Nearest ancestor among ``ids`` for every id that has one.

    Members of a cycle in ``parents`` get no upstream.
    """
    wanted = set(ids)
    result: dict[str, str] = {}
    for entity_id in ids:
        seen = {entity_id}
        current = parents.get(entity_id)
        found: str | None = None
        cyclic = False
        while current is not None:
            if current == entity_id:
                cyclic = True
                break
            if current in seen:
                break
            seen.add(current)
            if found is None and current in wanted:
                found = current
            current = parents.get(current)
        if cyclic:
            _LOGGER.debug("included_in_stat cycle through %s; not nested", entity_id)
        if found is not None and not cyclic:
            result[entity_id] = found
    return result
