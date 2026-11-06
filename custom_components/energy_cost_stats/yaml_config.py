"""The ``energy_cost_stats:`` YAML block: normalizer and exporter (docs/SPEC.md §2, §3).

Pure Python with no Home Assistant imports, like ``settings.py``. ``document_from_yaml``
turns the values a YAML loader returns into the stored JSON shape (the same one the
forms write to ``entry.options`` and to the ``tariff`` subentries) and then validates
it strictly with the existing parsers. ``export_document`` goes the other way.
Time-zone existence is checked by the caller (it needs Home Assistant's async helper).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Any

from .const import (
    CONF_APPLIED,
    CONF_COMPARE,
    CONF_EXCLUDE,
    CONF_ICON,
    CONF_INCLUDE,
    CONF_MODE,
    CONF_OVERRIDES,
    CONF_PANEL,
    CONF_SENSORS,
    CONF_SHOW,
    CONF_SPIKE_LIMIT,
    CONF_TIME_ZONE,
    CONF_TITLE,
    DEFAULT_PANEL_ICON,
    DEFAULT_PANEL_SHOW,
    DEFAULT_PANEL_TITLE,
    DEFAULT_SPIKE_LIMIT,
    INCLUDE_ALL,
    MODE_FILTER,
    TARGET_KEYS,
)
from .engine.tariff import TariffValidationError
from .engine.tariff_config import (
    APPLIED_KEYS,
    TARIFF_KEYS,
    VERSION_KEYS,
    ZONE_KEYS,
    config_from_data,
)
from .settings import (
    OPTION_KEYS,
    SettingsError,
    settings_from_options,
    settings_to_options,
    tariff_document,
)

# Keys the parser accepts, per mapping in the document. Paths are JSON-pointer-like;
# ``*`` stands for a list index or a mapping key. ``prices`` and ``hours`` are maps with
# free keys (zone keys) and are therefore not listed. The JSON Schema is kept in sync
# with this table by tests/integration/test_yaml_schema_sync.py.
ACCEPTED_KEYS: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        "": OPTION_KEYS | {"tariffs"},
        "/panel": frozenset({CONF_SHOW, CONF_TITLE, CONF_ICON}),
        "/sensors": frozenset({CONF_MODE, CONF_INCLUDE, CONF_EXCLUDE, CONF_OVERRIDES}),
        "/sensors/include": frozenset(TARGET_KEYS),
        "/sensors/exclude": frozenset(TARGET_KEYS),
        "/sensors/overrides/*": frozenset({CONF_SPIKE_LIMIT}),
        "/tariffs/*": TARIFF_KEYS,
        "/tariffs/*/versions/*": VERSION_KEYS,
        "/tariffs/*/versions/*/zones/*": ZONE_KEYS,
        "/applied/*": APPLIED_KEYS,
    }
)


class YamlConfigError(ValueError):
    """The YAML block is invalid; the message names the path of the problem."""


@dataclass(frozen=True)
class YamlDocument:
    """A validated block: the entry options and the tariff subentry data."""

    options: dict[str, Any]
    tariffs: tuple[dict[str, Any], ...]


def _fail(message: str) -> YamlConfigError:
    return YamlConfigError(message)


def _check_keys(raw: Mapping[Any, Any], pattern: str, label: str) -> None:
    unknown = sorted(str(key) for key in raw if key not in ACCEPTED_KEYS[pattern])
    if unknown:
        allowed = ", ".join(sorted(ACCEPTED_KEYS[pattern]))
        raise _fail(
            f"{label or 'configuration'}: unknown keys {', '.join(unknown)} "
            f"(allowed: {allowed})"
        )


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _fail(f"{label}: must be a mapping")
    return value  # pyright: ignore[reportUnknownVariableType]


def _items(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise _fail(f"{label}: must be a list")
    return value  # pyright: ignore[reportUnknownVariableType]


def _decimal(value: Any, label: str) -> Any:
    """Numbers become normalized decimal strings; everything else is kept."""
    if isinstance(value, bool):
        raise _fail(f"{label}: must be a decimal, not a boolean")
    if isinstance(value, (int, float)):
        try:
            return format(Decimal(str(value)), "f")
        except InvalidOperation as err:  # pragma: no cover - str(number) always parses
            raise _fail(f"{label}: must be a decimal") from err
    return value


def _date(value: Any, label: str) -> Any:
    if isinstance(value, datetime):
        raise _fail(f"{label}: must be a date (YYYY-MM-DD), not a datetime")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return value
    raise _fail(f"{label}: must be a date (YYYY-MM-DD)")


def _format_limit(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _panel(raw: Any) -> dict[str, Any]:
    panel = _mapping(raw, CONF_PANEL)
    _check_keys(panel, "/panel", CONF_PANEL)
    return {
        CONF_SHOW: panel.get(CONF_SHOW, DEFAULT_PANEL_SHOW),
        CONF_TITLE: panel.get(CONF_TITLE, DEFAULT_PANEL_TITLE),
        CONF_ICON: panel.get(CONF_ICON, DEFAULT_PANEL_ICON),
    }


def _sensors(raw: Any) -> dict[str, Any]:
    sensors = _mapping(raw, CONF_SENSORS)
    _check_keys(sensors, "/sensors", CONF_SENSORS)
    if CONF_MODE not in sensors:
        raise _fail("sensors.mode: required (energy_dashboard or filter)")
    result: dict[str, Any] = {CONF_MODE: sensors[CONF_MODE]}
    if CONF_INCLUDE in sensors:
        include = sensors[CONF_INCLUDE]
        if isinstance(include, Mapping):
            _check_keys(include, "/sensors/include", "sensors.include")  # pyright: ignore[reportUnknownArgumentType]
        result[CONF_INCLUDE] = include
    elif sensors[CONF_MODE] == MODE_FILTER:
        result[CONF_INCLUDE] = INCLUDE_ALL
    exclude = sensors.get(CONF_EXCLUDE, {})
    if isinstance(exclude, Mapping):
        _check_keys(exclude, "/sensors/exclude", "sensors.exclude")  # pyright: ignore[reportUnknownArgumentType]
    result[CONF_EXCLUDE] = exclude
    overrides = _mapping(sensors.get(CONF_OVERRIDES, {}), "sensors.overrides")
    converted: dict[str, Any] = {}
    for key, value in overrides.items():
        label = f"sensors.overrides.{key}"
        item = _mapping(value, label)
        _check_keys(item, "/sensors/overrides/*", label)
        converted[key] = {
            name: _decimal(limit, f"{label}.{name}") for name, limit in item.items()
        }
    result[CONF_OVERRIDES] = converted
    return result


def _zone(raw: Any, label: str) -> dict[str, Any]:
    zone = dict(_mapping(raw, label))
    _check_keys(zone, "/tariffs/*/versions/*/zones/*", label)
    if "price" in zone:
        zone["price"] = _decimal(zone["price"], f"{label}.price")
    return zone


def _version(raw: Any, label: str) -> dict[str, Any]:
    version = dict(_mapping(raw, label))
    _check_keys(version, "/tariffs/*/versions/*", label)
    if "valid_from" in version:
        version["valid_from"] = _date(version["valid_from"], f"{label}.valid_from")
    prices = version.get("prices")
    if isinstance(prices, Mapping):
        version["prices"] = {
            key: _decimal(value, f"{label}.prices.{key}")
            for key, value in prices.items()  # pyright: ignore[reportUnknownVariableType]
        }
    zones = version.get("zones")
    if isinstance(zones, list):
        version["zones"] = [
            _zone(zone, f"{label}.zones[{index}]")
            for index, zone in enumerate(zones)  # pyright: ignore[reportUnknownArgumentType, reportUnknownVariableType]
        ]
    return version


def _tariff(raw: Any, label: str) -> dict[str, Any]:
    tariff = dict(_mapping(raw, label))
    _check_keys(tariff, "/tariffs/*", label)
    versions = tariff.get("versions")
    if isinstance(versions, list):
        tariff["versions"] = [
            _version(version, f"{label}.versions[{index}]")
            for index, version in enumerate(versions)  # pyright: ignore[reportUnknownArgumentType, reportUnknownVariableType]
        ]
    return tariff


def _applied(raw: Any, tariffs: list[dict[str, Any]]) -> list[dict[str, str]]:
    if isinstance(raw, str):
        for tariff in tariffs:
            if tariff.get("id") == raw:
                dates = [
                    str(version["valid_from"])
                    for version in tariff.get("versions", [])
                    if isinstance(version, Mapping) and "valid_from" in version
                ]
                if not dates:
                    raise _fail(f"applied: tariff {raw!r} has no version")
                return [{"from": min(dates), "tariff": raw}]
        raise _fail(f"applied: unknown tariff {raw!r}")
    result: list[dict[str, str]] = []
    for index, item in enumerate(_items(raw, CONF_APPLIED)):
        label = f"applied[{index}]"
        entry = dict(_mapping(item, label))
        _check_keys(entry, "/applied/*", label)
        if "from" in entry:
            entry["from"] = _date(entry["from"], f"{label}.from")
        result.append(entry)  # pyright: ignore[reportArgumentType]
    return result


def document_from_yaml(
    raw: Any,
    *,
    default_time_zone: str,
    default_sensors: Mapping[str, Any],
) -> YamlDocument:
    """Normalize and strictly validate the YAML block; raise ``YamlConfigError``."""
    if raw is None:
        raw = {}
    block = _mapping(raw, "energy_cost_stats")
    _check_keys(block, "", "energy_cost_stats")

    options: dict[str, Any] = {
        CONF_TIME_ZONE: block.get(CONF_TIME_ZONE, default_time_zone),
        CONF_SPIKE_LIMIT: (
            _decimal(block[CONF_SPIKE_LIMIT], CONF_SPIKE_LIMIT)
            if CONF_SPIKE_LIMIT in block
            else _format_limit(DEFAULT_SPIKE_LIMIT)
        ),
    }
    if CONF_PANEL in block:
        options[CONF_PANEL] = _panel(block[CONF_PANEL])
    options[CONF_SENSORS] = (
        _sensors(block[CONF_SENSORS])
        if CONF_SENSORS in block
        else dict(default_sensors)
    )

    raw_tariffs = block.get("tariffs")
    if raw_tariffs is None:
        raw_tariffs = []
    tariffs = [
        _tariff(item, f"tariffs[{index}]")
        for index, item in enumerate(_items(raw_tariffs, "tariffs"))
    ]
    applied = block.get(CONF_APPLIED)
    if applied is not None:
        options[CONF_APPLIED] = _applied(applied, tariffs)
    compare = block.get(CONF_COMPARE)
    if compare is not None:
        options[CONF_COMPARE] = compare

    try:
        settings = settings_from_options(options)
        config_from_data(tariff_document(settings, tariffs))
    except (SettingsError, TariffValidationError) as err:
        raise _fail(str(err)) from err

    return YamlDocument(settings_to_options(settings), tuple(tariffs))


def _plain(value: Any) -> Any:
    """Plain ``dict`` / ``list`` copy (subentry data is a read-only mapping)."""
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}  # pyright: ignore[reportUnknownVariableType]
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]  # pyright: ignore[reportUnknownVariableType]
    return value


def _as_date(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return value
    return value


def export_document(
    options: Mapping[str, Any], tariff_data: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """The block content for the stored options and tariffs (dates as ``date``)."""
    document: dict[str, Any] = {
        CONF_TIME_ZONE: options[CONF_TIME_ZONE],
        CONF_SPIKE_LIMIT: options.get(CONF_SPIKE_LIMIT),
    }
    if CONF_PANEL in options:
        document[CONF_PANEL] = _plain(options[CONF_PANEL])
    document[CONF_SENSORS] = _plain(options[CONF_SENSORS])
    tariffs: list[Any] = []
    for data in tariff_data:
        tariff = _plain(data)
        for version in tariff.get("versions", []):
            version["valid_from"] = _as_date(version.get("valid_from"))
        tariffs.append(tariff)
    document["tariffs"] = tariffs
    if options.get(CONF_APPLIED):
        document[CONF_APPLIED] = [
            {"from": _as_date(item["from"]), "tariff": item["tariff"]}
            for item in options[CONF_APPLIED]
        ]
    if CONF_COMPARE in options:
        document[CONF_COMPARE] = list(options[CONF_COMPARE])
    return document
