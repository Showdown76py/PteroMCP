"""Tool registration for the MCP server.

Each submodule exposes a `register(mcp, get_client)` callable. The server
imports them and calls each one with the FastMCP instance and a factory that
returns an active :class:`pteromcp.client.PanelClient`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from pteromcp.client import PanelClient
    from pteromcp.config import Settings

ClientFactory = Callable[[], Awaitable["PanelClient"]]
Registrar = Callable[["FastMCP", ClientFactory, "Settings"], None]


def all_registrars() -> dict[str, Registrar]:
    """Map category name → registrar function. Imported lazily."""
    from pteromcp.tools import (
        allocations,
        client_surface,
        databases,
        eggs,
        mounts,
        nodes,
        roles,
        servers,
        users,
    )

    return {
        "users": users.register,
        "nodes": nodes.register,
        "servers": servers.register,
        "eggs": eggs.register,
        "roles": roles.register,
        "mounts": mounts.register,
        "databases": databases.register,
        "allocations": allocations.register,
        "client": client_surface.register,
    }
