"""YAML mode: import into the entry, reload action, repairs, read-only UI (task 021)."""

import copy
import json
import logging
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any
from unittest.mock import patch

import pytest
from homeassistant.config_entries import (
    SOURCE_IMPORT,
    ConfigEntry,
    ConfigEntryState,
    ConfigSubentry,
    ConfigSubentryData,
)
from homeassistant.core import Context, HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError, Unauthorized
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from homeassistant.util.yaml import parse_yaml
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_cost_stats.const import (
    DEFAULT_TITLE,
    DOMAIN,
    SCHEMA_URL,
)
from custom_components.energy_cost_stats.yaml_config import document_from_yaml

SENSORS = {"mode": "filter", "include": "all", "exclude": {}, "overrides": {}}


def _tariff(tariff_id: str, name: str, price: str = "7.40") -> dict[str, Any]:
    return {
        "id": tariff_id,
        "name": name,
        "versions": [
            {
                "valid_from": "2026-01-01",
                "preset": "single_rate",
                "prices": {"t0": price},
            }
        ],
    }


BLOCK: dict[str, Any] = {
    "time_zone": "Europe/Berlin",
    "spike_limit": "5",
    "sensors": SENSORS,
    "tariffs": [_tariff("main", "Main"), _tariff("other", "Other", "9.00")],
    "applied": [{"from": "2026-01-01", "tariff": "main"}],
}
UI_OPTIONS: dict[str, Any] = {
    "time_zone": "Asia/Tokyo",
    "spike_limit": "4",
    "sensors": SENSORS,
    "applied": [{"from": "2026-01-01", "tariff": "old"}],
}
INVALID: dict[str, Any] = {"unknown_key": 1}


def _entry_for(hass: HomeAssistant) -> ConfigEntry:
    (entry,) = hass.config_entries.async_entries(DOMAIN)
    return entry


def _tariffs_of(entry: ConfigEntry) -> dict[str, dict[str, Any]]:
    return {
        str(s.unique_id): json.loads(json.dumps(dict(s.data)))
        for s in entry.subentries.values()
    }


async def _setup_yaml(hass: HomeAssistant, block: Any) -> bool:
    result = await async_setup_component(hass, DOMAIN, {DOMAIN: block})
    await hass.async_block_till_done()
    return result


async def _add_ui_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEFAULT_TITLE,
        data={},
        options=copy.deepcopy(UI_OPTIONS),
        version=3,
        subentries_data=[
            ConfigSubentryData(
                data=_tariff("old", "Old"),
                subentry_type="tariff",
                title="Old",
                unique_id="old",
            ),
            ConfigSubentryData(
                data=_tariff("main", "Main", "1.00"),
                subentry_type="tariff",
                title="Main",
                unique_id="main",
            ),
        ],
    )
    entry.add_to_hass(hass)
    return entry


async def _reload(hass: HomeAssistant, block: Any, **kwargs: Any) -> None:
    config = {DOMAIN: block} if block is not None else {}
    with patch(
        "homeassistant.config.async_hass_config_yaml", return_value=config, **kwargs
    ):
        await hass.services.async_call(DOMAIN, "reload", blocking=True)
    await hass.async_block_till_done()


def _issue_error(hass: HomeAssistant) -> str:
    issue = _issue(hass)
    assert issue is not None
    assert issue.translation_placeholders is not None
    return issue.translation_placeholders["error"]


def _issue(hass: HomeAssistant) -> ir.IssueEntry | None:
    return ir.async_get(hass).async_get_issue(DOMAIN, "invalid_yaml")


async def _open(hass: HomeAssistant, entry: ConfigEntry, *path: str) -> dict[str, Any]:
    result: dict[str, Any] = dict(
        await hass.config_entries.options.async_init(entry.entry_id)
    )
    for choice in path:
        assert result["type"] is FlowResultType.MENU
        result = dict(
            await hass.config_entries.options.async_configure(
                result["flow_id"], {"next_step_id": choice}
            )
        )
    return result


async def test_yaml_creates_entry(hass: HomeAssistant):
    assert await _setup_yaml(hass, BLOCK)
    entry = _entry_for(hass)
    assert entry.state is ConfigEntryState.LOADED
    assert entry.source == SOURCE_IMPORT
    assert (entry.version, entry.minor_version) == (3, 1)
    assert (
        dict(entry.options)
        == document_from_yaml(BLOCK, default_time_zone="x", default_sensors={}).options
    )
    assert _tariffs_of(entry) == {t["id"]: t for t in BLOCK["tariffs"]}
    assert {s.title for s in entry.subentries.values()} == {"Main", "Other"}
    assert _issue(hass) is None
    report = await hass.services.async_call(
        DOMAIN,
        "get_report",
        {"start": "2026-01-15", "end": "2026-01-16", "grouping": "day"},
        blocking=True,
        return_response=True,
    )
    assert report is not None
    assert report["time_zone"] == "Europe/Berlin"


async def test_yaml_replaces_ui_config(hass: HomeAssistant, caplog):
    entry = await _add_ui_entry(hass)
    caplog.set_level(logging.WARNING)
    assert await _setup_yaml(hass, BLOCK)
    assert entry.state is ConfigEntryState.LOADED
    assert entry.options["time_zone"] == "Europe/Berlin"
    assert entry.options["applied"] == [{"from": "2026-01-01", "tariff": "main"}]
    assert _tariffs_of(entry) == {t["id"]: t for t in BLOCK["tariffs"]}
    assert "replaces the configuration made in the UI" in caplog.text


async def test_time_zone_default_keeps_stored(hass: HomeAssistant):
    block = {k: v for k, v in BLOCK.items() if k != "time_zone"}
    entry = await _add_ui_entry(hass)
    assert await _setup_yaml(hass, block)
    assert entry.options["time_zone"] == "Asia/Tokyo"
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    await _reload(hass, block)
    assert _entry_for(hass).options["time_zone"] == hass.config.time_zone


async def test_invalid_yaml_at_startup_keeps_last_config(hass: HomeAssistant, caplog):
    entry = await _add_ui_entry(hass)
    assert await _setup_yaml(hass, INVALID)
    assert entry.state is ConfigEntryState.LOADED
    assert dict(entry.options) == UI_OPTIONS
    assert "unknown_key" in _issue_error(hass)
    assert "unknown_key" in caplog.text


@pytest.mark.parametrize("block", [INVALID, ["a"], "text"])
async def test_invalid_yaml_without_entry(hass: HomeAssistant, block):
    assert await _setup_yaml(hass, block)
    assert hass.config_entries.async_entries(DOMAIN) == []
    assert _issue(hass) is not None
    result = dict(
        await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "yaml_mode"


async def test_unknown_time_zone_is_reported(hass: HomeAssistant):
    entry = await _add_ui_entry(hass)
    assert await _setup_yaml(hass, {**BLOCK, "time_zone": "Mars/Base"})
    assert dict(entry.options) == UI_OPTIONS
    assert "Mars/Base" in _issue_error(hass)


async def test_reload_applies_changes(hass: HomeAssistant):
    assert await _setup_yaml(hass, BLOCK)
    entry = _entry_for(hass)
    changed = copy.deepcopy(BLOCK)
    changed["tariffs"][0]["versions"][0]["prices"]["t0"] = "8.50"
    del changed["tariffs"][1]
    changed["tariffs"].append(_tariff("third", "Third", "3"))
    await _reload(hass, changed)
    assert entry.state is ConfigEntryState.LOADED
    assert set(_tariffs_of(entry)) == {"main", "third"}
    assert _tariffs_of(entry)["main"]["versions"][0]["prices"]["t0"] == "8.50"
    assert entry.runtime_data.tariffs.tariff("main").versions[0].zones[0].price == 8.5
    assert _issue(hass) is None


async def test_reload_invalid_raises_and_keeps_running(hass: HomeAssistant):
    assert await _setup_yaml(hass, BLOCK)
    entry = _entry_for(hass)
    before = dict(entry.options)
    with pytest.raises(HomeAssistantError) as err:
        await _reload(hass, INVALID)
    assert err.value.translation_key == "yaml_invalid"
    assert _issue(hass) is not None
    assert dict(entry.options) == before
    assert entry.state is ConfigEntryState.LOADED
    await _reload(hass, BLOCK)
    assert _issue(hass) is None


async def test_reload_syntax_error(hass: HomeAssistant):
    assert await _setup_yaml(hass, BLOCK)
    with (
        patch(
            "homeassistant.config.async_hass_config_yaml",
            side_effect=HomeAssistantError("bad yaml"),
        ),
        pytest.raises(HomeAssistantError) as err,
    ):
        await hass.services.async_call(DOMAIN, "reload", blocking=True)
    assert err.value.translation_key == "yaml_invalid"
    assert "bad yaml" in _issue_error(hass)


async def test_reload_block_added_and_removed(hass: HomeAssistant):
    entry = await _add_ui_entry(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    result = await _open(hass, entry)
    assert result["step_id"] == "init"
    hass.config_entries.options.async_abort(result["flow_id"])

    await _reload(hass, BLOCK)
    assert entry.options["time_zone"] == "Europe/Berlin"
    assert set(_tariffs_of(entry)) == {"main", "other"}
    assert (await _open(hass, entry))["step_id"] == "yaml_mode"

    await _reload(hass, None)
    assert _issue(hass) is None
    assert entry.state is ConfigEntryState.LOADED
    assert entry.options["time_zone"] == "Europe/Berlin"
    assert (await _open(hass, entry))["step_id"] == "init"


async def test_reload_creates_entry_when_missing(hass: HomeAssistant):
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    assert hass.config_entries.async_entries(DOMAIN) == []
    await _reload(hass, BLOCK)
    assert _entry_for(hass).state is ConfigEntryState.LOADED


async def test_reload_is_admin_only(hass: HomeAssistant, hass_read_only_user):
    assert await async_setup_component(hass, DOMAIN, {})
    with pytest.raises(Unauthorized):
        await hass.services.async_call(
            DOMAIN,
            "reload",
            blocking=True,
            context=Context(user_id=hass_read_only_user.id),
        )


async def test_deleted_subentry_restored(hass: HomeAssistant):
    assert await _setup_yaml(hass, BLOCK)
    entry = _entry_for(hass)
    gone = next(s for s in entry.subentries.values() if s.unique_id == "main")
    hass.config_entries.async_remove_subentry(entry, gone.subentry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert set(_tariffs_of(entry)) == {"main", "other"}
    assert entry.options["applied"] == [{"from": "2026-01-01", "tariff": "main"}]


async def test_options_read_only_in_yaml_mode(hass: HomeAssistant):
    assert await _setup_yaml(hass, {**BLOCK, "compare": ["other"]})
    entry = _entry_for(hass)
    before = dict(entry.options)
    result = await _open(hass, entry)
    assert result["step_id"] == "yaml_mode"
    assert result["menu_options"] == ["sensors_view", "applied_view", "export_yaml"]
    placeholders = result["description_placeholders"]
    assert placeholders["time_zone"] == "Europe/Berlin"
    assert placeholders["spike_limit"] == "5"
    assert placeholders["compare"] == "Other"
    assert placeholders["error"] == ""

    sensors = await _open(hass, entry, "sensors_view")
    assert sensors["step_id"] == "sensors_view"
    assert sensors["menu_options"] == ["yaml_mode"]
    assert set(sensors["description_placeholders"]) == {"count", "sensors"}

    applied = await _open(hass, entry, "applied_view")
    assert "2026-01-01" in applied["description_placeholders"]["history"]
    assert "Main" in applied["description_placeholders"]["history"]
    back = dict(
        await hass.config_entries.options.async_configure(
            applied["flow_id"], {"next_step_id": "yaml_mode"}
        )
    )
    assert back["step_id"] == "yaml_mode"
    assert dict(entry.options) == before

    with pytest.raises(HomeAssistantError):
        await _reload(hass, INVALID)
    shown = await _open(hass, entry)
    assert "unknown_key" in shown["description_placeholders"]["error"]
    assert dict(entry.options) == before


async def test_tariff_subentry_flows_abort_in_yaml_mode(hass: HomeAssistant):
    assert await _setup_yaml(hass, BLOCK)
    entry = _entry_for(hass)
    result = dict(
        await hass.config_entries.subentries.async_init(
            (entry.entry_id, "tariff"), context={"source": "user"}
        )
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "yaml_mode"
    subentry = next(iter(entry.subentries.values()))
    result = dict(
        await hass.config_entries.subentries.async_init(
            (entry.entry_id, "tariff"),
            context={"source": "reconfigure", "subentry_id": subentry.subentry_id},
        )
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "yaml_mode"


async def test_tariff_subentry_flows_start_in_ui_mode(hass: HomeAssistant):
    entry = await _add_ui_entry(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    result = dict(
        await hass.config_entries.subentries.async_init(
            (entry.entry_id, "tariff"), context={"source": "user"}
        )
    )
    assert result["type"] is FlowResultType.FORM
    subentry = next(iter(entry.subentries.values()))
    result = dict(
        await hass.config_entries.subentries.async_init(
            (entry.entry_id, "tariff"),
            context={"source": "reconfigure", "subentry_id": subentry.subentry_id},
        )
    )
    assert result["type"] is FlowResultType.MENU


def _round_trip(text_result: Mapping[str, Any]) -> Any:
    text = text_result["description_placeholders"]["yaml"]
    assert text.startswith("energy_cost_stats:\n")
    parsed: Any = parse_yaml(text)
    return parsed[DOMAIN]


async def test_export_yaml_step(hass: HomeAssistant):
    entry = await _add_ui_entry(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    init = await _open(hass, entry)
    assert init["menu_options"][-1] == "export_yaml"
    exported = await _open(hass, entry, "export_yaml")
    assert exported["description_placeholders"]["schema_url"] == SCHEMA_URL
    document = document_from_yaml(
        _round_trip(exported), default_time_zone="x", default_sensors={}
    )
    assert document.options == UI_OPTIONS
    assert [t["id"] for t in document.tariffs] == ["old", "main"]
    back = dict(
        await hass.config_entries.options.async_configure(
            exported["flow_id"], {"next_step_id": "init"}
        )
    )
    assert back["step_id"] == "init"


async def test_export_yaml_from_yaml_mode(hass: HomeAssistant):
    assert await _setup_yaml(hass, BLOCK)
    entry = _entry_for(hass)
    exported = await _open(hass, entry, "export_yaml")
    document = document_from_yaml(
        _round_trip(exported), default_time_zone="x", default_sensors={}
    )
    assert document.options == dict(entry.options)
    assert list(document.tariffs) == BLOCK["tariffs"]
    back = dict(
        await hass.config_entries.options.async_configure(
            exported["flow_id"], {"next_step_id": "init"}
        )
    )
    assert back["step_id"] == "yaml_mode"


async def test_warning_when_yaml_replaces_ui_edits_after_import(
    hass: HomeAssistant, caplog
):
    caplog.set_level(logging.WARNING)
    assert await _setup_yaml(hass, BLOCK)
    entry = _entry_for(hass)
    assert "replaces the configuration" not in caplog.text

    await _reload(hass, None)
    # Edit in the UI: change an option and add a tariff.
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, "spike_limit": "9"}
    )
    hass.config_entries.async_add_subentry(
        entry,
        ConfigSubentry(
            data=MappingProxyType(_tariff("ui_added", "UI added")),
            subentry_type="tariff",
            title="UI added",
            unique_id="ui_added",
        ),
    )
    await hass.async_block_till_done()
    await _reload(hass, BLOCK)
    assert "replaces the configuration made in the UI" in caplog.text
    assert entry.options["spike_limit"] == "5"
    assert set(_tariffs_of(entry)) == {"main", "other"}


async def test_invalid_block_and_deleted_subentry_does_not_fail_setup(
    hass: HomeAssistant,
):
    assert await _setup_yaml(hass, BLOCK)
    entry = _entry_for(hass)
    with pytest.raises(HomeAssistantError):
        await _reload(hass, INVALID)
    gone = next(s for s in entry.subentries.values() if s.unique_id == "main")
    hass.config_entries.async_remove_subentry(entry, gone.subentry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert "applied" not in entry.options or all(
        item["tariff"] != "main" for item in entry.options["applied"]
    )
    await _reload(hass, BLOCK)
    assert set(_tariffs_of(entry)) == {"main", "other"}
    assert entry.options["applied"] == [{"from": "2026-01-01", "tariff": "main"}]
    assert entry.state is ConfigEntryState.LOADED
