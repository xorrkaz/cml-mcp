# Copyright (c) 2025-2026  Cisco Systems, Inc.
# All rights reserved.

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

    @mcp.tool(
        annotations={
            "title": "Get Details About a Node Definition",
            "readOnlyHint": True,
        },
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
