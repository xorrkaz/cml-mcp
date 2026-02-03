#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#

from datetime import datetime

from pydantic import BaseModel, Field
from simple_common.schemas import BootEventType
from simple_webserver.schemas.common import (
    Coordinate,
    DefinitionID,
    Hostname,
    InterfaceStateModel,
    IPAddress,
    LinkStateModel,
    NodeStateModel,
    PinnedComputeID,
    StringDict,
    TagArray,
    UUID4Type,
)
from simple_webserver.schemas.interfaces import (
    InterfaceLabel,
    InterfaceResponse,
    InterfaceSlot,
)
from simple_webserver.schemas.labs import LabEventResponse
from simple_webserver.schemas.licensing import (
    Authorization,
    LicensingFeature,
    LicensingTransportResponse,
    ProductLicense,
    Registration,
    Udi,
)
from simple_webserver.schemas.links import LinkResponse
from simple_webserver.schemas.nodes import (
    AllocatedCpus,
    CpuLimit,
    DiskSpace,
    Node,
    NodeId,
    NodeLabel,
    NodeParameters,
    Ram,
)
from simple_webserver.schemas.system import (
    ComputeHostStatsWithDomInfo,
    ComputeStateField,
)
from simple_webserver.schemas.users import UserResponse


class ReadinessResponse(BaseModel, extra="forbid"):
    libvirt: bool = Field(...)
    fabric: bool = Field(...)
    device_mux: bool = Field(...)
    refplat_images_available: bool = Field(...)
    docker_shim: bool = Field(...)


class ConsistencyResponse(BaseModel, extra="forbid"):
    missing_nodes: list[UUID4Type] = Field(default_factory=list)
    orphaned_nodes: list[UUID4Type] = Field(default_factory=list)


class FabricResponse(BaseModel, extra="forbid"):
    id: UUID4Type = Field(...)
    name: str = Field(...)
    left_driver: str = Field(...)
    right_driver: str = Field(...)
    running: bool = Field(...)


class NodeDiagnostics(Node, extra="forbid"):
    configuration: list[StringDict] = Field(
        default_factory=list,
        description="A list of anonynimized node configurations.",
    )


class ComputeDiagnostics(BaseModel, extra="forbid"):
    """ComputeDiagnostics info"""

    identifier: str = Field(...)
    host_address: IPAddress = Field(...)
    hostname: Hostname = Field(...)
    link_driver: str = Field(...)
    kvm_vmx_enabled: bool = Field(...)
    is_controller: bool = Field(...)
    is_connector: bool = Field(...)
    is_simulator: bool = Field(...)
    readiness: ReadinessResponse = Field(...)
    lld_consistency: ConsistencyResponse
    nodes: dict[UUID4Type, NodeDiagnostics] = Field(default_factory=dict)
    links: dict[UUID4Type, LinkResponse] = Field(default_factory=dict)
    interfaces: dict[UUID4Type, InterfaceResponse] = Field(default_factory=dict)
    fabric: list[FabricResponse] = Field(default_factory=list)
    statistics: ComputeHostStatsWithDomInfo
    admission_state: ComputeStateField


ComputeDiagnosticsResponse = dict[UUID4Type, ComputeDiagnostics]


class EventDiagnostics(BaseModel, extra="forbid"):
    lab_id: UUID4Type = Field(...)
    node_id: UUID4Type = Field(...)
    event: BootEventType = Field(...)
    timestamp: datetime = Field(...)


EventDiagnosticsResponse = list[EventDiagnostics]


LabEventDiagnosticsResponse = dict[UUID4Type, list[LabEventResponse]]


class NodeStateTimes(BaseModel, extra="forbid"):
    QUEUED: int = Field(..., ge=0)
    STARTED: int = Field(..., ge=0)
    BOOTED: int = Field(..., ge=0)


class NodeDiagnosticResponse(BaseModel, extra="forbid"):
    label: NodeLabel = Field(...)
    state: NodeStateModel = Field(...)
    state_times: NodeStateTimes = Field(...)


class LinkDiagnosticResponse(BaseModel, extra="forbid"):
    state: LinkStateModel = Field(...)
    interface_a: UUID4Type = Field(default=None, description="ID of the interface A.")
    interface_b: UUID4Type = Field(default=None, description="ID of the interface B.")


class InterfaceDiagnosticResponse(BaseModel, extra="forbid"):
    label: InterfaceLabel = Field(default=None)
    slot: InterfaceSlot | None = Field(default=None)
    state: InterfaceStateModel = Field(...)
    node: UUID4Type = Field(default=None, description="ID of the node.")


class LabDiagnostics(BaseModel, extra="forbid"):
    """Lab Diagnostics Info"""

    created: datetime = Field(...)
    allocated: bool = Field(...)
    nodes: dict[UUID4Type, NodeDiagnosticResponse] = Field(...)
    links: dict[UUID4Type, LinkDiagnosticResponse] = Field(...)
    interfaces: dict[UUID4Type, InterfaceDiagnosticResponse] = Field(...)


LabDiagnosticsResponse = dict[UUID4Type, LabDiagnostics]


class LicensingDiagnosticsResponse(BaseModel, extra="forbid"):
    quota: int | None = Field(..., ge=0)
    started: int = Field(..., ge=0)
    user_quota: int | None = Field(...)
    user_started: int = Field(..., ge=0)


class LicensingStatusDiagnosticsResponse(BaseModel, extra="forbid"):
    registration: Registration = Field(...)
    authorization: Authorization = Field(...)
    features: list[LicensingFeature] = Field(...)
    reservation_mode: bool = Field(...)
    transport: LicensingTransportResponse = Field()
    udi: Udi = Field(...)
    product_license: ProductLicense = Field(...)


class NodeDefinitionDiagnostics(BaseModel, extra="forbid"):
    """Node definition diagnostics info"""

    id: DefinitionID = Field(...)
    images: list[DefinitionID] = Field(...)


NodeDefinitionDiagnosticsResponse = list[NodeDefinitionDiagnostics]


class NodeLaunchQueueDiagnostics(BaseModel, extra="forbid"):
    """Node launch queue diagnostics info"""

    boot_disk_size: DiskSpace = Field(default=None)
    cpu_limit: CpuLimit = Field(default=None)
    cpus: AllocatedCpus = Field(...)
    data_volume: DiskSpace = Field(default=None)
    hide_links: bool = Field(default=None, description="Whether to hide links to/from this node.")
    id: NodeId
    image_definition: DefinitionID | None = Field(default=None, description="Image Definition ID for the specified node.")
    lab_id: UUID4Type = Field(default=None)
    label: NodeLabel = Field(default=None)
    node_definition: DefinitionID = Field(..., description="Node Definition ID for the specified node.")
    parameters: NodeParameters
    pinned_compute_id: PinnedComputeID = Field(default=None)
    ram: Ram = Field(default=None)
    tags: TagArray = Field(default=None)
    x: Coordinate = Field(default=None, description="Node X coordinate.")
    y: Coordinate = Field(default=None, description="Node Y coordinate.")


NodeLaunchQueueDiagnosticsResponse = list[NodeLaunchQueueDiagnostics]


class ServiceDiagnosticsResponse(BaseModel, extra="forbid"):
    dispatcher: bool = Field(...)
    termws: bool = Field(...)


class StartupSchedulerDiagnosticsResponse(BaseModel, extra="forbid"):
    licensing_loaded: bool | None = Field(...)
    core_driver_connected: bool = Field(...)
    node_definitions_loaded: bool = Field(...)
    lld_connected: bool = Field(...)
    lld_synced: bool = Field(...)
    system_ready: bool = Field(...)


UserDiagnosticsResponse = list[UserResponse]


class InternalDiagnosticsResponse(BaseModel, extra="forbid"):
    computes: ComputeDiagnosticsResponse = Field(...)
    labs: LabDiagnosticsResponse = Field(...)
    lab_events: LabEventDiagnosticsResponse = Field(...)
    node_launch_queue: NodeLaunchQueueDiagnosticsResponse = Field(...)
    services: ServiceDiagnosticsResponse = Field(...)
    startup_scheduler: StartupSchedulerDiagnosticsResponse = Field(...)
    user_list: UserDiagnosticsResponse = Field(...)
    licensing: LicensingDiagnosticsResponse = Field(...)
    node_definitions: NodeDefinitionDiagnosticsResponse = Field(...)
    licensing_status: LicensingStatusDiagnosticsResponse = Field(...)


DiagnosticsResponse = (
    ComputeDiagnosticsResponse
    | EventDiagnosticsResponse
    | LabDiagnosticsResponse
    | LabEventDiagnosticsResponse
    | LicensingDiagnosticsResponse
    | NodeDefinitionDiagnosticsResponse
    | NodeLaunchQueueDiagnosticsResponse
    | ServiceDiagnosticsResponse
    | StartupSchedulerDiagnosticsResponse
    | UserDiagnosticsResponse
    | InternalDiagnosticsResponse
)
