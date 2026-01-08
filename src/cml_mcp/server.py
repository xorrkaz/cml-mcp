# Copyright (c) 2025  Cisco Systems, Inc.
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
import logging
import os
import re
import tempfile
from typing import Any

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
    EllipseAnnotation,
    LineAnnotation,
    RectangleAnnotation,
    TextAnnotation,
    AnnotationResponse,
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

cml_client = CMLClient(
    str(settings.cml_url),
    settings.cml_username,
    settings.cml_password,
    transport=str(settings.cml_mcp_transport),
    verify_ssl=settings.cml_verify_ssl,
)


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
        # Reset client state
        cml_client.token = None
        cml_client.admin = None
        os.environ.pop("PYATS_USERNAME", None)
        os.environ.pop("PYATS_PASSWORD", None)
        os.environ.pop("PYATS_AUTH_PASS", None)

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
                os.environ["PYATS_USERNAME"] = pyats_username
                os.environ["PYATS_PASSWORD"] = pyats_password
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
                    os.environ["PYATS_AUTH_PASS"] = pyats_enable_password
                except Exception:
                    raise McpError(ErrorData(message="Failed to decode Basic authentication credentials for PyATS Enable", code=-31002))

        cml_client.update_client(cml_url, username, password, verify_ssl)
        try:
            await cml_client.check_authentication()
        except Exception as e:
            logger.error("Authentication failed: %s", str(e), exc_info=True)
            raise McpError(ErrorData(message=f"Unauthorized: {str(e)}", code=-31002))
        return await call_next(context)


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


async def get_all_labs() -> list[UUID4Type]:
    """
    Get all labs from the CML server.

    Returns:
        list[UUID4Type]: A list of lab IDs.
    """
    labs = await cml_client.get("/labs", params={"show_all": True})
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

    # # Clients like to pass "null" as a string vs. null as a None type.
    # if not user or str(user) == "null":
    #     user = settings.cml_username  # Default to the configured username

    try:
        # If the requested user is not the configured user and is not an admin, deny access
        # if user and not await cml_client.is_admin():
        #     raise ValueError("User is not an admin and cannot view all labs.")
        ulabs = []
        # Get all labs from the CML server
        labs = await get_all_labs()
        for lab in labs:
            # For each lab, get its details
            lab_details = await cml_client.get(f"/labs/{lab}")
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
    try:
        users = await cml_client.get("/users")
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
    try:
        if not await cml_client.is_admin():
            raise ValueError("Only admin users can create new users.")
        # XXX The dict usage is a workaround for some LLMs that pass a JSON string
        # representation of the argument object.
        if isinstance(user, dict):
            user = UserCreate(**user)
        resp = await cml_client.post("/users", data=user.model_dump(mode="json", exclude_none=True))
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
    Delete user by UUID. Requires admin. IMPORTANT: Ask user for confirmation before executing.
    """
    try:
        if not await cml_client.is_admin():
            raise ValueError("Only admin users can delete users.")
        elicit_supported = True
        try:
            result = await ctx.elicit("Are you sure you want to delete this user?", response_type=None)
        except McpError as me:
            if me.error.code == METHOD_NOT_FOUND or me.error.code == INVALID_REQUEST:
                elicit_supported = False
            else:
                raise me
        if not elicit_supported or result.action == "accept":
            await cml_client.delete(f"/users/{user_id}")
            return True
        else:
            raise Exception("Delete operation cancelled by user.")
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
    try:
        groups = await cml_client.get("/groups")
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
    try:
        if not await cml_client.is_admin():
            raise ValueError("Only admin users can create new groups.")
        # XXX The dict usage is a workaround for some LLMs that pass a JSON string
        # representation of the argument object.
        if isinstance(group, dict):
            group = GroupCreate(**group)
        resp = await cml_client.post("/groups", data=group.model_dump(mode="json", exclude_none=True))
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
    Delete group by UUID. Requires admin. IMPORTANT: Ask user for confirmation before executing.
    """
    try:
        if not await cml_client.is_admin():
            raise ValueError("Only admin users can delete groups.")
        elicit_supported = True
        try:
            result = await ctx.elicit("Are you sure you want to delete this group?", response_type=None)
        except McpError as me:
            if me.error.code == METHOD_NOT_FOUND or me.error.code == INVALID_REQUEST:
                elicit_supported = False
            else:
                raise me
        if not elicit_supported or result.action == "accept":
            await cml_client.delete(f"/groups/{group_id}")
            return True
        else:
            raise Exception("Delete operation cancelled by user.")
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
    try:
        info = await cml_client.get("/system_information")
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
    try:
        status = await cml_client.get("/system_health")
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
    try:
        stats = await cml_client.get("/system_stats")
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
    try:
        licensing_info = await cml_client.get("/licensing")
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
    try:
        node_definitions = await cml_client.get("/simplified_node_definitions")
        return [SuperSimplifiedNodeDefinitionResponse(**nd).model_dump(exclude_unset=True) for nd in node_definitions]
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error getting CML node definitions: {str(e)}", exc_info=True)
        raise ToolError(e)


async def get_node_def_details(did: DefinitionID) -> NodeDefinition:
    """
    Get detailed information about a specific node definition by its ID.

    Args:
        did (DefinitionID): The node definition ID.

    Returns:
        NodeDefinition: The node definition details.
    """
    node_definition = await cml_client.get(f"/node_definitions/{did}", params={"json": True})
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
    try:
        return await get_node_def_details(did)
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
    try:
        # XXX The dict usage is a workaround for some LLMs that pass a JSON string
        # representation of the argument object.
        if isinstance(lab, dict):
            lab = LabRequest(**lab)
        resp = await cml_client.post("/labs", data=lab.model_dump(mode="json", exclude_none=True))
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
    try:
        # XXX The dict usage is a workaround for some LLMs that pass a JSON string
        # representation of the argument object.
        if isinstance(lab, dict):
            lab = LabRequest(**lab)
        await cml_client.patch(f"/labs/{lid}", data=lab.model_dump(mode="json", exclude_none=True))
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
    try:
        # XXX The dict usage is a workaround for some LLMs that pass a JSON string
        # representation of the argument object.
        if isinstance(topology, dict):
            topology = Topology(**topology)
        resp = await cml_client.post("/import", data=topology.model_dump(mode="json", exclude_defaults=True, exclude_none=True))
        return UUID4Type(resp["id"])
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error creating lab topology: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(annotations={"title": "Start a CML Lab", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True})
async def start_cml_lab(lid: UUID4Type, wait_for_convergence: bool = False) -> bool:
    """
    Start lab by UUID. Set wait_for_convergence=true to wait until all nodes reach stable state.
    """
    try:
        await cml_client.put(f"/labs/{lid}/start")
        if wait_for_convergence:
            while True:
                converged = await cml_client.get(f"/labs/{lid}/check_if_converged")
                if converged:
                    break
                await asyncio.sleep(3)
        return True
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error starting CML lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


async def stop_lab(lid: UUID4Type) -> None:
    """
    Stop a CML lab by its ID.

    Args:
        lid (UUID4Type): The lab ID.
    """
    await cml_client.put(f"/labs/{lid}/stop")


async def wipe_lab(lid: UUID4Type) -> None:
    """
    Wipe a CML lab by its ID.

    Args:
        lid (UUID4Type): The lab ID.
    """
    await cml_client.put(f"/labs/{lid}/wipe")


@server_mcp.tool(annotations={"title": "Stop a CML Lab", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True})
async def stop_cml_lab(lid: UUID4Type) -> bool:
    """
    Stop lab by UUID. Stops all running nodes.
    """
    try:
        await stop_lab(lid)
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
    Wipe lab by UUID. Erases all node data/configurations. IMPORTANT: Ask user for confirmation before executing.
    """
    try:
        elicit_supported = True
        try:
            result = await ctx.elicit("Are you sure you want to wipe the lab?", response_type=None)
        except McpError as me:
            if me.error.code == METHOD_NOT_FOUND or me.error.code == INVALID_REQUEST:
                elicit_supported = False
            else:
                raise me
        if not elicit_supported or result.action == "accept":
            await wipe_lab(lid)
            return True
        else:
            raise Exception("Wipe operation cancelled by user.")
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
    Delete lab by UUID. Auto-stops and wipes if needed. IMPORTANT: Ask user for confirmation before executing.
    """
    try:

        elicit_supported = True
        try:
            result = await ctx.elicit("Are you sure you want to delete the lab?", response_type=None)
        except McpError as me:
            if me.error.code == METHOD_NOT_FOUND or me.error.code == INVALID_REQUEST:
                elicit_supported = False
            else:
                raise me
        if not elicit_supported or result.action == "accept":
            await stop_lab(lid)  # Ensure the lab is stopped before deletion
            await wipe_lab(lid)  # Ensure the lab is wiped before deletion
            await cml_client.delete(f"/labs/{lid}")
            return True
        else:
            raise Exception("Delete operation cancelled by user.")
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error deleting CML lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


async def add_interface(lid: UUID4Type, intf: InterfaceCreate) -> SimplifiedInterfaceResponse:
    """
    Add an interface to a CML lab by its lab ID.

    Args:
        lid (UUID4Type): The lab ID.
        intf (InterfaceCreate): The interface definition as an InterfaceCreate object.

    Returns:
        InterfaceResponse: The added interface details.
    """
    resp = await cml_client.post(f"/labs/{lid}/interfaces", data=intf.model_dump(mode="json", exclude_none=True))
    return SimplifiedInterfaceResponse(**resp).model_dump(exclude_unset=True)


@server_mcp.tool(
    annotations={
        "title": "Add a Node to a CML Lab",
        "readOnlyHint": False,
        "destructiveHint": False,
    }
)
async def add_node_to_cml_lab(lid: UUID4Type, node: NodeCreate | dict) -> UUID4Type:
    """
    Add node to lab. Returns node UUID. Auto-creates default interfaces per node definition.
    Required: x (-15000 to 15000), y (-15000 to 15000), label (1-128 chars), node_definition (e.g., "alpine", "iosv").
    Optional: image_definition, ram (MB), cpus, cpu_limit (%), data_volume (GB), boot_disk_size (GB), tags, configuration, parameters.
    """
    try:
        # XXX The dict usage is a workaround for some LLMs that pass a JSON string
        # representation of the argument object.
        if isinstance(node, dict):
            node = NodeCreate(**node)
        resp = await cml_client.post(
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
    try:
        resp = await cml_client.get(f"/labs/{lid}/annotations")
        return [AnnotationResponse(**annotation).model_dump(exclude_unset=True) for annotation in resp]
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
    lid: UUID4Type, annotation: EllipseAnnotation | LineAnnotation | RectangleAnnotation | TextAnnotation | dict
) -> UUID4Type:
    """
    Add visual annotation to lab. Returns annotation UUID.
    Types: text (with text_content, text_font, text_size), rectangle (with border_radius), ellipse,
    line (with line_start/line_end: arrow/square/circle).
    Common: type, x1, y1 (coords -15000 to 15000), color, border_color, border_style (""/"2,2"/"4,2"),
    thickness (1-32), z_index (-10240 to 10240).
    Rectangle/ellipse: x2, y2. Text: rotation (0-360), text_bold, text_italic. Line: x2, y2.
    """
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
        resp = await cml_client.post(f"/labs/{lid}/annotations", data=annotation.model_dump(mode="json", exclude_defaults=True))
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
async def delete_annotation_from_lab(lid: UUID4Type, annotation_id: UUID4Type, ctx: Context) -> bool:
    """
    Delete annotation by lab and annotation UUID. IMPORTANT: Ask user for confirmation before executing.
    """
    try:
        elicit_supported = True
        try:
            result = await ctx.elicit("Are you sure you want to delete the annotation?", response_type=None)
        except McpError as me:
            if me.error.code == METHOD_NOT_FOUND or me.error.code == INVALID_REQUEST:
                elicit_supported = False
            else:
                raise me
        if not elicit_supported or result.action == "accept":
            await cml_client.delete(f"/labs/{lid}/annotations/{annotation_id}")
            return True
        else:
            raise Exception("Delete operation cancelled by user.")
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
async def add_interface_to_node(lid: UUID4Type, intf: InterfaceCreate | dict) -> SimplifiedInterfaceResponse:
    """
    Add interface to node. Returns interface with id, node, slot, type, and MAC address.
    Required: node (UUID). Optional: slot (0-128), mac_address ("00:11:22:33:44:55" format).
    """
    try:
        # XXX The dict usage is a workaround for some LLMs that pass a JSON string
        # representation of the argument object.
        if isinstance(intf, dict):
            intf = InterfaceCreate(**intf)
        return await add_interface(lid, intf)
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
async def get_interfaces_for_node(lid: UUID4Type, nid: UUID4Type) -> list[SimplifiedInterfaceResponse]:
    """
    Get node interfaces by lab and node UUID. Returns list with id, node, label, slot, type, MAC address, and IP config.
    """
    try:
        resp = await cml_client.get(f"/labs/{lid}/nodes/{nid}/interfaces", params={"data": True, "operational": False})
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
async def connect_two_nodes(lid: UUID4Type, link_info: LinkCreate | dict) -> UUID4Type:
    """
    Create link between two interfaces. Returns link UUID.
    Required: src_int (source interface UUID), dst_int (destination interface UUID).
    """
    try:
        # XXX The dict usage is a workaround for some LLMs that pass a JSON string
        # representation of the argument object.
        if isinstance(link_info, dict):
            link_info = LinkCreate(**link_info)
        resp = await cml_client.post(f"/labs/{lid}/links", data=link_info.model_dump(mode="json"))
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
    try:
        resp = await cml_client.get(f"/labs/{lid}/links", params={"data": True})
        return [LinkResponse(**link).model_dump(exclude_unset=True) for link in resp]
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error getting links for lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(annotations={"title": "Apply Link Conditioning", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True})
async def apply_link_conditioning(lid: UUID4Type, link_id: UUID4Type, condition: LinkConditionConfiguration | dict) -> bool:
    """
    Configure link network conditions by lab and link UUID.
    Fields (all optional): bandwidth (kbps, 0-10M), latency (ms, 0-10K), loss (%, 0-100), jitter (ms, 0-10K),
    duplicate (%, 0-100), corrupt_prob (%, 0-100), gap (ms), limit (ms), reorder_prob (%, 0-100),
    delay_corr/loss_corr/duplicate_corr/reorder_corr/corrupt_corr (%, 0-100), enabled (bool).
    """
    try:
        # XXX The dict usage is a workaround for some LLMs that pass a JSON string
        # representation of the argument object.
        if isinstance(condition, dict):
            condition = LinkConditionConfiguration(**condition)
        await cml_client.patch(f"/labs/{lid}/links/{link_id}/condition", data=condition.model_dump(mode="json", exclude_none=True))
        return True
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error conditioning link {link_id} in lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(annotations={"title": "Configure a CML Node", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True})
async def configure_cml_node(lid: UUID4Type, nid: UUID4Type, config: NodeConfigurationContent) -> bool:
    """
    Set node startup config by lab and node UUID. Node must be in CREATED state (new or wiped).
    More efficient than starting node and sending CLI. Config is string with device commands.
    """
    payload = {"configuration": str(config)}
    try:
        await cml_client.patch(f"/labs/{lid}/nodes/{nid}", data=payload)
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
    try:
        resp = await cml_client.get(f"/labs/{lid}/nodes", params={"data": True, "operational": True, "exclude_configurations": True})
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
    try:
        labs = await get_all_labs()
        for lid in labs:
            lab = await cml_client.get(f"/labs/{lid}")
            if lab["lab_title"] == str(title):
                return Lab(**lab).model_dump(exclude_unset=True)
        raise ValueError(f"Lab with title '{title}' not found.")
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error getting CML lab by title {title}: {str(e)}", exc_info=True)
        raise ToolError(e)


async def stop_node(lid: UUID4Type, nid: UUID4Type) -> None:
    """
    Stop a CML node by its lab ID and node ID.

    Args:
        lid (UUID4Type): The lab ID.
        nid (UUID4Type): The node ID.
    """
    await cml_client.put(f"/labs/{lid}/nodes/{nid}/state/stop")


async def wipe_node(lid: UUID4Type, nid: UUID4Type) -> None:
    """
    Wipe a CML node by its lab ID and node ID.

    Args:
        lid (UUID4Type): The lab ID.
        nid (UUID4Type): The node ID.
    """
    await cml_client.put(f"/labs/{lid}/nodes/{nid}/wipe_disks")


@server_mcp.tool(annotations={"title": "Stop a CML Node", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True})
async def stop_cml_node(lid: UUID4Type, nid: UUID4Type) -> bool:
    """
    Stop node by lab and node UUID. Powers down the node.
    """
    try:
        await stop_node(lid, nid)
        return True
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error stopping CML node {nid} in lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(annotations={"title": "Start a CML Node", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True})
async def start_cml_node(lid: UUID4Type, nid: UUID4Type, wait_for_convergence: bool = False) -> bool:
    """
    Start node by lab and node UUID. Set wait_for_convergence=true to wait until node reaches stable state.
    """
    try:
        await cml_client.put(f"/labs/{lid}/nodes/{nid}/state/start")
        if wait_for_convergence:
            while True:
                converged = await cml_client.get(f"/labs/{lid}/nodes/{nid}/check_if_converged")
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
    Wipe node by lab and node UUID. Erases all node data. Node must be stopped first. IMPORTANT: Ask user for confirmation before executing.
    """
    try:
        elicit_supported = True
        try:
            result = await ctx.elicit("Are you sure you want to wipe the node?", response_type=None)
        except McpError as me:
            if me.error.code == METHOD_NOT_FOUND or me.error.code == INVALID_REQUEST:
                elicit_supported = False
            else:
                raise me
        if not elicit_supported or result.action == "accept":
            await wipe_node(lid, nid)
            return True
        else:
            raise Exception("Wipe operation cancelled by user.")
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error wiping CML node {nid} in lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(annotations={"title": "Delete a node from a CML lab.", "readOnlyHint": False, "destructiveHint": True})
async def delete_cml_node(lid: UUID4Type, nid: UUID4Type, ctx: Context) -> bool:
    """
    Delete node by lab and node UUID. Auto-stops and wipes if needed. IMPORTANT: Ask user for confirmation before executing.
    """
    try:
        elicit_supported = True
        try:
            result = await ctx.elicit("Are you sure you want to delete the node?", response_type=None)
        except McpError as me:
            if me.error.code == METHOD_NOT_FOUND or me.error.code == INVALID_REQUEST:
                elicit_supported = False
            else:
                raise me
        if not elicit_supported or result.action == "accept":
            await stop_node(lid, nid)  # Ensure the node is stopped before deletion
            await wipe_node(lid, nid)
            await cml_client.delete(f"/labs/{lid}/nodes/{nid}")
            return True
        else:
            raise Exception("Delete operation cancelled by user.")
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
    try:
        await cml_client.put(f"/labs/{lid}/links/{link_id}/state/start")
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
    try:
        await cml_client.put(f"/labs/{lid}/links/{link_id}/state/stop")
        return True
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error stopping CML link {link_id} in lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)


@server_mcp.tool(annotations={"title": "Get Console Logs for a CML Node", "readOnlyHint": True})
async def get_console_log(lid: UUID4Type, nid: UUID4Type) -> list[ConsoleLogOutput]:
    """
    Get console output history by lab and node UUID. Node must be started.
    Returns list of log entries with time (ms since start) and message. Includes all console ports.
    Useful for troubleshooting, monitoring boot progress, and verifying CLI command results.
    """
    return_lines = []
    for i in range(0, 2):  # Assume a maximum of 2 consoles per node
        try:
            resp = await cml_client.get(f"/labs/{lid}/nodes/{nid}/consoles/{i}/log")
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
    lid: UUID4Type, label: NodeLabel, commands: str, config_command: bool = False  # pyright: ignore[reportInvalidTypeForm]
) -> str:
    """
    Send CLI commands to running node by lab UUID and node label. Node must be in BOOTED state.
    IMPORTANT: Can modify device state. Review commands before executing, especially with config_command=true.
    Separate multiple commands with newlines.
    config_command=false: exec/operational mode (default). config_command=true: config mode only
    (don't include "configure terminal" or "end").
    Returns command output text. Requires PyATS/Genie libraries.
    """
    cwd = os.getcwd()  # Save the current working directory
    try:
        os.chdir(tempfile.gettempdir())  # Change to a writable directory (required by pyATS/ClPyats)
        lab = cml_client.vclient.join_existing_lab(str(lid))  # Join the existing lab using the provided lab ID
        try:
            pylab = ClPyats(lab)  # Create a ClPyats object for interacting with the lab
            pylab.sync_testbed(cml_client.vclient.username, cml_client.vclient.password)  # Sync the testbed with CML credentials

            # Set the credentials for all devices other than the Terminal Server from ENVs, default to cisco
            for device in pylab._testbed.devices.values():
                if device.name != "terminal_server":
                    device.credentials.default.username = os.getenv("PYATS_USERNAME", "cisco")
                    device.credentials.default.password = os.getenv("PYATS_PASSWORD", "cisco")
                    device.credentials.enable.password = os.getenv("PYATS_AUTH_PASS", "cisco")

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
    except Exception as e:
        logger.error(f"Error sending CLI command '{commands}' to node {label} in lab {lid}: {str(e)}", exc_info=True)
        raise ToolError(e)
    finally:
        os.chdir(cwd)  # Restore the original working directory
