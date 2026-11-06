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
from functools import partial
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    ERR_INVALID_PERIOD,
    ERR_NOT_LOADED,
    ERR_PERIOD_TOO_LONG,
    ERR_UNKNOWN_ENTITY,
    ERR_UNKNOWN_TARIFF,
    MAX_HOURLY_DAYS,
    MAX_PERIOD_DAYS,
)
from .engine.models import Grouping, ReportRequest
from .engine.quality import QualitySettings
from .engine.report import build_report
from .engine.sensors import upstreams
from .engine.serialize import DeviceInfo, report_to_json
from .engine.tariff import TariffSchedule
from .engine.tariff_config import comparison_schedule
from .recorder_adapter import (
    HourlySeries,
    StatisticsStatus,
    async_read_hourly_changes,
)
from .sensor_resolver import async_resolve_sensors, display_name

_HOUR = timedelta(hours=1)
MIN_YEAR = 1970
MAX_YEAR = 9000
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

ERROR_MESSAGES = {
    ERR_NOT_LOADED: "Energy Cost Stats is not set up",
    ERR_INVALID_PERIOD: "Invalid period: {detail}",
    ERR_PERIOD_TOO_LONG: "The period is too long (at most {max})",
    ERR_UNKNOWN_ENTITY: "{entity_id} is not one of the selected energy sensors",
    ERR_UNKNOWN_TARIFF: "{tariff_id} is not a configured tariff",
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


@dataclass
class _Prepared:
    """A validated request with its statistics read once, ready to be priced."""

    runtime: Any
    request: ReportRequest
    read: Sequence[HourlySeries]
    quality: QualitySettings
    devices: list[DeviceInfo]
    time_zone: str
    nested: Mapping[str, str]


async def _async_prepare(
    hass: HomeAssistant,
    *,
    start: str,
    end: str,
    grouping: str,
    entities: Sequence[str] | None,
) -> _Prepared:
    """Validate the request and read the statistics (raises ``ReportError``)."""
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

    selection = await async_resolve_sensors(hass, settings.sensors)
    ids = _select_entities(selection.sensors, entities)
    request = ReportRequest(start_utc, end_utc, tz, grouping)
    read = await async_read_hourly_changes(hass, ids, start_utc, end_utc)
    # Only devices with readable statistics can account for a nested device's energy.
    readable = [
        item.statistic_id for item in read if item.status is StatisticsStatus.OK
    ]
    parents = upstreams(readable, selection.parents)
    quality = QualitySettings(
        spike_limit=settings.spike_limit,
        device_spike_limits=settings.sensors.spike_limits(),
    )
    devices = [
        DeviceInfo(
            item.statistic_id,
            display_name(hass, item.statistic_id, item.name),
            item.status.value,
            parents.get(item.statistic_id),
        )
        for item in read
    ]
    return _Prepared(runtime, request, read, quality, devices, time_zone, parents)


async def _async_priced_document(
    hass: HomeAssistant, prepared: _Prepared, schedule: TariffSchedule | None
) -> dict[str, Any]:
    """Price the prepared consumption with ``schedule`` and serialize the document."""
    report = await hass.async_add_executor_job(
        partial(
            build_report,
            prepared.request,
            schedule,
            [item.series for item in prepared.read],
            quality=prepared.quality,
            nested=prepared.nested,
        )
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
    return await _async_priced_document(hass, prepared, prepared.runtime.schedule)


async def async_get_comparison(
    hass: HomeAssistant,
    *,
    start: str,
    end: str,
    entities: Sequence[str] | None,
    tariffs: Sequence[str] | None,
) -> dict[str, Any]:
    """The actual report plus the same consumption priced with other tariffs.

    Statistics are read once; each tariff is priced with its own versions only.
    Raises ``ReportError`` for user mistakes.
    """
    prepared = await _async_prepare(
        hass, start=start, end=end, grouping=Grouping.TOTAL.value, entities=entities
    )
    config = prepared.runtime.tariffs
    selected = list(dict.fromkeys(config.compare if tariffs is None else tariffs))
    known = {tariff.id for tariff in config.tariffs}
    for tariff_id in selected:
        if tariff_id not in known:
            raise ReportError(ERR_UNKNOWN_TARIFF, tariff_id=tariff_id)
    actual = await _async_priced_document(hass, prepared, prepared.runtime.schedule)
    compared: list[dict[str, Any]] = []
    for tariff_id in selected:
        tariff = config.tariff(tariff_id)
        document = await _async_priced_document(
            hass, prepared, comparison_schedule(tariff)
        )
        compared.append({"id": tariff.id, "name": tariff.name, "report": document})
    return {"actual": actual, "tariffs": compared}
