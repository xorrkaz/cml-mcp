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
        Get CML server info: version, hostname, uptime, ready status, and configuration details.

        Examples:
        - "What version of CML is this?"
        - "Show me the CML server info"
        - "How long has the CML server been up?"
        """

        client = get_cml_client_dep()
        try:
            info = await client.get("/system_information")
            return SystemInformation(**info).model_dump(exclude_unset=True)
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error getting CML information")
            raise ToolError(e)

    @mcp.tool(
        annotations={
            "title": "Get CML System Health",
            "readOnlyHint": True,
        },
    )
    async def get_cml_status() -> SystemHealth:
        """
        Get CML system health: compute, controller, virl2, and overall health indicators.

        Examples:
        - "Is CML healthy?"
        - "Check the CML server status"
        - "Are all CML components running?"
        """
        client = get_cml_client_dep()
        try:
            status = await client.get("/system_health")
            return SystemHealth(**status).model_dump(exclude_unset=True)
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error getting CML status")
            raise ToolError(e)

    @mcp.tool(
        annotations={
            "title": "Get CML System Statistics",
            "readOnlyHint": True,
        },
    )
    async def get_cml_statistics() -> SystemStats:
        """
        Get CML resource usage: CPU, memory, disk, and counts of running labs/nodes/links and
        cluster stats.

        Examples:
        - "How much CPU and memory is CML using?"
        - "Show me how busy the CML server is"
        - "How many labs and nodes are running?"
        """
        client = get_cml_client_dep()
        try:
            stats = await client.get("/system_stats")
            return SystemStats(**stats).model_dump(exclude_unset=True)
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error getting CML statistics")
            raise ToolError(e)

    @mcp.tool(
        annotations={
            "title": "Get CML License Info",
            "readOnlyHint": True,
        },
    )
    async def get_cml_licensing_details() -> dict[str, Any]:
        """
        Get CML licensing info: registration status, features, node limits, and expiration dates.

        Examples:
        - "Is CML licensed?"
        - "When does my CML license expire?"
        - "How many nodes can I run on this license?"
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
            logger.exception("Error getting CML licensing details")
            raise ToolError(e)
