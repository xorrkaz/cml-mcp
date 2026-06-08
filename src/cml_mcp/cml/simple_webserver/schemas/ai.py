#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#
from pydantic import BaseModel, Field

from simple_webserver.schemas.common import OneLineStr, StringDict


class MCPServerConfiguration(BaseModel, extra="forbid"):
    """MCP server configuration."""

    command: OneLineStr = Field(..., description="Command to execute MCP server.")
    args: list[OneLineStr] = Field(..., description="Arguments for MCP server command.")
    env: StringDict = Field(
        ..., description="Environment variables for MCP server configuration."
    )


class MCPConfigurationResponse(BaseModel, extra="forbid"):
    """Configuration for a single MCP client."""

    # ruff N815: camelCase required to match MCP protocol JSON schema
    mcp_servers: dict[OneLineStr, MCPServerConfiguration] = Field(
        ..., alias="mcpServers", description="MCP server configurations."
    )
