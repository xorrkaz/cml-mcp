#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#
from datetime import datetime
from typing import Annotated, Literal

from fastapi import Body
from pydantic import BaseModel, Field

from cml_mcp.schemas.simple_core.common.events import LabEventElementType, LabEventType
from cml_mcp.schemas.simple_core.common.states import InterfaceState, LinkState, NodeState
from cml_mcp.schemas.annotations import AnnotationResponse
from cml_mcp.schemas.common import (
    BaseDBModel,
    EffectivePermissions,
    GenericDescription,
    OldPermission,
    Permissions,
    State,
    UserFullName,
    UserName,
    UUID4Type,
)
from cml_mcp.schemas.links import Link
from cml_mcp.schemas.nodes import Node
from cml_mcp.schemas.smart_annotations import SmartAnnotationBase

LabTitle = Annotated[
    str,
    Field(
        min_length=1,
        max_length=64,
        description="Title of the Lab.",
        examples=["Lab at Mon 17:27 PM"],
    ),
]

LabNotes = Annotated[
    str,
    Field(
        max_length=32768,
        description="Additional, textual free-form Lab notes.",
        examples=["Find why this topology does not perform as expected!"],
    ),
]

LabDescription = Annotated[
    GenericDescription,
    Field(
        description="Additional, textual free-form detail of the lab.",
        examples=["CCNA study lab"],
    ),
]


class LabGroupBase(BaseModel, extra="allow"):
    id: UUID4Type = Field(..., description="ID of the lab group.")
    permission: OldPermission = Field(
        ..., description="Permission level for the lab group."
    )


class GroupLab(LabGroupBase, extra="forbid"):
    pass


class LabGroup(LabGroupBase, extra="forbid"):
    name: str = Field(default=None, description="Name of the lab group.")


class LabGroupAssociation(BaseModel, extra="forbid"):
    id: UUID4Type = Field(..., description="ID of the group.")
    permissions: Permissions = Field(
        ..., description="Permissions for the specified group and lab."
    )


class LabUserAssociation(BaseModel, extra="forbid"):
    id: UUID4Type = Field(..., description="ID of the user.")
    permissions: Permissions = Field(
        ..., description="Permissions for the specified user and lab."
    )


class LabAssociations(BaseModel, extra="forbid"):
    groups: list[LabGroupAssociation] = Field(
        default=None, description="Array of group associations."
    )
    users: list[LabUserAssociation] = Field(
        default=None, description="Array of user associations."
    )


LabOwner = Annotated[UUID4Type, Field(description="ID of the lab owner.")]


class LabCreate(BaseModel, extra="forbid"):
    """Lab metadata."""

    title: LabTitle = Field(default=None)
    owner: LabOwner = Field(default=None)
    description: LabDescription = Field(default=None)
    notes: LabNotes = Field(default=None)
    groups: list[LabGroup] = Field(
        default=None,
        deprecated=True,
        description="Array of LabGroup objects - mapping from group ID to permissions.",
    )
    associations: LabAssociations = Field(
        default=None,
        description="Object of lab/group and lab/user associations.",
    )


class Lab(BaseDBModel):
    """Metadata about the state of the lab itself."""

    lab_description: LabDescription = Field(default=None)
    lab_notes: LabNotes = Field(default=None)
    lab_title: LabTitle = Field(...)
    owner: LabOwner = Field(default=None)
    owner_username: UserName = Field(default=None, description="The owner username.")
    owner_fullname: UserFullName = Field(
        default=None, description="The owner full name."
    )
    state: State = Field(..., description="The overall state of the lab.")
    node_count: int = Field(
        default=None, description="Number of nodes (or devices) in the lab.", ge=0
    )
    link_count: int = Field(
        default=None,
        description="Number of connections between nodes in the lab.",
        ge=0,
    )
    groups: list[LabGroup] = Field(
        default=None,
        deprecated=True,
        description="Array of LabGroup objects - mapping from group id to permissions.",
    )
    effective_permissions: EffectivePermissions = Field(...)


LabGroupsBody = Annotated[
    list[LabGroup],
    Body(
        description="This request body is a JSON object that describes the group permissions for a lab."
    ),
]

LabCreateBody = Annotated[LabCreate, Body(description="The lab's data.")]


class LabResponse(Lab, extra="forbid"):
    """The response body is a JSON lab object."""

    pass


LabNodeStateNames = list(NodeState.__members__.keys())
LabLinkStateNames = list(LinkState.__members__.keys())
LabInterfaceStateNames = list(InterfaceState.__members__.keys())


class LabElementStateResponse(BaseModel):
    """
    JSON object with the state of all
    nodes, interfaces, and links in the lab.
    """

    nodes: dict[UUID4Type, Literal[*LabNodeStateNames]] = Field(...)
    links: dict[UUID4Type, Literal[*LabLinkStateNames]] = Field(...)
    interfaces: dict[UUID4Type, Literal[*LabInterfaceStateNames]] = Field(...)


class LabSimulationStatsResponse(BaseModel):
    nodes: list[Node] = Field(default=None)
    links: list[Link] = Field(default=None)


LabEventNames = list(LabEventType.__members__.keys())
LabEventElementTypeNames = list(LabEventElementType.__members__.keys())


class LabEventResponse(BaseModel):
    """Lab Event Info"""

    lab_id: UUID4Type = Field(...)
    event: Literal[*LabEventNames] = Field(...)
    element_type: Literal[*LabEventElementTypeNames] = Field(...)
    element_id: UUID4Type = Field(...)
    data: dict = Field(...)
    previous: dict = Field(...)
    timestamp: datetime = Field(...)


class SimplifiedLabTopology(BaseModel):
    nodes: list[Node] = Field(...)
    links: list[Link] = Field(...)
    annotations: list[AnnotationResponse] = Field(default=None)
    smart_annotations: list[SmartAnnotationBase] = Field(default=None)


class LabInfoResponse(BaseDBModel, extra="forbid"):
    state: State = Field(..., description="The overall state of the lab.")
    lab_title: LabTitle = Field(...)
    lab_description: LabDescription = Field(...)
    lab_notes: LabNotes = Field(...)
    owner: LabOwner = Field(...)
    owner_username: str = Field(...)
    owner_fullname: str = Field(...)
    node_count: int = Field(..., ge=0, description="Number of nodes in the lab.")
    link_count: int = Field(
        ..., ge=0, description="Number of connections between nodes in the lab."
    )
    groups: list[LabGroup] = Field(...)
    effective_permissions: EffectivePermissions = Field(...)
    topology: SimplifiedLabTopology = Field(
        default=None, description="Lab topology data"
    )
