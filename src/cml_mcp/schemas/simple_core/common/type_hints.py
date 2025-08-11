#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#
from __future__ import annotations

from enum import Enum
from typing import NewType

AnnotationId = NewType("AnnotationId", str)
BridgeId = NewType("BridgeId", str)
ComputeId = NewType("ComputeId", str)
ConsoleKey = NewType("ConsoleKey", str)
DomainId = NewType("DomainId", str)
ElementId = NewType("ElementId", str)
ExternalConnectorId = NewType("ExternalConnectorId", str)
GroupId = NewType("GroupId", str)
InterfaceId = NewType("InterfaceId", ElementId)
LabId = NewType("LabId", str)
RepoId = NewType("RepoId", str)
LinkCaptureKey = NewType("LinkCaptureKey", str)
LinkId = NewType("LinkId", ElementId)
MacAddress = NewType("MacAddress", str)
NodeId = NewType("NodeId", ElementId)
NoticeId = NewType("NoticeId", str)
ResourcePoolId = NewType("ResourcePoolId", str)
SmartAnnotationId = NewType("SmartAnnotationId", str)
Tag = NewType("Tag", str)
UserId = NewType("UserId", str)
UserName = NewType("UserName", str)
VNCKey = NewType("VNCKey", str)

ServiceKey = ConsoleKey | LinkCaptureKey | VNCKey


class Service(Enum):
    CONSOLE = "Console"
    PCAP = "PCAP"
    VNC = "VNC"
