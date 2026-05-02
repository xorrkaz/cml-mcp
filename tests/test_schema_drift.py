"""
Test schema drift detection for flattened MCP tools.

This test validates that each flattened tool's input schema covers all required fields
from the source Pydantic model. When schemas change upstream, this test catches
missing field coverage to prevent silent breakage.
"""

import pytest
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport
from pydantic import BaseModel

from cml_mcp.cml.simple_webserver.schemas.annotations import (
    EllipseAnnotation,
    LineAnnotation,
    RectangleAnnotation,
    TextAnnotation,
)
from cml_mcp.cml.simple_webserver.schemas.groups import GroupCreate
from cml_mcp.cml.simple_webserver.schemas.interfaces import InterfaceCreate
from cml_mcp.cml.simple_webserver.schemas.labs import LabRequest
from cml_mcp.cml.simple_webserver.schemas.links import LinkConditionConfiguration, LinkCreate
from cml_mcp.cml.simple_webserver.schemas.nodes import NodeCreate
from cml_mcp.cml.simple_webserver.schemas.pcap import PCAPStart
from cml_mcp.cml.simple_webserver.schemas.users import UserCreate

# Map flattened tool names to their source Pydantic models
FLAT_TOOL_SCHEMAS: dict[str, type[BaseModel]] = {
    "create_empty_lab": LabRequest,
    "modify_cml_lab": LabRequest,
    "add_node_to_cml_lab": NodeCreate,
    "add_interface_to_node": InterfaceCreate,
    "connect_two_nodes": LinkCreate,
    "apply_link_conditioning": LinkConditionConfiguration,
    "start_packet_capture": PCAPStart,
    "create_cml_user": UserCreate,
    "create_cml_group": GroupCreate,
    "add_text_annotation": TextAnnotation,
    "add_rectangle_annotation": RectangleAnnotation,
    "add_ellipse_annotation": EllipseAnnotation,
    "add_line_annotation": LineAnnotation,
}

# Server-managed or intentionally-omitted required fields per model
OMIT_REQUIRED: dict[type[BaseModel], set[str]] = {
    LabRequest: set(),  # All required fields exposed
    NodeCreate: set(),  # All required fields exposed
    InterfaceCreate: set(),  # All required fields exposed
    LinkCreate: set(),  # All required fields exposed
    LinkConditionConfiguration: set(),  # All required fields exposed (note: all optional)
    PCAPStart: set(),  # All required fields exposed
    UserCreate: set(),  # All required fields exposed
    GroupCreate: set(),  # All required fields exposed
    TextAnnotation: {"type"},  # Injected by the tool
    RectangleAnnotation: {"type"},  # Injected by the tool
    EllipseAnnotation: {"type"},  # Injected by the tool
    LineAnnotation: {"type"},  # Injected by the tool
}


async def test_schema_coverage(main_mcp_client: Client[FastMCPTransport]):
    """
    Verify that each flattened tool's input schema covers all required fields from its source model.
    """
    tools = await main_mcp_client.list_tools()
    tool_map = {tool.name: tool for tool in tools}

    failures = []

    for tool_name, source_model in FLAT_TOOL_SCHEMAS.items():
        if tool_name not in tool_map:
            failures.append(f"Tool '{tool_name}' not found in registered tools")
            continue

        tool = tool_map[tool_name]
        tool_params = set(tool.inputSchema.get("properties", {}).keys())

        # Get required fields from the source model
        source_required = {name for name, field_info in source_model.model_fields.items() if field_info.is_required()}

        # Remove intentionally-omitted fields
        omitted = OMIT_REQUIRED.get(source_model, set())
        expected_required = source_required - omitted

        # Check that tool params are a superset of expected required fields
        missing_fields = expected_required - tool_params

        if missing_fields:
            failures.append(
                f"Tool '{tool_name}' is missing required fields from {source_model.__name__}: {sorted(missing_fields)}\n"
                f"  Tool params: {sorted(tool_params)}\n"
                f"  Source required: {sorted(source_required)}\n"
                f"  Expected (after omissions): {sorted(expected_required)}"
            )

    if failures:
        pytest.fail("Schema drift detected:\n\n" + "\n\n".join(failures))
