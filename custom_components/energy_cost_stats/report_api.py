"""Report request handling shared by the websocket command and the service.

Validates the request, reads statistics through the recorder adapter, builds the
report in an executor and returns the versioned JSON document (docs/SPEC.md §2, §4).
Design: tasks/013-report-websocket-and-service.md.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, tzinfo
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    ERR_INVALID_PERIOD,
    ERR_INVALID_SCENARIO,
    ERR_NOT_LOADED,
    ERR_PERIOD_TOO_LONG,
    ERR_UNKNOWN_ENTITY,
    MAX_HOURLY_DAYS,
    MAX_PERIOD_DAYS,
)
from .engine.models import DeviceSeries, Grouping, ReportRequest
from .engine.quality import QualitySettings
from .engine.report import build_report
from .engine.scenario import MAX_SCENARIOS, Scenario, scenario_from_data
from .engine.serialize import DeviceInfo, report_to_json
from .engine.tariff import TariffSchedule, TariffValidationError
from .recorder_adapter import HourlySeries, async_read_hourly_changes

_HOUR = timedelta(hours=1)
MIN_YEAR = 1970
MAX_YEAR = 9000
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

ERROR_MESSAGES = {
    ERR_NOT_LOADED: "Energy Cost Stats is not set up",
    ERR_INVALID_PERIOD: "Invalid period: {detail}",
    ERR_PERIOD_TOO_LONG: "The period is too long (at most {max})",
    ERR_UNKNOWN_ENTITY: "{entity_id} is not one of the configured energy sensors",
    ERR_INVALID_SCENARIO: "Invalid tariff scenario: {detail}",
}


class ReportError(Exception):
    """A user-facing request error with a translation key and placeholders."""

    def __init__(self, code: str, **placeholders: str) -> None:
        super().__init__(code)
        self.code = code
        self.placeholders = placeholders

    @property
    def message(self) -> str:
        """English message (websocket); the service uses the translation."""
        return ERROR_MESSAGES[self.code].format(**self.placeholders)


def _check_year(value: datetime, text: str) -> datetime:
    if not MIN_YEAR <= value.year <= MAX_YEAR:
        raise ValueError(f"{text!r} is outside {MIN_YEAR}..{MAX_YEAR}")
    return value


def parse_bound(text: str, tz: tzinfo) -> datetime:
    """Parse a period bound into an aware UTC datetime on a whole UTC hour.

    ``YYYY-MM-DD`` is local midnight in ``tz``, rounded up to the first UTC hour that
    starts on or after it (SPEC §5). An ISO datetime without offset is read in ``tz``
    (fold 0) and must already be on a whole UTC hour. Raises ``ValueError``.
    """
    value = text.strip()
    if _DATE_RE.match(value):
        local = datetime.combine(date.fromisoformat(value), time(), tzinfo=tz)
        utc = local.astimezone(UTC)
        floor = utc.replace(minute=0, second=0, microsecond=0)
        return _check_year(floor if floor == utc else floor + _HOUR, text)
    parsed = dt_util.parse_datetime(value)
    if parsed is None:
        raise ValueError(f"not a date or ISO datetime: {text!r}")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tz, fold=0)
    utc = parsed.astimezone(UTC)
    if (utc.minute, utc.second, utc.microsecond) != (0, 0, 0):
        raise ValueError(f"{text!r} is not on a whole UTC hour")
    return _check_year(utc, text)


def _loaded_entry(hass: HomeAssistant) -> Any:
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is ConfigEntryState.LOADED:
            return entry
    raise ReportError(ERR_NOT_LOADED)


def _select_entities(
    configured: Sequence[str], requested: Sequence[str] | None
) -> list[str]:
    if not requested:
        return list(configured)
    selected: list[str] = []
    for entity_id in requested:
        if entity_id not in configured:
            raise ReportError(ERR_UNKNOWN_ENTITY, entity_id=entity_id)
        if entity_id not in selected:
            selected.append(entity_id)
    return selected


def _zone_name(tz: tzinfo, configured: str) -> str:
    """IANA name of the report zone; it must be the configured one."""
    key = tz.key if isinstance(tz, ZoneInfo) else None
    if key != configured:
        raise RuntimeError(
            f"report zone {key!r} does not match the configured zone {configured!r}"
        )
    return configured


def _display_name(hass: HomeAssistant, series: HourlySeries) -> str:
    entity_id = series.statistic_id
    if (state := hass.states.get(entity_id)) is not None:
        return state.name
    registered = er.async_get(hass).async_get(entity_id)
    if registered is not None:
        registered_name = registered.name or registered.original_name
        if registered_name:
            return str(registered_name)
    return series.name or entity_id


@dataclass(frozen=True, slots=True)
class _Prepared:
    """A validated request with the statistics read for it."""

    request: ReportRequest
    series: list[DeviceSeries]
    devices: list[DeviceInfo]
    quality: QualitySettings
    time_zone: str
    schedule: TariffSchedule | None


async def _async_prepare(
    hass: HomeAssistant,
    *,
    start: str,
    end: str,
    grouping: str,
    entities: Sequence[str] | None,
) -> _Prepared:
    """Validate the request and read the statistics. Raises ``ReportError``."""
    entry = _loaded_entry(hass)
    runtime = entry.runtime_data
    settings = runtime.settings
    tz: tzinfo = runtime.tzinfo
    time_zone = _zone_name(tz, settings.time_zone)

    try:
        start_utc = parse_bound(start, tz)
        end_utc = parse_bound(end, tz)
    except (ValueError, OverflowError) as err:
        raise ReportError(ERR_INVALID_PERIOD, detail=str(err)) from err
    if end_utc <= start_utc:
        raise ReportError(ERR_INVALID_PERIOD, detail="end must be after start")
    span = end_utc - start_utc
    if Grouping(grouping) is Grouping.HOUR:
        if span > timedelta(days=MAX_HOURLY_DAYS) + _HOUR:
            raise ReportError(
                ERR_PERIOD_TOO_LONG, max=f"{MAX_HOURLY_DAYS} days for hourly grouping"
            )
    elif span > timedelta(days=MAX_PERIOD_DAYS):
        raise ReportError(ERR_PERIOD_TOO_LONG, max=f"{MAX_PERIOD_DAYS} days")

    ids = _select_entities(settings.entities, entities)
    request = ReportRequest(start_utc, end_utc, tz, grouping)
    read = await async_read_hourly_changes(hass, ids, start_utc, end_utc)
    return _Prepared(
        request=request,
        series=[item.series for item in read],
        devices=[
            DeviceInfo(item.statistic_id, _display_name(hass, item), item.status.value)
            for item in read
        ],
        quality=QualitySettings(
            spike_limit=settings.spike_limit,
            device_spike_limits=settings.device_spike_limits,
        ),
        time_zone=time_zone,
        schedule=runtime.schedule,
    )


def _document(
    hass: HomeAssistant, prepared: _Prepared, schedule: TariffSchedule | None
) -> dict[str, Any]:
    """Build and serialize one report (runs in the executor)."""
    report = build_report(
        prepared.request, schedule, prepared.series, quality=prepared.quality
    )
    return report_to_json(
        report,
        devices=prepared.devices,
        time_zone=prepared.time_zone,
        currency=hass.config.currency,
    )


async def async_get_report(
    hass: HomeAssistant,
    *,
    start: str,
    end: str,
    grouping: str,
    entities: Sequence[str] | None,
) -> dict[str, Any]:
    """Build the report document. Raises ``ReportError`` for user mistakes."""
    prepared = await _async_prepare(
        hass, start=start, end=end, grouping=grouping, entities=entities
    )
    return await hass.async_add_executor_job(
        _document, hass, prepared, prepared.schedule
    )


def parse_scenarios(data: Sequence[Mapping[str, Any]]) -> list[Scenario]:
    """Parse the request's scenarios. Raises ``ReportError(invalid_scenario)``."""
    if not 1 <= len(data) <= MAX_SCENARIOS:
        raise ReportError(
            ERR_INVALID_SCENARIO,
            detail=f"between 1 and {MAX_SCENARIOS} scenarios are allowed",
        )
    scenarios: list[Scenario] = []
    for index, item in enumerate(data, start=1):
        try:
            scenarios.append(scenario_from_data(item))
        except TariffValidationError as err:
            raise ReportError(
                ERR_INVALID_SCENARIO, detail=f"scenario {index}: {err}"
            ) from err
    return scenarios


async def async_get_comparison(
    hass: HomeAssistant,
    *,
    start: str,
    end: str,
    entities: Sequence[str] | None,
    scenarios: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Price the same consumption with the configured plans and each scenario.

    Statistics are read once; every document uses grouping ``total`` (SPEC §4.2).
    """
    parsed = parse_scenarios(scenarios)
    prepared = await _async_prepare(
        hass, start=start, end=end, grouping=Grouping.TOTAL.value, entities=entities
    )

    def build() -> dict[str, Any]:
        return {
            "actual": _document(hass, prepared, prepared.schedule),
            "scenarios": [
                {
                    "name": scenario.name,
                    "preset": scenario.preset,
                    "report": _document(hass, prepared, scenario.schedule),
                }
                for scenario in parsed
            ],
        }

    return await hass.async_add_executor_job(build)
