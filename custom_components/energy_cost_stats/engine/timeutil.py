"""UTC-hour and local-time helpers (tasks/005-time-and-zones.md).

Pure Python, stdlib only (CLAUDE.md principle 4). The engine's only notion of time is:
input is hourly energy deltas keyed by the **UTC start of the hour**; zones, plan
switches and groupings are derived from **local time** via `zoneinfo` (SPEC §5).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta, tzinfo

_HOUR = timedelta(hours=1)


def to_utc_hour(value: datetime) -> datetime:
    """Normalize an aware datetime that falls exactly on a UTC hour boundary.

    Returns the same instant with ``tzinfo=UTC``. Raises ``ValueError`` for naive
    datetimes and for any instant whose UTC representation is not on the hour
    (minute, second, microsecond all zero).
    """
    if value.tzinfo is None:
        raise ValueError(f"naive datetime not allowed: {value!r}")
    as_utc = value.astimezone(UTC)
    if (as_utc.minute, as_utc.second, as_utc.microsecond) != (0, 0, 0):
        raise ValueError(f"datetime is not on a UTC hour boundary: {value!r}")
    return as_utc


def iter_hours(start: datetime, end: datetime) -> Iterator[datetime]:
    """Yield the UTC hour starts in ``[start, end)``.

    ``start`` and ``end`` must already be normalized UTC hour starts (see
    ``to_utc_hour``); this function does not validate them.
    """
    current = start
    while current < end:
        yield current
        current += _HOUR


def local_day_start(day: date, tz: tzinfo) -> datetime:
    """The earliest UTC hour start whose local date (in ``tz``) is ``day``.

    Searches around a naive local-midnight guess (which may not exist, e.g. on a
    DST day whose switch happens at midnight) rather than trusting it directly.
    """
    guess = datetime.combine(day, datetime.min.time(), tz).astimezone(UTC)
    # Round down to a UTC hour boundary to search candidates on the hour grid.
    guess = guess.replace(minute=0, second=0, microsecond=0)

    # Search backward and forward a handful of hours (DST shifts are at most a
    # few hours) for the earliest UTC hour whose local date is `day`.
    candidates = [guess + timedelta(hours=offset) for offset in range(-26, 27)]
    matching = [
        candidate for candidate in candidates if candidate.astimezone(tz).date() == day
    ]
    if not matching:  # pragma: no cover - defensive; no known tz needs a wider search
        raise ValueError(f"could not locate local day start for {day} in {tz!r}")
    return min(matching)
