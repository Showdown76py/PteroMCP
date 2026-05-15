"""Allocation tools (per-node network ports, application surface)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from pteromcp.config import Settings
    from pteromcp.tools import ClientFactory


def register(mcp: FastMCP, get_client: ClientFactory, settings: Settings) -> None:
    @mcp.tool(
        name="allocations_list",
        description="List allocations on a node. Each allocation maps an ip:port pair to a possible server.",
    )
    async def allocations_list(
        node_id: int,
        per_page: int = 50,
        page: int = 1,
    ) -> dict[str, Any]:
        client = await get_client()
        return await client.get(
            f"/nodes/{node_id}/allocations",
            params={"per_page": per_page, "page": page},
        ) or {}

    @mcp.tool(
        name="allocations_create",
        description=(
            "Create one or more allocations on a node. `ports` accepts single ports ('25565') "
            "or ranges ('25565-25570'). `alias` is an optional public-facing hostname."
        ),
    )
    async def allocations_create(
        node_id: int,
        ip: str,
        ports: list[str],
        alias: str | None = None,
    ) -> dict[str, Any]:
        client = await get_client()
        body: dict[str, Any] = {"ip": ip, "ports": ports}
        if alias is not None:
            body["alias"] = alias
        await client.post(f"/nodes/{node_id}/allocations", json=body)
        return {"created": True, "node_id": node_id, "ip": ip, "ports": ports}

    @mcp.tool(
        name="allocations_delete",
        description="Delete an unassigned allocation from a node. Irreversible.",
    )
    async def allocations_delete(node_id: int, allocation_id: int) -> dict[str, Any]:
        client = await get_client()
        await client.delete(f"/nodes/{node_id}/allocations/{allocation_id}")
        return {"deleted": True, "node_id": node_id, "allocation_id": allocation_id}
