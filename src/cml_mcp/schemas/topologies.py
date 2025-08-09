#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#
from enum import StrEnum
from typing import Annotated

from fastapi import Body
from pydantic import BaseModel, Field

from cml_mcp.schemas.annotations import AnnotationResponse, AnnotationUpdate
from cml_mcp.schemas.common import MACAddress, UUID4Type
from cml_mcp.schemas.interfaces import InterfaceLabel, InterfaceSlot, InterfaceType
from cml_mcp.schemas.labs import LabDescription, LabNotes, LabTitle
from cml_mcp.schemas.links import (
    LinkConditionConfiguration,
    LinkLabel,
    LinkWithConditionConfig,
)
from cml_mcp.schemas.nodes import NodeConfiguration, NodeDefined
from cml_mcp.schemas.smart_annotations import (
    SmartAnnotationBase,
    SmartAnnotationResponse,
)

TopologyID = Annotated[str, Field(min_length=1, max_length=64, description="Element ID.", examples=["l1"])]


class TopologySchemaVersionEnum(StrEnum):
    v0_0_1 = "0.0.1"
    v0_0_2 = "0.0.2"
    v0_0_3 = "0.0.3"
    v0_0_4 = "0.0.4"
    v0_0_5 = "0.0.5"
    v0_1_0 = "0.1.0"
    v0_2_0 = "0.2.0"
    v0_2_1 = "0.2.1"
    v0_2_2 = "0.2.2"
    v0_3_0 = "0.3.0"


TopologySchemaVersion = Annotated[
    TopologySchemaVersionEnum,
    Field(description="Topology schema version.", examples=["0.2.2"]),
]


class LabTopology(BaseModel, extra="forbid"):
    version: TopologySchemaVersion = Field(...)
    title: LabTitle = Field(default=None)
    description: LabDescription = Field(default=None)
    notes: LabNotes = Field(default=None)


class LabTopologyWithOwner(LabTopology, extra="forbid"):
    owner: UUID4Type = Field(default=None)


class InterfaceTopology(BaseModel, extra="forbid"):
    id: TopologyID = Field(...)
    type: InterfaceType = Field(...)
    node: TopologyID = Field(default=None)
    label: InterfaceLabel = Field(default=None)
    slot: InterfaceSlot = Field(default=None)
    mac_address: MACAddress = Field(default=None)


class NodeTopology(NodeDefined, extra="forbid"):
    id: TopologyID = Field(...)
    interfaces: list[InterfaceTopology] = Field(...)
    configuration: NodeConfiguration = Field(default=None)


class LinkTopology(BaseModel, extra="forbid"):
    id: TopologyID = Field(...)
    i1: TopologyID = Field(...)
    i2: TopologyID = Field(...)
    n1: TopologyID = Field(...)
    n2: TopologyID = Field(...)
    label: LinkLabel = Field(default=None)
    conditioning: LinkConditionConfiguration = Field(default_factory=dict)


class Topology(BaseModel, extra="forbid"):
    """
    A JSON object that describes topology, including its nodes, interfaces,
    links, and details, such as the user-supplied title and notes.
    """

    nodes: list[NodeTopology] = Field(...)
    links: list[LinkTopology] = Field(...)
    lab: LabTopology = Field(...)
    annotations: list[AnnotationUpdate] = Field(default_factory=list)
    smart_annotations: list[SmartAnnotationBase] = Field(default_factory=list)


ImportTopologyBody = Annotated[
    Topology,
    Body(description="This request body is a JSON object that describes a single topology."),
]


class TopologyResponse(Topology, extra="forbid"):
    """The response body is a JSON topology object."""

    links: list[LinkWithConditionConfig] = Field(...)
    lab: LabTopologyWithOwner = Field(...)
    annotations: list[AnnotationResponse] = Field(default=None)
    smart_annotations: list[SmartAnnotationResponse] = Field(default=None)
