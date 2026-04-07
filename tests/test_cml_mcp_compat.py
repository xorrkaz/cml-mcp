"""
MCP Version Compatibility Tests

Exercises all 48 MCP tools against a live CML server.
Run manually against both 2.9 and 2.10 to verify compatibility:

    pytest --controller-url=https://2.9.server:port packaging/mcp_server/tests/test_mcp_compat.py
    pytest --controller-url=https://2.10.server:port packaging/mcp_server/tests/test_mcp_compat.py
"""

import asyncio
import logging
from pathlib import Path

import pytest
import yaml
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport
from fastmcp.exceptions import ToolError
from mcp.types import TextContent

from cml_mcp.cml.simple_webserver.schemas.annotations import (
    EllipseAnnotation,
    RectangleAnnotation,
    TextAnnotation,
)
from cml_mcp.cml.simple_webserver.schemas.common import UUID4Type
from cml_mcp.cml.simple_webserver.schemas.groups import GroupCreate
from cml_mcp.cml.simple_webserver.schemas.interfaces import InterfaceCreate
from cml_mcp.cml.simple_webserver.schemas.labs import LabRequest, LabTitle
from cml_mcp.cml.simple_webserver.schemas.links import LinkConditionConfiguration, LinkCreate
from cml_mcp.cml.simple_webserver.schemas.nodes import NodeCreate
from cml_mcp.cml.simple_webserver.schemas.pcap import PCAPStart
from cml_mcp.cml.simple_webserver.schemas.topologies import Topology
from cml_mcp.cml.simple_webserver.schemas.users import UserCreate

pytestmark = [pytest.mark.live_only, pytest.mark.slow]

logger = logging.getLogger(__name__)


def _extract_uuid(result) -> UUID4Type:
    assert isinstance(result.content, list) and len(result.content) > 0
    assert isinstance(result.content[0], TextContent)
    return UUID4Type(result.content[0].text)


# ---------------------------------------------------------------------------
# Read-only / standalone tools (no lab needed)
# ---------------------------------------------------------------------------
# Tools: list_tools (meta), get_cml_information, get_cml_status,
#        get_cml_statistics, get_cml_licensing_details,
#        get_cml_users, create_cml_user, delete_cml_user,
#        get_cml_groups, create_cml_group, delete_cml_group,
#        get_cml_node_definitions, get_node_definition_detail


async def test_list_tools(main_mcp_client: Client[FastMCPTransport]):
    """Meta: verify the server exposes tools."""
    tools = await main_mcp_client.list_tools()
    names = {t.name for t in tools}
    assert len(names) >= 40
    assert "get_cml_labs" in names
    assert "create_empty_lab" in names


async def test_system_tools(main_mcp_client: Client[FastMCPTransport]):
    """Tools: get_cml_information, get_cml_status, get_cml_statistics, get_cml_licensing_details."""
    info = await main_mcp_client.call_tool(name="get_cml_information", arguments={})
    assert info.structured_content is not None
    version = info.structured_content.get("version", "unknown")
    logger.info("CML version: %s", version)

    status = await main_mcp_client.call_tool(name="get_cml_status", arguments={})
    assert status.structured_content is not None

    stats = await main_mcp_client.call_tool(name="get_cml_statistics", arguments={})
    assert stats.structured_content is not None

    lic = await main_mcp_client.call_tool(name="get_cml_licensing_details", arguments={})
    assert lic.structured_content is not None


async def test_user_tools(main_mcp_client: Client[FastMCPTransport]):
    """Tools: get_cml_users, create_cml_user, delete_cml_user."""
    users = await main_mcp_client.call_tool(name="get_cml_users", arguments={})
    assert users.data is not None

    user = UserCreate(username="mcp_compat_user", password="CompatTest123!")
    result = await main_mcp_client.call_tool(name="create_cml_user", arguments={"user": user})
    user_id = _extract_uuid(result)

    del_result = await main_mcp_client.call_tool(name="delete_cml_user", arguments={"user_id": user_id})
    assert del_result.data is True


async def test_group_tools(main_mcp_client: Client[FastMCPTransport]):
    """Tools: get_cml_groups, create_cml_group, delete_cml_group."""
    groups = await main_mcp_client.call_tool(name="get_cml_groups", arguments={})
    assert groups.data is not None

    group = GroupCreate(name="mcp_compat_group", description="Compat test group")
    result = await main_mcp_client.call_tool(name="create_cml_group", arguments={"group": group})
    group_id = _extract_uuid(result)

    del_result = await main_mcp_client.call_tool(name="delete_cml_group", arguments={"group_id": group_id})
    assert del_result.data is True


async def test_node_definitions(main_mcp_client: Client[FastMCPTransport]):
    """Tools: get_cml_node_definitions, get_node_definition_detail."""
    defs = await main_mcp_client.call_tool(name="get_cml_node_definitions", arguments={})
    assert isinstance(defs.data, list)
    assert len(defs.data) > 0

    first_def = defs.data[0]
    did = first_def["id"] if isinstance(first_def, dict) else first_def.id
    detail = await main_mcp_client.call_tool(name="get_node_definition_detail", arguments={"did": did})
    assert detail.structured_content is not None


# ---------------------------------------------------------------------------
# Lab lifecycle
# ---------------------------------------------------------------------------
# Tools: create_empty_lab, get_cml_labs, get_cml_lab_by_title,
#        modify_cml_lab, download_lab_topology, clone_cml_lab,
#        create_full_lab_topology, delete_cml_lab


@pytest.fixture()
async def compat_lab(main_mcp_client: Client[FastMCPTransport]):
    """Create an empty lab for compat tests and delete it after."""
    lab_payload = {
        "title": "MCP Compat Lab",
        "description": "Compatibility test lab",
    }
    result = await main_mcp_client.call_tool(name="create_empty_lab", arguments={"lab": lab_payload})
    lab_id = _extract_uuid(result)
    yield lab_id
    await main_mcp_client.call_tool(name="delete_cml_lab", arguments={"lid": lab_id})


async def test_get_labs(main_mcp_client: Client[FastMCPTransport], compat_lab):
    """Tool: get_cml_labs."""
    result = await main_mcp_client.call_tool(name="get_cml_labs", arguments={})
    assert result.data is not None


async def test_get_lab_by_title(main_mcp_client: Client[FastMCPTransport], compat_lab):
    """Tool: get_cml_lab_by_title."""
    result = await main_mcp_client.call_tool(
        name="get_cml_lab_by_title",
        arguments={"title": "MCP Compat Lab"},
    )
    assert result.structured_content is not None


async def test_modify_lab(main_mcp_client: Client[FastMCPTransport], compat_lab):
    """Tool: modify_cml_lab."""
    lab = LabRequest(title=LabTitle("MCP Compat Lab Modified"))
    result = await main_mcp_client.call_tool(
        name="modify_cml_lab",
        arguments={"lid": compat_lab, "lab": lab},
    )
    assert result.data is True
    await main_mcp_client.call_tool(
        name="modify_cml_lab",
        arguments={"lid": compat_lab, "lab": LabRequest(title=LabTitle("MCP Compat Lab"))},
    )


async def test_download_topology(main_mcp_client: Client[FastMCPTransport], compat_lab):
    """Tool: download_lab_topology."""
    result = await main_mcp_client.call_tool(name="download_lab_topology", arguments={"lid": compat_lab})
    assert isinstance(result.content, list)
    assert len(result.content) > 0
    yaml_text = result.content[0].text
    parsed = yaml.safe_load(yaml_text)
    assert "lab" in parsed


async def test_clone_lab(main_mcp_client: Client[FastMCPTransport], compat_lab):
    """Tool: clone_cml_lab (+ delete_cml_lab for cleanup)."""
    result = await main_mcp_client.call_tool(
        name="clone_cml_lab",
        arguments={"lid": compat_lab, "new_title": "MCP Compat Clone"},
    )
    clone_id = _extract_uuid(result)
    del_result = await main_mcp_client.call_tool(name="delete_cml_lab", arguments={"lid": clone_id})
    assert del_result.data is True


async def test_create_full_topology(main_mcp_client: Client[FastMCPTransport]):
    """Tool: create_full_lab_topology (+ delete_cml_lab for cleanup)."""
    topo_path = Path(__file__).parent / "input_data" / "IOL_OSPF_Lab.yaml"
    with topo_path.open() as f:
        topo_data = Topology(**yaml.safe_load(f))
    result = await main_mcp_client.call_tool(name="create_full_lab_topology", arguments={"topology": topo_data})
    lab_id = _extract_uuid(result)

    del_result = await main_mcp_client.call_tool(name="delete_cml_lab", arguments={"lid": lab_id})
    assert del_result.data is True


# ---------------------------------------------------------------------------
# Node lifecycle
# ---------------------------------------------------------------------------
# Tools: add_node_to_cml_lab, get_nodes_for_cml_lab, configure_cml_node,
#        start_cml_node, stop_cml_node, wipe_cml_node, delete_cml_node


async def test_node_lifecycle(main_mcp_client: Client[FastMCPTransport], compat_lab):
    """Tools: add_node, get_nodes, configure, start, stop, wipe, delete."""
    node_create = NodeCreate(
        node_definition="alpine",
        label="Compat Node",
        x=0,
        y=0,
    )
    result = await main_mcp_client.call_tool(
        name="add_node_to_cml_lab",
        arguments={"lid": compat_lab, "node": node_create},
    )
    nid = _extract_uuid(result)

    nodes = await main_mcp_client.call_tool(name="get_nodes_for_cml_lab", arguments={"lid": compat_lab})
    assert isinstance(nodes.data, list)
    assert len(nodes.data) >= 1

    cfg = await main_mcp_client.call_tool(
        name="configure_cml_node",
        arguments={"lid": compat_lab, "nid": nid, "config": "hostname compat-test"},
    )
    assert cfg.data is True

    start = await main_mcp_client.call_tool(
        name="start_cml_node",
        arguments={"lid": compat_lab, "nid": nid, "wait_for_convergence": True},
    )
    assert start.data is True

    stop = await main_mcp_client.call_tool(
        name="stop_cml_node",
        arguments={"lid": compat_lab, "nid": nid},
    )
    assert stop.data is True

    await asyncio.sleep(5)

    wipe = await main_mcp_client.call_tool(
        name="wipe_cml_node",
        arguments={"lid": compat_lab, "nid": nid},
    )
    assert wipe.data is True

    delete = await main_mcp_client.call_tool(
        name="delete_cml_node",
        arguments={"lid": compat_lab, "nid": nid},
    )
    assert delete.data is True


# ---------------------------------------------------------------------------
# Interfaces and links
# ---------------------------------------------------------------------------
# Tools: add_interface_to_node, get_interfaces_for_node,
#        connect_two_nodes, get_all_links_for_lab,
#        start_cml_link, stop_cml_link, apply_link_conditioning


async def test_interface_and_link_mgmt(main_mcp_client: Client[FastMCPTransport], compat_lab):
    """Tools: add_interface, get_interfaces, connect, get_links, start/stop link, link conditioning."""
    node1 = NodeCreate(node_definition="alpine", label="Link Node 1", x=0, y=0)
    node2 = NodeCreate(node_definition="alpine", label="Link Node 2", x=200, y=0)
    n1_result = await main_mcp_client.call_tool(name="add_node_to_cml_lab", arguments={"lid": compat_lab, "node": node1})
    n1_id = _extract_uuid(n1_result)
    n2_result = await main_mcp_client.call_tool(name="add_node_to_cml_lab", arguments={"lid": compat_lab, "node": node2})
    n2_id = _extract_uuid(n2_result)

    intf_create = InterfaceCreate(node=n1_id)
    intf_result = await main_mcp_client.call_tool(
        name="add_interface_to_node",
        arguments={"lid": compat_lab, "intf": intf_create},
    )
    assert intf_result.content is not None or intf_result.structured_content is not None

    intf1 = await main_mcp_client.call_tool(
        name="get_interfaces_for_node",
        arguments={"lid": compat_lab, "nid": n1_id},
    )
    assert isinstance(intf1.data, list)
    assert len(intf1.data) >= 1

    intf2 = await main_mcp_client.call_tool(
        name="get_interfaces_for_node",
        arguments={"lid": compat_lab, "nid": n2_id},
    )
    assert isinstance(intf2.data, list)
    assert len(intf2.data) >= 1

    src_intf_id = intf1.data[0]["id"] if isinstance(intf1.data[0], dict) else intf1.data[0].id
    dst_intf_id = intf2.data[0]["id"] if isinstance(intf2.data[0], dict) else intf2.data[0].id

    link_create = LinkCreate(src_int=src_intf_id, dst_int=dst_intf_id)
    link_result = await main_mcp_client.call_tool(
        name="connect_two_nodes",
        arguments={"lid": compat_lab, "link_info": link_create},
    )
    link_id = _extract_uuid(link_result)

    links = await main_mcp_client.call_tool(name="get_all_links_for_lab", arguments={"lid": compat_lab})
    assert isinstance(links.data, list)
    assert len(links.data) >= 1

    cond = await main_mcp_client.call_tool(
        name="apply_link_conditioning",
        arguments={
            "lid": compat_lab,
            "link_id": link_id,
            "condition": LinkConditionConfiguration(enabled=True, bandwidth=1000, latency=10),
        },
    )
    assert cond.data is True

    await main_mcp_client.call_tool(
        name="start_cml_lab",
        arguments={"lid": compat_lab, "wait_for_convergence": True},
    )

    start_link = await main_mcp_client.call_tool(
        name="start_cml_link",
        arguments={"lid": compat_lab, "link_id": link_id},
    )
    assert start_link.data is True

    stop_link = await main_mcp_client.call_tool(
        name="stop_cml_link",
        arguments={"lid": compat_lab, "link_id": link_id},
    )
    assert stop_link.data is True

    await main_mcp_client.call_tool(
        name="stop_cml_lab",
        arguments={"lid": compat_lab},
    )


# ---------------------------------------------------------------------------
# Annotations
# ---------------------------------------------------------------------------
# Tools: add_annotation_to_cml_lab, get_annotations_for_cml_lab,
#        delete_annotation_from_lab


async def test_annotation_crud(main_mcp_client: Client[FastMCPTransport], compat_lab):
    """Tools: add_annotation, get_annotations, delete_annotation."""
    ellipse = EllipseAnnotation(
        x1=100,
        y1=100,
        x2=200,
        y2=200,
        border_color="#FF0000",
        thickness=2,
        border_style="",
        rotation=0,
        type="ellipse",
        color="#00FF00",
        z_index=1,
    )
    e_result = await main_mcp_client.call_tool(
        name="add_annotation_to_cml_lab",
        arguments={"lid": compat_lab, "annotation": ellipse},
    )
    annotation_id = _extract_uuid(e_result)

    rect = RectangleAnnotation(
        x1=200,
        y1=200,
        x2=300,
        y2=100,
        border_color="#0000FF",
        thickness=2,
        border_style="",
        type="rectangle",
        color="#FFFF00",
        z_index=2,
        border_radius=5,
        rotation=0,
    )
    await main_mcp_client.call_tool(
        name="add_annotation_to_cml_lab",
        arguments={"lid": compat_lab, "annotation": rect},
    )

    text = TextAnnotation(
        x1=300,
        y1=300,
        text_content="Compat Test",
        color="#000000",
        rotation=0,
        z_index=3,
        type="text",
        text_bold=False,
        text_italic=False,
        text_font="Arial",
        text_size=14,
        text_unit="px",
        thickness=1,
        border_style="",
        border_color="#000000",
    )
    await main_mcp_client.call_tool(
        name="add_annotation_to_cml_lab",
        arguments={"lid": compat_lab, "annotation": text},
    )

    anns = await main_mcp_client.call_tool(
        name="get_annotations_for_cml_lab",
        arguments={"lid": compat_lab},
    )
    assert isinstance(anns.data, list)
    assert len(anns.data) >= 3

    del_result = await main_mcp_client.call_tool(
        name="delete_annotation_from_lab",
        arguments={"lid": compat_lab, "annotation_id": annotation_id},
    )
    assert del_result.data is True


# ---------------------------------------------------------------------------
# PCAP and CLI (requires running lab)
# ---------------------------------------------------------------------------
# Tools: start_cml_lab, send_cli_command, get_console_log,
#        start_packet_capture, check_packet_capture_status,
#        stop_packet_capture, get_captured_packet_overview,
#        get_packet_capture_data


async def test_pcap_and_cli(main_mcp_client: Client[FastMCPTransport]):
    """Tools: start_lab, CLI, console log, PCAP lifecycle + data download.

    Creates its own lab with two IOL-XE nodes, starts it, exercises CLI/PCAP,
    then tears down.
    """
    lab_payload = {"title": "MCP Compat PCAP Lab", "description": "PCAP and CLI compat test"}
    lab_result = await main_mcp_client.call_tool(name="create_empty_lab", arguments={"lab": lab_payload})
    lab_id = _extract_uuid(lab_result)

    try:
        n1 = NodeCreate(
            node_definition="iol-xe",
            label="PCAP Node 1",
            x=0,
            y=0,
            configuration="hostname PCAP-Node-1\ninterface Ethernet0/0\nip address 192.0.2.1 255.255.255.0\nno shut\n!end\n",
        )
        n2 = NodeCreate(
            node_definition="iol-xe",
            label="PCAP Node 2",
            x=200,
            y=0,
            configuration="hostname PCAP-Node-2\ninterface Ethernet0/0\nip address 192.0.2.2 255.255.255.0\nno shut\n!end\n",
        )
        n1_id = _extract_uuid(await main_mcp_client.call_tool(name="add_node_to_cml_lab", arguments={"lid": lab_id, "node": n1}))
        n2_id = _extract_uuid(await main_mcp_client.call_tool(name="add_node_to_cml_lab", arguments={"lid": lab_id, "node": n2}))

        intf1 = await main_mcp_client.call_tool(name="get_interfaces_for_node", arguments={"lid": lab_id, "nid": n1_id})
        intf2 = await main_mcp_client.call_tool(name="get_interfaces_for_node", arguments={"lid": lab_id, "nid": n2_id})
        assert len(intf1.data) > 1 and len(intf2.data) > 1

        src_id = intf1.data[1]["id"] if isinstance(intf1.data[1], dict) else intf1.data[1].id
        dst_id = intf2.data[1]["id"] if isinstance(intf2.data[1], dict) else intf2.data[1].id
        link_result = await main_mcp_client.call_tool(
            name="connect_two_nodes",
            arguments={"lid": lab_id, "link_info": LinkCreate(src_int=src_id, dst_int=dst_id)},
        )
        link_id = _extract_uuid(link_result)

        # start_cml_lab (tool #1 in this test)
        start = await main_mcp_client.call_tool(
            name="start_cml_lab",
            arguments={"lid": lab_id, "wait_for_convergence": True},
        )
        assert start.data is True

        # get_console_log
        console = await main_mcp_client.call_tool(
            name="get_console_log",
            arguments={"lid": lab_id, "nid": n1_id},
        )
        assert console.data is not None

        # send_cli_command — may fail on older CML versions where the
        # in-process proxy connection is unavailable.
        try:
            cli = await main_mcp_client.call_tool(
                name="send_cli_command",
                arguments={"lid": lab_id, "label": "PCAP Node 1", "commands": "ping 192.0.2.2"},
            )
            assert isinstance(cli.content, list) and len(cli.content) > 0
        except ToolError as exc:
            if "failed to connect" in str(exc):
                pytest.skip(f"CLI proxy unavailable on this CML version: {exc}")
            raise

        links = await main_mcp_client.call_tool(name="get_all_links_for_lab", arguments={"lid": lab_id})
        link_data = links.data[0]
        actual_link_id = link_data["id"] if isinstance(link_data, dict) else link_data.id

        # start_packet_capture
        pcap_start = await main_mcp_client.call_tool(
            name="start_packet_capture",
            arguments={"lid": lab_id, "link_id": actual_link_id, "pcap": PCAPStart(maxpackets=50, bpfilter="icmp")},
        )
        assert pcap_start.data is True

        await main_mcp_client.call_tool(
            name="send_cli_command",
            arguments={"lid": lab_id, "label": "PCAP Node 1", "commands": "ping 192.0.2.2"},
        )

        # check_packet_capture_status
        pcap_status = await main_mcp_client.call_tool(
            name="check_packet_capture_status",
            arguments={"lid": lab_id, "link_id": actual_link_id},
        )
        assert pcap_status.structured_content is not None

        # stop_packet_capture
        pcap_stop = await main_mcp_client.call_tool(
            name="stop_packet_capture",
            arguments={"lid": lab_id, "link_id": actual_link_id},
        )
        assert pcap_stop.data is True

        # get_captured_packet_overview
        overview = await main_mcp_client.call_tool(
            name="get_captured_packet_overview",
            arguments={"lid": lab_id, "link_id": actual_link_id},
        )
        assert isinstance(overview.data, list)

        # get_packet_capture_data
        pcap_data = await main_mcp_client.call_tool(
            name="get_packet_capture_data",
            arguments={"lid": lab_id, "link_id": actual_link_id},
        )
        assert isinstance(pcap_data.content, list) and len(pcap_data.content) > 0

    finally:
        await main_mcp_client.call_tool(name="delete_cml_lab", arguments={"lid": lab_id})


# ---------------------------------------------------------------------------
# Lab stop / wipe / delete
# ---------------------------------------------------------------------------
# Tools: stop_cml_lab, wipe_cml_lab, delete_cml_lab


async def test_lab_stop_wipe_delete(main_mcp_client: Client[FastMCPTransport]):
    """Tools: start_cml_lab, stop_cml_lab, wipe_cml_lab, delete_cml_lab."""
    lab_payload = {"title": "MCP Compat Lifecycle Lab", "description": "Lab lifecycle test"}
    lab_result = await main_mcp_client.call_tool(name="create_empty_lab", arguments={"lab": lab_payload})
    lab_id = _extract_uuid(lab_result)

    try:
        node = NodeCreate(node_definition="alpine", label="Lifecycle Node", x=0, y=0)
        await main_mcp_client.call_tool(name="add_node_to_cml_lab", arguments={"lid": lab_id, "node": node})

        start = await main_mcp_client.call_tool(
            name="start_cml_lab",
            arguments={"lid": lab_id, "wait_for_convergence": True},
        )
        assert start.data is True

        stop = await main_mcp_client.call_tool(name="stop_cml_lab", arguments={"lid": lab_id})
        assert stop.data is True

        await asyncio.sleep(5)

        wipe = await main_mcp_client.call_tool(name="wipe_cml_lab", arguments={"lid": lab_id})
        assert wipe.data is True

    finally:
        await main_mcp_client.call_tool(name="delete_cml_lab", arguments={"lid": lab_id})
