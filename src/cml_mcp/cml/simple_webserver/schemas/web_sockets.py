#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#

from typing import Literal

from pydantic import BaseModel, Field

from simple_webserver.schemas.common import UUID4Type

LAB_FILTER_NONE = ""


class CmlWebSocketRequest(BaseModel):
    lab_filter: UUID4Type | Literal[LAB_FILTER_NONE] | None = Field(default=None)

    @property
    def has_lab_filter(self) -> bool:
        return "lab_filter" in self.__pydantic_fields_set__
