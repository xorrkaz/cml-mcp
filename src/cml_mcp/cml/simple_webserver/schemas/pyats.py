#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#
from typing import Literal

from pydantic import BaseModel, Field

from simple_webserver.schemas.common import (
    DeviceNature,
    IPAddress,
    OneLineStr,
    PyAtsCredentials,
    PyAtsOs,
    PyAtsToken,
    StringDict,
    UUID4Type,
)
from simple_webserver.schemas.interfaces import InterfaceLabel
from simple_webserver.schemas.nodes import NodeLabel


class PyAtsConnectionDetails(BaseModel, extra="forbid"):
    command: OneLineStr | None = Field(default=None, examples=["open ..."])
    protocol: OneLineStr = Field(..., examples=["ssh"])
    proxy: OneLineStr | None = Field(default=None)
    ip: IPAddress | OneLineStr | None = Field(
        default=None, description="IP address or hostname of the device"
    )
    port: int | None = Field(default=None, ge=0, le=65535)


class Connections(BaseModel, extra="forbid"):
    a: PyAtsConnectionDetails | None = Field(default=None)
    cli: PyAtsConnectionDetails | None = Field(default=None)
    defaults: StringDict | None = Field(default=None)


class PyAtsDeviceCredentials(BaseModel, extra="forbid"):
    default: PyAtsCredentials | None = Field(default=None)
    enable: PyAtsCredentials | None = Field(default=None)


class PyAtsDevice(BaseModel, extra="forbid"):
    connections: Connections
    credentials: PyAtsDeviceCredentials
    type: DeviceNature = Field(..., examples=["router"])
    os: PyAtsOs = Field(...)
    platform: PyAtsToken = Field(default=None)
    model: PyAtsToken = Field(default=None)


class PyAtsInterfaceSummary(BaseModel, extra="forbid"):
    link: UUID4Type | None = Field(default=None, description="Link ID if present")
    type: Literal["ethernet", "loopback"] = Field(
        ..., description="interface type", examples=["ethernet"]
    )


class PyAtsDeviceTopology(BaseModel, extra="forbid"):
    interfaces: dict[InterfaceLabel, PyAtsInterfaceSummary]


class PyAtsServerCustom(BaseModel, extra="forbid"):
    port: int = Field(..., ge=0, le=65535)


class PyAtsServer(BaseModel, extra="forbid"):
    type: Literal["server"] = Field(..., examples=["server"])
    address: IPAddress | OneLineStr = Field(
        ..., description="IP address or hostname of the server"
    )
    custom: PyAtsServerCustom
    credentials: PyAtsDeviceCredentials


class PyAtsTestbedServers(BaseModel, extra="forbid"):
    terminal_server: PyAtsServer = Field(
        ...,
        description=(
            "Console-server alias referenced by connections[*].proxy; "
            "required by genie's pyATS 25.1+ proxy lookup."
        ),
    )


class PyAtsTestbedHeader(BaseModel, extra="forbid"):
    name: OneLineStr = Field(
        ...,
        min_length=1,
        max_length=64,
        description="The name of the testbed.",
        examples=["Lab at Thu 07:09 AM"],
    )
    servers: PyAtsTestbedServers = Field(
        ..., description="Server aliases referenced by connections[*].proxy."
    )


class PyAtsTestbed(BaseModel, extra="forbid"):
    devices: dict[NodeLabel, PyAtsDevice] = Field(..., description="Device list")
    testbed: PyAtsTestbedHeader = Field(
        ..., description="Testbed metadata (name and server aliases)"
    )
    topology: dict[NodeLabel, PyAtsDeviceTopology] = Field(
        ..., description="Topology connections list"
    )
