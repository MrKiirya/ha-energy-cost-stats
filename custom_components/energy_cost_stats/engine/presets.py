"""Tariff presets: single-rate and the RU two-/three-zone plans.

Key convention (human decision, 2026-09-25): zone keys follow RU meter registers —
``t0`` = single-rate (a distinct key, never mixed with the two-zone ``t1`` in multi-plan
reports), ``t1`` = day/peak, ``t2`` = night, ``t3`` = semi-peak.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from types import MappingProxyType

from .tariff import Period, TariffPlan, Zone


def single_rate(
    *, valid_from: date, price: Decimal, name: str = "Single-rate"
) -> TariffPlan:
    """A single flat rate for the whole day."""
    return TariffPlan(
        valid_from=valid_from,
        name=name,
        zones=(
            Zone(
                key="t0",
                name="Single-rate",
                price=price,
                periods=(Period(0, 24),),
            ),
        ),
    )


def ru_two_zone(
    *,
    valid_from: date,
    day_price: Decimal,
    night_price: Decimal,
    name: str = "Two-zone",
) -> TariffPlan:
    """The Russian residential two-zone tariff: day 07:00-23:00, night 23:00-07:00."""
    return TariffPlan(
        valid_from=valid_from,
        name=name,
        zones=(
            Zone(key="t1", name="Day", price=day_price, periods=(Period(7, 23),)),
            Zone(key="t2", name="Night", price=night_price, periods=(Period(23, 7),)),
        ),
    )


def ru_three_zone(
    *,
    valid_from: date,
    peak_price: Decimal,
    semi_peak_price: Decimal,
    night_price: Decimal,
    name: str = "Three-zone",
) -> TariffPlan:
    """The Russian residential three-zone tariff: peak, semi-peak and night hours."""
    return TariffPlan(
        valid_from=valid_from,
        name=name,
        zones=(
            Zone(
                key="t1",
                name="Peak",
                price=peak_price,
                periods=(Period(7, 10), Period(17, 21)),
            ),
            Zone(key="t2", name="Night", price=night_price, periods=(Period(23, 7),)),
            Zone(
                key="t3",
                name="Semi-peak",
                price=semi_peak_price,
                periods=(Period(10, 17), Period(21, 23)),
            ),
        ),
    )


@dataclass(frozen=True, slots=True)
class PresetZone:
    """One zone of a preset: stable key, default display name and default hours."""

    key: str
    name: str
    periods: tuple[Period, ...]


PRESET_ZONES: Mapping[str, tuple[PresetZone, ...]] = MappingProxyType(
    {
        "single_rate": (PresetZone("t0", "Single-rate", (Period(0, 24),)),),
        "ru_two_zone": (
            PresetZone("t1", "Day", (Period(7, 23),)),
            PresetZone("t2", "Night", (Period(23, 7),)),
        ),
        "ru_three_zone": (
            PresetZone("t1", "Peak", (Period(7, 10), Period(17, 21))),
            PresetZone("t2", "Night", (Period(23, 7),)),
            PresetZone("t3", "Semi-peak", (Period(10, 17), Period(21, 23))),
        ),
    }
)
