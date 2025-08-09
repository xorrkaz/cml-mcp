#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#
from pydantic import BaseModel, Field

from cml_mcp.schemas.common import UUID4Type


class CmlWebSocketRequest(BaseModel):
    lab_filter: UUID4Type | str | None = Field(default=None)

    @property
    def has_lab_filter(self) -> bool:
        return "lab_filter" in self.__pydantic_fields_set__
