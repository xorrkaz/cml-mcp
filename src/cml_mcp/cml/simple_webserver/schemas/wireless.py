#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import Body
from pydantic import BaseModel, Field, model_validator

from simple_webserver.schemas.common import UUID4Type
from simple_webserver.schemas.pcap import PCAPStartBase, PCAPStatusBase


class WirelessPcapStart(PCAPStartBase, extra="forbid"):
    node_id: UUID4Type = Field(
        ...,
        description="Node ID used as the capture session key.",
    )

    @model_validator(mode="after")
    def check_at_least_one(self):
        if self.maxpackets is None and self.maxtime is None:
            raise ValueError("Either 'maxpackets' or 'maxtime' must be specified")
        return self


WirelessPcapStartBody = Annotated[
    WirelessPcapStart,
    Body(
        description=(
            "Send parameters in JSON format to start wireless PCAP."
            " At least one of 'maxpackets' or 'maxtime' must be specified."
        )
    ),
]


class WirelessPcapConfig(PCAPStatusBase, extra="forbid"):
    """Wireless PCAP configuration as returned in status responses."""

    node_id: UUID4Type | None = Field(
        default=None,
        description="Node ID used as the capture session key.",
    )


class WirelessPcapStatusResponse(BaseModel, extra="forbid"):
    config: WirelessPcapConfig | None = Field(
        None,
        description="The configuration of the PCAP. Empty when PCAP is not running",
    )
    starttime: datetime | None = Field(
        None, description="The start time of the PCAP. None when PCAP is not running"
    )
    packetscaptured: int | None = Field(
        None,
        description="The number of packets captured. None when PCAP is not running",
        ge=0,
    )


WirelessPcapActionResponse = Annotated[
    str,
    Field(description="Result message from the wireless PCAP operation."),
]
