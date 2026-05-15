"""Tests for the Settings module."""

from __future__ import annotations

import pytest

from pteromcp.config import ALL_CATEGORIES, Settings


def make(**kwargs) -> Settings:
    defaults: dict[str, object] = {
        "panel_url": "https://panel.example.test",
        "application_key": "papp_test",
    }
    defaults.update(kwargs)
    return Settings(**defaults)  # type: ignore[arg-type]


def test_base_url_strips_trailing_slash() -> None:
    s = make(panel_url="https://panel.example.test/")
    assert s.base_url() == "https://panel.example.test"


def test_disabled_categories_parses_csv() -> None:
    s = make(disabled_categories="client,users")
    assert s.disabled_set() == {"client", "users"}


def test_disabled_categories_validates() -> None:
    with pytest.raises(ValueError, match="Unknown disabled categories"):
        make(disabled_categories="not-a-category")


def test_disabled_categories_blank_is_empty() -> None:
    assert make(disabled_categories="").disabled_set() == set()


def test_require_application_key_raises_when_missing() -> None:
    s = make(application_key=None)
    with pytest.raises(RuntimeError, match="PTEROMCP_APPLICATION_KEY"):
        s.require_application_key()


def test_require_client_key_raises_when_missing() -> None:
    s = make()
    with pytest.raises(RuntimeError, match="PTEROMCP_CLIENT_KEY"):
        s.require_client_key()


def test_all_categories_constant_matches_documented() -> None:
    assert {
        "users",
        "nodes",
        "servers",
        "eggs",
        "roles",
        "mounts",
        "databases",
        "allocations",
        "client",
    } == ALL_CATEGORIES
