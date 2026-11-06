"""Unit tests for engine.sensors (tasks/020-sensors.md)."""

from decimal import Decimal
from typing import Any

import pytest

from engine.sensors import (
    Candidate,
    DashboardDevice,
    SensorMode,
    SensorOverride,
    SensorSettings,
    SensorTarget,
    is_valid_glob,
    select_sensors,
    upstreams,
)

pytestmark = pytest.mark.unit


def cand(entity_id: str, **kwargs: Any) -> Candidate:
    return Candidate(entity_id=entity_id, **kwargs)


def filter_settings(
    include: SensorTarget | None = None,
    exclude: SensorTarget | None = None,
    **kwargs: Any,
) -> SensorSettings:
    return SensorSettings(
        mode=SensorMode.FILTER,
        include=include,
        exclude=exclude or SensorTarget(),
        **kwargs,
    )


CANDIDATES = (
    cand("sensor.b_plug_1_energy", device_id="dev1", area_id="kitchen"),
    cand(
        "sensor.a_plug_2_energy",
        device_id="dev2",
        area_id="hall",
        floor_id="ground",
        labels=frozenset({"tracked"}),
    ),
    cand("sensor.c_meter_energy", eligible=False, area_id="kitchen"),
    cand("sensor.D_Plug_3_energy"),
)


def test_filter_all_takes_eligible_only():
    selection = select_sensors(filter_settings(), CANDIDATES, ())
    assert selection.sensors == (
        "sensor.D_Plug_3_energy",
        "sensor.a_plug_2_energy",
        "sensor.b_plug_1_energy",
    )


def test_include_entity_id_even_if_not_eligible():
    include = SensorTarget(entity_id=("sensor.c_meter_energy", "sensor.gone_energy"))
    selection = select_sensors(filter_settings(include), CANDIDATES, ())
    assert selection.sensors == ("sensor.c_meter_energy", "sensor.gone_energy")


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        (SensorTarget(device_id=("dev1",)), ["sensor.b_plug_1_energy"]),
        (SensorTarget(area_id=("kitchen",)), ["sensor.b_plug_1_energy"]),
        (SensorTarget(floor_id=("ground",)), ["sensor.a_plug_2_energy"]),
        (SensorTarget(label_id=("tracked",)), ["sensor.a_plug_2_energy"]),
        (SensorTarget(label_id=("none",)), []),
    ],
)
def test_include_by_device_area_floor_label(target: SensorTarget, expected: list[str]):
    selection = select_sensors(filter_settings(target), CANDIDATES, ())
    assert list(selection.sensors) == expected


def test_include_globs():
    include = SensorTarget(entity_globs=("sensor.*_plug_*_energy",))
    selection = select_sensors(filter_settings(include), CANDIDATES, ())
    # Case sensitive: sensor.D_Plug_3_energy does not match; ineligible ones skipped.
    assert selection.sensors == ("sensor.a_plug_2_energy", "sensor.b_plug_1_energy")
    include = SensorTarget(entity_globs=("sensor.c_*",))
    assert select_sensors(filter_settings(include), CANDIDATES, ()).sensors == ()


@pytest.mark.parametrize(
    "exclude",
    [
        SensorTarget(entity_id=("sensor.b_plug_1_energy",)),
        SensorTarget(entity_globs=("sensor.b_*",)),
        SensorTarget(device_id=("dev1",)),
        SensorTarget(area_id=("kitchen",)),
    ],
)
def test_exclude_wins(exclude: SensorTarget):
    include = SensorTarget(
        entity_id=("sensor.b_plug_1_energy",), entity_globs=("sensor.b_*",)
    )
    selection = select_sensors(filter_settings(include, exclude), CANDIDATES, ())
    assert "sensor.b_plug_1_energy" not in selection.sensors
    everything = select_sensors(filter_settings(None, exclude), CANDIDATES, ())
    assert "sensor.b_plug_1_energy" not in everything.sensors


def test_exclude_floor_and_label():
    exclude = SensorTarget(floor_id=("ground",))
    assert (
        "sensor.a_plug_2_energy"
        not in select_sensors(filter_settings(None, exclude), CANDIDATES, ()).sensors
    )
    exclude = SensorTarget(label_id=("tracked",))
    assert (
        "sensor.a_plug_2_energy"
        not in select_sensors(filter_settings(None, exclude), CANDIDATES, ()).sensors
    )


def test_dashboard_mode_order_dedup_exclude():
    dashboard = (
        DashboardDevice("sensor.z_energy"),
        DashboardDevice("sensor.a_energy"),
        DashboardDevice("sensor.z_energy"),
        DashboardDevice("ext:meter"),
        DashboardDevice("sensor.skip_energy"),
    )
    settings = SensorSettings(
        mode=SensorMode.ENERGY_DASHBOARD,
        exclude=SensorTarget(entity_id=("sensor.skip_energy",)),
    )
    selection = select_sensors(settings, (), dashboard)
    assert selection.sensors == ("sensor.z_energy", "sensor.a_energy", "ext:meter")
    settings = SensorSettings(
        mode=SensorMode.ENERGY_DASHBOARD,
        exclude=SensorTarget(entity_globs=("ext:*", "sensor.z_*")),
    )
    selection = select_sensors(settings, (), dashboard)
    assert selection.sensors == ("sensor.a_energy", "sensor.skip_energy")


def test_dashboard_exclude_uses_candidate_attributes():
    dashboard = (DashboardDevice("sensor.b_plug_1_energy"),)
    settings = SensorSettings(
        mode=SensorMode.ENERGY_DASHBOARD,
        exclude=SensorTarget(area_id=("kitchen",)),
    )
    assert select_sensors(settings, CANDIDATES, dashboard).sensors == ()


def test_parents_from_dashboard():
    dashboard = (
        DashboardDevice("sensor.a", included_in="sensor.b"),
        DashboardDevice("sensor.b"),
        DashboardDevice("sensor.c", included_in=None),
    )
    expected = {"sensor.a": "sensor.b"}
    dash = SensorSettings(mode=SensorMode.ENERGY_DASHBOARD)
    assert dict(select_sensors(dash, (), dashboard).parents) == expected
    flt = select_sensors(filter_settings(), CANDIDATES, dashboard)
    assert dict(flt.parents) == expected


def test_upstreams_nearest_selected_ancestor():
    parents = {"a": "b", "b": "c"}
    assert upstreams(["a", "c"], parents) == {"a": "c"}
    assert upstreams(["a", "b", "c"], parents) == {"a": "b", "b": "c"}
    assert upstreams(["a"], parents) == {}


def test_upstreams_cycle_safe(caplog: pytest.LogCaptureFixture):
    parents = {"a": "b", "b": "a", "c": "c"}
    # Members of a cycle have no upstream (otherwise both would leave the total).
    with caplog.at_level("DEBUG", logger="engine.sensors"):
        assert upstreams(["a", "b", "c"], parents) == {}
    assert "cycle" in caplog.text
    assert upstreams(["x", "a"], {"x": "a", "a": "b", "b": "a"}) == {"x": "a"}


def test_glob_validation():
    for good in ("sensor.*_plug_?_energy", "sensor.[ab]*", "sensor.[!a]*", "*"):
        assert is_valid_glob(good)
    for bad in ("", "  ", "sensor.A*", "sensor. x", "sensor/x"):
        assert not is_valid_glob(bad)


def test_settings_spike_limits():
    settings = SensorSettings(
        mode=SensorMode.FILTER,
        overrides={
            "sensor.a": SensorOverride(Decimal("6")),
            "sensor.b": SensorOverride(None),
        },
    )
    limits = settings.spike_limits()
    assert limits == {"sensor.a": Decimal("6"), "sensor.b": None}
    with pytest.raises(TypeError):
        limits["sensor.c"] = None  # type: ignore[index]
