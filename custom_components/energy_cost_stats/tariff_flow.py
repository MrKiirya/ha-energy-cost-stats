"""Subentry flow for tariffs: add a tariff, manage its versions, rename it (task 018).

One config subentry of type ``tariff`` per tariff (SPEC §3). The ``user`` source adds a
tariff in several small steps; the ``reconfigure`` source (the gear on the tariff's
row) opens a menu with new version / edit or delete a version / rename. All parsing and
document editing lives in ``engine/tariff_edit.py``; this module only collects form
input, validates the **whole** configuration with ``config_from_data`` and stores the
result. Errors inside sections are keyed by the section name because Home Assistant
shows them above the section, not at its fields. Any stored change reloads the entry
(``__init__.py``), which re-prices every past hour.
"""

import re
from collections.abc import Mapping, Sequence
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
from homeassistant.data_entry_flow import section
from homeassistant.helpers.selector import (
    BooleanSelector,
    DateSelector,
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
from homeassistant.util import slugify

from .const import (
    ABORT_YAML_MODE,
    BASE_COPY,
    BASE_CUSTOM,
    BASE_SINGLE_RATE,
    BASE_THREE_ZONE,
    BASE_TWO_ZONE,
    CONF_APPLIED,
    CONF_BASE,
    CONF_COMPARE,
    CONF_COUNT,
    CONF_DELETE,
    CONF_SOURCE,
    CONF_TARIFF_ID,
    CONF_TARIFF_NAME,
    CONF_VALID_FROM,
    CONF_VERSION,
    MAX_ZONES,
    SECTION_HOURS,
    SUBENTRY_TYPE_TARIFF,
)
from .engine.plan_codec import format_periods, parse_periods, parse_price
from .engine.presets import PRESET_ZONES
from .engine.tariff import Period, TariffValidationError, Zone
from .engine.tariff_config import Tariff, config_from_data
from .engine.tariff_edit import (
    ZoneInput,
    delete_version,
    diagnose_hours,
    first_version_doc,
    format_hours,
    later_version_doc,
    move_applied_start,
    rename_references,
    replace_version,
    unique_tariff_id,
    versions_table,
)
from .yaml_mode import is_yaml_mode

_ID_RE = re.compile(r"[a-z0-9_]{1,32}")
_PRESET_BASES = (BASE_SINGLE_RATE, BASE_TWO_ZONE, BASE_THREE_ZONE)
_DEFAULT_BASE = BASE_TWO_ZONE


@dataclass(frozen=True, slots=True)
class _ZoneForm:
    """Suggested text values of one zone section (empty text = no suggestion)."""

    key: str
    name: str = ""
    price: str = ""
    hours: str = ""


def _zone_section_key(index: int) -> str:
    return f"zone_{index}"


def _text() -> TextSelector:
    return TextSelector()


def _first_version_schema(
    count: int, *, with_key: bool, with_delete: bool
) -> vol.Schema:
    """A fresh schema (``add_suggested_values_to_schema`` mutates its sections)."""
    fields: dict[Any, Any] = {vol.Required(CONF_VALID_FROM): DateSelector()}
    for index in range(1, count + 1):
        inner: dict[Any, Any] = {}
        if with_key:
            inner[vol.Required("key")] = _text()
        inner[vol.Required("name")] = _text()
        inner[vol.Required("price")] = _text()
        inner[vol.Required("hours")] = _text()
        fields[vol.Required(_zone_section_key(index))] = section(
            vol.Schema(inner), {"collapsed": False}
        )
    if with_delete:
        fields[vol.Optional(CONF_DELETE, default=False)] = BooleanSelector()
    return vol.Schema(fields)


def _later_version_schema(count: int, *, with_delete: bool) -> vol.Schema:
    fields: dict[Any, Any] = {vol.Required(CONF_VALID_FROM): DateSelector()}
    for index in range(1, count + 1):
        fields[vol.Required(f"price_{index}")] = _text()
    fields[vol.Required(SECTION_HOURS)] = section(
        vol.Schema({vol.Required(f"hours_{i}"): _text() for i in range(1, count + 1)}),
        {"collapsed": True},
    )
    if with_delete:
        fields[vol.Optional(CONF_DELETE, default=False)] = BooleanSelector()
    return vol.Schema(fields)


def _price_text(price: Any) -> str:
    return format(price, "f")


def _suggest(**values: Any) -> dict[str, Any]:
    """Drop empty suggestions so the form field stays empty."""
    return {key: value for key, value in values.items() if value not in ("", None)}


def _zone_form_from_zone(zone: Zone) -> _ZoneForm:
    return _ZoneForm(
        zone.key, zone.name, _price_text(zone.price), format_periods(zone.periods)
    )


class TariffSubentryFlow(ConfigSubentryFlow):
    """Add a tariff (``user``) or manage an existing one (``reconfigure``)."""

    def __init__(self) -> None:
        """Initialize the flow state."""
        self._name = ""
        self._preset: str | None = None
        self._custom = False
        self._template: list[_ZoneForm] = []
        self._tariff_id = ""
        self._source_id = ""
        self._selected: str | None = None

    # ---- shared helpers --------------------------------------------

    def _tariff_subentries(self) -> list[ConfigSubentry]:
        return [
            subentry
            for subentry in self._get_entry().subentries.values()
            if subentry.subentry_type == SUBENTRY_TYPE_TARIFF
        ]

    @staticmethod
    def _resolve(subentry: ConfigSubentry) -> Tariff:
        return config_from_data({"tariffs": [dict(subentry.data)]}).tariffs[0]

    def _applied(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._get_entry().options.get(CONF_APPLIED, [])]

    def _compare(self) -> list[str] | None:
        compare = self._get_entry().options.get(CONF_COMPARE)
        return None if compare is None else list(compare)

    @staticmethod
    def _placeholders(**values: str) -> dict[str, str]:
        """Every placeholder the strings of the tariff steps may use."""
        base = {
            "zones": "",
            "hours": "",
            "detail": "",
            "name": "",
            "id": "",
            "versions": "",
            "applied": "",
            **{f"zone_{i}": "" for i in range(1, MAX_ZONES + 1)},
        }
        return {**base, **values}

    def _validate(
        self,
        tariff_doc: Mapping[str, Any],
        replacing: ConfigSubentry | None,
        applied: list[dict[str, Any]],
        compare: list[str] | None,
    ) -> tuple[dict[str, str], str]:
        """Validate the whole configuration; returns ``(errors, detail)``."""
        first = min(str(v["valid_from"]) for v in tariff_doc["versions"])
        if any(
            item["tariff"] == tariff_doc["id"] and str(item["from"]) < first
            for item in applied
        ):
            return {CONF_VALID_FROM: "applied_without_version"}, ""
        documents: list[Mapping[str, Any]] = [
            tariff_doc if item is replacing else dict(item.data)
            for item in self._tariff_subentries()
        ]
        if replacing is None:
            documents.append(tariff_doc)
        document: dict[str, Any] = {"tariffs": documents, "applied": applied}
        if compare is not None:
            document[CONF_COMPARE] = compare
        try:
            config_from_data(document)
        except TariffValidationError as err:
            return {"base": "invalid_tariff"}, str(err)
        return {}, ""

    def _store(
        self,
        subentry: ConfigSubentry,
        tariff_doc: Mapping[str, Any],
        *,
        applied: list[dict[str, Any]] | None = None,
        compare: list[str] | None = None,
    ) -> SubentryFlowResult:
        """Write options first, then the subentry, with no ``await`` in between.

        Both updates are applied before any update listener gets past its first yield
        (the listener in ``__init__.py`` yields once, because Home Assistant may start
        listeners eagerly), so the reload always sees a consistent configuration.
        """
        entry = self._get_entry()
        options = dict(entry.options)
        if applied is not None and applied != options.get(CONF_APPLIED, []):
            options[CONF_APPLIED] = applied
        if compare is not None and compare != options.get(CONF_COMPARE):
            options[CONF_COMPARE] = compare
        if options != dict(entry.options):
            self.hass.config_entries.async_update_entry(entry, options=options)
        changes: dict[str, Any] = {}
        if subentry.unique_id != tariff_doc["id"]:
            changes["unique_id"] = tariff_doc["id"]
        return self.async_update_and_abort(
            entry,
            subentry,
            title=str(tariff_doc["name"]),
            data=dict(tariff_doc),
            **changes,
        )

    @staticmethod
    def _move_applied(
        applied: list[dict[str, Any]], tariff_id: str, old: str, new: str
    ) -> list[dict[str, Any]] | None:
        """Move the applied item that started with the old first version.

        ``None`` when the new start would reorder the applied history.
        """
        moved = move_applied_start(
            [(str(item["from"]), str(item["tariff"])) for item in applied],
            tariff_id,
            old,
            new,
        )
        if moved is None:
            return None
        return [{"from": start, "tariff": tariff} for start, tariff in moved]

    # ---- reading zone sections -------------------------------------

    @staticmethod
    def _check_hours(
        entries: Sequence[tuple[str, str, tuple[Period, ...]]],
    ) -> tuple[dict[str, str], str]:
        """Overlaps per section, uncovered hours as ``base``; ``(errors, hours)``."""
        problems = diagnose_hours([(key, periods) for key, _, periods in entries])
        errors: dict[str, str] = {}
        for key, error_key, _ in entries:
            if key in problems.overlapping:
                errors[error_key] = "hours_overlap"
        uncovered = ""
        if problems.uncovered:
            errors["base"] = "hours_uncovered"
            uncovered = format_hours(problems.uncovered)
        return errors, uncovered

    def _read_zones(
        self,
        user_input: Mapping[str, Any],
        count: int,
        keys: Sequence[str] | None,
    ) -> tuple[list[ZoneInput], dict[str, str], str]:
        """Parse the zone sections; ``keys`` fixes the zone keys (otherwise typed)."""
        errors: dict[str, str] = {}
        zones: list[ZoneInput] = []
        for index in range(1, count + 1):
            name_key = _zone_section_key(index)
            values: Mapping[str, Any] = user_input.get(name_key) or {}
            key = keys[index - 1] if keys else str(values.get("key", "")).strip()
            name = str(values.get("name", "")).strip()
            try:
                if _ID_RE.fullmatch(key) is None:
                    raise _FieldError("invalid_zone_key")
                if not name:
                    raise _FieldError("blank_name")
                price = _parse_price(values.get("price", ""))
                periods = _parse_hours(values.get("hours", ""))
            except _FieldError as err:
                errors[name_key] = err.code
                continue
            zones.append(ZoneInput(key, name, price, periods))
        if errors:
            return zones, errors, ""
        seen: dict[str, int] = {}
        for zone in zones:
            seen[zone.key] = seen.get(zone.key, 0) + 1
        for index, zone in enumerate(zones, start=1):
            if seen[zone.key] > 1:
                errors[_zone_section_key(index)] = "duplicate_zone_key"
        if errors:
            return zones, errors, ""
        hour_errors, uncovered = self._check_hours(
            [
                (zone.key, _zone_section_key(index), zone.periods)
                for index, zone in enumerate(zones, start=1)
            ]
        )
        return zones, hour_errors, uncovered

    # ---- add a tariff ----------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Name and base of the new tariff."""
        if is_yaml_mode(self.hass):
            return self.async_abort(reason=ABORT_YAML_MODE)
        errors: dict[str, str] = {}
        has_tariffs = bool(self._tariff_subentries())
        if user_input is not None:
            name = str(user_input[CONF_TARIFF_NAME]).strip()
            base = user_input[CONF_BASE]
            if not name:
                errors[CONF_TARIFF_NAME] = "blank_name"
            else:
                self._name = name
                if base == BASE_COPY:
                    return await self.async_step_copy()
                if base == BASE_CUSTOM:
                    self._custom = True
                    return await self.async_step_custom_zones()
                self._preset = base
                self._template = [
                    _ZoneForm(z.key, z.name, "", format_periods(z.periods))
                    for z in PRESET_ZONES[base]
                ]
                return await self.async_step_tariff_id()
        bases = [*_PRESET_BASES, BASE_CUSTOM] + ([BASE_COPY] if has_tariffs else [])
        schema = vol.Schema(
            {
                vol.Required(CONF_TARIFF_NAME): _text(),
                vol.Required(CONF_BASE, default=_DEFAULT_BASE): SelectSelector(
                    SelectSelectorConfig(
                        options=bases,
                        translation_key="tariff_base",
                        mode=SelectSelectorMode.LIST,
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
            description_placeholders=self._placeholders(),
        )

    async def async_step_copy(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Choose the tariff whose latest version is the starting point."""
        subentries = self._tariff_subentries()
        if user_input is not None:
            source = next(
                (s for s in subentries if s.unique_id == user_input[CONF_SOURCE]), None
            )
            if source is not None:
                try:
                    tariff = self._resolve(source)
                except TariffValidationError:
                    return self.async_abort(reason="invalid_stored_tariff")
                first_version = source.data["versions"][0]
                self._preset = first_version.get("preset")
                self._template = [
                    _zone_form_from_zone(z) for z in tariff.versions[-1].zones
                ]
                return await self.async_step_tariff_id()
        options = [
            SelectOptionDict(value=str(s.unique_id), label=s.title) for s in subentries
        ]
        schema = vol.Schema(
            {
                vol.Required(CONF_SOURCE, default=options[-1]["value"]): SelectSelector(
                    SelectSelectorConfig(options=options, mode=SelectSelectorMode.LIST)
                )
            }
        )
        return self.async_show_form(
            step_id="copy",
            data_schema=schema,
            description_placeholders=self._placeholders(),
        )

    async def async_step_custom_zones(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """How many zones a custom tariff has."""
        if user_input is not None:
            count = int(user_input[CONF_COUNT])
            self._template = [_ZoneForm(f"t{index}") for index in range(1, count + 1)]
            return await self.async_step_tariff_id()
        schema = vol.Schema(
            {
                vol.Required(CONF_COUNT, default=2): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=MAX_ZONES, step=1, mode=NumberSelectorMode.BOX
                    )
                )
            }
        )
        return self.async_show_form(
            step_id="custom_zones",
            data_schema=schema,
            description_placeholders=self._placeholders(),
        )

    async def async_step_tariff_id(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """The id (prefilled from the name); it is the stable key of the tariff."""
        errors: dict[str, str] = {}
        taken = [str(s.unique_id) for s in self._tariff_subentries()]
        if user_input is not None:
            tariff_id = str(user_input[CONF_TARIFF_ID]).strip()
            if _ID_RE.fullmatch(tariff_id) is None:
                errors[CONF_TARIFF_ID] = "invalid_id"
            elif tariff_id in taken:
                errors[CONF_TARIFF_ID] = "id_taken"
            else:
                self._tariff_id = tariff_id
                return await self.async_step_first_version()
        suggestion = (
            user_input
            if user_input is not None
            else {CONF_TARIFF_ID: unique_tariff_id(slugify(self._name), taken)}
        )
        schema = vol.Schema({vol.Required(CONF_TARIFF_ID): _text()})
        return self.async_show_form(
            step_id="tariff_id",
            data_schema=self.add_suggested_values_to_schema(schema, suggestion),
            errors=errors,
            description_placeholders=self._placeholders(name=self._name),
        )

    def _zones_description(self, template: Sequence[_ZoneForm]) -> str:
        parts = [
            f"Zone {index}: {zone.name} ({zone.key})" if zone.name else f"Zone {index}"
            for index, zone in enumerate(template, start=1)
        ]
        return " · ".join(parts)

    def _first_version_form(
        self,
        step_id: str,
        template: Sequence[_ZoneForm],
        suggestion: Mapping[str, Any],
        errors: dict[str, str],
        placeholders: dict[str, str],
        *,
        with_key: bool,
        with_delete: bool,
    ) -> SubentryFlowResult:
        schema = _first_version_schema(
            len(template), with_key=with_key, with_delete=with_delete
        )
        return self.async_show_form(
            step_id=step_id,
            data_schema=self.add_suggested_values_to_schema(schema, suggestion),
            errors=errors,
            description_placeholders=self._placeholders(
                **{**placeholders, "zones": self._zones_description(template)}
            ),
        )

    @staticmethod
    def _zone_suggestions(
        template: Sequence[_ZoneForm], *, with_key: bool
    ) -> dict[str, Any]:
        suggestion: dict[str, Any] = {}
        for index, zone in enumerate(template, start=1):
            values = _suggest(name=zone.name, price=zone.price, hours=zone.hours)
            if with_key:
                values.update(_suggest(key=zone.key))
            suggestion[_zone_section_key(index)] = values
        return suggestion

    async def async_step_first_version(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """The first version: date, and name, price and hours of every zone."""
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}
        if user_input is not None:
            keys = None if self._custom else [zone.key for zone in self._template]
            zones, errors, uncovered = self._read_zones(
                user_input, len(self._template), keys
            )
            placeholders["hours"] = uncovered
            if not errors:
                doc = {
                    "id": self._tariff_id,
                    "name": self._name,
                    "versions": [
                        first_version_doc(
                            str(user_input[CONF_VALID_FROM]), zones, self._preset
                        )
                    ],
                }
                errors, detail = self._validate(
                    doc, None, self._applied(), self._compare()
                )
                placeholders["detail"] = detail
                if not errors:
                    return self.async_create_entry(
                        title=self._name, data=doc, unique_id=self._tariff_id
                    )
        suggestion = (
            user_input
            if user_input is not None
            else self._zone_suggestions(self._template, with_key=self._custom)
        )
        return self._first_version_form(
            "first_version",
            self._template,
            suggestion,
            errors,
            placeholders,
            with_key=self._custom,
            with_delete=False,
        )

    # ---- the tariff menu -------------------------------------------

    def _reconfigure_context(self) -> tuple[ConfigSubentry, Tariff]:
        subentry = self._get_reconfigure_subentry()
        return subentry, self._resolve(subentry)

    def _tariff_placeholders(self, tariff: Tariff) -> dict[str, str]:
        starts = [
            str(item["from"]) for item in self._applied() if item["tariff"] == tariff.id
        ]
        return self._placeholders(
            name=tariff.name,
            id=tariff.id,
            versions=versions_table(tariff),
            applied=f"Applied from {', '.join(starts)}" if starts else "Not applied",
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """The tariff menu."""
        if is_yaml_mode(self.hass):
            return self.async_abort(reason=ABORT_YAML_MODE)
        try:
            _, tariff = self._reconfigure_context()
        except TariffValidationError:
            return self.async_abort(reason="invalid_stored_tariff")
        return self.async_show_menu(
            step_id="reconfigure",
            menu_options=["new_version", "select_version", "rename"],
            description_placeholders=self._tariff_placeholders(tariff),
        )

    # ---- new and edited later versions -----------------------------

    def _today(self) -> date:
        runtime = getattr(self._get_entry(), "runtime_data", None)
        zone = getattr(runtime, "tzinfo", None)
        return dt_util.now(zone).date()

    async def async_step_new_version(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Add a later version (prices, and hours only when they change)."""
        return await self._later_version("new_version", None, user_input)

    async def async_step_edit_version(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Edit or delete a version other than the first."""
        return await self._later_version("edit_version", self._selected, user_input)

    async def _later_version(
        self, step_id: str, editing: str | None, user_input: dict[str, Any] | None
    ) -> SubentryFlowResult:
        subentry, tariff = self._reconfigure_context()
        versions = tariff.versions
        index = (
            next(
                i for i, v in enumerate(versions) if v.valid_from.isoformat() == editing
            )
            if editing is not None
            else len(versions) - 1
        )
        zones = versions[index].zones
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}
        if user_input is not None:
            errors, placeholders, result = self._save_later_version(
                subentry, tariff, editing, index, user_input
            )
            if result is not None:
                return result
        if user_input is not None:
            suggestion: Mapping[str, Any] = user_input
        else:
            suggestion = {
                f"price_{i}": _price_text(zone.price)
                for i, zone in enumerate(zones, start=1)
            }
            suggestion[SECTION_HOURS] = {
                f"hours_{i}": format_periods(zone.periods)
                for i, zone in enumerate(zones, start=1)
            }
            if editing is not None:
                suggestion[CONF_VALID_FROM] = editing
            elif self._today() > versions[-1].valid_from:
                suggestion[CONF_VALID_FROM] = self._today().isoformat()
        schema = _later_version_schema(len(zones), with_delete=editing is not None)
        zone_labels = {
            f"zone_{i}": f"{zone.name} ({zone.key})"
            for i, zone in enumerate(zones, start=1)
        }
        return self.async_show_form(
            step_id=step_id,
            data_schema=self.add_suggested_values_to_schema(schema, suggestion),
            errors=errors,
            description_placeholders={
                **self._tariff_placeholders(tariff),
                **zone_labels,
                **placeholders,
            },
        )

    def _save_later_version(
        self,
        subentry: ConfigSubentry,
        tariff: Tariff,
        editing: str | None,
        index: int,
        user_input: Mapping[str, Any],
    ) -> tuple[dict[str, str], dict[str, str], SubentryFlowResult | None]:
        """Validate and store; returns ``(errors, placeholders, result)``."""
        doc = dict(subentry.data)
        applied = self._applied()
        if editing is not None and user_input.get(CONF_DELETE):
            new_doc = delete_version(doc, editing)
            errors, detail = self._validate(new_doc, subentry, applied, self._compare())
            if errors:
                return errors, self._placeholders(detail=detail), None
            return {}, {}, self._store(subentry, new_doc, applied=applied)

        versions = tariff.versions
        zones = versions[index].zones
        valid_from = str(user_input[CONF_VALID_FROM])
        errors: dict[str, str] = {}
        others = [
            v.valid_from.isoformat()
            for v in versions
            if v.valid_from.isoformat() != editing
        ]
        if valid_from in others:
            errors[CONF_VALID_FROM] = "valid_from_taken"

        prices: dict[str, Any] = {}
        periods: dict[str, tuple[Period, ...]] = {}
        hours_input: Mapping[str, Any] = user_input.get(SECTION_HOURS) or {}
        for number, zone in enumerate(zones, start=1):
            try:
                prices[zone.key] = _parse_price(user_input.get(f"price_{number}", ""))
            except _FieldError as err:
                errors[f"price_{number}"] = err.code
            try:
                periods[zone.key] = _parse_hours(hours_input.get(f"hours_{number}", ""))
            except _FieldError as err:
                errors[SECTION_HOURS] = err.code
        placeholders: dict[str, str] = {}
        if not errors:
            hour_errors, uncovered = self._check_hours(
                [(key, SECTION_HOURS, value) for key, value in periods.items()]
            )
            errors.update(hour_errors)
            placeholders["hours"] = uncovered
        if errors:
            return errors, self._placeholders(**placeholders), None

        stored_version = (
            next(v for v in doc["versions"] if str(v["valid_from"]) == editing)
            if editing is not None
            else None
        )
        if stored_version is not None and ({"preset", "zones"} & stored_version.keys()):
            own = [
                ZoneInput(zone.key, zone.name, prices[zone.key], periods[zone.key])
                for zone in zones
            ]
            version_doc = first_version_doc(
                valid_from, own, stored_version.get("preset")
            )
        else:
            earlier = valid_from < versions[0].valid_from.isoformat()
            inherited = (
                versions[0].zones
                if earlier
                else self._inherited_zones(versions, valid_from, editing)
            )
            if [z.key for z in inherited] != [z.key for z in zones]:
                return (
                    {"base": "invalid_tariff"},
                    self._placeholders(detail="the zones of the version before differ"),
                    None,
                )
            if earlier:
                # A version before the first one becomes the new first version, so it
                # carries explicit zones (the former first version is unchanged).
                version_doc = first_version_doc(
                    valid_from,
                    [
                        ZoneInput(z.key, z.name, prices[z.key], periods[z.key])
                        for z in inherited
                    ],
                    None,
                )
            else:
                version_doc = later_version_doc(valid_from, prices, periods, inherited)
        new_doc = replace_version(doc, editing, version_doc)
        errors, detail = self._validate(new_doc, subentry, applied, self._compare())
        if errors:
            return errors, self._placeholders(detail=detail), None
        return {}, {}, self._store(subentry, new_doc, applied=applied)

    @staticmethod
    def _inherited_zones(
        versions: Sequence[Any], valid_from: str, editing: str | None
    ) -> Sequence[Zone]:
        """The zones in force on the day before ``valid_from`` (not the edited one)."""
        candidates = [
            v
            for v in versions
            if v.valid_from.isoformat() < valid_from
            and v.valid_from.isoformat() != editing
        ]
        return candidates[-1].zones

    # ---- edit or delete a version ----------------------------------

    async def async_step_select_version(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Choose the version to edit or delete."""
        _, tariff = self._reconfigure_context()
        dates = [v.valid_from.isoformat() for v in reversed(tariff.versions)]
        if user_input is not None and user_input[CONF_VERSION] in dates:
            self._selected = user_input[CONF_VERSION]
            if self._selected == dates[-1]:
                return await self.async_step_edit_first_version()
            return await self.async_step_edit_version()
        schema = vol.Schema(
            {
                vol.Required(CONF_VERSION): SelectSelector(
                    SelectSelectorConfig(options=dates, mode=SelectSelectorMode.LIST)
                )
            }
        )
        return self.async_show_form(
            step_id="select_version",
            data_schema=schema,
            description_placeholders=self._tariff_placeholders(tariff),
        )

    async def async_step_edit_first_version(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Edit or delete the first version (zone keys never change)."""
        subentry, tariff = self._reconfigure_context()
        first = tariff.versions[0]
        template = [_zone_form_from_zone(zone) for zone in first.zones]
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}
        if user_input is not None:
            errors, placeholders, result = self._save_first_version(
                subentry, tariff, user_input
            )
            if result is not None:
                return result
        suggestion: Mapping[str, Any]
        if user_input is not None:
            suggestion = user_input
        else:
            suggestion = {
                CONF_VALID_FROM: first.valid_from.isoformat(),
                **self._zone_suggestions(template, with_key=False),
            }
        return self._first_version_form(
            "edit_first_version",
            template,
            suggestion,
            errors,
            {**self._tariff_placeholders(tariff), **placeholders},
            with_key=False,
            with_delete=True,
        )

    def _save_first_version(
        self,
        subentry: ConfigSubentry,
        tariff: Tariff,
        user_input: Mapping[str, Any],
    ) -> tuple[dict[str, str], dict[str, str], SubentryFlowResult | None]:
        doc = dict(subentry.data)
        old = tariff.versions[0].valid_from.isoformat()
        applied = self._applied()
        if user_input.get(CONF_DELETE):
            if len(tariff.versions) == 1:
                return {CONF_DELETE: "last_version"}, {}, None
            new_doc = delete_version(doc, old)
            moved = self._move_applied(
                applied, tariff.id, old, str(new_doc["versions"][0]["valid_from"])
            )
            if moved is None:
                return {CONF_DELETE: "applied_order"}, {}, None
        else:
            keys = [zone.key for zone in tariff.versions[0].zones]
            zones, errors, uncovered = self._read_zones(user_input, len(keys), keys)
            valid_from = str(user_input[CONF_VALID_FROM])
            if not errors and valid_from in {
                v.valid_from.isoformat() for v in tariff.versions[1:]
            }:
                errors[CONF_VALID_FROM] = "valid_from_taken"
            if errors:
                return errors, {"hours": uncovered}, None
            version_doc = first_version_doc(
                valid_from, zones, doc["versions"][0].get("preset")
            )
            new_doc = replace_version(doc, old, version_doc)
            moved = self._move_applied(applied, tariff.id, old, valid_from)
            if moved is None:
                return {CONF_VALID_FROM: "applied_order"}, {}, None
        errors, detail = self._validate(new_doc, subentry, moved, self._compare())
        if errors:
            if user_input.get(CONF_DELETE) and CONF_VALID_FROM in errors:
                errors = {CONF_DELETE: errors[CONF_VALID_FROM]}
            return errors, {"detail": detail}, None
        return {}, {}, self._store(subentry, new_doc, applied=moved)

    # ---- rename ----------------------------------------------------

    async def async_step_rename(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Change the display name and the id; references to the id follow."""
        subentry, tariff = self._reconfigure_context()
        errors: dict[str, str] = {}
        if user_input is not None:
            name = str(user_input[CONF_TARIFF_NAME]).strip()
            new_id = str(user_input[CONF_TARIFF_ID]).strip()
            taken = {
                str(s.unique_id) for s in self._tariff_subentries() if s is not subentry
            }
            if not name:
                errors[CONF_TARIFF_NAME] = "blank_name"
            if _ID_RE.fullmatch(new_id) is None:
                errors[CONF_TARIFF_ID] = "invalid_id"
            elif new_id in taken:
                errors[CONF_TARIFF_ID] = "id_taken"
            if not errors:
                doc = {**dict(subentry.data), "id": new_id, "name": name}
                applied_pairs, compare = rename_references(
                    [(str(i["from"]), str(i["tariff"])) for i in self._applied()],
                    self._compare(),
                    tariff.id,
                    new_id,
                )
                applied = [{"from": s, "tariff": t} for s, t in applied_pairs]
                compare_list = None if compare is None else list(compare)
                errors, _ = self._validate(doc, subentry, applied, compare_list)
                if not errors:
                    return self._store(
                        subentry, doc, applied=applied, compare=compare_list
                    )
        suggestion = (
            user_input
            if user_input is not None
            else {CONF_TARIFF_NAME: tariff.name, CONF_TARIFF_ID: tariff.id}
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_TARIFF_NAME): _text(),
                vol.Required(CONF_TARIFF_ID): _text(),
            }
        )
        return self.async_show_form(
            step_id="rename",
            data_schema=self.add_suggested_values_to_schema(schema, suggestion),
            errors=errors,
            description_placeholders=self._tariff_placeholders(tariff),
        )


class _FieldError(Exception):
    """A form field that failed to parse; ``code`` is the translated error key."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _parse_price(value: Any) -> Decimal:
    try:
        return parse_price(str(value))
    except TariffValidationError as err:
        raise _FieldError("invalid_price") from err


def _parse_hours(value: Any) -> tuple[Period, ...]:
    try:
        return parse_periods(str(value))
    except TariffValidationError as err:
        raise _FieldError("invalid_hours") from err
