"""Integration settings: a strict mapping between ``entry.options`` and a typed object.

Pure configuration mapping with no Home Assistant imports. ``None`` for a spike
limit means "check disabled"; a missing key in ``device_spike_limits`` means "use
the global limit". Decimals are stored as normalized strings (no exponent).
The time zone name is not validated here (that needs Home Assistant's async helper).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Any

from .const import (
    CONF_APPLIED,
    CONF_COMPARE,
    CONF_DEVICE_SPIKE_LIMITS,
    CONF_ENTITIES,
    CONF_SPIKE_LIMIT,
    CONF_TIME_ZONE,
)

_KNOWN_KEYS = frozenset(
    {
        CONF_TIME_ZONE,
        CONF_SPIKE_LIMIT,
        CONF_DEVICE_SPIKE_LIMITS,
        CONF_ENTITIES,
        CONF_APPLIED,
        CONF_COMPARE,
    }
)


class SettingsError(ValueError):
    """Stored options are malformed."""


@dataclass(frozen=True)
class IntegrationSettings:
    """Parsed global settings."""

    time_zone: str
    spike_limit: Decimal | None
    device_spike_limits: Mapping[str, Decimal | None]
    entities: tuple[str, ...]
    # Applied tariff history as (ISO date, tariff id); validated with the tariffs.
    applied: tuple[tuple[str, str], ...] = ()
    # Explicit compare list (tariff ids); ``None`` = every tariff never applied.
    compare: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        """Make the override mapping read-only."""
        object.__setattr__(
            self,
            "device_spike_limits",
            MappingProxyType(dict(self.device_spike_limits)),
        )


def _parse_limit(value: Any, what: str) -> Decimal:
    if not isinstance(value, str):
        raise SettingsError(f"{what} must be a decimal string, got {value!r}")
    try:
        limit = Decimal(value)
    except InvalidOperation as err:
        raise SettingsError(f"{what} is not a valid decimal: {value!r}") from err
    if not limit.is_finite() or limit <= 0:
        raise SettingsError(f"{what} must be a finite number > 0, got {value!r}")
    return limit


def _format_limit(value: Decimal) -> str:
    return format(value.normalize(), "f")


def settings_from_options(options: Mapping[str, Any]) -> IntegrationSettings:
    """Parse ``entry.options``; raise ``SettingsError`` on anything unexpected."""
    unknown = set(options) - _KNOWN_KEYS
    if unknown:
        raise SettingsError(f"Unknown option keys: {sorted(unknown)}")

    time_zone = options.get(CONF_TIME_ZONE)
    if not isinstance(time_zone, str) or not time_zone:
        raise SettingsError("time_zone must be a non-empty string")

    raw_limit = options.get(CONF_SPIKE_LIMIT)
    spike_limit = (
        None if raw_limit is None else _parse_limit(raw_limit, CONF_SPIKE_LIMIT)
    )

    raw_overrides = options.get(CONF_DEVICE_SPIKE_LIMITS, {})
    if not isinstance(raw_overrides, Mapping):
        raise SettingsError("device_spike_limits must be a mapping")
    overrides: dict[str, Decimal | None] = {}
    for key, value in raw_overrides.items():
        if not isinstance(key, str) or not key:
            raise SettingsError(f"Invalid device id: {key!r}")
        overrides[key] = (
            None if value is None else _parse_limit(value, f"limit for {key}")
        )

    raw_entities = options.get(CONF_ENTITIES, [])
    if not isinstance(raw_entities, list):
        raise SettingsError("entities must be a list")
    if not all(isinstance(e, str) and e for e in raw_entities):
        raise SettingsError("entities must contain non-empty strings")
    if len(set(raw_entities)) != len(raw_entities):
        raise SettingsError("entities must not contain duplicates")

    raw_applied = options.get(CONF_APPLIED, [])
    if not isinstance(raw_applied, list):
        raise SettingsError("applied must be a list")
    applied: list[tuple[str, str]] = []
    for item in raw_applied:  # pyright: ignore[reportUnknownVariableType]
        if (
            not isinstance(item, Mapping)
            or set(item) != {"from", "tariff"}  # pyright: ignore[reportUnknownArgumentType]
            or not isinstance(item["from"], str)
            or not isinstance(item["tariff"], str)
        ):
            raise SettingsError("applied items must be {from, tariff} strings")
        applied.append((item["from"], item["tariff"]))

    raw_compare = options.get(CONF_COMPARE)
    compare: tuple[str, ...] | None = None
    if raw_compare is not None:
        if not isinstance(raw_compare, list) or not all(
            isinstance(c, str)
            for c in raw_compare  # pyright: ignore[reportUnknownVariableType]
        ):
            raise SettingsError("compare must be a list of tariff ids")
        compare = tuple(raw_compare)  # pyright: ignore[reportUnknownArgumentType]

    return IntegrationSettings(
        time_zone=time_zone,
        spike_limit=spike_limit,
        device_spike_limits=overrides,
        entities=tuple(raw_entities),
        applied=tuple(applied),
        compare=compare,
    )


def settings_to_options(settings: IntegrationSettings) -> dict[str, Any]:
    """Serialize settings to the JSON-friendly ``entry.options`` format."""
    options: dict[str, Any] = {
        CONF_TIME_ZONE: settings.time_zone,
        CONF_SPIKE_LIMIT: (
            None
            if settings.spike_limit is None
            else _format_limit(settings.spike_limit)
        ),
        CONF_DEVICE_SPIKE_LIMITS: {
            key: None if value is None else _format_limit(value)
            for key, value in settings.device_spike_limits.items()
        },
        CONF_ENTITIES: list(settings.entities),
    }
    if settings.applied:
        options[CONF_APPLIED] = [
            {"from": start, "tariff": tariff} for start, tariff in settings.applied
        ]
    if settings.compare is not None:
        options[CONF_COMPARE] = list(settings.compare)
    return options
