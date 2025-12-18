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
from mcp.types import INVALID_REQUEST, METHOD_NOT_FOUND, ErrorData, Icon
from pydantic import AnyHttpUrl
from virl2_client.models.cl_pyats import ClPyats, PyatsNotInstalled

from cml_mcp.cml.simple_webserver.schemas.annotations import EllipseAnnotation, LineAnnotation, RectangleAnnotation, TextAnnotation
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
        if verify_ssl_header:
            verify_ssl = verify_ssl_header == "true"
        else:
            verify_ssl = False

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

icon_data_url = """
data:image/png;base64,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
"""

server_mcp = FastMCP(
    name="Cisco Modeling Labs (CML)",
    website_url="https://www.cisco.com/go/cml",
    icons=[Icon(src=icon_data_url.strip(), mimeType="image/png", sizes=["any"])],
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
    Get the list of labs for a specific user or all labs if the user is an admin.
    To get labs for the current user, leave the "user" argument blank.
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
    Get the list of users from the CML server.
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
    Create a new user on the CML server and return their ID.

    The UserCreate schema supports the following fields:
    - username (str): The username of the new user.
    - password (str): The password of the new user.
    - fullname (str, optional): The full name of the new user.
    - description (str, optional): A description of the new user.
    - email (str, optional): The email address of the new user.
    - groups (list[str], optional): A list of group IDs to which the new user should be added.
    - admin (bool, optional): Whether the new user should have admin privileges.
    - resource_pool (str, optional): The resource pool ID to which the new user should be assigned.
    - opt_in (bool, optional): Whether the new user has opted in to receive communications.
    - tour_version (str, optional): The version of the introduction tour that the new user has seen.

    Only admin users can create new users.
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
    Delete a user from the CML server.

    Before running this tool make sure to ask the user if they're sure they want to delete this user and wait for a response.
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
    Get the list of groups from the CML server.
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
    Create a new group on the CML server and return its ID.

    The GroupCreate schema supports the following fields:
    - name (str): The name of the new group.
    - description (str, optional): A description of the new group.
    - members (list[str], optional): A list of user IDs to be added to the new group.
    - associations (list[LabGroupAssociation], optional): A list of lab/group associations.

    Only admin users can create new groups.
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
    Delete a group from the CML server.

    Before running this tool make sure to ask the user if they're sure they want to delete this group and wait for a response.
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
    Get information about the CML server.
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
    Get the status of the CML server.
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
    Get statistics about the CML server.
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
    Get licensing details from the CML server.
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
    Get the list of node definitions from the CML server.
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
    Get detailed information about a specific node definition by its ID.
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
    """Creates an empty lab topology in CML using the provided LabRequest definition and return its ID.

    The LabRequest schema supports the following fields:

    - title (str, optional): Title of the lab (1-64 characters).
    - owner (str, optional): UUID of the lab owner.
    - description (str, optional): Free-form textual description of the lab (max 4096 characters).
    - notes (str, optional): Additional notes for the lab (max 32768 characters).
    - associations (LabAssociations, optional): Object specifying lab/group and lab/user associations:
        - groups (list[LabGroupAssociation], optional): Each with:
            - id (str): UUID of the group.
            - permissions (list[str]): Permissions for the group ("lab_admin", "lab_edit", "lab_exec", "lab_view").
        - users (list[LabUserAssociation], optional): Each with:
            - id (str): UUID of the user.
            - permissions (list[str]): Permissions for the user ("lab_admin", "lab_edit", "lab_exec", "lab_view").
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
    Modify an existing CML lab's details using the provided LabRequest definition.

    The LabRequest schema supports the following fields:
    - title (str, optional): Title of the lab (1-64 characters).
    - owner (str, optional): UUID of the lab owner.
    - description (str, optional): Free-form textual description of the lab (max 4096 characters).
    - notes (str, optional): Additional notes for the lab (max 32768 characters).
    - associations (LabAssociations, optional): Object specifying lab/group and lab/user associations:
        - groups (list[LabGroupAssociation], optional): Each with:
            - id (str): UUID of the group.
            - permissions (list[str]): Permissions for the group ("lab_admin", "lab_edit", "lab_exec", "lab_view").
        - users (list[LabUserAssociation], optional): Each with:
            - id (str): UUID of the user.
            - permissions (list[str]): Permissions for the user ("lab_admin", "lab_edit", "lab_exec", "lab_view").
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
    Create a new, full lab topology in CML using a Topology object and return its ID.

    The Topology schema allows you to define all aspects of a lab in a single request, including:
      - Lab details: title, description, notes, and schema version.
      - Nodes: each with coordinates, label, node definition, image, RAM, CPU, tags, interfaces, and optional configuration.
      - Interfaces: type, slot, MAC address, label, and node association.
      - Links: connections between interfaces/nodes, with optional label and link conditioning (bandwidth, latency, loss, jitter, etc.).
      - Annotations: visual elements (text, rectangle, ellipse, line) for documentation or highlighting.
      - Smart annotations: advanced grouped/styled annotation objects.

    The Topology object must include at least:
      - lab: LabTopology (with version, title, description, notes)
      - nodes: list of NodeTopology objects (each with id, x, y, label, node_definition, interfaces)
      - links: list of LinkTopology objects (each with id, i1, i2, n1, n2)

    Optional fields:
      - annotations: list of annotation objects (text, rectangle, ellipse, line)
      - smart_annotations: list of SmartAnnotationBase objects
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
    Start a CML lab by its ID.

    If wait_for_convergence is True, the tool will wait for the lab to reach a stable state before returning.
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
    Stop a CML lab by its ID.
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
    Wipe a CML lab by its ID.

    Before running this tool make sure to ask the user if they're sure they want to wipe this lab and wait for a response.
    Wiping the lab will remove all the data from all the nodes within the lab.
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
    Delete a CML lab by its ID. If the lab is running and/or not wiped, it will be stopped and wiped first.

    Before running this tool make sure to ask the user if they're sure they want to delete this lab and
    wait for a response.
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
    Adds a node to a CML lab and returns the ID of the newly created node.

    The node argument must conform to the NodeCreate schema.

    Upon successful creation, the function also creates the default number of interfaces for the node,
    as determined by its node definition.  Therefore, before adding new interfaces to a node, check
    if it already has the required interfaces.

    NodeCreate schema highlights:
        - x (int): X coordinate (-15000 to 15000).
        - y (int): Y coordinate (-15000 to 15000).
        - label (str): Node label (1-128 characters).
        - node_definition (str): Node definition ID (1-250 characters).
        - Optional: image_definition, ram, cpu_limit, data_volume, boot_disk_size, hide_links, tags, cpus, configuration, parameters.
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
        "title": "Add an Annotation to a CML Lab",
        "readOnlyHint": False,
        "destructiveHint": False,
    }
)
async def add_annotation_to_cml_lab(
    lid: UUID4Type, annotation: EllipseAnnotation | LineAnnotation | RectangleAnnotation | TextAnnotation | dict
) -> UUID4Type:
    """
    Add a visual annotation to a CML lab topology and return its ID.

    The annotation must be an object that conforms to one of the following schemas:
            TextAnnotation schema:
                - type: "text"
                - x1, y1: Anchor coordinates (-15000 to 15000)
                - rotation: Degrees (0–360)
                - border_color: Border color (e.g., "#FF00FF", "rgba(255,0,0,0.5)", "lightgoldenrodyellow")
                - border_style: Border style ("": solid, "2,2": dotted, "4,2": dashed)
                - color: Fill color
                - thickness: Line thickness (1–32)
                - z_index: Layer (-10240 to 10240)
                - text_content: Text string (max 8192 chars)
                - text_font: Font name (max 128 chars)
                - text_size: Size (1–128)
                - text_unit: Unit ("pt", "px", "em")
                - text_bold: Bold (bool)
                - text_italic: Italic (bool)

            RectangleAnnotation schema:
                - type: "rectangle"
                - x1, y1: Anchor coordinates (-15000 to 15000)
                - x2, y2: Additional coordinates (width/height)
                - rotation: Degrees (0–360)
                - border_color: Border color
                - border_style: Border style
                - color: Fill color
                - thickness: Line thickness (1–32)
                - z_index: Layer (-10240 to 10240)
                - border_radius: Border radius (0–128)

            EllipseAnnotation schema:
                - type: "ellipse"
                - x1, y1: Anchor coordinates (-15000 to 15000)
                - x2, y2: Additional coordinates (width/height/radius)
                - rotation: Degrees (0–360)
                - border_color: Border color
                - border_style: Border style
                - color: Fill color
                - thickness: Line thickness (1–32)
                - z_index: Layer (-10240 to 10240)

            LineAnnotation schema:
                - type: "line"
                - x1, y1: Start coordinates (-15000 to 15000)
                - x2, y2: End coordinates (-15000 to 15000)
                - border_color: Border color
                - border_style: Border style
                - color: Fill color
                - thickness: Line thickness (1–32)
                - z_index: Layer (-10240 to 10240)
                - line_start: Line start style ("arrow", "square", "circle", or null)
                - line_end: Line end style ("arrow", "square", "circle", or null)
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
    Deletes a visual annotation from a CML lab topology by its ID and lab ID.

    Before using this tool, make sure to make sure to ask the user if they really
    want to delete the annotation and wait for a response.
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
    Adds a network interface to a node within a CML lab and returns the interface details.

    The interface is provided as an `InterfaceCreate` object matching the following schema:

    InterfaceCreate schema:
    - node (str, required): UUID4 of the target node. Example: "90f84e38-a71c-4d57-8d90-00fa8a197385"
    - slot (int, optional): Number of slots (0-128). Default: None.
    - mac_address (str or None, optional): MAC address in Linux format ("00:11:22:33:44:55"). Default: None.
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
    Get a list of interfaces for a specific node in a CML lab by its lab ID and node ID.
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
    Creates a link between two interfaces in a CML lab and return the link ID.

    This function establishes a connection between two nodes by creating a link using their interface UUIDs within a specified lab.
    The link is defined by the `link_info` parameter, which must include the source and destination interface UUIDs.

        lid (UUID4Type): The UUID4 identifier of the CML lab where the link will be created.
        link_info (LinkCreate): Details of the link to create. Must include:
            - src_int (str): UUID4 of the source interface.
            - dst_int (str): UUID4 of the destination interface.
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
    Get all links for a CML lab by its ID.
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
    Apply link conditioning to a specific link within a CML lab.

    This function configures network conditions (such as bandwidth, latency, loss, jitter, etc.) on a link identified by its lab ID
    and link ID.

        lid (UUID4Type): The unique identifier (UUID4) of the CML lab.
        link_id (UUID4Type): The unique identifier (UUID4) of the link within the lab.
        condition (LinkConditionConfiguration): The configuration object specifying link conditioning parameters. Fields include:
            - bandwidth (int | None): Bandwidth in kbps (0–10,000,000).
            - latency (int | None): Delay in ms (0–10,000).
            - delay_corr (float | int | None): Delay correlation in percent (0–100).
            - limit (int | None): Limit in ms (0–10,000).
            - loss (float | int | None): Packet loss in percent (0–100).
            - loss_corr (float | int | None): Loss correlation in percent (0–100).
            - gap (int | None): Gap between packets in ms (0–10,000).
            - duplicate (float | int | None): Probability of duplicate packets in percent (0–100).
            - duplicate_corr (float | int | None): Duplicate correlation in percent (0–100).
            - jitter (int | None): Jitter in ms (0–10,000).
            - reorder_prob (float | int | None): Probability of packet reordering in percent (0–100).
            - reorder_corr (float | int | None): Reorder correlation in percent (0–100).
            - corrupt_prob (float | int | None): Probability of corrupted frames in percent (0–100).
            - corrupt_corr (float | int | None): Corruption correlation in percent (0–100).
            - enabled (bool): Whether conditioning is enabled.
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
    Configure a node in a CML lab by its lab ID and node ID. The node must either be newly created or wiped (i.e.,
    in a CREATED state).  For new or wiped nodes, this is more efficient than starting the node and sending CLI
    commands.

    Args:
        lid (UUID4Type): The lab ID.
        nid (UUID4Type): The node ID.
        config (NodeConfigurationContent): A string representing the configuration content for the node.
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
    Get a list of nodes for a CML lab by its ID.
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
    Get a CML lab by its title.
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
    Stop a node in a CML lab by its lab ID and node ID.
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
    Start a node in a CML lab by its lab ID and node ID.

    If wait_for_convergence is True, the tool will wait for the node to reach a stable state before returning.
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
    Wipe a node in a CML lab by its lab ID and node ID. Node must be stopped first.

    Before using this tool, make sure to make sure to ask the user if they really
    want to wipe the node and wait for a response.  Wiping the node will remove all data from the node.
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
    Delete a node from a CML lab by its lab ID and node ID.

    If the node is running or not wiped, this tool will stop and wipe the node first.

    Before running this tool, make sure to ask the user if they really
    want to delete the node and wait for a response.  Deleting a node will remove all of its data.
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
    Start a link in a CML lab by its lab ID and link ID.
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
    Stop a link in a CML lab by its lab ID and link ID.
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
    Get the console log for a CML node by its lab ID and node ID.  For nodes with multiple consoles,
    logs from all consoles are returned.  To use this tool, the node must be started.  The console log
    provides a history of console output from the node which can be useful for troubleshooting and monitoring,
    as well as assessing work done via CLI commands.

    The returned list contains ConsoleLogLine objects with the following fields:
        - time (int): The number of milliseconds since the node started when the log line was generated.
        - message (str): The console log message.
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
    Send CLI command(s) to a node in a CML lab by its lab ID and node label. Nodes must be started and ready
    (i.e., in a BOOTED state) for this to succeed.

    Multiple commands can be sent separated by newlines.

    When config_command is True, provide only configuration commands—do not include commands to enter or exit configuration
    mode (e.g., "configure terminal" or "end"). When config_command is False, only operational/exec commands should be sent;
    configuration commands are not allowed.
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
