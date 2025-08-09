#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#
from typing import Annotated

from pydantic import BaseModel, Field

from cml_mcp.schemas.common import UUID4Type


class Error(BaseModel):
    code: int = Field(..., description="The HTTP status that was associated with this error.")
    description: str = Field(..., description="A human-readable message that describes the error.")


class ErrorResponse(Error):
    pass


class FreeFormResponse(BaseModel, extra="allow"):
    """A freeform JSON object."""

    pass


class IdObject(BaseModel):
    id: UUID4Type = Field(...)


class IdResponse(IdObject, extra="forbid"):
    """Successful POST / Create operation.
    The response body is a JSON object that indicates the ID of the created object."""

    pass


ConvergenceResponse = Annotated[
    bool,
    Field(description="The response body is a JSON object with a boolean indicating if convergence has occurred"),
]
