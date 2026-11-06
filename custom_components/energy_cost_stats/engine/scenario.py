"""Tariff comparison scenarios: one hypothetical plan priced over a whole window.

A scenario is a preset (its zone keys and default periods) with a price per zone and
optional period overrides, e.g. "what would this period cost on the three-zone tariff
at these prices?" (docs/SPEC.md §4.2, tasks/015-tariff-comparison.md). Pure Python
(CLAUDE.md principle 4).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from typing import Any, cast

from .plan_codec import parse_periods, parse_price
from .presets import ru_three_zone, ru_two_zone, single_rate
from .tariff import TariffPlan, TariffSchedule, TariffValidationError, Zone

PRESET_SINGLE_RATE = "single_rate"
PRESET_RU_TWO_ZONE = "ru_two_zone"
PRESET_RU_THREE_ZONE = "ru_three_zone"
SCENARIO_PRESETS = (PRESET_SINGLE_RATE, PRESET_RU_TWO_ZONE, PRESET_RU_THREE_ZONE)

MAX_SCENARIOS = 5

# A scenario applies to the whole window: any date before every statistics row.
_SCENARIO_VALID_FROM = date(1970, 1, 1)
_ZERO = Decimal(0)


def _preset_plan(preset: str) -> TariffPlan:
    """The preset with placeholder prices; zone keys and periods are what matter."""
    if preset == PRESET_SINGLE_RATE:
        return single_rate(valid_from=_SCENARIO_VALID_FROM, price=_ZERO)
    if preset == PRESET_RU_TWO_ZONE:
        return ru_two_zone(
            valid_from=_SCENARIO_VALID_FROM, day_price=_ZERO, night_price=_ZERO
        )
    if preset == PRESET_RU_THREE_ZONE:
        return ru_three_zone(
            valid_from=_SCENARIO_VALID_FROM,
            peak_price=_ZERO,
            semi_peak_price=_ZERO,
            night_price=_ZERO,
        )
    raise TariffValidationError(
        f"unknown preset {preset!r}; expected one of {list(SCENARIO_PRESETS)}"
    )


@dataclass(frozen=True, slots=True)
class Scenario:
    """A named hypothetical tariff plan."""

    name: str
    preset: str
    plan: TariffPlan

    @property
    def schedule(self) -> TariffSchedule:
        return TariffSchedule((self.plan,))


def scenario_from_data(data: Mapping[str, Any]) -> Scenario:
    """Parse ``{"preset", "prices": {key: "1.23"}, "periods"?: {key: "07:00-23:00"},
    "name"?}``. Raises `TariffValidationError` with a readable message."""
    unknown = set(data) - {"preset", "prices", "periods", "name"}
    if unknown:
        raise TariffValidationError(f"unknown scenario keys: {sorted(unknown)}")
    preset = data.get("preset")
    if not isinstance(preset, str):
        raise TariffValidationError("scenario preset is required")
    template = _preset_plan(preset)
    keys = [zone.key for zone in template.zones]

    raw_prices = data.get("prices")
    if not isinstance(raw_prices, Mapping):
        raise TariffValidationError("scenario prices must be a mapping zone -> price")
    prices = cast("Mapping[str, Any]", raw_prices)
    if set(prices) != set(keys):
        raise TariffValidationError(
            f"scenario prices must have exactly the zones {keys} of {preset}, "
            f"got {sorted(prices)}"
        )
    raw_periods: Any = data.get("periods")
    if raw_periods is None:
        raw_periods = {}
    if not isinstance(raw_periods, Mapping):
        raise TariffValidationError("scenario periods must be a mapping zone -> text")
    periods = cast("Mapping[str, Any]", raw_periods)
    extra = set(periods) - set(keys)
    if extra:
        raise TariffValidationError(
            f"scenario periods for unknown zones: {sorted(extra)}"
        )

    zones: list[Zone] = []
    for zone in template.zones:
        price_text = prices[zone.key]
        if not isinstance(price_text, str):
            raise TariffValidationError(f"price of {zone.key} must be a decimal string")
        try:
            price = parse_price(price_text)
        except (ValueError, ArithmeticError) as err:
            raise TariffValidationError(f"price of {zone.key}: {err}") from err
        zone_periods = zone.periods
        if zone.key in periods:
            text = periods[zone.key]
            if not isinstance(text, str):
                raise TariffValidationError(f"periods of {zone.key} must be text")
            try:
                zone_periods = parse_periods(text)
            except (ValueError, TariffValidationError) as err:
                raise TariffValidationError(f"periods of {zone.key}: {err}") from err
        zones.append(replace(zone, price=price, periods=zone_periods))

    name = data.get("name")
    if name is not None and (not isinstance(name, str) or not name.strip()):
        raise TariffValidationError("scenario name must be non-empty text")
    plan_name = name.strip() if isinstance(name, str) else template.name
    # TariffPlan validates coverage (every hour exactly once) on construction.
    plan = TariffPlan(
        valid_from=_SCENARIO_VALID_FROM, name=plan_name, zones=tuple(zones)
    )
    return Scenario(name=plan_name, preset=preset, plan=plan)
