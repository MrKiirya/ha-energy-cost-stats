"""Tariff data model: versioned plans -> zones -> whole-hour periods.

Pure Python, stdlib only (CLAUDE.md principle 4). See tasks/004-tariff-model.md and
docs/SPEC.md §3 for the data model and the human decisions this module implements:

- Zone keys follow RU meter registers: ``t0`` = single-rate, ``t1`` = day/peak,
  ``t2`` = night, ``t3`` = semi-peak (not time-of-day order).
- Prices are ``Decimal`` and must be >= 0 (0 = free hours is allowed).
- Volume tiers (``band_prices`` / ``volume_band_limits_kwh``) are reserved fields only:
  the engine uses the first-band price (``Zone.price``) everywhere in stage 1.
"""

from __future__ import annotations

import re
from bisect import bisect_right
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

_KEY_RE = re.compile(r"[a-z0-9_]{1,32}")
_HHMM_RE = re.compile(r"([0-9]{2}):([0-9]{2})")


class TariffValidationError(ValueError):
    """Raised when a tariff model object fails validation."""


@dataclass(frozen=True, slots=True)
class Period:
    """A half-open local-hour interval ``[start_hour, end_hour)``.

    ``end_hour < start_hour`` means the period crosses midnight, e.g. ``Period(23, 7)``
    covers hours 23, 0, 1, ..., 6. The full day is ``Period(0, 24)``.
    """

    start_hour: int
    end_hour: int

    def __post_init__(self) -> None:
        fields = (("start_hour", self.start_hour), ("end_hour", self.end_hour))
        for name, value in fields:
            if isinstance(value, bool) or not isinstance(value, int):  # pyright: ignore[reportUnnecessaryIsInstance]
                raise TariffValidationError(f"{name} must be an int, got {value!r}")
        if not (0 <= self.start_hour <= 23):
            raise TariffValidationError(
                f"start_hour must be in 0..23, got {self.start_hour}"
            )
        if not (1 <= self.end_hour <= 24):
            raise TariffValidationError(
                f"end_hour must be in 1..24, got {self.end_hour}"
            )
        if self.start_hour == self.end_hour:
            raise TariffValidationError("start_hour and end_hour must differ")

    def hours(self) -> tuple[int, ...]:
        """Hours covered by this period, in wall-clock order starting at start_hour."""
        if self.end_hour > self.start_hour:
            return tuple(range(self.start_hour, self.end_hour))
        return tuple(range(self.start_hour, 24)) + tuple(range(0, self.end_hour))

    @staticmethod
    def parse(start: str, end: str) -> Period:
        """Parse ``"HH:MM"`` strings as in the SPEC §3 JSON.

        Minutes must be ``"00"`` (whole hours only, hourly statistics limit).
        ``"00:00"`` or ``"24:00"`` as ``end`` means 24 (end of day). ``"24:00"`` as
        ``start`` is invalid.
        """
        start_hour = Period._parse_hhmm(start, allow_24=False)
        end_hour = Period._parse_hhmm(end, allow_24=True)
        if end_hour == 0:
            end_hour = 24
        return Period(start_hour, end_hour)

    @staticmethod
    def _parse_hhmm(value: str, *, allow_24: bool) -> int:
        match = _HHMM_RE.fullmatch(value)
        if match is None:
            raise TariffValidationError(f"invalid HH:MM string: {value!r}")
        hour_str, minute_str = match.groups()
        if minute_str != "00":
            raise TariffValidationError(f"minutes must be '00', got {value!r}")
        hour = int(hour_str)
        max_hour = 24 if allow_24 else 23
        if not (0 <= hour <= max_hour):
            raise TariffValidationError(f"hour out of range in {value!r}")
        return hour


@dataclass(frozen=True, slots=True)
class Zone:
    """A tariff zone: a stable key, a display name, a price and covered periods.

    ``band_prices`` is reserved for future volume-tier pricing (SPEC §3 decision 4);
    the engine ignores it in stage 1.
    """

    key: str
    name: str
    price: Decimal
    periods: tuple[Period, ...]
    band_prices: tuple[Decimal, ...] = ()

    def __post_init__(self) -> None:
        if not _KEY_RE.fullmatch(self.key):
            raise TariffValidationError(
                f"zone key must match ^[a-z0-9_]{{1,32}}$, got {self.key!r}"
            )
        if not self.name.strip():
            raise TariffValidationError("zone name must not be blank")
        _validate_price(self.price, label="zone price")
        if not self.periods:
            raise TariffValidationError(f"zone {self.key!r} has no periods")
        for band_price in self.band_prices:
            _validate_price(band_price, label=f"zone {self.key!r} band price")


def _validate_price(price: Decimal, *, label: str) -> None:
    if not isinstance(price, Decimal):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise TariffValidationError(
            f"{label} must be a Decimal, got {type(price).__name__}"
        )
    if not price.is_finite():
        raise TariffValidationError(f"{label} must be finite, got {price}")
    if price < 0:
        raise TariffValidationError(f"{label} must be >= 0, got {price}")


def _validate_volume_limit(limit: Decimal) -> None:
    if not isinstance(limit, Decimal):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise TariffValidationError(
            "volume_band_limits_kwh entries must be a Decimal, "
            f"got {type(limit).__name__}"
        )
    if not limit.is_finite():
        raise TariffValidationError(
            f"volume_band_limits_kwh entries must be finite, got {limit}"
        )
    if limit <= 0:
        raise TariffValidationError(
            f"volume_band_limits_kwh entries must be > 0, got {limit}"
        )


def _build_hour_lookup(zones: tuple[Zone, ...]) -> tuple[Zone, ...]:
    """Build a 24-entry hour-to-zone lookup for already-validated zones.

    Computed outside the ``TariffPlan`` dataclass (not stored as a field) so it
    never leaks through ``dataclasses.asdict()``/``repr()``/equality. Callers get
    fresh, already-validated coverage, so this is cheap (24 hours, a handful of
    zones/periods) and does not need caching.
    """
    lookup: list[Zone] = [zones[0]] * 24
    for zone in zones:
        for period in zone.periods:
            for hour in period.hours():
                lookup[hour] = zone
    return tuple(lookup)


@dataclass(frozen=True, slots=True)
class TariffPlan:
    """A versioned tariff plan: zones covering every local-day hour exactly once."""

    valid_from: date
    name: str
    zones: tuple[Zone, ...]
    volume_band_limits_kwh: tuple[Decimal, ...] = ()

    def __post_init__(self) -> None:
        if not self.zones:
            raise TariffValidationError("plan must have at least one zone")

        keys = [zone.key for zone in self.zones]
        seen: set[str] = set()
        for key in keys:
            if key in seen:
                raise TariffValidationError(f"duplicate zone key: {key}")
            seen.add(key)

        hour_owner: dict[int, list[str]] = {}
        for zone in self.zones:
            for period in zone.periods:
                for hour in period.hours():
                    hour_owner.setdefault(hour, []).append(zone.key)

        overlaps = {
            hour: owners for hour, owners in hour_owner.items() if len(owners) > 1
        }
        if overlaps:
            hour = min(overlaps)
            owners = overlaps[hour]
            raise TariffValidationError(
                f"hour {hour} covered by zones {' and '.join(owners)}"
            )

        missing = sorted(set(range(24)) - hour_owner.keys())
        if missing:
            raise TariffValidationError(
                f"hours not covered: {', '.join(str(h) for h in missing)}"
            )

        self._validate_volume_bands()

    def _validate_volume_bands(self) -> None:
        limits = self.volume_band_limits_kwh
        if limits:
            previous: Decimal | None = None
            for limit in limits:
                _validate_volume_limit(limit)
                if previous is not None and limit <= previous:
                    raise TariffValidationError(
                        "volume_band_limits_kwh must be strictly increasing, "
                        f"got {limits}"
                    )
                previous = limit

        for zone in self.zones:
            if not limits:
                if zone.band_prices:
                    raise TariffValidationError(
                        f"zone {zone.key!r} has band_prices but "
                        "volume_band_limits_kwh is empty"
                    )
            elif len(zone.band_prices) != len(limits):
                raise TariffValidationError(
                    f"zone {zone.key!r} has {len(zone.band_prices)} band_prices, "
                    f"expected {len(limits)}"
                )

    def zone_for_hour(self, hour: int) -> Zone:
        """The zone covering the given local hour (0..23)."""
        if not (0 <= hour <= 23):
            raise ValueError(f"hour must be in 0..23, got {hour}")
        return _build_hour_lookup(self.zones)[hour]

    def zone_keys(self) -> tuple[str, ...]:
        """Zone keys in declaration order."""
        return tuple(zone.key for zone in self.zones)


@dataclass(frozen=True, slots=True)
class TariffSchedule:
    """An ordered set of tariff plans, each with a distinct ``valid_from`` date."""

    plans: tuple[TariffPlan, ...]

    def __post_init__(self) -> None:
        if not self.plans:
            raise TariffValidationError("schedule must have at least one plan")

        valid_from_dates = [plan.valid_from for plan in self.plans]
        if len(set(valid_from_dates)) != len(valid_from_dates):
            raise TariffValidationError("duplicate valid_from date among plans")

        sorted_plans = tuple(sorted(self.plans, key=lambda plan: plan.valid_from))
        object.__setattr__(self, "plans", sorted_plans)

    def plan_for(self, local_date: date) -> TariffPlan | None:
        """The latest plan with ``valid_from <= local_date``.

        Returns ``None`` before the first plan.
        """
        valid_from_dates = [plan.valid_from for plan in self.plans]
        index = bisect_right(valid_from_dates, local_date) - 1
        if index < 0:
            return None
        return self.plans[index]

    def plans_between(self, start: date, end: date) -> tuple[TariffPlan, ...]:
        """Plans in effect on at least one local date in ``[start, end)``, in order."""
        if start >= end:
            return ()
        result: list[TariffPlan] = []
        for index, plan in enumerate(self.plans):
            plan_end = (
                self.plans[index + 1].valid_from
                if index + 1 < len(self.plans)
                else None
            )
            if plan.valid_from >= end:
                break
            if plan_end is not None and plan_end <= start:
                continue
            result.append(plan)
        return tuple(result)
