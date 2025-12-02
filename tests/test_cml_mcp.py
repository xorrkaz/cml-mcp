import pytest
import pprint
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport
from inline_snapshot import snapshot, outsource
from mcp.types import TextContent

from cml_mcp.schemas.annotations import EllipseAnnotation, LineAnnotation, RectangleAnnotation, TextAnnotation
from cml_mcp.schemas.common import DefinitionID, UserName, UUID4Type
from cml_mcp.schemas.groups import GroupCreate, GroupInfoResponse
from cml_mcp.schemas.interfaces import InterfaceCreate
from cml_mcp.schemas.labs import Lab, LabCreate, LabTitle

from cml_mcp.schemas.links import Link, LinkConditionConfiguration, LinkCreate
from cml_mcp.schemas.node_definitions import NodeDefinition
from cml_mcp.schemas.nodes import Node, NodeConfigurationContent, NodeCreate, NodeLabel
from cml_mcp.schemas.system import SystemHealth, SystemInformation, SystemStats
from cml_mcp.schemas.topologies import Topology
from cml_mcp.schemas.users import UserCreate, UserResponse
from cml_mcp.server import server_mcp
from cml_mcp.types import ConsoleLogOutput, SimplifiedInterfaceResponse, SuperSimplifiedNodeDefinitionResponse


@pytest.fixture()
async def main_mcp_client():
    async with Client(transport=server_mcp) as mcp_client:
        yield mcp_client


async def test_list_tools(main_mcp_client: Client[FastMCPTransport]):
    list_tools = await main_mcp_client.list_tools()

    assert len(list_tools) == snapshot(39)


async def test_get_cml_labs(main_mcp_client: Client[FastMCPTransport]):
    result = await main_mcp_client.call_tool(name="get_cml_labs", arguments={})
    # outsource(result.data, ".json")

    assert isinstance(result.data, list)
    assert len(result.data) > 0
    for lab in result.data:
        if isinstance(lab, dict):
            lab = Lab(**lab)
        assert isinstance(lab, Lab)


async def test_get_cml_users(main_mcp_client: Client[FastMCPTransport]):
    result = await main_mcp_client.call_tool(name="get_cml_users", arguments={})
    # outsource(result.data, ".json")

    assert isinstance(result.data, list)
    assert len(result.data) > 0
    for user in result.data:
        if isinstance(user, dict):
            user = UserResponse(**user)
        assert isinstance(user, UserResponse)


async def test_user_mgmt(main_mcp_client: Client[FastMCPTransport]):
    user_create = UserCreate(
        username=UserName("mcp_test_user"),
        password="TestPassword123!",
    )
    result = await main_mcp_client.call_tool(name="create_cml_user", arguments={"user": user_create})
    assert isinstance(result.content, list)
    assert len(result.content) > 0
    assert isinstance(result.content[0], TextContent)
    user_id = UUID4Type(result.content[0].text)
    del_result = await main_mcp_client.call_tool(name="delete_cml_user", arguments={"user_id": user_id})
    assert del_result.data is True

    user_create = {"username": "mcp_test_user2", "password": "TestPassword123!"}
    result = await main_mcp_client.call_tool(name="create_cml_user", arguments={"user": user_create})
    assert isinstance(result.content, list)
    assert len(result.content) > 0
    assert isinstance(result.content[0], TextContent)
    user_id = UUID4Type(result.content[0].text)
    del_result = await main_mcp_client.call_tool(name="delete_cml_user", arguments={"user_id": user_id})
    assert del_result.data is True


async def test_get_cml_groups(main_mcp_client: Client[FastMCPTransport]):
    result = await main_mcp_client.call_tool(name="get_cml_groups", arguments={})
    # outsource(result.data, ".json")

    assert isinstance(result.data, list)
    assert len(result.data) > 0
    for group in result.data:
        if isinstance(group, dict):
            group = GroupInfoResponse(**group)
        assert isinstance(group, GroupInfoResponse)


async def test_group_mgmt(main_mcp_client: Client[FastMCPTransport]):
    group_create = GroupCreate(
        name="mcp_test_group",
        description="Test group created by MCP tests",
    )
    result = await main_mcp_client.call_tool(name="create_cml_group", arguments={"group": group_create})
    assert isinstance(result.content, list)
    assert len(result.content) > 0
    assert isinstance(result.content[0], TextContent)
    group_id = UUID4Type(result.content[0].text)
    del_result = await main_mcp_client.call_tool(name="delete_cml_group", arguments={"group_id": group_id})
    assert del_result.data is True

    group_create = {"name": "mcp_test_group2", "description": "Test group created by MCP tests"}
    result = await main_mcp_client.call_tool(name="create_cml_group", arguments={"group": group_create})
    assert isinstance(result.content, list)
    assert len(result.content) > 0
    assert isinstance(result.content[0], TextContent)
    group_id = UUID4Type(result.content[0].text)
    del_result = await main_mcp_client.call_tool(name="delete_cml_group", arguments={"group_id": group_id})
    assert del_result.data is True


async def test_get_cml_information(main_mcp_client: Client[FastMCPTransport]):
    result = await main_mcp_client.call_tool(name="get_cml_information", arguments={})
    # outsource(result.structured_content, ".json")

    if isinstance(result.structured_content, dict):
        result.structured_content = SystemInformation(**result.structured_content)
    assert isinstance(result.structured_content, SystemInformation)


async def test_get_cml_status(main_mcp_client: Client[FastMCPTransport]):
    result = await main_mcp_client.call_tool(name="get_cml_status", arguments={})
    # outsource(result.structured_content, ".json")

    if isinstance(result.structured_content, dict):
        result.structured_content = SystemHealth(**result.structured_content)
    assert isinstance(result.structured_content, SystemHealth)


async def test_get_cml_statistics(main_mcp_client: Client[FastMCPTransport]):
    result = await main_mcp_client.call_tool(name="get_cml_statistics", arguments={})
    outsource(result.structured_content, ".json")

    if isinstance(result.structured_content, dict):
        result.structured_content = SystemStats(**result.structured_content)
    assert isinstance(result.structured_content, SystemStats)


async def test_get_cml_licensing_details(main_mcp_client: Client[FastMCPTransport]):
    result = await main_mcp_client.call_tool(name="get_cml_licensing_details", arguments={})
    outsource(result.structured_content, ".json")

    assert isinstance(result.structured_content, dict)


async def test_node_defs(main_mcp_client: Client[FastMCPTransport]):
    result = await main_mcp_client.call_tool(name="get_cml_node_definitions", arguments={})
    outsource(result.data, ".json")

    assert isinstance(result.data, list)
    assert len(result.data) > 0
    for i, node_def in enumerate(result.data):
        if isinstance(node_def, dict):
            node_def = SuperSimplifiedNodeDefinitionResponse(**node_def)
        assert isinstance(node_def, SuperSimplifiedNodeDefinitionResponse)
        nd_result = await main_mcp_client.call_tool(name="get_node_definition_detail", arguments={"did": DefinitionID(node_def.id)})
        if i == 0:
            outsource(nd_result.structured_content, ".json")
        if isinstance(nd_result.structured_content, dict):
            nd_result.structured_content = NodeDefinition(**nd_result.structured_content)
        assert isinstance(nd_result.structured_content, NodeDefinition)


async def test_empty_lab_mgmt(main_mcp_client: Client[FastMCPTransport]):
    title = LabTitle("MCP Test Lab")
    lab_create = LabCreate(
        title=title,
        description="This is a test lab created by MCP tests",
        notes="Some _markdown_ notes for the lab.",
    )
    result = await main_mcp_client.call_tool(name="create_empty_cml_lab", arguments={"lab": lab_create})
    assert isinstance(result.content, list)
    assert len(result.content) > 0
    assert isinstance(result.content[0], TextContent)
    lab_id = UUID4Type(result.content[0].text)

    # Fetch the lab details
    lab_result = await main_mcp_client.call_tool(name="get_cml_lab_by_title", arguments={"title": title})
    outsource(lab_result.structured_content, ".json")
    if isinstance(lab_result.structured_content, dict):
        lab_result.structured_content = Lab(**lab_result.structured_content)
    assert isinstance(lab_result.structured_content, Lab)
    assert lab_result.structured_content.id == lab_id

    # Delete the lab
    # This also tests stopping and wiping the lab.
    del_result = await main_mcp_client.call_tool(name="delete_cml_lab", arguments={"lid": lab_id})
    assert del_result.data is True
