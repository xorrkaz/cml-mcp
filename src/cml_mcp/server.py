# Copyright (c) 2025  Joe Clarke <jclarke@cisco.com>
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

import httpx
from fastmcp import FastMCP, Context
from virl2_client.models.cl_pyats import ClPyats

from cml_mcp.cml_client import CMLClient
from cml_mcp.schemas.common import UserName, UUID4Type
from cml_mcp.schemas.labs import Lab, LabTitle
from cml_mcp.schemas.node_definitions import NodeDefinition, SimplifiedNodeDefinitionResponse
from cml_mcp.schemas.nodes import Node, NodeConfigurationContent, NodeLabel
from cml_mcp.schemas.system import SystemHealth
from cml_mcp.schemas.topologies import Topology
from cml_mcp.settings import settings

# Set up logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(threadName)s %(name)s: %(message)s")
logger = logging.getLogger("cml-mcp")


server_mcp = FastMCP(
    "Cisco Modeling Labs MCP Server",
    dependencies=["httpx", "fastmcp", "fastapi", "pydantic_strict_partial", "typer", "virl2_client", "pyats[full]"],
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


@server_mcp.tool
async def get_cml_labs(user: UserName | None = None) -> list[Lab] | dict[str, str]:
    """
    Get the list of labs for a specific user or all labs if the user is an admin.

    Args:
        user (UserName | None): The username to filter labs by. If None, defaults to the configured username.

    Returns:
        list[Lab] | dict: A list of Lab objects owned by the user, or a dictionary with an error message if an error occurs.
    """
    if not user:
        user = settings.cml_username  # Default to the configured username

    try:
        # If the requested user is not the configured user and is not an admin, deny access
        if str(user) != settings.cml_username and not await cml_client.is_admin(str(user)):
            return {"error": "User is not an admin and cannot view all labs."}
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
        return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


@server_mcp.tool
async def get_cml_status() -> SystemHealth | dict[str, str]:
    """
    Get the status of the CML server.

    Returns:
        SystemHealth: The health/status of the CML server.
        dict: An error dictionary if an exception occurs.
    """
    try:
        status = await cml_client.get("/system_health")
        return SystemHealth(**status)
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


@server_mcp.tool
async def get_cml_node_definitions() -> list[SimplifiedNodeDefinitionResponse] | dict[str, str]:
    """
    Get the list of node definitions from the CML server.

    Returns:
        list[SimplifiedNodeDefinitionResponse]: A list of simplified node definitions.
        dict: An error dictionary if an exception occurs.
    """
    try:
        node_definitions = await cml_client.get("/simplified_node_definitions")
        return [SimplifiedNodeDefinitionResponse(**nd) for nd in node_definitions]
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


@server_mcp.tool
async def get_node_definition_detail(nid: UUID4Type) -> NodeDefinition | dict[str, str]:
    """
    Get detailed information about a specific node definition by its ID.

    Args:
        nid (UUID4Type): The node definition ID.

    Returns:
        NodeDefinition: The node definition details.
        dict: An error dictionary if an exception occurs.
    """
    try:
        node_definition = await cml_client.get(f"/node_definitions/{nid}")
        return NodeDefinition(**node_definition)
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


@server_mcp.tool
async def create_lab_topology(topology: Topology) -> UUID4Type | dict[str, str]:
    """
    Create a new lab topology.

    Args:
        topology (Topology): The topology definition.

    Returns:
        UUID4Type: The new lab topology ID if successful.
        dict: An error dictionary if an error occurs.
    """
    try:
        resp = await cml_client.post("/import", data=topology.model_dump())
        return UUID4Type(resp["id"])
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


@server_mcp.tool
async def start_cml_lab(lid: UUID4Type) -> None | dict[str, str]:
    """
    Start a CML lab by its ID.

    Args:
        lid (UUID4Type): The lab ID.

    Returns:
        None: If successful.
        dict: An error dictionary if an error occurs.
    """
    try:
        await cml_client.put(f"/labs/{lid}/start")
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


async def stop_lab(lid: UUID4Type) -> None:
    """
    Stop a CML lab by its ID.

    Args:
        lid (UUID4Type): The lab ID.

    Returns:
        None: If successful.
    """
    await cml_client.put(f"/labs/{lid}/stop")


async def wipe_lab(lid: UUID4Type) -> None:
    """
    Wipe a CML lab by its ID.

    Args:
        lid (UUID4Type): The lab ID.

    Returns:
        None: If successful.
    """
    await cml_client.put(f"/labs/{lid}/wipe")


@server_mcp.tool
async def stop_cml_lab(lid: UUID4Type) -> None | dict[str, str]:
    """
    Stop a CML lab by its ID.

    Args:
        lid (UUID4Type): The lab ID.

    Returns:
        None: If successful.
        dict: An error dictionary if an error occurs.
    """
    try:
        await stop_lab(lid)
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


@server_mcp.tool
async def wipe_cml_lab(lid: UUID4Type, ctx: Context) -> None | dict[str, str]:
    """
    Wipe a CML lab by its ID.

    Args:
        lid (UUID4Type): The lab ID.

    Returns:
        None: If successful.
        dict: An error dictionary if an error occurs.
    """
    try:
        result = await ctx.elicit("Are you sure you want to wipe the lab?")
        if result.action == "accept":
            await wipe_lab(lid)
        else:
            raise Exception("Wipe operation cancelled by user.")
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


@server_mcp.tool
async def delete_cml_lab(lid: UUID4Type, ctx: Context) -> None | dict[str, str]:
    """
    Delete a CML lab by its ID. If the lab is running and/or not wiped, it will be stopped and wiped first.

    Args:
        lid (UUID4Type): The lab ID.

    Returns:
        None: If successful.
        dict: An error dictionary if an error occurs.
    """
    try:
        result = await ctx.elicit("Are you sure you want to delete the lab?")
        if result.action == "accept":
            await stop_lab(lid)  # Ensure the lab is stopped before deletion
            await wipe_lab(lid)  # Ensure the lab is wiped before deletion
            await cml_client.delete(f"/labs/{lid}")
        else:
            raise Exception("Delete operation cancelled by user.")
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


@server_mcp.tool
async def configure_cml_node(lid: UUID4Type, nid: UUID4Type, config: NodeConfigurationContent) -> UUID4Type | dict[str, str]:
    """
    Configure a node in a CML lab by its lab ID and node ID. The node must be in a BOOTED (i.e., wiped) state.

    Args:
        lid (UUID4Type): The lab ID.
        nid (UUID4Type): The node ID.
        config (NodeConfigurationContent): The configuration content for the node.

    Returns:
        UUID4Type: The ID of the node configured if successful.
        dict: An error dictionary if an error occurs.
    """
    payload = {"configuration": str(config)}
    try:
        resp = await cml_client.patch(f"/labs/{lid}/nodes/{nid}", data=payload)
        return UUID4Type(resp)
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


@server_mcp.tool
async def get_nodes_for_cml_lab(lid: UUID4Type) -> list[Node] | dict[str, str]:
    """
    Get a list of nodes for a CML lab by its ID.

    Args:
        lid (UUID4Type): The lab ID.

    Returns:
        list[Node]: List of node objects (without their configurations).
        dict: An error dictionary if an error occurs.
    """
    try:
        resp = await cml_client.get(f"/labs/{lid}/nodes", data={"data": True, "operational": True, "exclude_configurations": True})
        return [Node(**node) for node in resp]
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


@server_mcp.tool
async def get_cml_lab_by_title(title: LabTitle) -> Lab | dict[str, str]:
    """
    Get a CML lab by its title.

    Args:
        title (LabTitle): The lab title.

    Returns:
        Lab: The lab object if found.
        dict: An error dictionary if an error occurs or lab is not found.
    """
    try:
        labs = await get_all_labs()
        for lid in labs:
            lab = await cml_client.get(f"/labs/{lid}")
            if lab["lab_title"] == str(title):
                return Lab(**lab)
        return {"error": "Lab not found"}
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


@server_mcp.tool
async def stop_cml_node(lid: UUID4Type, nid: UUID4Type) -> None | dict[str, str]:
    """
    Stop a node in a CML lab by its lab ID and node ID.

    Args:
        lid (UUID4Type): The lab ID.
        nid (UUID4Type): The node ID.

    Returns:
        None: If successful.
        dict: An error dictionary if an error occurs.
    """
    try:
        await cml_client.put(f"/labs/{lid}/nodes/{nid}/state/stop")
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


@server_mcp.tool
async def start_cml_node(lid: UUID4Type, nid: UUID4Type) -> None | dict[str, str]:
    """
    Start a node in a CML lab by its lab ID and node ID.

    Args:
        lid (UUID4Type): The lab ID.
        nid (UUID4Type): The node ID.

    Returns:
        None: If successful.
        dict: An error dictionary if an error occurs.
    """
    try:
        await cml_client.put(f"/labs/{lid}/nodes/{nid}/state/start")
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


@server_mcp.tool
async def wipe_cml_node(lid: UUID4Type, nid: UUID4Type, ctx: Context) -> None | dict[str, str]:
    """
    Wipe a node in a CML lab by its lab ID and node ID. Node must be stopped first.

    Args:
        lid (UUID4Type): The lab ID.
        nid (UUID4Type): The node ID.

    Returns:
        None: If successful.
        dict: An error dictionary if an error occurs.
    """
    try:
        result = await ctx.elicit("Are you sure you want to wipe the node?")
        if result.action == "accept":
            await cml_client.put(f"/labs/{lid}/nodes/{nid}/wipe_disks")
        else:
            raise Exception("Wipe operation cancelled by user.")
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


@server_mcp.tool
def send_cli_command(lid: UUID4Type, label: NodeLabel, command: str, config_command: bool = False) -> str | dict[str, str]:
    """
    Send a CLI command to a node in a CML lab by its lab ID and node label.

    Args:
        lid (UUID4Type): The lab ID.
        label (NodeLabel): The label of the node to send the command to.
        command (str): The CLI command to send.
        config_command (bool, optional): If True, send as a configuration command. Defaults to False.

    Returns:
        str | dict: The command output if successful, or a dictionary with an error message if an error occurs.
    """
    cwd = os.getcwd()  # Save the current working directory
    try:
        os.chdir(tempfile.gettempdir())  # Change to a writable directory (required by pyATS/ClPyats)
        lab = cml_client.vclient.join_existing_lab(str(lid))  # Join the existing lab using the provided lab ID
        pylab = ClPyats(lab)  # Create a ClPyats object for interacting with the lab
        pylab.sync_testbed(settings.cml_username, settings.cml_password)  # Sync the testbed with CML credentials
        if config_command:
            # Send the command as a configuration command
            return pylab.run_config_command(str(label), command)
        # Send the command as an exec/operational command
        return pylab.run_command(str(label), command)
    except Exception as e:
        return {"error": str(e)}
    finally:
        os.chdir(cwd)  # Restore the original working directory
