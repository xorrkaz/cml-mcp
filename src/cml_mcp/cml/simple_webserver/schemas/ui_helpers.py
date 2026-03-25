#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#

from pydantic import BaseModel, Field

from simple_common.schemas import LabState, LinkState, NodeState
from simple_webserver.schemas.common import (
    EffectivePermissions,
    PinnedComputeID,
    UUID4Type,
)
from simple_webserver.schemas.external_connector import ExternalConnectorMappingResponse
from simple_webserver.schemas.interfaces import InterfaceResponse
from simple_webserver.schemas.labs import LabAutostartMixin, LabInfoResponse
from simple_webserver.schemas.links import LinkWithConditionConfig
from simple_webserver.schemas.node_definitions import SimplifiedNodeDefinition
from simple_webserver.schemas.nodes import NodeOperationalData
from simple_webserver.schemas.resource_pools import ResourcePoolResponse
from simple_webserver.schemas.system import SystemHealth, SystemInformation
from simple_webserver.schemas.topologies import (
    LabTopologyWithOwner,
    NodeTopology,
    TopologyResponse,
)


class LabTilesResponse(BaseModel, extra="forbid"):
    lab_tiles: dict[UUID4Type, LabInfoResponse] = Field(default_factory=dict)


class UiTopologyNodeResponse(NodeTopology, extra="forbid"):
    state: NodeState
    compute_id: UUID4Type | None
    pinned_compute_id: PinnedComputeID | None
    interfaces: list[InterfaceResponse] = Field(default_factory=list)
    operational: NodeOperationalData | None
    resource_pool: UUID4Type | None


class UiTopologyLabResponse(LabTopologyWithOwner, extra="forbid"):
    state: LabState


class UiTopologyLinkResponse(LinkWithConditionConfig, extra="forbid"):
    state: LinkState


class UiPopulateLabTopologyResponse(TopologyResponse, extra="forbid"):
    effective_permissions: EffectivePermissions
    resource_pools: list[ResourcePoolResponse] = Field(default_factory=list)
    connector_mappings: ExternalConnectorMappingResponse
    autostart: LabAutostartMixin
    lab: UiTopologyLabResponse
    nodes: list[UiTopologyNodeResponse] = Field(default_factory=list)
    links: list[UiTopologyLinkResponse] = Field(default_factory=list)


class PopulatedLabTileResponse(BaseModel, extra="forbid"):
    topology: UiPopulateLabTopologyResponse
    health: SystemHealth
    system_information: SystemInformation
    simplified_node_definitions: list[SimplifiedNodeDefinition]
