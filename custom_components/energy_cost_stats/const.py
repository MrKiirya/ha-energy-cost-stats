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
