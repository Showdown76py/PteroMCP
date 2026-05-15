"""Per-server database tools (application surface)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from pteromcp.config import Settings
    from pteromcp.tools import ClientFactory


def register(mcp: FastMCP, get_client: ClientFactory, settings: Settings) -> None:
    @mcp.tool(
        name="databases_list",
        description="List databases attached to a server.",
    )
    async def databases_list(server_id: int, include: str | None = None) -> dict[str, Any]:
        client = await get_client()
        params = {"include": include} if include else None
        return await client.get(f"/servers/{server_id}/databases", params=params) or {}

    @mcp.tool(
        name="databases_get",
        description="Fetch a database attached to a server.",
    )
    async def databases_get(
        server_id: int,
        database_id: int,
        include: str | None = None,
    ) -> dict[str, Any]:
        client = await get_client()
        params = {"include": include} if include else None
        return await client.get(
            f"/servers/{server_id}/databases/{database_id}", params=params
        ) or {}

    @mcp.tool(
        name="databases_create",
        description=(
            "Create a new database on a server. `host` is the id of a configured database host. "
            "`remote` defaults to '%' (any host) — restrict it for security."
        ),
    )
    async def databases_create(
        server_id: int,
        database: str,
        host: int,
        remote: str = "%",
    ) -> dict[str, Any]:
        client = await get_client()
        body = {"database": database, "remote": remote, "host": host}
        return await client.post(f"/servers/{server_id}/databases", json=body) or {}

    @mcp.tool(
        name="databases_reset_password",
        description="Rotate the password of a server database.",
    )
    async def databases_reset_password(server_id: int, database_id: int) -> dict[str, Any]:
        client = await get_client()
        await client.post(f"/servers/{server_id}/databases/{database_id}/reset-password")
        return {"password_reset": True, "server_id": server_id, "database_id": database_id}

    @mcp.tool(
        name="databases_delete",
        description="Delete a database from a server. Irreversible.",
    )
    async def databases_delete(server_id: int, database_id: int) -> dict[str, Any]:
        client = await get_client()
        await client.delete(f"/servers/{server_id}/databases/{database_id}")
        return {"deleted": True, "server_id": server_id, "database_id": database_id}
