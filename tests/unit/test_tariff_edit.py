"""Unit tests for the pure tariff editing helpers (tasks/018)."""

import copy
import re
from decimal import Decimal
from typing import Any

import pytest

from engine.plan_codec import parse_periods
from engine.tariff import TariffValidationError, Zone
from engine.tariff_config import config_from_data
from engine.tariff_edit import (
    ZoneInput,
    delete_version,
    diagnose_hours,
    first_version_doc,
    format_hours,
    later_version_doc,
    move_applied_start,
    normalize_price,
    remove_from_applied,
    rename_references,
    replace_version,
    unique_tariff_id,
    versions_table,
)

ID_RE = re.compile(r"[a-z0-9_]{1,32}")


def zi(key: str, name: str, price: str, hours: str) -> ZoneInput:
    return ZoneInput(key, name, Decimal(price), parse_periods(hours))


DAY = zi("t1", "Day", "10.30", "07:00-23:00")
NIGHT = zi("t2", "Night", "4.43", "23:00-07:00")


def tariff_doc(*versions: dict[str, Any]) -> dict[str, Any]:
    return {"id": "two_zone", "name": "Two-zone", "versions": list(versions)}


def resolved(doc: dict[str, Any]) -> list[Any]:
    config = config_from_data({"tariffs": [doc]})
    return [(v.valid_from, v.zones) for v in config.tariffs[0].versions]


def test_normalize_price():
    assert normalize_price("10,30") == "10.30"
    assert normalize_price(" 4.43 ") == "4.43"
    assert normalize_price("0") == "0"
    for bad in ("-1", "1e3", "abc", ""):
        with pytest.raises(TariffValidationError):
            normalize_price(bad)


def test_unique_tariff_id():
    assert unique_tariff_id("two_zone", set()) == "two_zone"
    assert unique_tariff_id("two_zone", {"two_zone"}) == "two_zone_2"
    assert unique_tariff_id("two_zone", {"two_zone", "two_zone_2"}) == "two_zone_3"
    assert unique_tariff_id("", set()) == "tariff"
    assert unique_tariff_id("Ünï-Čode!", set()) == "node"
    long = "a" * 40
    assert unique_tariff_id(long, set()) == "a" * 32
    suffixed = unique_tariff_id(long, {"a" * 32})
    assert suffixed == "a" * 30 + "_2"
    for value in (suffixed, unique_tariff_id("!!!", set())):
        assert ID_RE.fullmatch(value)


def test_first_version_doc_keeps_preset():
    doc = first_version_doc("2026-01-01", [DAY, NIGHT], "ru_two_zone")
    assert doc == {
        "valid_from": "2026-01-01",
        "preset": "ru_two_zone",
        "prices": {"t1": "10.30", "t2": "4.43"},
    }
    config_from_data({"tariffs": [tariff_doc(doc)]})

    changed = first_version_doc(
        "2026-01-01",
        [
            zi("t1", "Day", "10.30", "06:00-23:00"),
            zi("t2", "Night", "4.43", "23:00-06:00"),
        ],
        "ru_two_zone",
    )
    assert changed["hours"] == {"t1": "06:00-23:00", "t2": "23:00-06:00"}
    config_from_data({"tariffs": [tariff_doc(changed)]})

    partly = first_version_doc(
        "2026-01-01",
        [
            zi("t1", "Day", "10.30", "07:00-23:00"),
            zi("t2", "Night", "4.43", "23:00-07:00"),
        ],
        "ru_two_zone",
    )
    assert "hours" not in partly


def test_first_version_doc_renamed_zone_is_explicit():
    peak = zi("t1", "Peak day", "10.30", "07:00-23:00")
    doc = first_version_doc("2026-01-01", [peak, NIGHT], "ru_two_zone")
    assert "preset" not in doc
    assert doc["zones"] == [
        {"key": "t1", "name": "Peak day", "price": "10.30", "hours": "07:00-23:00"},
        {"key": "t2", "name": "Night", "price": "4.43", "hours": "23:00-07:00"},
    ]
    config_from_data({"tariffs": [tariff_doc(doc)]})


def test_first_version_doc_custom():
    zones = [
        zi("b", "B", "1", "00:00-08:00"),
        zi("a", "A", "2.5", "08:00-16:00"),
        zi("c", "C", "3", "16:00-24:00"),
    ]
    doc = first_version_doc("2026-01-01", zones, None)
    assert [z["key"] for z in doc["zones"]] == ["b", "a", "c"]
    assert doc["zones"][1] == {
        "key": "a",
        "name": "A",
        "price": "2.5",
        "hours": "08:00-16:00",
    }
    config_from_data({"tariffs": [tariff_doc(doc)]})


def inherited() -> list[Zone]:
    return [Zone(z.key, z.name, z.price, z.periods) for z in (DAY, NIGHT)]


def test_later_version_doc():
    same = later_version_doc(
        "2026-07-01",
        {"t1": Decimal("11.00"), "t2": Decimal("4.60")},
        {"t1": DAY.periods, "t2": NIGHT.periods},
        inherited(),
    )
    assert same == {"valid_from": "2026-07-01", "prices": {"t1": "11.00", "t2": "4.60"}}
    one = later_version_doc(
        "2026-07-01",
        {"t1": Decimal("11.00"), "t2": Decimal("4.60")},
        {"t1": parse_periods("06:00-23:00"), "t2": NIGHT.periods},
        inherited(),
    )
    assert one["hours"] == {"t1": "06:00-23:00"}


def test_replace_version():
    first = {
        "valid_from": "2026-01-01",
        "preset": "ru_two_zone",
        "prices": {"t1": "1", "t2": "2"},
    }
    last = {"valid_from": "2026-09-01", "prices": {"t1": "3", "t2": "4"}}
    doc = tariff_doc(first, last)
    original = copy.deepcopy(doc)
    middle = {"valid_from": "2026-05-01", "prices": {"t1": "5", "t2": "6"}}
    inserted = replace_version(doc, None, middle)
    assert [v["valid_from"] for v in inserted["versions"]] == [
        "2026-01-01",
        "2026-05-01",
        "2026-09-01",
    ]
    moved = {"valid_from": "2026-12-01", "prices": {"t1": "7", "t2": "8"}}
    replaced = replace_version(inserted, "2026-05-01", moved)
    assert [v["valid_from"] for v in replaced["versions"]] == [
        "2026-01-01",
        "2026-09-01",
        "2026-12-01",
    ]
    assert doc == original
    with pytest.raises(TariffValidationError):
        replace_version(doc, "2030-01-01", middle)


def test_delete_version():
    first = {
        "valid_from": "2026-01-01",
        "preset": "ru_two_zone",
        "prices": {"t1": "1", "t2": "2"},
        "hours": {"t1": "06:00-23:00", "t2": "23:00-06:00"},
    }
    second = {"valid_from": "2026-05-01", "prices": {"t1": "3", "t2": "4"}}
    third = {"valid_from": "2026-09-01", "prices": {"t1": "5", "t2": "6"}}
    doc = tariff_doc(first, second, third)

    assert [v["valid_from"] for v in delete_version(doc, "2026-05-01")["versions"]] == [
        "2026-01-01",
        "2026-09-01",
    ]
    assert [v["valid_from"] for v in delete_version(doc, "2026-09-01")["versions"]] == [
        "2026-01-01",
        "2026-05-01",
    ]
    with pytest.raises(TariffValidationError):
        delete_version(tariff_doc(first), "2026-01-01")
    with pytest.raises(TariffValidationError):
        delete_version(doc, "2030-01-01")

    before = resolved(doc)
    after_doc = delete_version(doc, "2026-01-01")
    assert after_doc["versions"][0]["preset"] == "ru_two_zone"
    assert resolved(after_doc) == before[1:]

    explicit_first = {
        "valid_from": "2026-01-01",
        "zones": [
            {"key": "a", "name": "A", "price": "1", "hours": "00:00-12:00"},
            {"key": "b", "name": "B", "price": "2", "hours": "12:00-24:00"},
        ],
    }
    explicit = tariff_doc(
        explicit_first,
        {
            "valid_from": "2026-05-01",
            "prices": {"a": "3", "b": "4"},
            "hours": {"a": "00:00-10:00", "b": "10:00-24:00"},
        },
    )
    after_explicit = delete_version(explicit, "2026-01-01")
    assert "zones" in after_explicit["versions"][0]
    assert resolved(after_explicit) == resolved(explicit)[1:]

    own_set = tariff_doc(
        first,
        {"valid_from": "2026-05-01", "preset": "single_rate", "prices": {"t0": "1"}},
    )
    assert delete_version(own_set, "2026-01-01")["versions"] == [own_set["versions"][1]]


def test_diagnose_hours():
    def problems(a: str, b: str):
        return diagnose_hours([("t1", parse_periods(a)), ("t2", parse_periods(b))])

    ok = problems("07:00-23:00", "23:00-07:00")
    assert ok.uncovered == ()
    assert ok.overlapping == frozenset()
    gap = problems("07:00-22:00", "23:00-07:00")
    assert gap.uncovered == (22,)
    assert gap.overlapping == frozenset()
    overlap = problems("06:00-23:00", "23:00-07:00")
    assert overlap.overlapping == frozenset({"t1", "t2"})
    assert overlap.uncovered == ()


def test_rename_references():
    applied = (("2026-01-01", "old"), ("2026-03-01", "other"))
    new_applied, new_compare = rename_references(applied, ("old", "x"), "old", "new")
    assert new_applied == (("2026-01-01", "new"), ("2026-03-01", "other"))
    assert new_compare == ("new", "x")
    _, none_compare = rename_references(applied, None, "old", "new")
    assert none_compare is None


def test_versions_table():
    config = config_from_data(
        {
            "tariffs": [
                tariff_doc(
                    {
                        "valid_from": "2026-01-01",
                        "preset": "ru_two_zone",
                        "prices": {"t1": "10.30", "t2": "4.43"},
                    },
                    {
                        "valid_from": "2026-07-01",
                        "prices": {"t1": "11.00", "t2": "4.60"},
                    },
                )
            ]
        }
    )
    lines = versions_table(config.tariffs[0]).splitlines()
    assert len(lines) == 4
    assert "Valid from" in lines[0]
    assert "2026-01-01" in lines[2]
    assert "t1 10.30 · t2 4.43" in lines[2]
    assert "t1 11.00 · t2 4.60" in lines[3]


def test_format_hours():
    assert format_hours([22]) == "22:00-23:00"
    assert format_hours([5, 6, 22]) == "05:00-07:00, 22:00-23:00"
    assert format_hours([23, 0, 1]) == "23:00-02:00"
    assert format_hours(range(24)) == "00:00-24:00"
    assert format_hours([]) == ""


def test_move_applied_start():
    applied = (("2026-01-01", "a"), ("2026-05-01", "b"))
    assert move_applied_start(applied, "a", "2026-01-01", "2025-12-01") == (
        ("2025-12-01", "a"),
        ("2026-05-01", "b"),
    )
    assert move_applied_start(applied, "a", "2026-01-01", "2026-04-30") == (
        ("2026-04-30", "a"),
        ("2026-05-01", "b"),
    )
    # Not strictly before the next item, or not after the previous one: rejected.
    assert move_applied_start(applied, "a", "2026-01-01", "2026-05-01") is None
    assert move_applied_start(applied, "a", "2026-01-01", "2026-07-01") is None
    assert move_applied_start(applied, "b", "2026-05-01", "2026-01-01") is None
    assert move_applied_start(applied, "b", "2026-05-01", "2025-12-01") is None
    # Nothing to move: unchanged.
    assert move_applied_start(applied, "a", "2026-02-01", "2026-03-01") == applied
    assert move_applied_start(applied, "a", "2026-01-01", "2026-01-01") == applied


def test_remove_from_applied():
    firsts = {"a": "2026-01-01", "b": "2026-04-01", "c": "2026-01-01"}
    # A middle or last entry: the previous one continues; equal neighbours merge.
    assert remove_from_applied(
        (("2026-01-01", "a"), ("2026-03-01", "x"), ("2026-05-01", "a")), firsts
    ) == (("2026-01-01", "a"),)
    assert remove_from_applied((("2026-01-01", "a"), ("2026-05-01", "x")), firsts) == (
        ("2026-01-01", "a"),
    )
    # The first entry: the next takes over its period when it has a version then.
    assert remove_from_applied((("2026-03-01", "x"), ("2026-05-01", "c")), firsts) == (
        ("2026-03-01", "c"),
    )
    # Otherwise it keeps its own date.
    assert remove_from_applied((("2026-03-01", "x"), ("2026-05-01", "b")), firsts) == (
        ("2026-05-01", "b"),
    )
    # Everything removed.
    assert remove_from_applied((("2026-03-01", "x"),), firsts) == ()
    # No deleted tariff: only sorted, nothing merged away.
    assert remove_from_applied((("2026-05-01", "a"), ("2026-01-01", "b")), firsts) == (
        ("2026-01-01", "b"),
        ("2026-05-01", "a"),
    )
