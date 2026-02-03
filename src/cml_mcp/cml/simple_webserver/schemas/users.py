#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#
import re
from typing import Annotated

from fastapi import Body
from pydantic import BaseModel, Field
from simple_common.schemas import OptInStatus
from simple_webserver.schemas.common import (
    BaseDBModel,
    GenericDescription,
    Password,
    UserFullName,
    UserName,
    UUID4ArrayType,
    UUID4Type,
)
from simple_webserver.schemas.labs import LabUserAssociation

NewPassword = Annotated[Password, Field(..., description="The new password for the user.")]


class PasswordChange(BaseModel, extra="forbid"):
    """
    Data required for a password change. Both are required when changing your own
    password. The old password is optional and ignored if entered when resetting a
    password of a different user.
    """

    new_password: NewPassword = Field(...)
    old_password: Password = Field(default=None)


SshPubkey = Annotated[
    str,
    Field(
        description="""
            The content of an OpenSSH public/authorized key, settable only if console
            server authentication is enabled by global configuration. Clear with empty
            string.
        """,
        pattern=re.compile(r"^([a-zA-Z\d-]{1,30} [a-zA-Z\d+/]{1,4096}={0,2}(?: [a-zA-Z\d@.+_-]{0,64})?" r"(?![\n\r]))?$"),
        examples=["ssh-ecdsa-sha2-nistp256 AAAAE...tCyk44= user@cml"],
    ),
]


DirectoryDn = Annotated[
    str,
    Field(
        description="User distinguished name from LDAP",
        examples=["CN=John Doe,CN=users,DC=corp,DC=com"],
        max_length=255,
    ),
]


class UserBase(BaseModel):
    """This object holds information about a user."""

    username: UserName = Field(default=None)
    fullname: UserFullName = Field(default=None)
    description: GenericDescription = Field(
        default=None,
        description="Additional, textual free-form detail of the user.",
        examples=["Rules the network simulation world, location: unknown"],
    )
    # XXX: Allow email to be None for backward compatibility with existing users.
    email: str | None = Field(
        default=None,
        description="The optional e-mail address of the user.",
        examples=["johndoe@cisco.com"],
        max_length=128,
    )
    admin: bool = Field(
        default=None,
        description="Whether user has administrative rights or not.",
        examples=[True],
    )
    groups: UUID4ArrayType = Field(
        default=None,
        description="User groups. Associate the user with this list of group IDs.",
    )
    associations: list[LabUserAssociation] = Field(default=None, description="Array of lab/user associations.")
    resource_pool: UUID4Type | None = Field(
        default=None,
        description="Limit node launches by this user to the given resource pool.",
    )
    # XXX: Allow bool and None types for backward compatibility with CML 2.9.
    # XXX: Also set default to False for 2.9 compatibility.
    opt_in: OptInStatus | bool | None = Field(
        default=False,
        description="Telemetry opt-in state for user.",
        examples=[status.value for status in OptInStatus],
    )
    tour_version: str = Field(
        default=None,
        description="""
            The newest version of the introduction tour that the user has seen.
        """,
        examples=["2.7.0"],
        max_length=128,
    )


class UserUpdate(UserBase, extra="forbid"):
    password: PasswordChange = Field(default=None)
    pubkey: SshPubkey = Field(default=None)


UserUpdateBody = Annotated[UserUpdate, Body(description="The user's data.")]


class UserCreate(UserBase, extra="forbid"):
    username: UserName = Field(...)
    password: NewPassword = Field(...)
    pubkey: SshPubkey = Field(default=None)


class UserResponse(BaseDBModel, UserBase, extra="forbid"):
    """User info"""

    # XXX: Allow this to be None for backward compatibility with existing users.
    directory_dn: DirectoryDn | None = Field(default=None)
    labs: UUID4ArrayType = Field(default=None, description="Labs owned by the user.")
    pubkey_info: str | None = Field(
        default=None,
        description="""
            The size, SHA256 fingerprint, description and algorithm of a SSH public key
            that can be used with the terminal server, or null if this is disabled.
            example: "256 SHA256:dt3shBgmasotkuBr8F6RQO2HwDOdlOQvFujVyq96O9o user@cml
            (ECDSA)
        """,
        examples=[""],
        max_length=512,
    )


class UserBriefResponse(BaseModel, extra="forbid"):
    id: UUID4Type = Field(...)
    username: UserName = Field(...)
