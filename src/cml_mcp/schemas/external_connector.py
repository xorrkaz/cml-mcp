#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#
import re
from typing import Annotated

from fastapi import Body
from pydantic import BaseModel, Field

from cml_mcp.schemas.common import Tag, TagArray

ExternalConnectorDeviceName = Annotated[
    str,
    Field(
        pattern=re.compile(r"^(bridge|local|virbr|vlan)\d{1,4}(?![\n\r])$"),
        description="A Linux bridge name usable for external connectivity.",
    ),
]

NullableExternalConnectorDeviceName = Annotated[
    ExternalConnectorDeviceName | None,
    Field(description="A nullable Linux bridge name usable for external connectivity."),
]

ExternalConnectorTag = Annotated[
    Tag, Field(description="The key configured in external connector nodes.")
]


class ExternalConnectorMappingBase(BaseModel, extra="allow"):
    """Base for mapping of external connector lab node configs to available bridges."""

    key: ExternalConnectorTag = Field(default=None)
    device_name: NullableExternalConnectorDeviceName = Field(default=None)


class ExternalConnectorMapping(ExternalConnectorMappingBase, extra="forbid"):
    """Mapping of external connector lab node configs to available bridges."""

    key: ExternalConnectorTag = Field(...)
    device_name: NullableExternalConnectorDeviceName = Field(...)
    label: str = Field(
        default=None,
        description="Unique label for the external connector.",
        max_length=128,
    )
    tags: TagArray = Field(
        default=None, description="Tags denoting purpose of the external connector."
    )
    allowed: bool = Field(
        default=None,
        description="""
      If true, the calling user is allowed to start external connector nodes
      which are configured to use this external connector mapping.
      Users may be limited by the resource pool settings imposed on them.
    """,
    )


class ExternalConnectorMappingUpdate(ExternalConnectorMappingBase, extra="forbid"):
    """Update an external connector mapping."""

    key: ExternalConnectorTag = Field(...)
    device_name: NullableExternalConnectorDeviceName = Field(...)


ExternalConnectorMappingBody = Annotated[
    list[ExternalConnectorMappingUpdate],
    Body(description="Partial list of external connector key-device_name mappings."),
]

ExternalConnectorMappingResponse = Annotated[
    list[ExternalConnectorMapping],
    Field(description="List of external connector key-device_name mappings."),
]
