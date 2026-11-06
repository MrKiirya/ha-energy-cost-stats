"""Pure helpers behind the tariff forms: build, edit and check tariff documents.

Pure Python, stdlib only (CLAUDE.md principle 4). The functions work on the stored
tariff document (``{id, name, versions}``, SPEC §3) and never mutate their input.
The Home Assistant flow in ``tariff_flow.py`` only collects form input and delegates
here. Design: tasks/018-tariff-forms.md.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .plan_codec import format_periods, parse_price
from .presets import PRESET_ZONES
from .tariff import Period, TariffValidationError, Zone
from .tariff_config import Tariff, config_from_data

MAX_ID_LENGTH = 32
DEFAULT_ID = "tariff"
_ID_CHARS_RE = re.compile(r"[^a-z0-9_]")


@dataclass(frozen=True, slots=True)
class ZoneInput:
    """One zone as entered in a form (the price is already parsed)."""

    key: str
    name: str
    price: Decimal
    periods: tuple[Period, ...]


@dataclass(frozen=True, slots=True)
class HoursProblems:
    """Hours of the day that no zone covers and zones that share an hour."""

    uncovered: tuple[int, ...]
    overlapping: frozenset[str]


def _hours_of(periods: Sequence[Period]) -> frozenset[int]:
    return frozenset(hour for period in periods for hour in period.hours())


def _price_text(price: Decimal) -> str:
    return format(price, "f")


def normalize_price(text: str) -> str:
    """Validate a typed price and return it with a ``.`` separator."""
    return _price_text(parse_price(text))


def unique_tariff_id(base: str, taken: Collection[str]) -> str:
    """A valid tariff id derived from ``base`` that is not in ``taken``."""
    cleaned = _ID_CHARS_RE.sub("", base.lower())[:MAX_ID_LENGTH] or DEFAULT_ID
    if cleaned not in taken:
        return cleaned
    number = 2
    while True:
        suffix = f"_{number}"
        candidate = cleaned[: MAX_ID_LENGTH - len(suffix)] + suffix
        if candidate not in taken:
            return candidate
        number += 1


def _explicit_zone(zone: ZoneInput) -> dict[str, str]:
    return {
        "key": zone.key,
        "name": zone.name,
        "price": _price_text(zone.price),
        "hours": format_periods(zone.periods),
    }


def first_version_doc(
    valid_from: str, zones: Sequence[ZoneInput], preset: str | None
) -> dict[str, Any]:
    """The document of a first version: the preset form when it can express the zones.

    A preset cannot express renamed or re-keyed zones; explicit ``zones`` are used.
    """
    preset_zones = PRESET_ZONES.get(preset) if preset is not None else None
    if (
        preset is not None
        and preset_zones is not None
        and [(z.key, z.name) for z in zones] == [(p.key, p.name) for p in preset_zones]
    ):
        doc: dict[str, Any] = {
            "valid_from": valid_from,
            "preset": preset,
            "prices": {z.key: _price_text(z.price) for z in zones},
        }
        hours = {
            zone.key: format_periods(zone.periods)
            for zone, base in zip(zones, preset_zones, strict=True)
            if _hours_of(zone.periods) != _hours_of(base.periods)
        }
        if hours:
            doc["hours"] = hours
        return doc
    return {"valid_from": valid_from, "zones": [_explicit_zone(z) for z in zones]}


def later_version_doc(
    valid_from: str,
    prices: Mapping[str, Decimal],
    periods: Mapping[str, tuple[Period, ...]],
    inherited: Sequence[Zone],
) -> dict[str, Any]:
    """A later version: prices, plus ``hours`` for the zones whose hours changed."""
    doc: dict[str, Any] = {
        "valid_from": valid_from,
        "prices": {zone.key: _price_text(prices[zone.key]) for zone in inherited},
    }
    hours = {
        zone.key: format_periods(periods[zone.key])
        for zone in inherited
        if _hours_of(periods[zone.key]) != _hours_of(zone.periods)
    }
    if hours:
        doc["hours"] = hours
    return doc


def _versions(tariff_doc: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [dict(version) for version in tariff_doc["versions"]]


def _with_versions(
    tariff_doc: Mapping[str, Any], versions: list[dict[str, Any]]
) -> dict[str, Any]:
    result = copy.deepcopy({key: value for key, value in tariff_doc.items()})
    result["versions"] = copy.deepcopy(versions)
    return result


def replace_version(
    tariff_doc: Mapping[str, Any],
    old_valid_from: str | None,
    version_doc: Mapping[str, Any],
) -> dict[str, Any]:
    """Insert a version (``old_valid_from`` is ``None``) or replace one by its date."""
    versions = _versions(tariff_doc)
    if old_valid_from is not None:
        kept = [v for v in versions if str(v["valid_from"]) != old_valid_from]
        if len(kept) == len(versions):
            raise TariffValidationError(f"no version valid from {old_valid_from}")
        versions = kept
    versions.append(dict(version_doc))
    versions.sort(key=lambda version: str(version["valid_from"]))
    return _with_versions(tariff_doc, versions)


def delete_version(tariff_doc: Mapping[str, Any], valid_from: str) -> dict[str, Any]:
    """Remove a version; deleting the first one makes the next self-contained."""
    versions = _versions(tariff_doc)
    index = next(
        (i for i, v in enumerate(versions) if str(v["valid_from"]) == valid_from), None
    )
    if index is None:
        raise TariffValidationError(f"no version valid from {valid_from}")
    if len(versions) == 1:
        raise TariffValidationError("the only version of a tariff cannot be deleted")
    deleted = versions.pop(index)
    if index == 0 and not {"preset", "zones"} & versions[0].keys():
        resolved = config_from_data({"tariffs": [dict(tariff_doc)]}).tariffs[0]
        zones = resolved.versions[1].zones
        start = str(versions[0]["valid_from"])
        preset = deleted.get("preset")
        if preset is not None:
            versions[0] = first_version_doc(
                start,
                [ZoneInput(z.key, z.name, z.price, z.periods) for z in zones],
                str(preset),
            )
        else:
            versions[0] = {
                "valid_from": start,
                "zones": [
                    _explicit_zone(ZoneInput(z.key, z.name, z.price, z.periods))
                    for z in zones
                ],
            }
    return _with_versions(tariff_doc, versions)


def diagnose_hours(zones: Sequence[tuple[str, tuple[Period, ...]]]) -> HoursProblems:
    """Hours that no zone covers and the zones that share an hour with another zone."""
    owners: dict[int, list[str]] = {}
    for key, periods in zones:
        for hour in sorted(_hours_of(periods)):
            owners.setdefault(hour, []).append(key)
    overlapping = frozenset(
        key for keys in owners.values() if len(keys) > 1 for key in keys
    )
    uncovered = tuple(hour for hour in range(24) if hour not in owners)
    return HoursProblems(uncovered=uncovered, overlapping=overlapping)


def format_hours(hours: Collection[int]) -> str:
    """Hours as ``"05:00-07:00, 22:00-23:00"``; a run across midnight is merged."""
    runs: list[list[int]] = []
    for hour in sorted(set(hours)):
        if runs and runs[-1][1] == hour:
            runs[-1][1] = hour + 1
        else:
            runs.append([hour, hour + 1])
    if len(runs) > 1 and runs[0][0] == 0 and runs[-1][1] == 24:
        last = runs.pop()
        runs[0][0] = last[0]
    return ", ".join(f"{start:02d}:00-{end:02d}:00" for start, end in runs)


def rename_references(
    applied: Sequence[tuple[str, str]],
    compare: Sequence[str] | None,
    old_id: str,
    new_id: str,
) -> tuple[tuple[tuple[str, str], ...], tuple[str, ...] | None]:
    """Replace ``old_id`` in the applied history and in an explicit compare list."""
    new_applied = tuple(
        (start, new_id if tariff == old_id else tariff) for start, tariff in applied
    )
    new_compare = (
        None
        if compare is None
        else tuple(new_id if item == old_id else item for item in compare)
    )
    return new_applied, new_compare


def move_applied_start(
    applied: Sequence[tuple[str, str]], tariff_id: str, old: str, new: str
) -> tuple[tuple[str, str], ...] | None:
    """Move the applied item ``(old, tariff_id)`` to ``new``; ``None`` if that reorders.

    The new start must stay strictly between the neighbouring applied items, otherwise
    later hours would silently be priced by another tariff. An absent item or an
    unchanged date returns the history unchanged.
    """
    items = tuple(sorted(applied))
    if old == new or (old, tariff_id) not in items:
        return items
    index = items.index((old, tariff_id))
    if index > 0 and items[index - 1][0] >= new:
        return None
    if index + 1 < len(items) and items[index + 1][0] <= new:
        return None
    return (*items[:index], (new, tariff_id), *items[index + 1 :])


def remove_from_applied(
    applied: Sequence[tuple[str, str]], first_versions: Mapping[str, str]
) -> tuple[tuple[str, str], ...]:
    """Drop applied items whose tariff is not in ``first_versions`` (id -> first date).

    The previous item simply continues over the freed period and equal neighbours
    merge. When the first item is dropped, the next remaining one takes over its start
    if that tariff has a version valid then, otherwise it keeps its own date. Without
    a dropped item the history is only sorted.
    """
    items = tuple(sorted(applied))
    kept = [item for item in items if item[1] in first_versions]
    if len(kept) == len(items):
        return items
    if kept and items[0][1] not in first_versions:
        tariff_id = kept[0][1]
        if first_versions[tariff_id] <= items[0][0]:
            kept[0] = (items[0][0], tariff_id)
    merged: list[tuple[str, str]] = []
    for item in kept:
        if not merged or merged[-1][1] != item[1]:
            merged.append(item)
    return tuple(merged)


def versions_table(tariff: Tariff) -> str:
    """A markdown table of the versions: start date and prices per zone."""
    lines = ["| Valid from | Prices |", "|---|---|"]
    for version in tariff.versions:
        prices = " · ".join(
            f"{zone.key} {_price_text(zone.price)}" for zone in version.zones
        )
        lines.append(f"| {version.valid_from.isoformat()} | {prices} |")
    return "\n".join(lines)
