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
Lab management tools for CML MCP server.
"""

import asyncio
import logging

import httpx
import yaml
from fastmcp import Context
from fastmcp.exceptions import ToolError
from mcp.shared.exceptions import McpError
from mcp.types import INVALID_REQUEST, METHOD_NOT_FOUND

from cml_mcp.cml.simple_webserver.schemas.common import UserName, UUID4Type
from cml_mcp.cml.simple_webserver.schemas.labs import Lab, LabRequest, LabTitle
from cml_mcp.cml.simple_webserver.schemas.topologies import Topology
from cml_mcp.cml_client import CMLClient
from cml_mcp.tools.dependencies import get_cml_client_dep

logger = logging.getLogger("cml-mcp.tools.labs")


async def get_all_labs(client: CMLClient) -> list[UUID4Type]:
    """
    Get all labs from the CML server.

    Returns:
        list[UUID4Type]: A list of lab IDs.
    """
    labs = await client.get("/labs", params={"show_all": True})
    return [UUID4Type(lab) for lab in labs]


async def download_lab_file(lid: UUID4Type, client: CMLClient) -> str:
    """
    Download lab topology by UUID.

    Args:
        lid (UUID4Type): The lab ID.
        client (CMLClient): The CML client instance.

    Returns:
        str: The topology as a YAML string.
    """
    topo_data = await client.get(f"/labs/{lid}/download", is_binary=True)
    return topo_data.decode("utf-8")


async def create_full_topology_from_obj(topology: Topology, client: CMLClient) -> UUID4Type:
    """
    Create complete lab from Topology object.

    Args:
        topology (Topology): The topology object.
        client (CMLClient): The CML client instance.

    Returns:
        UUID4Type: The lab UUID.
    """
    resp = await client.post("/import", data=topology.model_dump(mode="json", exclude_defaults=True, exclude_none=True))
    return UUID4Type(resp["id"])


def register_tools(mcp):  # noqa: C901
    """Register all lab-related tools with the FastMCP server."""

    @mcp.tool(
        annotations={
            "title": "Get All CML Labs",
            "readOnlyHint": True,
        }
    )
    async def get_cml_labs(user: UserName | None = None) -> list[Lab]:
        """
        Retrieve labs for a specific user. Omit user parameter for current user's labs.
        Returns list of Lab objects with id, lab_title, owner_username, description, state, and metadata.
        """
        client = get_cml_client_dep()

        # # Clients like to pass "null" as a string vs. null as a None type.
        # if not user or str(user) == "null":
        #     user = settings.cml_username  # Default to the configured username

        try:
            # If the requested user is not the configured user and is not an admin, deny access
            # if user and not await client.is_admin():
            #     raise ValueError("User is not an admin and cannot view all labs.")
            ulabs = []
            # Get all labs from the CML server
            labs = await get_all_labs(client)
            for lab in labs:
                # For each lab, get its details
                lab_details = await client.get(f"/labs/{lab}")
                # Only include labs owned by the specified user
                if not user or lab_details.get("owner_username") == str(user):
                    ulabs.append(Lab(**lab_details).model_dump(exclude_unset=True))
            return ulabs
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error getting CML labs: {str(e)}", exc_info=True)
            raise ToolError(e)

    @mcp.tool(
        annotations={
            "title": "Create an Empty Lab",
            "readOnlyHint": False,
            "destructiveHint": False,
        },
    )
    async def create_empty_lab(lab: LabRequest | dict) -> UUID4Type:
        """
        Create empty lab. Returns lab UUID.
        Optional: title (str, 1-64 chars), owner (UUID), description (str, max 4096 chars), notes (str, max 32768 chars),
        associations (group/user permissions).
        """
        client = get_cml_client_dep()
        try:
            # XXX The dict usage is a workaround for some LLMs that pass a JSON string
            # representation of the argument object.
            if isinstance(lab, dict):
                lab = LabRequest(**lab)
            resp = await client.post("/labs", data=lab.model_dump(mode="json", exclude_none=True))
            return UUID4Type(resp["id"])
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error creating empty lab topology: {str(e)}", exc_info=True)
            raise ToolError(e)

    @mcp.tool(
        annotations={
            "title": "Modify CML Lab Properties",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def modify_cml_lab(lid: UUID4Type, lab: LabRequest | dict) -> bool:
        """
        Update lab metadata by UUID.
        Modifiable: title, owner, description, notes, associations (group/user permissions).
        """
        client = get_cml_client_dep()
        try:
            # XXX The dict usage is a workaround for some LLMs that pass a JSON string
            # representation of the argument object.
            if isinstance(lab, dict):
                lab = LabRequest(**lab)
            await client.patch(f"/labs/{lid}", data=lab.model_dump(mode="json", exclude_none=True))
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error modifying lab {lid}: {str(e)}", exc_info=True)
            raise ToolError(e)

    @mcp.tool(
        annotations={
            "title": "Create a Full Lab Topology",
            "readOnlyHint": False,
            "destructiveHint": False,
        },
    )
    async def create_full_lab_topology(topology: Topology | dict) -> UUID4Type:
        """
        Create complete lab from Topology. Returns lab UUID.
        Required: lab (title, version), nodes (id, x, y, label, node_definition, interfaces), links (id, i1, i2, n1, n2).
        Optional: annotations (text/rectangle/ellipse/line), smart_annotations.
        Supports full configuration: RAM, CPU, images, interface MAC addresses, link conditioning, and node configs.
        """
        client = get_cml_client_dep()
        try:
            # XXX The dict usage is a workaround for some LLMs that pass a JSON string
            # representation of the argument object.
            if isinstance(topology, dict):
                topology = Topology(**topology)
            return await create_full_topology_from_obj(topology, client)
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error creating lab topology: {str(e)}", exc_info=True)
            raise ToolError(e)

    @mcp.tool(
        annotations={"title": "Start a CML Lab", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True},
    )
    async def start_cml_lab(
        lid: UUID4Type,
        wait_for_convergence: bool = False,
    ) -> bool:
        """
        Start lab by UUID. Set wait_for_convergence=true to wait until all nodes reach stable state.
        """
        client = get_cml_client_dep()
        try:
            await client.put(f"/labs/{lid}/start")
            if wait_for_convergence:
                while True:
                    converged = await client.get(f"/labs/{lid}/check_if_converged")
                    if converged:
                        break
                    await asyncio.sleep(3)
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error starting CML lab {lid}: {str(e)}", exc_info=True)
            raise ToolError(e)

    async def stop_lab(lid: UUID4Type, client: CMLClient) -> None:
        """
        Stop a CML lab by its ID.

        Args:
            lid (UUID4Type): The lab ID.
            client (CMLClient): The CML client instance.
        """
        await client.put(f"/labs/{lid}/stop")

    async def wipe_lab(lid: UUID4Type, client: CMLClient) -> None:
        """
        Wipe a CML lab by its ID.

        Args:
            lid (UUID4Type): The lab ID.
            client (CMLClient): The CML client instance.
        """
        await client.put(f"/labs/{lid}/wipe")

    @mcp.tool(
        annotations={"title": "Stop a CML Lab", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True},
    )
    async def stop_cml_lab(lid: UUID4Type) -> bool:
        """
        Stop lab by UUID. Stops all running nodes.
        """
        client = get_cml_client_dep()
        try:
            await stop_lab(lid, client)
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error stopping CML lab {lid}: {str(e)}", exc_info=True)
            raise ToolError(e)

    @mcp.tool(
        annotations={
            "title": "Wipe a CML Lab",
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
        },
    )
    async def wipe_cml_lab(lid: UUID4Type, ctx: Context) -> bool:
        """
        Wipe lab by UUID. Erases all node data/configurations. CRITICAL: Always confirm
        wipe with user first, unless user is responding "yes" to your confirmation prompt.
        """
        client = get_cml_client_dep()
        try:
            elicit_supported = True
            try:
                result = await ctx.elicit("Are you sure you want to wipe the lab?", response_type=None)
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
            await wipe_lab(lid, client)
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error wiping CML lab {lid}: {str(e)}", exc_info=True)
            raise ToolError(e)

    @mcp.tool(
        annotations={
            "title": "Delete a CML Lab",
            "readOnlyHint": False,
            "destructiveHint": True,
        },
    )
    async def delete_cml_lab(lid: UUID4Type, ctx: Context) -> bool:
        """
        Delete lab by UUID. Auto-stops and wipes if needed. CRITICAL: Always ask "Confirm deletion of [item]?" and wait for user's "yes"
        before deleting.
        """
        client = get_cml_client_dep()
        try:
            elicit_supported = True
            try:
                result = await ctx.elicit("Are you sure you want to delete the lab?", response_type=None)
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
            await stop_lab(lid, client)  # Ensure the lab is stopped before deletion
            await wipe_lab(lid, client)  # Ensure the lab is wiped before deletion
            await client.delete(f"/labs/{lid}")
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error deleting CML lab {lid}: {str(e)}", exc_info=True)
            raise ToolError(e)

    @mcp.tool(
        annotations={"title": "Get a CML Lab by Title", "readOnlyHint": True},
    )
    async def get_cml_lab_by_title(title: LabTitle) -> Lab:
        """
        Find lab by title. Returns Lab object with id, state, nodes, and metadata.
        """
        client = get_cml_client_dep()
        try:
            labs = await get_all_labs(client)
            for lid in labs:
                lab = await client.get(f"/labs/{lid}")
                if lab["lab_title"] == str(title):
                    return Lab(**lab).model_dump(exclude_unset=True)
            raise ValueError(f"Lab with title '{title}' not found.")
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error getting CML lab by title {title}: {str(e)}", exc_info=True)
            raise ToolError(e)

    @mcp.tool(
        annotations={"title": "Download lab topology", "readOnlyHint": True},
    )
    async def download_lab_topology(lid: UUID4Type) -> str:
        """
        Download lab topology by UUID. Returns the topology as a YAML string.
        This string should be presented to the user as a YAML file for saving.
        """
        client = get_cml_client_dep()
        try:
            return await download_lab_file(lid, client)
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error downloading lab topology for lab {lid}: {str(e)}", exc_info=True)
            raise ToolError(e)

    @mcp.tool(
        annotations={"title": "Clone CML Lab", "readOnlyHint": False, "destructiveHint": False},
    )
    async def clone_cml_lab(lid: UUID4Type, new_title: LabTitle | None = None) -> UUID4Type:
        """
        Clone lab by UUID. Optionally provide a new title for the cloned lab, else title is "Copy of {original title}".
        Returns the UUID of the newly created lab.
        """
        client = get_cml_client_dep()
        try:
            topo_file = await download_lab_file(lid, client)
            yaml_data = yaml.safe_load(topo_file)
            if new_title:
                yaml_data["lab"]["title"] = str(new_title)
            else:
                yaml_data["lab"]["title"] = f"Copy of {yaml_data['lab']['title']}"

            topology = Topology(**yaml_data)
            return await create_full_topology_from_obj(topology, client)
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error cloning CML lab {lid}: {str(e)}", exc_info=True)
            raise ToolError(e)
