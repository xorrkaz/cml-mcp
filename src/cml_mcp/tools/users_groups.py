# Copyright (c) 2025-2026  Cisco Systems, Inc.
# All rights reserved.

"""
User and group management tools for CML MCP server.
"""

import logging

import httpx
from fastmcp import Context
from fastmcp.exceptions import ToolError
from mcp.shared.exceptions import McpError
from mcp.types import INVALID_REQUEST, METHOD_NOT_FOUND

from cml_mcp.cml.simple_webserver.schemas.common import UUID4Type
from cml_mcp.cml.simple_webserver.schemas.groups import GroupCreate, GroupResponse
from cml_mcp.cml.simple_webserver.schemas.users import UserCreate, UserResponse
from cml_mcp.tools.dependencies import get_cml_client_dep
from cml_mcp.tools.model_helpers import lenient_construct

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

    @mcp.tool(
        annotations={
            "title": "Create CML User",
            "readOnlyHint": False,
            "destructiveHint": False,
        },
    )
    async def create_cml_user(user: UserCreate | dict | str) -> UUID4Type:
        """
        Create a new CML user. Requires admin privileges. Returns the new user's UUID.

        Required: username, password. Optional: fullname, description, email, groups
        (UUID list), admin (bool), resource_pool (UUID).

        Examples:
        - "Create a user named alice with password ChangeMe123"
        - "Add a new admin account 'bob'"
        - "Provision a CML user for carol"
        """
        client = get_cml_client_dep()
        try:
            if not await client.is_admin():
                raise ValueError("Only admin users can create new users.")
            if isinstance(user, (dict, str)):
                user = lenient_construct(UserCreate, user)
            resp = await client.post("/users", data=user.model_dump(mode="json", exclude_defaults=True, exclude_none=True))
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

    @mcp.tool(
        annotations={
            "title": "Create CML Group",
            "readOnlyHint": False,
            "destructiveHint": False,
        },
    )
    async def create_cml_group(group: GroupCreate | dict | str) -> UUID4Type:
        """
        Create a new CML group. Requires admin privileges. Returns the new group's UUID.

        Required: name. Optional: description, members (user UUID list), associations (lab
        permissions).

        Examples:
        - "Create a group called 'engineers'"
        - "Add a new CML group named 'students'"
        - "Set up a group for the QA team"
        """
        client = get_cml_client_dep()
        try:
            if not await client.is_admin():
                raise ValueError("Only admin users can create new groups.")
            if isinstance(group, (dict, str)):
                group = lenient_construct(GroupCreate, group)
            resp = await client.post("/groups", data=group.model_dump(mode="json", exclude_none=True))
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
