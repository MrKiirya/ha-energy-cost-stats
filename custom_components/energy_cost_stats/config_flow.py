"""Config flow and options flow for Energy Cost Stats."""

import zoneinfo
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import datetime
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
from homeassistant.data_entry_flow import section
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    BooleanSelector,
    DateSelector,
    EntitySelector,
    EntitySelectorConfig,
    IconSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)
from homeassistant.util import dt as dt_util

from . import EnergyCostStatsConfigEntry
from .const import (
    CONF_CHANGE,
    CONF_DELETE,
    CONF_DEVICE_SPIKE_LIMITS,
    CONF_EDIT_DEVICE_LIMITS,
    CONF_ENTITIES,
    CONF_FROM,
    CONF_ICON,
    CONF_SHOW,
    CONF_SIDEBAR,
    CONF_SPIKE_CHECK,
    CONF_SPIKE_LIMIT,
    CONF_TARIFF,
    CONF_TARIFFS,
    CONF_TIME_ZONE,
    CONF_TITLE,
    CONF_USE_DEFAULT,
    DEFAULT_PANEL_ICON,
    DEFAULT_PANEL_SHOW,
    DEFAULT_PANEL_TITLE,
    DEFAULT_SPIKE_LIMIT,
    DEFAULT_TITLE,
    DOMAIN,
    MENU_STEPS,
    SUBENTRY_TYPE_TARIFF,
)
from .engine.tariff import TariffValidationError
from .engine.tariff_config import (
    AppliedValidationError,
    Tariff,
    TariffConfig,
    config_from_data,
)
from .settings import (
    IntegrationSettings,
    PanelSettings,
    SettingsError,
    settings_from_options,
    settings_to_options,
    tariff_document,
)
from .tariff_flow import TariffSubentryFlow

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

    VERSION = 2
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
        """Tariffs are config subentries (docs/SPEC.md §3)."""
        return {SUBENTRY_TYPE_TARIFF: TariffSubentryFlow}

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
    """Options menu: sensors, applied tariff history, comparison and general settings.

    Every leaf form re-reads ``entry.options`` when it is submitted and ends the flow
    with the full option set (the entry then reloads and re-prices all hours). The
    forms that change the tariff document (applied history, comparison) first
    validate the result with the same document the setup uses.
    """

    def __init__(self) -> None:
        """Initialize the flow state."""
        self._entities: tuple[str, ...] = ()
        self._picked: str | None = None

    # ---- shared helpers --------------------------------------------------------

    def _current(self) -> IntegrationSettings:
        return settings_from_options(self.config_entry.options)

    def _tariff_data(self) -> list[Mapping[str, Any]]:
        return [
            subentry.data
            for subentry in self.config_entry.subentries.values()
            if subentry.subentry_type == SUBENTRY_TYPE_TARIFF
        ]

    def _tariffs(self) -> tuple[Tariff, ...]:
        return config_from_data({"tariffs": self._tariff_data()}).tariffs

    def _load(self, *, need_tariffs: bool = False) -> IntegrationSettings:
        """Current settings; raises ``_Abort`` with the reason to abort the flow."""
        try:
            settings = self._current()
            tariffs = self._tariffs()
        except (SettingsError, TariffValidationError) as err:
            raise _Abort("invalid_options") from err
        if need_tariffs and not tariffs:
            raise _Abort("no_tariffs")
        return settings

    def _is_energy_entity(self, entity_id: str) -> bool:
        registry_entry = er.async_get(self.hass).async_get(entity_id)
        if registry_entry is not None:
            device_class = registry_entry.device_class or (
                registry_entry.original_device_class
            )
            return device_class == _ENERGY
        state = self.hass.states.get(entity_id)
        return state is not None and state.attributes.get("device_class") == _ENERGY

    def _validate(self, settings: IntegrationSettings) -> TariffConfig:
        """Parse the candidate document exactly as setup will."""
        return config_from_data(tariff_document(settings, self._tariff_data()))

    def _check(
        self,
        settings: IntegrationSettings,
        new: tuple[str, str] | None = None,
    ) -> tuple[dict[str, str], dict[str, str]]:
        """Return ``(errors, placeholders)`` for the candidate; empty when valid.

        ``new`` is the ``(from, tariff)`` entry the user just typed. A problem in
        another entry of an already broken stored history is reported as a form
        error, not at the ``from`` field.
        """
        placeholders = {"first_valid_from": "", "detail": ""}
        try:
            self._validate(settings)
        except AppliedValidationError as err:
            change = err.change
            own = (
                new is not None
                and change is not None
                and (change.from_date.isoformat(), change.tariff) == new
            )
            if not own:
                placeholders["detail"] = str(err)
                return {"base": "invalid_config"}, placeholders
            if err.first_valid_from is not None:
                placeholders["first_valid_from"] = err.first_valid_from.isoformat()
            field = CONF_TARIFF if err.code == "unknown_tariff" else CONF_FROM
            return {field: err.code}, placeholders
        except TariffValidationError as err:
            placeholders["detail"] = str(err)
            return {"base": "invalid_config"}, placeholders
        return {}, placeholders

    def _save(self, settings: IntegrationSettings) -> ConfigFlowResult:
        return self.async_create_entry(data=settings_to_options(settings))

    def _tariff_options(self, tariffs: Sequence[Tariff]) -> list[SelectOptionDict]:
        return [SelectOptionDict(value=t.id, label=t.name) for t in tariffs]

    def _tariff_select(
        self, tariffs: Sequence[Tariff], *, multiple: bool = False
    ) -> SelectSelector:
        return SelectSelector(
            SelectSelectorConfig(
                options=self._tariff_options(tariffs),
                mode=SelectSelectorMode.LIST
                if multiple
                else SelectSelectorMode.DROPDOWN,
                multiple=multiple,
            )
        )

    # ---- menu ------------------------------------------------------------------

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the options menu."""
        try:
            self._load()
        except _Abort as err:
            return self.async_abort(reason=err.reason)
        return self.async_show_menu(step_id="init", menu_options=list(MENU_STEPS))

    # ---- sensors ---------------------------------------------------------------

    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select the energy sensors (and optionally edit per-device limits)."""
        try:
            current = self._load()
        except _Abort as err:
            return self.async_abort(reason=err.reason)

        errors: dict[str, str] = {}
        if user_input is not None:
            new_entities = [
                entity_id
                for entity_id in user_input.get(CONF_ENTITIES, [])
                if entity_id not in current.entities
                and not self._is_energy_entity(entity_id)
            ]
            if new_entities:
                errors[CONF_ENTITIES] = "not_energy_entity"
            else:
                entities = tuple(dict.fromkeys(user_input.get(CONF_ENTITIES, [])))
                kept = {
                    key: value
                    for key, value in current.device_spike_limits.items()
                    if key in entities
                }
                self._entities = entities
                if user_input.get(CONF_EDIT_DEVICE_LIMITS, False) and entities:
                    return await self.async_step_device_limits()
                return self._save(
                    replace(current, entities=entities, device_spike_limits=kept)
                )

        suggested: Mapping[str, Any]
        if user_input is not None:
            suggested = user_input
        else:
            suggested = {CONF_ENTITIES: list(current.entities)}
        schema = vol.Schema(
            {
                vol.Optional(CONF_ENTITIES): EntitySelector(
                    EntitySelectorConfig(
                        domain="sensor", device_class=_ENERGY, multiple=True
                    )
                ),
                vol.Required(CONF_EDIT_DEVICE_LIMITS, default=False): BooleanSelector(),
            }
        )
        return self.async_show_form(
            step_id="sensors",
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
            errors=errors,
        )

    async def async_step_device_limits(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Set an optional spike limit per selected entity."""
        try:
            current = self._load()
        except _Abort as err:
            return self.async_abort(reason=err.reason)
        entities = self._entities
        if not entities:
            return await self.async_step_sensors()
        settings = replace(
            current,
            entities=entities,
            device_spike_limits={
                k: v for k, v in current.device_spike_limits.items() if k in entities
            },
        )

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
            return self._save(replace(settings, device_spike_limits=limits))

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

    # ---- general ---------------------------------------------------------------

    async def async_step_general(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit the time zone, the spike limit and the sidebar panel options."""
        try:
            current = self._load()
        except _Abort as err:
            return self.async_abort(reason=err.reason)

        errors: dict[str, str] = {}
        panel = current.panel or PanelSettings(
            DEFAULT_PANEL_SHOW, DEFAULT_PANEL_TITLE, DEFAULT_PANEL_ICON
        )
        if user_input is not None:
            limit, limit_valid = _global_limit_from_input(
                user_input, current.spike_limit
            )
            if limit_valid:
                sidebar = user_input.get(CONF_SIDEBAR) or {}
                title = str(sidebar.get(CONF_TITLE) or "").strip()
                icon = str(sidebar.get(CONF_ICON) or "").strip()
                return self._save(
                    replace(
                        current,
                        time_zone=user_input[CONF_TIME_ZONE],
                        spike_limit=limit,
                        panel=PanelSettings(
                            show=bool(sidebar.get(CONF_SHOW, panel.show)),
                            title=title or panel.title,
                            icon=icon or panel.icon,
                        ),
                    )
                )
            errors[CONF_SPIKE_LIMIT] = "invalid_limit"

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
                CONF_SIDEBAR: {
                    CONF_SHOW: panel.show,
                    CONF_TITLE: panel.title,
                    CONF_ICON: panel.icon,
                },
            }
        names = await _async_timezone_names(self.hass, current.time_zone)
        schema = vol.Schema(
            {
                vol.Required(CONF_TIME_ZONE): _timezone_selector(names),
                vol.Required(CONF_SPIKE_CHECK): BooleanSelector(),
                vol.Optional(CONF_SPIKE_LIMIT): _spike_limit_selector(),
                vol.Required(CONF_SIDEBAR): section(
                    vol.Schema(
                        {
                            vol.Optional(CONF_SHOW): BooleanSelector(),
                            vol.Optional(CONF_TITLE): TextSelector(),
                            vol.Optional(CONF_ICON): IconSelector(),
                        }
                    ),
                    {"collapsed": True},
                ),
            }
        )
        return self.async_show_form(
            step_id="general",
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
            errors=errors,
        )

    # ---- applied tariff history --------------------------------------------------

    def _history_rows(self, settings: IntegrationSettings) -> str:
        names = {t.id: t.name for t in self._tariffs()}
        rows = [
            f"| {start} | {names.get(tariff, tariff).replace('|', chr(92) + '|')}"
            f" (`{tariff}`) |"
            for start, tariff in sorted(settings.applied)
        ]
        return "\n".join(rows) if rows else "| — | — |"

    async def async_step_applied(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the applied history and the actions on it."""
        try:
            current = self._load(need_tariffs=True)
        except _Abort as err:
            return self.async_abort(reason=err.reason)
        options = ["applied_single", "applied_add"]
        if current.applied:
            options.append("applied_pick")
        return self.async_show_menu(
            step_id="applied",
            menu_options=options,
            description_placeholders={"history": self._history_rows(current)},
        )

    def _show_applied_form(
        self,
        step_id: str,
        schema: vol.Schema,
        suggested: Mapping[str, Any],
        errors: dict[str, str],
        placeholders: dict[str, str],
    ) -> ConfigFlowResult:
        return self.async_show_form(
            step_id=step_id,
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def _async_today(self, time_zone: str) -> str:
        """Today's date in the configured time zone (host zone as a fallback)."""
        tz = await dt_util.async_get_time_zone(time_zone)
        return datetime.now(tz).date().isoformat()

    async def async_step_applied_single(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Use one tariff for the whole period (replaces the history)."""
        try:
            current = self._load(need_tariffs=True)
        except _Abort as err:
            return self.async_abort(reason=err.reason)
        tariffs = self._tariffs()
        by_id = {t.id: t for t in tariffs}
        errors: dict[str, str] = {}
        placeholders = {"first_valid_from": "", "detail": ""}
        if user_input is not None:
            tariff = by_id.get(user_input[CONF_TARIFF])
            if tariff is None:
                errors = {CONF_TARIFF: "unknown_tariff"}
            else:
                start = user_input.get(CONF_FROM) or (
                    tariff.versions[0].valid_from.isoformat()
                )
                candidate = replace(current, applied=((start, tariff.id),))
                errors, placeholders = self._check(candidate, (start, tariff.id))
                if not errors:
                    return self._save(candidate)
        if user_input is not None:
            suggested: Mapping[str, Any] = user_input
        else:
            last = sorted(current.applied)[-1][1] if current.applied else None
            first = by_id.get(last, tariffs[0]) if last else tariffs[0]
            suggested = {CONF_TARIFF: first.id}
        schema = vol.Schema(
            {
                vol.Required(CONF_TARIFF): self._tariff_select(tariffs),
                vol.Optional(CONF_FROM): DateSelector(),
            }
        )
        return self._show_applied_form(
            "applied_single", schema, suggested, errors, placeholders
        )

    async def async_step_applied_add(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add one change to the applied history."""
        try:
            current = self._load(need_tariffs=True)
        except _Abort as err:
            return self.async_abort(reason=err.reason)
        tariffs = self._tariffs()
        errors: dict[str, str] = {}
        placeholders = {"first_valid_from": "", "detail": ""}
        if user_input is not None:
            new = (user_input[CONF_FROM], user_input[CONF_TARIFF])
            candidate = replace(current, applied=(*current.applied, new))
            errors, placeholders = self._check(candidate, new)
            if not errors:
                return self._save(candidate)
        suggested: Mapping[str, Any] = user_input or {
            CONF_FROM: await self._async_today(current.time_zone)
        }
        schema = vol.Schema(
            {
                vol.Required(CONF_FROM): DateSelector(),
                vol.Required(CONF_TARIFF): self._tariff_select(tariffs),
            }
        )
        return self._show_applied_form(
            "applied_add", schema, suggested, errors, placeholders
        )

    async def async_step_applied_pick(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick one change of the history to edit."""
        try:
            current = self._load(need_tariffs=True)
        except _Abort as err:
            return self.async_abort(reason=err.reason)
        if user_input is not None:
            self._picked = user_input[CONF_CHANGE]
            return await self.async_step_applied_change()
        names = {t.id: t.name for t in self._tariffs()}
        options = [
            SelectOptionDict(
                value=start, label=f"{start} · {names.get(tariff, tariff)}"
            )
            for start, tariff in sorted(current.applied)
        ]
        schema = vol.Schema(
            {
                vol.Required(CONF_CHANGE): SelectSelector(
                    SelectSelectorConfig(options=options, mode=SelectSelectorMode.LIST)
                )
            }
        )
        return self.async_show_form(step_id="applied_pick", data_schema=schema)

    async def async_step_applied_change(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Re-date, re-assign or delete the picked change."""
        try:
            current = self._load(need_tariffs=True)
        except _Abort as err:
            return self.async_abort(reason=err.reason)
        picked = next(
            (item for item in current.applied if item[0] == self._picked), None
        )
        if picked is None:
            return await self.async_step_applied()
        tariffs = self._tariffs()
        errors: dict[str, str] = {}
        placeholders = {"first_valid_from": "", "detail": ""}
        if user_input is not None:
            rest = tuple(item for item in current.applied if item != picked)
            new = None
            if user_input.get(CONF_DELETE, False):
                applied = rest
            else:
                new = (user_input[CONF_FROM], user_input[CONF_TARIFF])
                applied = (*rest, new)
            candidate = replace(current, applied=applied)
            errors, placeholders = self._check(candidate, new)
            if not errors:
                return self._save(candidate)
        suggested: Mapping[str, Any] = user_input or {
            CONF_FROM: picked[0],
            CONF_TARIFF: picked[1],
        }
        schema = vol.Schema(
            {
                vol.Required(CONF_FROM): DateSelector(),
                vol.Required(CONF_TARIFF): self._tariff_select(tariffs),
                vol.Required(CONF_DELETE, default=False): BooleanSelector(),
            }
        )
        return self._show_applied_form(
            "applied_change", schema, suggested, errors, placeholders
        )

    # ---- comparison ------------------------------------------------------------

    async def async_step_compare(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose the tariffs shown in the comparison."""
        try:
            current = self._load(need_tariffs=True)
        except _Abort as err:
            return self.async_abort(reason=err.reason)
        tariffs = self._tariffs()
        # Computed from the raw history so that a broken history cannot block this step.
        used = {tariff for _, tariff in current.applied}
        default_ids = tuple(t.id for t in tariffs if t.id not in used)
        if user_input is not None:
            if user_input.get(CONF_USE_DEFAULT, False):
                compare = None
            else:
                chosen = set(user_input.get(CONF_TARIFFS, []))
                compare = tuple(t.id for t in tariffs if t.id in chosen)
            candidate = replace(current, compare=compare)
            errors, placeholders = self._check(candidate)
            if not errors:
                return self._save(candidate)
            return self._show_compare(
                tariffs, user_input, errors, default_ids, placeholders["detail"]
            )
        suggested = {
            CONF_USE_DEFAULT: current.compare is None,
            CONF_TARIFFS: list(
                default_ids if current.compare is None else current.compare
            ),
        }
        return self._show_compare(tariffs, suggested, {}, default_ids)

    def _show_compare(
        self,
        tariffs: Sequence[Tariff],
        suggested: Mapping[str, Any],
        errors: dict[str, str],
        default_ids: Sequence[str],
        detail: str = "",
    ) -> ConfigFlowResult:
        names = {t.id: t.name for t in tariffs}
        schema = vol.Schema(
            {
                vol.Required(CONF_USE_DEFAULT): BooleanSelector(),
                vol.Optional(CONF_TARIFFS): self._tariff_select(tariffs, multiple=True),
            }
        )
        return self.async_show_form(
            step_id="compare",
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
            errors=errors,
            description_placeholders={
                "default": ", ".join(names[i] for i in default_ids) or "-",
                "detail": detail,
            },
        )


class _Abort(Exception):
    """Internal: abort the options flow with this reason."""

    def __init__(self, reason: str) -> None:
        """Keep the abort reason."""
        super().__init__(reason)
        self.reason = reason
