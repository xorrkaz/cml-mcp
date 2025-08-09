#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#

from pydantic import BaseModel, Field


class ImportLabObject(BaseModel, extra="forbid"):
    id: str = Field(..., description="The lab ID of the imported lab.")
    warnings: list[str] | None = Field(..., description="Warnings, if any, as Markdown.")


class ImportLabResponse(ImportLabObject, extra="forbid"):
    """Successful lab import.
    The response has the lab ID and potential warnings as text / Markdown."""

    pass
