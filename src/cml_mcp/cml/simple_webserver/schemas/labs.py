#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#
from datetime import datetime
from typing import Annotated

from fastapi import Body
from pydantic import BaseModel, Field
from simple_common.schemas import LabEventElementType, LabEventType
from simple_webserver.schemas.annotations import AnnotationResponse
from simple_webserver.schemas.common import (
    BaseDBModel,
    EffectivePermissions,
    GenericDescription,
    InterfaceStateModel,
    LabStateModel,
    LinkStateModel,
    NodeStateModel,
    OldPermission,
    Permissions,
    UserFullName,
    UserName,
    UUID4Type,
)
from simple_webserver.schemas.links import LinkResponse, SimplifiedLinkResponse
from simple_webserver.schemas.nodes import (
    AllocatedCpus,
    CpuLimit,
    NodeResponse,
    Ram,
    SimplifiedNodeResponse,
)
from simple_webserver.schemas.smart_annotations import SmartAnnotationBase

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


class LabGroupBase(BaseModel):
    id: UUID4Type = Field(..., description="ID of the lab group.")
    permission: OldPermission = Field(..., description="Permission level for the lab group.")


class GroupLab(LabGroupBase, extra="forbid"):
    pass


class LabGroup(LabGroupBase, extra="forbid"):
    name: str = Field(default=None, description="Name of the lab group.")


class LabGroupAssociation(BaseModel, extra="forbid"):
    id: UUID4Type = Field(..., description="ID of the group.")
    permissions: Permissions = Field(..., description="Permissions for the specified group and lab.")


class LabUserAssociation(BaseModel, extra="forbid"):
    id: UUID4Type = Field(..., description="ID of the user.")
    permissions: Permissions = Field(..., description="Permissions for the specified user and lab.")


class LabAssociations(BaseModel, extra="forbid"):
    groups: list[LabGroupAssociation] = Field(default=None, description="Array of group associations.")
    users: list[LabUserAssociation] = Field(default=None, description="Array of user associations.")


LabOwner = Annotated[UUID4Type, Field(description="ID of the lab owner.")]


class LabAutostart(BaseModel, extra="forbid"):
    enabled: bool = Field(default=False, description="Enable lab start when CML host boots.")
    priority: int | None = Field(default=None, description="Priority of the autostarted lab.", ge=0, le=10000)
    delay: int | None = Field(
        default=None,
        description="Delay before the lab with next priority is autostarted.",
        ge=0,
        le=86400,
    )


LabAutostartMixin = Annotated[
    # XXX: This is only set to None for CML 2.9 backward compatibility.
    LabAutostart | None,
    Field(
        default=None,
        description="The lab's autostart configuration. (Since: 2.10)",
    ),
]


class NodeStaging(BaseModel, extra="forbid"):
    enabled: bool = Field(default=False, description="Whether the node staging is enabled.")
    start_remaining: bool = Field(
        default=True,
        description="Whether nodes with unset priority should be started.",
    )
    abort_on_failure: bool = Field(
        default=False,
        description="""
            Whether remaining nodes should be skipped once a node fails to start.
        """,
    )


NodeStagingMixin = Annotated[
    # XXX: This is only set to None for CML 2.9 backward compatibility.
    NodeStaging | None,
    Field(default=None, description="The lab's node staging configuration. (Since: 2.10)"),
]


class LabRequest(BaseModel, extra="forbid"):
    """Lab metadata."""

    title: LabTitle = Field(default=None)
    owner: LabOwner = Field(default=None)
    description: LabDescription = Field(default=None)
    notes: LabNotes = Field(default=None)
    groups: list[LabGroup] = Field(
        default=None,
        description="Array of LabGroup objects - mapping from group ID to permissions.",
    )
    associations: LabAssociations = Field(
        default=None,
        description="Object of lab/group and lab/user associations.",
    )
    autostart: LabAutostartMixin = Field(...)
    node_staging: NodeStagingMixin = Field(...)


class Lab(BaseDBModel, extra="forbid"):
    """Metadata about the state of the lab itself."""

    lab_description: LabDescription = Field(default=None)
    lab_notes: LabNotes = Field(default=None)
    lab_title: LabTitle = Field(...)
    owner: LabOwner = Field(default=None)
    owner_username: UserName = Field(default=None, description="The owner username.")
    owner_fullname: UserFullName = Field(default=None, description="The owner full name.")
    state: LabStateModel = Field(...)
    node_count: int = Field(default=None, description="Number of nodes (or devices) in the lab.", ge=0)
    link_count: int = Field(
        default=None,
        description="Number of connections between nodes in the lab.",
        ge=0,
    )
    groups: list[LabGroup] = Field(
        default=None,
        description="Array of LabGroup objects - mapping from group ID to permissions.",
    )
    effective_permissions: EffectivePermissions = Field(...)
    autostart: LabAutostartMixin = Field(default=...)
    node_staging: NodeStagingMixin = Field(default=...)


LabGroupsBody = Annotated[
    list[LabGroup],
    Body(description="This request body is a JSON object that describes the group permissions for a lab."),
]

LabBody = Annotated[LabRequest, Body(description="The lab's data.")]


class LabResponse(Lab, extra="forbid"):
    """The response body is a JSON lab object."""

    pass


class LabElementStateResponse(BaseModel, extra="forbid"):
    """
    JSON object with the state of all
    nodes, interfaces, and links in the lab.
    """

    nodes: dict[UUID4Type, NodeStateModel] = Field(...)
    links: dict[UUID4Type, LinkStateModel] = Field(...)
    interfaces: dict[UUID4Type, InterfaceStateModel] = Field(...)


class LinkStats(BaseModel, extra="forbid"):
    readpackets: int = Field(default=0, description="Number of packets read.")
    readbytes: int = Field(default=0, description="Number of bytes read.")
    writepackets: int = Field(default=0, description="Number of packets written.")
    writebytes: int = Field(default=0, description="Number of bytes written.")
    drops: int = Field(default=0, description="Number of packets dropped.")


class NodeTimesBase(BaseModel):
    times: dict[NodeStateModel, int] = Field(
        default_factory=dict,
        description="Timestamps for states QUEUED, STARTED, BOOTED.",
    )


class NodeTimes(NodeTimesBase, extra="forbid"):
    pass


class NodeStats(NodeTimesBase, extra="forbid"):
    cpu_usage: float = Field(default=0.0, description="CPU usage in percent.")
    ram_usage: float = Field(default=0.0, description="RAM usage in percent.")
    disk_usage: int = Field(default=0, description="Disk usage in MB.")
    block0_wr_bytes: int = Field(default=0, description="Number of bytes written.")
    block0_rd_bytes: int = Field(default=0, description="Number of bytes read.")
    cpu_limit: CpuLimit = Field(...)
    cpus: AllocatedCpus = Field(...)
    ram: Ram = Field(...)


class LabSimulationStatsResponse(BaseModel, extra="forbid"):
    links: dict[UUID4Type, LinkStats] = Field(default_factory=dict)
    nodes: dict[UUID4Type, NodeStats | NodeTimes] = Field(default_factory=dict)


class LabEventResponse(BaseModel, extra="forbid"):
    """Lab Event Info"""

    lab_id: UUID4Type = Field(...)
    event: LabEventType = Field(...)
    element_type: LabEventElementType = Field(...)
    element_id: UUID4Type = Field(...)
    data: dict = Field(...)
    previous: dict = Field(...)
    timestamp: datetime = Field(...)


class LabTopologyInfoBase(BaseModel):
    """Base class for lab topology with common fields."""

    annotations: list[AnnotationResponse] = Field(default_factory=list)
    smart_annotations: list[SmartAnnotationBase] = Field(default_factory=list)


class LabTopologyInfo(LabTopologyInfoBase, extra="forbid"):
    nodes: list[NodeResponse] = Field(...)
    links: list[LinkResponse] = Field(...)


class SimplifiedLabTopologyInfo(LabTopologyInfoBase, extra="forbid"):
    nodes: list[SimplifiedNodeResponse] = Field(...)
    links: list[SimplifiedLinkResponse] = Field(...)


class LabInfoResponse(Lab, extra="forbid"):
    topology: LabTopologyInfo | SimplifiedLabTopologyInfo = Field(default=None, description="Lab topology data")
