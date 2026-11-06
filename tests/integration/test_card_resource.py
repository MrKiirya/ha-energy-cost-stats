"""The integration serves the card bundle as a frontend module (SPEC §2)."""

from http import HTTPStatus
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.energy_cost_stats.const import CARD_URL, DOMAIN
from custom_components.energy_cost_stats.frontend import CARD_PATH, card_version


async def test_card_bundle_is_served(hass: HomeAssistant, hass_client):
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    client = await hass_client()
    response = await client.get(CARD_URL)
    assert response.status == HTTPStatus.OK
    body = await response.text()
    assert body == CARD_PATH.read_text(encoding="utf-8")
    assert "energy-cost-stats-card" in body


async def test_card_registered_as_extra_module(hass: HomeAssistant):
    """With the frontend loaded, the bundle URL (content-hash versioned) is added.

    The real ``frontend`` integration needs the ``home-assistant-frontend`` package,
    which is not in the lock file, so the frontend is marked as loaded instead.
    """
    hass.config.components.add("frontend")
    with patch(
        "custom_components.energy_cost_stats.frontend.add_extra_js_url"
    ) as add_url:
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()

    expected = f"{CARD_URL}?v={card_version(CARD_PATH.read_bytes())}"
    add_url.assert_called_once_with(hass, expected)


async def test_card_without_frontend(hass: HomeAssistant):
    """Without the frontend integration (a headless setup) setup still succeeds."""
    with patch(
        "custom_components.energy_cost_stats.frontend.add_extra_js_url"
    ) as add_url:
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()
    add_url.assert_not_called()


def test_card_version_is_content_hash():
    assert card_version(b"a") == card_version(b"a")
    assert card_version(b"a") != card_version(b"b")
    assert len(card_version(b"a")) == 12
