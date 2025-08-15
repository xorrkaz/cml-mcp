#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#
from typing import Annotated, Literal

from fastapi import Body
from pydantic import BaseModel, Field

from cml_mcp.schemas.common import (
    Label,
    LinuxInterfaceName,
    MACAddress,
    State,
    UUID4Type,
)

InterfaceLabel = Annotated[Label, Field(..., description="An interface label.")]
InterfaceSlot = Annotated[int, Field(ge=0, le=128, description="Number of slots.")]

InterfaceType = Annotated[Literal["physical", "loopback"], Field(description="Interface type.")]


class InterfaceCreate(BaseModel, extra="forbid"):
    node: UUID4Type = Field(...)
    slot: InterfaceSlot = Field(default=None)
    mac_address: MACAddress = Field(default=None)


class InterfaceUpdate(BaseModel, extra="forbid"):
    mac_address: MACAddress = Field(default=None)


class InterfaceBase(BaseModel):
    """Interface object."""

    lab_id: UUID4Type = Field(default=None, description="ID of the lab.")
    label: InterfaceLabel = Field(default=None)
    type: InterfaceType = Field(default=None)
    slot: InterfaceSlot = Field(default=None)
    mac_address: MACAddress = Field(default=None)
    is_connected: bool = Field(default=None, description="Whether this interface is connected (in-use).")
    state: State = Field(default=None, description="The status of the link in the lab.")


InterfaceCreateBody = Annotated[
    InterfaceCreate,
    Body(
        description="A JSON object that specifies a request to create an interface "
        "on a node. If the slot is omitted, the request indicates "
        "the *first* unused slot on the node. If the slot is specified, "
        "the request indicates *all unallocated* slots up to and including "
        "that slot."
    ),
]

InterfaceUpdateBody = Annotated[
    InterfaceUpdate,
    Body(description="A JSON object with an interface's updatable properties."),
]


class InterfaceOperationalDataResponse(BaseModel, extra="forbid"):
    device_name: LinuxInterfaceName | None = Field(default=None, max_length=64, description="Device name.")
    mac_address: MACAddress = Field(default=None)
    src_udp_port: int | None = Field(default=None, ge=0, le=65535, description="Source UDP port.")
    dst_udp_port: int | None = Field(default=None, ge=0, le=65535, description="Destination UDP port.")


class InterfaceResponse(InterfaceBase, extra="forbid"):
    """The response body is a JSON interface object."""

    id: UUID4Type = Field(..., description="ID of the interface.")
    label: InterfaceLabel = Field(...)
    node: UUID4Type = Field(default=None, description="ID of the node.")
    src_udp_port: int | None = Field(default=None, ge=0, le=65535, description="Source UDP port (operational).")
    dst_udp_port: int | None = Field(default=None, ge=0, le=65535, description="Destination UDP port (operational).")
    device_name: LinuxInterfaceName | None = Field(default=None, max_length=64, description="Device name (operational).")
    operational: InterfaceOperationalDataResponse | None = Field(
        default=None,
        description="Additional operational data associated with the interface.",
    )
    slot: InterfaceSlot | None = Field(default=None)


class InterfaceStateResponse(BaseModel, extra="forbid"):
    label: InterfaceLabel = Field(...)
    state: State = Field(...)
