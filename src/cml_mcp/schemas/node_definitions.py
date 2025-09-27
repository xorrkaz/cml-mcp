#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#
import re
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from cml_mcp.schemas.common import DefinitionID, FilePath
from cml_mcp.schemas.nodes import NodeConfigurationContent, NodeParameters


class DriverTypes(StrEnum):
    ASAV = "asav"
    ALPINE = "alpine"
    CAT9K = "cat9k"
    COREOS = "coreos"
    CSR1000V = "csr1000v"
    EXTERNAL_CONNECTOR = "external_connector"
    IOL = "iol"
    IOL_L2 = "iol-l2"
    IOSV = "iosv"
    IOSVL2 = "iosvl2"
    IOSXRV = "iosxrv"
    IOSXRV9000 = "iosxrv9000"
    LXC = "lxc"
    NXOSV = "nxosv"
    NXOSV9000 = "nxosv9000"
    PAGENT = "pagent"
    SERVER = "server"
    TREX = "trex"
    UBUNTU = "ubuntu"
    UNMANAGED_SWITCH = "unmanaged_switch"
    WAN_EMULATOR = "wan_emulator"


class NicDrivers(StrEnum):
    VIRTIO = "virtio"
    E1000 = "e1000"
    RTL8139 = "rtl8139"
    VMXNET3 = "vmxnet3"
    E1000E = "e1000e"
    E1000_82544GC = "e1000-82544gc"
    E1000_82545EM = "e1000-82545em"
    I82550 = "i82550"
    I82551 = "i82551"
    I82557A = "i82557a"
    I82557B = "i82557b"
    I82557C = "i82557c"
    I82558A = "i82558a"
    I82558B = "i82558b"
    I82559A = "i82559a"
    I82559B = "i82559b"
    I82559C = "i82559c"
    I82559ER = "i82559er"
    I82562 = "i82562"
    I82801 = "i82801"


class LibvirtDomainDrivers(StrEnum):
    DOCKER = "docker"
    IOL = "iol"
    KVM = "kvm"
    LXC = "lxc"
    NONE = "none"


class DiskDrivers(StrEnum):
    IDE = "ide"
    SATA = "sata"
    VIRTIO = "virtio"


class VideoModels(StrEnum):
    VGA = "vga"
    CIRRUS = "cirrus"
    VMVGA = "vmvga"
    QXL = "qxl"
    XEN = "xen"
    VIRTIO = "virtio"
    NONE = "none"


class DeviceNature(StrEnum):
    ROUTER = "router"
    SWITCH = "switch"
    SERVER = "server"
    HOST = "host"
    CLOUD = "cloud"
    FIREWALL = "firewall"
    EXTERNAL_CONNECTOR = "external_connector"


class VideoDevice(BaseModel, extra="forbid"):
    memory: int = Field(..., description="Video Memory.", ge=1, le=128)
    model: VideoModels = Field(default=None, description="Video Model.")


class LinuxNative(BaseModel, extra="forbid"):
    """Base for simulation objects."""

    libvirt_domain_driver: LibvirtDomainDrivers = Field(..., description="Domain Driver.")
    driver: DriverTypes = Field(..., description="Simulation Driver.")
    disk_driver: DiskDrivers | None = Field(default=None, description="Disk Driver.")
    efi_boot: bool | None = Field(default=None, description="If set, use EFI boot for the VM.")
    efi_code: FilePath | None = Field(default=None, description="EFI code file path; if unset, use default.")
    efi_vars: FilePath | None = Field(
        default=None,
        description="EFI NVRAM var template path; if unset, the code file "
        "is made writable; if set to constant 'stateless', "
        "the code file is marked stateless.",
    )
    machine_type: str | None = Field(
        default=None,
        description="QEMU machine type, defaults to pc; q35 is more modern.",
        min_length=1,
        max_length=32,
    )
    ram: int | None = Field(default=None, description="Memory in MiB.", ge=1, le=1048576)
    cpus: int | None = Field(default=None, description="CPUs.", ge=1, le=128)
    cpu_limit: int | None = Field(default=None, description="CPU Limit.", ge=20, le=100)
    cpu_model: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        pattern=re.compile(r"^[a-zA-Z\d-]{1,32}(,[+!?^-][a-z\d._]{1,16})*(?![\n\r])$"),
    )
    nic_driver: NicDrivers | None = Field(
        default=None,
        description="Network Driver.",
    )
    data_volume: int | None = Field(default=None, description="Data Disk Size in GiB.", ge=0, le=4096)
    boot_disk_size: int | None = Field(default=None, description="Boot Disk Size in GiB.", ge=0, le=4096)
    video: VideoDevice | None = Field(default=None, description="If present, then VNC can be used with the node VM.")
    enable_rng: bool = Field(
        default=True,
        description="If set, use a random number generator.",
    )
    enable_tpm: bool = Field(
        default=False,
        description="If set, enable an emulated TPM 2.0.",
    )

    @model_validator(mode="after")
    def validate(self):
        if self.libvirt_domain_driver == LibvirtDomainDrivers.KVM:
            required = [self.cpus, self.ram, self.nic_driver, self.disk_driver]
            if not all(required):
                raise ValueError(f"{required} must be specified when libvirt_domain_driver=kvm")

        if self.ram is None and self.libvirt_domain_driver in [
            LibvirtDomainDrivers.DOCKER,
            LibvirtDomainDrivers.LXC,
            LibvirtDomainDrivers.IOL,
        ]:
            raise ValueError("ram must be specified when libvirt_domain_driver in [docker, lxc, iol]")
        return self


PhysicalField = Annotated[str, Field(min_length=1, max_length=32)]

LoopBackField = Annotated[str, Field(min_length=1, max_length=32)]

ManagementField = Annotated[str, Field(min_length=1, max_length=32)]


class Interfaces(BaseModel, extra="forbid"):
    """
    Interface configurations.
    """

    serial_ports: int = Field(..., description="Number of serial Ports (console, aux, ...).", ge=0, le=4)
    default_console: int | None = Field(
        default=None,
        description="Default serial port for console connections.",
        ge=0,
        le=4,
    )
    physical: list[PhysicalField] = Field(..., description="List of physical interfaces.")
    has_loopback_zero: bool = Field(..., description="Has `loopback0` interface (used with ANK).")
    min_count: int | None = Field(
        default=None,
        description="Minimal number of physical interfaces needed to start a node.",
        ge=0,
        le=64,
    )
    default_count: int | None = Field(default=None, description="Default number of physical interfaces.", ge=1, le=64)
    iol_static_ethernets: Literal[0, 4, 8, 12, 16] | None = Field(
        default=None,
        description="Only for IOL nodes, the number of static Ethernet interfaces"
        " preceding any serial interface; default 0 means "
        "all interfaces are Ethernet.",
    )
    loopback: list[LoopBackField] = Field(default_factory=list, description="List of loopback interfaces.")
    management: list[ManagementField] = Field(default_factory=list, description="List of management interfaces.")

    # @model_validator(mode="after")
    # def validate_one_of(self):
    #     if self.has_loopback_zero and not self.loopback:
    #         raise ValueError("loopback must be specified when has_loopback_zero=True")
    #     return self


class VMProperties(BaseModel, extra="forbid"):
    """Virtual Machine properties."""

    ram: bool = Field(..., description="RAM")
    cpus: bool = Field(..., description="CPU Count.")
    data_volume: bool = Field(..., description="Data Disk Size.")
    boot_disk_size: bool = Field(..., description="Boot Disk Size.")
    cpu_limit: bool | None = Field(default=None, description="CPU Limit.")


CompletedNode = Annotated[str, Field(max_length=128)]


class Boot(BaseModel, extra="forbid"):
    timeout: int = Field(..., description="Timeout (seconds).", examples=[60], le=86400)
    completed: list[CompletedNode] = Field(
        default=None,
        description='A list of strings which should be matched to determine when the node is "ready".',
        examples=[[CompletedNode("string")]],
    )
    uses_regex: bool | None = Field(
        default=None,
        description="Whether the strings in `completed` should be treated as regular expressions or not.",
    )


class UsageEstimations(BaseModel, extra="forbid"):
    """
    Estimated resource usage.
    """

    cpus: int | None = Field(
        default=None,
        description=("Estimated CPUs usage in one-hundred-part shares of whole CPUs " "(up to 128 CPUs / 12800 shares)."),
        ge=1,
        le=12800,
        examples=[40],
    )
    ram: int | None = Field(
        default=None,
        description="Estimated RAM usage in MiB.",
        ge=1,
        le=1048576,
        examples=[50],
    )
    disk: int | None = Field(
        default=None,
        description="Estimated Disk usage in MiB.",
        ge=1,
        le=4194304,
        examples=[500],
    )


class Simulation(BaseModel, extra="forbid"):
    """
    Simulation parameters.
    """

    linux_native: LinuxNative = Field(..., description="Linux native simulation configuration.")
    parameters: NodeParameters | None = Field(default=None, description="Node-specific parameters.")
    usage_estimations: UsageEstimations | None = Field(default=None, description="Estimated resource usage parameters.")


class General(BaseModel, extra="forbid"):
    """
    General information for the node type.
    """

    nature: DeviceNature = Field(..., description='The "nature" / kind of the node type defined here.')
    description: str = Field(default=None, description="A description of the node type.", max_length=4096)
    read_only: bool = Field(
        default=False,
        description="Whether the node definition can be updated and deleted.",
    )


class ConfigurationDrivers(StrEnum):
    asav = "asav"
    alpine = "alpine"
    cat9000v = "cat9000v"
    coreos = "coreos"
    csr1000v = "csr1000v"
    desktop = "desktop"
    fmcv = "fmcv"
    ftdv = "ftdv"
    iosv = "iosv"
    iosvl2 = "iosvl2"
    iosxrv = "iosxrv"
    iosxrv9000 = "iosxrv9000"
    lxc = "lxc"
    nxosv = "nxosv"
    nxosv9000 = "nxosv9000"
    pagent = "pagent"
    sdwan = "sdwan"
    sdwan_edge = "sdwan_edge"
    sdwan_manager = "sdwan_manager"
    server = "server"
    trex = "trex"
    ubuntu = "ubuntu"
    wan_emulator = "wan_emulator"


class ConfigurationMediaTypes(StrEnum):
    iso = "iso"
    fat = "fat"
    raw = "raw"
    ext4 = "ext4"


class ConfigurationGenerator(BaseModel, extra="forbid"):
    """
    Generator configuration details.
    """

    driver: ConfigurationDrivers | None = Field(..., description="Configuration Driver.")


class ConfigurationFile(BaseModel, extra="forbid"):
    """
    Configuration file details.
    """

    editable: bool = Field(..., description="Is the configuration file editable?")
    name: str = Field(
        ...,
        description="The name of the configuration file.",
        min_length=1,
        max_length=64,
    )
    content: NodeConfigurationContent = Field(default=None)


class ConfigurationProvisioning(BaseModel, extra="forbid"):
    """
    Provisioning configuration details.
    """

    files: list[ConfigurationFile] = Field(..., description="List of node configuration file objects.")
    media_type: ConfigurationMediaTypes = Field(..., description="The type of the configuration media.")
    volume_name: str = Field(
        ...,
        description="The volume name of the configuration media.",
        min_length=1,
        max_length=32,
    )


class Configuration(BaseModel, extra="forbid"):
    """
    Node definition configuration details.
    """

    generator: ConfigurationGenerator = Field(..., description="Generator configuration details.")
    provisioning: ConfigurationProvisioning = Field(default=None, description="Provisioning configuration details.")


class Device(BaseModel, extra="forbid"):
    interfaces: Interfaces = Field(...)


class Icons(StrEnum):
    router = "router"
    switch = "switch"
    server = "server"
    host = "host"
    cloud = "cloud"
    firewall = "firewall"
    access_point = "access_point"
    wl = "wl"


class Ui(BaseModel, extra="forbid"):
    """
    UI-related settings for the node type.
    """

    label_prefix: str = Field(
        ...,
        description="The textual prefix for node labels.",
        min_length=1,
        max_length=32,
    )
    icon: Icons = Field(..., description="The icon to use with this node type.")
    label: str = Field(..., description="The node type label.", min_length=1, max_length=32)
    visible: bool = Field(..., description="Determines visibility in the UI for this node type.")
    group: Literal["Cisco", "Others"] | None = Field(default=None, description="Intended to group similar node types (unused).")
    description: str | None = Field(
        default=None,
        description="The description of the node type (can be Markdown).",
        max_length=4096,
    )
    has_configuration: bool | None = Field(default=None)
    show_ram: bool | None = Field(default=None)
    show_cpus: bool | None = Field(default=None)
    show_cpu_limit: bool | None = Field(default=None)
    show_data_volume: bool | None = Field(default=None)
    show_boot_disk_size: bool | None = Field(default=None)
    has_config_extraction: bool | None = Field(default=None)


class Inherited(BaseModel, extra="forbid"):
    image: VMProperties = Field(...)
    node: VMProperties = Field(...)


class Pyats(BaseModel, extra="forbid"):
    os: str = Field(
        ...,
        description="The operating system as defined / understood by pyATS.",
        min_length=1,
        max_length=32,
    )
    series: str | None = Field(
        default=None,
        description="The device series as defined by pyATS / Unicon.",
        min_length=1,
        max_length=32,
    )
    model: str | None = Field(
        default=None,
        description="The device model as defined by pyATS / Unicon.",
        min_length=1,
        max_length=32,
    )
    use_in_testbed: bool | None = Field(default=None, description="Use this device in an exported testbed?")
    username: str | None = Field(
        default=None,
        description="Use this username with pyATS / Unicon when interacting with this node type.",
        min_length=1,
        max_length=64,
    )
    password: str | None = Field(
        default=None,
        description="Use this password with pyATS / Unicon when interacting with this node type.",
        min_length=1,
        max_length=128,
    )
    config_extract_command: str | None = Field(
        default=None,
        description="This is the CLI command to use when configurations " "should be extracted from a device of this node type.",
        max_length=4096,
    )


Schema = Annotated[
    str,
    Field(
        description="The schema version used for this node type.",
        min_length=1,
        max_length=32,
        examples=["0.0.1"],
    ),
]


class NodeDefinition(BaseModel, extra="forbid"):
    id: DefinitionID = Field(
        ...,
        description="""
            A symbolic name used to identify this node definition, such as `iosv` or
            `asav`.
        """,
    )
    boot: Boot = Field(...)
    sim: Simulation = Field(...)
    general: General = Field(...)
    configuration: Configuration = Field(...)
    device: Device = Field(...)
    ui: Ui = Field(...)
    inherited: Inherited = Field(default=None)
    pyats: Pyats = Field(default=None)
    schema_version: Schema = Field(default=None)


class SimulationUi(BaseModel, extra="forbid"):
    """
    Simplified simulation parameters.
    """

    parameters: NodeParameters = Field(default=None, description="Node-specific parameters.")
    ram: int | None = Field(default=None, ge=0)
    cpus: int | None = Field(default=None, ge=0)
    cpu_limit: int | None = Field(default=100, ge=20, le=100)
    data_volume: int | None = Field(default=None, ge=0)
    boot_disk_size: int | None = Field(default=None, ge=0)
    console: bool | None = Field(default=None)
    simulate: bool | None = Field(default=None)
    custom_mac: bool | None = Field(default=None)
    vnc: bool | None = Field(default=None)


class SimplifiedNodeDefinitionResponse(BaseModel, extra="allow"):
    id: DefinitionID = Field(
        ...,
        description="""
            A symbolic name used to identify this node definition, such as `iosv` or
            `asav`.
        """,
    )
    general: General = Field(...)
    device: Device = Field(...)
    ui: Ui = Field(...)
    sim: SimulationUi = Field(...)
    image_definitions: list[DefinitionID] = Field(default=None)


NodeDefinitionList = Annotated[
    list[NodeDefinition],
    Field(description="Array of Node Definitions"),
]
