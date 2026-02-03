#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#


from enum import StrEnum

from pydantic import BaseModel, Field, RootModel
from simple_common.schemas import DomainDriver
from simple_webserver.schemas.common import IPAddress, UUID4Type
from simple_webserver.schemas.labs import LabTitle
from simple_webserver.schemas.links import LinkLabel
from simple_webserver.schemas.nodes import NodeLabel

UpperDomainDriver = StrEnum("UpperDomainDriver", {member.name: member.name for member in DomainDriver})


class BaseLabDetails(BaseModel):
    node_id: UUID4Type
    compute_id: UUID4Type
    lab_id: UUID4Type
    label: NodeLabel


class ConsoleLabDetails(BaseLabDetails, extra="forbid"):
    driver: UpperDomainDriver
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
