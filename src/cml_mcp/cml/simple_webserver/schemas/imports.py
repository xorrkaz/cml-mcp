#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#

from pydantic import BaseModel, Field


class ImportLabResponse(BaseModel, extra="forbid"):
    """
    Successful lab import.
    The response has the lab ID
    and potential warnings as text / Markdown.
    """

    id: str = Field(..., description="The lab ID of the imported lab.")
    warnings: list[str] | None = Field(..., description="Warnings, if any, as Markdown.")
