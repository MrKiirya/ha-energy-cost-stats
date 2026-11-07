"""Sidebar panel: registered through the entry lifecycle (task 023)."""

import copy
import logging
from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.frontend import DATA_PANELS
from homeassistant.config_entries import ConfigEntryState, ConfigSubentryData
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_cost_stats.const import (
    DEFAULT_TITLE,
    DOMAIN,
    PANEL_ELEMENT,
    PANEL_URL_PATH,
)

PANEL = {"show": True, "title": "Energy cost", "icon": "mdi:cash-multiple"}
TARIFF = {
    "id": "main",
    "name": "Main",
    "versions": [
        {"valid_from": "2026-01-01", "preset": "single_rate", "prices": {"t0": "7.40"}}
    ],
}
OPTIONS: dict[str, Any] = {
    "time_zone": "Europe/Berlin",
    "spike_limit": "4",
    "sensors": {"mode": "filter", "include": "all", "exclude": {}, "overrides": {}},
    "applied": [{"from": "2026-01-01", "tariff": "main"}],
}


@pytest.fixture
def add_url(hass: HomeAssistant) -> Iterator[MagicMock]:
    """Frontend marked as loaded (its package is not installed in the tests)."""
    hass.config.components.add("frontend")
    hass.data[DATA_PANELS] = {}
    with patch(
        "custom_components.energy_cost_stats.frontend.add_extra_js_url"
    ) as patched:
        yield patched


def _entry(hass: HomeAssistant, panel: dict[str, Any] | None) -> MockConfigEntry:
    options = copy.deepcopy(OPTIONS)
    if panel is not None:
        options["panel"] = panel
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEFAULT_TITLE,
        data={},
        options=options,
        version=3,
        subentries_data=[
            ConfigSubentryData(
                data=TARIFF, subentry_type="tariff", title="Main", unique_id="main"
            )
        ],
    )
    entry.add_to_hass(hass)
    return entry


async def _load(hass: HomeAssistant, panel: dict[str, Any] | None) -> MockConfigEntry:
    entry = _entry(hass, panel)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    return entry


def _panels(hass: HomeAssistant) -> dict[str, Any]:
    return hass.data[DATA_PANELS]


async def _save_general(
    hass: HomeAssistant, entry: MockConfigEntry, sidebar: dict[str, Any]
) -> None:
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "general"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "time_zone": "Europe/Berlin",
            "spike_check": True,
            "spike_limit": 4,
            "sidebar": sidebar,
        },
    )
    assert result.get("type") is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()


async def test_panel_registered_when_shown(hass: HomeAssistant, add_url: MagicMock):
    await _load(hass, PANEL)
    panel = _panels(hass)[PANEL_URL_PATH]
    assert panel.component_name == "custom"
    assert panel.sidebar_title == "Energy cost"
    assert panel.sidebar_icon == "mdi:cash-multiple"
    assert panel.require_admin is False
    custom = panel.config["_panel_custom"]
    assert custom["name"] == PANEL_ELEMENT == "energy-cost-stats-panel"
    assert custom["embed_iframe"] is False
    add_url.assert_called_once()
    assert custom["module_url"] == add_url.call_args.args[1]


@pytest.mark.parametrize("panel", [{**PANEL, "show": False}, None])
async def test_no_panel_when_hidden_or_unset(
    hass: HomeAssistant, add_url: MagicMock, panel: dict[str, Any] | None
):
    await _load(hass, panel)
    assert PANEL_URL_PATH not in _panels(hass)


async def test_no_panel_without_frontend(hass: HomeAssistant, caplog):
    caplog.set_level(logging.WARNING)
    entry = await _load(hass, PANEL)
    assert entry.state is ConfigEntryState.LOADED
    assert DATA_PANELS not in hass.data or PANEL_URL_PATH not in _panels(hass)
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]


async def test_options_change_updates_panel_live(
    hass: HomeAssistant, add_url: MagicMock
):
    entry = await _load(hass, None)
    assert PANEL_URL_PATH not in _panels(hass)

    await _save_general(hass, entry, PANEL)
    assert _panels(hass)[PANEL_URL_PATH].sidebar_title == "Energy cost"

    await _save_general(hass, entry, {**PANEL, "title": "Costs", "icon": "mdi:flash"})
    panel = _panels(hass)[PANEL_URL_PATH]
    assert (panel.sidebar_title, panel.sidebar_icon) == ("Costs", "mdi:flash")
    assert [p for p in _panels(hass).values() if p.component_name == "custom"] == [
        panel
    ]

    await _save_general(hass, entry, {**PANEL, "show": False})
    assert PANEL_URL_PATH not in _panels(hass)
    assert entry.state is ConfigEntryState.LOADED


async def test_unload_and_remove_drop_panel(
    hass: HomeAssistant, add_url: MagicMock, caplog
):
    caplog.set_level(logging.WARNING)
    entry = await _load(hass, PANEL)
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert PANEL_URL_PATH not in _panels(hass)

    # Panel already gone when the entry is removed: removal must stay silent.
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert PANEL_URL_PATH in _panels(hass)
    _panels(hass).pop(PANEL_URL_PATH)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert PANEL_URL_PATH not in _panels(hass)
    assert "unknown panel" not in caplog.text.lower()


async def test_path_conflict_is_not_fatal(
    hass: HomeAssistant, add_url: MagicMock, caplog
):
    caplog.set_level(logging.WARNING)
    foreign = MagicMock()
    _panels(hass)[PANEL_URL_PATH] = foreign
    entry = await _load(hass, PANEL)
    assert entry.state is ConfigEntryState.LOADED
    assert any(
        r.levelno == logging.WARNING
        and r.name == "custom_components.energy_cost_stats.panel"
        and "Cannot add the sidebar panel" in r.getMessage()
        for r in caplog.records
    )
    assert _panels(hass)[PANEL_URL_PATH] is foreign

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert _panels(hass)[PANEL_URL_PATH] is foreign


async def test_yaml_mode_panel(hass: HomeAssistant, add_url: MagicMock):
    block = {
        **OPTIONS,
        "tariffs": [TARIFF],
        "panel": {**PANEL, "title": "Costs", "icon": "mdi:flash"},
    }

    async def reload(content: dict[str, Any]) -> None:
        with patch(
            "homeassistant.config.async_hass_config_yaml",
            return_value={DOMAIN: content},
        ):
            await hass.services.async_call(DOMAIN, "reload", blocking=True)
        await hass.async_block_till_done()

    assert await async_setup_component(hass, DOMAIN, {DOMAIN: block})
    await hass.async_block_till_done()
    panel = _panels(hass)[PANEL_URL_PATH]
    assert (panel.sidebar_title, panel.sidebar_icon) == ("Costs", "mdi:flash")

    await reload({**block, "panel": {**block["panel"], "show": False}})
    assert PANEL_URL_PATH not in _panels(hass)

    await reload(block)
    assert PANEL_URL_PATH in _panels(hass)


async def test_card_extra_module_registered_once(
    hass: HomeAssistant, add_url: MagicMock
):
    entry = await _load(hass, PANEL)
    await _save_general(hass, entry, {**PANEL, "title": "Costs"})
    add_url.assert_called_once()
    panel = _panels(hass)[PANEL_URL_PATH]
    assert panel.config["_panel_custom"]["module_url"] == add_url.call_args.args[1]
