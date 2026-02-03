#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#
from typing import Annotated

from fastapi import Body
from pydantic import BaseModel, Field, conlist
from simple_webserver.schemas.common import (
    GenericDescription,
    Label,
    NullableGenericDescription,
    UUID4ArrayType,
    UUID4Type,
)
from simple_webserver.schemas.external_connector import ExternalConnectorDeviceName

ResourcePoolLabel = Annotated[Label, Field(..., description="A resource pool label.")]


class ResourcePoolBaseData(BaseModel):
    """Resource pool imitable data."""

    licenses: int | None = Field(
        default=None,
        ge=0,
        le=320,
        description="Number of allowed or used node licenses.",
    )
    ram: int | None = Field(
        default=None,
        ge=0,
        le=33554432,
        description="Amount of memory (MB) allowed or used.",
    )
    disk_space: int | None = Field(
        default=None,
        ge=0,
        le=32768,
        description="(Not enforced) Amount of disk space (GB) allowed or used.",
    )
    external_connectors: conlist(ExternalConnectorDeviceName, min_length=0, max_length=128) | None = Field(
        default=None,
        description="List of external connector interface names allowed or used.",
        examples=[ExternalConnectorDeviceName("bridge0")],
    )


class ResourcePoolBase(ResourcePoolBaseData):
    """Resource pool base."""

    label: ResourcePoolLabel = Field(default=None)
    description: NullableGenericDescription = Field(default=None, description="Free-form textual description of the resource pool.")
    cpus: int | None = Field(
        default=None,
        ge=0,
        le=4096,
        description="Limit the number of whole cpus allowed in the pool.",
    )


class ResourcePoolUpdate(ResourcePoolBase, extra="forbid"):
    """Resource pool updatable attributes."""

    pass


class ResourcePoolTemplateCreate(ResourcePoolBase, extra="forbid"):
    """Resource pool template create attributes."""

    label: ResourcePoolLabel = Field(...)
    users: UUID4ArrayType = Field(default=None, description="List of user IDs assigned to the created pool.")


class ResourcePoolCreate(ResourcePoolTemplateCreate, extra="forbid"):
    """Resource pool create attributes."""

    shared: bool = Field(
        default=None,
        description="If set to `false`, a list of pools will be created (pool per user)",
    )
    template: UUID4Type | None = Field(
        default=None,
        description="Parent template pool providing defaults to this pool.",
    )


class ResourcePool(ResourcePoolBase, extra="forbid"):
    """Resource pool configuration data."""

    id: UUID4Type
    template: UUID4Type | None = Field(
        default=None,
        description="Parent template pool providing defaults to this pool.",
    )


class ResourcePoolAdmin(ResourcePool, extra="forbid"):
    """Resource pool configuration data. with involved users"""

    users: UUID4ArrayType = Field(default=None, description="List of user IDs assigned to the pool.")


class ResourcePoolTemplate(ResourcePoolBase, extra="forbid"):
    """Resource pool configuration data."""

    id: UUID4Type


class ResourcePoolTemplateAdmin(ResourcePoolTemplate, extra="forbid"):
    """
    Resource pool configuration data.
    With user pools inherited from this template
    """

    user_pools: UUID4ArrayType = Field(
        default=None,
        description="List of resource pools instantiated from this template.",
    )


class ResourcePoolUsageData(ResourcePoolBaseData, extra="forbid"):
    """Resource pool usage statistics data."""

    cpus: int | None = Field(
        None,
        description="Usage in one-hundred-part shares of whole cpus.",
        ge=0,
        le=409600,
    )


class ResourcePoolUsage(BaseModel, extra="forbid"):
    """Resource pool resolved allowed and usage data."""

    id: UUID4Type
    label: ResourcePoolLabel = Field(default=None)

    description: GenericDescription | None = Field(default=None, description="Free-form textual description of the resource pool.")
    limit: ResourcePoolUsageData = Field(default=None, description="Resolved limits (from self or parent template).")
    usage: ResourcePoolUsageData = Field(
        default=None,
        description="Current total usage by nodes using the resource pool.",
    )


ResourcePoolCreateBody = Annotated[
    ResourcePoolTemplateCreate | ResourcePoolCreate,
    Body(description="A JSON object with a resource pool's initial properties."),
]

ResourcePoolUpdateBody = Annotated[
    ResourcePoolUpdate,
    Body(description="A JSON object with a resource pool's updatable properties."),
]

ResourcePoolResponse = ResourcePool | ResourcePoolAdmin

ResourcePoolTemplateResponse = ResourcePoolTemplate | ResourcePoolTemplateAdmin
