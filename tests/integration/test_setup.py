"""Integration smoke test: the integration loads through async_setup_component."""

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.energy_cost_stats.const import DOMAIN


async def test_async_setup(hass: HomeAssistant):
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    assert DOMAIN in hass.config.components
    assert "recorder" in hass.config.components
    assert not any(DOMAIN in state.entity_id for state in hass.states.async_all())
