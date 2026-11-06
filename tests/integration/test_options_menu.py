"""Options flow menu: sensors, applied history, comparison, general (task 019)."""

import json
from collections.abc import Awaitable, Callable
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState, ConfigSubentryData
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_cost_stats.const import DEFAULT_TITLE, DOMAIN

PLUG_01 = "sensor.plug_01"
COMPONENT = Path(__file__).parents[2] / "custom_components" / "energy_cost_stats"


def _tariff(
    tariff_id: str, name: str, valid_from: str = "2026-01-01"
) -> dict[str, Any]:
    return {
        "id": tariff_id,
        "name": name,
        "versions": [
            {
                "valid_from": valid_from,
                "preset": "single_rate",
                "prices": {"t0": "7.40"},
            }
        ],
    }


TARIFFS = [
    _tariff("main", "Main"),
    _tariff("other", "Other | Plan"),
    _tariff("late", "Late", "2026-06-01"),
]
BASE_OPTIONS: dict[str, Any] = {
    "time_zone": "Europe/Berlin",
    "spike_limit": "4",
    "sensors": {
        "mode": "filter",
        "include": {"entity_id": [PLUG_01]},
        "exclude": {},
        "overrides": {PLUG_01: {"spike_limit": "10"}},
    },
    "applied": [{"from": "2026-01-01", "tariff": "main"}],
}


async def _call(func: Callable[..., Awaitable[Any]], *args: Any) -> dict[str, Any]:
    return dict(await func(*args))


async def _add_entry(
    hass: HomeAssistant,
    options: dict[str, Any] | None = None,
    tariffs: list[dict[str, Any]] | None = None,
    *,
    loads: bool = True,
) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEFAULT_TITLE,
        data={},
        options=dict(BASE_OPTIONS if options is None else options),
        version=3,
        subentries_data=[
            ConfigSubentryData(
                data=data,
                subentry_type="tariff",
                title=data["name"],
                unique_id=data["id"],
            )
            for data in (TARIFFS if tariffs is None else tariffs)
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id) is loads
    await hass.async_block_till_done()
    return entry


async def _open(
    hass: HomeAssistant, entry: MockConfigEntry, *path: str
) -> dict[str, Any]:
    """Start the options flow and follow menu choices."""
    result = await _call(hass.config_entries.options.async_init, entry.entry_id)
    for choice in path:
        assert result["type"] is FlowResultType.MENU
        result = await _call(
            hass.config_entries.options.async_configure,
            result["flow_id"],
            {"next_step_id": choice},
        )
    return result


async def _submit(
    hass: HomeAssistant, result: dict[str, Any], user_input: dict[str, Any]
) -> dict[str, Any]:
    return await _call(
        hass.config_entries.options.async_configure, result["flow_id"], user_input
    )


def _markers(schema: vol.Schema) -> dict[str, Any]:
    return {str(key): key for key in schema.schema}


def _suggested(schema: vol.Schema) -> dict[str, Any]:
    found: dict[str, Any] = {}
    for key, value in schema.schema.items():
        if hasattr(value, "schema") and isinstance(value.schema, vol.Schema):
            found[str(key)] = _suggested(value.schema)
        elif key.description and "suggested_value" in key.description:
            found[str(key)] = key.description["suggested_value"]
    return found


def _select_values(schema: vol.Schema, name: str) -> list[str]:
    selector = schema.schema[_markers(schema)[name]]
    return [option["value"] for option in selector.config["options"]]


async def _applied_pick(hass: HomeAssistant, entry: MockConfigEntry, from_: str):
    result = await _open(hass, entry, "applied", "applied_pick")
    return await _submit(hass, result, {"change": from_})


TWO_CHANGES = [
    {"from": "2026-01-01", "tariff": "main"},
    {"from": "2026-03-01", "tariff": "other"},
]


async def test_init_is_menu(hass: HomeAssistant):
    entry = await _add_entry(hass)
    result = await _open(hass, entry)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"
    assert result["menu_options"] == ["sensors", "applied", "compare", "general"]


async def test_general_saves_and_keeps_other_options(hass: HomeAssistant):
    entry = await _add_entry(
        hass, {**BASE_OPTIONS, "applied": TWO_CHANGES, "compare": ["late"]}
    )
    result = await _open(hass, entry, "general")
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "general"
    result = await _submit(
        hass,
        result,
        {"time_zone": "UTC", "spike_check": True, "spike_limit": 6, "sidebar": {}},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["time_zone"] == "UTC"
    assert entry.options["spike_limit"] == "6"
    assert entry.options["sensors"] == BASE_OPTIONS["sensors"]
    assert entry.options["applied"] == TWO_CHANGES
    assert entry.options["compare"] == ["late"]
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.settings.time_zone == "UTC"


async def test_general_prefills_current_values(hass: HomeAssistant):
    entry = await _add_entry(hass)
    result = await _open(hass, entry, "general")
    suggested = _suggested(result["data_schema"])
    assert suggested["time_zone"] == "Europe/Berlin"
    assert suggested["spike_check"] is True
    assert suggested["spike_limit"] == 4
    assert suggested["sidebar"] == {
        "show": False,
        "title": "Energy cost",
        "icon": "mdi:cash-multiple",
    }

    panel = {"show": True, "title": "Costs", "icon": "mdi:flash"}
    entry2 = await _add_entry(hass, {**BASE_OPTIONS, "panel": panel})
    result = await _open(hass, entry2, "general")
    assert _suggested(result["data_schema"])["sidebar"] == panel


async def test_general_saves_panel(hass: HomeAssistant):
    entry = await _add_entry(hass)
    result = await _open(hass, entry, "general")
    result = await _submit(
        hass,
        result,
        {
            "time_zone": "Europe/Berlin",
            "spike_check": True,
            "spike_limit": 4,
            "sidebar": {"show": True, "title": "Costs", "icon": "mdi:flash"},
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["panel"] == {
        "show": True,
        "title": "Costs",
        "icon": "mdi:flash",
    }
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED


async def test_general_rejects_invalid_limit(hass: HomeAssistant):
    entry = await _add_entry(hass)
    before = dict(entry.options)
    result = await _open(hass, entry, "general")
    result = await _submit(
        hass,
        result,
        {
            "time_zone": "Europe/Berlin",
            "spike_check": True,
            "spike_limit": float("nan"),
            "sidebar": {},
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"spike_limit": "invalid_limit"}
    assert dict(entry.options) == before


async def test_applied_aborts_without_tariffs(hass: HomeAssistant):
    entry = await _add_entry(hass, tariffs=[], options={**BASE_OPTIONS, "applied": []})
    for choice in ("applied", "compare"):
        result = await _open(hass, entry, choice)
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "no_tariffs"


async def test_applied_menu_shows_history(hass: HomeAssistant):
    entry = await _add_entry(hass, {**BASE_OPTIONS, "applied": TWO_CHANGES[::-1]})
    result = await _open(hass, entry, "applied")
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "applied"
    assert result["menu_options"] == ["applied_single", "applied_add", "applied_pick"]
    rows = result["description_placeholders"]["history"].splitlines()
    assert rows == [
        "| 2026-01-01 | Main (`main`) |",
        "| 2026-03-01 | Other \\| Plan (`other`) |",
    ]


async def test_applied_menu_empty_history(hass: HomeAssistant):
    entry = await _add_entry(hass, {**BASE_OPTIONS, "applied": []})
    result = await _open(hass, entry, "applied")
    assert result["menu_options"] == ["applied_single", "applied_add"]
    assert result["description_placeholders"]["history"] == "| — | — |"


async def test_applied_add_change(hass: HomeAssistant):
    entry = await _add_entry(hass)
    result = await _open(hass, entry, "applied", "applied_add")
    assert result["step_id"] == "applied_add"
    result = await _submit(hass, result, {"from": "2026-03-01", "tariff": "other"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["applied"] == TWO_CHANGES
    assert entry.options["sensors"] == BASE_OPTIONS["sensors"]
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    schedule = entry.runtime_data.schedule
    assert schedule.plan_for(date(2026, 2, 1)).name == "Main"
    assert schedule.plan_for(date(2026, 3, 2)).name == "Other | Plan"


async def test_applied_add_duplicate_date(hass: HomeAssistant):
    entry = await _add_entry(hass)
    before = dict(entry.options)
    result = await _open(hass, entry, "applied", "applied_add")
    result = await _submit(hass, result, {"from": "2026-01-01", "tariff": "other"})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"from": "duplicate_from"}
    assert dict(entry.options) == before


async def test_applied_add_before_first_version(hass: HomeAssistant):
    entry = await _add_entry(hass)
    before = dict(entry.options)
    result = await _open(hass, entry, "applied", "applied_add")
    result = await _submit(hass, result, {"from": "2026-02-01", "tariff": "late"})
    assert result["errors"] == {"from": "no_version"}
    assert result["description_placeholders"]["first_valid_from"] == "2026-06-01"
    assert dict(entry.options) == before


async def test_applied_single_replaces_history(hass: HomeAssistant):
    entry = await _add_entry(hass, {**BASE_OPTIONS, "applied": TWO_CHANGES})
    result = await _open(hass, entry, "applied", "applied_single")
    assert result["step_id"] == "applied_single"
    assert _suggested(result["data_schema"]) == {"tariff": "other"}
    assert _select_values(result["data_schema"], "tariff") == ["main", "other", "late"]
    result = await _submit(hass, result, {"tariff": "late"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["applied"] == [{"from": "2026-06-01", "tariff": "late"}]
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED


async def test_applied_single_explicit_date(hass: HomeAssistant):
    entry = await _add_entry(hass, {**BASE_OPTIONS, "applied": TWO_CHANGES})
    result = await _open(hass, entry, "applied", "applied_single")
    result = await _submit(hass, result, {"tariff": "other", "from": "2026-02-10"})
    assert entry.options["applied"] == [{"from": "2026-02-10", "tariff": "other"}]


async def test_applied_pick_lists_changes(hass: HomeAssistant):
    entry = await _add_entry(hass, {**BASE_OPTIONS, "applied": TWO_CHANGES})
    result = await _open(hass, entry, "applied", "applied_pick")
    assert result["step_id"] == "applied_pick"
    selector = result["data_schema"].schema[_markers(result["data_schema"])["change"]]
    assert [o["label"] for o in selector.config["options"]] == [
        "2026-01-01 · Main",
        "2026-03-01 · Other | Plan",
    ]
    result = await _submit(hass, result, {"change": "2026-03-01"})
    assert result["step_id"] == "applied_change"
    suggested = _suggested(result["data_schema"])
    assert suggested["from"] == "2026-03-01"
    assert suggested["tariff"] == "other"


async def test_applied_change_redate(hass: HomeAssistant):
    entry = await _add_entry(
        hass,
        {
            **BASE_OPTIONS,
            "applied": [*TWO_CHANGES, {"from": "2026-06-01", "tariff": "late"}],
        },
    )
    result = await _applied_pick(hass, entry, "2026-03-01")
    result = await _submit(hass, result, {"from": "2026-07-01", "tariff": "other"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["applied"] == [
        {"from": "2026-01-01", "tariff": "main"},
        {"from": "2026-06-01", "tariff": "late"},
        {"from": "2026-07-01", "tariff": "other"},
    ]


async def test_applied_change_tariff(hass: HomeAssistant):
    entry = await _add_entry(hass, {**BASE_OPTIONS, "applied": TWO_CHANGES})
    result = await _applied_pick(hass, entry, "2026-03-01")
    result = await _submit(hass, result, {"from": "2026-03-01", "tariff": "main"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["applied"][1] == {"from": "2026-03-01", "tariff": "main"}


async def test_applied_change_delete(hass: HomeAssistant):
    entry = await _add_entry(hass, {**BASE_OPTIONS, "applied": TWO_CHANGES})
    result = await _applied_pick(hass, entry, "2026-03-01")
    result = await _submit(
        hass, result, {"from": "2026-03-01", "tariff": "other", "delete": True}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["applied"] == [TWO_CHANGES[0]]
    await hass.async_block_till_done()

    result = await _applied_pick(hass, entry, "2026-01-01")
    await _submit(
        hass, result, {"from": "2026-01-01", "tariff": "main", "delete": True}
    )
    assert "applied" not in entry.options
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.schedule is None


async def test_applied_change_validation_error(hass: HomeAssistant):
    entry = await _add_entry(hass, {**BASE_OPTIONS, "applied": TWO_CHANGES})
    before = dict(entry.options)
    result = await _applied_pick(hass, entry, "2026-03-01")
    result = await _submit(hass, result, {"from": "2026-01-01", "tariff": "other"})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"from": "duplicate_from"}
    assert dict(entry.options) == before


async def test_compare_default_stores_no_key(hass: HomeAssistant):
    entry = await _add_entry(hass, {**BASE_OPTIONS, "compare": ["late"]})
    result = await _open(hass, entry, "compare")
    assert result["step_id"] == "compare"
    result = await _submit(hass, result, {"use_default": True, "tariffs": ["late"]})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert "compare" not in entry.options
    assert entry.options["applied"] == BASE_OPTIONS["applied"]
    await hass.async_block_till_done()
    assert entry.runtime_data.tariffs.compare == ("other", "late")


async def test_compare_explicit_subset_in_tariff_order(hass: HomeAssistant):
    entry = await _add_entry(hass)
    result = await _open(hass, entry, "compare")
    result = await _submit(
        hass, result, {"use_default": False, "tariffs": ["late", "main"]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["compare"] == ["main", "late"]


async def test_compare_empty_list(hass: HomeAssistant):
    entry = await _add_entry(hass)
    result = await _open(hass, entry, "compare")
    result = await _submit(hass, result, {"use_default": False, "tariffs": []})
    assert entry.options["compare"] == []
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.tariffs.compare == ()


async def test_compare_prefill(hass: HomeAssistant):
    entry = await _add_entry(hass)
    result = await _open(hass, entry, "compare")
    suggested = _suggested(result["data_schema"])
    assert suggested == {"use_default": True, "tariffs": ["other", "late"]}
    assert result["description_placeholders"]["default"] == "Other | Plan, Late"

    entry2 = await _add_entry(hass, {**BASE_OPTIONS, "compare": ["main"]})
    result = await _open(hass, entry2, "compare")
    assert _suggested(result["data_schema"]) == {
        "use_default": False,
        "tariffs": ["main"],
    }


async def test_submit_uses_current_options(hass: HomeAssistant):
    entry = await _add_entry(hass)
    result = await _open(hass, entry, "general")
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, "applied": TWO_CHANGES}
    )
    result = await _submit(
        hass,
        result,
        {"time_zone": "UTC", "spike_check": True, "spike_limit": 4, "sidebar": {}},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["applied"] == TWO_CHANGES
    assert entry.options["time_zone"] == "UTC"


async def test_corrupt_options_abort(hass: HomeAssistant):
    entry = await _add_entry(hass)
    good = dict(entry.options)
    for choice in ("sensors", "applied", "compare", "general"):
        menu = await _open(hass, entry)
        hass.config_entries.async_update_entry(
            entry, options={**good, "spike_limit": "abc"}
        )
        await hass.async_block_till_done()
        result = await _call(
            hass.config_entries.options.async_configure,
            menu["flow_id"],
            {"next_step_id": choice},
        )
        assert result["type"] is FlowResultType.ABORT, choice
        assert result["reason"] == "invalid_options"
        hass.config_entries.async_update_entry(entry, options=good)
        await hass.async_block_till_done()


async def test_options_strings_complete(hass: HomeAssistant):
    entry = await _add_entry(hass, {**BASE_OPTIONS, "applied": TWO_CHANGES})
    for path in (
        "strings.json",
        "translations/en.json",
    ):
        options = json.loads((COMPONENT / path).read_text())["options"]
        steps = options["step"]
        for step_id in (
            "init",
            "sensors",
            "sensors_select",
            "sensors_preview",
            "device_limits",
            "general",
            "applied",
            "applied_single",
            "applied_add",
            "applied_pick",
            "applied_change",
            "compare",
        ):
            assert "title" in steps[step_id], (path, step_id)
        assert set(steps["init"]["menu_options"]) == {
            "sensors",
            "applied",
            "compare",
            "general",
        }
        assert set(steps["applied"]["menu_options"]) == {
            "applied_single",
            "applied_add",
            "applied_pick",
        }
        assert set(steps["sensors"]["menu_options"]) == {
            "sensors_select",
            "device_limits",
        }
        assert set(steps["sensors_preview"]["menu_options"]) == {
            "sensors_save",
            "sensors_select",
        }
        select = steps["sensors_select"]
        assert set(select["data"]) == {"mode"}
        assert set(select["sections"]) == {"include", "exclude"}
        assert set(select["sections"]["include"]["data"]) == {
            "all",
            "target",
            "entity_globs",
        }
        assert set(select["sections"]["exclude"]["data"]) == {
            "target",
            "entity_globs",
        }
        selector = json.loads((COMPONENT / path).read_text())["selector"]
        assert set(selector["sensor_mode"]["options"]) == {
            "energy_dashboard",
            "filter",
        }
        for placeholder in ("{count}", "{sensors}"):
            assert placeholder in steps["sensors"]["description"], path
            assert placeholder in steps["sensors_preview"]["description"], path
        assert set(steps["general"]["sections"]) == {"sidebar"}
        assert set(steps["general"]["sections"]["sidebar"]["data"]) == {
            "show",
            "title",
            "icon",
        }
        for error in (
            "no_dashboard_devices",
            "nothing_included",
            "invalid_glob",
            "invalid_target",
            "invalid_limit",
            "duplicate_from",
            "no_version",
            "unknown_tariff",
            "invalid_config",
        ):
            assert error in options["error"], (path, error)
        for abort in ("invalid_options", "no_tariffs", "no_sensors"):
            assert abort in options["abort"], (path, abort)
    # Every form field of every leaf step has a label.
    flows = {
        "general": ("general",),
        "applied_single": ("applied", "applied_single"),
        "applied_add": ("applied", "applied_add"),
        "compare": ("compare",),
    }
    steps = json.loads((COMPONENT / "strings.json").read_text())["options"]["step"]
    for step_id, path in flows.items():
        result = await _open(hass, entry, *path)
        top = [n for n in _markers(result["data_schema"]) if n != "sidebar"]
        for name in top:
            assert name in steps[step_id]["data"], (step_id, name)


BROKEN = {**BASE_OPTIONS, "applied": [{"from": "2025-01-01", "tariff": "main"}]}


async def test_compare_with_invalid_stored_history(hass: HomeAssistant):
    entry = await _add_entry(hass, BROKEN, loads=False)
    assert entry.state is ConfigEntryState.SETUP_ERROR
    result = await _open(hass, entry, "compare")
    assert result["type"] is FlowResultType.FORM
    assert _suggested(result["data_schema"]) == {
        "use_default": True,
        "tariffs": ["other", "late"],
    }


async def test_applied_add_on_invalid_history_reports_base_error(
    hass: HomeAssistant,
):
    entry = await _add_entry(hass, BROKEN, loads=False)
    result = await _open(hass, entry, "applied", "applied_add")
    result = await _submit(hass, result, {"from": "2026-03-01", "tariff": "other"})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_config"}
    assert "no version" in result["description_placeholders"]["detail"]
    assert entry.options["applied"] == BROKEN["applied"]


async def test_applied_single_repairs_invalid_history(hass: HomeAssistant):
    entry = await _add_entry(hass, BROKEN, loads=False)
    result = await _open(hass, entry, "applied", "applied_single")
    result = await _submit(hass, result, {"tariff": "main"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["applied"] == [{"from": "2026-01-01", "tariff": "main"}]


async def test_applied_add_tariff_deleted_while_form_is_open(hass: HomeAssistant):
    entry = await _add_entry(hass)
    result = await _open(hass, entry, "applied", "applied_add")
    subentry = next(
        item for item in entry.subentries.values() if item.unique_id == "other"
    )
    hass.config_entries.async_remove_subentry(entry, subentry.subentry_id)
    await hass.async_block_till_done()
    result = await _submit(hass, result, {"from": "2026-03-01", "tariff": "other"})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"tariff": "unknown_tariff"}


async def test_applied_add_prefills_today_in_configured_zone(hass: HomeAssistant):
    entry = await _add_entry(hass)
    result = await _open(hass, entry, "applied", "applied_add")
    expected = datetime.now(ZoneInfo("Europe/Berlin")).date().isoformat()
    assert _suggested(result["data_schema"])["from"] == expected


async def test_applied_single_tariff_deleted_while_form_is_open(
    hass: HomeAssistant,
):
    entry = await _add_entry(hass)
    result = await _open(hass, entry, "applied", "applied_single")
    subentry = next(
        item for item in entry.subentries.values() if item.unique_id == "other"
    )
    hass.config_entries.async_remove_subentry(entry, subentry.subentry_id)
    await hass.async_block_till_done()
    result = await _submit(hass, result, {"tariff": "other"})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"tariff": "unknown_tariff"}


async def test_compare_submit_on_invalid_history_shows_detail(hass: HomeAssistant):
    entry = await _add_entry(hass, BROKEN, loads=False)
    result = await _open(hass, entry, "compare")
    result = await _submit(hass, result, {"use_default": True, "tariffs": []})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_config"}
    assert "no version" in result["description_placeholders"]["detail"]
