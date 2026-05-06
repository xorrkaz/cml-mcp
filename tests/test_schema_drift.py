"""
Test schema drift detection for flattened MCP tools.

This test validates that each flattened tool's input schema covers all required fields
from the source Pydantic model. When schemas change upstream, this test catches
missing field coverage to prevent silent breakage.
"""

from typing import Annotated

import pytest
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport
from pydantic import BaseModel, TypeAdapter

from cml_mcp.cml.simple_webserver.schemas.annotations import (
    EllipseAnnotation,
    LineAnnotation,
    RectangleAnnotation,
    TextAnnotation,
)
from cml_mcp.cml.simple_webserver.schemas.groups import GroupCreate
from cml_mcp.cml.simple_webserver.schemas.interfaces import InterfaceCreate
from cml_mcp.cml.simple_webserver.schemas.labs import LabAssociations, LabRequest
from cml_mcp.cml.simple_webserver.schemas.links import LinkConditionConfiguration, LinkCreate
from cml_mcp.cml.simple_webserver.schemas.nodes import NodeCreate
from cml_mcp.cml.simple_webserver.schemas.pcap import PCAPStart
from cml_mcp.cml.simple_webserver.schemas.users import UserCreate

# Map flattened tool names to their source Pydantic models
FLAT_TOOL_SCHEMAS: dict[str, type[BaseModel]] = {
    "create_empty_lab": LabRequest,
    "modify_cml_lab": LabRequest,
    "set_cml_lab_permissions": LabAssociations,
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
    LabAssociations: set(),  # Both fields (groups, users) are optional
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


def _flatten_nullable(schema: dict) -> dict:
    """
    Flatten anyOf/nullable JSON Schema into a single dict.

    For schemas like ``{"anyOf": [{"type": "integer", "minimum": 1}, {"type": "null"}]}``,
    merges the non-null branch's keys into the outer dict so constraint keys are always
    accessible at the top level regardless of whether they were emitted at the root or
    inside the anyOf branch.
    """
    merged = {k: v for k, v in schema.items() if k != "anyOf"}
    for branch in schema.get("anyOf", []):
        if isinstance(branch, dict) and branch.get("type") != "null":
            for k, v in branch.items():
                merged.setdefault(k, v)
    return merged


# Constraint keys that must propagate from source FieldInfo to the tool's JSON Schema.
# Description is intentionally excluded: annotation tools use type aliases (e.g. CoordinateFloat,
# AnnotationColor) directly on some params, which carry a type-level description that differs
# from the source field's description -- that is by design, not drift.
_CONSTRAINT_KEYS = frozenset({"minimum", "maximum", "minLength", "maxLength", "pattern"})


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


async def test_constraint_coverage(main_mcp_client: Client[FastMCPTransport]):
    """
    Verify that each flattened tool's parameter JSON Schema carries the same numeric and string
    constraints (minimum/maximum/minLength/maxLength/pattern) as the corresponding source
    Pydantic model field.

    Strategy: for every source-model field that also appears in the tool's inputSchema, build
    the per-field source JSON Schema via ``TypeAdapter(Annotated[field_info.annotation,
    field_info]).json_schema()`` and compare the extracted constraint values against the tool's
    ``inputSchema["properties"][field_name]``.  Optional/nullable ``anyOf`` wrappers are
    unwrapped via ``_flatten_nullable`` before comparison so constraints are always compared at
    the top level regardless of the Pydantic emission style.

    Fields in OMIT_REQUIRED (server-managed / injected) and fields present in the source model
    but not exposed as a tool parameter are skipped -- only the intersection is checked.
    """
    tools = await main_mcp_client.list_tools()
    tool_map = {tool.name: tool for tool in tools}

    failures: list[str] = []
    checked_pairs = 0

    for tool_name, source_model in FLAT_TOOL_SCHEMAS.items():
        if tool_name not in tool_map:
            continue  # test_schema_coverage already flags missing tools

        tool = tool_map[tool_name]
        tool_props = tool.inputSchema.get("properties", {})
        omitted = OMIT_REQUIRED.get(source_model, set())

        for field_name, field_info in source_model.model_fields.items():
            if field_name in omitted or field_name not in tool_props:
                # Intentionally omitted or not directly exposed as a tool param; skip.
                continue

            # Build per-field source JSON Schema via TypeAdapter.
            # Annotated[annotation, field_info] reconstructs exactly what Pydantic would emit
            # for a standalone field carrying these constraints.
            try:
                src_schema = TypeAdapter(Annotated[field_info.annotation, field_info]).json_schema()
            except Exception:
                continue  # unhandleable type (e.g. forward ref); skip gracefully

            src_flat = _flatten_nullable(src_schema)
            src_constraints = {k: v for k, v in src_flat.items() if k in _CONSTRAINT_KEYS}
            if not src_constraints:
                continue  # no numeric / string constraints on this field; nothing to check

            checked_pairs += 1
            tool_flat = _flatten_nullable(tool_props[field_name])

            for key, src_val in src_constraints.items():
                if key not in tool_flat:
                    failures.append(
                        f"Tool '{tool_name}' / param '{field_name}': "
                        f"missing constraint '{key}'\n"
                        f"  source ({source_model.__name__}): {key}={src_val!r}"
                    )
                elif tool_flat[key] != src_val:
                    failures.append(
                        f"Tool '{tool_name}' / param '{field_name}': "
                        f"constraint '{key}' mismatch\n"
                        f"  source ({source_model.__name__}): {src_val!r}\n"
                        f"  tool:   {tool_flat[key]!r}"
                    )

    if failures:
        pytest.fail(f"Constraint drift detected ({checked_pairs} (tool, field) pairs checked):\n\n" + "\n\n".join(failures))
