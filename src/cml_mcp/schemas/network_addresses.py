#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#
from typing import Annotated

from pydantic import BaseModel, Field

from cml_mcp.schemas.common import (
    IPv4Address,
    IPv6Address,
    Label,
    MACAddress,
    UUID4Type,
)
from cml_mcp.schemas.nodes import NodeId, NodeLabel


class NetworkInterface(BaseModel, extra="forbid"):
    id: UUID4Type = Field(..., description="Unique identifier of the network interface")
    label: Label = Field(..., description="Label of the network interface")
    ip4: list[IPv4Address] = Field(
        default_factory=list,
        description="List of assigned IPv4 addresses or empty list if no IPv4 addresses assigned",
    )
    ip6: list[IPv6Address] = Field(
        default_factory=list,
        description="List of assigned IPv4 addresses or empty list if no IPv4 addresses assigned",
    )


class NodeNetworkAddressesResponse(BaseModel, extra="forbid"):
    name: NodeLabel
    interfaces: dict[MACAddress, NetworkInterface] = Field(
        default_factory=dict,
        description="Dictionary mapping MAC addresses to network interfaces",
    )


LabNetworkAddressesResponse = Annotated[
    dict[NodeId, NodeNetworkAddressesResponse],
    Field(description="Lab network addresses dictionary or empty dictionary if lab is not started"),
]
