#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#
from enum import StrEnum
from typing import Annotated

from fastapi import Body
from pydantic import BaseModel, ConfigDict, Field, model_validator

from cml_mcp.schemas.common import (
    Coordinate,
    DefinitionID,
    Label,
    PinnedComputeID,
    TagArray,
    UUID4Type,
)

NodeLabel = Annotated[Label, Field(..., description="A node label.", examples=["desktop-1"])]
NodeId = Annotated[
    UUID4Type,
    Field(
        ...,
        description="A node UUID4.",
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

Cpus = Annotated[int | None, Field(ge=1, le=128, description="Number of CPUs. Can be null.")]

AllocatedCpus = Annotated[
    int | None,
    Field(ge=0, le=128, description="Number allocated of CPUs. Can be null."),
]

CpuLimit = Annotated[int | None, Field(ge=20, le=100, description="CPU limit percentage. Can be null.")]

DiskSpace = Annotated[int | None, Field(ge=0, le=4096, description="Disk space in GB. Can be null.")]

IOLAppId = Annotated[int | None, Field(ge=1, le=1022, description="IOL Application ID. Can be null.")]


NodeConfigurationContent = Annotated[str | None, Field(description="Node configuration (no more than 20MB).")]


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


class NodeParameters(BaseModel, extra="allow"):
    model_config = ConfigDict(
        json_schema_extra={
            "description": "Key-value pairs of a custom node SMBIOS parameters.",
            "example": {"smbios.bios.vendor": "Lenovo"},
        }
    )

    @model_validator(mode="after")
    def check_types(self):
        for field_name, value in self.__dict__.items():
            if value is not None and not isinstance(value, str):
                raise TypeError(f"Value for '{field_name}' must be a string or None," f"but got {type(value).__name__}.")
        return self


class NodeBase(BaseModel, extra="allow"):
    """Node object base."""

    x: Coordinate = Field(default=None, description="Node X coordinate.")
    y: Coordinate = Field(default=None, description="Node Y coordinate.")
    label: NodeLabel = Field(default=None)
    parameters: NodeParameters = Field(default=None)
    image_definition: DefinitionID | None = Field(default=None, description="Image Definition ID for the specified node.")
    ram: Ram = Field(default=None)
    cpu_limit: CpuLimit = Field(default=None)
    data_volume: DiskSpace = Field(default=None)
    boot_disk_size: DiskSpace = Field(default=None)
    hide_links: bool | None = Field(default=None, description="Whether to hide links to/from this node.")
    tags: TagArray = Field(default=None)


class NodeUpdate(NodeBase, extra="forbid"):
    cpus: Cpus = Field(default=None)
    configuration: NodeConfiguration = Field(default=None)
    pinned_compute_id: PinnedComputeID = Field(default=None)


class NodeStates(StrEnum):
    DEFINED_ON_CORE = "DEFINED_ON_CORE"
    STOPPED = "STOPPED"
    STARTED = "STARTED"
    QUEUED = "QUEUED"
    BOOTED = "BOOTED"
    DISCONNECTED = "DISCONNECTED"


class BootProgresses(StrEnum):
    NOT_RUNNING = "Not running"
    BOOTING = "Booting"
    BOOTED = "Booted"


BootProgress = Annotated[BootProgresses, Field(description="Node boot progress.")]


class NodeDefinedBase(NodeBase, extra="allow"):
    node_definition: DefinitionID = Field(..., description="Node Definition ID for the specified node.")
    x: Coordinate = Field(...)
    y: Coordinate = Field(...)
    label: NodeLabel = Field(...)


class NodeDefined(NodeDefinedBase, extra="allow"):
    cpus: Cpus = Field(default=None)


class NodeCreate(NodeDefined, extra="forbid"):
    configuration: NodeConfiguration = Field(default=None)


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
    compute_id: UUID4Type | None = Field(..., description="The ID of the compute host where this node is deployed.")
    image_definition: DefinitionID | None = Field(..., description="Image definition ID used for the specified node.")
    vnc_key: UUID4Type | None = Field(
        ...,
        description="The key used to connect to a node's graphical VNC console " "if supported by node.",
    )
    resource_pool: UUID4Type | None = Field(
        default=None,
        description="Node was launched with resources from the given resource pool.",
    )
    iol_app_id: IOLAppId = Field(default=None)
    serial_consoles: list[ConsoleKeyDetails] = Field(default=None)


class Node(NodeDefinedBase, extra="forbid"):
    id: NodeId
    boot_progress: BootProgress = Field(
        default=None,
        description="Flag indicating whether the node appears to have completed its boot.",
    )
    compute_id: UUID4Type | None = Field(
        default=None,
        description="The ID of the compute host where this node is deployed.",
    )
    cpus: AllocatedCpus = Field(...)
    iol_app_id: IOLAppId = Field(default=None)
    operational: NodeOperationalData = Field(
        default=None,
        description="Additional operational data associated with the node.",
    )
    resource_pool: UUID4Type | None = Field(
        default=None,
        description="Node was launched with resources from the given resource pool.",
    )
    state: NodeStates = Field(default=None, description="The state of the node.")
    vnc_key: UUID4Type | None = Field(
        default=None,
        description="The key used to connect to a node's graphical VNC console, if supported by node.",
    )
    configuration: NodeConfiguration = Field(default=None)
    pinned_compute_id: PinnedComputeID = Field(default=None)
    lab_id: UUID4Type = Field(default=None)
    serial_consoles: list[ConsoleKeyDetails] = Field(default_factory=list)


NodeCreateBody = Annotated[NodeCreate, Body(description="A JSON object with a node's fundamental properties.")]

NodeUpdateBody = Annotated[NodeUpdate, Body(description="A JSON object with a node's updatable properties.")]


class NodeStateResponse(BaseModel, extra="forbid"):
    state: str = Field(default=None)
    progress: str = Field(default=None)


NodeResponse = Annotated[Node, Field(description="The response body is a JSON node object.")]
