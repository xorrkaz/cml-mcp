# Copyright (c) 2025-2026  Cisco Systems, Inc.
# All rights reserved.

"""
Interface management tools for CML MCP server.
"""

import logging

import httpx
from fastmcp.exceptions import ToolError

from cml_mcp.cml.simple_webserver.schemas.common import UUID4Type
from cml_mcp.cml.simple_webserver.schemas.interfaces import InterfaceCreate
from cml_mcp.cml_client import CMLClient
from cml_mcp.tools.dependencies import get_cml_client_dep
from cml_mcp.types import SimplifiedInterfaceResponse

logger = logging.getLogger("cml-mcp.tools.interfaces")


async def add_interface(lid: UUID4Type, intf: InterfaceCreate, client: CMLClient) -> SimplifiedInterfaceResponse:
    """
    Add an interface to a CML lab by its lab ID.

    Args:
        lid (UUID4Type): The lab ID.
        intf (InterfaceCreate): The interface definition as an InterfaceCreate object.
        client (CMLClient): The CML client instance.

    Returns:
        InterfaceResponse: The added interface details.
    """
    resp = await client.post(f"/labs/{lid}/interfaces", data=intf.model_dump(mode="json", exclude_none=True))
    return SimplifiedInterfaceResponse(**resp).model_dump(exclude_unset=True)


def register_tools(mcp):
    """Register all interface-related tools with the FastMCP server."""

    @mcp.tool(
        annotations={
            "title": "Add an Interface to a CML Node",
            "readOnlyHint": False,
            "destructiveHint": False,
        },
    )
    async def add_interface_to_node(
        lid: UUID4Type,
        intf: InterfaceCreate | dict,
    ) -> SimplifiedInterfaceResponse:
        """
        Add interface to node. Returns interface with id, node, slot, type, and MAC address.
        Input: interface object. Prefer a JSON object; JSON-encoded object strings are accepted.
        Required: node (node UUID). Optional: slot (0-128), mac_address ("00:11:22:33:44:55" format).
        """
        client = get_cml_client_dep()
        try:
            # XXX The dict usage is a workaround for some LLMs that pass a JSON string
            # representation of the argument object.
            if isinstance(intf, dict):
                intf = InterfaceCreate(**intf)
            return await add_interface(lid, intf, client)
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error adding interface to node {intf.node} in lab {lid}: {str(e)}", exc_info=True)
            raise ToolError(e)

    @mcp.tool(
        annotations={
            "title": "Get Interfaces for a CML Node",
            "readOnlyHint": True,
        },
    )
    async def get_interfaces_for_node(
        lid: UUID4Type,
        nid: UUID4Type,
    ) -> list[SimplifiedInterfaceResponse]:
        """
        Get node interfaces by lab and node UUID. Returns list with id, node, label, slot, type, MAC address, and IP config.
        """
        client = get_cml_client_dep()
        try:
            resp = await client.get(f"/labs/{lid}/nodes/{nid}/interfaces", params={"data": True, "operational": False})
            return [SimplifiedInterfaceResponse(**iface).model_dump(exclude_unset=True) for iface in resp]
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error getting interfaces for node {nid} in lab {lid}: {str(e)}", exc_info=True)
            raise ToolError(e)
