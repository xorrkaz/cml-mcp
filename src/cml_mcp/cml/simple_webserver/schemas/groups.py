#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#
from typing import Annotated

from fastapi import Body, Path
from pydantic import BaseModel, Field
from simple_webserver.schemas.common import (
    BaseDBModel,
    GenericDescription,
    GroupName,
    UUID4ArrayType,
    UUID4Type,
)
from simple_webserver.schemas.labs import GroupLab, LabGroupAssociation

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


class GroupBase(BaseModel):
    """Base class for group create/update."""

    description: GenericDescription = Field(
        default=None,
        description="Additional, textual free-form detail of the group.",
        examples=["CCNA study group"],
    )
    members: UUID4ArrayType = Field(
        default=[],
        description="Members of the group as a list of user IDs.",
    )


class GroupCreateBase(GroupBase):
    """Information needed to create a group."""

    name: GroupName = Field(...)


class GroupUpdateBase(GroupBase):
    """Information needed to update a group."""

    name: GroupName = Field(default=None)


class GroupAssocNew(BaseModel):
    associations: list[LabGroupAssociation] = Field(default=None, description="Array of lab/group associations.")


class GroupAssocOld(BaseModel):
    labs: list[GroupLab] = Field(
        default=None,
        description="Labs of the group as a object of lab IDs and permission.",
    )


class GroupCreate(GroupCreateBase, GroupAssocNew, extra="forbid"):
    pass


class GroupCreateOld(GroupCreateBase, GroupAssocOld, extra="forbid"):
    pass


class GroupUpdate(GroupUpdateBase, GroupAssocNew, extra="forbid"):
    pass


class GroupUpdateOld(GroupUpdateBase, GroupAssocOld, extra="forbid"):
    pass


GroupCreateBodyParameter = Annotated[GroupCreate | GroupCreateOld, Body(...)]

GroupUpdateBodyParameter = Annotated[GroupUpdate | GroupUpdateOld, Body(...)]


class GroupResponse(BaseDBModel, GroupCreateBase, GroupAssocNew, GroupAssocOld, extra="forbid"):
    """Information about a group."""

    # XXX: Allow this to be None for backward compatibility with existing groups.
    directory_dn: str | None = Field(
        default=None,
        description="Group distinguished name from LDAP",
        max_length=255,
        examples=["CN=Lab 1 Members,CN=groups,DC=corp,DC=com"],
    )
    directory_exists: bool | None = Field(default=None, description="Whether the group exists on LDAP")


class GroupBriefResponse(BaseModel, extra="forbid"):
    id: UUID4Type = Field(...)
    name: GroupName = Field(...)
