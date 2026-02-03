#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#
from typing import Annotated, Literal

from pydantic import BaseModel, Field
from simple_webserver.schemas.common import (
    DeviceNature,
    DriverType,
    IPAddress,
    StringDict,
    UUID4Type,
)
from simple_webserver.schemas.interfaces import InterfaceLabel
from simple_webserver.schemas.nodes import NodeLabel

PyAtsOs = Annotated[
    str,
    Field(
        description="The operating system as defined / understood by pyATS.",
        min_length=1,
        max_length=32,
        examples=["linux"],
    ),
]


PyAtsModel = Annotated[
    str,
    Field(
        description="The device model as defined by pyATS / Unicon.",
        min_length=1,
        max_length=32,
        examples=["cirrus"],
    ),
]

PyatsUsername = Annotated[
    str | None,
    Field(
        description="Username to use with pyATS / Unicon",
        min_length=1,
        max_length=64,
    ),
]

PyatsPassword = Annotated[
    str | None,
    Field(
        description="Password to use with pyATS / Unicon",
        min_length=1,
        max_length=128,
    ),
]


class PyAtsConnectionDetails(BaseModel, extra="forbid"):
    command: str | None = Field(default=None, examples=["open ..."])
    protocol: str = Field(..., examples=["ssh"])
    proxy: str | None = Field(default=None)
    ip: IPAddress | str | None = Field(default=None, description="IP address or hostname of the device")
    port: int | None = Field(default=None, ge=0, le=65535)


class Connections(BaseModel, extra="forbid"):
    a: PyAtsConnectionDetails | None = Field(default=None)
    cli: PyAtsConnectionDetails | None = Field(default=None)
    defaults: StringDict | None = Field(default=None)


class PyAtsCredentials(BaseModel, extra="forbid"):
    username: PyatsUsername = Field(default=None)
    password: PyatsPassword = Field(default=None)


class PyAtsDeviceCredentials(BaseModel, extra="forbid"):
    default: PyAtsCredentials


class PyAtsDevice(BaseModel, extra="forbid"):
    connections: Connections
    credentials: PyAtsDeviceCredentials
    os: PyAtsOs = Field(...)
    type: DeviceNature = Field(..., examples=["router"])
    model: PyAtsModel | None = Field(default=None)
    platform: DriverType | None = Field(default=None, examples=["iosv"])


class PyAtsInterfaceSummary(BaseModel, extra="forbid"):
    link: UUID4Type | None = Field(default=None, description="Link ID if present")
    type: Literal["ethernet", "loopback"] = Field(..., description="interface type", examples=["ethernet"])


class PyAtsDeviceTopology(BaseModel, extra="forbid"):
    interfaces: dict[InterfaceLabel, PyAtsInterfaceSummary]


class PyAtsTestbedName(BaseModel, extra="forbid"):
    name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="The name of the testbed.",
        examples=["Lab at Thu 07:09 AM"],
    )


class PyAtsTestbed(BaseModel, extra="forbid"):
    devices: dict[NodeLabel, PyAtsDevice] = Field(..., description="Device list")
    testbed: PyAtsTestbedName = Field(..., description="Testbed details (name)")
    topology: dict[NodeLabel, PyAtsDeviceTopology] = Field(..., description="Topology connections list")
