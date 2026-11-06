"""Settings mapping: options dict <-> IntegrationSettings (no hass needed)."""

from dataclasses import FrozenInstanceError
from decimal import Decimal
from typing import Any

import pytest

from custom_components.energy_cost_stats.engine.sensors import (
    SensorMode,
    SensorSettings,
)
from custom_components.energy_cost_stats.settings import (
    IntegrationSettings,
    PanelSettings,
    SettingsError,
    migrate_sensor_options,
    settings_from_options,
    settings_to_options,
    tariff_document,
)

EXAMPLE: dict[str, Any] = {
    "time_zone": "Europe/Berlin",
    "spike_limit": "4",
    "sensors": {
        "mode": "filter",
        "include": {"entity_id": ["sensor.plug_01", "sensor.plug_02"]},
        "exclude": {},
        "overrides": {
            "sensor.plug_01": {"spike_limit": "10"},
            "sensor.plug_02": {"spike_limit": None},
        },
    },
}


def _sensors(**changes: Any) -> dict[str, Any]:
    sensors = {**EXAMPLE["sensors"], **changes}
    return _with(sensors={k: v for k, v in sensors.items() if v is not ...})


def _with(**changes: Any) -> dict[str, Any]:
    options = {**EXAMPLE, **changes}
    return {k: v for k, v in options.items() if v is not ...}


def test_roundtrip():
    settings = settings_from_options(EXAMPLE)
    assert settings.time_zone == "Europe/Berlin"
    assert settings.spike_limit == Decimal("4")
    assert dict(settings.sensors.spike_limits()) == {
        "sensor.plug_01": Decimal("10"),
        "sensor.plug_02": None,
    }
    assert settings.sensors.mode is SensorMode.FILTER
    assert settings.sensors.include is not None
    assert settings.sensors.include.entity_id == ("sensor.plug_01", "sensor.plug_02")
    assert settings_to_options(settings) == EXAMPLE


def test_null_spike_limit_disables():
    settings = settings_from_options(_with(spike_limit=None))
    assert settings.spike_limit is None
    assert settings_to_options(settings)["spike_limit"] is None


def test_decimal_normalization():
    def stored(value: str) -> Any:
        settings = IntegrationSettings(
            time_zone="UTC",
            spike_limit=Decimal(value),
            sensors=SensorSettings(mode=SensorMode.FILTER),
        )
        return settings_to_options(settings)["spike_limit"]

    assert stored("4.0") == "4"
    assert stored("2.50") == "2.5"
    assert stored("0.125") == "0.125"
    assert stored("1E+1") == "10"


@pytest.mark.parametrize(
    "options",
    [
        _with(spike_limit="0"),
        _with(spike_limit="-1"),
        _with(spike_limit="abc"),
        _with(spike_limit="NaN"),
        _with(spike_limit="Infinity"),
        _with(spike_limit=4),
        _with(spike_limit=4.0),
        _with(spike_limit=True),
        _with(time_zone=...),
        _with(time_zone=5),
        _with(unknown_key=1),
    ],
)
def test_invalid_options(options: dict[str, Any]):
    with pytest.raises(SettingsError):
        settings_from_options(options)


def test_overrides_read_only():
    settings = settings_from_options(EXAMPLE)
    with pytest.raises(TypeError):
        settings.sensors.overrides["sensor.plug_01"] = None  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        settings.time_zone = "UTC"  # type: ignore[misc]


APPLIED = [
    {"from": "2026-01-01", "tariff": "two_zone"},
    {"from": "2026-07-01", "tariff": "single"},
]


def test_applied_and_compare_roundtrip():
    options = _with(applied=APPLIED, compare=["three_zone"])
    settings = settings_from_options(options)
    assert settings.applied == (
        ("2026-01-01", "two_zone"),
        ("2026-07-01", "single"),
    )
    assert settings.compare == ("three_zone",)
    assert settings_to_options(settings) == options


def test_applied_and_compare_absent_when_unset():
    settings = settings_from_options(EXAMPLE)
    assert settings.applied == ()
    assert settings.compare is None
    written = settings_to_options(settings)
    assert "applied" not in written
    assert "compare" not in written


def test_empty_compare_list_is_kept():
    settings = settings_from_options(_with(compare=[]))
    assert settings.compare == ()
    assert settings_to_options(settings)["compare"] == []


@pytest.mark.parametrize(
    "bad",
    [
        "two_zone",
        {"from": "2026-01-01", "tariff": "a"},
        ["two_zone"],
        [{"from": "2026-01-01"}],
        [{"from": "2026-01-01", "tariff": "a", "extra": 1}],
        [{"from": 20260101, "tariff": "a"}],
        [{"from": "2026-01-01", "tariff": None}],
    ],
)
def test_rejects_malformed_applied(bad: Any):
    with pytest.raises(SettingsError, match="applied"):
        settings_from_options(_with(applied=bad))


@pytest.mark.parametrize("bad", ["single", ["single", 5], {"a": "b"}])
def test_rejects_malformed_compare(bad: Any):
    with pytest.raises(SettingsError, match="compare"):
        settings_from_options(_with(compare=bad))


PANEL = {"show": True, "title": "Energy cost", "icon": "mdi:cash-multiple"}


def test_panel_round_trip():
    options = _with(panel=PANEL)
    settings = settings_from_options(options)
    assert settings.panel == PanelSettings(True, "Energy cost", "mdi:cash-multiple")
    assert settings_to_options(settings) == options


def test_panel_absent_is_none_and_not_written():
    settings = settings_from_options(EXAMPLE)
    assert settings.panel is None
    assert "panel" not in settings_to_options(settings)


@pytest.mark.parametrize(
    "bad",
    [
        "yes",
        {**PANEL, "extra": 1},
        {**PANEL, "show": "true"},
        {**PANEL, "title": "  "},
        {**PANEL, "icon": ""},
        {"show": True, "title": "Energy cost"},
    ],
)
def test_panel_rejects_malformed(bad: Any):
    with pytest.raises(SettingsError):
        settings_from_options(_with(panel=bad))


def test_tariff_document():
    tariffs = [{"id": "a", "name": "A", "versions": []}]
    settings = settings_from_options(
        _with(applied=[{"from": "2026-01-01", "tariff": "a"}])
    )
    assert tariff_document(settings, tariffs) == {
        "tariffs": tariffs,
        "applied": [{"from": "2026-01-01", "tariff": "a"}],
    }
    with_compare = settings_from_options(_with(compare=["a"]))
    assert tariff_document(with_compare, tariffs) == {
        "tariffs": tariffs,
        "applied": [],
        "compare": ["a"],
    }


DASHBOARD = {"mode": "energy_dashboard", "exclude": {}, "overrides": {}}
FILTER_ALL = {"mode": "filter", "include": "all", "exclude": {}, "overrides": {}}
FULL_TARGET = {
    "entity_id": ["sensor.plug_01_energy"],
    "device_id": ["dev1"],
    "area_id": ["kitchen"],
    "floor_id": ["ground"],
    "label_id": ["cost_tracking"],
    "entity_globs": ["sensor.*_plug_*_energy"],
}


@pytest.mark.parametrize(
    "sensors",
    [
        DASHBOARD,
        {**DASHBOARD, "exclude": {"entity_id": ["sensor.main_meter_t1"]}},
        FILTER_ALL,
        {**FILTER_ALL, "include": FULL_TARGET, "exclude": FULL_TARGET},
        {
            **FILTER_ALL,
            "overrides": {
                "sensor.a": {"spike_limit": "6"},
                "sensor.b": {"spike_limit": None},
            },
        },
    ],
)
def test_sensors_round_trip(sensors: dict[str, Any]):
    options = _with(sensors=sensors)
    assert settings_to_options(settings_from_options(options)) == options


def test_sensors_decimal_limit_normalized():
    sensors = {**FILTER_ALL, "overrides": {"sensor.a": {"spike_limit": "6.50"}}}
    written = settings_to_options(settings_from_options(_with(sensors=sensors)))
    assert written["sensors"]["overrides"]["sensor.a"] == {"spike_limit": "6.5"}


@pytest.mark.parametrize(
    "sensors",
    [
        {**FILTER_ALL, "mode": "other"},
        {**DASHBOARD, "include": "all"},
        {**DASHBOARD, "include": {"entity_id": ["sensor.a"]}},
        {k: v for k, v in FILTER_ALL.items() if k != "include"},
        {**FILTER_ALL, "include": {}},
        {**FILTER_ALL, "include": "everything"},
        {**FILTER_ALL, "include": {"unknown": ["a"]}},
        {**FILTER_ALL, "include": {"area_id": "kitchen"}},
        {**FILTER_ALL, "include": {"area_id": ["a", "a"]}},
        {**FILTER_ALL, "include": {"area_id": [""]}},
        {**FILTER_ALL, "include": {"area_id": [5]}},
        {**FILTER_ALL, "exclude": {"unknown": ["a"]}},
        {**FILTER_ALL, "exclude": "all"},
        {**FILTER_ALL, "include": {"entity_globs": ["Sensor.*"]}},
        {**FILTER_ALL, "exclude": {"entity_globs": ["sensor. x"]}},
        {**FILTER_ALL, "overrides": {"sensor.a": {}}},
        {**FILTER_ALL, "overrides": {"sensor.a": {"spike_limit": "4", "x": 1}}},
        {**FILTER_ALL, "overrides": {"sensor.a": {"spike_limit": "0"}}},
        {**FILTER_ALL, "overrides": {"sensor.a": {"spike_limit": 4}}},
        {**FILTER_ALL, "overrides": {"": {"spike_limit": "4"}}},
        {**FILTER_ALL, "overrides": ["sensor.a"]},
        {**FILTER_ALL, "extra": 1},
        {k: v for k, v in FILTER_ALL.items() if k != "overrides"},
        {k: v for k, v in FILTER_ALL.items() if k != "exclude"},
        "all",
    ],
)
def test_sensors_rejects_malformed(sensors: Any):
    with pytest.raises(SettingsError):
        settings_from_options(_with(sensors=sensors))


@pytest.mark.parametrize(
    "extra",
    [
        {"entities": ["sensor.plug_01"]},
        {"device_spike_limits": {"sensor.plug_01": "5"}},
    ],
)
def test_old_sensor_keys_rejected(extra: dict[str, Any]):
    with pytest.raises(SettingsError):
        settings_from_options({**EXAMPLE, **extra})


def test_sensors_required():
    with pytest.raises(SettingsError, match="sensors"):
        settings_from_options(_with(sensors=...))


def test_migrate_sensor_options():
    default = {
        "mode": "energy_dashboard",
        "exclude": {},
        "overrides": {},
    }
    old = {
        "time_zone": "UTC",
        "spike_limit": "4",
        "entities": ["sensor.a", "sensor.b"],
        "device_spike_limits": {"sensor.a": "10", "sensor.b": None},
        "applied": APPLIED,
    }
    migrated = migrate_sensor_options(old, default)
    assert migrated == {
        "time_zone": "UTC",
        "spike_limit": "4",
        "applied": APPLIED,
        "sensors": {
            "mode": "filter",
            "include": {"entity_id": ["sensor.a", "sensor.b"]},
            "exclude": {},
            "overrides": {
                "sensor.a": {"spike_limit": "10"},
                "sensor.b": {"spike_limit": None},
            },
        },
    }
    assert "entities" in old  # the input is not modified
    settings_from_options(migrated)

    empty = {**old, "entities": [], "device_spike_limits": {"sensor.c": "3"}}
    migrated = migrate_sensor_options(empty, default)
    assert migrated["sensors"] == {
        **default,
        "overrides": {"sensor.c": {"spike_limit": "3"}},
    }
    bare = migrate_sensor_options({"time_zone": "UTC", "spike_limit": "4"}, FILTER_ALL)
    assert bare["sensors"] == FILTER_ALL
    # Already migrated options are returned unchanged.
    assert migrate_sensor_options(migrated, FILTER_ALL) == migrated
