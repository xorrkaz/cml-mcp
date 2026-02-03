"""
CML MCP Server Tests

These tests can run in two modes:
1. Mock mode (default): Uses mock data from tests/mocks/ directory
   - Set USE_MOCKS=true or leave unset
   - Fast, no CML server required
   - Tests basic functionality and data flow

2. Live mode: Tests against a real CML server
   - Set USE_MOCKS=false
   - Requires CML_URL, CML_USERNAME, CML_PASSWORD environment variables
   - Tests full integration with actual CML API

Usage:
  # Run with mocks (default)
  pytest tests/test_cml_mcp.py

  # Run against live server
  USE_MOCKS=false pytest tests/test_cml_mcp.py

  # Run only tests that work with mocks
  pytest -m "not live_only" tests/test_cml_mcp.py

  # Run only tests that require live server
  pytest -m live_only tests/test_cml_mcp.py
"""

from pathlib import Path

import pytest
import yaml
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport
from inline_snapshot import snapshot  # , outsource
from mcp.types import TextContent

from cml_mcp.cml.simple_webserver.schemas.annotations import (
    EllipseAnnotation,
    EllipseAnnotationResponse,
    LineAnnotation,
    LineAnnotationResponse,
    RectangleAnnotation,
    RectangleAnnotationResponse,
    TextAnnotation,
    TextAnnotationResponse,
)
from cml_mcp.cml.simple_webserver.schemas.common import DefinitionID, UserName, UUID4Type
from cml_mcp.cml.simple_webserver.schemas.groups import GroupCreate, GroupResponse
from cml_mcp.cml.simple_webserver.schemas.interfaces import InterfaceCreate
from cml_mcp.cml.simple_webserver.schemas.labs import Lab, LabTitle
from cml_mcp.cml.simple_webserver.schemas.links import LinkConditionConfiguration, LinkCreate, LinkResponse
from cml_mcp.cml.simple_webserver.schemas.node_definitions import NodeDefinition
from cml_mcp.cml.simple_webserver.schemas.nodes import Node, NodeCreate
from cml_mcp.cml.simple_webserver.schemas.pcap import PCAPItem, PCAPStart, PCAPStatusResponse
from cml_mcp.cml.simple_webserver.schemas.system import SystemHealth, SystemInformation, SystemStats
from cml_mcp.cml.simple_webserver.schemas.topologies import Topology
from cml_mcp.cml.simple_webserver.schemas.users import UserCreate, UserResponse
from cml_mcp.types import SimplifiedInterfaceResponse, SuperSimplifiedNodeDefinitionResponse


async def test_list_tools(main_mcp_client: Client[FastMCPTransport]):
    list_tools = await main_mcp_client.list_tools()

    assert len(list_tools) == snapshot(47)


async def test_get_cml_labs(main_mcp_client: Client[FastMCPTransport], created_lab):
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


@pytest.mark.live_only
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
    # set-up: create group
    group_create = GroupCreate(
        name="mcp_test_group",
        description="Test group created by MCP tests",
    )
    _ = await main_mcp_client.call_tool(name="create_cml_group", arguments={"group": group_create})
    # skip asserts as there should be separate test for this specific call

    result = await main_mcp_client.call_tool(name="get_cml_groups", arguments={})
    # outsource(result.data, ".json")

    assert isinstance(result.data, list)
    assert len(result.data) > 0
    for group in result.data:
        if isinstance(group, dict):
            group = GroupResponse(**group)
        assert isinstance(group, GroupResponse)

    # clean-up
    _ = await main_mcp_client.call_tool(name="delete_cml_group", arguments={"group_id": group.id})


@pytest.mark.live_only
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
    # outsource(result.structured_content, ".json")

    if isinstance(result.structured_content, dict):
        result.structured_content = SystemStats(**result.structured_content)
    assert isinstance(result.structured_content, SystemStats)


async def test_get_cml_licensing_details(main_mcp_client: Client[FastMCPTransport]):
    result = await main_mcp_client.call_tool(name="get_cml_licensing_details", arguments={})
    # outsource(result.structured_content, ".json")

    assert isinstance(result.structured_content, dict)


async def test_node_defs(main_mcp_client: Client[FastMCPTransport]):
    result = await main_mcp_client.call_tool(name="get_cml_node_definitions", arguments={})
    # outsource(result.data, ".json")

    assert isinstance(result.data, list)
    assert len(result.data) > 0
    for i, node_def in enumerate(result.data):
        if isinstance(node_def, dict):
            node_def = SuperSimplifiedNodeDefinitionResponse(**node_def)
        assert isinstance(node_def, SuperSimplifiedNodeDefinitionResponse)
        nd_result = await main_mcp_client.call_tool(name="get_node_definition_detail", arguments={"did": DefinitionID(node_def.id)})
        if i == 0:
            pass
            # outsource(nd_result.structured_content, ".json")
        if isinstance(nd_result.structured_content, dict):
            nd_result.structured_content = NodeDefinition(**nd_result.structured_content)
        assert isinstance(nd_result.structured_content, NodeDefinition)


@pytest.mark.mock_only
async def test_get_annotations_for_cml_lab(main_mcp_client: Client[FastMCPTransport]):
    """
    Test retrieving annotations for a CML lab.
    This test only works in mock mode using get_annotations_for_cml_lab.json.
    For live annotation testing, see test_add_annotation_to_cml_lab.
    """
    # Get labs to extract a lab_id (in mock mode, this returns mock data)
    labs_result = await main_mcp_client.call_tool(name="get_cml_labs", arguments={})
    assert isinstance(labs_result.data, list)
    assert len(labs_result.data) > 0

    # Use the first lab's ID
    lab = labs_result.data[0]
    if isinstance(lab, dict):
        lab = Lab(**lab)
    lab_id = lab.id

    # Retrieve all annotations for the lab
    ann_result = await main_mcp_client.call_tool(
        name="get_annotations_for_cml_lab",
        arguments={"lid": lab_id},
    )
    assert isinstance(ann_result.data, list)
    # In mock mode, we expect 4 annotations from the mock file
    assert len(ann_result.data) == snapshot(4)
    # outsource(ann_result.data, ".json")

    # Validate each annotation type
    annotation_types = {"ellipse", "line", "rectangle", "text"}
    found_types = set()

    for annotation in ann_result.data:
        if isinstance(annotation, dict):
            ann_type = annotation.get("type")
            found_types.add(ann_type)

            # Validate the structure based on type
            if ann_type == "ellipse":
                annotation = EllipseAnnotationResponse(**annotation)
                assert annotation.type == "ellipse"
                assert annotation.x1 == snapshot(150.0)
                assert annotation.y1 == snapshot(150.0)
                assert annotation.rotation == snapshot(15)
            elif ann_type == "line":
                annotation = LineAnnotationResponse(**annotation)
                assert annotation.type == "line"
                assert annotation.line_start == snapshot("arrow")
                assert annotation.line_end == snapshot("circle")
            elif ann_type == "rectangle":
                annotation = RectangleAnnotationResponse(**annotation)
                assert annotation.type == "rectangle"
                assert annotation.border_radius == snapshot(10)
            elif ann_type == "text":
                annotation = TextAnnotationResponse(**annotation)
                assert annotation.type == "text"
                assert annotation.text_content == snapshot("This is a test annotation")
                assert annotation.text_bold is True
                assert annotation.text_italic is False
            else:
                pytest.fail(f"Unknown annotation type: {ann_type}")

    # Verify all annotation types are present in mock data
    assert found_types == annotation_types, f"Expected {annotation_types}, but found {found_types}"


@pytest.mark.mock_only
async def test_packet_capture_operations(main_mcp_client: Client[FastMCPTransport]):
    """
    Test packet capture operations in mock mode.
    This test only works in mock mode using packet capture mock files.
    For live packet capture testing, see test_connect_two_nodes.
    """
    # Get labs to extract a lab_id (in mock mode, this returns mock data)
    labs_result = await main_mcp_client.call_tool(name="get_cml_labs", arguments={})
    assert isinstance(labs_result.data, list)
    assert len(labs_result.data) > 0

    # Use the first lab's ID
    lab = labs_result.data[0]
    if isinstance(lab, dict):
        lab = Lab(**lab)
    lab_id = lab.id

    # Get links for the lab
    links_result = await main_mcp_client.call_tool(
        name="get_all_links_for_lab",
        arguments={"lid": lab_id},
    )
    assert isinstance(links_result.data, list)
    assert len(links_result.data) > 0
    link = links_result.data[0]
    if isinstance(link, dict):
        link = LinkResponse(**link)
    link_id = link.id

    # Start packet capture
    capture_result = await main_mcp_client.call_tool(
        name="start_packet_capture",
        arguments={
            "lid": lab_id,
            "link_id": link_id,
            "pcap": PCAPStart(maxpackets=100, bpfilter="icmp"),
        },
    )
    assert capture_result.data is True

    # Check packet capture status
    pcap_status = await main_mcp_client.call_tool(
        name="check_packet_capture_status",
        arguments={
            "lid": lab_id,
            "link_id": link_id,
        },
    )
    if isinstance(pcap_status.structured_content, dict):
        pcap_status.structured_content = PCAPStatusResponse(**pcap_status.structured_content)
    assert isinstance(pcap_status.structured_content, PCAPStatusResponse)
    assert pcap_status.structured_content.packetscaptured == snapshot(8)
    assert pcap_status.structured_content.config.maxpackets == snapshot(100)
    assert pcap_status.structured_content.config.bpfilter == snapshot("icmp")

    # Stop packet capture
    stop_result = await main_mcp_client.call_tool(
        name="stop_packet_capture",
        arguments={
            "lid": lab_id,
            "link_id": link_id,
        },
    )
    assert stop_result.data is True

    # Get packet overview
    packet_overview = await main_mcp_client.call_tool(
        name="get_captured_packet_overview",
        arguments={
            "lid": lab_id,
            "link_id": link_id,
        },
    )
    assert isinstance(packet_overview.data, list)
    assert len(packet_overview.data) > 0

    # Verify packet structure
    found_icmp = False
    for item in packet_overview.data:
        if isinstance(item, dict):
            item = PCAPItem(**item)
        assert isinstance(item, PCAPItem)
        if item.protocol.lower() == "icmp":
            found_icmp = True
    assert found_icmp is True


@pytest.mark.live_only
async def test_empty_lab_mgmt(main_mcp_client: Client[FastMCPTransport], created_lab):
    lid, lab_create = created_lab
    # Fetch the lab details
    lab_result = await main_mcp_client.call_tool(name="get_cml_lab_by_title", arguments={"title": lab_create.title})

    # outsource(lab_result.structured_content, ".json")
    if isinstance(lab_result.structured_content, dict):
        lab_result.structured_content = Lab(**lab_result.structured_content)
    assert isinstance(lab_result.structured_content, Lab)
    assert lab_result.structured_content.id == lid


@pytest.mark.live_only
async def test_modify_cml_lab(
    main_mcp_client: Client[FastMCPTransport],
    created_lab,
):
    lab_id, lab_create = created_lab
    lab_create.title = LabTitle("MCP Modified Lab Title")
    mod_result = await main_mcp_client.call_tool(name="modify_cml_lab", arguments={"lid": lab_id, "lab": lab_create})

    assert mod_result.data is True


@pytest.mark.live_only
async def test_full_cml_topology(main_mcp_client: Client[FastMCPTransport]):
    topo = Path("tests/input_data/IOL_OSPF_Lab.yaml")
    with topo.open("r") as f:
        topo_data = Topology(**(yaml.safe_load(f)))
    result = await main_mcp_client.call_tool(name="create_full_lab_topology", arguments={"topology": topo_data})
    assert isinstance(result.content, list)
    assert len(result.content) > 0
    assert isinstance(result.content[0], TextContent)
    lab_id = UUID4Type(result.content[0].text)

    # Clean up - delete the lab
    del_result = await main_mcp_client.call_tool(name="delete_cml_lab", arguments={"lid": lab_id})
    assert del_result.data is True


@pytest.mark.live_only
async def test_intf_management(main_mcp_client: Client[FastMCPTransport], created_lab):
    lab_id = created_lab[0]

    node_create = NodeCreate(
        node_definition="iol-xe",
        label="MCP Test Node",
        x=100,
        y=100,
        configuration="hostname MCP-Test-Node\n!end\n",
    )
    node_result = await main_mcp_client.call_tool(name="add_node_to_cml_lab", arguments={"lid": lab_id, "node": node_create})
    assert isinstance(node_result.content, list)
    assert len(node_result.content) > 0
    assert isinstance(node_result.content[0], TextContent)
    node_id = UUID4Type(node_result.content[0].text)

    interface_create = InterfaceCreate(
        node=node_id,
    )
    iface_result = await main_mcp_client.call_tool(
        name="add_interface_to_node",
        arguments={"lid": lab_id, "intf": interface_create},
    )
    assert isinstance(iface_result.content, list)
    assert len(iface_result.content) > 0
    assert isinstance(iface_result.content[0], TextContent)
    _ = UUID4Type(iface_result.content[0].text)

    intf_result = await main_mcp_client.call_tool(
        name="get_interfaces_for_node",
        arguments={"lid": lab_id, "nid": node_id},
    )
    assert isinstance(intf_result.data, list)
    assert len(intf_result.data) == snapshot(6)
    # outsource(intf_result.data, ".json")
    for intf in intf_result.data:
        if isinstance(intf, dict):
            intf = SimplifiedInterfaceResponse(**intf)
        assert isinstance(intf, SimplifiedInterfaceResponse)


@pytest.mark.live_only
async def test_add_annotation_to_cml_lab(
    main_mcp_client: Client[FastMCPTransport],
    created_lab,
):
    lab_id = created_lab[0]

    ellipse_annotation = EllipseAnnotation(
        x1=150,
        y1=150,
        x2=200,
        y2=200,
        border_color="#FF0000",
        thickness=2,
        border_style="4,2",
        rotation=15,
        type="ellipse",
        color="#00FF00",
        z_index=1,
    )
    ellipse_result = await main_mcp_client.call_tool(
        name="add_annotation_to_cml_lab",
        arguments={"lid": lab_id, "annotation": ellipse_annotation},
    )
    assert isinstance(ellipse_result.content, list)
    assert len(ellipse_result.content) > 0
    assert isinstance(ellipse_result.content[0], TextContent)
    _ = UUID4Type(ellipse_result.content[0].text)

    line_annotation = LineAnnotation(
        x1=100,
        y1=100,
        x2=200,
        y2=200,
        color="#0000FF",
        z_index=2,
        type="line",
        thickness=3,
        border_style="",
        border_color="#0000FF",
        line_start="arrow",
        line_end="circle",
    )
    line_result = await main_mcp_client.call_tool(
        name="add_annotation_to_cml_lab",
        arguments={"lid": lab_id, "annotation": line_annotation},
    )
    assert isinstance(line_result.content, list)
    assert len(line_result.content) > 0
    assert isinstance(line_result.content[0], TextContent)
    _ = UUID4Type(line_result.content[0].text)

    rectangle_annotation = RectangleAnnotation(
        x1=200,
        y1=200,
        x2=350,
        y2=275,
        border_color="#FFFF00",
        thickness=4,
        border_style="",
        type="rectangle",
        color="#FF00FF",
        z_index=3,
        border_radius=10,
        rotation=0,
    )
    rectangle_result = await main_mcp_client.call_tool(
        name="add_annotation_to_cml_lab",
        arguments={"lid": lab_id, "annotation": rectangle_annotation},
    )
    assert isinstance(rectangle_result.content, list)
    assert len(rectangle_result.content) > 0
    assert isinstance(rectangle_result.content[0], TextContent)
    _ = UUID4Type(rectangle_result.content[0].text)

    text_annotation = TextAnnotation(
        x1=250,
        y1=250,
        text_content="This is a test annotation",
        color="#00FFFF",
        rotation=0,
        z_index=4,
        type="text",
        text_bold=True,
        text_italic=False,
        text_font="Arial",
        text_size=14,
        text_unit="px",
        thickness=1,
        border_style="2,2",
        border_color="#000000",
    )
    text_result = await main_mcp_client.call_tool(
        name="add_annotation_to_cml_lab",
        arguments={"lid": lab_id, "annotation": text_annotation},
    )
    assert isinstance(text_result.content, list)
    assert len(text_result.content) > 0
    assert isinstance(text_result.content[0], TextContent)
    _ = UUID4Type(text_result.content[0].text)

    # Retrieve all annotations for the lab
    ann_result = await main_mcp_client.call_tool(
        name="get_annotations_for_cml_lab",
        arguments={"lid": lab_id},
    )
    assert isinstance(ann_result.data, list)
    assert len(ann_result.data) == snapshot(4)
    # outsource(ann_result.data, ".json")
    for annotation in ann_result.data:
        if isinstance(annotation, dict):
            ann_type = annotation.get("type")
            if ann_type == "ellipse":
                annotation = EllipseAnnotationResponse(**annotation)
            elif ann_type == "line":
                annotation = LineAnnotationResponse(**annotation)
            elif ann_type == "rectangle":
                annotation = RectangleAnnotationResponse(**annotation)
            elif ann_type == "text":
                annotation = TextAnnotationResponse(**annotation)
            assert annotation.type in {"ellipse", "line", "rectangle", "text"}


@pytest.mark.live_only
async def test_connect_two_nodes(main_mcp_client: Client[FastMCPTransport], created_lab):
    lab_id = created_lab[0]

    node1_create = NodeCreate(
        node_definition="iol-xe",
        label="MCP Test Node 1",
        x=100,
        y=100,
        configuration="hostname MCP-Test-Node-1\ninterface Ethernet0/0\nip address 192.0.2.1 255.255.255.0\nno shut\n!end\n",
    )
    node1_result = await main_mcp_client.call_tool(name="add_node_to_cml_lab", arguments={"lid": lab_id, "node": node1_create})
    assert isinstance(node1_result.content, list)
    assert len(node1_result.content) > 0
    assert isinstance(node1_result.content[0], TextContent)
    node1_id = UUID4Type(node1_result.content[0].text)

    node2_create = NodeCreate(
        node_definition="iol-xe",
        label="MCP Test Node 2",
        x=300,
        y=100,
        configuration="hostname MCP-Test-Node-2\ninterface Ethernet0/0\nip address 192.0.2.2 255.255.255.0\nno shut\n!end\n",
    )
    node2_result = await main_mcp_client.call_tool(name="add_node_to_cml_lab", arguments={"lid": lab_id, "node": node2_create})
    assert isinstance(node2_result.content, list)
    assert len(node2_result.content) > 0
    assert isinstance(node2_result.content[0], TextContent)
    node2_id = UUID4Type(node2_result.content[0].text)

    intf1_result = await main_mcp_client.call_tool(name="get_interfaces_for_node", arguments={"lid": lab_id, "nid": node1_id})
    intf2_result = await main_mcp_client.call_tool(name="get_interfaces_for_node", arguments={"lid": lab_id, "nid": node2_id})
    assert isinstance(intf1_result.data, list)
    assert isinstance(intf2_result.data, list)
    assert len(intf1_result.data) > 1  # Interface index 0 is a loopback and cannot be connected.
    assert len(intf2_result.data) > 1  # Interface index 0 is a loopback and cannot be connected.

    # Interface index 0 is a loopback and cannot be connected.
    link_create = LinkCreate(
        src_int=intf1_result.data[1]["id"],
        dst_int=intf2_result.data[1]["id"],
    )
    link_result = await main_mcp_client.call_tool(name="connect_two_nodes", arguments={"lid": lab_id, "link_info": link_create})
    assert isinstance(link_result.content, list)
    assert len(link_result.content) > 0
    assert isinstance(link_result.content[0], TextContent)
    _ = UUID4Type(link_result.content[0].text)

    link_result = await main_mcp_client.call_tool(
        name="get_all_links_for_lab",
        arguments={"lid": lab_id},
    )
    assert isinstance(link_result.data, list)
    assert len(link_result.data) == snapshot(1)
    # outsource(link_result.data, ".json")
    for link in link_result.data:
        if isinstance(link, dict):
            link = LinkResponse(**link)
        assert isinstance(link, LinkResponse)

    _ = await main_mcp_client.call_tool(
        name="start_cml_lab",
        arguments={"lid": lab_id, "wait_for_convergence": True},
    )

    capture_result = await main_mcp_client.call_tool(
        name="start_packet_capture",
        arguments={
            "lid": lab_id,
            "link_id": LinkResponse(**link_result.data[0]).id,
            "pcap": PCAPStart(maxpackets=100, bpfilter="icmp"),
            # we don't need 100, but we don't want it to stop too early either
        },
    )
    assert capture_result.data is True

    _ = await main_mcp_client.call_tool(
        name="send_cli_command",
        arguments={"lid": lab_id, "label": "MCP Test Node 1", "commands": "ping 192.0.2.2"},
    )

    pcap_status = await main_mcp_client.call_tool(
        name="check_packet_capture_status",
        arguments={
            "lid": lab_id,
            "link_id": LinkResponse(**link_result.data[0]).id,
        },
    )
    # outsource(pcap_status.structured_content, ".json")
    if isinstance(pcap_status.structured_content, dict):
        pcap_status.structured_content = PCAPStatusResponse(**pcap_status.structured_content)
    assert isinstance(pcap_status.structured_content, PCAPStatusResponse)
    assert pcap_status.structured_content.packetscaptured >= 5  # should be at least 5 packets from the ping

    stop_result = await main_mcp_client.call_tool(
        name="stop_packet_capture",
        arguments={
            "lid": lab_id,
            "link_id": LinkResponse(**link_result.data[0]).id,
        },
    )
    assert stop_result.data is True

    packet_overview = await main_mcp_client.call_tool(
        name="get_captured_packet_overview",
        arguments={
            "lid": lab_id,
            "link_id": LinkResponse(**link_result.data[0]).id,
        },
    )
    # outsource(packet_overview.data, ".json")
    assert isinstance(packet_overview.data, list)
    assert len(packet_overview.data) >= 5
    found_icmp = False
    for item in packet_overview.data:
        if isinstance(item, dict):
            item = PCAPItem(**item)
        assert isinstance(item, PCAPItem)
        if item.protocol.lower() == "icmp":
            found_icmp = True
    assert found_icmp is True

    cond_result = await main_mcp_client.call_tool(
        name="apply_link_conditioning",
        arguments={
            "lid": lab_id,
            "link_id": LinkResponse(**link_result.data[0]).id,
            "condition": LinkConditionConfiguration(
                enabled=True,
                bandwidth=1000,
                latency=50,
                loss=0.1,
            ),
        },
    )
    assert cond_result.data is True


@pytest.mark.live_only
async def test_get_nodes_for_cml_lab(main_mcp_client: Client[FastMCPTransport], created_lab):
    lab_id = created_lab[0]

    node_create = NodeCreate(
        node_definition="iol-xe",
        label="MCP Test Node",
        x=100,
        y=100,
        configuration="hostname MCP-Test-Node\n!end\n",
    )
    for i in range(3):
        node_create.label = f"MCP Test Node {i + 1}"
        node_result = await main_mcp_client.call_tool(name="add_node_to_cml_lab", arguments={"lid": lab_id, "node": node_create})

        assert isinstance(node_result.content, list)
        assert len(node_result.content) > 0
        assert isinstance(node_result.content[0], TextContent)
        _ = UUID4Type(node_result.content[0].text)

    nodes_result = await main_mcp_client.call_tool(name="get_nodes_for_cml_lab", arguments={"lid": lab_id})
    # outsource(nodes_result.data, ".json")

    assert isinstance(nodes_result.data, list)
    assert len(nodes_result.data) == snapshot(3)
    for node in nodes_result.data:
        if isinstance(node, dict):
            node = Node(**node)
        assert isinstance(node, Node)


@pytest.mark.mock_only
@pytest.mark.asyncio
async def test_download_lab_topology(main_mcp_client, created_lab):
    """Test downloading a lab topology as YAML."""
    lab_id = created_lab[0]

    # Download the lab topology
    download_result = await main_mcp_client.call_tool(name="download_lab_topology", arguments={"lid": lab_id})
    assert isinstance(download_result.content, list)
    assert len(download_result.content) > 0
    assert isinstance(download_result.content[0], TextContent)
    # The result should be a YAML string
    yaml_content = download_result.content[0].text
    assert isinstance(yaml_content, str)
    assert len(yaml_content) > 0


@pytest.mark.mock_only
@pytest.mark.asyncio
async def test_clone_cml_lab(main_mcp_client, created_lab):
    """Test cloning a CML lab with a router node."""
    source_lab_id = created_lab[0]

    # Add a router node to the source lab
    node_create = NodeCreate(
        node_definition="iol-xe",
        label="Test Router",
        x=100,
        y=100,
    )
    node_result = await main_mcp_client.call_tool(name="add_node_to_cml_lab", arguments={"lid": source_lab_id, "node": node_create})
    assert isinstance(node_result.content, list)
    assert len(node_result.content) > 0

    # Clone the lab with a new title
    clone_result = await main_mcp_client.call_tool(name="clone_cml_lab", arguments={"lid": source_lab_id, "new_title": "Cloned Lab"})
    assert isinstance(clone_result.content, list)
    assert len(clone_result.content) > 0
    assert isinstance(clone_result.content[0], TextContent)
    cloned_lab_id = UUID4Type(clone_result.content[0].text)
    assert cloned_lab_id != source_lab_id

    # Clean up - delete clone lab
    del_result = await main_mcp_client.call_tool(name="delete_cml_lab", arguments={"lid": cloned_lab_id})
    assert del_result.data is True


@pytest.mark.live_only
@pytest.mark.asyncio
async def test_download_lab_topology_live(main_mcp_client, created_lab):
    """Test downloading a lab topology as YAML against live CML server."""
    lab_id = created_lab[0]

    # Download the lab topology
    download_result = await main_mcp_client.call_tool(name="download_lab_topology", arguments={"lid": lab_id})
    assert isinstance(download_result.content, list)
    assert len(download_result.content) > 0
    assert isinstance(download_result.content[0], TextContent)
    # The result should be a YAML string
    yaml_content = download_result.content[0].text
    assert isinstance(yaml_content, str)
    assert len(yaml_content) > 0
    # Verify it's valid YAML by parsing it
    import yaml

    parsed = yaml.safe_load(yaml_content)
    assert "lab" in parsed


@pytest.mark.live_only
@pytest.mark.asyncio
async def test_clone_cml_lab_live(main_mcp_client, created_lab):
    """Test cloning a CML lab with a router node against live CML server."""

    source_lab_id = created_lab[0]

    # Add a router node to the source lab
    node_create = NodeCreate(
        node_definition="iol-xe",
        label="Test Router",
        x=100,
        y=100,
    )
    node_result = await main_mcp_client.call_tool(name="add_node_to_cml_lab", arguments={"lid": source_lab_id, "node": node_create})
    assert isinstance(node_result.content, list)
    assert len(node_result.content) > 0

    # Clone the lab with a new title
    clone_result = await main_mcp_client.call_tool(name="clone_cml_lab", arguments={"lid": source_lab_id, "new_title": "Live Cloned Lab"})
    assert isinstance(clone_result.content, list)
    assert len(clone_result.content) > 0
    assert isinstance(clone_result.content[0], TextContent)
    cloned_lab_id = UUID4Type(clone_result.content[0].text)
    assert cloned_lab_id != source_lab_id

    # Verify the cloned lab has the router node
    cloned_nodes = await main_mcp_client.call_tool(name="get_nodes_for_cml_lab", arguments={"lid": cloned_lab_id})
    assert isinstance(cloned_nodes.content, list)
    assert len(cloned_nodes.content) > 0

    # Clean up - delete both labs (source is deleted in fixture)
    del_result = await main_mcp_client.call_tool(name="delete_cml_lab", arguments={"lid": cloned_lab_id})
    assert del_result.data is True
