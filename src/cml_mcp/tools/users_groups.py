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
        Retrieve all users. Returns list with id, username, fullname, email, admin status, groups, and resource_pool.
        """
        client = get_cml_client_dep()
        try:
            users = await client.get("/users")
            return [UserResponse(**user).model_dump(exclude_unset=True) for user in users]
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error getting CML user information: {str(e)}", exc_info=True)
            raise ToolError(e)

    @mcp.tool(
        annotations={
            "title": "Create CML User",
            "readOnlyHint": False,
            "destructiveHint": False,
        },
    )
    async def create_cml_user(user: UserCreate | dict) -> UUID4Type:
        """
        Create user. Requires admin. Returns user UUID.
        Input: user object. Prefer a JSON object; JSON-encoded object strings are accepted.
        Required: username, password. Optional: fullname, description, email, groups (UUID list), admin (bool), resource_pool (UUID).
        """
        client = get_cml_client_dep()
        try:
            if not await client.is_admin():
                raise ValueError("Only admin users can create new users.")
            # XXX The dict usage is a workaround for some LLMs that pass a JSON string
            # representation of the argument object.
            if isinstance(user, dict):
                user = UserCreate(**user)
            resp = await client.post("/users", data=user.model_dump(mode="json", exclude_none=True))
            return UUID4Type(resp["id"])
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error creating CML user: {str(e)}", exc_info=True)
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
        Delete user by UUID. Requires admin. CRITICAL: Always ask "Confirm deletion of [item]?" and wait for
        user's "yes" before deleting.
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
                logger.debug(f"elicit() failed (possibly client disconnect): {type(e).__name__}: {e}")
                elicit_supported = False
            if elicit_supported and result.action != "accept":
                raise Exception("Delete operation cancelled by user.")
            await client.delete(f"/users/{user_id}")
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error deleting CML user: {str(e)}", exc_info=True)
            raise ToolError(e)

    @mcp.tool(
        annotations={
            "title": "Get List of CML Groups",
            "readOnlyHint": True,
        },
    )
    async def get_cml_groups() -> list[GroupResponse]:
        """
        Retrieve all groups. Returns list with id, name, description, members (user UUIDs), and lab associations.
        """
        client = get_cml_client_dep()
        try:
            groups = await client.get("/groups")
            return [GroupResponse(**group).model_dump(exclude_unset=True) for group in groups]
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error getting CML group information: {str(e)}", exc_info=True)
            raise ToolError(e)

    @mcp.tool(
        annotations={
            "title": "Create CML Group",
            "readOnlyHint": False,
            "destructiveHint": False,
        },
    )
    async def create_cml_group(group: GroupCreate | dict) -> UUID4Type:
        """
        Create group. Requires admin. Returns group UUID.
        Input: group object. Prefer a JSON object; JSON-encoded object strings are accepted.
        Required: name. Optional: description, members (user UUID list), associations (lab permissions).
        """
        client = get_cml_client_dep()
        try:
            if not await client.is_admin():
                raise ValueError("Only admin users can create new groups.")
            # XXX The dict usage is a workaround for some LLMs that pass a JSON string
            # representation of the argument object.
            if isinstance(group, dict):
                group = GroupCreate(**group)
            resp = await client.post("/groups", data=group.model_dump(mode="json", exclude_none=True))
            return UUID4Type(resp["id"])
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error creating CML group: {str(e)}", exc_info=True)
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
        Delete group by UUID. Requires admin. CRITICAL: Always ask "Confirm deletion of [item]?" and wait for
        user's "yes" before deleting.
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
                logger.debug(f"elicit() failed (possibly client disconnect): {type(e).__name__}: {e}")
                elicit_supported = False
            if elicit_supported and result.action != "accept":
                raise Exception("Delete operation cancelled by user.")
            await client.delete(f"/groups/{group_id}")
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error deleting CML group: {str(e)}", exc_info=True)
            raise ToolError(e)
