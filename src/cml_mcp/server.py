# Copyright (c) 2025  Cisco Systems, Inc.
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

import logging
import os
import tempfile
from typing import Any

import httpx
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from mcp.shared.exceptions import McpError
from mcp.types import METHOD_NOT_FOUND
from virl2_client.models.cl_pyats import ClPyats

from cml_mcp.cml_client import CMLClient
from cml_mcp.schemas.annotations import (
    EllipseAnnotation,
    LineAnnotation,
    RectangleAnnotation,
    TextAnnotation,
)
from cml_mcp.schemas.common import DefinitionID, UserName, UUID4Type
from cml_mcp.schemas.interfaces import InterfaceCreate
from cml_mcp.schemas.labs import Lab, LabCreate, LabTitle

# from cml_mcp.schemas.licensing import LicensingStatus
from cml_mcp.schemas.links import Link, LinkConditionConfiguration, LinkCreate
from cml_mcp.schemas.node_definitions import NodeDefinition
from cml_mcp.schemas.nodes import Node, NodeConfigurationContent, NodeCreate, NodeLabel
from cml_mcp.schemas.system import SystemHealth, SystemInformation, SystemStats
from cml_mcp.schemas.topologies import Topology
from cml_mcp.settings import settings
from cml_mcp.types import SuperSimplifiedNodeDefinitionResponse, SimplifiedInterfaceResponse

# Set up logging
loglevel = logging.DEBUG if os.getenv("DEBUG", "false").lower() == "true" else logging.INFO
logging.basicConfig(level=loglevel, format="%(asctime)s %(levelname)s %(threadName)s %(name)s: %(message)s")
logger = logging.getLogger("cml-mcp")


server_mcp = FastMCP(
    "Cisco Modeling Labs (CML)",
    dependencies=["httpx", "fastmcp", "fastapi", "pydantic_strict_partial", "typer", "virl2_client", "pyats[full]"],
    log_level=logging.getLevelName(loglevel),
    debug=loglevel == logging.DEBUG,
)
cml_client = CMLClient(host=str(settings.cml_url), username=settings.cml_username, password=settings.cml_password)


async def get_all_labs() -> list[UUID4Type]:
    """
    Get all labs from the CML server.

    Returns:
        list[UUID4Type]: A list of lab IDs.
    """
    labs = await cml_client.get("/labs", params={"show_all": True})
    return [UUID4Type(lab) for lab in labs]


@server_mcp.tool(
    annotations={
        "title": "Get All CML Labs",
        "readOnlyHint": True,
    }
)
async def get_cml_labs(user: UserName = settings.cml_username) -> list[Lab]:
    """
    Get the list of labs for a specific user or all labs if the user is an admin.
    To get labs for the current user, leave the "user" argument blank.
    """

    # # Clients like to pass "null" as a string vs. null as a None type.
    # if not user or str(user) == "null":
    #     user = settings.cml_username  # Default to the configured username

    try:
        # If the requested user is not the configured user and is not an admin, deny access
        if str(user) != settings.cml_username and not await cml_client.is_admin():
            raise ValueError("User is not an admin and cannot view all labs.")
        ulabs = []
        # Get all labs from the CML server
        labs = await get_all_labs()
        for lab in labs:
            # For each lab, get its details
            lab_details = await cml_client.get(f"/labs/{lab}")
            # Only include labs owned by the specified user
            if lab_details.get("owner_username") == str(user):
                ulabs.append(Lab(**lab_details))
        return ulabs
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error getting CML labs: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(
    annotations={
        "title": "Get CML System Information",
        "readOnlyHint": True,
    }
)
async def get_cml_information() -> SystemInformation:
    """
    Get information about the CML server.
    """
    try:
        info = await cml_client.get("/system_information")
        return SystemInformation(**info)
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error getting CML information: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(
    annotations={
        "title": "Get CML System Health",
        "readOnlyHint": True,
    }
)
async def get_cml_status() -> SystemHealth:
    """
    Get the status of the CML server.
    """
    try:
        status = await cml_client.get("/system_health")
        return SystemHealth(**status)
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error getting CML status: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(
    annotations={
        "title": "Get CML System Statistics",
        "readOnlyHint": True,
    }
)
async def get_cml_statistics() -> SystemStats:
    """
    Get statistics about the CML server.
    """
    try:
        stats = await cml_client.get("/system_stats")
        return SystemStats(**stats)
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error getting CML statistics: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(
    annotations={
        "title": "Get CML License Info",
        "readOnlyHint": True,
    }
)
async def get_cml_licensing_details() -> dict[str, Any]:
    """
    Get licensing details from the CML server.
    """
    try:
        licensing_info = await cml_client.get("/licensing")
        # This is needed because some clients attempt to serialize the response
        # with Python classes for datetime rather than as pure JSON.  Cursor
        # is notably affected whereas Claude Desktop is not.
        return dict(licensing_info)
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error getting CML licensing details: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(
    annotations={
        "title": "Get All CML Node Definitions",
        "readOnlyHint": True,
    }
)
async def get_cml_node_definitions() -> list[SuperSimplifiedNodeDefinitionResponse]:
    """
    Get the list of node definitions from the CML server.
    """
    try:
        node_definitions = await cml_client.get("/simplified_node_definitions")
        return [SuperSimplifiedNodeDefinitionResponse(**nd) for nd in node_definitions]
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error getting CML node definitions: {str(e)}", exc_info=True)
        raise ToolError(e)


async def get_node_def_details(did: DefinitionID) -> NodeDefinition:
    """
    Get detailed information about a specific node definition by its ID.

    Args:
        did (DefinitionID): The node definition ID.

    Returns:
        NodeDefinition: The node definition details.
    """
    node_definition = await cml_client.get(f"/node_definitions/{did}", params={"json": True})
    return NodeDefinition(**node_definition)


@server_mcp.tool(
    annotations={
        "title": "Get Details About a Node Definition",
        "readOnlyHint": True,
    }
)
async def get_node_definition_detail(did: DefinitionID) -> NodeDefinition:
    """
    Get detailed information about a specific node definition by its ID.
    """
    try:
        return await get_node_def_details(did)
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error getting node definition detail for {did}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(
    annotations={
        "title": "Create an Empty Lab",
        "readOnlyHint": False,
        "destructiveHint": False,
    }
)
async def create_empty_lab(lab: LabCreate | dict) -> UUID4Type:
    """Creates an empty lab topology in CML using the provided LabCreate definition.

    The LabCreate schema supports the following fields:

    - title (str, optional): Title of the lab (1-64 characters).
    - owner (str, optional): UUID of the lab owner.
    - description (str, optional): Free-form textual description of the lab (max 4096 characters).
    - notes (str, optional): Additional notes for the lab (max 32768 characters).
    - associations (LabAssociations, optional): Object specifying lab/group and lab/user associations:
        - groups (list[LabGroupAssociation], optional): Each with:
            - id (str): UUID of the group.
            - permissions (list[str]): Permissions for the group ("lab_admin", "lab_edit", "lab_exec", "lab_view").
        - users (list[LabUserAssociation], optional): Each with:
            - id (str): UUID of the user.
            - permissions (list[str]): Permissions for the user ("lab_admin", "lab_edit", "lab_exec", "lab_view").
    """
    try:
        # XXX The dict usage is a workaround for some LLMs that pass a JSON string
        # representation of the argument object.
        if isinstance(lab, dict):
            lab = LabCreate(**lab)
        resp = await cml_client.post("/labs", data=lab.model_dump(mode="json", exclude_none=True))
        return UUID4Type(resp["id"])
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error creating empty lab topology: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(
    annotations={
        "title": "Create a Full Lab Topology",
        "readOnlyHint": False,
        "destructiveHint": False,
    }
)
async def create_full_lab_topology(topology: Topology | dict) -> UUID4Type:
    """
    Create a new, full lab topology in CML using a Topology object.

    The Topology schema allows you to define all aspects of a lab in a single request, including:
      - Lab details: title, description, notes, and schema version.
      - Nodes: each with coordinates, label, node definition, image, RAM, CPU, tags, interfaces, and optional configuration.
      - Interfaces: type, slot, MAC address, label, and node association.
      - Links: connections between interfaces/nodes, with optional label and link conditioning (bandwidth, latency, loss, jitter, etc.).
      - Annotations: visual elements (text, rectangle, ellipse, line) for documentation or highlighting.
      - Smart annotations: advanced grouped/styled annotation objects.

    The Topology object must include at least:
      - lab: LabTopology (with version, title, description, notes)
      - nodes: list of NodeTopology objects (each with id, x, y, label, node_definition, interfaces)
      - links: list of LinkTopology objects (each with id, i1, i2, n1, n2)

    Optional fields:
      - annotations: list of annotation objects (text, rectangle, ellipse, line)
      - smart_annotations: list of SmartAnnotationBase objects
    """
    try:
        # XXX The dict usage is a workaround for some LLMs that pass a JSON string
        # representation of the argument object.
        if isinstance(topology, dict):
            topology = Topology(**topology)
        resp = await cml_client.post("/import", data=topology.model_dump(mode="json", exclude_defaults=True, exclude_none=True))
        return UUID4Type(resp["id"])
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error creating lab topology: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(annotations={"title": "Start a CML Lab", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True})
async def start_cml_lab(lid: UUID4Type) -> bool:
    """
    Start a CML lab by its ID.
    """
    try:
        await cml_client.put(f"/labs/{lid}/start")
        return True
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error starting CML lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


async def stop_lab(lid: UUID4Type) -> None:
    """
    Stop a CML lab by its ID.

    Args:
        lid (UUID4Type): The lab ID.
    """
    await cml_client.put(f"/labs/{lid}/stop")


async def wipe_lab(lid: UUID4Type) -> None:
    """
    Wipe a CML lab by its ID.

    Args:
        lid (UUID4Type): The lab ID.
    """
    await cml_client.put(f"/labs/{lid}/wipe")


@server_mcp.tool(annotations={"title": "Stop a CML Lab", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True})
async def stop_cml_lab(lid: UUID4Type) -> bool:
    """
    Stop a CML lab by its ID.
    """
    try:
        await stop_lab(lid)
        return True
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error stopping CML lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(
    annotations={
        "title": "Wipe a CML Lab",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
    }
)
async def wipe_cml_lab(lid: UUID4Type, ctx: Context) -> bool:
    """
    Wipe a CML lab by its ID.

    Before running this tool make sure to ask the user if they're sure they want to wipe this lab and wait for a response.
    Wiping the lab will remove all the data from all the nodes within the lab.
    """
    try:
        elicit_supported = True
        try:
            result = await ctx.elicit("Are you sure you want to wipe the lab?", response_type=None)
        except McpError as me:
            if me.error.code == METHOD_NOT_FOUND:
                elicit_supported = False
            else:
                raise me
        if not elicit_supported or result.action == "accept":
            await wipe_lab(lid)
            return True
        else:
            raise Exception("Wipe operation cancelled by user.")
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error wiping CML lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(
    annotations={
        "title": "Delete a CML Lab",
        "readOnlyHint": False,
        "destructiveHint": True,
    }
)
async def delete_cml_lab(lid: UUID4Type, ctx: Context) -> bool:
    """
    Delete a CML lab by its ID. If the lab is running and/or not wiped, it will be stopped and wiped first.

    Before running this tool make sure to ask the user if they're sure they want to delete this lab and
    wait for a response.
    """
    try:

        elicit_supported = True
        try:
            result = await ctx.elicit("Are you sure you want to delete the lab?", response_type=None)
        except McpError as me:
            if me.error.code == METHOD_NOT_FOUND:
                elicit_supported = False
            else:
                raise me
        if not elicit_supported or result.action == "accept":
            await stop_lab(lid)  # Ensure the lab is stopped before deletion
            await wipe_lab(lid)  # Ensure the lab is wiped before deletion
            await cml_client.delete(f"/labs/{lid}")
            return True
        else:
            raise Exception("Delete operation cancelled by user.")
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error deleting CML lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


async def add_interface(lid: UUID4Type, intf: InterfaceCreate) -> SimplifiedInterfaceResponse:
    """
    Add an interface to a CML lab by its lab ID.

    Args:
        lid (UUID4Type): The lab ID.
        intf (InterfaceCreate): The interface definition as an InterfaceCreate object.

    Returns:
        InterfaceResponse: The added interface details.
    """
    resp = await cml_client.post(f"/labs/{lid}/interfaces", data=intf.model_dump(mode="json", exclude_none=True))
    return SimplifiedInterfaceResponse(**resp)


@server_mcp.tool(
    annotations={
        "title": "Add a Node to a CML Lab",
        "readOnlyHint": False,
        "destructiveHint": False,
    }
)
async def add_node_to_cml_lab(lid: UUID4Type, node: NodeCreate | dict) -> UUID4Type:
    """
    Adds a node to a CML lab and returns the unique ID of the newly created node.

    The node argument must conform to the NodeCreate schema.

    Upon successful creation, the function also provisions the default number of interfaces for the node,
    as determined by its node definition.

    NodeCreate schema highlights:
        - x (int): X coordinate (-15000 to 15000).
        - y (int): Y coordinate (-15000 to 15000).
        - label (str): Node label (1-128 characters).
        - node_definition (str): Node definition ID (1-250 characters).
        - Optional: image_definition, ram, cpu_limit, data_volume, boot_disk_size, hide_links, tags, cpus, configuration, parameters.
    """
    try:
        # XXX The dict usage is a workaround for some LLMs that pass a JSON string
        # representation of the argument object.
        if isinstance(node, dict):
            node = NodeCreate(**node)
        resp = await cml_client.post(f"/labs/{lid}/nodes", data=node.model_dump(mode="json", exclude_defaults=True))
        # Create the default number of interfaces for the node def.  This is modeled after what happens in the UI.
        try:
            nd = await get_node_def_details(node.node_definition)
            defcount = nd.device.interfaces.default_count
            if not defcount:
                defcount = nd.device.interfaces.min_count
                if not defcount:
                    defcount = 1
            for _ in range(defcount):
                ic = {"node": resp["id"]}
                await add_interface(lid, InterfaceCreate(**ic))
        except Exception as ie:
            logger.error(f"Error adding interfaces for node {resp['id']} in lab {lid}: {str(ie)}", exc_info=True)
        return UUID4Type(resp["id"])
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error adding CML node to lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(
    annotations={
        "title": "Add an Annotation to a CML Lab",
        "readOnlyHint": False,
        "destructiveHint": False,
    }
)
async def add_annotation_to_cml_lab(
    lid: UUID4Type, annotation: EllipseAnnotation | LineAnnotation | RectangleAnnotation | TextAnnotation | dict
) -> UUID4Type:
    """
    Add a visual annotation to a CML lab topology.

    The annotation must be an object that conforms to one of the following schemas:
            TextAnnotation schema:
                - type: "text"
                - x1, y1: Anchor coordinates (-15000 to 15000)
                - rotation: Degrees (0–360)
                - border_color: Border color (e.g., "#FF00FF", "rgba(255,0,0,0.5)", "lightgoldenrodyellow")
                - border_style: Border style ("": solid, "2,2": dotted, "4,2": dashed)
                - color: Fill color
                - thickness: Line thickness (1–32)
                - z_index: Layer (-10240 to 10240)
                - text_content: Text string (max 8192 chars)
                - text_font: Font name (max 128 chars)
                - text_size: Size (1–128)
                - text_unit: Unit ("pt", "px", "em")
                - text_bold: Bold (bool)
                - text_italic: Italic (bool)

            RectangleAnnotation schema:
                - type: "rectangle"
                - x1, y1: Anchor coordinates (-15000 to 15000)
                - x2, y2: Additional coordinates (width/height)
                - rotation: Degrees (0–360)
                - border_color: Border color
                - border_style: Border style
                - color: Fill color
                - thickness: Line thickness (1–32)
                - z_index: Layer (-10240 to 10240)
                - border_radius: Border radius (0–128)

            EllipseAnnotation schema:
                - type: "ellipse"
                - x1, y1: Anchor coordinates (-15000 to 15000)
                - x2, y2: Additional coordinates (width/height/radius)
                - rotation: Degrees (0–360)
                - border_color: Border color
                - border_style: Border style
                - color: Fill color
                - thickness: Line thickness (1–32)
                - z_index: Layer (-10240 to 10240)

            LineAnnotation schema:
                - type: "line"
                - x1, y1: Start coordinates (-15000 to 15000)
                - x2, y2: End coordinates (-15000 to 15000)
                - border_color: Border color
                - border_style: Border style
                - color: Fill color
                - thickness: Line thickness (1–32)
                - z_index: Layer (-10240 to 10240)
                - line_start: Line start style ("arrow", "square", "circle", or null)
                - line_end: Line end style ("arrow", "square", "circle", or null)
    """
    try:
        # XXX The dict usage is a workaround for some LLMs that pass a JSON string
        # representation of the argument object.
        if isinstance(annotation, dict):
            if annotation["type"] == "text":
                annotation = TextAnnotation(**annotation)
            elif annotation["type"] == "rectangle":
                annotation = RectangleAnnotation(**annotation)
            elif annotation["type"] == "ellipse":
                annotation = EllipseAnnotation(**annotation)
            elif annotation["type"] == "line":
                annotation = LineAnnotation(**annotation)
            else:
                raise ValueError(
                    f"Invalid annotation type: {annotation['type']}. Must be one of 'text', 'rectangle', 'ellipse', or 'line'."
                )
        resp = await cml_client.post(f"/labs/{lid}/annotations", data=annotation.model_dump(mode="json", exclude_defaults=True))
        return UUID4Type(resp["id"])
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error adding annotation to lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(
    annotations={
        "title": "Add an Interface to a CML Node",
        "readOnlyHint": False,
        "destructiveHint": False,
    }
)
async def add_interface_to_node(lid: UUID4Type, intf: InterfaceCreate | dict) -> SimplifiedInterfaceResponse:
    """
    Adds a network interface to a node within a CML lab.

    The interface is provided as an `InterfaceCreate` object matching the following schema:

    InterfaceCreate schema:
    - node (str, required): UUID4 of the target node. Example: "90f84e38-a71c-4d57-8d90-00fa8a197385"
    - slot (int, optional): Number of slots (0-128). Default: None.
    - mac_address (str or None, optional): MAC address in Linux format ("00:11:22:33:44:55"). Default: None.
    """
    try:
        # XXX The dict usage is a workaround for some LLMs that pass a JSON string
        # representation of the argument object.
        if isinstance(intf, dict):
            intf = InterfaceCreate(**intf)
        return await add_interface(lid, intf)
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error adding interface to node {intf.node} in lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(
    annotations={
        "title": "Get Interfaces for a CML Node",
        "readOnlyHint": True,
    }
)
async def get_interfaces_for_node(lid: UUID4Type, nid: UUID4Type) -> list[SimplifiedInterfaceResponse]:
    """
    Get a list of interfaces for a specific node in a CML lab by its lab ID and node ID.
    """
    try:
        resp = await cml_client.get(f"/labs/{lid}/nodes/{nid}/interfaces", params={"data": True, "operational": False})
        return [SimplifiedInterfaceResponse(**iface) for iface in resp]
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error getting interfaces for node {nid} in lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(
    annotations={
        "title": "Connect Two Nodes in a CML Lab",
        "readOnlyHint": False,
        "destructiveHint": False,
    }
)
async def connect_two_nodes(lid: UUID4Type, link_info: LinkCreate | dict) -> UUID4Type:
    """
    Creates a link between two interfaces in a CML lab.

    This function establishes a connection between two nodes by creating a link using their interface UUIDs within a specified lab.
    The link is defined by the `link_info` parameter, which must include the source and destination interface UUIDs.

        lid (UUID4Type): The UUID4 identifier of the CML lab where the link will be created.
        link_info (LinkCreate): Details of the link to create. Must include:
            - src_int (str): UUID4 of the source interface.
            - dst_int (str): UUID4 of the destination interface.
    """
    try:
        # XXX The dict usage is a workaround for some LLMs that pass a JSON string
        # representation of the argument object.
        if isinstance(link_info, dict):
            link_info = LinkCreate(**link_info)
        resp = await cml_client.post(f"/labs/{lid}/links", data=link_info.model_dump(mode="json"))
        return UUID4Type(resp["id"])
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error creating link for {link_info}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(
    annotations={
        "title": "Get All Links for a CML Lab",
        "readOnlyHint": True,
    }
)
async def get_all_links_for_lab(lid: UUID4Type) -> list[Link]:
    """
    Get all links for a CML lab by its ID.
    """
    try:
        resp = await cml_client.get(f"/labs/{lid}/links", params={"data": True})
        return [Link(**link) for link in resp]
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error getting links for lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(annotations={"title": "Apply Link Conditioning", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True})
async def apply_link_conditioning(lid: UUID4Type, link_id: UUID4Type, condition: LinkConditionConfiguration | dict) -> bool:
    """
    Apply link conditioning to a specific link within a CML lab.

    This function configures network conditions (such as bandwidth, latency, loss, jitter, etc.) on a link identified by its lab ID
    and link ID.

        lid (UUID4Type): The unique identifier (UUID4) of the CML lab.
        link_id (UUID4Type): The unique identifier (UUID4) of the link within the lab.
        condition (LinkConditionConfiguration): The configuration object specifying link conditioning parameters. Fields include:
            - bandwidth (int | None): Bandwidth in kbps (0–10,000,000).
            - latency (int | None): Delay in ms (0–10,000).
            - delay_corr (float | int | None): Delay correlation in percent (0–100).
            - limit (int | None): Limit in ms (0–10,000).
            - loss (float | int | None): Packet loss in percent (0–100).
            - loss_corr (float | int | None): Loss correlation in percent (0–100).
            - gap (int | None): Gap between packets in ms (0–10,000).
            - duplicate (float | int | None): Probability of duplicate packets in percent (0–100).
            - duplicate_corr (float | int | None): Duplicate correlation in percent (0–100).
            - jitter (int | None): Jitter in ms (0–10,000).
            - reorder_prob (float | int | None): Probability of packet reordering in percent (0–100).
            - reorder_corr (float | int | None): Reorder correlation in percent (0–100).
            - corrupt_prob (float | int | None): Probability of corrupted frames in percent (0–100).
            - corrupt_corr (float | int | None): Corruption correlation in percent (0–100).
            - enabled (bool): Whether conditioning is enabled.
    """
    try:
        # XXX The dict usage is a workaround for some LLMs that pass a JSON string
        # representation of the argument object.
        if isinstance(condition, dict):
            condition = LinkConditionConfiguration(**condition)
        await cml_client.patch(f"/labs/{lid}/links/{link_id}/condition", data=condition.model_dump(mode="json", exclude_none=True))
        return True
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error conditioning link {link_id} in lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(annotations={"title": "Configure a CML Node", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True})
async def configure_cml_node(lid: UUID4Type, nid: UUID4Type, config: NodeConfigurationContent) -> bool:
    """
    Configure a node in a CML lab by its lab ID and node ID. The node must either be newly created or wiped (i.e.,
    in a CREATED state).  For new or wiped nodes, this is more efficient than starting the node and sending CLI
    commands.

    Args:
        lid (UUID4Type): The lab ID.
        nid (UUID4Type): The node ID.
        config (NodeConfigurationContent): A string representing the configuration content for the node.
    """
    payload = {"configuration": str(config)}
    try:
        await cml_client.patch(f"/labs/{lid}/nodes/{nid}", data=payload)
        return True
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error configuring CML node {nid} in lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(annotations={"title": "Get Nodes for a CML Lab", "readOnlyHint": True})
async def get_nodes_for_cml_lab(lid: UUID4Type) -> list[Node]:
    """
    Get a list of nodes for a CML lab by its ID.
    """
    try:
        resp = await cml_client.get(f"/labs/{lid}/nodes", params={"data": True, "operational": True, "exclude_configurations": True})
        rnodes = []
        for node in list(resp):
            # XXX: Fixup known issues with bad data coming from
            # certain node types.
            if node["operational"].get("vnc_key") == "":
                node["operational"]["vnc_key"] = None
            if node["operational"].get("image_definition") == "":
                node["operational"]["image_definition"] = None
            if node["operational"].get("serial_consoles") is None:
                node["operational"]["serial_consoles"] = []
            rnodes.append(Node(**node))
        return rnodes
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error getting nodes for CML lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(annotations={"title": "Get a CML Lab by Title", "readOnlyHint": True})
async def get_cml_lab_by_title(title: LabTitle) -> Lab:
    """
    Get a CML lab by its title.
    """
    try:
        labs = await get_all_labs()
        for lid in labs:
            lab = await cml_client.get(f"/labs/{lid}")
            if lab["lab_title"] == str(title):
                return Lab(**lab)
        raise ValueError(f"Lab with title '{title}' not found.")
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error getting CML lab by title {title}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(annotations={"title": "Stop a CML Node", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True})
async def stop_cml_node(lid: UUID4Type, nid: UUID4Type) -> bool:
    """
    Stop a node in a CML lab by its lab ID and node ID.
    """
    try:
        await cml_client.put(f"/labs/{lid}/nodes/{nid}/state/stop")
        return True
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error stopping CML node {nid} in lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(annotations={"title": "Start a CML Node", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True})
async def start_cml_node(lid: UUID4Type, nid: UUID4Type) -> bool:
    """
    Start a node in a CML lab by its lab ID and node ID.
    """
    try:
        await cml_client.put(f"/labs/{lid}/nodes/{nid}/state/start")
        return True
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error starting CML node {nid} in lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(annotations={"title": "Wipe a CML Node", "readOnlyHint": False, "destructiveHint": True, "idempotentHint": True})
async def wipe_cml_node(lid: UUID4Type, nid: UUID4Type, ctx: Context) -> bool:
    """
    Wipe a node in a CML lab by its lab ID and node ID. Node must be stopped first.

    Before using this tool, make sure to make sure to ask the user if they really
    want to wipe the node and wait for a response.  Wiping the node will remove all data from the node.
    """
    try:
        elicit_supported = True
        try:
            result = await ctx.elicit("Are you sure you want to wipe the node?", response_type=None)
        except McpError as me:
            if me.error.code == METHOD_NOT_FOUND:
                elicit_supported = False
            else:
                raise me
        if not elicit_supported or result.action == "accept":
            await cml_client.put(f"/labs/{lid}/nodes/{nid}/wipe_disks")
            return True
        else:
            raise Exception("Wipe operation cancelled by user.")
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error wiping CML node {nid} in lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(annotations={"title": "Send CLI Command to CML Node", "readOnlyHint": False, "destructiveHint": True})
def send_cli_command(lid: UUID4Type, label: NodeLabel, commands: str, config_command: bool = False) -> str:
    """
    Send CLI command(s) to a node in a CML lab by its lab ID and node label. Nodes must be started and ready
    (i.e., in a BOOTED state) for this to succeed.

    Multiple commands can be sent separated by newlines.

    When config_command is True, provide only configuration commands—do not include commands to enter or exit configuration
    mode (e.g., "configure terminal" or "end"). When config_command is False, only operational/exec commands should be sent;
    configuration commands are not allowed.
    """
    cwd = os.getcwd()  # Save the current working directory
    try:
        os.chdir(tempfile.gettempdir())  # Change to a writable directory (required by pyATS/ClPyats)
        lab = cml_client.vclient.join_existing_lab(str(lid))  # Join the existing lab using the provided lab ID
        pylab = ClPyats(lab)  # Create a ClPyats object for interacting with the lab
        pylab.sync_testbed(settings.cml_username, settings.cml_password)  # Sync the testbed with CML credentials
        if config_command:
            # Send the command as a configuration command
            return pylab.run_config_command(str(label), commands)
        # Send the command as an exec/operational command
        return pylab.run_command(str(label), commands)
    except Exception as e:
        logger.error(f"Error sending CLI command '{commands}' to node {label} in lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)
    finally:
        os.chdir(cwd)  # Restore the original working directory
