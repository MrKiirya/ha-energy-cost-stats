"""Codec between tariff plans and their JSON storage form, plus form-text parsers.

Pure Python, stdlib only (CLAUDE.md principle 4). Implements D-1 and D-2 of
tasks/010-tariff-plan-subentries.md:

- Prices are stored as decimal strings (scale kept, never exponent notation), so money
  never passes through ``float``.
- Reading storage is strict: unknown keys, wrong JSON types and bad dates raise
  ``TariffValidationError``.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from .tariff import Period, TariffPlan, TariffValidationError, Zone

# Upper bound for a price or volume limit (sanity range).
MAX_PRICE = Decimal("1000000")

_PRICE_RE = re.compile(r"[0-9]+(?:[.,][0-9]+)?", re.ASCII)
_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", re.ASCII)

_PLAN_KEYS = frozenset({"valid_from", "name", "zones", "volume_band_limits_kwh"})
_PLAN_REQUIRED = frozenset({"valid_from", "name", "zones"})
_ZONE_KEYS = frozenset({"key", "name", "price", "periods", "band_prices"})
_ZONE_REQUIRED = frozenset({"key", "name", "price", "periods"})


def parse_price(text: str) -> Decimal:
    """Parse a typed price: digits with an optional ``.`` or ``,`` decimal part."""
    stripped = text.strip()
    if _PRICE_RE.fullmatch(stripped) is None:
        raise TariffValidationError(f"invalid price: {text!r}")
    value = Decimal(stripped.replace(",", "."))
    if value > MAX_PRICE:
        raise TariffValidationError(f"price too large: {text!r}")
    return value


def _format_hour(hour: int) -> str:
    return f"{hour:02d}:00"


def format_periods(periods: Sequence[Period]) -> str:
    """Format periods as ``"07:00-10:00, 17:00-21:00"`` (end of day is ``24:00``)."""
    return ", ".join(
        f"{_format_hour(period.start_hour)}-{_format_hour(period.end_hour)}"
        for period in periods
    )


def parse_periods(text: str) -> tuple[Period, ...]:
    """Parse comma- or semicolon-separated ``HH:MM-HH:MM`` items."""
    compact = re.sub(r"\s+", "", text).replace("\u2013", "-")
    periods: list[Period] = []
    for item in re.split(r"[,;]", compact):
        parts = item.split("-")
        if len(parts) != 2:
            raise TariffValidationError(f"invalid period: {item!r}")
        periods.append(Period.parse(parts[0], parts[1]))
    return tuple(periods)


def _format_price(price: Decimal) -> str:
    return format(price, "f")


def plan_to_data(plan: TariffPlan) -> dict[str, Any]:
    """Serialize a plan to JSON-compatible data (SPEC §3)."""
    zones: list[dict[str, Any]] = []
    for zone in plan.zones:
        zone_data: dict[str, Any] = {
            "key": zone.key,
            "name": zone.name,
            "price": _format_price(zone.price),
            "periods": [
                [_format_hour(period.start_hour), _format_hour(period.end_hour)]
                for period in zone.periods
            ],
        }
        if zone.band_prices:
            zone_data["band_prices"] = [_format_price(p) for p in zone.band_prices]
        zones.append(zone_data)
    data: dict[str, Any] = {
        "valid_from": plan.valid_from.isoformat(),
        "name": plan.name,
        "zones": zones,
    }
    if plan.volume_band_limits_kwh:
        data["volume_band_limits_kwh"] = [
            _format_price(limit) for limit in plan.volume_band_limits_kwh
        ]
    return data


def _check_keys(
    data: Mapping[str, Any],
    allowed: frozenset[str],
    required: frozenset[str],
    label: str,
) -> None:
    unknown = sorted(str(key) for key in data if key not in allowed)
    if unknown:
        raise TariffValidationError(f"{label}: unknown keys {', '.join(unknown)}")
    missing = sorted(required - data.keys())
    if missing:
        raise TariffValidationError(f"{label}: missing keys {', '.join(missing)}")


def _read_str(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise TariffValidationError(f"{label} must be a string")
    return value


def _read_stored_price(value: Any, label: str) -> Decimal:
    text = _read_str(value, label)
    if "," in text:
        raise TariffValidationError(f"{label}: invalid stored price {text!r}")
    return parse_price(text)


def _read_list(value: Any, label: str) -> Sequence[Any]:
    if not isinstance(value, (list, tuple)):
        raise TariffValidationError(f"{label} must be a list")
    return value  # pyright: ignore[reportUnknownVariableType]


def _read_date(value: Any) -> date:
    text = _read_str(value, "valid_from")
    if _DATE_RE.fullmatch(text) is None:
        raise TariffValidationError(f"valid_from must be YYYY-MM-DD, got {text!r}")
    try:
        return date.fromisoformat(text)
    except ValueError as err:
        raise TariffValidationError(f"invalid valid_from: {text!r}") from err


def _read_period(value: Any) -> Period:
    pair = _read_list(value, "period")
    if len(pair) != 2:
        raise TariffValidationError("a period must be [start, end]")
    return Period.parse(
        _read_str(pair[0], "period start"), _read_str(pair[1], "period end")
    )


def _read_zone(value: Any) -> Zone:
    if not isinstance(value, Mapping):
        raise TariffValidationError("a zone must be an object")
    zone: Mapping[str, Any] = value  # pyright: ignore[reportUnknownVariableType]
    _check_keys(zone, _ZONE_KEYS, _ZONE_REQUIRED, "zone")
    periods = tuple(
        _read_period(item) for item in _read_list(zone["periods"], "periods")
    )
    band_prices = tuple(
        _read_stored_price(item, "band price")
        for item in _read_list(zone.get("band_prices", []), "band_prices")
    )
    return Zone(
        key=_read_str(zone["key"], "zone key"),
        name=_read_str(zone["name"], "zone name"),
        price=_read_stored_price(zone["price"], "zone price"),
        periods=periods,
        band_prices=band_prices,
    )


def plan_from_data(data: Mapping[str, Any]) -> TariffPlan:
    """Parse stored plan data strictly; raises ``TariffValidationError``."""
    if not isinstance(data, Mapping):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise TariffValidationError("plan data must be an object")
    _check_keys(data, _PLAN_KEYS, _PLAN_REQUIRED, "plan")
    name = _read_str(data["name"], "plan name")
    if not name.strip():
        raise TariffValidationError("plan name must not be blank")
    zones = tuple(_read_zone(item) for item in _read_list(data["zones"], "zones"))
    limits = tuple(
        _read_stored_price(item, "volume band limit")
        for item in _read_list(data.get("volume_band_limits_kwh", []), "limits")
    )
    return TariffPlan(
        valid_from=_read_date(data["valid_from"]),
        name=name,
        zones=zones,
        volume_band_limits_kwh=limits,
    )
