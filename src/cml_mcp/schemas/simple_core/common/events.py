#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#
from __future__ import annotations

import time
from datetime import datetime
from enum import Enum
from typing import NamedTuple

import attr

from .type_hints import (
    ComputeId,
    ExternalConnectorId,
    LabId,
    LinkCaptureKey,
    LinkId,
    NodeId,
    NoticeId,
    UserId,
)


class BootEventType(Enum):
    MONITOR = 1
    BOOTED = 2


@attr.s(kw_only=True)
class BaseEvent:
    timestamp: int = attr.ib(factory=lambda: int(time.time()))
    isotimestamp: str = attr.ib(init=False)

    def __attrs_post_init__(self):
        self.isotimestamp = datetime.fromtimestamp(self.timestamp).isoformat()


@attr.s(kw_only=True)
class BootProgressDiagnosticEvent(BaseEvent):
    lab_id: LabId = attr.ib()
    node_id: NodeId = attr.ib()
    event: BootEventType = attr.ib()

    def as_dict(self):
        return {
            "lab_id": self.lab_id,
            "node_id": self.node_id,
            "event": self.event.name,
            "timestamp": self.isotimestamp,
        }


class LabEventType(Enum):
    ADD = 1
    REMOVE = 2
    CHANGE = 3
    STATE_CHANGED = 4


class LabEventElementType(Enum):
    LAB = 1
    NODE = 2
    LINK = 3
    INTERFACE = 4
    ANNOTATION = 5
    CONNECTOR_MAPPING = 6
    SMART_ANNOTATION = 7


class LinkConditionEvent(NamedTuple):
    lab_id: LabId
    link_id: LinkId
    data: dict[str, int] = {}


class LldEventTypes(Enum):
    REGISTERED = 0
    CONNECTED = 1
    SYNCED = 2
    DISCONNECTED = 3
    READINESS = 4
    SYNC_FAILED = 5
    REMOVED = 6
    STATE_CHANGED = 7


class LldEvent(NamedTuple):
    id: ComputeId
    event_type: LldEventTypes
    data: dict = {}


# Events that are commented out are libvirt events that are not used at all.
# We don't actually need this enum.  We could use libvirt events instead.
# But this is more readable.
class NodeEventTypes(Enum):
    DEFINED = 0
    UNDEFINED = 1
    STARTED = 2
    # SUSPENDED = 3
    # RESUMED = 4
    STOPPED = 5
    # SHUTDOWN = 6
    # PMSUSPENDED = 7
    # CRASHED = 8


class LldNodeEvent(NamedTuple):
    id: ComputeId
    node_id: NodeId
    event_type: NodeEventTypes


class NoticeEventTypes(Enum):
    ADD = 1
    REMOVE = 2
    CHANGE = 3
    ACKNOWLEDGEMENT = 4
    MAINTENANCE = 5


class NoticeEvent(NamedTuple):
    id: NoticeId
    event_type: NoticeEventTypes


class ExternalConnectorEventTypes(Enum):
    ADD = 1
    REMOVE = 2
    CHANGE = 3
    SYNC = 4


class ExternalConnectorEvent(NamedTuple):
    id: ExternalConnectorId | None
    event_type: ExternalConnectorEventTypes


class PcapEventTypes(str, Enum):
    START = 1
    STOP = 2


class PcapEvent(NamedTuple):
    status: PcapEventTypes
    lab_id: LabId
    link_id: LinkId
    link_capture_key: LinkCaptureKey


class StopConsoleEvent(NamedTuple):
    lab_id: LabId
    console_uuid: str


class SystemEventTypes(Enum):
    FEEDBACK_SUBMITTED = 1
    FEEDBACK_FAILURE = 2


class SystemEvent(NamedTuple):
    event_type: SystemEventTypes
    message: str
    data: dict


class LabUsersChangedEvent(NamedTuple):
    lab_id: LabId
    users: list[UserId]
