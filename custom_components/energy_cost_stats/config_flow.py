"""Config flow and options flow for Energy Cost Stats."""

import zoneinfo
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from . import EnergyCostStatsConfigEntry
from .const import (
    CONF_DEVICE_SPIKE_LIMITS,
    CONF_EDIT_DEVICE_LIMITS,
    CONF_ENTITIES,
    CONF_SPIKE_CHECK,
    CONF_SPIKE_LIMIT,
    CONF_TIME_ZONE,
    DEFAULT_SPIKE_LIMIT,
    DEFAULT_TITLE,
    DOMAIN,
    SUBENTRY_TYPE_TARIFF_PLAN,
)
from .settings import (
    IntegrationSettings,
    SettingsError,
    settings_from_options,
    settings_to_options,
)
from .subentry_flow import TariffPlanSubentryFlow

_ENERGY = "energy"


def _spike_limit_selector() -> NumberSelector:
    return NumberSelector(
        NumberSelectorConfig(
            min=0.001,
            step="any",
            mode=NumberSelectorMode.BOX,
            unit_of_measurement="kWh",
        )
    )


def _device_limit_selector() -> NumberSelector:
    return NumberSelector(
        NumberSelectorConfig(
            min=0,
            step="any",
            mode=NumberSelectorMode.BOX,
            unit_of_measurement="kWh",
        )
    )


def _to_decimal(value: float | int | str) -> Decimal:
    """Convert a selector value; floats must go through ``str``."""
    return Decimal(str(value))


def _finite(value: float | int | str) -> Decimal | None:
    """Return the value as a finite ``Decimal``, or ``None`` (NaN, infinity, junk)."""
    try:
        result = _to_decimal(value)
    except InvalidOperation:
        return None
    return result if result.is_finite() else None


def _global_limit_from_input(
    user_input: Mapping[str, Any], fallback: Decimal | None
) -> tuple[Decimal | None, bool]:
    """Return ``(limit, valid)``; the limit is ``None`` when the check is off."""
    if not user_input.get(CONF_SPIKE_CHECK, True):
        return None, True
    raw = user_input.get(CONF_SPIKE_LIMIT)
    if raw is None:
        return (fallback or DEFAULT_SPIKE_LIMIT), True
    limit = _finite(raw)
    if limit is None or limit <= 0:
        return None, False
    return limit, True


def _limit_to_number(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral_value() else float(value)


async def _async_timezone_names(hass: HomeAssistant, current: str) -> list[str]:
    names = await hass.async_add_executor_job(zoneinfo.available_timezones)
    return sorted({*names, current})


def _timezone_selector(names: list[str]) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(options=names, mode=SelectSelectorMode.DROPDOWN)
    )


class EnergyCostStatsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Initial setup: time zone and global spike limit."""

    VERSION = 1
    MINOR_VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: EnergyCostStatsConfigEntry,
    ) -> "EnergyCostStatsOptionsFlow":
        """Return the options flow (constructed without the config entry)."""
        return EnergyCostStatsOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Tariff plans are config subentries."""
        return {SUBENTRY_TYPE_TARIFF_PLAN: TariffPlanSubentryFlow}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the time zone and the spike limit."""
        errors: dict[str, str] = {}
        if user_input is not None:
            limit, valid = _global_limit_from_input(user_input, None)
            if valid:
                settings = IntegrationSettings(
                    time_zone=user_input[CONF_TIME_ZONE],
                    spike_limit=limit,
                    device_spike_limits={},
                    entities=(),
                )
                return self.async_create_entry(
                    title=DEFAULT_TITLE,
                    data={},
                    options=settings_to_options(settings),
                )
            errors[CONF_SPIKE_LIMIT] = "invalid_limit"

        default_tz = self.hass.config.time_zone
        names = await _async_timezone_names(self.hass, default_tz)
        schema = vol.Schema(
            {
                vol.Required(CONF_TIME_ZONE, default=default_tz): _timezone_selector(
                    names
                ),
                vol.Required(CONF_SPIKE_CHECK, default=True): BooleanSelector(),
                vol.Required(
                    CONF_SPIKE_LIMIT, default=float(DEFAULT_SPIKE_LIMIT)
                ): _spike_limit_selector(),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)


class EnergyCostStatsOptionsFlow(OptionsFlow):
    """Edit global settings, the energy sensors and per-device spike limits."""

    def __init__(self) -> None:
        """Initialize the flow state."""
        self._settings: IntegrationSettings | None = None

    def _current(self) -> IntegrationSettings:
        return settings_from_options(self.config_entry.options)

    def _is_energy_entity(self, entity_id: str) -> bool:
        registry_entry = er.async_get(self.hass).async_get(entity_id)
        if registry_entry is not None:
            device_class = registry_entry.device_class or (
                registry_entry.original_device_class
            )
            return device_class == _ENERGY
        state = self.hass.states.get(entity_id)
        return state is not None and state.attributes.get("device_class") == _ENERGY

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit time zone, spike limit and the selected entities."""
        try:
            current = self._current()
        except SettingsError:
            return self.async_abort(reason="invalid_options")

        errors: dict[str, str] = {}
        if user_input is not None:
            new_entities = [
                entity_id
                for entity_id in user_input.get(CONF_ENTITIES, [])
                if entity_id not in current.entities
                and not self._is_energy_entity(entity_id)
            ]
            limit, limit_valid = _global_limit_from_input(
                user_input, current.spike_limit
            )
            if not limit_valid:
                errors[CONF_SPIKE_LIMIT] = "invalid_limit"
            if new_entities:
                errors[CONF_ENTITIES] = "not_energy_entity"
            if not errors:
                entities = tuple(dict.fromkeys(user_input.get(CONF_ENTITIES, [])))
                kept = {
                    key: value
                    for key, value in current.device_spike_limits.items()
                    if key in entities
                }
                self._settings = IntegrationSettings(
                    time_zone=user_input[CONF_TIME_ZONE],
                    spike_limit=limit,
                    device_spike_limits=kept,
                    entities=entities,
                )
                if user_input.get(CONF_EDIT_DEVICE_LIMITS, False) and entities:
                    return await self.async_step_device_limits()
                return self.async_create_entry(data=settings_to_options(self._settings))

        suggested: Mapping[str, Any]
        if user_input is not None:
            suggested = user_input
        else:
            suggested = {
                CONF_TIME_ZONE: current.time_zone,
                CONF_SPIKE_CHECK: current.spike_limit is not None,
                CONF_SPIKE_LIMIT: _limit_to_number(
                    current.spike_limit or DEFAULT_SPIKE_LIMIT
                ),
                CONF_ENTITIES: list(current.entities),
            }
        names = await _async_timezone_names(self.hass, current.time_zone)
        schema = vol.Schema(
            {
                vol.Required(CONF_TIME_ZONE): _timezone_selector(names),
                vol.Required(CONF_SPIKE_CHECK): BooleanSelector(),
                vol.Optional(CONF_SPIKE_LIMIT): _spike_limit_selector(),
                vol.Optional(CONF_ENTITIES): EntitySelector(
                    EntitySelectorConfig(
                        domain="sensor", device_class=_ENERGY, multiple=True
                    )
                ),
                vol.Required(CONF_EDIT_DEVICE_LIMITS, default=False): BooleanSelector(),
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
            errors=errors,
        )

    async def async_step_device_limits(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Set an optional spike limit per selected entity."""
        settings = self._settings
        if settings is None:
            return await self.async_step_init()

        if user_input is not None:
            limits: dict[str, Decimal | None] = {}
            errors: dict[str, str] = {}
            for entity_id in settings.entities:
                if entity_id not in user_input:
                    continue
                value = _finite(user_input[entity_id])
                if value is None or value < 0:
                    errors[entity_id] = "invalid_limit"
                    continue
                limits[entity_id] = None if value == 0 else value
            if errors:
                return self._show_device_limits(settings, user_input, errors)
            final = IntegrationSettings(
                time_zone=settings.time_zone,
                spike_limit=settings.spike_limit,
                device_spike_limits=limits,
                entities=settings.entities,
            )
            return self.async_create_entry(data=settings_to_options(final))

        return self._show_device_limits(settings, None, {})

    def _show_device_limits(
        self,
        settings: IntegrationSettings,
        user_input: Mapping[str, Any] | None,
        errors: dict[str, str],
    ) -> ConfigFlowResult:
        suggested: dict[str, Any] = {}
        if user_input is not None:
            suggested = dict(user_input)
        else:
            stored = dict(self.config_entry.options.get(CONF_DEVICE_SPIKE_LIMITS, {}))
            for entity_id in settings.entities:
                if entity_id not in stored:
                    continue
                raw = stored[entity_id]
                suggested[entity_id] = (
                    0 if raw is None else _limit_to_number(_to_decimal(raw))
                )
        schema = vol.Schema(
            {
                vol.Optional(entity_id): _device_limit_selector()
                for entity_id in settings.entities
            }
        )
        return self.async_show_form(
            step_id="device_limits",
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
            errors=errors,
        )
