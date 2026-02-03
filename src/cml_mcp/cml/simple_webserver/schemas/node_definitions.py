#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#
import re
from enum import StrEnum, auto
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field, conlist, model_validator
from simple_common.schemas import ConfigurationMediaType, DomainDriver
from simple_webserver.schemas.common import (
    DefinitionID,
    DeviceNature,
    DriverType,
    FilePath,
)
from simple_webserver.schemas.nodes import NodeConfigurationContent, NodeParameters
from simple_webserver.schemas.pyats import PyAtsCredentials, PyAtsModel, PyAtsOs


class NicDriver(StrEnum):
    VIRTIO = auto()
    E1000 = auto()
    RTL8139 = auto()
    VMXNET3 = auto()
    E1000E = auto()
    E1000_82544GC = "e1000-82544gc"
    E1000_82545EM = "e1000-82545em"
    I82550 = auto()
    I82551 = auto()
    I82557A = auto()
    I82557B = auto()
    I82557C = auto()
    I82558A = auto()
    I82558B = auto()
    I82559A = auto()
    I82559B = auto()
    I82559C = auto()
    I82559ER = auto()
    I82562 = auto()
    I82801 = auto()


class DiskDriver(StrEnum):
    IDE = auto()
    SATA = auto()
    VIRTIO = auto()


class VideoModel(StrEnum):
    VGA = auto()
    CIRRUS = auto()
    VMVGA = auto()
    QXL = auto()
    XEN = auto()
    VIRTIO = auto()
    NONE = auto()


class VideoDevice(BaseModel, extra="forbid"):
    memory: int = Field(..., description="Video Memory.", ge=1, le=128)
    model: VideoModel = Field(default=None, description="Video Model.")


class LinuxNative(BaseModel, extra="forbid"):
    """Base for simulation objects."""

    libvirt_domain_driver: DomainDriver = Field(..., description="Domain Driver.")
    driver: DriverType = Field(..., description="Simulation Driver.")
    disk_driver: DiskDriver = Field(default=None, description="Disk Driver.")
    efi_boot: bool = Field(default=None, description="If set, use EFI boot for the VM.")
    efi_code: FilePath = Field(default=None, description="EFI code file path; if unset, use default.")
    efi_vars: FilePath = Field(
        default=None,
        description="EFI NVRAM var template path; if unset, the code file "
        "is made writable; if set to constant 'stateless', "
        "the code file is marked stateless.",
    )
    machine_type: str = Field(
        default=None,
        description="QEMU machine type, defaults to pc; q35 is more modern.",
        min_length=1,
        max_length=32,
    )
    ram: int = Field(default=None, description="Memory in MiB.", ge=1, le=1048576)
    cpus: int = Field(default=None, description="CPUs.", ge=1, le=128)
    cpu_limit: int = Field(default=None, description="CPU Limit.", ge=20, le=100)
    cpu_model: str = Field(
        default=None,
        min_length=1,
        max_length=64,
        pattern=re.compile(r"^[a-zA-Z\d-]{1,32}(,[+!?^-][a-z\d._]{1,16})*(?![\n\r])$"),
    )
    nic_driver: NicDriver = Field(
        default=None,
        description="Network Driver.",
    )
    data_volume: int = Field(default=None, description="Data Disk Size in GiB.", ge=0, le=4096)
    boot_disk_size: int = Field(default=None, description="Boot Disk Size in GiB.", ge=0, le=4096)
    video: VideoDevice = Field(default=None, description="If present, then VNC can be used with the node VM.")
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
        required: list[str] = []
        if self.libvirt_domain_driver is DomainDriver.KVM:
            required = ["cpus", "ram", "nic_driver", "disk_driver"]
        elif self.libvirt_domain_driver.is_simulated:
            required = ["ram"]
        for key in required:
            if not getattr(self, key, None):
                raise ValueError(f"{key} must be specified when libvirt_domain_driver is" f" {self.libvirt_domain_driver.value}")
        return self


PhysicalField = Annotated[str, Field(min_length=1, max_length=32)]

LoopBackField = Annotated[str, Field(min_length=1, max_length=32)]

ManagementField = Annotated[str, Field(min_length=1, max_length=32)]


class Interfaces(BaseModel, extra="forbid"):
    """
    Interface configurations.
    """

    serial_ports: int = Field(
        ...,
        description="""
            Number of serial ports (console, aux, ...). Maximum value is 4 for KVM
            and 2 for Docker/IOL nodes.
        """,
        ge=0,
        le=4,
    )
    default_console: int = Field(
        default=None,
        description="Default serial port for console connections.",
        ge=0,
        le=4,
    )
    physical: conlist(PhysicalField, min_length=1) = Field(..., description="List of physical interfaces.")
    has_loopback_zero: bool = Field(..., description="Has `loopback0` interface (used with ANK).")
    min_count: int = Field(
        default=None,
        description="Minimal number of physical interfaces needed to start a node.",
        ge=0,
        le=64,
    )
    default_count: int = Field(default=None, description="Default number of physical interfaces.", ge=1, le=64)
    iol_static_ethernets: Literal[0, 4, 8, 12, 16] = Field(
        default=None,
        description="Only for IOL nodes, the number of static Ethernet interfaces"
        " preceding any serial interface; default 0 means "
        "all interfaces are Ethernet.",
    )
    loopback: conlist(LoopBackField, min_length=1) = Field(default=None, description="List of loopback interfaces.")
    management: conlist(ManagementField, min_length=1) = Field(default=None, description="List of management interfaces.")

    @model_validator(mode="after")
    def validate_one_of(self):
        if self.has_loopback_zero and not self.loopback:
            raise ValueError("loopback must be specified when has_loopback_zero=True")
        return self


class VMProperties(BaseModel, extra="forbid"):
    """Virtual Machine properties."""

    ram: bool = Field(..., description="RAM")
    cpus: bool = Field(..., description="CPU Count.")
    data_volume: bool = Field(..., description="Data Disk Size.")
    boot_disk_size: bool = Field(..., description="Boot Disk Size.")
    cpu_limit: bool = Field(default=None, description="CPU Limit.")


CompletedNode = Annotated[str, Field(max_length=128)]


class Boot(BaseModel, extra="forbid"):
    timeout: int = Field(..., description="Timeout (seconds).", examples=[60], le=86400)
    completed: conlist(CompletedNode, min_length=1) = Field(
        default=None,
        description='A list of strings which should be matched to determine when the node is "ready".',
        examples=[[CompletedNode("string")]],
    )
    uses_regex: bool = Field(
        default=None,
        description="Whether the strings in `completed` should be treated as regular expressions or not.",
    )


class UsageEstimations(BaseModel, extra="forbid"):
    """
    Estimated resource usage.
    """

    cpus: int = Field(
        default=None,
        description=("Estimated CPUs usage in one-hundred-part shares of whole CPUs " "(up to 128 CPUs / 12800 shares)."),
        ge=1,
        le=12800,
        examples=[40],
    )
    ram: int = Field(
        default=None,
        description="Estimated RAM usage in MiB.",
        ge=1,
        le=1048576,
        examples=[50],
    )
    disk: int = Field(
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
    parameters: NodeParameters
    usage_estimations: UsageEstimations = Field(default=None, description="Estimated resource usage parameters.")


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


class ConfigurationDriver(StrEnum):
    ASAV = auto()
    ALPINE = auto()
    CAT9000V = auto()
    COREOS = auto()
    CSR1000v = auto()
    DESKTOP = auto()
    FMCV = auto()
    FTDV = auto()
    IOSV = auto()
    IOSVL2 = auto()
    IOSXRV = auto()
    IOSXRV9000 = auto()
    LXC = auto()
    NXOSV = auto()
    NXOSV9000 = auto()
    PAGENT = auto()
    SDWAN = auto()
    SDWAN_EDGE = auto()
    SDWAN_MANAGER = auto()
    SERVER = auto()
    TREX = auto()
    UBUNTU = auto()
    WAN_EMULATOR = auto()


class ConfigurationGenerator(BaseModel, extra="forbid"):
    """
    Generator configuration details.
    """

    driver: ConfigurationDriver | None = Field(..., description="Configuration Driver.")


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

    files: conlist(ConfigurationFile, min_length=1) = Field(..., description="List of node configuration file objects.")
    media_type: ConfigurationMediaType = Field(..., description="The type of the configuration media.")
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


class Icon(StrEnum):
    router = auto()
    switch = auto()
    server = auto()
    host = auto()
    cloud = auto()
    firewall = auto()
    access_point = auto()
    wlc = auto()


URI_BASE64_IMAGE_CONTENT_REGEX = re.compile(
    r"^data:image/(png|jpeg|svg\+xml);base64,((?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{4}|" r"[A-Za-z0-9+/]{3}=|[A-Za-z0-9+/]{2}={2}))$"
)


def validate_icon_uri(uri: str) -> str:
    """
    Validates if the string is a valid base64 encoded image URI
    containing PNG, JPEG, or SVG.
    """
    if not URI_BASE64_IMAGE_CONTENT_REGEX.fullmatch(uri):
        raise ValueError("Invalid URI content. Check encoded data type")
    return uri


IconDataUri = Annotated[str, AfterValidator(validate_icon_uri)]


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
    icon: Icon | IconDataUri = Field(
        ...,
        description="The icon to use with this node type."
        "Select one from the list or pass custom URI with "
        "png|jpeg|svg+xml image encoded to base64 in following "
        "format: data:<MIME_TYPE>;base64,<BASE_64_CONTENT>",
    )

    label: str = Field(..., description="The node type label.", min_length=1, max_length=32)
    visible: bool = Field(..., description="Determines visibility in the UI for this node type.")
    group: Literal["Cisco", "Others"] = Field(default=None, description="Intended to group similar node types (unused).")
    description: str = Field(
        default=None,
        description="The description of the node type (can be Markdown).",
        max_length=4096,
    )


class UiSimplified(Ui, extra="forbid"):
    has_configuration: bool = Field(default=None)
    show_ram: bool = Field(default=None)
    show_cpus: bool = Field(default=None)
    show_cpu_limit: bool = Field(default=None)
    show_data_volume: bool = Field(default=None)
    show_boot_disk_size: bool = Field(default=None)
    has_config_extraction: bool = Field(default=None)


class Inherited(BaseModel, extra="forbid"):
    image: VMProperties = Field(...)
    node: VMProperties = Field(...)


class PyAts(PyAtsCredentials, extra="forbid"):
    os: PyAtsOs = Field(...)
    series: str = Field(
        default=None,
        description="The device series as defined by pyATS / Unicon.",
        min_length=1,
        max_length=32,
    )
    model: PyAtsModel = Field(default=None)
    use_in_testbed: bool = Field(default=True, description="Use this device in an exported testbed?")
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
    pyats: PyAts = Field(default=None)
    schema_version: Schema = Field(default=None)
    image_definitions: list[DefinitionID] = Field(
        default_factory=list,
        description="""
            The current list of installed image definitions that are associated with the
            node definition.
        """,
    )

    @model_validator(mode="after")
    def validate_serial_consoles_number(self):
        serial_ports = self.device.interfaces.serial_ports
        domain_driver = self.sim.linux_native.libvirt_domain_driver

        max_limit = domain_driver.serial_port_limit

        if serial_ports > max_limit:
            raise ValueError(f"{domain_driver} supports up to {serial_ports} serial consoles.")

        return self


class SimulationUiSimplified(BaseModel, extra="forbid"):
    """
    Simplified simulation parameters.
    """

    parameters: NodeParameters
    ram: int = Field(default=None, ge=0)
    cpus: int = Field(default=None, ge=0)
    cpu_limit: int = Field(default=100, ge=20, le=100)
    data_volume: int = Field(default=None, ge=0)
    boot_disk_size: int = Field(default=None, ge=0)
    console: bool = Field(default=None)
    simulate: bool = Field(default=None)
    custom_mac: bool = Field(default=None)
    vnc: bool = Field(default=None)


class SimplifiedNodeDefinition(BaseModel, extra="forbid"):
    id: DefinitionID = Field(
        ...,
        description="""
            A symbolic name used to identify this node definition, such as `iosv` or
            `asav`.
        """,
    )
    general: General = Field(...)
    device: Device = Field(...)
    ui: UiSimplified = Field(...)
    sim: SimulationUiSimplified = Field(...)
    image_definitions: list[DefinitionID] = Field(default_factory=list)
