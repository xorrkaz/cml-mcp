#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#
from datetime import datetime
from enum import StrEnum
from typing import Annotated

from fastapi import Body
from pydantic import BaseModel, Field, model_validator

from cml_mcp.schemas.common import (
    Hostname,
    IPNetwork,
    Label,
    MACAddress,
    TagArray,
    UUID4ArrayType,
    UUID4Type,
)
from cml_mcp.schemas.external_connector import ExternalConnectorDeviceName


class WebSocketStatusResponse(BaseModel):
    """(**Placeholder**) Expect the fields and values to change in the future."""

    clients: str = Field(default=None, description="Client status information.")
    capture_websockets: str = Field(default=None, description="Capture websocket status.")
    capture_server_stream: str = Field(default=None, description="Capture server stream status.")
    lld_websocket: str = Field(default=None, description="LLD websocket status.")


class ExternalConnectorForwardingItems(StrEnum):
    BRIDGE = "BRIDGE"
    NAT = "NAT"
    OFF = "OFF"


ExternalConnectorForwarding = Annotated[
    ExternalConnectorForwardingItems,
    Field(
        description="""
    External connector bridge forwarding mode.
    * `BRIDGE` - forwards to a member L2 interface (physical, vlan, etc.)
    * `NAT` - forwards using the controller host's routing tables with NAT.
    * `OFF` - isolated private network for labs on the same CML instance.
    """,
        examples=[ExternalConnectorForwardingItems.NAT],
    ),
]


class ExternalConnectorBase(BaseModel, extra="allow"):
    """
    Configurable properties of available external connector target device (bridge)
    which are realized by lower-level services on the controller host.
    At this point, only IP snooper and L2 filtering are managed via this API.
    """

    snooped: bool = Field(
        default=None,
        description="IP snooping service is enabled for the network segment.",
    )
    protected: bool = Field(
        default=None,
        description="L2 protection filtering is enabled for the network segment.",
    )


ExternalConnectorLabel = Annotated[Label, Field(description="Unique label for the external connector.")]


class ExternalConnectorConfig(ExternalConnectorBase, extra="allow"):
    """
    Configurable properties of external connector target device (bridge).
    """

    label: ExternalConnectorLabel = Field(default=None)
    tags: TagArray = Field(default=None, description="Assigned tags denoting purpose of the connector.")


class ExternalConnectorUpdate(ExternalConnectorConfig, extra="forbid"):
    """
    Update properties of external connector target device (bridge).
    """

    pass


class ExternalConnectorState(ExternalConnectorBase, extra="forbid"):
    """
    Operational state of an external connector target device (bridge).
    """

    label: ExternalConnectorLabel | None = Field(...)
    interface: str | None = Field(...)
    forwarding: ExternalConnectorForwarding = Field(..., description="Forwarding mode for the bridge.")
    mtu: int = Field(default=None, description="MTU on the bridge device.")
    exists: bool = Field(default=None, description="The device exists on the controller host.")
    enabled: bool = Field(default=None, description="The device is enabled for forwarding.")
    stp: bool = Field(
        default=None,
        description="The connector bridge participates in the Spanning Tree Protocol.",
    )
    ip_networks: list[IPNetwork] | None = Field(default=None, description="Assigned IP networks to the bridge device.")


class ExternalConnector(ExternalConnectorConfig, extra="forbid"):
    """
    External connector target device (bridge) configuration and state.
    """

    id: UUID4Type = Field(..., description="The external connector's unique identifier.")
    label: ExternalConnectorLabel = Field(...)
    device_name: ExternalConnectorDeviceName = Field(
        default=None,
        description="The (bridge) interface name on the controller host used for outbound traffic.",
    )
    allowed: bool = Field(
        default=None,
        description=(
            "If true, the calling user is allowed to start external connector nodes "
            "which are configured to use this external connector bridge. "
            "Users may be limited by the resource pool settings imposed on them."
        ),
    )
    operational: ExternalConnectorState = Field(default=None, description="The operational state of the external connector.")
    protected: bool = Field(
        default=None,
        description="L2 protection filtering is enabled for the network segment.",
    )
    snooped: bool = Field(
        default=None,
        description="IP snooping service is enabled for the network segment.",
    )
    tags: TagArray = Field(default=None, description="Assigned tags denoting the purpose of the connector.")


class ExternalConnectorsSync(BaseModel):
    push_configured_state: bool = Field(
        default=True,
        description="""
      If true, the (default-if-newly-detected) connector configuration is
      pushed into the controller host system; this means all bridges will
      be set to snooped, and L2 bridges will be protected.
      If false, the host state is preserved and reported in the response.
    """,
    )


class ComputeStates(StrEnum):
    UNREGISTERED = "UNREGISTERED"
    REGISTERED = "REGISTERED"
    ONLINE = "ONLINE"
    READY = "READY"


ComputeState = Annotated[
    ComputeStates,
    Field(
        description="""
    Compute host administrative admission state.
    * `UNREGISTERED` - host shall be disconnected by controller before removal.
    * `REGISTERED` - host has been registered (will be switched ready immediately).
    * `ONLINE` - host is part of cluster but does not allow to start nodes.
    * `READY` - host is part of cluster and allowed to start nodes.
    """,
        examples=[ComputeStates.READY],
    ),
]


class ComputeHostConfig(BaseModel, extra="forbid"):
    """Compute host configurable attributes."""

    admission_state: ComputeState = Field(...)


class NodeCountsBase(BaseModel):
    total_nodes: int | None = Field(default=None, description="The total number of nodes.")
    total_orphans: int | None = Field(default=None, description="The total number of orphaned nodes.")
    running_nodes: int | None = Field(default=None, description="The total number of running nodes.")
    running_orphans: int | None = Field(default=None, description="The total number of running orphaned nodes.")


class NodeCounts(NodeCountsBase, extra="forbid"):
    pass


class ComputeHostBase(BaseModel, extra="forbid"):
    """
    Information about administrative state of a compute host.
    """

    id: UUID4Type = Field(..., description="The compute host's unique identifier.")
    server_address: str = Field(..., description="Host address on the internal cluster network.")
    hostname: Hostname = Field(..., description="The compute host's unique hostname.")
    is_simulator: bool = Field(..., description="Host is used for virtual machine nodes.")
    is_connector: bool = Field(
        ...,
        description="Host is used for external connector and unmanaged switch nodes.",
    )
    admission_state: ComputeState = Field(..., description="The admission state of the compute host.")
    nodes: UUID4ArrayType = Field(..., description="List of node ID's deployed on the host.", deprecated=True)
    node_counts: NodeCounts = Field(..., description="Count of nodes and orphans deployed and running on the host.")
    is_connected: bool = Field(..., description="Host is communicating with the controller.")
    is_synced: bool = Field(..., description="Host state is synchronized with the controller.")


class SystemNoticeLevels(StrEnum):
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"


SystemNoticeLevel = Annotated[
    SystemNoticeLevels,
    Field(
        description="""
    System notice importance level.
    * `INFO` - informative neutral notice.
    * `SUCCESS` - notice reporting a successful outcome.
    * `WARNING` - notice warning about potential issues or actions to take.
    * `ERROR` - notice reporting a negative outcome or required actions.
    """,
        examples=[SystemNoticeLevels.WARNING],
    ),
]

SystemNoticeLabel = Annotated[Label, Field(description="Short label or heading of the notice.")]

SystemNoticeContent = Annotated[str, Field(max_length=8192, description="Content of the notice message.")]

SystemNoticeEnabled = Annotated[bool, Field(description="Notice is enabled and actively shown to users.")]


class SystemNoticeAcknowledgements(BaseModel, extra="allow"):
    @model_validator(mode="after")
    def check_types(self):
        for field_name, value in self.__dict__.items():
            if not isinstance(value, bool):
                raise TypeError(f"Value for '{field_name}' must be a bool, " f"but got {type(value).__name__}.")
        return self


class SystemNoticeBase(BaseModel, extra="allow"):
    """
    Basic information about an administrative notice to users.
    """

    level: SystemNoticeLevel = Field(default=SystemNoticeLevels.INFO)
    label: SystemNoticeLabel = Field(default=None)
    content: SystemNoticeContent = Field(default=None)
    enabled: SystemNoticeEnabled = Field(default=None)


class SystemNoticeCreate(SystemNoticeBase, extra="forbid"):
    """
    Attributes of a new administrative notice to users.
    """

    groups: UUID4ArrayType = Field(default=None, description="List of group IDs associated to the created notice.")
    level: SystemNoticeLevel = Field(...)
    label: SystemNoticeLabel = Field(...)
    content: SystemNoticeContent = Field(default="")
    enabled: SystemNoticeEnabled = Field(default=False)


class SystemNoticeAcknowledgementUpdate(BaseModel, extra="forbid"):
    """
    Update an administrative notice's acknowledgement state for some users.
    """

    acknowledged: SystemNoticeAcknowledgements = Field(..., description="Users and their new acknowledgement states.")


class SystemNoticeActivated(BaseModel, extra="forbid"):
    """
    Model representing the activation timestamp of a system notice.
    """

    activated: datetime | None = Field(default=None, description="Timestamp when the notice was enabled")


class SystemNoticeUpdate(SystemNoticeBase, extra="forbid"):
    """
    Administrative notice update attributes.
    """

    add_groups: UUID4ArrayType = Field(default=None, description="List of group IDs to associate with the notice.")
    del_groups: UUID4ArrayType = Field(default=None, description="List of group IDs to disassociate from the notice.")


class SystemNotice(SystemNoticeBase, SystemNoticeActivated, extra="forbid"):
    """
    Information about an administrative notice to users.
    """

    id: UUID4Type = Field(..., description="The notice's unique identifier.")
    acknowledged: SystemNoticeAcknowledgements = Field(
        default=None,
        description="Users which receive this notice and their acknowledgement status.",
    )
    level: SystemNoticeLevel = Field(...)
    label: SystemNoticeLabel = Field(...)
    content: SystemNoticeContent = Field(...)
    enabled: SystemNoticeEnabled = Field(...)
    groups: UUID4ArrayType = Field(default=None, description="List of group IDs associated with the notice.")


class MaintenanceModeBase(BaseModel, extra="allow"):
    """
    Common maintenance mode configuration attributes.
    """

    maintenance_mode: bool = Field(
        default=None,
        description="Enable maintenance mode, e.g. to disallow non-admin access.",
        examples=[True],
    )
    notice: UUID4Type | None = Field(
        default=None,
        description="Maintenance login screen system notice's unique identifier.",
    )


class MaintenanceModeUpdate(MaintenanceModeBase, extra="forbid"):
    """
    Maintenance mode configuration options.
    """

    pass


class MaintenanceMode(MaintenanceModeBase, extra="forbid"):
    """
    Maintenance mode state.
    """

    resolved_notice: SystemNotice | None = Field(default=None, description="Configured maintenance system notice.")


class MemoryStats(BaseModel):
    used: float = Field(..., description="Amount of memory used.")
    free: float = Field(..., description="Amount of memory free.")
    total: float = Field(..., description="Total memory available.")


class DiskStats(BaseModel):
    used: float = Field(..., description="Amount of disk space used.")
    free: float = Field(..., description="Amount of disk space free.")
    total: float = Field(..., description="Total disk space available.")


class BasicCpuStats(BaseModel, extra="allow"):
    count: int = Field(default=0, ge=0)
    percent: float = Field(default=0.0, ge=0, le=100)


class CpuStats(BasicCpuStats, extra="forbid"):
    pass


class BasicComputeHostStats(BaseModel, extra="allow"):
    """
    The system statistics for a particular compute host.
    """

    cpu: CpuStats = Field(
        ...,
        description="CPU statistics that shows number of cpus and load percent",
    )
    memory: MemoryStats = Field(..., description="Memory statistics of the compute host.")
    disk: DiskStats = Field(..., description="Disk statistics of the compute host.")


class ComputeHostStats(BasicComputeHostStats, extra="forbid"):
    pass


class SystemInformation(BaseModel, extra="forbid"):
    """
    System information details.
    """

    version: str = Field(..., description="The CML release version.")
    ready: bool = Field(
        ...,
        description="Indicate whether there is at least one compute capable of starting nodes.",
    )
    allow_ssh_pubkey_auth: bool = Field(
        ...,
        description="Flag indicating whether SSH-based console server authentication is enabled.",
    )
    oui: MACAddress = Field(..., description="The OUI prefix used for all assigned interface MAC addresses.")


class DomInfo(NodeCountsBase, extra="forbid"):
    allocated_cpus: int = Field(..., description="The number of allocated CPUs.", ge=0)
    allocated_memory: int = Field(..., description="The number of allocated memory.", ge=0)


class CpuHealthStats(BasicCpuStats, extra="forbid"):
    model: str = Field(..., description="The CPU model name.")
    hyperthreading: bool = Field(default=False, description="Indicates if hyperthreading is enabled.")
    predicted: int = Field(..., description="The number of predicted CPUs.", ge=0)
    load: list[float] = Field(..., description="The CPU load (last few entries).")


class ComputeHostStatsWithDomInfo(BasicComputeHostStats, extra="forbid"):
    cpu: CpuHealthStats = Field(...)
    dominfo: DomInfo = Field(...)


class ComputeHostWithStats(BaseModel, extra="allow"):
    """
    Combines compute host statistics with additional details.
    """

    hostname: Hostname = Field(..., description="The hostname of the compute host.")
    is_controller: bool = Field(..., description="Indicates if the host is a controller.")
    stats: ComputeHostStatsWithDomInfo = Field(..., description="The compute host statistics.")


class ControllerDiskStats(BaseModel, extra="forbid"):
    disk: DiskStats


class SystemStats(BaseModel, extra="forbid"):
    """
    The system information for all compute hosts.
    """

    computes: dict[UUID4Type, ComputeHostWithStats] = Field(
        default=None,
        description="Individual compute hosts with their respective statistics.",
    )
    all: ComputeHostStats = Field(
        default=None,
        description="Controller host with statistics totals for all computes.",
    )
    controller: ControllerDiskStats = Field(default=None, description="Controller disk usage statistics.")


class ComputeHealth(BaseModel, extra="forbid"):
    kvm_vmx_enabled: bool | None = Field(...)
    enough_cpus: bool | None = Field(...)
    lld_connected: bool = Field(...)
    lld_synced: bool | None = Field(...)
    libvirt: bool | None = Field(...)
    fabric: bool | None = Field(...)
    device_mux: bool | None = Field(...)
    refplat_images_available: bool | None = Field(...)
    docker_shim: bool | None = Field(...)
    valid: bool | None = Field(...)
    admission_state: ComputeStates = Field(...)
    is_controller: bool = Field(...)
    hostname: Hostname = Field(...)


class ControllerHealth(BaseModel, extra="forbid"):
    core_connected: bool = Field(..., description="Indicates whether core controller is connected")
    nodes_loaded: bool = Field(..., description="Indicates whether nodes were loaded")
    images_loaded: bool = Field(..., description="Indicates whether image definitions were loaded")
    valid: bool = Field(..., description="Indicates whether the controller is in valid state.")


class SystemHealth(BaseModel, extra="forbid"):
    valid: bool | None = Field(..., description="Indicates if the system is healthy.")
    computes: dict[UUID4Type, ComputeHealth] = Field(..., description="Compute hosts health statistics.")
    is_licensed: bool | None = Field(..., description="Indicates if the system is licensed.")
    is_enterprise: bool = Field(..., description="Indicates if the system is enterprise.")
    controller: ControllerHealth = Field(..., description="Controller health statistics.")


ComputeHostUpdateBody = Annotated[ComputeHostConfig, Body(description="Set administrative state of a compute host.")]

ExternalConnectorUpdateBody = Annotated[
    ExternalConnectorUpdate,
    Body(description="Set configuration of an external connector."),
]

ExternalConnectorsSyncBody = Annotated[
    ExternalConnectorsSync | str,
    Body(description="Set parameters for external connector sync."),
]

SystemNoticeCreateBody = Annotated[SystemNoticeCreate, Body(description="Create a system notice.")]

SystemNoticeUpdateBody = Annotated[
    SystemNoticeUpdate | SystemNoticeAcknowledgementUpdate,
    Body(description="Set attributes or acknowledgements of a system notice."),
]

ExternalConnectorResponse = Annotated[ExternalConnector, Field(description="External connector configuration and state.")]
