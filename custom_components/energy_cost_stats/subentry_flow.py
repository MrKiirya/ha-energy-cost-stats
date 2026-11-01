"""Config subentry flow for tariff plans (add from preset or copy, edit)."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigSubentry,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.helpers.selector import (
    DateSelector,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .const import (
    CONF_PLAN_NAME,
    CONF_PRESET,
    CONF_SOURCE_PLAN,
    CONF_VALID_FROM,
    PRESET_RU_TWO_ZONE,
    PRESET_SINGLE_RATE,
    PRESETS,
    SUBENTRY_TYPE_TARIFF_PLAN,
    zone_field,
)
from .engine.plan_codec import (
    format_periods,
    parse_periods,
    parse_price,
    plan_from_data,
    plan_to_data,
)
from .engine.presets import ru_three_zone, ru_two_zone, single_rate
from .engine.tariff import TariffPlan, TariffValidationError, Zone

_ZERO = Decimal(0)
_DETAIL = "detail"


@dataclass
class _ZoneTemplate:
    """What the plan form needs to know about one (fixed) zone."""

    key: str
    name: str
    periods: str
    price: str | None = None
    band_prices: tuple[Decimal, ...] = ()


def _preset_plan(preset: str) -> TariffPlan:
    start = date(2000, 1, 1)
    if preset == PRESET_SINGLE_RATE:
        return single_rate(valid_from=start, price=_ZERO)
    if preset == PRESET_RU_TWO_ZONE:
        return ru_two_zone(valid_from=start, day_price=_ZERO, night_price=_ZERO)
    return ru_three_zone(
        valid_from=start, peak_price=_ZERO, semi_peak_price=_ZERO, night_price=_ZERO
    )


def _plan_title(valid_from: date, name: str) -> str:
    return f"{valid_from.isoformat()} · {name}"


class TariffPlanSubentryFlow(ConfigSubentryFlow):
    """Add a tariff plan from a preset or as a copy, or edit an existing one."""

    def __init__(self) -> None:
        """Initialize the flow state."""
        self._name = ""
        self._zones: list[_ZoneTemplate] = []
        self._limits: tuple[Decimal, ...] = ()
        self._suggested: dict[str, Any] = {}
        self._editing: ConfigSubentry | None = None
        self._detail = ""

    def _plans(self) -> list[ConfigSubentry]:
        return [
            subentry
            for subentry in self._get_entry().subentries.values()
            if subentry.subentry_type == SUBENTRY_TYPE_TARIFF_PLAN
        ]

    def _load_template(self, plan: TariffPlan, *, with_prices: bool) -> None:
        self._name = plan.name
        self._limits = plan.volume_band_limits_kwh
        self._zones = [
            _ZoneTemplate(
                key=zone.key,
                name=zone.name,
                periods=format_periods(zone.periods),
                price=format(zone.price, "f") if with_prices else None,
                band_prices=zone.band_prices,
            )
            for zone in plan.zones
        ]

    def _template_suggestions(self) -> dict[str, Any]:
        suggested: dict[str, Any] = {CONF_PLAN_NAME: self._name}
        for zone in self._zones:
            suggested[zone_field(zone.key, "name")] = zone.name
            if zone.price is not None:
                suggested[zone_field(zone.key, "price")] = zone.price
            suggested[zone_field(zone.key, "periods")] = zone.periods
        return suggested

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Start: presets only when there are no plans, else a menu."""
        if not self._plans():
            return await self.async_step_preset()
        return self.async_show_menu(step_id="user", menu_options=["preset", "copy"])

    async def async_step_preset(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Choose a preset; its zones (with empty prices) fill the plan form."""
        if user_input is not None:
            self._load_template(
                _preset_plan(user_input[CONF_PRESET]), with_prices=False
            )
            self._suggested = self._template_suggestions()
            return self._show_plan_form({})
        schema = vol.Schema(
            {
                vol.Required(CONF_PRESET, default=PRESET_RU_TWO_ZONE): SelectSelector(
                    SelectSelectorConfig(
                        options=list(PRESETS),
                        mode=SelectSelectorMode.LIST,
                        translation_key="preset",
                    )
                )
            }
        )
        return self.async_show_form(step_id="preset", data_schema=schema)

    async def async_step_copy(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Copy an existing plan; defaults to the one with the latest ``valid_from``."""
        plans = self._plans()
        if user_input is not None:
            source = self._get_entry().subentries.get(user_input[CONF_SOURCE_PLAN])
            if source is None:
                return self.async_abort(reason="unknown_plan")
            try:
                plan = plan_from_data(source.data)
            except TariffValidationError:
                return self.async_abort(reason="invalid_plan_data")
            self._load_template(plan, with_prices=True)
            self._suggested = self._template_suggestions()
            return self._show_plan_form({})
        if not plans:
            return await self.async_step_preset()
        latest = max(plans, key=lambda s: str(s.data.get(CONF_VALID_FROM, "")))
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SOURCE_PLAN, default=latest.subentry_id
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value=s.subentry_id, label=s.title)
                            for s in sorted(
                                plans,
                                key=lambda s: str(s.data.get(CONF_VALID_FROM, "")),
                            )
                        ],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )
        return self.async_show_form(step_id="copy", data_schema=schema)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Edit an existing plan with the same form as a new one."""
        subentry = self._get_reconfigure_subentry()
        try:
            plan = plan_from_data(subentry.data)
        except TariffValidationError:
            return self.async_abort(reason="invalid_plan_data")
        self._editing = subentry
        self._load_template(plan, with_prices=True)
        self._suggested = {
            CONF_VALID_FROM: plan.valid_from.isoformat(),
            **self._template_suggestions(),
        }
        return self._show_plan_form({})

    async def async_step_plan(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Validate the submitted plan and save it."""
        if user_input is None or not self._zones:
            return self._show_plan_form({})
        errors: dict[str, str] = {}
        self._detail = ""
        plan = self._parse_plan(user_input, errors)
        if plan is None:
            self._suggested = dict(user_input)
            return self._show_plan_form(errors)
        title = _plan_title(plan.valid_from, plan.name)
        unique_id = plan.valid_from.isoformat()
        data = plan_to_data(plan)
        if self._editing is not None:
            return self.async_update_and_abort(
                self._get_entry(),
                self._editing,
                title=title,
                data=data,
                unique_id=unique_id,
            )
        return self.async_create_entry(title=title, data=data, unique_id=unique_id)

    def _parse_plan(
        self, user_input: Mapping[str, Any], errors: dict[str, str]
    ) -> TariffPlan | None:
        """Parse the form; fills ``errors`` (field errors first, then ``base``)."""
        valid_from = self._parse_valid_from(user_input, errors)
        name = str(user_input[CONF_PLAN_NAME]).strip()
        if not name:
            errors[CONF_PLAN_NAME] = "blank_name"
        zones: list[Zone] = []
        for template in self._zones:
            zone = self._parse_zone(template, user_input, errors)
            if zone is not None:
                zones.append(zone)
        if errors or valid_from is None:
            return None
        try:
            return TariffPlan(
                valid_from=valid_from,
                name=name,
                zones=tuple(zones),
                volume_band_limits_kwh=self._limits,
            )
        except TariffValidationError as err:
            errors["base"] = "invalid_plan"
            self._detail = str(err)
            return None

    def _parse_valid_from(
        self, user_input: Mapping[str, Any], errors: dict[str, str]
    ) -> date | None:
        try:
            valid_from = date.fromisoformat(str(user_input[CONF_VALID_FROM]))
        except ValueError:
            errors[CONF_VALID_FROM] = "invalid_date"
            return None
        own_id = self._editing.subentry_id if self._editing is not None else None
        taken = any(
            subentry.subentry_id != own_id
            and subentry.data.get(CONF_VALID_FROM) == valid_from.isoformat()
            for subentry in self._plans()
        )
        if taken:
            errors[CONF_VALID_FROM] = "valid_from_taken"
        return valid_from

    @staticmethod
    def _parse_zone(
        template: _ZoneTemplate,
        user_input: Mapping[str, Any],
        errors: dict[str, str],
    ) -> Zone | None:
        name_field = zone_field(template.key, "name")
        price_field = zone_field(template.key, "price")
        periods_field = zone_field(template.key, "periods")
        name = str(user_input[name_field]).strip()
        if not name:
            errors[name_field] = "blank_name"
        price: Decimal | None = None
        try:
            price = parse_price(str(user_input[price_field]))
        except TariffValidationError:
            errors[price_field] = "invalid_price"
        periods = None
        try:
            periods = parse_periods(str(user_input[periods_field]))
        except TariffValidationError:
            errors[periods_field] = "invalid_periods"
        if not name or price is None or periods is None:
            return None
        return Zone(
            key=template.key,
            name=name,
            price=price,
            periods=periods,
            band_prices=template.band_prices,
        )

    def _show_plan_form(self, errors: dict[str, str]) -> SubentryFlowResult:
        fields: dict[Any, Any] = {
            vol.Required(CONF_VALID_FROM): DateSelector(),
            vol.Required(CONF_PLAN_NAME): TextSelector(),
        }
        for zone in self._zones:
            fields[vol.Required(zone_field(zone.key, "name"))] = TextSelector()
            fields[vol.Required(zone_field(zone.key, "price"))] = TextSelector()
            fields[vol.Required(zone_field(zone.key, "periods"))] = TextSelector()
        detail = self._detail if "base" in errors else ""
        return self.async_show_form(
            step_id="plan",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(fields), self._suggested
            ),
            errors=errors,
            description_placeholders={_DETAIL: detail},
        )
