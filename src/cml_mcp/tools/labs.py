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
from typing import Annotated

import httpx
import yaml
from fastmcp import Context
from fastmcp.exceptions import ToolError

from cml_mcp.cml.simple_webserver.schemas.common import UUID4_REG_EXP, UserName, UUID4Type
from cml_mcp.cml.simple_webserver.schemas.labs import Lab, LabAssociations, LabDescription, LabNotes, LabOwner, LabTitle
from cml_mcp.cml.simple_webserver.schemas.topologies import Topology
from cml_mcp.cml_client import CMLClient
from cml_mcp.tools.dependencies import elicit_confirmation, get_cml_client_dep
from cml_mcp.tools.model_helpers import build_payload, field_from, lenient_construct

logger = logging.getLogger("cml-mcp.tools.labs")

_VALID_LAB_PERMISSIONS = {"LAB_ADMIN", "LAB_EDIT", "LAB_EXEC", "LAB_VIEW"}


def _validate_lab_associations(items: list[dict] | None, kind: str) -> None:
    """Validate a groups/users list for set_cml_lab_permissions. Raises ToolError on bad input."""
    if items is None:
        return
    if not isinstance(items, list):
        raise ToolError(f"Invalid {kind} permission entries: expected a list, got {type(items).__name__}")
    for idx, entry in enumerate(items):
        prefix = f"Invalid {kind} permission entry [{idx}]"
        if not isinstance(entry, dict):
            raise ToolError(f"{prefix}: expected a dict, got {type(entry).__name__}")
        extra = set(entry.keys()) - {"id", "permissions"}
        missing = {"id", "permissions"} - set(entry.keys())
        if missing or extra:
            raise ToolError(
                f"{prefix}: must contain exactly the keys 'id' and 'permissions' "
                f"(missing={sorted(missing)}, unexpected={sorted(extra)})"
            )
        ent_id = entry["id"]
        if not isinstance(ent_id, str) or not UUID4_REG_EXP.match(ent_id):
            raise ToolError(f"{prefix}: 'id' must be a UUID4 string, got {ent_id!r}")
        perms = entry["permissions"]
        if not isinstance(perms, list) or not perms:
            raise ToolError(f"{prefix}: 'permissions' must be a non-empty list of strings")
        for perm in perms:
            if not isinstance(perm, str) or perm not in _VALID_LAB_PERMISSIONS:
                raise ToolError(f"{prefix}: invalid permission {perm!r}; must be one of {sorted(_VALID_LAB_PERMISSIONS)}")


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
    resp = await client.post("/import", data=topology.model_dump(mode="json", exclude_unset=True, exclude_none=True))
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
        List CML labs, optionally filtered by owner username.

        Returns Lab objects with id, lab_title, owner_username, description, state, and metadata.
        Omit `user` to get all labs (admin) or current user's labs (non-admin).

        Examples:
        - "Show me all my CML labs"
        - "List all available labs in CML"
        - "What labs does alice own?"
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
            logger.exception("Error getting CML labs")
            raise ToolError(e)

    # Source schema: LabRequest (cml/simple_webserver/schemas/labs.py)
    # Exposed: title, description, notes, owner
    # Omitted: groups (deprecated), associations (use set_cml_lab_permissions), autostart, node_staging (server-managed defaults)
    @mcp.tool(
        annotations={
            "title": "Create an Empty Lab",
            "readOnlyHint": False,
            "destructiveHint": False,
        },
    )
    async def create_empty_lab(
        title: LabTitle | None = None,
        description: LabDescription | None = None,
        notes: LabNotes | None = None,
        owner: LabOwner | None = None,
    ) -> UUID4Type:
        """
        Create an empty CML lab (no nodes/links). Returns the new lab UUID.

        Optional: title (1-64 chars), owner (UUID), description (<=4096 chars), notes (<=32768 chars).
        Use set_cml_lab_permissions to configure group/user access after creation.

        Examples:
        - "Create a new empty lab called 'OSPF Practice'"
        - "Make me a blank CML lab"
        - "Start a new lab titled 'Customer Demo'"
        """
        client = get_cml_client_dep()
        try:
            payload = build_payload(
                title=title,
                description=description,
                notes=notes,
                owner=str(owner) if owner is not None else None,
            )
            resp = await client.post("/labs", data=payload)
            return UUID4Type(resp["id"])
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error creating empty lab topology")
            raise ToolError(e)

    # Source schema: LabRequest (cml/simple_webserver/schemas/labs.py)
    # Exposed: title, description, notes, owner
    # Omitted: groups (deprecated), associations (use set_cml_lab_permissions), autostart, node_staging (server-managed)
    @mcp.tool(
        annotations={
            "title": "Modify CML Lab Properties",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def modify_cml_lab(
        lid: UUID4Type,
        title: LabTitle | None = None,
        description: LabDescription | None = None,
        notes: LabNotes | None = None,
        owner: LabOwner | None = None,
    ) -> bool:
        """
        Update lab metadata (title, owner, description, notes) by lab UUID.
        Only provided fields are modified; omitted fields remain unchanged.

        Examples:
        - "Rename lab abc123 to 'Production Test'"
        - "Change the owner of my lab to bob"
        - "Update the description on lab abc123"
        """
        client = get_cml_client_dep()
        try:
            # PATCH-friendly: only include non-None values
            payload = build_payload(
                title=title,
                description=description,
                notes=notes,
                owner=str(owner) if owner is not None else None,
            )
            await client.patch(f"/labs/{lid}", data=payload)
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error modifying lab %s", lid)
            raise ToolError(e)

    # Source schema: LabAssociations (cml/simple_webserver/schemas/labs.py)
    # Exposed: groups (list of {id: UUID, permissions: list[str]}), users (list of {id: UUID, permissions: list[str]})
    @mcp.tool(
        annotations={
            "title": "Set CML Lab Permissions",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def set_cml_lab_permissions(
        lid: UUID4Type,
        groups: Annotated[list[dict] | None, field_from(LabAssociations, "groups")] = None,
        users: Annotated[list[dict] | None, field_from(LabAssociations, "users")] = None,
    ) -> bool:
        """
        Configure group and user permissions for a CML lab by lab UUID.

        Valid permissions: LAB_ADMIN (full control), LAB_EDIT (modify topology), LAB_EXEC (start/stop), LAB_VIEW (read-only).
        Validation: invalid entries raise an error before the request is sent.

        Each group dict: {"id": "<group-uuid>", "permissions": ["LAB_ADMIN", "LAB_EDIT", "LAB_EXEC", "LAB_VIEW"]}
        Each user dict: {"id": "<user-uuid>", "permissions": ["LAB_ADMIN", "LAB_EDIT", "LAB_EXEC", "LAB_VIEW"]}

        Examples:
        - "Give group abc read-only access to lab xyz"
        - "Grant user alice LAB_EDIT and LAB_EXEC permissions on my lab"
        - "Set permissions for lab 123: group xyz gets LAB_ADMIN, user bob gets LAB_VIEW"
        """
        client = get_cml_client_dep()
        try:
            _validate_lab_associations(groups, "group")
            _validate_lab_associations(users, "user")
            payload = {"associations": build_payload(groups=groups, users=users)}
            await client.patch(f"/labs/{lid}", data=payload)
            return True
        except ToolError:
            raise
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error setting lab permissions for lab %s", lid)
            raise ToolError(e)

    @mcp.tool(
        annotations={
            "title": "Create a Full Lab Topology",
            "readOnlyHint": False,
            "destructiveHint": False,
        },
    )
    async def create_full_lab_topology(topology: Topology | dict | str) -> UUID4Type:
        """
        Import a complete CML lab from a Topology object (nodes + links + lab metadata).

        IMPORTANT: `topology` MUST be a structured object (or dict / JSON-encoded object string)
        matching the CML Topology schema with top-level keys `lab`, `nodes`, `links`, and
        optionally `annotations`. Do NOT pass a raw string such as a lab title, a YAML blob,
        or a non-Topology JSON string — those will fail. For simpler use cases, prefer
        `create_empty_lab` followed by `add_node_to_cml_lab` and `connect_two_nodes`.

        Expected shape:
          {
            "lab": {"title": "...", "version": "0.3.0"},
            "nodes": [{"id": "n0", "label": "R1", "node_definition": "iol-xe",
                       "x": 0, "y": 0, "interfaces": [...]}],
            "links": [{"id": "l0", "n1": "n0", "n2": "n1", "i1": "...", "i2": "..."}]
          }

        Required: lab (title, version), nodes (id, x, y, label, node_definition, interfaces),
        links (id, i1, i2, n1, n2). Optional: annotations, smart_annotations.
        Supports RAM, CPU, images, MAC addresses, link conditioning, and node startup configs.

        Examples:
        - "Create a full CML lab with 2 routers, 1 switch, and a firewall in a hub-spoke"
        - "Build a triangle topology with 3 CSR1000v routers"
        - "Set up a lab with an IOSv router connected to an ASAv firewall"
        """
        client = get_cml_client_dep()
        try:
            if isinstance(topology, (dict, str)):
                topology = lenient_construct(Topology, topology)
            return await create_full_topology_from_obj(topology, client)
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error creating lab topology")
            raise ToolError(e)

    @mcp.tool(
        annotations={"title": "Start a CML Lab", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True},
    )
    async def start_cml_lab(
        lid: UUID4Type,
        wait_for_convergence: bool = False,
    ) -> bool:
        """
        Start (boot) a CML lab and all its nodes by lab UUID.

        Set wait_for_convergence=true to block until every node reports a stable state.

        Examples:
        - "Start the lab with ID abc123"
        - "Boot up my OSPF lab"
        - "Power on lab xyz and wait until it converges"
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
            logger.exception("Error starting CML lab %s", lid)
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
        Stop (power off) all running nodes in a CML lab by lab UUID.

        Examples:
        - "Stop my CML lab"
        - "Shut down lab abc123"
        - "Power off all nodes in the OSPF lab"
        """
        client = get_cml_client_dep()
        try:
            await stop_lab(lid, client)
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error stopping CML lab %s", lid)
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
        Wipe a CML lab by UUID -- erases all node disk data and configurations. Lab is stopped first if needed.

        CRITICAL: Destructive and irreversible. Always ask "Confirm wipe of [lab]?" and wait for the
        user's "yes" before invoking this tool.

        Examples:
        - "Wipe the OSPF lab"
        - "Reset lab abc123 to a clean state"
        - "Erase all node data in my CML lab"
        """
        client = get_cml_client_dep()
        try:
            if not await elicit_confirmation(ctx, "Are you sure you want to wipe the lab?"):
                raise Exception("Wipe operation cancelled by user.")
            await wipe_lab(lid, client)
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error wiping CML lab %s", lid)
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
        Delete a CML lab by UUID. Auto-stops and wipes the lab first.

        CRITICAL: Destructive and irreversible. Always ask "Confirm deletion of [lab]?" and wait for the
        user's "yes" before invoking this tool.

        Examples:
        - "Delete lab abc123"
        - "Remove my OSPF lab"
        - "Get rid of the test lab"
        """
        client = get_cml_client_dep()
        try:
            if not await elicit_confirmation(ctx, "Are you sure you want to delete the lab?"):
                raise Exception("Delete operation cancelled by user.")
            await stop_lab(lid, client)  # Ensure the lab is stopped before deletion
            await wipe_lab(lid, client)  # Ensure the lab is wiped before deletion
            await client.delete(f"/labs/{lid}")
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error deleting CML lab %s", lid)
            raise ToolError(e)

    @mcp.tool(
        annotations={"title": "Get a CML Lab by Title", "readOnlyHint": True},
    )
    async def get_cml_lab_by_title(title: LabTitle) -> Lab:
        """
        Look up a single CML lab by its exact, case-sensitive title. Returns the Lab object.

        Examples:
        - "Get the lab titled 'OSPF Practice'"
        - "Find my lab named 'Customer Demo'"
        - "Look up the 'BGP Lab' by name"
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
            logger.exception("Error getting CML lab by title %s", title)
            raise ToolError(e)

    @mcp.tool(
        annotations={"title": "Download lab topology", "readOnlyHint": True},
    )
    async def download_lab_topology(lid: UUID4Type) -> str:
        """
        Download the full topology for a lab by UUID as a YAML string. Present this to the user
        for saving to a .yaml file (e.g. for backup or sharing).

        Examples:
        - "Export lab abc123 as YAML"
        - "Download my OSPF lab topology"
        - "Give me a backup of lab xyz"
        """
        client = get_cml_client_dep()
        try:
            return await download_lab_file(lid, client)
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error downloading lab topology for lab %s", lid)
            raise ToolError(e)

    @mcp.tool(
        annotations={"title": "Clone CML Lab", "readOnlyHint": False, "destructiveHint": False},
    )
    async def clone_cml_lab(lid: UUID4Type, new_title: LabTitle | None = None) -> UUID4Type:
        """
        Clone an existing lab by UUID, optionally with a new title. Returns the new lab's UUID.
        If new_title is omitted, the clone is named "Copy of <original title>".

        Examples:
        - "Clone lab abc123"
        - "Make a copy of my OSPF lab called 'OSPF Lab v2'"
        - "Duplicate the BGP lab"
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
            logger.exception("Error cloning CML lab %s", lid)
            raise ToolError(e)
