"""Recorder adapter: hourly `change` statistics with neighbour keys
(tasks/011-recorder-adapter.md)."""

import ast
import asyncio
from collections.abc import Awaitable, Callable, Iterable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from itertools import pairwise
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from homeassistant.components.recorder.models import StatisticMeanType
from homeassistant.components.recorder.statistics import (
    get_metadata,
    statistics_during_period,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.recorder import get_instance
from homeassistant.util import dt as dt_util

from custom_components.energy_cost_stats import recorder_adapter
from custom_components.energy_cost_stats.engine.models import (
    DataStatus,
    Grouping,
    ReportRequest,
)
from custom_components.energy_cost_stats.engine.presets import ru_two_zone
from custom_components.energy_cost_stats.engine.report import build_report
from custom_components.energy_cost_stats.engine.tariff import TariffSchedule
from custom_components.energy_cost_stats.recorder_adapter import (
    HourlySeries,
    StatisticsStatus,
    async_read_hourly_changes,
    classify_metadata,
)

SeedStatistics = Callable[..., Awaitable[None]]
HOUR = timedelta(hours=1)
W_START = datetime(2026, 1, 15, tzinfo=UTC)
W_END = datetime(2026, 1, 16, tzinfo=UTC)
MSK = ZoneInfo("Europe/Moscow")
BER = ZoneInfo("Europe/Berlin")
PLUG_01 = "sensor.plug_01"
PLUG_02 = "sensor.plug_02"


def ramp(
    first: datetime, last: datetime, *, step: float = 1.0, base: float = 0.0
) -> dict[datetime, float]:
    """Cumulative sums ``base + step, base + 2*step, ...`` on hours first..last."""
    sums: dict[datetime, float] = {}
    current = first
    total = base
    while current <= last:
        total += step
        sums[current] = total
        current += HOUR
    return sums


def schedule() -> TariffSchedule:
    return TariffSchedule(
        (
            ru_two_zone(
                valid_from=date(2020, 1, 1),
                day_price=Decimal(5),
                night_price=Decimal(3),
            ),
        )
    )


def hourly_report(series: Iterable[HourlySeries], tz, start, end):
    request = ReportRequest(start, end, tz, Grouping.HOUR)
    return build_report(request, schedule(), [s.series for s in series])


def bucket_at(report, start: datetime):
    for bucket in report.buckets:
        if bucket.start == start:
            return bucket
    raise AssertionError(f"no bucket at {start}")


async def read_one(hass: HomeAssistant, statistic_id: str = PLUG_01) -> HourlySeries:
    (result,) = await async_read_hourly_changes(hass, [statistic_id], W_START, W_END)
    return result


async def test_reads_window_and_trims_neighbours(
    hass: HomeAssistant, seed_statistics: SeedStatistics
) -> None:
    await seed_statistics(PLUG_01, ramp(W_START - 3 * HOUR, W_END + 3 * HOUR))
    result = await read_one(hass)
    assert result.status is StatisticsStatus.OK
    assert result.series.device_id == PLUG_01
    expected = [W_START - HOUR] + [W_START + i * HOUR for i in range(24)] + [W_END]
    assert sorted(result.series.deltas) == expected
    assert len(result.series.deltas) == 26
    for key, value in result.series.deltas.items():
        assert key.tzinfo is not None
        assert key.utcoffset() == timedelta(0)
        assert value == 1


async def test_change_relative_to_previous_row(
    hass: HomeAssistant, seed_statistics: SeedStatistics
) -> None:
    await seed_statistics(
        PLUG_01,
        {W_START - HOUR: 10.0, W_START: 12.5, W_START + HOUR: 13.0},
    )
    deltas = (await read_one(hass)).series.deltas
    assert deltas[W_START - HOUR] == Decimal("10.0")
    assert deltas[W_START] == Decimal("2.5")
    assert deltas[W_START + HOUR] == Decimal("0.5")


@pytest.mark.parametrize("days", [2, 40, 400])
async def test_lookback_far(
    hass: HomeAssistant, seed_statistics: SeedStatistics, days: int
) -> None:
    predecessor = W_START - timedelta(days=days)
    sums = {predecessor: 1.0}
    sums.update(ramp(W_START + 2 * HOUR, W_END + 2 * HOUR, base=3.0))
    await seed_statistics(PLUG_01, sums)
    result = await read_one(hass)
    deltas = result.series.deltas
    assert deltas[predecessor] == 1
    assert deltas[W_START + 2 * HOUR] == 3
    assert not any(predecessor < key < W_START + 2 * HOUR for key in deltas)

    report = hourly_report([result], MSK, W_START, W_END)
    for offset in range(3):
        coverage = bucket_at(report, W_START + offset * HOUR).total.coverage
        assert coverage.estimated == 1, offset
    assert bucket_at(report, W_START + 3 * HOUR).total.status is DataStatus.COMPLETE


async def test_null_sum_row_before_main_query_start(
    hass: HomeAssistant, seed_statistics: SeedStatistics
) -> None:
    """HA's baseline for a query is the row just before it, even with a NULL sum, so
    its first `change` would be the full cumulative sum. The adapter recomputes it."""
    day = timedelta(days=1)
    sums: dict[datetime, float | None] = {
        W_START - day - 2 * HOUR: 100.0,
        W_START - day - HOUR: None,
    }
    sums.update(ramp(W_START, W_END, base=100.0))
    await seed_statistics(PLUG_01, sums)
    deltas = (await read_one(hass)).series.deltas
    assert deltas[W_START - day - 2 * HOUR] == 100
    assert deltas[W_START] == 1
    assert deltas[W_START + HOUR] == 1


async def test_null_sum_row_before_lookahead_query_start(
    hass: HomeAssistant, seed_statistics: SeedStatistics
) -> None:
    day = timedelta(days=1)
    sums: dict[datetime, float | None] = dict(ramp(W_START, W_START + 20 * HOUR))
    sums[W_END + day - HOUR] = None
    sums[W_END + 5 * day] = 24.0
    await seed_statistics(PLUG_01, sums)
    result = await read_one(hass)
    assert result.series.deltas[W_END + 5 * day] == 3
    report = hourly_report([result], MSK, W_START, W_END)
    assert bucket_at(report, W_START + 21 * HOUR).total.coverage.estimated == 1


async def test_null_sum_row_before_lookback_step_start(
    hass: HomeAssistant, seed_statistics: SeedStatistics
) -> None:
    day = timedelta(days=1)
    sums: dict[datetime, float | None] = {
        W_START - 31 * day - 2 * HOUR: 100.0,
        W_START - 31 * day - HOUR: None,
        W_START - 20 * day: 101.0,
        W_START - 10 * day: 102.0,
    }
    sums.update(ramp(W_START, W_END, base=102.0))
    await seed_statistics(PLUG_01, sums)
    deltas = (await read_one(hass)).series.deltas
    assert deltas[W_START - 10 * day] == 1
    assert deltas[W_START] == 1


async def test_lookback_missing_means_first_key_is_measured(
    hass: HomeAssistant, seed_statistics: SeedStatistics
) -> None:
    await seed_statistics(PLUG_01, ramp(W_START + 2 * HOUR, W_END, base=2.0))
    result = await read_one(hass)
    assert min(result.series.deltas) == W_START + 2 * HOUR
    report = hourly_report([result], MSK, W_START, W_END)
    assert bucket_at(report, W_START + 2 * HOUR).total.status is DataStatus.COMPLETE
    assert bucket_at(report, W_START).total.status is DataStatus.MISSING


@pytest.mark.parametrize("days", [5, 60])
async def test_lookahead_far(
    hass: HomeAssistant, seed_statistics: SeedStatistics, days: int
) -> None:
    after = W_END + timedelta(days=days)
    sums = ramp(W_START, W_START + 19 * HOUR)
    sums[after] = 23.0
    sums[after + HOUR] = 24.0
    sums[after + 2 * HOUR] = 25.0
    await seed_statistics(PLUG_01, sums)
    result = await read_one(hass)
    deltas = result.series.deltas
    assert deltas[after] == 3
    assert not any(key > after for key in deltas)
    assert max(deltas) == after

    report = hourly_report([result], MSK, W_START, W_END)
    for hour in range(20, 24):
        coverage = bucket_at(report, W_START + hour * HOUR).total.coverage
        assert coverage.estimated == 1, hour
        assert coverage.missing == 0, hour


async def test_no_neighbours(
    hass: HomeAssistant, seed_statistics: SeedStatistics
) -> None:
    await seed_statistics(PLUG_01, ramp(W_START + 5 * HOUR, W_START + 10 * HOUR))
    deltas = (await read_one(hass)).series.deltas
    assert sorted(deltas) == [W_START + i * HOUR for i in range(5, 11)]


async def test_null_sum_rows_dropped(
    hass: HomeAssistant, seed_statistics: SeedStatistics
) -> None:
    sums: dict[datetime, float | None] = dict(ramp(W_START, W_START + 10 * HOUR))
    sums[W_START + 4 * HOUR] = None
    await seed_statistics(PLUG_01, sums)
    deltas = (await read_one(hass)).series.deltas
    assert W_START + 4 * HOUR not in deltas
    assert deltas[W_START + 5 * HOUR] == 2
    assert deltas[W_START + 3 * HOUR] == 1


async def test_wh_converted_to_kwh(
    hass: HomeAssistant, seed_statistics: SeedStatistics
) -> None:
    await seed_statistics(
        PLUG_02, ramp(W_START, W_START + 5 * HOUR, step=1000.0), unit="Wh"
    )
    result = await read_one(hass, PLUG_02)
    assert result.status is StatisticsStatus.OK
    assert len(result.series.deltas) == 6
    assert all(value == Decimal("1.0") for value in result.series.deltas.values())


async def test_statuses(hass: HomeAssistant, seed_statistics: SeedStatistics) -> None:
    await seed_statistics(PLUG_01, ramp(W_START, W_START + 3 * HOUR), name="Plug 1")
    await seed_statistics(
        "sensor.power_01",
        {W_START: 100.0, W_START + HOUR: 120.0},
        unit="W",
        has_sum=False,
        mean_type=StatisticMeanType.ARITHMETIC,
        name="Power 1",
    )
    results = await async_read_hourly_changes(
        hass, [PLUG_01, "sensor.missing_01", "sensor.power_01"], W_START, W_END
    )
    assert [r.statistic_id for r in results] == [
        PLUG_01,
        "sensor.missing_01",
        "sensor.power_01",
    ]
    assert [r.status for r in results] == [
        StatisticsStatus.OK,
        StatisticsStatus.NO_STATISTICS,
        StatisticsStatus.UNSUPPORTED,
    ]
    assert results[0].series.deltas
    assert not results[1].series.deltas
    assert not results[2].series.deltas
    assert [r.series.device_id for r in results] == [r.statistic_id for r in results]
    assert results[0].name == "Plug 1"
    assert results[1].name is None
    assert results[2].name == "Power 1"


def test_classify_metadata_ignores_unknown_fields() -> None:
    full = {
        "has_sum": True,
        "unit_of_measurement": "kWh",
        "mean_type": 0,
        "unit_class": "energy",
        "has_mean": False,
        "future_key": "x",
    }
    assert classify_metadata(full) is StatisticsStatus.OK
    assert classify_metadata({"unit_of_measurement": "kWh"}) is (
        StatisticsStatus.UNSUPPORTED
    )
    assert classify_metadata({**full, "has_sum": False}) is StatisticsStatus.UNSUPPORTED
    for unit in (None, "W", "m³"):
        assert classify_metadata({**full, "unit_of_measurement": unit}) is (
            StatisticsStatus.UNSUPPORTED
        )
    for unit in ("Wh", "MWh"):
        assert classify_metadata({**full, "unit_of_measurement": unit}) is (
            StatisticsStatus.OK
        )


async def test_external_statistic_id(
    hass: HomeAssistant, seed_statistics: SeedStatistics
) -> None:
    await seed_statistics("test:meter_01", ramp(W_START, W_START + 3 * HOUR))
    result = await read_one(hass, "test:meter_01")
    assert result.status is StatisticsStatus.OK
    assert sorted(result.series.deltas) == [W_START + i * HOUR for i in range(4)]
    assert all(value == 1 for value in result.series.deltas.values())


async def test_rejects_bad_arguments(hass: HomeAssistant) -> None:
    cases = [
        ([PLUG_01, PLUG_01], W_START, W_END),
        ([""], W_START, W_END),
        ([PLUG_01], datetime(2026, 1, 15), W_END),
        ([PLUG_01], W_START + timedelta(minutes=30), W_END),
        ([PLUG_01], W_START, W_START),
    ]
    for ids, start, end in cases:
        with pytest.raises(ValueError):
            await async_read_hourly_changes(hass, ids, start, end)
    assert await async_read_hourly_changes(hass, [], W_START, W_END) == ()


async def test_runs_in_recorder_executor(
    hass: HomeAssistant, seed_statistics: SeedStatistics
) -> None:
    await seed_statistics(PLUG_01, ramp(W_START, W_START + 3 * HOUR))
    off_loop: dict[str, list[bool]] = {"statistics": [], "metadata": []}

    def make_wrapper(kind: str, real):
        def wrapper(*args, **kwargs):
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                off_loop[kind].append(True)
            else:
                off_loop[kind].append(False)
            return real(*args, **kwargs)

        return wrapper

    instance = get_instance(hass)
    with (
        patch.object(
            recorder_adapter,
            "statistics_during_period",
            make_wrapper("statistics", statistics_during_period),
        ),
        patch.object(
            recorder_adapter, "get_metadata", make_wrapper("metadata", get_metadata)
        ),
        patch.object(
            instance, "async_add_executor_job", wraps=instance.async_add_executor_job
        ) as submit,
    ):
        await read_one(hass)
    assert off_loop["statistics"]
    assert off_loop["metadata"]
    assert all(off_loop["statistics"])
    assert all(off_loop["metadata"])
    assert submit.call_count == 1


async def test_future_lookahead_steps_are_skipped(
    hass: HomeAssistant, seed_statistics: SeedStatistics
) -> None:
    end = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)
    start = end - 3 * HOUR
    await seed_statistics(PLUG_01, ramp(start - 2 * HOUR, end - HOUR))
    with patch.object(
        recorder_adapter, "statistics_during_period", wraps=statistics_during_period
    ) as spy:
        (result,) = await async_read_hourly_changes(hass, [PLUG_01], start, end)
    assert spy.call_count == 1
    assert max(result.series.deltas) == end - HOUR


async def test_single_query_when_neighbours_are_near(
    hass: HomeAssistant, seed_statistics: SeedStatistics
) -> None:
    near = ramp(W_START - 3 * HOUR, W_END + 3 * HOUR)
    await seed_statistics(PLUG_01, near)
    await seed_statistics(PLUG_02, near)
    with patch.object(
        recorder_adapter, "statistics_during_period", wraps=statistics_during_period
    ) as spy:
        await async_read_hourly_changes(hass, [PLUG_01, PLUG_02], W_START, W_END)
    assert spy.call_count == 1

    far = {W_START - timedelta(days=40): 1.0}
    far.update(ramp(W_START, W_END + 3 * HOUR, base=1.0))
    await seed_statistics("sensor.plug_03", far)
    with patch.object(
        recorder_adapter, "statistics_during_period", wraps=statistics_during_period
    ) as spy:
        await async_read_hourly_changes(
            hass, [PLUG_01, "sensor.plug_03"], W_START, W_END
        )
    assert spy.call_count == 3
    for call in spy.call_args_list[1:]:
        assert call.kwargs["statistic_ids"] == {"sensor.plug_03"}


async def test_window_independence_end_to_end(
    hass: HomeAssistant, seed_statistics: SeedStatistics
) -> None:
    day1 = datetime(2026, 3, 27, 23, tzinfo=UTC)  # local 2026-03-28 00:00 (CET)
    window_end = datetime(2026, 3, 30, 22, tzinfo=UTC)  # local 2026-03-31 00:00 (CEST)
    sums: dict[datetime, float | None] = {}
    total = 0.0
    current = day1 - 3 * HOUR
    gap = set(range(10, 14))  # gap inside local day one
    gap |= set(range(22, 26))  # gap across the first local midnight
    while current <= window_end + 3 * HOUR:
        index = int((current - day1) / HOUR)
        amount = 0.5
        if index == 50:
            amount = 10.0  # spike
        total += amount
        if index not in gap:
            sums[current] = total
        current += HOUR
    await seed_statistics(PLUG_01, sums)

    async def report_for(start: datetime, end: datetime):
        (series,) = await async_read_hourly_changes(hass, [PLUG_01], start, end)
        return hourly_report([series], BER, start, end)

    full = await report_for(day1, window_end)
    assert full.totals.total.coverage.estimated > 0
    assert full.totals.total.coverage.excluded > 0
    common = 0
    boundaries = [day1, datetime(2026, 3, 28, 23, tzinfo=UTC)]
    boundaries += [datetime(2026, 3, 29, 22, tzinfo=UTC), window_end]
    for start, end in pairwise(boundaries):
        single = await report_for(start, end)
        for bucket in single.buckets:
            assert bucket.rows == bucket_at(full, bucket.start).rows
            common += 1
    assert common == 71


def test_only_adapter_imports_recorder() -> None:
    package = Path(recorder_adapter.__file__).parent
    offenders: list[str] = []
    for path in package.rglob("*.py"):
        if path.name == "recorder_adapter.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [module] + [f"{module}.{alias.name}" for alias in node.names]
            if any(
                n == "homeassistant.components.recorder"
                or n.startswith("homeassistant.components.recorder.")
                for n in names
            ):
                offenders.append(str(path))
    assert offenders == []
