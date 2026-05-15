"""Mount tools (bind-mounts into server containers)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from pteromcp.config import Settings
    from pteromcp.tools import ClientFactory


def register(mcp: FastMCP, get_client: ClientFactory, settings: Settings) -> None:
    @mcp.tool(
        name="mounts_list",
        description="List configured mounts.",
    )
    async def mounts_list(per_page: int = 50, page: int = 1) -> dict[str, Any]:
        client = await get_client()
        return await client.get("/mounts", params={"per_page": per_page, "page": page}) or {}

    @mcp.tool(
        name="mounts_get",
        description="Fetch a single mount by id.",
    )
    async def mounts_get(mount_id: int) -> dict[str, Any]:
        client = await get_client()
        return await client.get(f"/mounts/{mount_id}") or {}

    @mcp.tool(
        name="mounts_create",
        description=(
            "Create a new mount. `source` is the host path, `target` the in-container path. "
            "`user_mountable` controls whether end-users can attach it to their servers."
        ),
    )
    async def mounts_create(
        name: str,
        source: str,
        target: str,
        description: str | None = None,
        read_only: bool = False,
        user_mountable: bool = False,
    ) -> dict[str, Any]:
        client = await get_client()
        body: dict[str, Any] = {
            "name": name,
            "source": source,
            "target": target,
            "read_only": read_only,
            "user_mountable": user_mountable,
        }
        if description is not None:
            body["description"] = description
        return await client.post("/mounts", json=body) or {}

    @mcp.tool(
        name="mounts_update",
        description="Update an existing mount.",
    )
    async def mounts_update(
        mount_id: int,
        name: str | None = None,
        source: str | None = None,
        target: str | None = None,
        description: str | None = None,
        read_only: bool | None = None,
        user_mountable: bool | None = None,
    ) -> dict[str, Any]:
        client = await get_client()
        body: dict[str, Any] = {}
        for key, value in {
            "name": name,
            "source": source,
            "target": target,
            "description": description,
            "read_only": read_only,
            "user_mountable": user_mountable,
        }.items():
            if value is not None:
                body[key] = value
        return await client.patch(f"/mounts/{mount_id}", json=body) or {}

    @mcp.tool(
        name="mounts_delete",
        description="Delete a mount. Irreversible.",
    )
    async def mounts_delete(mount_id: int) -> dict[str, Any]:
        client = await get_client()
        await client.delete(f"/mounts/{mount_id}")
        return {"deleted": True, "mount_id": mount_id}
