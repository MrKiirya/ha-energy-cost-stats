"""The YAML normalizer and exporter (task 021)."""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pytest
from homeassistant.util.yaml import dump, parse_yaml
from jsonschema import Draft7Validator

from custom_components.energy_cost_stats.const import DEFAULT_SPIKE_LIMIT, DOMAIN
from custom_components.energy_cost_stats.yaml_config import (
    YamlConfigError,
    document_from_yaml,
    export_document,
)

FIXTURES = Path(__file__).parents[1] / "fixtures" / "yaml_config"
SCHEMA = json.loads(
    (Path(__file__).parents[2] / "schema" / "energy_cost_stats.schema.json").read_text(
        encoding="utf-8"
    )
)


def _parse(text: str) -> Any:
    return parse_yaml(text)


def _iso(value: Any) -> Any:
    """Dates as ISO strings, as an editor reads them."""
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _iso(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_iso(item) for item in value]
    return value


DEFAULT_SENSORS: dict[str, Any] = {
    "mode": "filter",
    "include": "all",
    "exclude": {},
    "overrides": {},
}
TZ = "Europe/Berlin"


def _load(raw: Any) -> Any:
    return document_from_yaml(
        raw, default_time_zone=TZ, default_sensors=DEFAULT_SENSORS
    )


def _flat(version_extra: dict[str, Any] | None = None) -> dict[str, Any]:
    version: dict[str, Any] = {
        "valid_from": "2026-01-01",
        "preset": "single_rate",
        "prices": {"t0": "7.40"},
    }
    version.update(version_extra or {})
    return {"id": "flat", "name": "Flat", "versions": [version]}


def test_full_design_example():
    raw = _parse((FIXTURES / "valid" / "full_example.yaml").read_text())
    document = _load(raw)
    assert document.options == {
        "time_zone": "Europe/Berlin",
        "spike_limit": "4",
        "sensors": {
            "mode": "filter",
            "include": {
                "entity_id": ["sensor.plug_01_energy"],
                "area_id": ["kitchen"],
                "label_id": ["cost_tracking"],
                "entity_globs": ["sensor.*_plug_*_energy"],
            },
            "exclude": {
                "entity_id": ["sensor.meter_t1", "sensor.meter_t2"],
                "entity_globs": ["sensor.sub_meter_*"],
            },
            "overrides": {
                "sensor.plug_01_energy": {"spike_limit": "6"},
                "sensor.plug_02_energy": {"spike_limit": None},
            },
        },
        "applied": [{"from": "2026-01-01", "tariff": "two_zone"}],
        "compare": ["single_rate", "three_zone"],
        "panel": {"show": True, "title": "Energy cost", "icon": "mdi:cash-multiple"},
    }
    assert [t["id"] for t in document.tariffs] == [
        "two_zone",
        "three_zone",
        "single_rate",
    ]
    assert document.tariffs[0]["versions"][0] == {
        "valid_from": "2026-01-01",
        "preset": "ru_two_zone",
        "prices": {"t1": "8.10", "t2": "3.20"},
    }
    assert document.tariffs[1]["versions"][0]["zones"][2] == {
        "key": "t2",
        "name": "Night",
        "price": "3.45",
        "hours": "23:00-07:00",
    }


@pytest.mark.parametrize("raw", [None, {}])
def test_defaults(raw):
    document = _load(raw)
    assert document.options == {
        "time_zone": TZ,
        "spike_limit": "4",
        "sensors": DEFAULT_SENSORS,
    }
    assert str(DEFAULT_SPIKE_LIMIT) == "4"
    assert document.tariffs == ()


def test_defaults_fill_partial_blocks():
    document = _load({"panel": {"show": True}, "sensors": {"mode": "filter"}})
    assert document.options["panel"] == {
        "show": True,
        "title": "Energy cost",
        "icon": "mdi:cash-multiple",
    }
    assert document.options["sensors"] == {
        "mode": "filter",
        "include": "all",
        "exclude": {},
        "overrides": {},
    }
    assert "applied" not in document.options
    assert "compare" not in document.options
    dashboard = _load({"sensors": {"mode": "energy_dashboard"}})
    assert dashboard.options["sensors"] == {
        "mode": "energy_dashboard",
        "exclude": {},
        "overrides": {},
    }


def test_spike_limit_null_disables_the_check():
    assert _load({"spike_limit": None}).options["spike_limit"] is None


@pytest.mark.parametrize(
    ("value", "expected", "limit"),
    [
        (5, "5", "5"),
        (8.1, "8.1", "8.1"),
        (1e-05, "0.00001", "0.00001"),
        ("8.10", "8.10", "8.1"),
    ],
)
def test_numbers_become_decimal_strings(value, expected, limit):
    sensors = {
        "mode": "filter",
        "overrides": {"sensor.plug_01": {"spike_limit": value}},
    }
    tariff = _flat({"prices": {"t0": value}})
    zone = {
        "id": "zoned",
        "name": "Zoned",
        "versions": [
            {
                "valid_from": date(2026, 1, 1),
                "zones": [
                    {"key": "t0", "name": "All", "price": value, "hours": "00:00-24:00"}
                ],
            }
        ],
    }
    document = _load({"sensors": sensors, "tariffs": [tariff, zone]})
    assert document.options["sensors"]["overrides"]["sensor.plug_01"] == {
        "spike_limit": limit
    }
    assert document.tariffs[0]["versions"][0]["prices"] == {"t0": expected}
    assert document.tariffs[1]["versions"][0]["zones"][0]["price"] == expected
    assert _load({"spike_limit": value}).options["spike_limit"] == limit


@pytest.mark.parametrize(
    "raw",
    [
        {"spike_limit": True},
        {"tariffs": [_flat({"prices": {"t0": True}})]},
        {"sensors": {"mode": "filter", "overrides": {"a": {"spike_limit": True}}}},
    ],
)
def test_booleans_are_not_numbers(raw):
    with pytest.raises(YamlConfigError, match="boolean"):
        _load(raw)


def test_dates():
    for value in (date(2026, 1, 1), "2026-01-01"):
        document = _load(
            {
                "tariffs": [_flat({"valid_from": value})],
                "applied": [{"from": value, "tariff": "flat"}],
            }
        )
        assert document.tariffs[0]["versions"][0]["valid_from"] == "2026-01-01"
        assert document.options["applied"] == [{"from": "2026-01-01", "tariff": "flat"}]
    with pytest.raises(YamlConfigError, match=r"versions\[0\]\.valid_from"):
        _load({"tariffs": [_flat({"valid_from": datetime(2026, 1, 1, 12)})]})
    with pytest.raises(YamlConfigError, match="YYYY-MM-DD"):
        _load({"tariffs": [_flat({"valid_from": "2026-1-1"})]})
    with pytest.raises(YamlConfigError, match=r"applied\[0\]\.from"):
        _load({"tariffs": [_flat()], "applied": [{"from": 5, "tariff": "flat"}]})


def test_applied_short_form():
    second = {"valid_from": date(2026, 6, 1), "prices": {"t0": 8}}
    tariff = _flat()
    tariff["versions"].append(second)
    document = _load({"tariffs": [tariff], "applied": "flat"})
    assert document.options["applied"] == [{"from": "2026-01-01", "tariff": "flat"}]
    with pytest.raises(YamlConfigError, match="unknown tariff 'nope'"):
        _load({"tariffs": [tariff], "applied": "nope"})
    with pytest.raises(YamlConfigError, match="no version"):
        _load(
            {
                "tariffs": [{"id": "flat", "name": "x", "versions": []}],
                "applied": "flat",
            }
        )


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (["a"], "energy_cost_stats: must be a mapping"),
        ("text", "energy_cost_stats: must be a mapping"),
        ({"currency": "EUR"}, "unknown keys currency"),
        ({"panel": {"colour": 1}}, "panel: unknown keys colour"),
        ({"panel": None}, "panel: must be a mapping"),
        ({"sensors": {"mode": "filter", "x": 1}}, "sensors: unknown keys x"),
        ({"sensors": {}}, "sensors.mode: required"),
        (
            {"sensors": {"mode": "filter", "include": {"zone": []}}},
            "sensors.include: unknown keys zone",
        ),
        (
            {"sensors": {"mode": "filter", "overrides": {"a": {"x": 1}}}},
            "sensors.overrides.a: unknown keys x",
        ),
        ({"sensors": {"mode": "filter", "overrides": []}}, "sensors.overrides"),
        ({"tariffs": {}}, "tariffs: must be a list"),
        ({"tariffs": ["x"]}, r"tariffs\[0\]: must be a mapping"),
        ({"tariffs": [{"id": "a", "extra": 1}]}, r"tariffs\[0\]: unknown keys extra"),
        (
            {"tariffs": [_flat({"tax": 1})]},
            r"tariffs\[0\]\.versions\[0\]: unknown keys tax",
        ),
        (
            {
                "tariffs": [
                    _flat(
                        {
                            "preset": None,
                            "prices": None,
                            "zones": [{"key": "t0", "colour": 1}],
                        }
                    )
                ]
            },
            r"versions\[0\]\.zones\[0\]: unknown keys colour",
        ),
        ({"tariffs": [_flat(), _flat()]}, "duplicate tariff id"),
        (
            {
                "tariffs": [
                    {
                        "id": "two",
                        "name": "Two",
                        "versions": [
                            {
                                "valid_from": "2026-01-01",
                                "zones": [
                                    {
                                        "key": "a",
                                        "name": "A",
                                        "price": "1",
                                        "hours": "00:00-12:00",
                                    },
                                    {
                                        "key": "b",
                                        "name": "B",
                                        "price": "1",
                                        "hours": "10:00-24:00",
                                    },
                                ],
                            }
                        ],
                    }
                ]
            },
            "covered by zones",
        ),
        ({"tariffs": [_flat({"prices": {"t9": "1"}})]}, "prices must name exactly"),
        (
            {
                "tariffs": [_flat()],
                "applied": [{"from": "2025-01-01", "tariff": "flat"}],
            },
            "has no version valid on 2025-01-01",
        ),
        (
            {"applied": [{"from": "2026-01-01", "tariff": "x", "y": 1}]},
            "applied\\[0\\]",
        ),
        ({"applied": "a"}, "unknown tariff"),
        ({"compare": ["nope"]}, "compare: unknown tariff"),
        (
            {"sensors": {"mode": "filter", "exclude": {"entity_globs": ["Bad Glob"]}}},
            "invalid patterns",
        ),
        ({"spike_limit": 0}, "spike_limit"),
    ],
)
def test_rejects_invalid(raw, message):
    with pytest.raises(YamlConfigError, match=message):
        _load(raw)


STORED_TARIFFS: list[dict[str, Any]] = [
    _flat(),
    {
        "id": "two_zone",
        "name": "Два тарифа",
        "versions": [
            {
                "valid_from": "2026-01-01",
                "preset": "ru_two_zone",
                "prices": {"t1": "8.10", "t2": "3.20"},
                "hours": {"t1": "06:00-22:00", "t2": "22:00-06:00"},
            },
            {"valid_from": "2026-07-01", "prices": {"t1": "8.75", "t2": "3.45"}},
        ],
    },
]
STORED_BASE: dict[str, Any] = {
    "time_zone": "Europe/Berlin",
    "spike_limit": "4",
    "sensors": {
        "mode": "filter",
        "include": {"entity_id": ["sensor.plug_01"], "entity_globs": ["sensor.*_x"]},
        "exclude": {},
        "overrides": {"sensor.plug_01": {"spike_limit": None}},
    },
}


@pytest.mark.parametrize(
    "options",
    [
        STORED_BASE,
        {**STORED_BASE, "spike_limit": None},
        {
            **STORED_BASE,
            "applied": [
                {"from": "2026-01-01", "tariff": "flat"},
                {"from": "2026-07-01", "tariff": "two_zone"},
            ],
            "compare": ["flat"],
            "panel": {"show": True, "title": "Cost", "icon": "mdi:flash"},
        },
        {
            **STORED_BASE,
            "sensors": {
                "mode": "energy_dashboard",
                "exclude": {"label_id": ["meter"]},
                "overrides": {"sensor.plug_01": {"spike_limit": "6.5"}},
            },
            "compare": [],
        },
    ],
)
def test_export_round_trip(options):
    exported = export_document(options, STORED_TARIFFS)
    text = dump({DOMAIN: exported})
    assert text.startswith("energy_cost_stats:\n")
    keys = list(exported)
    assert keys[:2] == ["time_zone", "spike_limit"]
    assert keys.index("sensors") < keys.index("tariffs")
    assert "valid_from: 2026-01-01\n" in text
    assert "'8.10'" in text or '"8.10"' in text
    parsed = _parse(text)[DOMAIN]
    assert not list(Draft7Validator(SCHEMA).iter_errors(_iso(parsed)))
    document = _load(parsed)
    assert document.options == options
    assert list(document.tariffs) == STORED_TARIFFS


def test_export_key_order_and_optional_parts():
    options = {
        **STORED_BASE,
        "applied": [{"from": "2026-01-01", "tariff": "flat"}],
        "compare": ["flat"],
        "panel": {"show": False, "title": "T", "icon": "mdi:x"},
    }
    keys = list(export_document(options, STORED_TARIFFS))
    assert keys == [
        "time_zone",
        "spike_limit",
        "panel",
        "sensors",
        "tariffs",
        "applied",
        "compare",
    ]
    bare = list(export_document(STORED_BASE, []))
    assert bare == ["time_zone", "spike_limit", "sensors", "tariffs"]
    unparsable = export_document(
        STORED_BASE, [{"id": "x", "name": "x", "versions": [{"valid_from": "soon"}]}]
    )
    assert unparsable["tariffs"][0]["versions"][0]["valid_from"] == "soon"


def test_yaml_loader_types():
    raw = _parse(
        "tariffs:\n"
        "  - id: flat\n"
        "    name: Flat\n"
        "    versions:\n"
        "      - valid_from: 2026-01-01\n"
        "        preset: single_rate\n"
        "        prices: { t0: 7.4 }\n"
    )
    version = raw["tariffs"][0]["versions"][0]
    assert type(version["valid_from"]) is date
    assert type(version["prices"]["t0"]) is float
    document = _load(raw)
    assert document.tariffs[0]["versions"][0]["valid_from"] == "2026-01-01"
    assert document.tariffs[0]["versions"][0]["prices"] == {"t0": "7.4"}
