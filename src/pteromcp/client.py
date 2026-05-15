"""Async HTTP client for Pterodactyl and Pelican panels.

This module wraps the small subset of behaviours that are common to every
endpoint of the panel API: authentication header, JSON encoding, error
mapping, panel detection, read-only enforcement.

Both panels (Pterodactyl and its Pelican fork) expose two API surfaces:

* `/api/application/*` — admin operations (requires an "application" key).
* `/api/client/*`      — per-user operations (requires a "client" key).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Literal

import httpx

from pteromcp.config import Settings
from pteromcp.errors import PanelHTTPError, ReadOnlyError

JSON = dict[str, Any]
Surface = Literal["application", "client"]
MUTATING_METHODS = frozenset({"POST", "PATCH", "PUT", "DELETE"})


def _format_error(payload: Any, status_code: int) -> str:
    """Render a human-readable message from the panel's error payload."""
    if isinstance(payload, dict):
        errors = payload.get("errors")
        if isinstance(errors, list) and errors:
            parts = []
            for err in errors:
                if not isinstance(err, dict):
                    continue
                code = err.get("code")
                detail = err.get("detail") or err.get("title") or err.get("message")
                if code and detail:
                    parts.append(f"{code}: {detail}")
                elif detail:
                    parts.append(str(detail))
                elif code:
                    parts.append(str(code))
            if parts:
                return "; ".join(parts)
        if "message" in payload:
            return str(payload["message"])
    if isinstance(payload, str) and payload:
        return payload[:300]
    return f"HTTP {status_code}"


class PanelClient:
    """Thin async wrapper around the panel HTTP API."""

    def __init__(self, settings: Settings, http: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self._http = http
        self._owns_http = http is None
        self._detected_type: Literal["pterodactyl", "pelican"] | None = (
            settings.panel_type if settings.panel_type != "auto" else None
        )

    @property
    def http(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                base_url=self.settings.base_url(),
                timeout=self.settings.timeout,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "User-Agent": f"PteroMCP/{_user_agent_version()}",
                },
            )
        return self._http

    async def aclose(self) -> None:
        if self._owns_http and self._http is not None:
            await self._http.aclose()
            self._http = None

    async def __aenter__(self) -> PanelClient:
        _ = self.http  # eager construction
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    def _auth_header(self, surface: Surface) -> dict[str, str]:
        key = (
            self.settings.require_application_key()
            if surface == "application"
            else self.settings.require_client_key()
        )
        return {"Authorization": f"Bearer {key}"}

    async def request(
        self,
        method: str,
        path: str,
        *,
        surface: Surface = "application",
        params: dict[str, Any] | None = None,
        json: Any = None,
    ) -> JSON | None:
        method = method.upper()
        if self.settings.read_only and method in MUTATING_METHODS:
            raise ReadOnlyError(method, path)

        # Normalise the path: callers may pass either `nodes` or `/nodes`.
        path = path if path.startswith("/") else f"/{path}"
        full = f"/api/{surface}{path}"

        response = await self.http.request(
            method,
            full,
            params=_clean_params(params),
            json=json,
            headers=self._auth_header(surface),
        )

        if response.status_code == 204 or not response.content:
            if 200 <= response.status_code < 300:
                return None
            raise PanelHTTPError(
                response.status_code,
                f"HTTP {response.status_code} (empty body)",
                method=method,
                url=full,
            )

        try:
            payload = response.json()
        except ValueError:
            payload = response.text

        if 200 <= response.status_code < 300:
            return payload if isinstance(payload, dict) else {"data": payload}

        raise PanelHTTPError(
            response.status_code,
            _format_error(payload, response.status_code),
            method=method,
            url=full,
            payload=payload,
        )

    # Convenience wrappers ---------------------------------------------------

    async def get(self, path: str, **kw: Any) -> JSON | None:
        return await self.request("GET", path, **kw)

    async def post(self, path: str, json: Any = None, **kw: Any) -> JSON | None:
        return await self.request("POST", path, json=json, **kw)

    async def patch(self, path: str, json: Any = None, **kw: Any) -> JSON | None:
        return await self.request("PATCH", path, json=json, **kw)

    async def put(self, path: str, json: Any = None, **kw: Any) -> JSON | None:
        return await self.request("PUT", path, json=json, **kw)

    async def delete(self, path: str, **kw: Any) -> JSON | None:
        return await self.request("DELETE", path, **kw)

    # Pagination -------------------------------------------------------------

    async def list_all(
        self,
        path: str,
        *,
        surface: Surface = "application",
        params: dict[str, Any] | None = None,
        max_pages: int = 100,
    ) -> list[JSON]:
        """Walk a paginated `object: list` endpoint and return all items."""
        items: list[JSON] = []
        page = 1
        base_params = dict(params or {})
        while page <= max_pages:
            base_params["page"] = page
            payload = await self.request("GET", path, surface=surface, params=base_params)
            if not isinstance(payload, dict):
                break
            data = payload.get("data") or []
            items.extend(item for item in data if isinstance(item, dict))
            pagination = (
                (payload.get("meta") or {}).get("pagination") or {}
                if isinstance(payload.get("meta"), dict)
                else {}
            )
            total_pages = int(pagination.get("total_pages") or 1)
            if page >= total_pages:
                break
            page += 1
        return items

    # Panel detection --------------------------------------------------------

    async def detect_panel_type(self) -> Literal["pterodactyl", "pelican"]:
        """Detect whether the panel is Pterodactyl or its Pelican fork.

        Pelican removed the `/api/application/locations` route. If that
        endpoint returns 404 we conclude Pelican, otherwise Pterodactyl.
        Detection is cached on the instance.
        """
        if self._detected_type is not None:
            return self._detected_type
        try:
            await self.request("GET", "/locations", surface="application")
        except PanelHTTPError as err:
            if err.status_code == 404:
                self._detected_type = "pelican"
                return self._detected_type
            raise
        self._detected_type = "pterodactyl"
        return self._detected_type


def _clean_params(params: dict[str, Any] | None) -> dict[str, Any] | None:
    if not params:
        return None
    out = {}
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, bool):
            out[key] = "true" if value else "false"
        else:
            out[key] = value
    return out or None


def _user_agent_version() -> str:
    from pteromcp._version import __version__
    return __version__


@asynccontextmanager
async def panel_client(settings: Settings) -> AsyncIterator[PanelClient]:
    """Convenience async context manager for a PanelClient."""
    client = PanelClient(settings)
    try:
        yield client
    finally:
        await client.aclose()
