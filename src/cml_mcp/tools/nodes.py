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
Node management tools for CML MCP server.
"""

import asyncio
import logging
from typing import Annotated

import httpx
from fastmcp import Context
from fastmcp.exceptions import ToolError

from cml_mcp.cml.simple_webserver.schemas.common import Coordinate, DefinitionID, TagArray, UUID4Type
from cml_mcp.cml.simple_webserver.schemas.nodes import CpuLimit, Cpus, DiskSpace, Node, NodeConfigurationContent, NodeCreate, Ram
from cml_mcp.cml_client import CMLClient
from cml_mcp.tools.dependencies import elicit_confirmation, get_cml_client_dep
from cml_mcp.tools.model_helpers import build_payload, field_from

logger = logging.getLogger("cml-mcp.tools.nodes")


async def stop_node(lab_id: UUID4Type, node_id: UUID4Type, client: CMLClient) -> None:
    """
    Stop a CML node by its lab ID and node ID.

    Args:
        lab_id (UUID4Type): The lab ID.
        node_id (UUID4Type): The node ID.
        client (CMLClient): The CML client instance.
    """
    await client.put(f"/labs/{lab_id}/nodes/{node_id}/state/stop")


async def wipe_node(lab_id: UUID4Type, node_id: UUID4Type, client: CMLClient) -> None:
    """
    Wipe a CML node by its lab ID and node ID.

    Args:
        lab_id (UUID4Type): The lab ID.
        node_id (UUID4Type): The node ID.
        client (CMLClient): The CML client instance.
    """
    await client.put(f"/labs/{lab_id}/nodes/{node_id}/wipe_disks")


def register_tools(mcp):  # noqa: C901
    """Register all node-related tools with the FastMCP server."""

    @mcp.tool(
        annotations={
            "title": "Get All Nodes for a CML Lab",
            "readOnlyHint": True,
        },
    )
    async def get_nodes_for_cml_lab(lab_id: UUID4Type) -> list[Node]:
        """
        List all nodes in a lab by lab UUID. Returns id, label, node_definition, x/y, state,
        interfaces, and operational data (CPU, RAM, serial consoles).

        Examples:
        - "List all nodes in my CML lab"
        - "What devices are in lab abc123?"
        - "Show me the topology nodes"
        """

        client = get_cml_client_dep()
        try:
            resp = await client.get(f"/labs/{lab_id}/nodes", params={"data": True, "operational": True, "exclude_configurations": True})
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
            logger.exception("Error getting nodes for CML lab %s", lab_id)
            raise ToolError(e)

    # Source schema: NodeCreate (cml/simple_webserver/schemas/nodes.py)
    # Exposed: label, x, y, node_definition, image_definition, ram, cpus, cpu_limit, data_volume, boot_disk_size,
    #          tags, configuration, parameters, hide_links, priority, pyats
    # Omitted: (none - all user-meaningful fields exposed)
    @mcp.tool(
        annotations={
            "title": "Add a Node to a CML Lab",
            "readOnlyHint": False,
            "destructiveHint": False,
        },
    )
    async def add_node_to_cml_lab(
        lab_id: UUID4Type,
        node_definition: DefinitionID,
        label: Annotated[str | None, field_from(NodeCreate, "label")] = None,
        x: Coordinate | None = None,
        y: Coordinate | None = None,
        image_definition: DefinitionID | None = None,
        ram: Ram = None,
        cpus: Cpus = None,
        cpu_limit: CpuLimit = None,
        data_volume: DiskSpace = None,
        boot_disk_size: DiskSpace = None,
        tags: TagArray | None = None,
        configuration: Annotated[str | None, field_from(NodeCreate, "configuration")] = None,
        parameters: Annotated[dict[str, str | None] | None, field_from(NodeCreate, "parameters")] = None,
        hide_links: Annotated[bool | None, field_from(NodeCreate, "hide_links")] = None,
        priority: Annotated[int | None, field_from(NodeCreate, "priority")] = None,
        pyats: Annotated[dict | None, field_from(NodeCreate, "pyats")] = None,
    ) -> UUID4Type:
        """
        Add a node to an existing lab. Returns the new node's UUID. Default interfaces are auto-created.

        Required: lab_id (lab UUID), node_definition (e.g. "alpine", "iosv", "csr1000v" -- discover via get_cml_node_definitions).
        Optional: label (1-128 chars), x/y coordinates (-15000..15000), image_definition, ram (MB, 1-1048576),
        cpus (1-128), cpu_limit (%, 20-100), data_volume (GB, 0-4096), boot_disk_size (GB, 0-4096),
        tags (list of strings), configuration (string or dict), parameters (dict), hide_links (bool),
        priority (0-10000), pyats (PyATS credentials dict).

        Examples:
        - "Add a CSR1000v router called 'R3' to my lab"
        - "Insert an IOSv switch into the topology"
        - "Add an Alpine node to lab abc123"
        """
        client = get_cml_client_dep()
        try:
            payload = build_payload(
                node_definition=node_definition,
                label=label,
                x=x,
                y=y,
                image_definition=image_definition,
                ram=ram,
                cpus=cpus,
                cpu_limit=cpu_limit,
                data_volume=data_volume,
                boot_disk_size=boot_disk_size,
                tags=tags,
                configuration=configuration,
                parameters=parameters,
                hide_links=hide_links,
                priority=priority,
                pyats=pyats,
            )
            resp = await client.post(
                f"/labs/{lab_id}/nodes",
                params={"populate_interfaces": True},
                data=payload,
            )
            return UUID4Type(resp["id"])
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error adding CML node to lab %s", lab_id)
            raise ToolError(e)

    @mcp.tool(
        annotations={"title": "Configure a CML Node", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True},
    )
    async def configure_cml_node(
        lab_id: UUID4Type,
        node_id: UUID4Type,
        config: NodeConfigurationContent,
    ) -> bool:
        """
        Set the startup configuration for a node by lab and node UUID. The `config` is a plain
        string of device CLI commands. Node must be in the CREATED state (newly added or wiped).

        Prefer this over starting the node and using send_cli_command -- it is faster and avoids
        needing the node to be running.

        Examples:
        - "Set the startup config for R1 in lab abc123"
        - "Apply this bootstrap config to the ASAv node"
        - "Load the IOS config onto router xyz"
        """
        client = get_cml_client_dep()
        payload = {"configuration": str(config)}
        try:
            await client.patch(f"/labs/{lab_id}/nodes/{node_id}", data=payload)
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error configuring CML node %s in lab %s", node_id, lab_id)
            raise ToolError(e)

    @mcp.tool(
        annotations={"title": "Stop a CML Node", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True},
    )
    async def stop_cml_node(lab_id: UUID4Type, node_id: UUID4Type) -> bool:
        """
        Stop (power down) a single node by lab and node UUID.

        Examples:
        - "Stop node R1 in my lab"
        - "Power down the firewall"
        - "Shut down node xyz"
        """
        client = get_cml_client_dep()
        try:
            await stop_node(lab_id, node_id, client)
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error stopping CML node %s in lab %s", node_id, lab_id)
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
        lab_id: UUID4Type,
        node_id: UUID4Type,
        wait_for_convergence: bool = False,
    ) -> bool:
        """
        Start (boot) a single node by lab and node UUID.
        Set wait_for_convergence=true to block until the node reaches a stable state.

        Examples:
        - "Start router R1"
        - "Boot the firewall node"
        - "Power on node xyz and wait for convergence"
        """
        client = get_cml_client_dep()
        try:
            await client.put(f"/labs/{lab_id}/nodes/{node_id}/state/start")
            if wait_for_convergence:
                while True:
                    converged = await client.get(f"/labs/{lab_id}/nodes/{node_id}/check_if_converged")
                    if converged:
                        break
                    await asyncio.sleep(3)
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error starting CML node %s in lab %s", node_id, lab_id)
            raise ToolError(e)

    @mcp.tool(
        annotations={"title": "Wipe a CML Node", "readOnlyHint": False, "destructiveHint": True, "idempotentHint": True},
    )
    async def wipe_cml_node(lab_id: UUID4Type, node_id: UUID4Type, ctx: Context) -> bool:
        """
        Wipe a single node's disks by lab and node UUID. Erases all node data. Node must be stopped first.

        CRITICAL: Destructive and irreversible. Always ask "Confirm wipe of [node]?" and wait for the
        user's "yes" before invoking this tool.

        Examples:
        - "Wipe node R1"
        - "Reset the firewall node to factory defaults"
        - "Erase the disk on node xyz"
        """
        client = get_cml_client_dep()
        try:
            if not await elicit_confirmation(ctx, "Are you sure you want to wipe the node?"):
                raise Exception("Wipe operation cancelled by user.")
            await wipe_node(lab_id, node_id, client)
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error wiping CML node %s in lab %s", node_id, lab_id)
            raise ToolError(e)

    @mcp.tool(
        annotations={"title": "Delete a node from a CML lab.", "readOnlyHint": False, "destructiveHint": True},
    )
    async def delete_cml_node(lab_id: UUID4Type, node_id: UUID4Type, ctx: Context) -> bool:
        """
        Delete a node from a lab by lab and node UUID. Auto-stops and wipes the node first.

        CRITICAL: Destructive and irreversible. Always ask "Confirm deletion of [node]?" and wait for the
        user's "yes" before invoking this tool.

        Examples:
        - "Delete node R1 from my lab"
        - "Remove the firewall from the topology"
        - "Get rid of node xyz"
        """
        client = get_cml_client_dep()
        try:
            if not await elicit_confirmation(ctx, "Are you sure you want to delete the node?"):
                raise Exception("Delete operation cancelled by user.")
            await stop_node(lab_id, node_id, client)  # Ensure the node is stopped before deletion
            await wipe_node(lab_id, node_id, client)
            await client.delete(f"/labs/{lab_id}/nodes/{node_id}")
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error deleting CML node %s in lab %s", node_id, lab_id)
            raise ToolError(e)
