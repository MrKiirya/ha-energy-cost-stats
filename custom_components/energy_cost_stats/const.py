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
CONF_APPLIED: Final = "applied"
CONF_COMPARE: Final = "compare"
CONF_PANEL: Final = "panel"

# Form-only keys (never stored).
CONF_SPIKE_CHECK: Final = "spike_check"
CONF_EDIT_DEVICE_LIMITS: Final = "edit_device_limits"

CONF_USE_DEFAULT: Final = "use_default"
CONF_TARIFFS: Final = "tariffs"
CONF_CHANGE: Final = "change"
CONF_DELETE: Final = "delete"
CONF_FROM: Final = "from"
CONF_TARIFF: Final = "tariff"
CONF_SIDEBAR: Final = "sidebar"
CONF_SHOW: Final = "show"
CONF_TITLE: Final = "title"
CONF_ICON: Final = "icon"

# Sidebar panel defaults (the panel itself is not implemented yet).
DEFAULT_PANEL_SHOW: Final = False
DEFAULT_PANEL_TITLE: Final = "Energy cost"
DEFAULT_PANEL_ICON: Final = "mdi:cash-multiple"

# Options menu step ids.
MENU_STEPS: Final = ("sensors", "applied", "compare", "general")

# Default spike limit in kWh per hour (SPEC §5).
DEFAULT_SPIKE_LIMIT: Final = Decimal("4")

# Tariff subentries (docs/SPEC.md §3): one config subentry per tariff.
SUBENTRY_TYPE_TARIFF: Final = "tariff"
# Legacy (config entry version 1) subentry type, only read by the migration.
SUBENTRY_TYPE_TARIFF_PLAN: Final = "tariff_plan"
MIGRATED_TARIFF_ID: Final = "main"

# Tariff forms (tariff_flow.py): bases offered when adding a tariff and form-only keys.
BASE_SINGLE_RATE: Final = "single_rate"
BASE_TWO_ZONE: Final = "ru_two_zone"
BASE_THREE_ZONE: Final = "ru_three_zone"
BASE_CUSTOM: Final = "custom"
BASE_COPY: Final = "copy"
MAX_ZONES: Final = 6
CONF_TARIFF_ID: Final = "id"
CONF_TARIFF_NAME: Final = "name"
CONF_BASE: Final = "base"
CONF_SOURCE: Final = "source"
CONF_COUNT: Final = "count"
CONF_VALID_FROM: Final = "valid_from"
CONF_VERSION: Final = "version"
SECTION_HOURS: Final = "hours"

# Report API (docs/SPEC.md §2): websocket command, service, request fields, errors.
SERVICE_GET_REPORT: Final = "get_report"
WS_TYPE_REPORT: Final = "energy_cost_stats/report"
WS_TYPE_COMPARE: Final = "energy_cost_stats/compare"
ATTR_TARIFFS: Final = "tariffs"

ATTR_START: Final = "start"
ATTR_END: Final = "end"
ATTR_GROUPING: Final = "grouping"
ATTR_ENTITIES: Final = "entities"

ERR_NOT_LOADED: Final = "not_loaded"
ERR_INVALID_PERIOD: Final = "invalid_period"
ERR_PERIOD_TOO_LONG: Final = "period_too_long"
ERR_UNKNOWN_ENTITY: Final = "unknown_entity"
ERR_UNKNOWN_TARIFF: Final = "unknown_tariff"

# Hourly reports are limited to 31 days plus the closing hour (745 buckets).
MAX_HOURLY_DAYS: Final = 31
MAX_PERIOD_DAYS: Final = 3660

# Lovelace card bundle served by the integration (frontend.py).
CARD_URL: Final = "/energy_cost_stats/energy-cost-stats-card.js"
