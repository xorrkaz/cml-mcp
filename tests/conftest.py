"""
pytest configuration and fixtures for CML MCP tests.

This module provides fixtures for both mock and live testing modes.
Set the USE_MOCKS environment variable to control the behavior:
- USE_MOCKS=true (default): Use mock data from tests/mocks/
- USE_MOCKS=false: Run against a live CML server
"""

import base64
import json
import os
from pathlib import Path
from typing import Any, AsyncGenerator

import httpx
import pytest
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport
from mcp.types import TextContent

from cml_mcp.cml.simple_webserver.schemas.common import UUID4Type
from cml_mcp.cml.simple_webserver.schemas.labs import LabRequest, LabTitle
from cml_mcp.settings import settings

COMMON_TEST_LAB_TITLE = LabTitle("MCP Test Lab")

# Determine if we should use mocks
USE_MOCKS = os.getenv("USE_MOCKS", "true").lower() == "true"
MOCKS_DIR = Path(__file__).parent / "mocks"


class MockHTTPXResponse:
    """Mock httpx.Response for simulating API responses."""

    def __init__(self, json_data: Any, status_code: int = 200):
        self._json_data = json_data
        self.status_code = status_code
        self.text = json.dumps(json_data) if not isinstance(json_data, str) else json_data

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            from httpx import HTTPStatusError, Request, Response

            request = Request("GET", "http://test")
            response = Response(self.status_code, request=request)
            raise HTTPStatusError("Error", request=request, response=response)


class MockCMLClient:
    """Mock CML client that returns data from JSON files."""

    def __init__(self):
        self.mocks_dir = MOCKS_DIR
        self._created_resources = {
            "labs": {},
            "nodes": {},
            "users": {},
            "groups": {},
            "interfaces": {},
            "links": {},
            "annotations": {},
            "packet_captures": {},
        }
        self._next_id = 1000

    def _generate_id(self) -> str:
        """Generate a unique ID for created resources."""
        import uuid

        return str(uuid.uuid4())

    def _load_mock_file(self, filename: str) -> Any:
        """Load mock data from a JSON file."""
        filepath = self.mocks_dir / filename
        if filepath.exists():
            with open(filepath) as f:
                return json.load(f)
        return None

    async def get(self, endpoint: str, params: dict | None = None, is_binary: bool = False) -> Any:
        """Mock GET request handler."""
        # Map endpoints to mock files
        endpoint_map = {
            "/labs": "get_labs.json",
            "/users": "get_users.json",
            "/groups": "get_groups.json",
            "/system_information": "get_cml_info.json",
            "/system_stats": "get_cml_statistics.json",
            "/system_health": "get_cml_status.json",
            "/licensing": "get_cml_licensing_details.json",
            "/node_definitions": "get_node_defs.json",
            "/simplified_node_definitions": "get_node_defs.json",
        }

        # Handle specific patterns
        if endpoint in endpoint_map:
            data = self._load_mock_file(endpoint_map[endpoint])
            if data is not None:
                # Special handling for /labs endpoint
                if endpoint == "/labs" and params and params.get("show_all"):
                    # Return just the list of lab IDs
                    return [lab["id"] for lab in data]
                return data

        # Handle lab-specific endpoints
        if "/labs/" in endpoint:
            parts = endpoint.split("/")
            lab_id = parts[2] if len(parts) > 2 else None

            if endpoint.endswith("/nodes"):
                return self._load_mock_file("get_nodes_for_cml_lab.json") or []
            elif endpoint.endswith("/links"):
                return self._load_mock_file("get_all_links_for_lab.json") or []
            elif endpoint.endswith("/annotations"):
                return self._load_mock_file("get_annotations_for_cml_lab.json") or []
            elif endpoint.endswith("/download"):
                # Handle lab topology download
                # Returns bytes (YAML) when is_binary=True, matching real CML API behavior
                data = self._load_mock_file("download_lab_topology.json") or {}
                if is_binary:
                    import yaml

                    return yaml.dump(data).encode("utf-8")
                return data
            elif "/nodes/" in endpoint and endpoint.endswith("/interfaces"):
                return self._load_mock_file("get_interfaces_for_node.json") or []
            elif "/links/" in endpoint and "/capture/status" in endpoint:
                # Handle packet capture status check
                return self._load_mock_file("check_packet_capture_status.json") or {}
            elif "/links/" in endpoint and "/capture/key" in endpoint:
                # Return a mock capture key
                return "3464b046-c8ab-4624-af57-4bfc66429139"
            elif len(parts) == 3:
                # /labs/{lab_id} - return individual lab details
                # Load all labs and find the matching one
                labs_data = self._load_mock_file("get_labs.json")
                if labs_data:
                    for lab in labs_data:
                        if lab.get("id") == lab_id:
                            return lab
                # If lab not found or no params match, return first lab
                return labs_data[0] if labs_data else {}

        # Handle node definition details
        if "/node_definitions/" in endpoint:
            return self._load_mock_file("get_node_def_detail.json")

        # Handle lab title lookup
        if "/populate?title=" in endpoint:
            return self._load_mock_file("get_cml_lab_by_title.json")

        # Handle pcap endpoints
        if "/pcap/" in endpoint and "/packets" in endpoint:
            # Get captured packet overview
            return self._load_mock_file("get_captured_packet_overview.json") or []
        elif "/pcap/" in endpoint:
            # Get full packet capture data (binary)
            # Return empty bytes for now
            return b""

        # Return empty response for unknown endpoints
        return {}

    async def post(self, endpoint: str, data: dict | None = None, params: dict | None = None) -> Any | None:
        """Mock POST request handler."""
        # Handle create operations
        if endpoint == "/labs":
            lab_id = self._generate_id()
            self._created_resources["labs"][lab_id] = data
            return {"id": lab_id}

        if endpoint == "/import":
            # Handle lab topology import (used by clone_cml_lab)
            lab_id = self._generate_id()
            self._created_resources["labs"][lab_id] = data
            return {"id": lab_id}

        if "/labs/" in endpoint:
            if endpoint.endswith("/nodes"):
                node_id = self._generate_id()
                self._created_resources["nodes"][node_id] = data
                return {"id": node_id}
            elif endpoint.endswith("/interfaces"):
                intf_id = self._generate_id()
                self._created_resources["interfaces"][intf_id] = data
                return intf_id
            elif endpoint.endswith("/links"):
                link_id = self._generate_id()
                self._created_resources["links"][link_id] = data
                return link_id
            elif endpoint.endswith("/annotations"):
                annotation_id = self._generate_id()
                self._created_resources["annotations"][annotation_id] = data
                return annotation_id
            elif endpoint.endswith("/start"):
                return None
            elif endpoint.endswith("/stop"):
                return None
            elif endpoint.endswith("/wipe"):
                return None

        if endpoint == "/users":
            user_id = self._generate_id()
            self._created_resources["users"][user_id] = data
            return user_id

        if endpoint == "/groups":
            group_id = self._generate_id()
            self._created_resources["groups"][group_id] = data
            return group_id

        # Default response
        return None

    async def put(self, endpoint: str, data: dict | None = None) -> Any | None:
        """Mock PUT request handler."""
        # Handle update operations
        if "/labs/" in endpoint:
            if "/capture/start" in endpoint:
                # Start packet capture
                return None
            elif "/capture/stop" in endpoint:
                # Stop packet capture
                return None
            elif "/lab" in endpoint:
                # Update lab
                return None
            elif "/link_conditions" in endpoint:
                # Apply link conditioning
                return None
            elif "/nodes/" in endpoint and "/configuration" in endpoint:
                # Update node configuration
                return None

        # Default response
        return None

    async def patch(self, endpoint: str, data: dict | None = None) -> Any | None:
        """Mock PATCH request handler."""
        # Handle patch operations
        return None

    async def delete(self, endpoint: str) -> dict | None:
        """Mock DELETE request handler."""
        # Handle delete operations
        if "/labs/" in endpoint:
            parts = endpoint.split("/")
            if len(parts) >= 3:
                lab_id = parts[2]
                self._created_resources["labs"].pop(lab_id, None)
        elif "/users/" in endpoint:
            parts = endpoint.split("/")
            if len(parts) >= 3:
                user_id = parts[2]
                self._created_resources["users"].pop(user_id, None)
        elif "/groups/" in endpoint:
            parts = endpoint.split("/")
            if len(parts) >= 3:
                group_id = parts[2]
                self._created_resources["groups"].pop(group_id, None)

        return None

    async def login(self) -> None:
        """Mock login - no-op."""
        pass

    async def check_authentication(self) -> None:
        """Mock authentication check - no-op."""
        pass

    async def is_admin(self) -> bool:
        """Mock admin check - always return True for testing."""
        return True

    async def close(self) -> None:
        """Mock close - no-op."""
        pass


# Monkey-patch at module load time if using mocks
if USE_MOCKS:
    # We need to patch BEFORE server.py gets imported
    # Import cml_client module first
    import cml_mcp.cml_client

    # Store the original class
    _original_cml_client_class = cml_mcp.cml_client.CMLClient

    # Replace CMLClient constructor
    cml_mcp.cml_client.CMLClient = lambda *args, **kwargs: MockCMLClient()


@pytest.fixture()
async def main_mcp_client():
    """
    Main MCP client fixture for testing.
    Works with both mock and live modes.
    """
    from fastmcp.client import Client

    from cml_mcp.server import server_mcp

    async with Client(transport=server_mcp) as mcp_client:
        yield mcp_client


def custom_httpx_client_factory(
    headers=None,
    *args,
    **kwargs,
):
    """
    Custom httpx client factory.
    standard does not allow to disable ssl verification.
    which affects systems with self-signed certificates.

    basically just ignores any args/kwargs passed by fastMCP while creating
    https client object.

    headers can be passed to this func or directly to mcp client.
    """
    kwargs["verify"] = False
    kwargs["follow_redirects"] = True
    kwargs["headers"] = headers
    return httpx.AsyncClient(*args, **kwargs)


if settings.cml_mcp_remote_server_url:

    @pytest.fixture()
    async def main_mcp_client():
        """
        Main MCP client fixture for testing.
        Works with both mock and live modes.
        """
        creds_bytes = ":".join([settings.cml_username, settings.cml_password]).encode()
        base64_creds = base64.b64encode(creds_bytes).decode()

        headers = {
            "X-Authorization": f"Basic {base64_creds}",
        }

        from fastmcp.client import Client
        from fastmcp.client.transports import StreamableHttpTransport

        remote_server = StreamableHttpTransport(
            url=settings.cml_mcp_remote_server_url,
            headers=headers,
            httpx_client_factory=custom_httpx_client_factory,
        )
        # timeout set to 300 because lab_converge takes time
        async with Client(transport=remote_server, timeout=300) as mcp_client:
            yield mcp_client


def pytest_configure(config):
    """Add custom markers."""
    config.addinivalue_line("markers", "live_only: mark test to run only against live CML server")
    config.addinivalue_line("markers", "mock_only: mark test to run only with mocks")


def pytest_collection_modifyitems(config, items):
    """Skip tests based on USE_MOCKS setting."""
    skip_live = pytest.mark.skip(reason="Skipped in mock mode (USE_MOCKS=true)")
    skip_mock = pytest.mark.skip(reason="Skipped in live mode (USE_MOCKS=false)")

    for item in items:
        if USE_MOCKS and "live_only" in item.keywords:
            item.add_marker(skip_live)
        elif not USE_MOCKS and "mock_only" in item.keywords:
            item.add_marker(skip_mock)


@pytest.fixture
async def created_lab(main_mcp_client: Client[FastMCPTransport]) -> AsyncGenerator[tuple[UUID4Type, LabRequest], None]:
    # --- Setup: create lab ---
    title = COMMON_TEST_LAB_TITLE
    lab_create = LabRequest(
        title=title,
        description="This is a test lab created by MCP tests",
        notes="Some _markdown_ notes for the lab.",
    )

    result = await main_mcp_client.call_tool(
        name="create_empty_lab",
        arguments={"lab": lab_create},
    )

    assert isinstance(result.content, list)
    assert len(result.content) > 0
    assert isinstance(result.content[0], TextContent)

    lab_id = UUID4Type(result.content[0].text)

    yield lab_id, lab_create

    # --- Teardown: delete lab ---
    del_result = await main_mcp_client.call_tool(
        name="delete_cml_lab",
        arguments={"lid": lab_id},
    )
    assert del_result.data is True
