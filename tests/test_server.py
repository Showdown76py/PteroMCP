"""Tests for the FastMCP server assembly."""

from __future__ import annotations

import httpx
import respx
from mcp.server.fastmcp import FastMCP

from pteromcp.config import Settings
from pteromcp.server import create_server


def _settings(**kw) -> Settings:
    defaults: dict[str, object] = {
        "panel_url": "https://panel.example.test",
        "application_key": "papp_test",
        "client_key": "ptlc_test",
    }
    defaults.update(kw)
    return Settings(**defaults)  # type: ignore[arg-type]


def _tool_names(mcp: FastMCP) -> set[str]:
    return {t.name for t in mcp._tool_manager.list_tools()}


def test_server_registers_all_categories() -> None:
    mcp = create_server(_settings())
    names = _tool_names(mcp)
    # Sanity: at least one tool from each category.
    expected_samples = {
        "panel_info",
        "users_list",
        "nodes_list",
        "servers_list",
        "eggs_list",
        "roles_list",
        "mounts_list",
        "databases_list",
        "allocations_list",
        "client_account",
    }
    missing = expected_samples - names
    assert not missing, f"Missing tools: {missing}"
    assert len(names) >= 60


def test_disabled_categories_skip_registration() -> None:
    mcp = create_server(_settings(disabled_categories="client,roles"))
    names = _tool_names(mcp)
    assert "client_account" not in names
    assert "roles_list" not in names
    # Non-disabled categories still register.
    assert "users_list" in names


@respx.mock
async def test_panel_info_tool_reports_state() -> None:
    respx.get("https://panel.example.test/api/application/locations").mock(
        return_value=httpx.Response(
            404, json={"errors": [{"code": "NotFoundHttpException"}]}
        )
    )
    mcp = create_server(_settings())
    tool = mcp._tool_manager.get_tool("panel_info")
    assert tool is not None
    result = await tool.fn()  # type: ignore[misc]
    assert result["panel_type"] == "pelican"
    assert result["panel_url"] == "https://panel.example.test"
    assert result["application_key_configured"] is True
    assert "users" in result["enabled_categories"]
