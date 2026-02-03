#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#
from datetime import datetime
from enum import StrEnum, auto
from typing import Annotated

from fastapi import Body, Path
from pydantic import BaseModel, Field, model_validator
from simple_webserver.schemas.common import IPAddress, MACAddress, UUID4Type

LINK_ENCAP_DESCRIPTION = "Link encapsulation"

CaptureKeyPathParameter = Annotated[UUID4Type, Path(description="The UUID of the PCAP (link capture key).")]


PacketIdPathParameter = Annotated[
    int,
    Path(
        description="The numeric ID of a specific packet within the PCAP.",
        ge=1,
        le=1000000,
        examples=[4712],
    ),
]


class LinkEncap(StrEnum):
    ETHERNET = auto()
    FRELAY = auto()
    PPP = auto()
    PPP_HDLC = auto()
    PPPOE = auto()
    C_HLDC = auto()
    SLIP = auto()
    AX25 = auto()
    IEEE802_11 = auto()


class PCAPStart(BaseModel, extra="forbid"):
    maxpackets: int = Field(
        default=None,
        description="Maximum amount of packets to be captured.",
        ge=1,
        le=1000000,
        examples=[50],
    )
    maxtime: int = Field(
        default=None,
        description="Maximum time (seconds) the PCAP can run.",
        ge=1,
        le=86400,
        examples=[60],
    )
    bpfilter: str = Field(
        default=None,
        description="Berkeley packet filter.",
        min_length=1,
        max_length=128,
        examples=["src 0.0.0.0"],
    )
    encap: LinkEncap = Field(default=LinkEncap.ETHERNET, description=LINK_ENCAP_DESCRIPTION)

    @model_validator(mode="after")
    def check_at_least_one(self):
        if self.maxpackets is None and self.maxtime is None:
            raise ValueError("Either 'maxpackets' or 'maxtime' must be specified")
        return self


PCAPStartBody = Annotated[PCAPStart, Body(description="Send parameters in JSON format to start PCAP.")]


class PCAPConfigStatus(BaseModel, extra="forbid"):
    maxpackets: int = Field(
        default=None,
        description="Maximum amount of packets to be captured.",
        ge=0,
        le=1000000,
        examples=[50],
    )
    maxtime: int | None = Field(
        default=None,
        description="Maximum time (seconds) the PCAP can run.",
        ge=0,
        le=86400,
        examples=[60],
    )
    bpfilter: str | None = Field(
        default=None,
        description="Berkeley packet filter.",
        min_length=1,
        max_length=128,
        examples=["src 0.0.0.0"],
    )
    encap: LinkEncap | None = Field(default=None, description=LINK_ENCAP_DESCRIPTION)
    link_capture_key: UUID4Type | None = Field(
        ...,
        description="Key or ID for the packet capture running on the specified link.",
    )


class PCAPStatusResponse(BaseModel, extra="forbid"):
    config: PCAPConfigStatus | None = Field(
        None,
        description="The configuration of the PCAP. Empty when PCAP is not running",
    )
    starttime: datetime | None = Field(None, description="The start time of the PCAP. None when PCAP is not running")
    packetscaptured: int | None = Field(
        None,
        description="The number of packets captured. None when PCAP is not running",
        ge=0,
    )


class PCAPItem(BaseModel, extra="forbid"):
    no: str = Field(
        ...,
        description="Packet number",
        min_length=1,
        max_length=16,
        examples=["1", "2", "3"],
    )
    time: str = Field(
        ...,
        description="Time since PCAP was started",
        min_length=1,
        max_length=16,
        examples=["12.003743"],
    )
    source: MACAddress | IPAddress = Field(..., description="The MAC/IP address of the source.")
    destination: MACAddress | IPAddress = Field(..., description="The MAC/IP address of the destination.")
    length: str = Field(
        ...,
        description="The length of the packet.",
        min_length=1,
        max_length=16,
        examples=["64"],
    )
    protocol: str = Field(
        ...,
        description="Protocol of the packet.",
        min_length=1,
        max_length=16,
    )
    info: str = Field(
        ...,
        description="Information about the packet.",
        min_length=1,
        max_length=512,
    )
