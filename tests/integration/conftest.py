"""Integration test fixtures: enable the in-memory recorder and custom integrations.

`recorder_mock` must be requested before `enable_custom_integrations`
(pytest-homeassistant-custom-component README).
"""

import pytest


@pytest.fixture(autouse=True)
async def _auto_enable(recorder_mock, enable_custom_integrations):
    """Enable the mocked recorder and custom integration loading for every test here."""
