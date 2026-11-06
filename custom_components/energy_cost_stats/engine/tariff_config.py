"""Tariffs with versions, the applied history and the comparison list (SPEC §3).

Pure Python, stdlib only (CLAUDE.md principle 4). ``config_from_data`` parses the
configuration document (the same shape the planned YAML configuration uses) strictly and
raises ``TariffValidationError``. ``effective_schedule`` turns the applied history into
the schedule used for the real cost; ``comparison_schedule`` prices a single tariff over
its own versions only. Design: tasks/017-tariff-model.md.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from .plan_codec import parse_periods, parse_price
from .presets import PRESET_ZONES
from .tariff import TariffPlan, TariffSchedule, TariffValidationError, Zone

_ID_RE = re.compile(r"[a-z0-9_]{1,32}")
_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", re.ASCII)

_DOC_KEYS = frozenset({"tariffs", "applied", "compare"})
_TARIFF_KEYS = frozenset({"id", "name", "versions"})
_VERSION_KEYS = frozenset({"valid_from", "preset", "zones", "prices", "hours"})
_ZONE_KEYS = frozenset({"key", "name", "price", "hours"})
_APPLIED_KEYS = frozenset({"from", "tariff"})


@dataclass(frozen=True, slots=True)
class Tariff:
    """A named tariff: versions sorted by ``valid_from``, each a full ``TariffPlan``."""

    id: str
    name: str
    versions: tuple[TariffPlan, ...]


@dataclass(frozen=True, slots=True)
class AppliedChange:
    """From ``from_date`` (a local date) the tariff ``tariff`` is the one in use."""

    from_date: date
    tariff: str


@dataclass(frozen=True, slots=True)
class TariffConfig:
    """All tariffs, the applied history (sorted) and the resolved compare list."""

    tariffs: tuple[Tariff, ...] = ()
    applied: tuple[AppliedChange, ...] = ()
    compare: tuple[str, ...] = ()

    def tariff(self, tariff_id: str) -> Tariff:
        """The tariff with this id; ``KeyError`` if there is none."""
        for item in self.tariffs:
            if item.id == tariff_id:
                return item
        raise KeyError(tariff_id)


def default_compare(config: TariffConfig) -> tuple[str, ...]:
    """Ids of the tariffs that never appear in the applied history."""
    used = {change.tariff for change in config.applied}
    return tuple(item.id for item in config.tariffs if item.id not in used)


def comparison_schedule(tariff: Tariff) -> TariffSchedule:
    """Price a tariff with its own versions only (earlier hours stay unpriced)."""
    return TariffSchedule(tariff.versions)


def effective_schedule(config: TariffConfig) -> TariffSchedule | None:
    """The schedule of the real cost, or ``None`` when nothing is applied.

    For each applied interval ``[from_i, from_i+1)`` the version in force at ``from_i``
    (re-dated to ``from_i``) is used, then the later versions inside the interval.
    """
    plans: list[TariffPlan] = []
    for index, change in enumerate(config.applied):
        end = (
            config.applied[index + 1].from_date
            if index + 1 < len(config.applied)
            else None
        )
        versions = config.tariff(change.tariff).versions
        in_force = [v for v in versions if v.valid_from <= change.from_date]
        plans.append(replace(in_force[-1], valid_from=change.from_date))
        plans.extend(
            v
            for v in versions
            if v.valid_from > change.from_date and (end is None or v.valid_from < end)
        )
    return TariffSchedule(tuple(plans)) if plans else None


# ---- parsing -------------------------------------------------------------------


def _fail(message: str) -> TariffValidationError:
    return TariffValidationError(message)


def _check_keys(data: Mapping[str, Any], allowed: frozenset[str], label: str) -> None:
    unknown = sorted(str(key) for key in data if key not in allowed)
    if unknown:
        raise _fail(f"{label}: unknown keys {', '.join(unknown)}")


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _fail(f"{label} must be an object")
    return value  # pyright: ignore[reportUnknownVariableType]


def _list(value: Any, label: str) -> Sequence[Any]:
    if not isinstance(value, (list, tuple)):
        raise _fail(f"{label} must be a list")
    return value  # pyright: ignore[reportUnknownVariableType]


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise _fail(f"{label} must be a string")
    return value


def _date(value: Any, label: str) -> date:
    if isinstance(value, datetime):
        raise _fail(f"{label} must be a date, not a datetime")
    if isinstance(value, date):
        return value
    text = _text(value, label)
    if _DATE_RE.fullmatch(text) is None:
        raise _fail(f"{label} must be YYYY-MM-DD, got {text!r}")
    try:
        return date.fromisoformat(text)
    except ValueError as err:
        raise _fail(f"invalid {label}: {text!r}") from err


def _price(value: Any, label: str) -> Decimal:
    if not isinstance(value, str) or "," in value:
        raise _fail(f"{label} must be a decimal string, got {value!r}")
    return parse_price(value)


def _hours(value: Any, label: str) -> Any:
    if isinstance(value, Mapping):
        raise _fail(f"{label}: weekday-dependent hours are not supported yet")
    return parse_periods(_text(value, f"{label} hours"))


def _prices(version: Mapping[str, Any]) -> dict[str, Decimal]:
    raw = _mapping(version["prices"], "prices")
    return {str(key): _price(raw[key], f"price of {key}") for key in raw}


def _hour_overrides(version: Mapping[str, Any]) -> dict[str, Any]:
    raw = _mapping(version.get("hours", {}), "hours")
    return {str(key): _hours(raw[key], f"zone {key}") for key in raw}


def _apply_overrides(
    zones: Sequence[Zone], prices: dict[str, Decimal] | None, hours: dict[str, Any]
) -> tuple[Zone, ...]:
    keys = {zone.key for zone in zones}
    if prices is not None and set(prices) != keys:
        raise _fail(
            f"prices must name exactly the zones {', '.join(sorted(keys))}, "
            f"got {', '.join(sorted(prices)) or 'none'}"
        )
    unknown = sorted(set(hours) - keys)
    if unknown:
        raise _fail(f"hours name unknown zones: {', '.join(unknown)}")
    return tuple(
        replace(
            zone,
            price=zone.price if prices is None else prices[zone.key],
            periods=hours.get(zone.key, zone.periods),
        )
        for zone in zones
    )


def _explicit_zones(raw: Any) -> tuple[Zone, ...]:
    zones: list[Zone] = []
    for item in _list(raw, "zones"):
        zone = _mapping(item, "zone")
        _check_keys(zone, _ZONE_KEYS, "zone")
        missing = sorted(_ZONE_KEYS - zone.keys())
        if missing:
            raise _fail(f"zone: missing keys {', '.join(missing)}")
        key = _text(zone["key"], "zone key")
        zones.append(
            Zone(
                key=key,
                name=_text(zone["name"], "zone name"),
                price=_price(zone["price"], f"price of {key}"),
                periods=_hours(zone["hours"], f"zone {key}"),
            )
        )
    return tuple(zones)


def _version_zones(
    version: Mapping[str, Any], previous: tuple[Zone, ...] | None
) -> tuple[Zone, ...]:
    has_preset = "preset" in version
    has_zones = "zones" in version
    if has_preset and has_zones:
        raise _fail("give either preset or zones, not both")
    if has_zones:
        if "prices" in version or "hours" in version:
            raise _fail("prices and hours are not allowed together with zones")
        return _explicit_zones(version["zones"])
    if has_preset:
        name = _text(version["preset"], "preset")
        if name not in PRESET_ZONES:
            raise _fail(f"unknown preset {name!r}")
        base = tuple(
            Zone(key=z.key, name=z.name, price=Decimal(0), periods=z.periods)
            for z in PRESET_ZONES[name]
        )
    elif previous is not None:
        base = previous
    else:
        raise _fail("the first version needs preset or zones")
    if "prices" not in version:
        raise _fail("a version without explicit zones needs prices")
    return _apply_overrides(base, _prices(version), _hour_overrides(version))


def _tariff(data: Any) -> Tariff:
    raw = _mapping(data, "tariff")
    _check_keys(raw, _TARIFF_KEYS, "tariff")
    missing = sorted(_TARIFF_KEYS - raw.keys())
    if missing:
        raise _fail(f"tariff: missing keys {', '.join(missing)}")
    tariff_id = _text(raw["id"], "tariff id")
    if _ID_RE.fullmatch(tariff_id) is None:
        raise _fail(f"invalid tariff id {tariff_id!r}: use a-z, 0-9 and _ (1-32)")
    name = _text(raw["name"], "tariff name")
    if not name.strip():
        raise _fail(f"tariff {tariff_id}: name must not be blank")
    items = _list(raw["versions"], "versions")
    if not items:
        raise _fail(f"tariff {tariff_id}: needs at least one version")

    parsed: list[tuple[date, Mapping[str, Any]]] = []
    for item in items:
        version = _mapping(item, "version")
        _check_keys(version, _VERSION_KEYS, "version")
        if "valid_from" not in version:
            raise _fail("version: missing keys valid_from")
        parsed.append((_date(version["valid_from"], "valid_from"), version))
    parsed.sort(key=lambda pair: pair[0])
    dates = [pair[0] for pair in parsed]
    if len(set(dates)) != len(dates):
        raise _fail(f"tariff {tariff_id}: duplicate valid_from date")

    plans: list[TariffPlan] = []
    zones: tuple[Zone, ...] | None = None
    for valid_from, version in parsed:
        try:
            zones = _version_zones(version, zones)
            plans.append(TariffPlan(valid_from=valid_from, name=name, zones=zones))
        except TariffValidationError as err:
            raise _fail(f"tariff {tariff_id}, version {valid_from}: {err}") from err
    return Tariff(tariff_id, name, tuple(plans))


def _applied(raw: Any, tariffs: Mapping[str, Tariff]) -> tuple[AppliedChange, ...]:
    if raw is None:
        return ()
    changes: list[AppliedChange] = []
    if isinstance(raw, str):
        if raw not in tariffs:
            raise _fail(f"applied: unknown tariff {raw!r}")
        changes.append(AppliedChange(tariffs[raw].versions[0].valid_from, raw))
    else:
        for item in _list(raw, "applied"):
            entry = _mapping(item, "applied item")
            _check_keys(entry, _APPLIED_KEYS, "applied item")
            missing = sorted(_APPLIED_KEYS - entry.keys())
            if missing:
                raise _fail(f"applied item: missing keys {', '.join(missing)}")
            tariff_id = _text(entry["tariff"], "applied tariff")
            if tariff_id not in tariffs:
                raise _fail(f"applied: unknown tariff {tariff_id!r}")
            changes.append(
                AppliedChange(_date(entry["from"], "applied from"), tariff_id)
            )
    changes.sort(key=lambda change: change.from_date)
    starts = [change.from_date for change in changes]
    if len(set(starts)) != len(starts):
        raise _fail("applied: duplicate from date")
    for change in changes:
        if tariffs[change.tariff].versions[0].valid_from > change.from_date:
            raise _fail(
                f"applied: tariff {change.tariff!r} has no version valid on "
                f"{change.from_date.isoformat()}"
            )
    return tuple(changes)


def config_from_data(data: Mapping[str, Any]) -> TariffConfig:
    """Parse the configuration document strictly; raises ``TariffValidationError``."""
    document = _mapping(data, "configuration")
    _check_keys(document, _DOC_KEYS, "configuration")
    tariffs: dict[str, Tariff] = {}
    for item in _list(document.get("tariffs", []), "tariffs"):
        tariff = _tariff(item)
        if tariff.id in tariffs:
            raise _fail(f"duplicate tariff id {tariff.id!r}")
        tariffs[tariff.id] = tariff
    config = TariffConfig(
        tariffs=tuple(tariffs.values()),
        applied=_applied(document.get("applied"), tariffs),
    )
    raw_compare = document.get("compare")
    if raw_compare is None:
        compare = default_compare(config)
    else:
        compare = tuple(
            _text(item, "compare item") for item in _list(raw_compare, "compare")
        )
        for tariff_id in compare:
            if tariff_id not in tariffs:
                raise _fail(f"compare: unknown tariff {tariff_id!r}")
    return replace(config, compare=compare)
