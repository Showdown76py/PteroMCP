"""User-management tools (application surface)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from pteromcp.config import Settings
    from pteromcp.tools import ClientFactory


def register(mcp: FastMCP, get_client: ClientFactory, settings: Settings) -> None:
    @mcp.tool(
        name="users_list",
        description=(
            "List panel users (application surface). Supports search filter and pagination."
        ),
    )
    async def users_list(
        search: str | None = None,
        per_page: int = 50,
        page: int = 1,
        include: str | None = None,
    ) -> dict[str, Any]:
        client = await get_client()
        params: dict[str, Any] = {"per_page": per_page, "page": page}
        if search:
            params["filter[email]"] = search
        if include:
            params["include"] = include
        return await client.get("/users", params=params) or {}

    @mcp.tool(
        name="users_get",
        description="Fetch a single user by numeric id. Use include='servers' to attach owned servers.",
    )
    async def users_get(user_id: int, include: str | None = None) -> dict[str, Any]:
        client = await get_client()
        params = {"include": include} if include else None
        return await client.get(f"/users/{user_id}", params=params) or {}

    @mcp.tool(
        name="users_get_external",
        description="Look up a user by their external_id (string set during creation).",
    )
    async def users_get_external(external_id: str) -> dict[str, Any]:
        client = await get_client()
        return await client.get(f"/users/external/{external_id}") or {}

    @mcp.tool(
        name="users_create",
        description=(
            "Create a new panel user. Required: email, username, first_name, last_name. "
            "Optional: password (auto-generated if omitted), root_admin, language, external_id."
        ),
    )
    async def users_create(
        email: str,
        username: str,
        first_name: str,
        last_name: str,
        password: str | None = None,
        root_admin: bool = False,
        language: str = "en",
        external_id: str | None = None,
    ) -> dict[str, Any]:
        client = await get_client()
        body: dict[str, Any] = {
            "email": email,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "root_admin": root_admin,
            "language": language,
        }
        if password:
            body["password"] = password
        if external_id:
            body["external_id"] = external_id
        return await client.post("/users", json=body) or {}

    @mcp.tool(
        name="users_update",
        description=(
            "Partially update a user. Provide only the fields you want to change. "
            "Note: Pterodactyl requires email, username, first_name, last_name and language "
            "in the body even for partial edits — pass the current values for unchanged fields."
        ),
    )
    async def users_update(
        user_id: int,
        email: str,
        username: str,
        first_name: str,
        last_name: str,
        language: str = "en",
        password: str | None = None,
        root_admin: bool | None = None,
        external_id: str | None = None,
    ) -> dict[str, Any]:
        client = await get_client()
        body: dict[str, Any] = {
            "email": email,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "language": language,
        }
        if password is not None:
            body["password"] = password
        if root_admin is not None:
            body["root_admin"] = root_admin
        if external_id is not None:
            body["external_id"] = external_id
        return await client.patch(f"/users/{user_id}", json=body) or {}

    @mcp.tool(
        name="users_delete",
        description=(
            "Delete a panel user. The user must not own any servers. Irreversible."
        ),
    )
    async def users_delete(user_id: int) -> dict[str, Any]:
        client = await get_client()
        await client.delete(f"/users/{user_id}")
        return {"deleted": True, "user_id": user_id}
