#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from simple_common.schemas import OptInStatus, TelemetryEventCategory


class OptInBase(BaseModel):
    opt_in: OptInStatus = Field(
        ...,
        description="Telemetry opt-in state.",
        examples=[status.value for status in OptInStatus],
    )


class OptInGetResponse(OptInBase, extra="forbid"):
    show_modal: bool = Field(
        ...,
        description="Whether usage data collection modal was displayed.",
        examples=[True],
    )


class OptInUpdate(OptInBase, extra="forbid"):
    pass


class TelemetryEventResponse(BaseModel, extra="forbid"):
    category: TelemetryEventCategory = Field(
        ..., description="Telemetry event category."
    )
    timestamp: datetime = Field(..., description="The timestamp of the event.")
    data: dict[str, Any] = Field(..., description="The data of the event.")
