"""Node and allocation tools (application surface)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from pteromcp.config import Settings
    from pteromcp.tools import ClientFactory


def register(mcp: FastMCP, get_client: ClientFactory, settings: Settings) -> None:
    @mcp.tool(
        name="nodes_list",
        description="List all panel nodes (machines that run game servers).",
    )
    async def nodes_list(
        per_page: int = 50,
        page: int = 1,
        include: str | None = None,
    ) -> dict[str, Any]:
        client = await get_client()
        params: dict[str, Any] = {"per_page": per_page, "page": page}
        if include:
            params["include"] = include
        return await client.get("/nodes", params=params) or {}

    @mcp.tool(
        name="nodes_get",
        description=(
            "Fetch a single node by id. Useful include values: 'allocations', 'location' "
            "(Pterodactyl only), 'servers'."
        ),
    )
    async def nodes_get(node_id: int, include: str | None = None) -> dict[str, Any]:
        client = await get_client()
        params = {"include": include} if include else None
        return await client.get(f"/nodes/{node_id}", params=params) or {}

    @mcp.tool(
        name="nodes_configuration",
        description=(
            "Return the wings/daemon configuration block for a node. "
            "Note: includes the node token — treat as a secret."
        ),
    )
    async def nodes_configuration(node_id: int) -> dict[str, Any]:
        client = await get_client()
        return await client.get(f"/nodes/{node_id}/configuration") or {}

    @mcp.tool(
        name="nodes_create",
        description=(
            "Create a new node. On Pterodactyl pass `location_id`; on Pelican locations "
            "do not exist so the field is ignored. Memory/disk values are in MB."
        ),
    )
    async def nodes_create(
        name: str,
        fqdn: str,
        memory: int,
        disk: int,
        daemon_listen: int = 8080,
        daemon_sftp: int = 2022,
        scheme: str = "https",
        memory_overallocate: int = 0,
        disk_overallocate: int = 0,
        upload_size: int = 100,
        behind_proxy: bool = False,
        public: bool = True,
        maintenance_mode: bool = False,
        location_id: int | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        client = await get_client()
        body: dict[str, Any] = {
            "name": name,
            "fqdn": fqdn,
            "scheme": scheme,
            "memory": memory,
            "memory_overallocate": memory_overallocate,
            "disk": disk,
            "disk_overallocate": disk_overallocate,
            "upload_size": upload_size,
            "daemon_sftp": daemon_sftp,
            "daemon_listen": daemon_listen,
            "behind_proxy": behind_proxy,
            "public": public,
            "maintenance_mode": maintenance_mode,
        }
        if location_id is not None:
            body["location_id"] = location_id
        if description is not None:
            body["description"] = description
        return await client.post("/nodes", json=body) or {}

    @mcp.tool(
        name="nodes_update",
        description=(
            "Update a node. Send the full set of required fields plus any you want to change."
        ),
    )
    async def nodes_update(
        node_id: int,
        name: str,
        fqdn: str,
        memory: int,
        disk: int,
        scheme: str = "https",
        memory_overallocate: int = 0,
        disk_overallocate: int = 0,
        upload_size: int = 100,
        daemon_listen: int = 8080,
        daemon_sftp: int = 2022,
        behind_proxy: bool = False,
        public: bool = True,
        maintenance_mode: bool = False,
        location_id: int | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        client = await get_client()
        body: dict[str, Any] = {
            "name": name,
            "fqdn": fqdn,
            "scheme": scheme,
            "memory": memory,
            "memory_overallocate": memory_overallocate,
            "disk": disk,
            "disk_overallocate": disk_overallocate,
            "upload_size": upload_size,
            "daemon_sftp": daemon_sftp,
            "daemon_listen": daemon_listen,
            "behind_proxy": behind_proxy,
            "public": public,
            "maintenance_mode": maintenance_mode,
        }
        if location_id is not None:
            body["location_id"] = location_id
        if description is not None:
            body["description"] = description
        return await client.patch(f"/nodes/{node_id}", json=body) or {}

    @mcp.tool(
        name="nodes_delete",
        description="Delete a node. The node must have no servers assigned. Irreversible.",
    )
    async def nodes_delete(node_id: int) -> dict[str, Any]:
        client = await get_client()
        await client.delete(f"/nodes/{node_id}")
        return {"deleted": True, "node_id": node_id}
