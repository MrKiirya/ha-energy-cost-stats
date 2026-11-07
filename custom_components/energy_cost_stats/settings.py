"""Integration settings: a strict mapping between ``entry.options`` and a typed object.

Pure configuration mapping with no Home Assistant imports. ``None`` for a spike
limit means "check disabled"; a sensor without an override uses the global limit.
The ``sensors`` key (selection mode, include / exclude targets, per-sensor overrides)
is documented in docs/SPEC.md §2. Decimals are stored as normalized strings
(no exponent).
The time zone name is not validated here (that needs Home Assistant's async helper).
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from .const import (
    CONF_APPLIED,
    CONF_COMPARE,
    CONF_EXCLUDE,
    CONF_INCLUDE,
    CONF_MODE,
    CONF_OVERRIDES,
    CONF_PANEL,
    CONF_SENSORS,
    CONF_SPIKE_LIMIT,
    CONF_TIME_ZONE,
    INCLUDE_ALL,
    TARGET_KEYS,
)
from .engine.sensors import (
    SensorMode,
    SensorOverride,
    SensorSettings,
    SensorTarget,
    is_valid_glob,
)

OPTION_KEYS = frozenset(
    {
        CONF_TIME_ZONE,
        CONF_SPIKE_LIMIT,
        CONF_SENSORS,
        CONF_APPLIED,
        CONF_COMPARE,
        CONF_PANEL,
    }
)


class SettingsError(ValueError):
    """Stored options are malformed."""


@dataclass(frozen=True)
class PanelSettings:
    """Sidebar panel options: whether to show the entry, and its title and icon."""

    show: bool
    title: str
    icon: str


@dataclass(frozen=True)
class IntegrationSettings:
    """Parsed global settings."""

    time_zone: str
    spike_limit: Decimal | None
    sensors: SensorSettings
    # Applied tariff history as (ISO date, tariff id); validated with the tariffs.
    applied: tuple[tuple[str, str], ...] = ()
    # Explicit compare list (tariff ids); ``None`` = every tariff never applied.
    compare: tuple[str, ...] | None = None
    # Sidebar panel options; ``None`` = never configured.
    panel: PanelSettings | None = None


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


def _parse_target(raw: Any, what: str) -> SensorTarget:
    if not isinstance(raw, Mapping):
        raise SettingsError(f"{what} must be a mapping")
    unknown = set(raw) - set(TARGET_KEYS)  # pyright: ignore[reportUnknownArgumentType]
    if unknown:
        raise SettingsError(f"{what} has unknown keys: {sorted(unknown)}")
    values: dict[str, tuple[str, ...]] = {}
    for key in TARGET_KEYS:
        if key not in raw:
            continue
        items = raw[key]
        if not isinstance(items, list) or not all(
            isinstance(item, str) and item
            for item in items  # pyright: ignore[reportUnknownVariableType]
        ):
            raise SettingsError(f"{what}.{key} must be a list of non-empty strings")
        if len(set(items)) != len(items):  # pyright: ignore[reportUnknownArgumentType]
            raise SettingsError(f"{what}.{key} must not contain duplicates")
        values[key] = tuple(items)  # pyright: ignore[reportUnknownArgumentType]
    bad = [glob for glob in values.get("entity_globs", ()) if not is_valid_glob(glob)]
    if bad:
        raise SettingsError(f"{what}.entity_globs has invalid patterns: {bad}")
    return SensorTarget(**values)


def _target_to_data(target: SensorTarget) -> dict[str, list[str]]:
    data: dict[str, list[str]] = {}
    for key in TARGET_KEYS:
        value: tuple[str, ...] = getattr(target, key)
        if value:
            data[key] = list(value)
    return data


def _parse_sensors(raw: Any) -> SensorSettings:
    keys = {CONF_MODE, CONF_INCLUDE, CONF_EXCLUDE, CONF_OVERRIDES}
    if not isinstance(raw, Mapping) or not set(raw) <= keys:  # pyright: ignore[reportUnknownArgumentType]
        raise SettingsError("sensors must be a mapping with mode, include, exclude")
    if not {CONF_MODE, CONF_EXCLUDE, CONF_OVERRIDES} <= set(raw):  # pyright: ignore[reportUnknownArgumentType]
        raise SettingsError("sensors needs mode, exclude and overrides")
    try:
        mode = SensorMode(raw[CONF_MODE])
    except ValueError as err:
        raise SettingsError(f"unknown sensors mode: {raw[CONF_MODE]!r}") from err
    include: SensorTarget | None = None
    if mode is SensorMode.ENERGY_DASHBOARD:
        if CONF_INCLUDE in raw:
            raise SettingsError("sensors.include is only allowed in filter mode")
    else:
        if CONF_INCLUDE not in raw:
            raise SettingsError("sensors.include is required in filter mode")
        if raw[CONF_INCLUDE] != INCLUDE_ALL:
            include = _parse_target(raw[CONF_INCLUDE], "sensors.include")
            if include.is_empty:
                raise SettingsError("sensors.include selects nothing")
    exclude = _parse_target(raw[CONF_EXCLUDE], "sensors.exclude")
    raw_overrides = raw[CONF_OVERRIDES]
    if not isinstance(raw_overrides, Mapping):
        raise SettingsError("sensors.overrides must be a mapping")
    overrides: dict[str, SensorOverride] = {}
    for key, value in raw_overrides.items():  # pyright: ignore[reportUnknownVariableType]
        if not isinstance(key, str) or not key:
            raise SettingsError(f"Invalid override entity id: {key!r}")
        if not isinstance(value, Mapping) or set(value) != {CONF_SPIKE_LIMIT}:  # pyright: ignore[reportUnknownArgumentType]
            raise SettingsError(f"override for {key} must be {{spike_limit}}")
        limit = value[CONF_SPIKE_LIMIT]
        overrides[key] = SensorOverride(
            None if limit is None else _parse_limit(limit, f"limit for {key}")
        )
    return SensorSettings(
        mode=mode, include=include, exclude=exclude, overrides=overrides
    )


def _sensors_to_data(sensors: SensorSettings) -> dict[str, Any]:
    data: dict[str, Any] = {CONF_MODE: sensors.mode.value}
    if sensors.mode is SensorMode.FILTER:
        data[CONF_INCLUDE] = (
            INCLUDE_ALL if sensors.include is None else _target_to_data(sensors.include)
        )
    data[CONF_EXCLUDE] = _target_to_data(sensors.exclude)
    data[CONF_OVERRIDES] = {
        key: {
            CONF_SPIKE_LIMIT: (
                None if item.spike_limit is None else _format_limit(item.spike_limit)
            )
        }
        for key, item in sensors.overrides.items()
    }
    return data


def migrate_sensor_options(
    options: Mapping[str, Any], default: Mapping[str, Any]
) -> dict[str, Any]:
    """Version 2 -> 3: ``entities`` + ``device_spike_limits`` become ``sensors``.

    A non-empty ``entities`` list becomes a filter on exactly those ids; an empty one
    becomes ``default`` (the first-setup selection). Other keys are untouched; options
    that already have ``sensors`` are returned unchanged.
    """
    migrated = dict(options)
    if CONF_SENSORS in migrated:
        return migrated
    entities = migrated.pop("entities", [])
    limits = migrated.pop("device_spike_limits", {})
    overrides = {key: {CONF_SPIKE_LIMIT: value} for key, value in dict(limits).items()}
    if entities:
        sensors: dict[str, Any] = {
            CONF_MODE: SensorMode.FILTER.value,
            CONF_INCLUDE: {"entity_id": list(entities)},
            CONF_EXCLUDE: {},
            CONF_OVERRIDES: overrides,
        }
    else:
        sensors = {**default, CONF_OVERRIDES: overrides}
    migrated[CONF_SENSORS] = sensors
    return migrated


def _parse_panel(raw: Any) -> PanelSettings:
    if not isinstance(raw, Mapping) or set(raw) != {"show", "title", "icon"}:  # pyright: ignore[reportUnknownArgumentType]
        raise SettingsError("panel must be a {show, title, icon} mapping")
    show, title, icon = raw["show"], raw["title"], raw["icon"]
    if not isinstance(show, bool):
        raise SettingsError("panel show must be a boolean")
    if not isinstance(title, str) or not title.strip():
        raise SettingsError("panel title must be a non-blank string")
    if not isinstance(icon, str) or not icon.strip():
        raise SettingsError("panel icon must be a non-blank string")
    return PanelSettings(show=show, title=title, icon=icon)


def settings_from_options(options: Mapping[str, Any]) -> IntegrationSettings:
    """Parse ``entry.options``; raise ``SettingsError`` on anything unexpected."""
    unknown = set(options) - OPTION_KEYS
    if unknown:
        raise SettingsError(f"Unknown option keys: {sorted(unknown)}")

    time_zone = options.get(CONF_TIME_ZONE)
    if not isinstance(time_zone, str) or not time_zone:
        raise SettingsError("time_zone must be a non-empty string")

    raw_limit = options.get(CONF_SPIKE_LIMIT)
    spike_limit = (
        None if raw_limit is None else _parse_limit(raw_limit, CONF_SPIKE_LIMIT)
    )

    if CONF_SENSORS not in options:
        raise SettingsError("sensors is required")
    sensors = _parse_sensors(options[CONF_SENSORS])

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

    panel = _parse_panel(options[CONF_PANEL]) if CONF_PANEL in options else None

    return IntegrationSettings(
        time_zone=time_zone,
        spike_limit=spike_limit,
        sensors=sensors,
        applied=tuple(applied),
        compare=compare,
        panel=panel,
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
        CONF_SENSORS: _sensors_to_data(settings.sensors),
    }
    if settings.applied:
        options[CONF_APPLIED] = [
            {"from": start, "tariff": tariff} for start, tariff in settings.applied
        ]
    if settings.compare is not None:
        options[CONF_COMPARE] = list(settings.compare)
    if settings.panel is not None:
        options[CONF_PANEL] = {
            "show": settings.panel.show,
            "title": settings.panel.title,
            "icon": settings.panel.icon,
        }
    return options


def tariff_document(
    settings: IntegrationSettings, tariff_data: Iterable[Mapping[str, Any]]
) -> dict[str, Any]:
    """The configuration document for ``config_from_data`` (tariffs + options)."""
    document: dict[str, Any] = {
        "tariffs": list(tariff_data),
        "applied": [
            {"from": start, "tariff": tariff} for start, tariff in settings.applied
        ],
    }
    if settings.compare is not None:
        document["compare"] = list(settings.compare)
    return document
