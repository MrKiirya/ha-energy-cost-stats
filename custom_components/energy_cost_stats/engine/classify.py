"""UTC hour -> local plan/zone/bucket classification (tasks/005-time-and-zones.md).

Pure Python, stdlib only (CLAUDE.md principle 4). ``classify_hours`` is computed once
per report and shared by every device (see the performance note in the task file):
callers must not call `TariffPlan.zone_for_hour` per device x hour.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, tzinfo

from .models import Grouping
from .tariff import TariffPlan, TariffSchedule, Zone
from .timeutil import iter_hours, to_utc_hour

BucketKey = datetime | date | None


@dataclass(frozen=True, slots=True)
class HourInfo:
    """One UTC hour's local start, tariff plan and zone.

    ``plan``/``zone`` are ``None`` for hours before the schedule's first plan.
    """

    utc_start: datetime
    local_start: datetime
    plan: TariffPlan | None
    zone: Zone | None


def classify_hours(
    schedule: TariffSchedule, start: datetime, end: datetime, tz: tzinfo
) -> tuple[HourInfo, ...]:
    """Classify every UTC hour in ``[start, end)`` by local plan and zone.

    Every UTC hour ``h`` is attributed by its local start ``h.astimezone(tz)``: the
    plan is ``schedule.plan_for(local_start.date())`` and the zone is
    ``plan.zone_for_hour(local_start.hour)``. This single rule handles plan switches
    at local midnight, zones crossing midnight, and DST (see the task file's design
    notes); the engine never constructs a local midnight as a bound.

    Known limitation (SPEC §5): for time zones with a non-whole-hour UTC offset
    (e.g. ``Asia/Kolkata``, UTC+05:30), every UTC hour's local start falls on
    ``xx:30`` rather than ``xx:00``, so the local date and every zone/plan
    boundary shift by that remainder. This is accepted, not rejected.
    """
    utc_start = to_utc_hour(start)
    utc_end = to_utc_hour(end)
    if utc_end <= utc_start:
        raise ValueError(f"end ({utc_end}) must be after start ({utc_start})")

    # Build each plan's 24-entry hour lookup once per report, not per hour: avoids
    # rebuilding TariffPlan.zone_for_hour's internal lookup for every hour classified
    # (004 review performance note).
    plan_zone_lookups: dict[int, tuple[Zone, ...]] = {}

    infos: list[HourInfo] = []
    for hour in iter_hours(utc_start, utc_end):
        local_start = hour.astimezone(tz)
        plan = schedule.plan_for(local_start.date())
        zone: Zone | None = None
        if plan is not None:
            plan_id = id(plan)
            lookup = plan_zone_lookups.get(plan_id)
            if lookup is None:
                lookup = tuple(plan.zone_for_hour(h) for h in range(24))
                plan_zone_lookups[plan_id] = lookup
            zone = lookup[local_start.hour]
        infos.append(
            HourInfo(utc_start=hour, local_start=local_start, plan=plan, zone=zone)
        )
    return tuple(infos)


def bucket_key(info: HourInfo, grouping: Grouping) -> BucketKey:
    """The report bucket a classified hour belongs to, for the given grouping."""
    if grouping is Grouping.HOUR:
        return info.utc_start
    if grouping is Grouping.TOTAL:
        return None
    local_date = info.local_start.date()
    if grouping is Grouping.DAY:
        return local_date
    if grouping is Grouping.WEEK:
        return local_date - timedelta(days=local_date.weekday())
    if grouping is Grouping.MONTH:
        return local_date.replace(day=1)
    raise ValueError(f"unknown grouping: {grouping!r}")  # pragma: no cover
