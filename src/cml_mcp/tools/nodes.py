# Copyright (c) 2025-2026  Cisco Systems, Inc.
# All rights reserved.

"""
Node management tools for CML MCP server.
"""

import asyncio
import logging

import httpx
from fastmcp import Context
from fastmcp.exceptions import ToolError
from mcp.shared.exceptions import McpError
from mcp.types import INVALID_REQUEST, METHOD_NOT_FOUND

from cml_mcp.cml.simple_webserver.schemas.common import UUID4Type
from cml_mcp.cml.simple_webserver.schemas.nodes import Node, NodeConfigurationContent, NodeCreate
from cml_mcp.cml_client import CMLClient
from cml_mcp.tools.dependencies import get_cml_client_dep

logger = logging.getLogger("cml-mcp.tools.nodes")


async def stop_node(lid: UUID4Type, nid: UUID4Type, client: CMLClient) -> None:
    """
    Stop a CML node by its lab ID and node ID.

    Args:
        lid (UUID4Type): The lab ID.
        nid (UUID4Type): The node ID.
        client (CMLClient): The CML client instance.
    """
    await client.put(f"/labs/{lid}/nodes/{nid}/state/stop")


async def wipe_node(lid: UUID4Type, nid: UUID4Type, client: CMLClient) -> None:
    """
    Wipe a CML node by its lab ID and node ID.

    Args:
        lid (UUID4Type): The lab ID.
        nid (UUID4Type): The node ID.
        client (CMLClient): The CML client instance.
    """
    await client.put(f"/labs/{lid}/nodes/{nid}/wipe_disks")


def register_tools(mcp):  # noqa: C901
    """Register all node-related tools with the FastMCP server."""

    @mcp.tool(
        annotations={
            "title": "Get All Nodes for a CML Lab",
            "readOnlyHint": True,
        },
    )
    async def get_nodes_for_cml_lab(lid: UUID4Type) -> list[Node]:
        """
        Get lab nodes by UUID. Returns list with id, label, node_definition, x, y, state, interfaces, and operational data (CPU/RAM/serial).
        """
        client = get_cml_client_dep()
        try:
            resp = await client.get(f"/labs/{lid}/nodes", params={"data": True, "operational": True, "exclude_configurations": True})
            rnodes = []
            for node in list(resp):
                # XXX: Fixup known issues with bad data coming from
                # certain node types.
                if node.get("operational") is not None:
                    if node["operational"].get("vnc_key") == "":
                        node["operational"]["vnc_key"] = None
                    if node["operational"].get("image_definition") == "":
                        node["operational"]["image_definition"] = None
                    if node["operational"].get("serial_consoles") is None:
                        node["operational"]["serial_consoles"] = []
                rnodes.append(Node(**node).model_dump(exclude_unset=True))
            return rnodes
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error getting nodes for CML lab {lid}: {str(e)}", exc_info=True)
            raise ToolError(e)

    @mcp.tool(
        annotations={
            "title": "Add a Node to a CML Lab",
            "readOnlyHint": False,
            "destructiveHint": False,
        },
    )
    async def add_node_to_cml_lab(
        lid: UUID4Type,
        node: NodeCreate | dict,
    ) -> UUID4Type:
        """
        Add node to lab. Returns node UUID. Auto-creates default interfaces per node definition.
        Required: x (-15000 to 15000), y (-15000 to 15000), label (1-128 chars), node_definition (e.g., "alpine", "iosv").
        Optional: image_definition, ram (MB), cpus, cpu_limit (%), data_volume (GB), boot_disk_size (GB), tags, configuration, parameters.
        """
        client = get_cml_client_dep()
        try:
            # XXX The dict usage is a workaround for some LLMs that pass a JSON string
            # representation of the argument object.
            if isinstance(node, dict):
                node = NodeCreate(**node)
            resp = await client.post(
                f"/labs/{lid}/nodes", params={"populate_interfaces": True}, data=node.model_dump(mode="json", exclude_defaults=True)
            )
            return UUID4Type(resp["id"])
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error adding CML node to lab {lid}: {str(e)}", exc_info=True)
            raise ToolError(e)

    @mcp.tool(
        annotations={"title": "Configure a CML Node", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True},
    )
    async def configure_cml_node(
        lid: UUID4Type,
        nid: UUID4Type,
        config: NodeConfigurationContent,
    ) -> bool:
        """
        Set node startup config by lab and node UUID. Node must be in CREATED state (new or wiped).
        More efficient than starting node and sending CLI. Config is string with device commands.
        """
        client = get_cml_client_dep()
        payload = {"configuration": str(config)}
        try:
            await client.patch(f"/labs/{lid}/nodes/{nid}", data=payload)
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error configuring CML node {nid} in lab {lid}: {str(e)}", exc_info=True)
            raise ToolError(e)

    @mcp.tool(
        annotations={"title": "Stop a CML Node", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True},
    )
    async def stop_cml_node(lid: UUID4Type, nid: UUID4Type) -> bool:
        """
        Stop node by lab and node UUID. Powers down the node.
        """
        client = get_cml_client_dep()
        try:
            await stop_node(lid, nid, client)
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error stopping CML node {nid} in lab {lid}: {str(e)}", exc_info=True)
            raise ToolError(e)

    @mcp.tool(
        annotations={
            "title": "Start a CML Node",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def start_cml_node(
        lid: UUID4Type,
        nid: UUID4Type,
        wait_for_convergence: bool = False,
    ) -> bool:
        """
        Start node by lab and node UUID. Set wait_for_convergence=true to wait until node reaches stable state.
        """
        client = get_cml_client_dep()
        try:
            await client.put(f"/labs/{lid}/nodes/{nid}/state/start")
            if wait_for_convergence:
                while True:
                    converged = await client.get(f"/labs/{lid}/nodes/{nid}/check_if_converged")
                    if converged:
                        break
                    await asyncio.sleep(3)
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error starting CML node {nid} in lab {lid}: {str(e)}", exc_info=True)
            raise ToolError(e)

    @mcp.tool(
        annotations={"title": "Wipe a CML Node", "readOnlyHint": False, "destructiveHint": True, "idempotentHint": True},
    )
    async def wipe_cml_node(lid: UUID4Type, nid: UUID4Type, ctx: Context) -> bool:
        """
        Wipe node by lab and node UUID. Erases all node data. Node must be stopped first. CRITICAL: Always confirm
        wipe with user first, unless user is responding "yes" to your confirmation prompt.
        """
        client = get_cml_client_dep()
        try:
            elicit_supported = True
            try:
                result = await ctx.elicit("Are you sure you want to wipe the node?", response_type=None)
            except McpError as me:
                if me.error.code == METHOD_NOT_FOUND or me.error.code == INVALID_REQUEST:
                    elicit_supported = False
                else:
                    raise me
            except Exception as e:
                # Handle stream closure errors (common in stateless HTTP when client disconnects)
                # Treat as if elicit is not supported and proceed without confirmation
                logger.debug(f"elicit() failed (possibly client disconnect): {type(e).__name__}: {e}")
                elicit_supported = False
            if elicit_supported and result.action != "accept":
                raise Exception("Wipe operation cancelled by user.")
            await wipe_node(lid, nid, client)
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error wiping CML node {nid} in lab {lid}: {str(e)}", exc_info=True)
            raise ToolError(e)

    @mcp.tool(
        annotations={"title": "Delete a node from a CML lab.", "readOnlyHint": False, "destructiveHint": True},
    )
    async def delete_cml_node(lid: UUID4Type, nid: UUID4Type, ctx: Context) -> bool:
        """
        Delete node by lab and node UUID. Auto-stops and wipes if needed. CRITICAL: Always ask "Confirm deletion of [item]?" and wait for
        user's "yes" before deleting.
        """
        client = get_cml_client_dep()
        try:
            elicit_supported = True
            try:
                result = await ctx.elicit("Are you sure you want to delete the node?", response_type=None)
            except McpError as me:
                if me.error.code == METHOD_NOT_FOUND or me.error.code == INVALID_REQUEST:
                    elicit_supported = False
                else:
                    raise me
            except Exception as e:
                # Handle stream closure errors (common in stateless HTTP when client disconnects)
                # Treat as if elicit is not supported and proceed without confirmation
                logger.debug(f"elicit() failed (possibly client disconnect): {type(e).__name__}: {e}")
                elicit_supported = False
            if elicit_supported and result.action != "accept":
                raise Exception("Delete operation cancelled by user.")
            await stop_node(lid, nid, client)  # Ensure the node is stopped before deletion
            await wipe_node(lid, nid, client)
            await client.delete(f"/labs/{lid}/nodes/{nid}")
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error deleting CML node {nid} in lab {lid}: {str(e)}", exc_info=True)
            raise ToolError(e)
