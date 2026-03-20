#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#
from datetime import datetime
from enum import StrEnum, auto
from typing import Annotated, Literal

from fastapi import Body, Path
from pydantic import BaseModel, Field, model_validator

from simple_webserver.schemas.common import IPAddress, MACAddress, UUID4Type

LINK_ENCAP_DESCRIPTION = "Link encapsulation"
PCAP_MAX_PACKETS = 1_000_000
PCAP_MAX_TIME = 86_400

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
    C_HDLC = auto()
    SLIP = auto()
    AX25 = auto()
    IEEE802_11 = auto()
    RADIOTAP = auto()


class PCAPStartBase(BaseModel, extra="forbid"):
    """Shared request fields for starting a PCAP capture (wired and wireless)."""

    maxpackets: int = Field(
        default=None,
        description="Maximum amount of packets to be captured.",
        ge=1,
        le=PCAP_MAX_PACKETS,
        examples=[5000],
    )
    maxtime: int = Field(
        default=None,
        description="Maximum time (seconds) the PCAP can run.",
        ge=1,
        le=PCAP_MAX_TIME,
        examples=[60],
    )
    bpfilter: str = Field(
        default="",
        description="Berkeley packet filter.",
        max_length=128,
        examples=["src 0.0.0.0"],
    )
    encap: LinkEncap = Field(
        default=LinkEncap.ETHERNET, description=LINK_ENCAP_DESCRIPTION
    )


class PCAPStatusBase(BaseModel, extra="forbid"):
    """Shared response fields for PCAP capture status (wired and wireless)."""

    maxpackets: int | None = Field(
        default=None,
        description="Maximum amount of packets to be captured.",
        ge=0,
        le=PCAP_MAX_PACKETS,
    )
    maxtime: int | None = Field(
        default=None,
        description="Maximum time (seconds) the PCAP can run.",
        ge=0,
        le=PCAP_MAX_TIME,
    )
    bpfilter: str | None = Field(
        default=None,
        description="Berkeley packet filter.",
        max_length=128,
    )
    encap: LinkEncap | None = Field(default=None, description=LINK_ENCAP_DESCRIPTION)


class PCAPStart(PCAPStartBase, extra="forbid"):
    @model_validator(mode="after")
    def check_at_least_one(self):
        if self.maxpackets is None and self.maxtime is None:
            raise ValueError("Either 'maxpackets' or 'maxtime' must be specified")
        return self


PCAPStartBody = Annotated[
    PCAPStart,
    Body(
        description=(
            "Send parameters in JSON format to start PCAP."
            " At least one of 'maxpackets' or 'maxtime' must be specified."
        )
    ),
]


class PCAPConfigStatus(PCAPStatusBase, extra="forbid"):
    link_capture_key: UUID4Type | None = Field(
        default=None,
        description="Deprecated. ID for the packet capture, now same as link ID.",
    )


class PCAPStatusResponse(BaseModel, extra="forbid"):
    config: PCAPConfigStatus = Field(
        default_factory=PCAPConfigStatus,
        description="The configuration of the PCAP. All null when not running.",
    )
    starttime: datetime | None = Field(
        None, description="The start time of the PCAP. None when PCAP is not running"
    )
    packetscaptured: int | None = Field(
        None,
        description="The number of packets captured. None when PCAP is not running",
        ge=0,
    )


type PCAPPeer = MACAddress | IPAddress | Literal["N/A"]


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
    source: PCAPPeer = Field(..., description="The MAC/IP address of the source.")
    destination: PCAPPeer = Field(
        ..., description="The MAC/IP address of the destination."
    )
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


class PCAPFieldItem(BaseModel, extra="forbid"):
    name: str = Field(default="", description="Protocol field name")
    formatted_name: str = Field(default="", description="Formatted field details")
    pos: int | None = Field(default=None, description="Field offset in octets")
    show: str = Field(default="", description="Field summary value")
    size: int | None = Field(default=None, description="Field size in octets")
    field: list["PCAPFieldItem"] | None = Field(
        default=None, description="Nested subfield items"
    )


class PCAPProtoItem(BaseModel, extra="forbid"):
    name: str = Field(default="", description="Protocol layer name")
    formatted_name: str = Field(default="", description="Formatted protocol name")
    field: list[PCAPFieldItem] | None = Field(default=None, description="Field items")


class PCAPDetailedItem(BaseModel, extra="forbid"):
    proto: list[PCAPProtoItem] | None = Field(
        default=None, description="Decoded protocol layer details"
    )
