#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#
from enum import StrEnum
from typing import Annotated

from fastapi import Body
from pydantic import BaseModel, Field

from simple_webserver.schemas.common import (
    Coordinate,
    DefinitionID,
    Label,
    NodeStateModel,
    PinnedComputeID,
    PyAtsCredentials,
    TagArray,
    UUID4Type,
)

NodeLabel = Annotated[
    Label, Field(..., description="A node label.", examples=["desktop-1"])
]
NodeId = Annotated[
    UUID4Type,
    Field(
        ...,
        description="ID of the node.",
        examples=["26f677f3-fcb2-47ef-9171-dc112d80b54f"],
    ),
]

Ram = Annotated[
    int | None,
    Field(
        ge=1,
        le=1048576,
        description="RAM size in MB. Can be null.",
    ),
]

Cpus = Annotated[
    int | None, Field(ge=1, le=128, description="Number of CPUs. Can be null.")
]

AllocatedCpus = Annotated[
    int | None,
    Field(ge=0, le=128, description="Number allocated of CPUs. Can be null."),
]

CpuLimit = Annotated[
    int | None, Field(ge=20, le=100, description="CPU limit percentage. Can be null.")
]

DiskSpace = Annotated[
    int | None, Field(ge=0, le=4096, description="Disk space in GB. Can be null.")
]

IOLAppId = Annotated[
    int | None, Field(ge=1, le=1022, description="IOL Application ID. Can be null.")
]

NodeConfigurationContent = Annotated[
    str | None, Field(description="Node configuration (no more than 20MB).")
]


class NodeConfigurationFile(BaseModel, extra="forbid"):
    name: Annotated[
        str,
        Field(
            ...,
            min_length=1,
            max_length=64,
            description=(
                "The name of the configuration file. Can also use the keyword "
                '"Main" to denote the main configuration file for the given definition.'
            ),
        ),
    ]
    content: NodeConfigurationContent = Field(default=None)


NodeConfigurationFiles = Annotated[
    list[NodeConfigurationFile],
    Field(description="List of node configuration file objects."),
]

NodeConfiguration = Annotated[
    NodeConfigurationContent | NodeConfigurationFiles | NodeConfigurationFile,
    Field(
        description=(
            "Node configuration. Either an array of file objects, or a single file "
            "object, or just the content of the main configuration file."
        )
    ),
]


NodeParameters = Annotated[
    dict[str, str | None],
    Field(
        default_factory=dict,
        description="Node-specific parameters.",
        examples=[{"smbios.bios.vendor": "Lenovo"}],
    ),
]


class NodeBase(BaseModel):
    """Node object base."""

    label: NodeLabel = Field(default=None)
    x: Coordinate = Field(default=None, description="Node X coordinate.")
    y: Coordinate = Field(default=None, description="Node Y coordinate.")
    image_definition: DefinitionID | None = Field(
        default=None, description="Image Definition ID for the specified node."
    )
    tags: TagArray = Field(default=None)


class NodeBaseExtended(NodeBase):
    configuration: NodeConfiguration = Field(default=None)
    parameters: NodeParameters
    ram: Ram = Field(default=None)
    cpu_limit: CpuLimit = Field(default=None)
    data_volume: DiskSpace = Field(default=None)
    boot_disk_size: DiskSpace = Field(default=None)
    hide_links: bool = Field(
        default=False, description="Whether to hide links to/from this node."
    )
    priority: int | None = Field(
        default=None,
        description="Priority of the node during lab start.",
        ge=0,
        le=10000,
    )
    pyats: PyAtsCredentials = Field(
        default_factory=PyAtsCredentials,
        description="pyATS specific credentials for the node.",
    )


class NodeUpdate(NodeBaseExtended, extra="forbid"):
    cpus: Cpus = Field(default=None)
    pinned_compute_id: PinnedComputeID = Field(default=None)


class BootProgress(StrEnum):
    NOT_RUNNING = "Not running"
    BOOTING = "Booting"
    BOOTED = "Booted"


class NodeDefinedBase(NodeBaseExtended):
    node_definition: DefinitionID = Field(
        ..., description="Node Definition ID for the specified node."
    )


class NodeDefined(NodeDefinedBase):
    cpus: Cpus = Field(default=None)


class NodeCreate(NodeDefined, extra="forbid"):
    pass


class ConsoleKeyDetails(BaseModel, extra="forbid"):
    console_key: UUID4Type = Field(default=None)
    label: Label = Field(default=None)
    device_number: int = Field(default=None)


class NodeOperationalData(BaseModel, extra="forbid"):
    """Operational data resolved when a node was started."""

    boot_disk_size: DiskSpace = Field(...)
    cpu_limit: CpuLimit = Field(...)
    cpus: AllocatedCpus = Field(...)
    data_volume: DiskSpace = Field(...)
    ram: Ram = Field(...)
    compute_id: UUID4Type | None = Field(
        ..., description="The ID of the compute host where this node is deployed."
    )
    image_definition: DefinitionID | None = Field(
        ..., description="Image definition ID used for the specified node."
    )
    vnc_key: UUID4Type | None = Field(
        ...,
        description="The key used to connect to a node's graphical VNC console "
        "if supported by node.",
    )
    resource_pool: UUID4Type | None = Field(
        default=None,
        description="Node was launched with resources from the given resource pool.",
    )
    iol_app_id: IOLAppId = Field(default=None)
    serial_consoles: list[ConsoleKeyDetails] = Field(default_factory=list)


class Node(NodeDefinedBase):
    id: NodeId
    boot_progress: BootProgress = Field(
        default=None,
        description="Flag indicating whether the node appears to have completed its boot.",
    )
    cpus: AllocatedCpus = Field(...)
    operational: NodeOperationalData | None = Field(
        default=None,
        description="Additional operational data associated with the node.",
    )
    state: NodeStateModel = Field(...)
    pinned_compute_id: PinnedComputeID = Field(default=None)
    lab_id: UUID4Type = Field(default=None)


class NodeResponse(Node, extra="forbid"):
    """The response body is a JSON node object."""

    configuration: NodeConfigurationFiles = Field(default=None)


NodeCreateBody = Annotated[
    NodeCreate, Body(description="A JSON object with a node's fundamental properties.")
]

NodeUpdateBody = Annotated[
    NodeUpdate, Body(description="A JSON object with a node's updatable properties.")
]


class NodeStateResponse(BaseModel, extra="forbid"):
    state: str = Field(default=None)
    progress: str = Field(default=None)


class SimplifiedNodeResponse(NodeBase, extra="forbid"):
    """Simplified node object with only essential fields."""

    id: NodeId
    node_definition: DefinitionID = Field(..., description="Node definition.")
    state: NodeStateModel = Field(...)


MixedNodeResponse = Annotated[
    NodeResponse | SimplifiedNodeResponse,
    Field(description="The response body is a JSON node object."),
]
