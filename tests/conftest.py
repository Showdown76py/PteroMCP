"""Shared pytest fixtures."""

from __future__ import annotations

import os

import pytest

from pteromcp.client import PanelClient
from pteromcp.config import Settings


def _build_settings(**overrides) -> Settings:
    defaults = {
        "panel_url": "https://panel.example.test",
        "application_key": "papp_unit_test_key",
        "client_key": "ptlc_unit_test_key",
        "panel_type": "auto",
        "timeout": 5.0,
        "read_only": False,
        "disabled_categories": "",
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


@pytest.fixture()
def settings() -> Settings:
    return _build_settings()


@pytest.fixture()
def read_only_settings() -> Settings:
    return _build_settings(read_only=True)


@pytest.fixture()
async def panel_client(settings: Settings):
    client = PanelClient(settings)
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture()
def integration_credentials() -> dict[str, str] | None:
    """Return real panel credentials from env, or None to skip the test."""
    url = os.environ.get("PTEROMCP_INTEGRATION_URL")
    key = os.environ.get("PTEROMCP_INTEGRATION_APPKEY")
    if not (url and key):
        return None
    return {"url": url, "key": key}
