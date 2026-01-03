#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#

from enum import Enum

from pydantic import BaseModel, Field, RootModel

from simple_webserver.schemas.common import IPAddress, UUID4Type
from simple_webserver.schemas.labs import LabTitle
from simple_webserver.schemas.links import LinkLabel
from simple_webserver.schemas.node_definitions import LibvirtDomainDriver
from simple_webserver.schemas.nodes import NodeLabel

UpperLibvirtDomainDrivers = Enum(
    "UpperLibvirtDomainDrivers",
    {member.name: member.name.upper() for member in LibvirtDomainDriver},
)


class BaseLabDetails(BaseModel):
    node_id: UUID4Type
    compute_id: UUID4Type
    lab_id: UUID4Type
    label: NodeLabel


class ConsoleLabDetails(BaseLabDetails, extra="forbid"):
    driver: UpperLibvirtDomainDrivers
    line: int = Field(..., ge=0)


class VNCLabDetails(BaseLabDetails, extra="forbid"):
    compute_address: IPAddress


class LinkCaptureDetails(BaseModel, extra="forbid"):
    lab_id: UUID4Type
    lab_title: LabTitle
    label: LinkLabel


class ConsoleKeysResponse(RootModel[dict[UUID4Type, ConsoleLabDetails]]):
    pass


class VNCKeysResponse(RootModel[dict[UUID4Type, VNCLabDetails]]):
    pass


class LinkCaptureKeysResponse(RootModel[dict[UUID4Type, LinkCaptureDetails]]):
    pass
