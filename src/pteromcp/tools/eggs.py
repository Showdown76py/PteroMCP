"""Egg / nest tools.

Pterodactyl groups eggs into nests; Pelican removed nests and exposes eggs
directly. We expose tools that work on both flavors by detecting the panel
type via :meth:`PanelClient.detect_panel_type`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from pteromcp.config import Settings
    from pteromcp.tools import ClientFactory


def register(mcp: FastMCP, get_client: ClientFactory, settings: Settings) -> None:
    @mcp.tool(
        name="eggs_list",
        description=(
            "List eggs. On Pelican, omit nest_id. On Pterodactyl, pass nest_id to enumerate "
            "the eggs inside a nest; otherwise the call uses /eggs which only exists on Pelican."
        ),
    )
    async def eggs_list(
        nest_id: int | None = None,
        per_page: int = 50,
        page: int = 1,
        include: str | None = None,
    ) -> dict[str, Any]:
        client = await get_client()
        params: dict[str, Any] = {"per_page": per_page, "page": page}
        if include:
            params["include"] = include
        path = f"/nests/{nest_id}/eggs" if nest_id is not None else "/eggs"
        return await client.get(path, params=params) or {}

    @mcp.tool(
        name="eggs_get",
        description=(
            "Fetch a single egg. On Pterodactyl provide nest_id; on Pelican omit it. "
            "Useful include values: 'variables', 'config', 'nest', 'script'."
        ),
    )
    async def eggs_get(
        egg_id: int,
        nest_id: int | None = None,
        include: str | None = None,
    ) -> dict[str, Any]:
        client = await get_client()
        params = {"include": include} if include else None
        path = (
            f"/nests/{nest_id}/eggs/{egg_id}"
            if nest_id is not None
            else f"/eggs/{egg_id}"
        )
        return await client.get(path, params=params) or {}

    @mcp.tool(
        name="nests_list",
        description="List nests. Pterodactyl-only; returns a clear error on Pelican.",
    )
    async def nests_list(per_page: int = 50, page: int = 1) -> dict[str, Any]:
        client = await get_client()
        return await client.get("/nests", params={"per_page": per_page, "page": page}) or {}

    @mcp.tool(
        name="nests_get",
        description="Fetch a single nest by id. Pterodactyl-only.",
    )
    async def nests_get(nest_id: int, include: str | None = None) -> dict[str, Any]:
        client = await get_client()
        params = {"include": include} if include else None
        return await client.get(f"/nests/{nest_id}", params=params) or {}
