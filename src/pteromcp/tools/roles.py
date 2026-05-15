"""Role tools (Pelican only — Pterodactyl has no roles endpoint)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from pteromcp.config import Settings
    from pteromcp.tools import ClientFactory


def register(mcp: FastMCP, get_client: ClientFactory, settings: Settings) -> None:
    @mcp.tool(
        name="roles_list",
        description="List admin roles. Pelican-only — returns 404 on Pterodactyl.",
    )
    async def roles_list(per_page: int = 50, page: int = 1) -> dict[str, Any]:
        client = await get_client()
        return await client.get("/roles", params={"per_page": per_page, "page": page}) or {}

    @mcp.tool(
        name="roles_get",
        description="Fetch a single role by id. Pelican-only.",
    )
    async def roles_get(role_id: int) -> dict[str, Any]:
        client = await get_client()
        return await client.get(f"/roles/{role_id}") or {}

    @mcp.tool(
        name="roles_create",
        description="Create a new admin role. Pelican-only.",
    )
    async def roles_create(name: str, description: str | None = None) -> dict[str, Any]:
        client = await get_client()
        body: dict[str, Any] = {"name": name}
        if description:
            body["description"] = description
        return await client.post("/roles", json=body) or {}

    @mcp.tool(
        name="roles_update",
        description="Rename a role or update its description. Pelican-only.",
    )
    async def roles_update(
        role_id: int,
        name: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        client = await get_client()
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        return await client.patch(f"/roles/{role_id}", json=body) or {}

    @mcp.tool(
        name="roles_delete",
        description="Delete a role. The 'Root Admin' role cannot be deleted. Pelican-only.",
    )
    async def roles_delete(role_id: int) -> dict[str, Any]:
        client = await get_client()
        await client.delete(f"/roles/{role_id}")
        return {"deleted": True, "role_id": role_id}
