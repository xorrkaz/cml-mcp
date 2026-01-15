# Copyright (c) 2025-2026  Cisco Systems, Inc.
# All rights reserved.

"""
System information and statistics tools for CML MCP server.
"""

import logging
from typing import Any

import httpx
from fastmcp.exceptions import ToolError

from cml_mcp.cml.simple_webserver.schemas.system import SystemHealth, SystemInformation, SystemStats
from cml_mcp.tools.dependencies import get_cml_client_dep

logger = logging.getLogger("cml-mcp.tools.system")


def register_tools(mcp):
    """Register all system-related tools with the FastMCP server."""

    @mcp.tool(
        annotations={
            "title": "Get CML System Information",
            "readOnlyHint": True,
        },
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

    @mcp.tool(
        annotations={
            "title": "Get CML System Health",
            "readOnlyHint": True,
        },
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

    @mcp.tool(
        annotations={
            "title": "Get CML System Statistics",
            "readOnlyHint": True,
        },
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

    @mcp.tool(
        annotations={
            "title": "Get CML License Info",
            "readOnlyHint": True,
        },
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
