"""Unit tests for tariff presets (tasks/004-tariff-model.md).

Zone key convention (human decision, 2026-09-25, overrides the task body): `t0` is the
single-rate key (a distinct column, never mixed with the two-zone `t1` in multi-plan
reports); `t1` = day/peak, `t2` = night, `t3` = semi-peak.
"""

import dataclasses
from datetime import date
from decimal import Decimal

from engine.presets import ru_three_zone, ru_two_zone, single_rate


def test_single_rate():
    plan = single_rate(valid_from=date(2026, 1, 1), price=Decimal("7.50"))
    assert [zone.key for zone in plan.zones] == ["t0"]
    for hour in range(24):
        zone = plan.zone_for_hour(hour)
        assert zone.key == "t0"
        assert zone.price == Decimal("7.50")


def test_ru_two_zone():
    plan = ru_two_zone(
        valid_from=date(2026, 1, 1),
        day_price=Decimal("10.30"),
        night_price=Decimal("4.43"),
    )
    day_hours = [h for h in range(24) if plan.zone_for_hour(h).key == "t1"]
    night_hours = [h for h in range(24) if plan.zone_for_hour(h).key == "t2"]

    assert len(day_hours) == 16
    assert len(night_hours) == 8
    assert plan.zone_for_hour(7).price == Decimal("10.30")
    assert plan.zone_for_hour(23).price == Decimal("4.43")
    day_zone = next(z for z in plan.zones if z.key == "t1")
    night_zone = next(z for z in plan.zones if z.key == "t2")
    assert day_zone.name == "Day"
    assert night_zone.name == "Night"


def test_ru_three_zone():
    plan = ru_three_zone(
        valid_from=date(2026, 1, 1),
        peak_price=Decimal("11.00"),
        semi_peak_price=Decimal("7.00"),
        night_price=Decimal("4.43"),
    )
    peak_hours = {h for h in range(24) if plan.zone_for_hour(h).key == "t1"}
    night_hours = {h for h in range(24) if plan.zone_for_hour(h).key == "t2"}
    semi_peak_hours = {h for h in range(24) if plan.zone_for_hour(h).key == "t3"}

    assert peak_hours == {7, 8, 9, 17, 18, 19, 20}
    assert semi_peak_hours == {10, 11, 12, 13, 14, 15, 16, 21, 22}
    assert night_hours == {23, 0, 1, 2, 3, 4, 5, 6}


def test_presets_editable():
    plan = single_rate(valid_from=date(2026, 1, 1), price=Decimal("7.50"))
    zone = plan.zones[0]
    renamed = dataclasses.replace(zone, name="Daytime")
    new_plan = dataclasses.replace(plan, zones=(renamed,))
    assert new_plan.zones[0].key == "t0"
    assert new_plan.zones[0].name == "Daytime"
