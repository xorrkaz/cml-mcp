#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#
from typing import Annotated

from pydantic import BaseModel, Field
from simple_webserver.schemas.common import UUID4Type


class ErrorResponse(BaseModel, extra="forbid"):
    code: int = Field(..., description="The HTTP status that was associated with this error.")
    description: str = Field(..., description="A human-readable message that describes the error.")


class FreeFormResponse(BaseModel, extra="forbid"):
    """A freeform JSON object."""

    pass


class IdResponse(BaseModel, extra="forbid"):
    """
    Successful POST / Create operation.
    The response body is a JSON object that indicates the ID of the created object.
    """

    id: UUID4Type = Field(...)


ConvergenceResponse = Annotated[
    bool,
    Field(description="The response body is a JSON object with a boolean indicating if convergence has occurred"),
]
