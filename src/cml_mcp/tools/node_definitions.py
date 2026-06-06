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
Node definition tools for CML MCP server.
"""

import logging

import httpx
from fastmcp.exceptions import ToolError

from cml_mcp.cml.simple_webserver.schemas.common import DefinitionID
from cml_mcp.cml.simple_webserver.schemas.node_definitions import NodeDefinition
from cml_mcp.cml_client import CMLClient
from cml_mcp.tools.dependencies import get_cml_client_dep
from cml_mcp.types import SuperSimplifiedNodeDefinitionResponse

logger = logging.getLogger("cml-mcp.tools.node_definitions")


async def get_node_def_details(definition_id: DefinitionID, client: CMLClient) -> NodeDefinition:
    """
    Get detailed information about a specific node definition by its ID.

    Args:
        did (DefinitionID): The node definition ID.

    Returns:
        NodeDefinition: The node definition details.
    """
    node_definition = await client.get(f"/node_definitions/{definition_id}", params={"json": True})
    return NodeDefinition(**node_definition).model_dump(exclude_unset=True)


def register_tools(mcp):
    """Register all node definition tools with the FastMCP server."""

    @mcp.tool(
        annotations={
            "title": "Get All CML Node Definitions",
            "readOnlyHint": True,
        },
    )
    async def get_cml_node_definitions() -> list[SuperSimplifiedNodeDefinitionResponse]:
        """
        List all available node types on this CML server. Returns id, label, general_nature
        (switch/router/server/desktop), and schema_version.

        Use this to discover valid `node_definition` values before calling add_node_to_cml_lab.

        Examples:
        - "What node types can I use in CML?"
        - "List all available device definitions"
        - "Show me the supported routers and switches"
        """

        client = get_cml_client_dep()
        try:
            node_definitions = await client.get("/simplified_node_definitions")
            return [SuperSimplifiedNodeDefinitionResponse(**nd).model_dump(exclude_unset=True) for nd in node_definitions]
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error getting CML node definitions")
            raise ToolError(e)

    @mcp.tool(
        annotations={
            "title": "Get Details About a Node Definition",
            "readOnlyHint": True,
        },
    )
    async def get_node_definition_detail(definition_id: DefinitionID) -> NodeDefinition:
        """
        Get full details for one node definition by id: interfaces, default device config,
        boot options, and resource requirements.

        Examples:
        - "Tell me more about the csr1000v node definition"
        - "How many interfaces does iosv have by default?"
        - "What's the default RAM for an ASAv?"
        """
        client = get_cml_client_dep()
        try:
            return await get_node_def_details(definition_id, client)
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error getting node definition detail for %s", definition_id)
            raise ToolError(e)
