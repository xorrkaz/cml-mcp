# Copyright (c) 2025-2026  Cisco Systems, Inc.
# All rights reserved.

"""
Interface management tools for CML MCP server.
"""

import logging

import httpx
from fastmcp.exceptions import ToolError

from cml_mcp.cml.simple_webserver.schemas.common import MACAddress, UUID4Type
from cml_mcp.cml.simple_webserver.schemas.interfaces import InterfaceSlot
from cml_mcp.cml_client import CMLClient
from cml_mcp.tools.dependencies import get_cml_client_dep
from cml_mcp.tools.model_helpers import build_payload
from cml_mcp.types import SimplifiedInterfaceResponse

logger = logging.getLogger("cml-mcp.tools.interfaces")


async def add_interface(lab_id: UUID4Type, payload: dict, client: CMLClient) -> SimplifiedInterfaceResponse:
    """
    Add an interface to a CML lab by its lab ID.

    Args:
        lab_id (UUID4Type): The lab ID.
        payload (dict): The interface creation payload.
        client (CMLClient): The CML client instance.

    Returns:
        InterfaceResponse: The added interface details.
    """
    resp = await client.post(f"/labs/{lab_id}/interfaces", data=payload)
    # See DEVELOPMENT.md "Object-typed return values": dump after construction so FastMCP doesn't double-marshal.
    return SimplifiedInterfaceResponse(**resp).model_dump(exclude_unset=True)


def register_tools(mcp):
    """Register all interface-related tools with the FastMCP server."""

    # Source schema: InterfaceCreate (cml/simple_webserver/schemas/interfaces.py)
    # Exposed: node, slot, mac_address
    # Omitted: (none - all fields exposed)
    @mcp.tool(
        annotations={
            "title": "Add an Interface to a CML Node",
            "readOnlyHint": False,
            "destructiveHint": False,
        },
    )
    async def add_interface_to_node(
        lab_id: UUID4Type,
        node: UUID4Type,
        slot: InterfaceSlot | None = None,
        mac_address: MACAddress = None,
    ) -> SimplifiedInterfaceResponse:
        """
        Add a new interface to a node. Returns interface details (id, node, slot, type, MAC).

        Required: lab_id (lab UUID), node (node UUID). Optional: slot (0-128), mac_address (e.g. "00:11:22:33:44:55").

        Examples:
        - "Add a new interface to node R1"
        - "Give the firewall another GigabitEthernet port"
        - "Add interface slot 3 to node xyz"
        """

        client = get_cml_client_dep()
        try:
            payload = build_payload(
                node=str(node),
                slot=slot,
                mac_address=mac_address,
            )
            return await add_interface(lab_id, payload, client)
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error adding interface to node %s in lab %s", node, lab_id)
            raise ToolError(e)

    @mcp.tool(
        annotations={
            "title": "Get Interfaces for a CML Node",
            "readOnlyHint": True,
        },
    )
    async def get_interfaces_for_node(
        lab_id: UUID4Type,
        node_id: UUID4Type,
    ) -> list[SimplifiedInterfaceResponse]:
        """
        List all interfaces on a node by lab and node UUID. Returns id, node, label, slot, type,
        MAC address, and IP configuration.

        Examples:
        - "List the interfaces on R1"
        - "Show me the ports on the firewall"
        - "What interfaces does node xyz have?"
        """
        client = get_cml_client_dep()
        try:
            resp = await client.get(f"/labs/{lab_id}/nodes/{node_id}/interfaces", params={"data": True, "operational": False})
            # See DEVELOPMENT.md "Object-typed return values": dump after construction so FastMCP doesn't double-marshal.
            return [SimplifiedInterfaceResponse(**iface).model_dump(exclude_unset=True) for iface in resp]
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error getting interfaces for node %s in lab %s", node_id, lab_id)
            raise ToolError(e)
