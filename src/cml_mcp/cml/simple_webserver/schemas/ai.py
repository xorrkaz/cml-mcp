#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#
from pydantic import BaseModel, Field
from simple_webserver.schemas.common import StringDict


class MCPServerConfiguration(BaseModel, extra="forbid"):
    """MCP server configuration."""

    command: str = Field(..., description="Command to execute MCP server.")
    args: list[str] = Field(..., description="Arguments for MCP server command.")
    env: StringDict = Field(..., description="Environment variables for MCP server configuration.")


class MCPConfigurationResponse(BaseModel, extra="forbid"):
    """Configuration for a single MCP client."""

    mcpServers: dict[str, MCPServerConfiguration] = Field(..., description="MCP server configurations.")
