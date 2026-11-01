"""Integration test fixtures: enable the in-memory recorder and custom integrations.

`recorder_mock` must be requested before `enable_custom_integrations`
(pytest-homeassistant-custom-component README).
"""

from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime
from typing import Any

import pytest
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    async_import_statistics,
)
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)

SeedStatistics = Callable[..., Awaitable[None]]


@pytest.fixture(autouse=True)
async def _auto_enable(recorder_mock, enable_custom_integrations):
    """Enable the mocked recorder and custom integration loading for every test here."""


@pytest.fixture
def seed_statistics(hass: HomeAssistant) -> SeedStatistics:
    """Return ``seed(statistic_id, sums, ...)`` writing hourly statistics rows.

    ``sums`` maps an aware hour start to a cumulative sum; ``None`` writes a row
    without a ``sum`` key (a NULL sum). With ``has_sum=False`` the values are written
    as ``mean`` instead. Ids containing ``:`` are external statistics.
    """

    async def seed(
        statistic_id: str,
        sums: Mapping[datetime, float | None],
        *,
        unit: str = "kWh",
        has_sum: bool = True,
        mean_type: StatisticMeanType = StatisticMeanType.NONE,
        name: str | None = None,
    ) -> None:
        external = ":" in statistic_id
        source = statistic_id.split(":", 1)[0] if external else "recorder"
        metadata: dict[str, Any] = {
            "has_sum": has_sum,
            "mean_type": mean_type,
            "name": name,
            "source": source,
            "statistic_id": statistic_id,
            "unit_of_measurement": unit,
        }
        if "unit_class" in StatisticMetaData.__annotations__:
            metadata["unit_class"] = {
                "kWh": "energy",
                "Wh": "energy",
                "MWh": "energy",
                "W": "power",
                "kW": "power",
            }.get(unit)
        rows: list[StatisticData] = []
        for start, value in sorted(sums.items()):
            row: dict[str, Any] = {"start": start}
            if value is not None:
                row["mean" if not has_sum else "sum"] = value
            rows.append(StatisticData(**row))  # type: ignore[typeddict-item]
        if external:
            async_add_external_statistics(hass, StatisticMetaData(**metadata), rows)  # type: ignore[typeddict-item]
        else:
            async_import_statistics(hass, StatisticMetaData(**metadata), rows)  # type: ignore[typeddict-item]
        await async_wait_recording_done(hass)

    return seed
