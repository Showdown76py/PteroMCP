"""Unit tests for the async PanelClient using respx for HTTP mocking."""

from __future__ import annotations

import httpx
import pytest
import respx

from pteromcp.client import PanelClient
from pteromcp.config import Settings
from pteromcp.errors import PanelHTTPError, ReadOnlyError


def _settings(**kw) -> Settings:
    defaults: dict[str, object] = {
        "panel_url": "https://panel.example.test",
        "application_key": "papp_test",
        "client_key": "ptlc_test",
    }
    defaults.update(kw)
    return Settings(**defaults)  # type: ignore[arg-type]


@respx.mock
async def test_get_request_returns_dict_payload() -> None:
    respx.get("https://panel.example.test/api/application/users").mock(
        return_value=httpx.Response(200, json={"object": "list", "data": []})
    )
    async with PanelClient(_settings()) as c:
        result = await c.get("/users")
    assert result == {"object": "list", "data": []}


@respx.mock
async def test_authorization_header_used() -> None:
    route = respx.get("https://panel.example.test/api/application/users").mock(
        return_value=httpx.Response(200, json={"object": "list", "data": []})
    )
    async with PanelClient(_settings()) as c:
        await c.get("/users")
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer papp_test"
    assert request.headers["Accept"] == "application/json"


@respx.mock
async def test_client_surface_uses_client_key() -> None:
    route = respx.get("https://panel.example.test/api/client/account").mock(
        return_value=httpx.Response(200, json={"attributes": {"id": 1}})
    )
    async with PanelClient(_settings()) as c:
        await c.get("/account", surface="client")
    assert route.calls.last.request.headers["Authorization"] == "Bearer ptlc_test"


@respx.mock
async def test_non_2xx_raises_panel_http_error() -> None:
    respx.get("https://panel.example.test/api/application/nope").mock(
        return_value=httpx.Response(
            404,
            json={"errors": [{"code": "NotFoundHttpException", "detail": "missing"}]},
        )
    )
    async with PanelClient(_settings()) as c:
        with pytest.raises(PanelHTTPError) as info:
            await c.get("/nope")
    err = info.value
    assert err.status_code == 404
    assert "NotFoundHttpException" in str(err)


@respx.mock
async def test_empty_body_returns_none_on_success() -> None:
    respx.delete("https://panel.example.test/api/application/users/1").mock(
        return_value=httpx.Response(204)
    )
    async with PanelClient(_settings()) as c:
        result = await c.delete("/users/1")
    assert result is None


async def test_read_only_blocks_post() -> None:
    async with PanelClient(_settings(read_only=True)) as c:
        with pytest.raises(ReadOnlyError):
            await c.post("/users", json={"x": 1})


@respx.mock
async def test_detect_pelican_when_locations_404() -> None:
    respx.get("https://panel.example.test/api/application/locations").mock(
        return_value=httpx.Response(
            404, json={"errors": [{"code": "NotFoundHttpException"}]}
        )
    )
    async with PanelClient(_settings()) as c:
        kind = await c.detect_panel_type()
    assert kind == "pelican"


@respx.mock
async def test_detect_pterodactyl_when_locations_ok() -> None:
    respx.get("https://panel.example.test/api/application/locations").mock(
        return_value=httpx.Response(200, json={"object": "list", "data": []})
    )
    async with PanelClient(_settings()) as c:
        kind = await c.detect_panel_type()
    assert kind == "pterodactyl"


@respx.mock
async def test_detection_cached() -> None:
    route = respx.get("https://panel.example.test/api/application/locations").mock(
        return_value=httpx.Response(200, json={"data": []})
    )
    async with PanelClient(_settings()) as c:
        await c.detect_panel_type()
        await c.detect_panel_type()
    assert route.call_count == 1


@respx.mock
async def test_list_all_walks_pages() -> None:
    pages = {
        1: {
            "object": "list",
            "data": [{"id": 1}],
            "meta": {"pagination": {"total_pages": 2, "current_page": 1}},
        },
        2: {
            "object": "list",
            "data": [{"id": 2}],
            "meta": {"pagination": {"total_pages": 2, "current_page": 2}},
        },
    }

    def respond(request: httpx.Request) -> httpx.Response:
        page = int(dict(request.url.params).get("page", "1"))
        return httpx.Response(200, json=pages[page])

    respx.get("https://panel.example.test/api/application/users").mock(side_effect=respond)
    async with PanelClient(_settings()) as c:
        items = await c.list_all("/users")
    assert [i["id"] for i in items] == [1, 2]


@respx.mock
async def test_clean_params_drops_none_and_serialises_bool() -> None:
    route = respx.get("https://panel.example.test/api/application/users").mock(
        return_value=httpx.Response(200, json={"object": "list", "data": []})
    )
    async with PanelClient(_settings()) as c:
        await c.get("/users", params={"keep": "x", "drop": None, "flag": True})
    sent = dict(route.calls.last.request.url.params)
    assert sent == {"keep": "x", "flag": "true"}
