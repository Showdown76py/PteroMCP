"""End-to-end test: spawn the server via stdio and use the official MCP client.

This validates that:
  * `python -m pteromcp` actually starts and speaks MCP over stdio;
  * the official client can list tools and call them;
  * the `panel_info` tool round-trips through the protocol.
"""

from __future__ import annotations

import os
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.fixture()
def integration_env() -> dict[str, str]:
    url = os.environ.get("PTEROMCP_INTEGRATION_URL")
    key = os.environ.get("PTEROMCP_INTEGRATION_APPKEY")
    if not (url and key):
        pytest.skip(
            "PTEROMCP_INTEGRATION_URL and PTEROMCP_INTEGRATION_APPKEY must be set."
        )
    return {
        "PTEROMCP_PANEL_URL": url,
        "PTEROMCP_APPLICATION_KEY": key,
        "PYTHONUNBUFFERED": "1",
    }


@pytest.mark.integration
async def test_stdio_handshake_and_panel_info(integration_env: dict[str, str]) -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "pteromcp", "stdio"],
        env={**os.environ, **integration_env},
    )

    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        init = await session.initialize()
        assert init.serverInfo.name == "pteromcp"

        tools = await session.list_tools()
        tool_names = {t.name for t in tools.tools}
        assert "panel_info" in tool_names
        assert "users_list" in tool_names
        assert "servers_list" in tool_names

        result = await session.call_tool("panel_info", {})
        assert result.isError is False, result
        assert result.structuredContent is not None
        assert result.structuredContent["panel_type"] in {"pterodactyl", "pelican"}
        assert result.structuredContent["application_key_configured"] is True


@pytest.mark.integration
async def test_stdio_list_users_returns_data(integration_env: dict[str, str]) -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "pteromcp", "stdio"],
        env={**os.environ, **integration_env},
    )

    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool("users_list", {"per_page": 5, "page": 1})
        assert result.isError is False, result
        assert result.structuredContent is not None
        # FastMCP wraps non-model returns under a top-level "result" key when
        # structured_output is on; fall back to the dict itself otherwise.
        payload = result.structuredContent.get("result", result.structuredContent)
        assert "data" in payload
