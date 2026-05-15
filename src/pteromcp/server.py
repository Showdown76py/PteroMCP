"""PteroMCP MCP server entry-point.

Defines a :class:`mcp.server.fastmcp.FastMCP` instance, registers every tool
module, and exposes a `create_server` factory plus a `run_stdio` helper.
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from pteromcp._version import __version__
from pteromcp.client import PanelClient
from pteromcp.config import Settings
from pteromcp.tools import all_registrars

log = logging.getLogger("pteromcp")

INSTRUCTIONS = """\
PteroMCP exposes the Pterodactyl / Pelican panel API to MCP clients.

Capabilities are organised in categories:
  * users          – CRUD on panel users.
  * nodes          – CRUD on game-server hosts (wings/daemon).
  * allocations    – per-node ip:port allocations.
  * servers        – CRUD on game servers + suspend / unsuspend / reinstall.
  * databases      – per-server database management.
  * eggs / nests   – egg lookup (nests are Pterodactyl-only).
  * roles          – admin role management (Pelican-only).
  * mounts         – bind-mounts attached to containers.
  * client         – per-user operations (requires a client API key): power signals,
                     console commands, file ops, backups, schedules.

All tools accept and return JSON. IDs are integers unless explicitly described
as "short identifier" (which the client API returns).
"""


def create_server(settings: Settings | None = None) -> FastMCP:
    """Build a FastMCP server with all tool categories registered."""
    cfg: Settings = settings if settings is not None else Settings()  # type: ignore[call-arg]
    disabled = cfg.disabled_set()

    # We keep a single shared PanelClient across all tool calls. FastMCP runs
    # tools concurrently, but httpx.AsyncClient is safe for concurrent use.
    panel_client = PanelClient(cfg)

    async def get_client() -> PanelClient:
        return panel_client

    mcp = FastMCP(
        name="pteromcp",
        instructions=INSTRUCTIONS,
    )

    @mcp.tool(
        name="panel_info",
        description=(
            "Return PteroMCP / panel info: detected panel type, base URL, version, "
            "whether the client surface is configured, and which tool categories are enabled."
        ),
    )
    async def panel_info() -> dict[str, object]:
        try:
            detected = await panel_client.detect_panel_type()
        except Exception as err:
            detected = f"detection-failed: {err}"
        return {
            "pteromcp_version": __version__,
            "panel_url": cfg.base_url(),
            "panel_type": detected,
            "application_key_configured": bool(cfg.application_key),
            "client_key_configured": bool(cfg.client_key),
            "read_only": cfg.read_only,
            "enabled_categories": sorted(set(all_registrars()) - disabled),
            "disabled_categories": sorted(disabled),
        }

    registrars = all_registrars()
    for name, registrar in registrars.items():
        if name in disabled:
            log.info("Skipping disabled category: %s", name)
            continue
        registrar(mcp, get_client, cfg)

    return mcp


def run_stdio() -> None:
    """Run the server over stdio. This is the standard MCP transport."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = Settings()  # type: ignore[call-arg]
    server = create_server(settings)
    server.run("stdio")
