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

from enum import StrEnum

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

    cml_url: AnyHttpUrl = Field(..., description="URL of the Cisco Modeling Labs server")
    cml_username: str | None = Field(default=None, description="Username for CML server authentication")
    cml_password: str | None = Field(default=None, description="Password for CML server authentication")
    cml_mcp_transport: TransportEnum = Field(
        default=TransportEnum.STDIO,
        description="Transport type for the MCP server",
    )
    cml_mcp_bind: IPvAnyAddress = Field(
        default="0.0.0.0",
        description="IP address to bind the MCP server when transport is HTTP",
    )
    cml_mcp_port: int = Field(
        default=9000,
        description="Port to bind the MCP server when transport is HTTP",
    )


settings = Settings()
if settings.cml_mcp_transport == TransportEnum.STDIO:
    if not settings.cml_username or not settings.cml_password:
        raise ValueError("CML_USERNAME and CML_PASSWORD must be set when using stdio transport")
else:
    # Use '__bogus__' as the default for http to have some initial credentials.  The real
    # values will be provided through Basic Auth.
    settings.cml_username = "__bogus__"
    settings.cml_password = "__bogus__"
