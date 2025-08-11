#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#
from __future__ import annotations

from enum import Enum, StrEnum, auto

import attr

from .constants import SUPPORTED_IMAGE_FORMATS


class DomainDriver(Enum):
    KVM = 1
    LXC = 2
    NONE = 3
    IOL = 4
    DOCKER = 5
    UMS = 6

    @property
    def is_simulated(self) -> bool:
        return self is not DomainDriver.NONE and self is not DomainDriver.UMS

    @property
    def is_iol(self) -> bool:
        return self is DomainDriver.IOL

    @property
    def custom_mac(self) -> bool:
        return self is DomainDriver.KVM or self is DomainDriver.LXC or self is DomainDriver.DOCKER

    @property
    def interface_state(self) -> bool:
        return self is DomainDriver.KVM or self is DomainDriver.DOCKER

    @property
    def max_disks(self) -> int:
        if self.is_simulated is DomainDriver.NONE:
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
        if self is DomainDriver.IOL:
            return SUPPORTED_IMAGE_FORMATS[2:3]
        return SUPPORTED_IMAGE_FORMATS[3:]


@attr.s(kw_only=True)
class ConsistencyResult:
    missing_nodes: set[str] = attr.ib(converter=attr.converters.default_if_none(set()), factory=set)
    orphaned_nodes: set[str] = attr.ib(converter=attr.converters.default_if_none(set()), factory=set)

    def asdict(self) -> dict[str, set[str]]:
        return attr.asdict(self)


@attr.s(auto_attribs=True)
class Readiness:
    libvirt: bool = False
    fabric: bool = False
    device_mux: bool = False
    refplat_images_available: bool = False
    docker_shim: bool = False

    @property
    def can_sync(self) -> bool:
        return self.libvirt and self.fabric and self.device_mux

    def as_dict(self, can_connect=True) -> dict[str, bool | None]:
        if can_connect:
            return attr.asdict(self)
        else:
            return {
                "libvirt": None,
                "fabric": None,
                "device_mux": None,
                "refplat_images_available": None,
                "docker_shim": None,
            }


class DiagnosticsCategory(StrEnum):
    COMPUTES = auto()
    LABS = auto()
    LAB_EVENTS = auto()
    NODE_LAUNCH_QUEUE = auto()
    SERVICES = auto()
    NODE_DEFINITIONS = auto()
    USER_LIST = auto()
    LICENSING = auto()
    STARTUP_SCHEDULER = auto()


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
