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

import asyncio
import base64
import contextvars
import logging
import os
import re
import tempfile
from typing import Any, Optional

import httpx
from fastmcp import Context, FastMCP
from fastmcp import settings as fastmcp_settings
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware, MiddlewareContext
from mcp.shared.exceptions import McpError
from mcp.types import INVALID_REQUEST, METHOD_NOT_FOUND, ErrorData  # Icon
from pydantic import AnyHttpUrl
from virl2_client.models.cl_pyats import ClPyats, PyatsNotInstalled

from cml_mcp.cml.simple_webserver.schemas.annotations import (
    AnnotationResponse,
    EllipseAnnotation,
    EllipseAnnotationResponse,
    LineAnnotation,
    LineAnnotationResponse,
    RectangleAnnotation,
    RectangleAnnotationResponse,
    TextAnnotation,
    TextAnnotationResponse,
)
from cml_mcp.cml.simple_webserver.schemas.common import DefinitionID, UserName, UUID4Type
from cml_mcp.cml.simple_webserver.schemas.groups import GroupCreate, GroupResponse
from cml_mcp.cml.simple_webserver.schemas.interfaces import InterfaceCreate
from cml_mcp.cml.simple_webserver.schemas.labs import Lab, LabRequest, LabTitle

# from cml_mcp.cml.simple_webserver.schemas.licensing import LicensingStatus
from cml_mcp.cml.simple_webserver.schemas.links import LinkConditionConfiguration, LinkCreate, LinkResponse
from cml_mcp.cml.simple_webserver.schemas.node_definitions import NodeDefinition
from cml_mcp.cml.simple_webserver.schemas.nodes import Node, NodeConfigurationContent, NodeCreate, NodeLabel
from cml_mcp.cml.simple_webserver.schemas.system import SystemHealth, SystemInformation, SystemStats
from cml_mcp.cml.simple_webserver.schemas.topologies import Topology
from cml_mcp.cml.simple_webserver.schemas.users import UserCreate, UserResponse
from cml_mcp.cml_client import CMLClient
from cml_mcp.settings import settings
from cml_mcp.types import ConsoleLogOutput, SimplifiedInterfaceResponse, SuperSimplifiedNodeDefinitionResponse

# Set up logging
logger = logging.getLogger("cml-mcp")
loglevel = logging.DEBUG if os.getenv("DEBUG", "false").lower() == "true" else logging.INFO
logger.setLevel(loglevel)
# Configure handler with format for this module only
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(threadName)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False

# # Enable global debugging for all modules
# logging.basicConfig(level=loglevel, format="%(asctime)s %(levelname)s %(threadName)s %(name)s: %(message)s")
# # Set root logger level
# logging.getLogger().setLevel(loglevel)

# Global singleton client for stdio transport
# Only initialize if we're using stdio transport to avoid resource waste
if settings.cml_mcp_transport == "stdio":
    cml_client = CMLClient(
        str(settings.cml_url),
        settings.cml_username,
        settings.cml_password,
        transport=str(settings.cml_mcp_transport),
        verify_ssl=settings.cml_verify_ssl,
    )
else:
    # In HTTP mode, we don't need a global client - each request creates its own
    cml_client = None  # type: ignore[assignment]

# Context variable to store request-scoped client for HTTP transport
_request_client: contextvars.ContextVar[Optional[CMLClient]] = contextvars.ContextVar("request_client", default=None)

# Context variables for PyATS credentials (per-request isolation)
_pyats_username: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("pyats_username", default=None)
_pyats_password: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("pyats_password", default=None)
_pyats_auth_pass: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("pyats_auth_pass", default=None)


# Provide a custom token validation function.
class CustomHttpRequestMiddleware(Middleware):

    @staticmethod
    def _validate_url(url: AnyHttpUrl | str, allowed_urls: list[AnyHttpUrl], url_pattern: str | None) -> None:
        if not allowed_urls and not url_pattern:
            raise McpError(
                ErrorData(
                    message="At least one of CML_ALLOWED_URLS or CML_URL_PATTERN must be set when using HTTP transport to accept"
                    " client-provided CML server URLs",
                    code=-31003,
                )
            )
        if allowed_urls:
            for allowed_url in allowed_urls:
                if str(url).lower() == str(allowed_url).lower():
                    break
            else:
                raise McpError(
                    ErrorData(
                        message=f"CML server URL '{url}' is not in the list of allowed URLs",
                        code=-31003,
                    )
                )
        if url_pattern:
            if not re.match(url_pattern, str(url)):
                raise McpError(
                    ErrorData(
                        message=f"CML server URL '{url}' does not match the required pattern",
                        code=-31004,
                    )
                )

    async def on_request(self, context: MiddlewareContext, call_next) -> Any:
        # Reset PyATS contextvars for this request
        _pyats_username.set(None)
        _pyats_password.set(None)
        _pyats_auth_pass.set(None)

        headers = get_http_headers()
        cml_url = headers.get("x-cml-server-url")
        if not cml_url:
            if settings.cml_url:
                cml_url = str(settings.cml_url)
            else:
                raise McpError(
                    ErrorData(
                        message="Missing X-CML-Server-URL header and no default CML_URL configured",
                        code=-31002,
                    )
                )
        else:
            # Validate the server URL is allowed.
            CustomHttpRequestMiddleware._validate_url(cml_url, settings.cml_allowed_urls, settings.cml_url_pattern)
        verify_ssl_header = headers.get("x-cml-verify-ssl", "").lower()
        verify_ssl = verify_ssl_header == "true"

        auth_header = headers.get("x-authorization")
        if not auth_header or not auth_header.startswith("Basic "):
            raise McpError(ErrorData(message="Unauthorized: Missing or invalid X-Authorization header", code=-31002))
        parts = auth_header.split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "basic":
            raise McpError(ErrorData(message="Invalid X-Authorization header format. Expected 'Basic <credentials>'", code=-31001))
        try:
            decoded = base64.b64decode(parts[1]).decode("utf-8")
            username, password = decoded.split(":", 1)
        except Exception:
            raise McpError(ErrorData(message="Failed to decode Basic authentication credentials", code=-31002))
        pyats_header = headers.get("x-pyats-authorization")
        if pyats_header and pyats_header.startswith("Basic "):
            pyats_parts = pyats_header.split(" ", 1)
            if len(pyats_parts) != 2 or pyats_parts[0].lower() != "basic":
                raise McpError(
                    ErrorData(message="Invalid X-PyATS-Authorization header format. Expected 'Basic <credentials>'", code=-31001)
                )
            try:
                pyats_decoded = base64.b64decode(pyats_parts[1]).decode("utf-8")
                pyats_username, pyats_password = pyats_decoded.split(":", 1)
                _pyats_username.set(pyats_username)
                _pyats_password.set(pyats_password)
            except Exception:
                raise McpError(ErrorData(message="Failed to decode Basic authentication credentials for PyATS", code=-31002))
            pyats_enable_header = headers.get("x-pyats-enable")
            if pyats_enable_header and pyats_enable_header.startswith("Basic "):
                pyats_enable_parts = pyats_enable_header.split(" ", 1)
                if len(pyats_enable_parts) != 2 or pyats_enable_parts[0].lower() != "basic":
                    raise McpError(ErrorData(message="Invalid X-PyATS-Enable header format. Expected 'Basic <credentials>'", code=-31001))
                try:
                    pyats_enable_decoded = base64.b64decode(pyats_enable_parts[1]).decode("utf-8")
                    pyats_enable_password = pyats_enable_decoded
                    _pyats_auth_pass.set(pyats_enable_password)
                except Exception:
                    raise McpError(ErrorData(message="Failed to decode Basic authentication credentials for PyATS Enable", code=-31002))

        # Create a new client for this request.
        request_client = CMLClient(cml_url, username, password, transport="http", verify_ssl=verify_ssl)
        try:
            await request_client.login()
        except Exception as e:
            logger.error("Authentication failed: %s", str(e), exc_info=True)
            raise McpError(ErrorData(message=f"Unauthorized: {str(e)}", code=-31002))

        # Store the client in context variable for this request
        _request_client.set(request_client)
        try:
            result = await call_next(context)
            logger.debug(f"Request to {cml_url} completed successfully")
            return result
        except Exception as request_error:
            # Log request processing errors for diagnostics
            logger.warning(
                f"Request to {cml_url} failed: {type(request_error).__name__}: {request_error}",
                exc_info=False,  # Don't need full trace for client disconnects
            )
            raise
        finally:
            # Clean up the client after the request
            try:
                await request_client.close()
                logger.debug(f"Successfully closed client for request to {cml_url}")
            except Exception as cleanup_error:
                # Log but don't raise - we don't want cleanup failures to mask the actual error
                logger.error(f"Failed to close HTTP client for {cml_url}: {cleanup_error}", exc_info=True)
            finally:
                # Always clear the context var even if cleanup fails
                _request_client.set(None)


if settings.cml_mcp_transport == "http":
    fastmcp_settings.stateless_http = True

server_mcp = FastMCP(
    name="Cisco Modeling Labs (CML)",
    website_url="https://www.cisco.com/go/cml",
    # icons=[Icon(src="https://www.marcuscom.com/cml-mcp/img/cml_icon.png", mimeType="image/png", sizes=["any"])],
)
app = None
if settings.cml_mcp_transport == "http":
    server_mcp.add_middleware(CustomHttpRequestMiddleware())
    app = server_mcp.http_app()


def get_cml_client_dep() -> CMLClient:
    """
    Dependency function to get the appropriate CML client.
    For HTTP transport, returns the request-scoped client.
    For stdio transport, returns the global singleton.
    """
    if settings.cml_mcp_transport == "http":
        client = _request_client.get()
        if client is None:
            raise RuntimeError(
                "No request client available in contextvar. This usually means the tool "
                "was called outside of a proper HTTP request context (e.g., from a spawned "
                "task without context propagation, or before middleware initialization). "
                "Check that async tasks properly inherit context."
            )
        return client
    else:
        if cml_client is None:
            raise RuntimeError("Global CML client is not initialized. This should never happen in stdio mode.")
        return cml_client


async def get_all_labs(client: CMLClient) -> list[UUID4Type]:
    """
    Get all labs from the CML server.

    Returns:
        list[UUID4Type]: A list of lab IDs.
    """
    labs = await client.get("/labs", params={"show_all": True})
    return [UUID4Type(lab) for lab in labs]


@server_mcp.tool(
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


@server_mcp.tool(
    annotations={
        "title": "Get List of CML Users",
        "readOnlyHint": True,
    }
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


@server_mcp.tool(
    annotations={
        "title": "Create CML User",
        "readOnlyHint": False,
        "destructiveHint": False,
    }
)
async def create_cml_user(user: UserCreate | dict) -> UUID4Type:
    """
    Create user. Requires admin. Returns user UUID.
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


@server_mcp.tool(
    annotations={
        "title": "Delete CML User",
        "readOnlyHint": False,
        "destructiveHint": True,
    }
)
async def delete_cml_user(user_id: UUID4Type, ctx: Context) -> bool:
    """
    Delete user by UUID. Requires admin. CRITICAL: Always confirm
    deletion with user first, unless user is responding "yes" to your confirmation prompt.
    """
    client = get_cml_client_dep()
    try:
        if not await client.is_admin():
            raise ValueError("Only admin users can delete users.")
        # In HTTP transport, skip elicit as it's not compatible with stateless mode
        if client.transport != "http":
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


@server_mcp.tool(
    annotations={
        "title": "Get List of CML Groups",
        "readOnlyHint": True,
    }
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


@server_mcp.tool(
    annotations={
        "title": "Create CML Group",
        "readOnlyHint": False,
        "destructiveHint": False,
    }
)
async def create_cml_group(group: GroupCreate | dict) -> UUID4Type:
    """
    Create group. Requires admin. Returns group UUID.
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


@server_mcp.tool(
    annotations={
        "title": "Delete CML Group",
        "readOnlyHint": False,
        "destructiveHint": True,
    }
)
async def delete_cml_group(group_id: UUID4Type, ctx: Context) -> bool:
    """
    Delete group by UUID. Requires admin. CRITICAL: Always confirm
    deletion with user first, unless user is responding "yes" to your confirmation prompt.
    """
    client = get_cml_client_dep()
    try:
        if not await client.is_admin():
            raise ValueError("Only admin users can delete groups.")
        # In HTTP transport, skip elicit as it's not compatible with stateless mode
        if client.transport != "http":
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


@server_mcp.tool(
    annotations={
        "title": "Get CML System Information",
        "readOnlyHint": True,
    }
)
async def get_cml_information() -> SystemInformation:
    """
    Get server info: version, hostname, system_uptime, ready status, and configuration details.
    """
    client = get_cml_client_dep()
    try:
        info = await client.get("/system_information")
        return SystemInformation(**info).model_dump(exclude_unset=True)
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error getting CML information: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(
    annotations={
        "title": "Get CML System Health",
        "readOnlyHint": True,
    }
)
async def get_cml_status() -> SystemHealth:
    """
    Get health status: compute, controller, virl2, and overall system health indicators.
    """
    client = get_cml_client_dep()
    try:
        status = await client.get("/system_health")
        return SystemHealth(**status).model_dump(exclude_unset=True)
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error getting CML status: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(
    annotations={
        "title": "Get CML System Statistics",
        "readOnlyHint": True,
    }
)
async def get_cml_statistics() -> SystemStats:
    """
    Get resource usage: CPU, memory, disk, running labs/nodes/links counts, and cluster statistics.
    """
    client = get_cml_client_dep()
    try:
        stats = await client.get("/system_stats")
        return SystemStats(**stats).model_dump(exclude_unset=True)
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error getting CML statistics: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(
    annotations={
        "title": "Get CML License Info",
        "readOnlyHint": True,
    }
)
async def get_cml_licensing_details() -> dict[str, Any]:
    """
    Get licensing info: registration status, features, node limits, and expiration dates.
    """
    client = get_cml_client_dep()
    try:
        licensing_info = await client.get("/licensing")
        # This is needed because some clients attempt to serialize the response
        # with Python classes for datetime rather than as pure JSON.  Cursor
        # is notably affected whereas Claude Desktop is not.
        return dict(licensing_info)
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error getting CML licensing details: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(
    annotations={
        "title": "Get All CML Node Definitions",
        "readOnlyHint": True,
    }
)
async def get_cml_node_definitions() -> list[SuperSimplifiedNodeDefinitionResponse]:
    """
    Get available node types. Returns list with id, label, general_nature (switch/router/server/desktop), and schema_version.
    Use for discovering valid node_definition values when creating nodes.
    """
    client = get_cml_client_dep()
    try:
        node_definitions = await client.get("/simplified_node_definitions")
        return [SuperSimplifiedNodeDefinitionResponse(**nd).model_dump(exclude_unset=True) for nd in node_definitions]
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error getting CML node definitions: {str(e)}", exc_info=True)
        raise ToolError(e)


async def get_node_def_details(did: DefinitionID, client: CMLClient) -> NodeDefinition:
    """
    Get detailed information about a specific node definition by its ID.

    Args:
        did (DefinitionID): The node definition ID.

    Returns:
        NodeDefinition: The node definition details.
    """
    node_definition = await client.get(f"/node_definitions/{did}", params={"json": True})
    return NodeDefinition(**node_definition).model_dump(exclude_unset=True)


@server_mcp.tool(
    annotations={
        "title": "Get Details About a Node Definition",
        "readOnlyHint": True,
    }
)
async def get_node_definition_detail(did: DefinitionID) -> NodeDefinition:
    """
    Get detailed node definition by id: interfaces, device config, boot options, and resource requirements.
    """
    client = get_cml_client_dep()
    try:
        return await get_node_def_details(did, client)
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error getting node definition detail for {did}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(
    annotations={
        "title": "Create an Empty Lab",
        "readOnlyHint": False,
        "destructiveHint": False,
    }
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


@server_mcp.tool(
    annotations={
        "title": "Modify CML Lab Properties",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
    }
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


@server_mcp.tool(
    annotations={
        "title": "Create a Full Lab Topology",
        "readOnlyHint": False,
        "destructiveHint": False,
    }
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
        resp = await client.post("/import", data=topology.model_dump(mode="json", exclude_defaults=True, exclude_none=True))
        return UUID4Type(resp["id"])
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error creating lab topology: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(annotations={"title": "Start a CML Lab", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True})
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


@server_mcp.tool(annotations={"title": "Stop a CML Lab", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True})
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


@server_mcp.tool(
    annotations={
        "title": "Wipe a CML Lab",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
    }
)
async def wipe_cml_lab(lid: UUID4Type, ctx: Context) -> bool:
    """
    Wipe lab by UUID. Erases all node data/configurations. CRITICAL: Always confirm
    wipe with user first, unless user is responding "yes" to your confirmation prompt.
    """
    client = get_cml_client_dep()
    try:
        # In HTTP transport, skip elicit as it's not compatible with stateless mode
        if client.transport != "http":
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


@server_mcp.tool(
    annotations={
        "title": "Delete a CML Lab",
        "readOnlyHint": False,
        "destructiveHint": True,
    }
)
async def delete_cml_lab(lid: UUID4Type, ctx: Context) -> bool:
    """
    Delete lab by UUID. Auto-stops and wipes if needed. CRITICAL: Always confirm
    deletion with user first, unless user is responding "yes" to your confirmation prompt.
    """
    client = get_cml_client_dep()
    try:
        # In HTTP transport, skip elicit as it's not compatible with stateless mode
        if client.transport != "http":
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


@server_mcp.tool(
    annotations={
        "title": "Add a Node to a CML Lab",
        "readOnlyHint": False,
        "destructiveHint": False,
    }
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


@server_mcp.tool(
    annotations={
        "title": "Get all annotations for a CML Lab",
        "readOnlyHint": True,
    }
)
async def get_annotations_for_cml_lab(lid: UUID4Type) -> list[AnnotationResponse]:
    """
    Get all visual annotations for a lab by lab UUID. Returns list of AnnotationResponse objects.
    """
    client = get_cml_client_dep()
    try:
        resp = await client.get(f"/labs/{lid}/annotations")
        ann_list = []
        for annotation in resp:
            if annotation.get("type") == "text":
                annotation_obj = TextAnnotationResponse(**annotation)
            elif annotation.get("type") == "rectangle":
                annotation_obj = RectangleAnnotationResponse(**annotation)
            elif annotation.get("type") == "ellipse":
                annotation_obj = EllipseAnnotationResponse(**annotation)
            elif annotation.get("type") == "line":
                annotation_obj = LineAnnotationResponse(**annotation)
            else:
                raise ValueError(
                    f"Invalid annotation type: {annotation.get('type')}. Must be one of 'text', 'rectangle', 'ellipse', or 'line'."
                )
            ann_list.append(annotation_obj.model_dump(exclude_unset=True))
        return ann_list
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error getting annotations for lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(
    annotations={
        "title": "Add an Annotation to a CML Lab",
        "readOnlyHint": False,
        "destructiveHint": False,
    }
)
async def add_annotation_to_cml_lab(
    lid: UUID4Type,
    annotation: EllipseAnnotation | LineAnnotation | RectangleAnnotation | TextAnnotation | dict,
) -> UUID4Type:
    """
    Add visual annotation to lab. Returns annotation UUID.
    Required field: type ("text"/"rectangle"/"ellipse"/"line").

    Common fields: x1, y1 (coords -15000 to 15000), color, border_color, border_style (""/"2,2"/"4,2"),
    thickness (1-32), z_index (-10240 to 10240).

    Rectangle/Ellipse: x2, y2 are WIDTH and HEIGHT from x1,y1, NOT corners! For box (-200,-100) to (200,-50),
    use x1=-200, y1=-100, x2=400, y2=50. Also: rotation (0-360), border_radius (0-128, rectangles only).

    Line: x2, y2 are absolute endpoint coords (unlike rectangles). line_start/line_end: "arrow"/"square"/"circle"/null.

    Text: text_content (max 8192 chars), text_font (required), text_size (1-128), text_unit ("pt"/"px"/"em"), text_bold/text_italic (bool),
    rotation (0-360).
    """
    client = get_cml_client_dep()
    try:
        # XXX The dict usage is a workaround for some LLMs that pass a JSON string
        # representation of the argument object.
        if isinstance(annotation, dict):
            if annotation["type"] == "text":
                annotation = TextAnnotation(**annotation)
            elif annotation["type"] == "rectangle":
                annotation = RectangleAnnotation(**annotation)
            elif annotation["type"] == "ellipse":
                annotation = EllipseAnnotation(**annotation)
            elif annotation["type"] == "line":
                annotation = LineAnnotation(**annotation)
            else:
                raise ValueError(
                    f"Invalid annotation type: {annotation['type']}. Must be one of 'text', 'rectangle', 'ellipse', or 'line'."
                )
        resp = await client.post(f"/labs/{lid}/annotations", data=annotation.model_dump(mode="json", exclude_defaults=True))
        return UUID4Type(resp["id"])
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error adding annotation to lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(
    annotations={
        "title": "Delete an Annotation from a CML Lab",
        "readOnlyHint": False,
        "destructiveHint": True,
    }
)
async def delete_annotation_from_lab(
    lid: UUID4Type,
    annotation_id: UUID4Type,
    ctx: Context,
) -> bool:
    """
    Delete annotation by lab and annotation UUID. CRITICAL: Always confirm
    deletion with user first, unless user is responding "yes" to your confirmation prompt.
    """
    client = get_cml_client_dep()
    try:
        # In HTTP transport, skip elicit as it's not compatible with stateless mode
        if client.transport != "http":
            elicit_supported = True
            try:
                result = await ctx.elicit("Are you sure you want to delete the annotation?", response_type=None)
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
        await client.delete(f"/labs/{lid}/annotations/{annotation_id}")
        return True
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error deleting annotation {annotation_id} from lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(
    annotations={
        "title": "Add an Interface to a CML Node",
        "readOnlyHint": False,
        "destructiveHint": False,
    }
)
async def add_interface_to_node(
    lid: UUID4Type,
    intf: InterfaceCreate | dict,
) -> SimplifiedInterfaceResponse:
    """
    Add interface to node. Returns interface with id, node, slot, type, and MAC address.
    Required: node (UUID). Optional: slot (0-128), mac_address ("00:11:22:33:44:55" format).
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


@server_mcp.tool(
    annotations={
        "title": "Get Interfaces for a CML Node",
        "readOnlyHint": True,
    }
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


@server_mcp.tool(
    annotations={
        "title": "Connect Two Nodes in a CML Lab",
        "readOnlyHint": False,
        "destructiveHint": False,
    }
)
async def connect_two_nodes(
    lid: UUID4Type,
    link_info: LinkCreate | dict,
) -> UUID4Type:
    """
    Create link between two interfaces. Returns link UUID.
    Required: src_int (source interface UUID), dst_int (destination interface UUID).
    """
    client = get_cml_client_dep()
    try:
        # XXX The dict usage is a workaround for some LLMs that pass a JSON string
        # representation of the argument object.
        if isinstance(link_info, dict):
            link_info = LinkCreate(**link_info)
        resp = await client.post(f"/labs/{lid}/links", data=link_info.model_dump(mode="json"))
        return UUID4Type(resp["id"])
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error creating link for {link_info}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(
    annotations={
        "title": "Get All Links for a CML Lab",
        "readOnlyHint": True,
    }
)
async def get_all_links_for_lab(lid: UUID4Type) -> list[LinkResponse]:
    """
    Get lab links by UUID. Returns list with id, label, interface_a, interface_b, node_a, node_b, state, and capture_key.
    """
    client = get_cml_client_dep()
    try:
        resp = await client.get(f"/labs/{lid}/links", params={"data": True})
        return [LinkResponse(**link).model_dump(exclude_unset=True) for link in resp]
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error getting links for lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(annotations={"title": "Apply Link Conditioning", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True})
async def apply_link_conditioning(
    lid: UUID4Type,
    link_id: UUID4Type,
    condition: LinkConditionConfiguration | dict,
) -> bool:
    """
    Configure link network conditions by lab and link UUID.
    Fields (all optional): bandwidth (kbps, 0-10M), latency (ms, 0-10K), loss (%, 0-100), jitter (ms, 0-10K),
    duplicate (%, 0-100), corrupt_prob (%, 0-100), gap (ms), limit (ms), reorder_prob (%, 0-100),
    delay_corr/loss_corr/duplicate_corr/reorder_corr/corrupt_corr (%, 0-100), enabled (bool).
    """
    client = get_cml_client_dep()
    try:
        # XXX The dict usage is a workaround for some LLMs that pass a JSON string
        # representation of the argument object.
        if isinstance(condition, dict):
            condition = LinkConditionConfiguration(**condition)
        await client.patch(f"/labs/{lid}/links/{link_id}/condition", data=condition.model_dump(mode="json", exclude_none=True))
        return True
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error conditioning link {link_id} in lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(annotations={"title": "Configure a CML Node", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True})
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


@server_mcp.tool(annotations={"title": "Get Nodes for a CML Lab", "readOnlyHint": True})
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
            if "operational" in node:
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


@server_mcp.tool(annotations={"title": "Get a CML Lab by Title", "readOnlyHint": True})
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


@server_mcp.tool(annotations={"title": "Stop a CML Node", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True})
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


@server_mcp.tool(annotations={"title": "Start a CML Node", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True})
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


@server_mcp.tool(annotations={"title": "Wipe a CML Node", "readOnlyHint": False, "destructiveHint": True, "idempotentHint": True})
async def wipe_cml_node(lid: UUID4Type, nid: UUID4Type, ctx: Context) -> bool:
    """
    Wipe node by lab and node UUID. Erases all node data. Node must be stopped first. CRITICAL: Always confirm
    wipe with user first, unless user is responding "yes" to your confirmation prompt.
    """
    client = get_cml_client_dep()
    try:
        # In HTTP transport, skip elicit as it's not compatible with stateless mode
        if client.transport != "http":
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


@server_mcp.tool(annotations={"title": "Delete a node from a CML lab.", "readOnlyHint": False, "destructiveHint": True})
async def delete_cml_node(lid: UUID4Type, nid: UUID4Type, ctx: Context) -> bool:
    """
    Delete node by lab and node UUID. Auto-stops and wipes if needed. CRITICAL: Always confirm
    deletion with user first, unless user is responding "yes" to your confirmation prompt.
    """
    client = get_cml_client_dep()
    try:
        # In HTTP transport, skip elicit as it's not compatible with stateless mode
        if client.transport != "http":
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


@server_mcp.tool(
    annotations={
        "title": "Start a CML Link",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
    }
)
async def start_cml_link(lid: UUID4Type, link_id: UUID4Type) -> bool:
    """
    Start link by lab and link UUID. Enables connectivity.
    """
    client = get_cml_client_dep()
    try:
        await client.put(f"/labs/{lid}/links/{link_id}/state/start")
        return True
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error starting CML link {link_id} in lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(
    annotations={
        "title": "Stop a CML Link",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
    }
)
async def stop_cml_link(lid: UUID4Type, link_id: UUID4Type) -> bool:
    """
    Stop link by lab and link UUID. Disables connectivity.
    """
    client = get_cml_client_dep()
    try:
        await client.put(f"/labs/{lid}/links/{link_id}/state/stop")
        return True
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error stopping CML link {link_id} in lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(annotations={"title": "Get Console Logs for a CML Node", "readOnlyHint": True})
async def get_console_log(
    lid: UUID4Type,
    nid: UUID4Type,
) -> list[ConsoleLogOutput]:
    """
    Get console output history by lab and node UUID. Node must be started.
    Returns list of log entries with time (ms since start) and message. Includes all console ports.
    Useful for troubleshooting, monitoring boot progress, and verifying CLI command results.
    """
    client = get_cml_client_dep()
    return_lines = []
    for i in range(0, 2):  # Assume a maximum of 2 consoles per node
        try:
            resp = await client.get(f"/labs/{lid}/nodes/{nid}/consoles/{i}/log")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                continue  # Console index does not exist, try the next one
            else:
                raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error getting console log for node {nid} in lab {lid}: {str(e)}", exc_info=True)
            raise ToolError(e)
        lines = re.split(r"\r?\n", resp)
        for line in lines:
            if not line.startswith("|"):
                if len(return_lines) > 0:
                    # Append to the last message if the line does not start with a timestamp
                    return_lines[-1].message += "\n" + line
                continue
            _, log_time, msg = line.split("|", 2)
            return_lines.append(ConsoleLogOutput(time=int(log_time), message=msg))

    return return_lines


@server_mcp.tool(annotations={"title": "Send CLI Command to CML Node", "readOnlyHint": False, "destructiveHint": True})
async def send_cli_command(
    lid: UUID4Type,
    label: NodeLabel,  # pyright: ignore[reportInvalidTypeForm]
    commands: str,
    config_command: bool = False,
) -> str:
    """
    Send CLI commands to running node by lab UUID and node label. Node must be in BOOTED state.
    CRITICAL: Can modify device state. Review commands before executing, especially with config_command=true.
    Separate multiple commands with newlines.
    config_command=false: exec/operational mode (default). config_command=true: config mode only
    (don't include "configure terminal" or "end").
    Returns command output text. Requires PyATS/Genie libraries.
    """
    client = get_cml_client_dep()

    # Verify vclient is available
    if client.vclient is None:
        raise ToolError(
            "PyATS CLI commands require the virl2_client library. " "Ensure the CML client was initialized with valid credentials."
        )

    # Use asyncio.to_thread to prevent blocking the event loop with synchronous operations
    # and to avoid os.chdir() race conditions between concurrent requests
    try:
        output = await asyncio.to_thread(_send_cli_command_sync, client, lid, label, commands, config_command)
        return output
    except Exception as e:
        logger.error(f"Error sending CLI command '{commands}' to node {label} in lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


def _send_cli_command_sync(
    client: CMLClient,
    lid: UUID4Type,
    label: NodeLabel,  # pyright: ignore[reportInvalidTypeForm]
    commands: str,
    config_command: bool,
) -> str:
    """
    Synchronous helper for send_cli_command to isolate blocking operations in a thread.
    This prevents os.chdir() race conditions and event loop blocking.
    """
    cwd = os.getcwd()  # Save the current working directory
    try:
        os.chdir(tempfile.gettempdir())  # Change to a writable directory (required by pyATS/ClPyats)
        lab = client.vclient.join_existing_lab(str(lid))  # Join the existing lab using the provided lab ID
        try:
            pylab = ClPyats(lab)  # Create a ClPyats object for interacting with the lab
            pylab.sync_testbed(client.vclient.username, client.vclient.password)  # Sync the testbed with CML credentials

            # Set the credentials for all devices other than the Terminal Server
            # For HTTP transport: use contextvars (request-scoped, prevents race conditions)
            # For stdio transport: fall back to environment variables
            for device in pylab._testbed.devices.values():
                if device.name != "terminal_server":
                    device.credentials.default.username = _pyats_username.get() or os.getenv("PYATS_USERNAME", "cisco")
                    device.credentials.default.password = _pyats_password.get() or os.getenv("PYATS_PASSWORD", "cisco")
                    device.credentials.enable.password = _pyats_auth_pass.get() or os.getenv("PYATS_AUTH_PASS", "cisco")

        except PyatsNotInstalled:
            raise ImportError(
                "PyATS and Genie are required to send commands to running devices.  See the documentation on how to install them."
            )
        if config_command:
            # Send the command as a configuration command
            results = pylab.run_config_command(str(label), commands)
        else:
            # Send the command as an exec/operational command
            results = pylab.run_command(str(label), commands)

        # Genie may return dict output where the key is the command and the value is its output.
        if isinstance(results, dict):
            output = ""
            for cmd, cmd_output in results.items():
                output += f"Command: {cmd}\nOutput:\n{cmd_output}\n"
        else:
            output = str(results)

        return output
    finally:
        os.chdir(cwd)  # Restore the original working directory
