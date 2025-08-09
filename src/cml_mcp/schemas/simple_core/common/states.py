#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#
from enum import Enum


class FSMState(Enum):
    pass


class LabState(FSMState):
    DEFINED_ON_CORE = 0
    STOPPED = 1
    STARTED = 2


class NodeState(FSMState):
    DEFINED_ON_CORE = 0
    STOPPED = 1
    STARTED = 2
    QUEUED = 3
    BOOTED = 4
    DISCONNECTED = 5

    @property
    def is_starting(self) -> bool:
        return self is NodeState.QUEUED or self is NodeState.STARTED or self is NodeState.BOOTED


class LinkState(FSMState):
    DEFINED_ON_CORE = 0
    STOPPED = 1
    STARTED = 2


class InterfaceState(FSMState):
    DEFINED_ON_CORE = 0
    STOPPED = 1
    STARTED = 2
