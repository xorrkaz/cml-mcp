#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#

from enum import StrEnum, auto


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
        return (
            self is NodeState.QUEUED
            or self is NodeState.STARTED
            or self is NodeState.BOOTED
        )


class LinkState(FSMState):
    DEFINED_ON_CORE = "DEFINED_ON_CORE"
    STOPPED = "STOPPED"
    STARTED = "STARTED"


class InterfaceState(FSMState):
    DEFINED_ON_CORE = "DEFINED_ON_CORE"
    STOPPED = "STOPPED"
    STARTED = "STARTED"


class LabEventType(StrEnum):
    ADD = "ADD"
    REMOVE = "REMOVE"
    CHANGE = "CHANGE"
    STATE_CHANGED = "STATE_CHANGED"


class LabEventElementType(StrEnum):
    LAB = "LAB"
    NODE = "NODE"
    LINK = "LINK"
    INTERFACE = "INTERFACE"
    ANNOTATION = "ANNOTATION"
    CONNECTOR_MAPPING = "CONNECTOR_MAPPING"
    SMART_ANNOTATION = "SMART_ANNOTATION"


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
