"""Integration tests that hit a real Pterodactyl/Pelican panel.

These tests are skipped unless `PTEROMCP_INTEGRATION_URL` and
`PTEROMCP_INTEGRATION_APPKEY` are set. They are designed to be safe:

* read-only operations on existing data;
* create-then-delete flows for users and node allocations on resources we
  ourselves created during the test.

A unique suffix derived from `os.urandom` keeps every test run namespaced so
parallel runs cannot collide.
"""

from __future__ import annotations

import os
import secrets

import pytest

from pteromcp.client import PanelClient
from pteromcp.config import Settings

pytestmark = pytest.mark.integration


def _make_settings() -> Settings:
    url = os.environ.get("PTEROMCP_INTEGRATION_URL")
    key = os.environ.get("PTEROMCP_INTEGRATION_APPKEY")
    if not (url and key):
        pytest.skip(
            "PTEROMCP_INTEGRATION_URL and PTEROMCP_INTEGRATION_APPKEY must be set "
            "to run integration tests."
        )
    return Settings(  # type: ignore[call-arg]
        panel_url=url,
        application_key=key,
        client_key=os.environ.get("PTEROMCP_INTEGRATION_CLIENTKEY"),
        panel_type="auto",
        timeout=30.0,
    )


def _suffix() -> str:
    return secrets.token_hex(4)


@pytest.fixture()
async def panel():
    async with PanelClient(_make_settings()) as client:
        yield client


async def test_panel_detection(panel: PanelClient) -> None:
    kind = await panel.detect_panel_type()
    assert kind in {"pterodactyl", "pelican"}


async def test_list_users_paginates(panel: PanelClient) -> None:
    payload = await panel.get("/users", params={"per_page": 5, "page": 1})
    assert payload is not None
    assert payload["object"] == "list"
    assert "data" in payload
    assert "meta" in payload


async def test_list_nodes(panel: PanelClient) -> None:
    payload = await panel.get("/nodes")
    assert payload is not None
    assert payload["object"] == "list"


async def test_list_servers_with_include(panel: PanelClient) -> None:
    payload = await panel.get("/servers", params={"per_page": 5, "include": "user,node"})
    assert payload is not None
    assert payload["object"] == "list"
    for item in payload.get("data", []):
        assert "relationships" in item["attributes"], "include= should attach relationships"


async def test_list_eggs(panel: PanelClient) -> None:
    kind = await panel.detect_panel_type()
    path = "/eggs" if kind == "pelican" else "/nests/1/eggs"
    payload = await panel.get(path)
    assert payload is not None
    assert payload["object"] == "list"


async def test_user_create_update_delete_round_trip(panel: PanelClient) -> None:
    suffix = _suffix()
    username = f"pteromcp_test_{suffix}"
    email = f"pteromcp-test-{suffix}@example.invalid"

    created = await panel.post(
        "/users",
        json={
            "email": email,
            "username": username,
            "first_name": "PteroMCP",
            "last_name": "Integration",
            "root_admin": False,
            "language": "en",
            "password": f"PteroMCP-{secrets.token_hex(16)}-pw",
        },
    )
    assert created is not None
    user_id = created["attributes"]["id"]

    try:
        fetched = await panel.get(f"/users/{user_id}")
        assert fetched is not None
        assert fetched["attributes"]["username"] == username

        # Update something observable in the response (username is exposed
        # on every panel flavor; first_name is omitted by Pelican).
        new_username = f"pteromcp_upd_{suffix}"
        updated = await panel.patch(
            f"/users/{user_id}",
            json={
                "email": email,
                "username": new_username,
                "first_name": "PteroMCP",
                "last_name": "Integration",
                "language": "en",
            },
        )
        assert updated is not None
        assert updated["attributes"]["username"] == new_username
    finally:
        await panel.delete(f"/users/{user_id}")


async def test_allocation_create_and_delete_round_trip(panel: PanelClient) -> None:
    """Create an allocation on the first node, then delete it.

    Uses an obscure port in the 35000-35999 range and the loopback IP. We
    immediately delete it to leave the node clean.
    """
    nodes_list = await panel.get("/nodes", params={"per_page": 1})
    assert nodes_list is not None
    nodes = nodes_list.get("data") or []
    if not nodes:
        pytest.skip("Panel has no nodes to test allocations against.")
    node_id = nodes[0]["attributes"]["id"]

    port = 35000 + secrets.randbelow(1000)
    ip = "127.0.0.1"

    await panel.post(
        f"/nodes/{node_id}/allocations",
        json={"ip": ip, "ports": [str(port)]},
    )

    # Pelican returns 204 on success. Find the new allocation by walking pages.
    new_id: int | None = None
    try:
        for item in await panel.list_all(f"/nodes/{node_id}/allocations"):
            attrs = item.get("attributes", {})
            if attrs.get("ip") == ip and attrs.get("port") == port:
                new_id = attrs["id"]
                break
        assert new_id is not None, (
            f"Allocation {ip}:{port} created but not found on node {node_id}"
        )
    finally:
        if new_id is not None:
            await panel.delete(f"/nodes/{node_id}/allocations/{new_id}")


async def test_server_create_and_force_delete(panel: PanelClient) -> None:
    """Create a minimal Minecraft server and immediately force-delete it.

    Gated by `PTEROMCP_INTEGRATION_SERVER_TEST=1` because it triggers a real
    egg install on a wings daemon. `force=True` on delete bypasses daemon
    health checks, ensuring cleanup even if the install never finishes.
    """
    if os.environ.get("PTEROMCP_INTEGRATION_SERVER_TEST") != "1":
        pytest.skip(
            "Set PTEROMCP_INTEGRATION_SERVER_TEST=1 to opt in to the server "
            "create/delete round-trip (triggers a real install)."
        )

    nodes = (await panel.get("/nodes", params={"per_page": 1}) or {}).get("data", [])
    assert nodes, "No node available."
    node_id = nodes[0]["attributes"]["id"]

    # Locate an unassigned allocation.
    allocation_id: int | None = None
    for item in await panel.list_all(f"/nodes/{node_id}/allocations"):
        attrs = item["attributes"]
        if not attrs.get("assigned"):
            allocation_id = attrs["id"]
            break
    if allocation_id is None:
        pytest.skip(f"Node {node_id} has no unassigned allocation.")

    # Pick an admin user as owner.
    users = (await panel.get("/users", params={"per_page": 50}) or {}).get("data", [])
    admin = next(
        (u for u in users if u["attributes"].get("root_admin")), users[0] if users else None
    )
    assert admin, "No user to own the test server."
    owner = admin["attributes"]["id"]

    suffix = _suffix()
    body = {
        "name": f"pteromcp-test-{suffix}",
        "user": owner,
        "egg": 4,  # Vanilla Minecraft Java
        "docker_image": "ghcr.io/pterodactyl/yolks:java_17",
        "startup": "java -Xms128M -Xmx{{SERVER_MEMORY}}M -jar {{SERVER_JARFILE}}",
        "environment": {"SERVER_JARFILE": "server.jar", "VANILLA_VERSION": "latest"},
        "limits": {
            "memory": 512,
            "swap": 0,
            "disk": 512,
            "io": 500,
            "cpu": 0,
            "oom_disabled": True,
        },
        "feature_limits": {"databases": 0, "allocations": 0, "backups": 0},
        "allocation": {"default": allocation_id},
        "skip_scripts": True,
        "start_on_completion": False,
    }
    created = await panel.post("/servers", json=body)
    assert created is not None
    server_id = created["attributes"]["id"]
    try:
        fetched = await panel.get(f"/servers/{server_id}")
        assert fetched is not None
        assert fetched["attributes"]["name"].startswith("pteromcp-test-")
    finally:
        # Force-delete: the daemon may not be reachable from the test machine.
        await panel.delete(f"/servers/{server_id}/force")


async def test_node_configuration_endpoint(panel: PanelClient) -> None:
    nodes_list = await panel.get("/nodes", params={"per_page": 1})
    assert nodes_list is not None
    nodes = nodes_list.get("data") or []
    if not nodes:
        pytest.skip("Panel has no nodes.")
    node_id = nodes[0]["attributes"]["id"]
    config = await panel.get(f"/nodes/{node_id}/configuration")
    assert config is not None
    # Wings config exposes a `uuid` and `api` block.
    assert "uuid" in config
    assert "api" in config
