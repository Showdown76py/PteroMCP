"""Server CRUD and power tools (application surface)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from pteromcp.config import Settings
    from pteromcp.tools import ClientFactory


def register(mcp: FastMCP, get_client: ClientFactory, settings: Settings) -> None:
    @mcp.tool(
        name="servers_list",
        description=(
            "List all servers on the panel. Useful include values: 'allocations', 'user', "
            "'node', 'egg', 'variables', 'databases'."
        ),
    )
    async def servers_list(
        per_page: int = 50,
        page: int = 1,
        include: str | None = None,
        filter_name: str | None = None,
    ) -> dict[str, Any]:
        client = await get_client()
        params: dict[str, Any] = {"per_page": per_page, "page": page}
        if include:
            params["include"] = include
        if filter_name:
            params["filter[name]"] = filter_name
        return await client.get("/servers", params=params) or {}

    @mcp.tool(
        name="servers_get",
        description="Fetch a server by numeric id (e.g. 2), not by short identifier.",
    )
    async def servers_get(server_id: int, include: str | None = None) -> dict[str, Any]:
        client = await get_client()
        params = {"include": include} if include else None
        return await client.get(f"/servers/{server_id}", params=params) or {}

    @mcp.tool(
        name="servers_get_external",
        description="Look up a server by its external_id (string set during creation).",
    )
    async def servers_get_external(external_id: str) -> dict[str, Any]:
        client = await get_client()
        return await client.get(f"/servers/external/{external_id}") or {}

    @mcp.tool(
        name="servers_create",
        description=(
            "Create a new server. Required: name, owner user_id, egg id, docker image, "
            "startup command, allocation id, and resource limits. "
            "`environment` is a dict of egg-variable names to values. "
            "If `start_on_completion=True` the server boots once the install finishes."
        ),
    )
    async def servers_create(
        name: str,
        user_id: int,
        egg: int,
        docker_image: str,
        startup: str,
        environment: dict[str, Any],
        memory: int,
        disk: int,
        cpu: int = 0,
        swap: int = 0,
        io: int = 500,
        allocation_id: int | None = None,
        additional_allocation_ids: list[int] | None = None,
        databases: int = 0,
        allocations: int = 0,
        backups: int = 0,
        oom_disabled: bool = True,
        skip_scripts: bool = False,
        start_on_completion: bool = False,
        external_id: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        client = await get_client()
        if allocation_id is None:
            raise ValueError("allocation_id is required to create a server.")
        body: dict[str, Any] = {
            "name": name,
            "user": user_id,
            "egg": egg,
            "docker_image": docker_image,
            "startup": startup,
            "environment": environment,
            "limits": {
                "memory": memory,
                "swap": swap,
                "disk": disk,
                "io": io,
                "cpu": cpu,
                "oom_disabled": oom_disabled,
            },
            "feature_limits": {
                "databases": databases,
                "allocations": allocations,
                "backups": backups,
            },
            "allocation": {"default": allocation_id},
            "skip_scripts": skip_scripts,
            "start_on_completion": start_on_completion,
        }
        if additional_allocation_ids:
            body["allocation"]["additional"] = additional_allocation_ids
        if external_id is not None:
            body["external_id"] = external_id
        if description is not None:
            body["description"] = description
        return await client.post("/servers", json=body) or {}

    @mcp.tool(
        name="servers_update_details",
        description="Update administrative metadata of a server (name, user owner, external id, description).",
    )
    async def servers_update_details(
        server_id: int,
        name: str,
        user_id: int,
        external_id: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        client = await get_client()
        body: dict[str, Any] = {"name": name, "user": user_id}
        if external_id is not None:
            body["external_id"] = external_id
        if description is not None:
            body["description"] = description
        return await client.patch(f"/servers/{server_id}/details", json=body) or {}

    @mcp.tool(
        name="servers_update_build",
        description=(
            "Update resource limits / feature limits / allocations of a server. "
            "All limit fields are required."
        ),
    )
    async def servers_update_build(
        server_id: int,
        allocation_id: int,
        memory: int,
        disk: int,
        cpu: int,
        swap: int = 0,
        io: int = 500,
        databases: int = 0,
        allocations: int = 0,
        backups: int = 0,
        oom_disabled: bool = True,
        add_allocations: list[int] | None = None,
        remove_allocations: list[int] | None = None,
    ) -> dict[str, Any]:
        client = await get_client()
        body: dict[str, Any] = {
            "allocation": allocation_id,
            "memory": memory,
            "swap": swap,
            "disk": disk,
            "io": io,
            "cpu": cpu,
            "oom_disabled": oom_disabled,
            "feature_limits": {
                "databases": databases,
                "allocations": allocations,
                "backups": backups,
            },
        }
        if add_allocations:
            body["add_allocations"] = add_allocations
        if remove_allocations:
            body["remove_allocations"] = remove_allocations
        return await client.patch(f"/servers/{server_id}/build", json=body) or {}

    @mcp.tool(
        name="servers_update_startup",
        description=(
            "Update startup command, egg, docker image and environment variables. "
            "Set `skip_scripts=True` to skip the install script after egg changes."
        ),
    )
    async def servers_update_startup(
        server_id: int,
        startup: str,
        egg: int,
        docker_image: str,
        environment: dict[str, Any],
        skip_scripts: bool = False,
    ) -> dict[str, Any]:
        client = await get_client()
        body = {
            "startup": startup,
            "egg": egg,
            "image": docker_image,
            "environment": environment,
            "skip_scripts": skip_scripts,
        }
        return await client.patch(f"/servers/{server_id}/startup", json=body) or {}

    @mcp.tool(
        name="servers_suspend",
        description="Suspend a server (stop it and lock the user out). Reversible via servers_unsuspend.",
    )
    async def servers_suspend(server_id: int) -> dict[str, Any]:
        client = await get_client()
        await client.post(f"/servers/{server_id}/suspend")
        return {"suspended": True, "server_id": server_id}

    @mcp.tool(
        name="servers_unsuspend",
        description="Unsuspend a previously suspended server.",
    )
    async def servers_unsuspend(server_id: int) -> dict[str, Any]:
        client = await get_client()
        await client.post(f"/servers/{server_id}/unsuspend")
        return {"unsuspended": True, "server_id": server_id}

    @mcp.tool(
        name="servers_reinstall",
        description="Trigger a fresh egg install on the server (wipes /home/container).",
    )
    async def servers_reinstall(server_id: int) -> dict[str, Any]:
        client = await get_client()
        await client.post(f"/servers/{server_id}/reinstall")
        return {"reinstall_triggered": True, "server_id": server_id}

    @mcp.tool(
        name="servers_delete",
        description=(
            "Delete a server. If `force=True`, the server is removed even if the daemon "
            "reports an error. Irreversible."
        ),
    )
    async def servers_delete(server_id: int, force: bool = False) -> dict[str, Any]:
        client = await get_client()
        path = f"/servers/{server_id}" + ("/force" if force else "")
        await client.delete(path)
        return {"deleted": True, "server_id": server_id, "force": force}
