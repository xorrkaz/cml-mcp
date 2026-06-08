#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#
from datetime import datetime
from enum import StrEnum, auto
from typing import Annotated, Any

from fastapi import Body
from pydantic import BaseModel, Field

from simple_common.schemas import OptInStatus, TelemetryEventCategory
from simple_webserver.schemas.common import MultiLineStr, OneLineStr


class FeedbackScope(StrEnum):
    PRODUCT = auto()
    PAGE = auto()


class FeedbackSchema(BaseModel, extra="forbid"):
    """A freeform JSON object for feedback submission."""

    # TODO: we should implement email regex
    email: OneLineStr = Field(..., description="The user's email address.")
    feedback: MultiLineStr = Field(..., description="The feedback content.")
    path: OneLineStr = Field(..., description="The path where feedback was submitted.")
    place: OneLineStr = Field(
        ..., description="The place where feedback was submitted."
    )
    scope: FeedbackScope = Field(..., description="The feedback scope.")
    score: int = Field(..., description="The feedback score.", ge=1, le=10)


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


OptInUpdateBody = Annotated[
    OptInUpdate,
    Body(
        description="The request body is a JSON object describing the desired state "
        "of the telemetry feature."
    ),
]

FeedbackBody = Annotated[
    FeedbackSchema,
    Body(
        description="The request body is a JSON object with the feedback in free form."
    ),
]


class TelemetryEventResponse(BaseModel, extra="forbid"):
    category: TelemetryEventCategory = Field(
        ..., description="Telemetry event category."
    )
    timestamp: datetime = Field(..., description="The timestamp of the event.")
    data: dict[OneLineStr, Any] = Field(..., description="The data of the event.")
