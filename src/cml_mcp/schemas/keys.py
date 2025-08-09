#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#

from enum import Enum

from pydantic import BaseModel, Field, RootModel

from cml_mcp.schemas.common import IPAddress, UUID4Type
from cml_mcp.schemas.node_definitions import LibvirtDomainDrivers
from cml_mcp.schemas.nodes import NodeLabel

# TODO: delete this part during SIMPLE-7552
# core_driver returns these values in upper case
# when simple_ui has enum with lower case
# PS: user does not see this name. only values.
UpperLibvirtDomainDrivers = Enum(
    "UpperLibvirtDomainDrivers",
    {member.name: member.name.upper() for member in LibvirtDomainDrivers},
)


class BaseLabDetails(BaseModel):
    node_id: UUID4Type
    compute_id: UUID4Type
    lab_id: UUID4Type
    label: NodeLabel


class ConsoleLabDetail(BaseLabDetails, extra="forbid"):
    driver: UpperLibvirtDomainDrivers
    line: int = Field(..., ge=0)


class VNCLabDetail(BaseLabDetails, extra="forbid"):
    compute_address: IPAddress


# preferable over Annotated dict as it is pydantic model.
class ConsoleKeysResponse(RootModel[dict[UUID4Type, ConsoleLabDetail]]):
    pass


class VNCKeysResponse(RootModel[dict[UUID4Type, VNCLabDetail]]):
    pass
