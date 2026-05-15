"""Tools that hit the per-user client API (/api/client/*).

Requires a client API key, which is distinct from the application key. If no
client key is configured, every tool here will return a clear error instead
of failing inside the HTTP call.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from pteromcp.config import Settings
    from pteromcp.tools import ClientFactory


def register(mcp: FastMCP, get_client: ClientFactory, settings: Settings) -> None:
    @mcp.tool(
        name="client_account",
        description="Return information about the user account that owns the client key.",
    )
    async def client_account() -> dict[str, Any]:
        client = await get_client()
        return await client.get("/account", surface="client") or {}

    @mcp.tool(
        name="client_servers_list",
        description=(
            "List the servers visible to the user. The panel returns short identifiers — "
            "use them in the rest of the client_* tools."
        ),
    )
    async def client_servers_list(
        per_page: int = 50,
        page: int = 1,
        include: str | None = None,
    ) -> dict[str, Any]:
        client = await get_client()
        params: dict[str, Any] = {"per_page": per_page, "page": page}
        if include:
            params["include"] = include
        return await client.get("", surface="client", params=params) or {}

    @mcp.tool(
        name="client_server_get",
        description="Fetch details of a server visible to the user. `server` is the short identifier.",
    )
    async def client_server_get(server: str, include: str | None = None) -> dict[str, Any]:
        client = await get_client()
        params = {"include": include} if include else None
        return await client.get(f"/servers/{server}", surface="client", params=params) or {}

    @mcp.tool(
        name="client_server_resources",
        description="Return live CPU / memory / disk / network usage for a server.",
    )
    async def client_server_resources(server: str) -> dict[str, Any]:
        client = await get_client()
        return await client.get(f"/servers/{server}/resources", surface="client") or {}

    @mcp.tool(
        name="client_server_power",
        description=(
            "Send a power signal to a server. Allowed signals: 'start', 'stop', 'restart', 'kill'."
        ),
    )
    async def client_server_power(server: str, signal: str) -> dict[str, Any]:
        if signal not in {"start", "stop", "restart", "kill"}:
            raise ValueError("signal must be one of: start, stop, restart, kill")
        client = await get_client()
        await client.post(
            f"/servers/{server}/power",
            surface="client",
            json={"signal": signal},
        )
        return {"server": server, "signal": signal, "accepted": True}

    @mcp.tool(
        name="client_server_command",
        description="Send a console command to a server (the server must be running).",
    )
    async def client_server_command(server: str, command: str) -> dict[str, Any]:
        client = await get_client()
        await client.post(
            f"/servers/{server}/command",
            surface="client",
            json={"command": command},
        )
        return {"server": server, "command": command, "sent": True}

    @mcp.tool(
        name="client_server_websocket",
        description=(
            "Return a short-lived WebSocket URL + token that can be used to stream console "
            "output / send commands. Tokens expire after ~15 minutes."
        ),
    )
    async def client_server_websocket(server: str) -> dict[str, Any]:
        client = await get_client()
        return await client.get(f"/servers/{server}/websocket", surface="client") or {}

    # --- File operations --------------------------------------------------

    @mcp.tool(
        name="client_files_list",
        description="List files in a directory of a server. `directory` defaults to '/'.",
    )
    async def client_files_list(server: str, directory: str = "/") -> dict[str, Any]:
        client = await get_client()
        return await client.get(
            f"/servers/{server}/files/list",
            surface="client",
            params={"directory": directory},
        ) or {}

    @mcp.tool(
        name="client_files_contents",
        description="Return the contents of a file on a server as a string.",
    )
    async def client_files_contents(server: str, file: str) -> dict[str, Any]:
        client = await get_client()
        payload = await client.get(
            f"/servers/{server}/files/contents",
            surface="client",
            params={"file": file},
        )
        if isinstance(payload, dict) and "data" in payload:
            return payload
        return {"data": payload, "file": file}

    @mcp.tool(
        name="client_files_write",
        description="Overwrite a file with the given contents. Creates intermediate dirs if needed.",
    )
    async def client_files_write(server: str, file: str, contents: str) -> dict[str, Any]:
        client = await get_client()
        # The write endpoint uses raw text body, not JSON. Build a manual request.
        # We piggy-back on the client by encoding as JSON-safe payload — most
        # panels accept text/plain so we go through httpx directly.
        request_url = f"/api/client/servers/{server}/files/write"
        response = await client.http.request(
            "POST",
            request_url,
            params={"file": file},
            content=contents.encode("utf-8"),
            headers={
                **client._auth_header("client"),  # type: ignore[attr-defined]
                "Content-Type": "text/plain",
            },
        )
        response.raise_for_status()
        return {"written": True, "file": file, "bytes": len(contents)}

    @mcp.tool(
        name="client_files_rename",
        description=(
            "Rename or move one or more files. `files` is a list of {from, to} pairs."
        ),
    )
    async def client_files_rename(
        server: str,
        files: list[dict[str, str]],
        root: str = "/",
    ) -> dict[str, Any]:
        client = await get_client()
        await client.put(
            f"/servers/{server}/files/rename",
            surface="client",
            json={"root": root, "files": files},
        )
        return {"renamed": True, "count": len(files)}

    @mcp.tool(
        name="client_files_copy",
        description="Duplicate a file on a server.",
    )
    async def client_files_copy(server: str, location: str) -> dict[str, Any]:
        client = await get_client()
        await client.post(
            f"/servers/{server}/files/copy",
            surface="client",
            json={"location": location},
        )
        return {"copied": True, "location": location}

    @mcp.tool(
        name="client_files_delete",
        description="Delete files or directories on a server.",
    )
    async def client_files_delete(
        server: str,
        files: list[str],
        root: str = "/",
    ) -> dict[str, Any]:
        client = await get_client()
        await client.post(
            f"/servers/{server}/files/delete",
            surface="client",
            json={"root": root, "files": files},
        )
        return {"deleted": True, "count": len(files)}

    @mcp.tool(
        name="client_files_create_folder",
        description="Create a new folder under `root` (default '/').",
    )
    async def client_files_create_folder(
        server: str,
        name: str,
        root: str = "/",
    ) -> dict[str, Any]:
        client = await get_client()
        await client.post(
            f"/servers/{server}/files/create-folder",
            surface="client",
            json={"root": root, "name": name},
        )
        return {"created": True, "name": name, "root": root}

    # --- Backups ----------------------------------------------------------

    @mcp.tool(
        name="client_backups_list",
        description="List backups for a server.",
    )
    async def client_backups_list(server: str) -> dict[str, Any]:
        client = await get_client()
        return await client.get(f"/servers/{server}/backups", surface="client") or {}

    @mcp.tool(
        name="client_backups_create",
        description=(
            "Create a new backup. Pass `is_locked=True` to prevent the rotation policy "
            "from deleting it. `ignored_files` is a newline-separated list of glob patterns."
        ),
    )
    async def client_backups_create(
        server: str,
        name: str | None = None,
        ignored_files: str | None = None,
        is_locked: bool = False,
    ) -> dict[str, Any]:
        client = await get_client()
        body: dict[str, Any] = {"is_locked": is_locked}
        if name is not None:
            body["name"] = name
        if ignored_files is not None:
            body["ignored"] = ignored_files
        return await client.post(
            f"/servers/{server}/backups",
            surface="client",
            json=body,
        ) or {}

    @mcp.tool(
        name="client_backups_get",
        description="Fetch a backup by UUID.",
    )
    async def client_backups_get(server: str, backup: str) -> dict[str, Any]:
        client = await get_client()
        return await client.get(
            f"/servers/{server}/backups/{backup}", surface="client"
        ) or {}

    @mcp.tool(
        name="client_backups_restore",
        description=(
            "Restore a backup. WARNING: this overwrites the server contents. "
            "Set `truncate=True` to wipe the server before restoring."
        ),
    )
    async def client_backups_restore(
        server: str,
        backup: str,
        truncate: bool = False,
    ) -> dict[str, Any]:
        client = await get_client()
        await client.post(
            f"/servers/{server}/backups/{backup}/restore",
            surface="client",
            json={"truncate": truncate},
        )
        return {"restore_triggered": True, "backup": backup}

    @mcp.tool(
        name="client_backups_delete",
        description="Delete a backup. Irreversible.",
    )
    async def client_backups_delete(server: str, backup: str) -> dict[str, Any]:
        client = await get_client()
        await client.delete(f"/servers/{server}/backups/{backup}", surface="client")
        return {"deleted": True, "backup": backup}

    # --- Schedules --------------------------------------------------------

    @mcp.tool(
        name="client_schedules_list",
        description="List scheduled tasks for a server.",
    )
    async def client_schedules_list(server: str) -> dict[str, Any]:
        client = await get_client()
        return await client.get(f"/servers/{server}/schedules", surface="client") or {}

    @mcp.tool(
        name="client_schedules_get",
        description="Fetch a schedule by id.",
    )
    async def client_schedules_get(server: str, schedule_id: int) -> dict[str, Any]:
        client = await get_client()
        return await client.get(
            f"/servers/{server}/schedules/{schedule_id}", surface="client"
        ) or {}

    @mcp.tool(
        name="client_schedules_execute",
        description="Trigger a schedule immediately, regardless of its cron timing.",
    )
    async def client_schedules_execute(server: str, schedule_id: int) -> dict[str, Any]:
        client = await get_client()
        await client.post(
            f"/servers/{server}/schedules/{schedule_id}/execute",
            surface="client",
        )
        return {"executed": True, "schedule_id": schedule_id}
