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
User and group management tools for CML MCP server.
"""

import logging
from typing import Annotated

import httpx
from fastmcp import Context
from fastmcp.exceptions import ToolError
from mcp.shared.exceptions import McpError
from mcp.types import INVALID_REQUEST, METHOD_NOT_FOUND

from cml_mcp.cml.simple_webserver.schemas.common import GroupName, UserFullName, UserName, UUID4Type
from cml_mcp.cml.simple_webserver.schemas.groups import GroupCreate, GroupResponse
from cml_mcp.cml.simple_webserver.schemas.users import UserCreate, UserResponse
from cml_mcp.tools.dependencies import get_cml_client_dep
from cml_mcp.tools.model_helpers import build_payload, field_from

logger = logging.getLogger("cml-mcp.tools.users_groups")


def register_tools(mcp):  # noqa: C901
    """Register all user and group management tools with the FastMCP server."""

    @mcp.tool(
        annotations={
            "title": "Get List of CML Users",
            "readOnlyHint": True,
        },
    )
    async def get_cml_users() -> list[UserResponse]:
        """
        List all CML users. Returns id, username, fullname, email, admin status, groups,
        and resource_pool.

        Examples:
        - "Show me all CML users"
        - "Who has accounts on this CML server?"
        - "List the users and their groups"
        """

        client = get_cml_client_dep()
        try:
            users = await client.get("/users")
            return [UserResponse(**user).model_dump(exclude_unset=True) for user in users]
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error getting CML user information")
            raise ToolError(e)

    # Source schema: UserCreate (cml/simple_webserver/schemas/users.py)
    # Exposed: username, password, fullname, description, email, admin, groups, associations, resource_pool, opt_in, tour_version, pubkey
    # Omitted: (none - all user-meaningful fields exposed)
    @mcp.tool(
        annotations={
            "title": "Create CML User",
            "readOnlyHint": False,
            "destructiveHint": False,
        },
    )
    async def create_cml_user(
        username: UserName,
        password: Annotated[str, field_from(UserCreate, "password")],
        fullname: UserFullName | None = None,
        description: Annotated[str | None, field_from(UserCreate, "description")] = None,
        email: Annotated[str | None, field_from(UserCreate, "email")] = None,
        admin: Annotated[bool | None, field_from(UserCreate, "admin")] = None,
        groups: Annotated[list[str] | None, field_from(UserCreate, "groups")] = None,
        associations: Annotated[list[dict] | None, field_from(UserCreate, "associations")] = None,
        resource_pool: Annotated[UUID4Type | None, field_from(UserCreate, "resource_pool")] = None,
        opt_in: Annotated[str | None, field_from(UserCreate, "opt_in")] = None,
        tour_version: Annotated[str | None, field_from(UserCreate, "tour_version")] = None,
        pubkey: Annotated[str | None, field_from(UserCreate, "pubkey")] = None,
    ) -> UUID4Type:
        """
        Create a new CML user. Requires admin privileges. Returns the new user's UUID.

        Required: username, password. Optional: fullname, description, email (max 128 chars),
        groups (list of group UUIDs), admin (bool), resource_pool (UUID), associations (list of lab dicts),
        opt_in ("UNSET"/"ACCEPTED"/"DECLINED"), tour_version (max 128 chars), pubkey (SSH public key).

        Examples:
        - "Create a user named alice with password ChangeMe123"
        - "Add a new admin account 'bob'"
        - "Provision a CML user for carol"
        """
        client = get_cml_client_dep()
        try:
            if not await client.is_admin():
                raise ValueError("Only admin users can create new users.")

            payload = build_payload(
                username=username,
                password=password,
                fullname=fullname,
                description=description,
                email=email,
                admin=admin,
                groups=groups,
                associations=associations,
                resource_pool=str(resource_pool) if resource_pool is not None else None,
                opt_in=opt_in,
                tour_version=tour_version,
                pubkey=pubkey,
            )
            resp = await client.post("/users", data=payload)
            return UUID4Type(resp["id"])
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error creating CML user")
            raise ToolError(e)

    @mcp.tool(
        annotations={
            "title": "Delete CML User",
            "readOnlyHint": False,
            "destructiveHint": True,
        },
    )
    async def delete_cml_user(user_id: UUID4Type, ctx: Context) -> bool:
        """
        Delete a CML user by UUID. Requires admin privileges.

        CRITICAL: Destructive and irreversible. Always ask "Confirm deletion of [user]?" and
        wait for the user's "yes" before invoking this tool.

        Examples:
        - "Delete user alice"
        - "Remove the bob account from CML"
        - "Get rid of user xyz"
        """
        client = get_cml_client_dep()
        try:
            if not await client.is_admin():
                raise ValueError("Only admin users can delete users.")
            elicit_supported = True
            try:
                result = await ctx.elicit("Are you sure you want to delete this user?", response_type=None)
            except McpError as me:
                if me.error.code == METHOD_NOT_FOUND or me.error.code == INVALID_REQUEST:
                    elicit_supported = False
                else:
                    raise me
            except Exception as e:
                # Handle stream closure errors (common in stateless HTTP when client disconnects)
                # Treat as if elicit is not supported and proceed without confirmation
                logger.debug("elicit() failed (possibly client disconnect): %s: %s", type(e).__name__, e)
                elicit_supported = False
            if elicit_supported and result.action != "accept":
                raise Exception("Delete operation cancelled by user.")
            await client.delete(f"/users/{user_id}")
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error deleting CML user")
            raise ToolError(e)

    @mcp.tool(
        annotations={
            "title": "Get List of CML Groups",
            "readOnlyHint": True,
        },
    )
    async def get_cml_groups() -> list[GroupResponse]:
        """
        List all CML groups. Returns id, name, description, members (user UUIDs), and lab
        associations.

        Examples:
        - "List all CML groups"
        - "Who's in the engineers group?"
        - "Show me group memberships"
        """
        client = get_cml_client_dep()
        try:
            groups = await client.get("/groups")
            return [GroupResponse(**group).model_dump(exclude_unset=True) for group in groups]
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error getting CML group information")
            raise ToolError(e)

    # Source schema: GroupCreate (cml/simple_webserver/schemas/groups.py)
    # Exposed: name, description, members, associations
    # Omitted: (none - all user-meaningful fields exposed)
    @mcp.tool(
        annotations={
            "title": "Create CML Group",
            "readOnlyHint": False,
            "destructiveHint": False,
        },
    )
    async def create_cml_group(
        name: GroupName,
        description: Annotated[str | None, field_from(GroupCreate, "description")] = None,
        members: Annotated[list[str] | None, field_from(GroupCreate, "members")] = None,
        associations: Annotated[list[dict] | None, field_from(GroupCreate, "associations")] = None,
    ) -> UUID4Type:
        """
        Create a new CML group. Requires admin privileges. Returns the new group's UUID.

        Required: name (1-64 chars). Optional: description, members (list of user UUIDs),
        associations (list of lab/group association dicts).

        Examples:
        - "Create a group called 'engineers'"
        - "Add a new CML group named 'students'"
        - "Set up a group for the QA team"
        """
        client = get_cml_client_dep()
        try:
            if not await client.is_admin():
                raise ValueError("Only admin users can create new groups.")

            payload = build_payload(
                name=name,
                members=members or [],
                description=description,
                associations=associations,
            )
            resp = await client.post("/groups", data=payload)
            return UUID4Type(resp["id"])
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error creating CML group")
            raise ToolError(e)

    @mcp.tool(
        annotations={
            "title": "Delete CML Group",
            "readOnlyHint": False,
            "destructiveHint": True,
        },
    )
    async def delete_cml_group(group_id: UUID4Type, ctx: Context) -> bool:
        """
        Delete a CML group by UUID. Requires admin privileges.

        CRITICAL: Destructive and irreversible. Always ask "Confirm deletion of [group]?" and
        wait for the user's "yes" before invoking this tool.

        Examples:
        - "Delete the 'students' group"
        - "Remove group xyz"
        - "Get rid of the QA team group"
        """
        client = get_cml_client_dep()
        try:
            if not await client.is_admin():
                raise ValueError("Only admin users can delete groups.")
            elicit_supported = True
            try:
                result = await ctx.elicit("Are you sure you want to delete this group?", response_type=None)
            except McpError as me:
                if me.error.code == METHOD_NOT_FOUND or me.error.code == INVALID_REQUEST:
                    elicit_supported = False
                else:
                    raise me
            except Exception as e:
                # Handle stream closure errors (common in stateless HTTP when client disconnects)
                # Treat as if elicit is not supported and proceed without confirmation
                logger.debug("elicit() failed (possibly client disconnect): %s: %s", type(e).__name__, e)
                elicit_supported = False
            if elicit_supported and result.action != "accept":
                raise Exception("Delete operation cancelled by user.")
            await client.delete(f"/groups/{group_id}")
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error deleting CML group")
            raise ToolError(e)
