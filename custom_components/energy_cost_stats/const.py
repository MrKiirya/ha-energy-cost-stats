"""Shared constants for the Energy Cost Stats integration."""

from decimal import Decimal
from typing import Final

DOMAIN: Final = "energy_cost_stats"

DEFAULT_TITLE: Final = "Energy Cost Stats"

# Option keys (entry.options).
CONF_TIME_ZONE: Final = "time_zone"
CONF_SPIKE_LIMIT: Final = "spike_limit"
CONF_DEVICE_SPIKE_LIMITS: Final = "device_spike_limits"
CONF_ENTITIES: Final = "entities"

# Form-only keys (never stored).
CONF_SPIKE_CHECK: Final = "spike_check"
CONF_EDIT_DEVICE_LIMITS: Final = "edit_device_limits"

# Default spike limit in kWh per hour (SPEC §5).
DEFAULT_SPIKE_LIMIT: Final = Decimal("4")

# Tariff plan subentries (docs/SPEC.md §3).
SUBENTRY_TYPE_TARIFF_PLAN: Final = "tariff_plan"
PRESET_SINGLE_RATE: Final = "single_rate"
PRESET_RU_TWO_ZONE: Final = "ru_two_zone"
PRESET_RU_THREE_ZONE: Final = "ru_three_zone"
PRESETS: Final = (PRESET_SINGLE_RATE, PRESET_RU_TWO_ZONE, PRESET_RU_THREE_ZONE)

# Tariff plan form field names.
CONF_PRESET: Final = "preset"
CONF_SOURCE_PLAN: Final = "source_plan"
CONF_VALID_FROM: Final = "valid_from"
CONF_PLAN_NAME: Final = "name"


def zone_field(key: str, suffix: str) -> str:
    """Form field name of a zone attribute, e.g. ``t1_price``."""
    return f"{key}_{suffix}"


# Report API (docs/SPEC.md §2): websocket command, service, request fields, errors.
SERVICE_GET_REPORT: Final = "get_report"
WS_TYPE_REPORT: Final = "energy_cost_stats/report"

ATTR_START: Final = "start"
ATTR_END: Final = "end"
ATTR_GROUPING: Final = "grouping"
ATTR_ENTITIES: Final = "entities"

ERR_NOT_LOADED: Final = "not_loaded"
ERR_INVALID_PERIOD: Final = "invalid_period"
ERR_PERIOD_TOO_LONG: Final = "period_too_long"
ERR_UNKNOWN_ENTITY: Final = "unknown_entity"

# Hourly reports are limited to 31 days plus the closing hour (745 buckets).
MAX_HOURLY_DAYS: Final = 31
MAX_PERIOD_DAYS: Final = 3660
