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

from enum import StrEnum
from ipaddress import IPv4Address

from pydantic import AnyHttpUrl, Field, IPvAnyAddress
from pydantic_settings import BaseSettings, SettingsConfigDict


class TransportEnum(StrEnum):
    """Transport types supported by the MCP server."""

    HTTP = "http"
    STDIO = "stdio"


class Settings(BaseSettings):
    """Settings for the CML MCP server."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    cml_url: AnyHttpUrl | None = Field(default=None, description="URL of the Cisco Modeling Labs server")
    cml_mcp_remote_server_url: AnyHttpUrl | None = Field(
        default=None, description="URL of the remote CML mcp server. " "Can be read from Swagger API docs"
    )
    cml_username: str | None = Field(default=None, description="Username for CML server authentication")
    cml_password: str | None = Field(default=None, description="Password for CML server authentication")
    cml_verify_ssl: bool = Field(
        default=False,
        description="Whether to verify the CML server's SSL certificate",
    )
    cml_mcp_transport: TransportEnum = Field(
        default=TransportEnum.STDIO,
        description="Transport type for the MCP server",
    )
    cml_mcp_bind: IPvAnyAddress = Field(
        default_factory=lambda: IPv4Address("0.0.0.0"),
        description="IP address to bind the MCP server when transport is HTTP",
    )
    cml_mcp_port: int = Field(
        default=9000,
        description="Port to bind the MCP server when transport is HTTP",
    )
    cml_allowed_urls: list[AnyHttpUrl] = Field(
        default_factory=list,
        description="List of allowed CML server URLs when transport is HTTP.  Empty list allows any URL.",
    )
    cml_url_pattern: str | None = Field(
        default=None,
        description="Regex pattern that the CML server URL must match when transport is HTTP (e.g., '^https://cml\\.example\\.com').",
    )
    cml_mcp_acl_file: str | None = Field(
        default=None,
        description="Path to a YAML file specifying access control lists for various MCP capabilities (only used in HTTP transport mode).",
    )


settings = Settings()
if settings.cml_mcp_remote_server_url:
    if not settings.cml_username or not settings.cml_password:
        raise ValueError("CML_USERNAME, and CML_PASSWORD must be set when using remote MCP server")

elif settings.cml_mcp_transport == TransportEnum.STDIO:
    if not settings.cml_url or not settings.cml_username or not settings.cml_password:
        raise ValueError("CML_URL, CML_USERNAME, and CML_PASSWORD must be set when using stdio transport")
