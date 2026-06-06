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


async def add_interface(lab_id: UUID4Type, payload: dict, client: CMLClient) -> list[SimplifiedInterfaceResponse]:
    """
    Add an interface to a CML lab by its lab ID.

    Args:
        lab_id (UUID4Type): The lab ID.
        payload (dict): The interface creation payload.
        client (CMLClient): The CML client instance.

    Returns:
        list[SimplifiedInterfaceResponse]: The added interfaces details.
    """
    resp = await client.post(f"/labs/{lab_id}/interfaces", data=payload)
    # See DEVELOPMENT.md "Object-typed return values": dump after construction so FastMCP doesn't double-marshal.
    if isinstance(resp, dict):
        return [SimplifiedInterfaceResponse(**resp).model_dump(exclude_unset=True)]

    return [SimplifiedInterfaceResponse(**item).model_dump(exclude_unset=True) for item in resp]


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
    ) -> list[SimplifiedInterfaceResponse]:
        """
        Add a new interface to a node. Returns interface details (id, node, slot, type, MAC).  Note: depending on
        the slot requested, multiple interfaces may be added, so a list of added interfaces is returned.

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
