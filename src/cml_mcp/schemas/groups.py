#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#
from typing import Annotated

from fastapi import Body, Path
from pydantic import BaseModel, Field

from cml_mcp.schemas.common import (
    BaseDBModel,
    GenericDescription,
    GroupName,
    UUID4ArrayType,
    UUID4Type,
)
from cml_mcp.schemas.labs import GroupLab, LabGroupAssociation

GroupIdPathParameter = Annotated[UUID4Type, Path(description="The unique ID of a group on this controller.")]


GroupNamePathParameter = Annotated[
    str,
    Path(
        description="The group name of a group on this controller.",
        examples=["CCNA Study Group Class of 21"],
        min_length=1,
        max_length=64,
    ),
]


class GroupUpdateBase(BaseModel, extra="forbid"):
    """Information needed to create or update a group."""

    name: GroupName | None = Field(default=None)
    description: GenericDescription | None = Field(
        default=None,
        description="Additional, textual free-form detail of the group.",
        examples=["CCNA study group"],
    )
    members: UUID4ArrayType | None = Field(
        default=None,
        description="Members of the group as a list of user IDs.",
    )


class GroupUpdateOld(GroupUpdateBase):
    labs: list[GroupLab] | None = Field(
        default=None,
        deprecated=True,
        description="Labs of the group as a object of lab IDs and permission.",
    )


class GroupUpdate(GroupUpdateBase):
    associations: list[LabGroupAssociation] | None = Field(default=None, description="Array of lab/group associations.")


class GroupCreateOld(GroupUpdateOld):
    name: GroupName = Field(...)


class GroupCreate(GroupUpdate):
    name: GroupName = Field(...)


GroupCreateBodyParameter = Annotated[GroupCreate | GroupCreateOld, Body(...)]

GroupUpdateBodyParameter = Annotated[GroupUpdate | GroupUpdateOld, Body(...)]


class GroupInfoResponse(BaseDBModel, GroupCreate, GroupCreateOld, extra="forbid"):
    """Information about a group."""

    directory_dn: str | None = Field(
        default=None,
        description="Group distinguished name from LDAP",
        max_length=255,
        examples=["CN=Lab 1 Members,CN=groups,DC=corp,DC=com"],
    )
    directory_exists: bool | None = Field(default=None, description="Whether the group exists on LDAP")
