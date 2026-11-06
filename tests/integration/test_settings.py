"""Settings mapping: options dict <-> IntegrationSettings (no hass needed)."""

from dataclasses import FrozenInstanceError
from decimal import Decimal
from typing import Any

import pytest

from custom_components.energy_cost_stats.settings import (
    IntegrationSettings,
    PanelSettings,
    SettingsError,
    settings_from_options,
    settings_to_options,
    tariff_document,
)

EXAMPLE: dict[str, Any] = {
    "time_zone": "Europe/Berlin",
    "spike_limit": "4",
    "device_spike_limits": {"sensor.plug_01": "10", "sensor.plug_02": None},
    "entities": ["sensor.plug_01", "sensor.plug_02"],
}


def _with(**changes: Any) -> dict[str, Any]:
    options = {**EXAMPLE, **changes}
    return {k: v for k, v in options.items() if v is not ...}


def test_roundtrip():
    settings = settings_from_options(EXAMPLE)
    assert settings.time_zone == "Europe/Berlin"
    assert settings.spike_limit == Decimal("4")
    assert dict(settings.device_spike_limits) == {
        "sensor.plug_01": Decimal("10"),
        "sensor.plug_02": None,
    }
    assert settings.entities == ("sensor.plug_01", "sensor.plug_02")
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
            device_spike_limits={},
            entities=(),
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
        _with(device_spike_limits={"sensor.plug_01": "0"}),
        _with(device_spike_limits={"": "5"}),
        _with(entities="sensor.plug_01"),
        _with(entities=["sensor.plug_01", 5]),
        _with(entities=["sensor.plug_01", "sensor.plug_01"]),
        _with(time_zone=...),
        _with(time_zone=5),
        _with(unknown_key=1),
    ],
)
def test_invalid_options(options: dict[str, Any]):
    with pytest.raises(SettingsError):
        settings_from_options(options)


def test_device_limits_read_only():
    settings = settings_from_options(EXAMPLE)
    with pytest.raises(TypeError):
        settings.device_spike_limits["sensor.plug_01"] = Decimal("1")  # type: ignore[index]
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
