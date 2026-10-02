# Copyright (c) 2025-2026  Cisco Systems, Inc.
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.

# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

"""
End-to-end regression tests calling flattened MCP tools with only their required
arguments -- the shape an LLM produces when it simply omits optional kwargs rather
than passing explicit nulls. These run against the mock client (no live CML server
required) because the original bug (field_from() leaking a None-unsafe validator
into the tool's argument schema) is a FastMCP-side validation failure that happens
before any HTTP request is made -- see tests/test_schema_drift.py for the matching
schema-level checks.
"""

from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport
from mcp.types import TextContent

from cml_mcp.cml.simple_webserver.schemas.common import UUID4Type

# Syntactically-valid UUID4 for link/interface ids the mock client doesn't otherwise validate.
_FAKE_UUID = UUID4Type("90f84e38-a71c-4d57-8d90-00fa8a197385")


def _result_uuid(result) -> UUID4Type:
    assert isinstance(result.content, list)
    assert len(result.content) > 0
    assert isinstance(result.content[0], TextContent)
    return UUID4Type(result.content[0].text)


async def test_create_empty_lab_with_no_arguments(main_mcp_client: Client[FastMCPTransport]):
    """Original bug report: create_empty_lab() called with zero arguments must not raise."""
    result = await main_mcp_client.call_tool(name="create_empty_lab", arguments={})
    lab_id = _result_uuid(result)

    del_result = await main_mcp_client.call_tool(name="delete_cml_lab", arguments={"lab_id": lab_id})
    assert del_result.data is True


async def test_modify_cml_lab_with_only_lab_id(main_mcp_client: Client[FastMCPTransport], created_lab: UUID4Type):
    result = await main_mcp_client.call_tool(name="modify_cml_lab", arguments={"lab_id": created_lab})
    assert result.data is True


async def test_set_cml_lab_permissions_with_only_lab_id(main_mcp_client: Client[FastMCPTransport], created_lab: UUID4Type):
    result = await main_mcp_client.call_tool(name="set_cml_lab_permissions", arguments={"lab_id": created_lab})
    assert result.data is True


async def test_add_node_to_cml_lab_with_only_required_args(main_mcp_client: Client[FastMCPTransport], created_lab: UUID4Type):
    result = await main_mcp_client.call_tool(
        name="add_node_to_cml_lab",
        arguments={"lab_id": created_lab, "node_definition": "iol-xe"},
    )
    assert _result_uuid(result)


async def test_start_packet_capture_with_only_required_args(main_mcp_client: Client[FastMCPTransport], created_lab: UUID4Type):
    # maxtime is required by the tool's own "at least one of maxtime/maxpackets" check;
    # bpfilter/encap (optional, OneLineStr-based) are intentionally omitted here.
    result = await main_mcp_client.call_tool(
        name="start_packet_capture",
        arguments={"lab_id": created_lab, "link_id": _FAKE_UUID, "maxtime": 60},
    )
    assert result.data is True


async def test_apply_link_conditioning_with_only_required_args(main_mcp_client: Client[FastMCPTransport], created_lab: UUID4Type):
    result = await main_mcp_client.call_tool(
        name="apply_link_conditioning",
        arguments={"lab_id": created_lab, "link_id": _FAKE_UUID},
    )
    assert result.data is True


async def test_create_cml_user_with_only_required_args(main_mcp_client: Client[FastMCPTransport]):
    result = await main_mcp_client.call_tool(
        name="create_cml_user",
        arguments={"username": "mcp_optional_args_user", "password": "TestPassword123!"},
    )
    user_id = _result_uuid(result)

    del_result = await main_mcp_client.call_tool(name="delete_cml_user", arguments={"user_id": user_id})
    assert del_result.data is True


async def test_create_cml_group_with_only_required_args(main_mcp_client: Client[FastMCPTransport]):
    result = await main_mcp_client.call_tool(name="create_cml_group", arguments={"name": "mcp_optional_args_group"})
    group_id = _result_uuid(result)

    del_result = await main_mcp_client.call_tool(name="delete_cml_group", arguments={"group_id": group_id})
    assert del_result.data is True
