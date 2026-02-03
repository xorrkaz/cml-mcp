#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#

from enum import StrEnum, auto

QCOW2 = "qcow2"
QCOW = "qcow"
TAR = "tar"
TARGZ = "tar.gz"
SUPPORTED_IMAGE_FORMATS = [QCOW2, QCOW, TAR, TARGZ]


class AuthMethod(StrEnum):
    LOCAL = auto()
    LDAP = auto()
    RADIUS = auto()


class BootEventType(StrEnum):
    MONITOR = "MONITOR"
    BOOTED = "BOOTED"


class ComputeState(StrEnum):
    UNREGISTERED = "UNREGISTERED"
    REGISTERED = "REGISTERED"
    ONLINE = "ONLINE"
    READY = "READY"

    @property
    def can_connect(self) -> bool:
        return self is ComputeState.ONLINE or self is ComputeState.READY

    @property
    def can_launch(self) -> bool:
        return self is ComputeState.READY

    @property
    def is_initial(self) -> bool:
        return self is ComputeState.REGISTERED or self is ComputeState.READY


class ConfigurationMediaType(StrEnum):
    ISO = auto()
    FAT = auto()
    RAW = auto()
    EXT4 = auto()


class DefaultPermissions:
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    LAB_VIEW = "lab_view"
    LAB_EXEC = "lab_exec"
    LAB_EDIT = "lab_edit"
    LAB_ADMIN = "lab_admin"
    FULL_PERMISSIONS = [LAB_ADMIN, LAB_EXEC, LAB_EDIT, LAB_VIEW]
    VIEW_PERMISSIONS = [LAB_VIEW]
    FULL_PERMISSION_SET = set(FULL_PERMISSIONS)


class DomainDriver(StrEnum):
    KVM = auto()
    NONE = auto()
    IOL = auto()
    DOCKER = auto()
    UMS = auto()

    @property
    def is_simulated(self) -> bool:
        return self is not DomainDriver.NONE and self is not DomainDriver.UMS

    @property
    def is_iol(self) -> bool:
        return self is DomainDriver.IOL

    @property
    def is_kvm_or_docker(self) -> bool:
        return self is DomainDriver.KVM or self is DomainDriver.DOCKER

    @property
    def max_disks(self) -> int:
        if not self.is_simulated:
            return 0
        if self is DomainDriver.KVM:
            return 4
        return 1

    @property
    def image_formats(self) -> list[str]:
        if not self.is_simulated:
            return []
        if self is DomainDriver.KVM:
            return SUPPORTED_IMAGE_FORMATS[:2]
        return SUPPORTED_IMAGE_FORMATS[2:]

    @property
    def serial_port_limit(self) -> int:
        if not self.is_simulated:
            return 0
        if self is DomainDriver.KVM:
            return 4
        return 2


class FSMState(StrEnum):
    pass


class LabState(FSMState):
    DEFINED_ON_CORE = "DEFINED_ON_CORE"
    STOPPED = "STOPPED"
    STARTED = "STARTED"


class NodeState(FSMState):
    DEFINED_ON_CORE = "DEFINED_ON_CORE"
    STOPPED = "STOPPED"
    STARTED = "STARTED"
    QUEUED = "QUEUED"
    BOOTED = "BOOTED"
    DISCONNECTED = "DISCONNECTED"

    @property
    def is_starting(self) -> bool:
        return self is NodeState.QUEUED or self is NodeState.STARTED or self is NodeState.BOOTED


class LinkState(FSMState):
    DEFINED_ON_CORE = "DEFINED_ON_CORE"
    STOPPED = "STOPPED"
    STARTED = "STARTED"


class InterfaceState(FSMState):
    DEFINED_ON_CORE = "DEFINED_ON_CORE"
    STOPPED = "STOPPED"
    STARTED = "STARTED"


class LabEventType(StrEnum):
    ADD = "CREATED"
    REMOVE = "DELETED"
    CHANGE = "MODIFIED"
    STATE_CHANGED = "state"


class LabEventElementType(StrEnum):
    LAB = "Lab"
    NODE = "Node"
    LINK = "Link"
    INTERFACE = "Interface"
    ANNOTATION = "Annotation"
    CONNECTOR_MAPPING = "ConnectorMapping"
    SMART_ANNOTATION = "SmartAnnotation"


class OptInStatus(StrEnum):
    ACCEPTED = auto()
    DECLINED = auto()
    UNSET = auto()


class TelemetryEventCategory(StrEnum):
    START_LAB = auto()
    STOP_LAB = auto()
    QUEUE_NODE = auto()
    STOP_NODE = auto()
    START_NODE = auto()
    BOOT_NODE = auto()
    WIPE_NODE = auto()
    PACKET_CAPTURE = auto()
    LICENSE_INFO = auto()
    MAINTENANCE_STATE_CHANGE = auto()
    NOTICE_STATE_CHANGE = auto()
    RUNNING_NODES = auto()
    RESOURCE_POOL = auto()
    USER_ACTIVITY = auto()
    USER_GROUP = auto()
    SYSTEM_STATS = auto()
    BLKINFO = auto()
    VMWARE = auto()
    DMIINFO = auto()
    CPUINFO = auto()
    MEMINFO = auto()
    HYPERVISOR = auto()
    IMPORT_LAB = auto()
    EXPORT_LAB = auto()
    AAA_INFO = auto()
