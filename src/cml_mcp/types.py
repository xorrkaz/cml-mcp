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

from typing import Literal

from pydantic import BaseModel, Field

from cml_mcp.cml.simple_webserver.schemas.common import DefinitionID, LinuxInterfaceName, UUID4Type
from cml_mcp.cml.simple_webserver.schemas.node_definitions import General


class SimplifiedInterfaces(BaseModel, extra="ignore"):
    """
    Interface configurations.
    """

    serial_ports: int = Field(
        ...,
        description="""
            Number of serial ports (console, aux, ...). Maximum value is 4 for KVM
            and 2 for Docker/IOL nodes.
        """,
        ge=0,
        le=4,
    )
    default_console: int | None = Field(
        default=None,
        description="Default serial port for console connections.",
        ge=0,
        le=4,
    )
    has_loopback_zero: bool = Field(..., description="Has `loopback0` interface (used with ANK).")
    min_count: int | None = Field(
        default=None,
        description="Minimal number of physical interfaces needed to start a node.",
        ge=0,
        le=64,
    )
    default_count: int | None = Field(default=None, description="Default number of physical interfaces.", ge=1, le=64)
    iol_static_ethernets: Literal[0, 4, 8, 12, 16] = Field(
        default=0,
        description="Only for IOL nodes, the number of static Ethernet interfaces"
        " preceding any serial interface; default 0 means "
        "all interfaces are Ethernet.",
    )


class SimplifiedDevice(BaseModel, extra="ignore"):
    interfaces: SimplifiedInterfaces = Field(...)


class SuperSimplifiedNodeDefinitionResponse(BaseModel, extra="ignore"):
    id: DefinitionID = Field(
        ...,
        description="""
            A symbolic name used to identify this node definition, such as `iosv` or
            `asav`.
        """,
    )
    general: General = Field(...)
    device: SimplifiedDevice = Field(...)
    image_definitions: list[DefinitionID] = Field(default_factory=list)


class SimplifiedInterfaceBase(BaseModel, extra="ignore"):
    """Interface object."""

    label: str = Field(default=None)
    is_connected: bool = Field(default=None, description="Whether this interface is connected (in-use).")


class SimplifiedInterfaceResponse(SimplifiedInterfaceBase, extra="ignore"):
    """The response body is a JSON interface object."""

    id: UUID4Type = Field(..., description="ID of the interface.")
    label: str = Field(...)
    device_name: LinuxInterfaceName | None = Field(default=None, max_length=64, description="Device name (operational).")


class ConsoleLogOutput(BaseModel, extra="forbid"):
    """Console log output at a specific time."""

    time: int = Field(..., description="The number of milliseconds since the node booted when this log line was recorded.")
    message: str = Field(..., description="The log message content.")
