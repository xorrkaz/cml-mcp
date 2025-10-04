#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#
import re
from typing import Annotated

from fastapi import Body
from pydantic import BaseModel, Field

from cml_mcp.schemas.common import (
    BaseDBModel,
    GenericDescription,
    UserFullName,
    UserName,
    UUID4ArrayType,
    UUID4Type,
)
from cml_mcp.schemas.labs import LabUserAssociation

Password = Annotated[str, Field(description="The password of the user.", examples=["super-secret"])]


class PasswordChange(BaseModel, extra="forbid"):
    """
    Data required for a password change. Both are required when changing your own
    password. The old password is optional and ignored if entered when resetting a
    password of a different user.
    """

    new_password: Password = Field(...)
    old_password: Password | None = Field(default=None)


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

    username: UserName | None = Field(default=None)
    fullname: UserFullName | None = Field(default=None)
    description: GenericDescription | None = Field(
        default=None,
        description="Additional, textual free-form detail of the user.",
        examples=["Rules the network simulation world, location: unknown"],
    )
    email: str | None = Field(
        default=None,
        description="The optional e-mail address of the user.",
        examples=["johndoe@cisco.com"],
        max_length=128,
    )
    admin: bool | None = Field(
        default=None,
        description="Whether user has administrative rights or not.",
        examples=[True],
    )
    groups: UUID4ArrayType | None = Field(
        default=None,
        description="User groups. Associate the user with this list of group IDs.",
    )
    associations: list[LabUserAssociation] | None = Field(default=None, description="Array of lab/user associations.")
    resource_pool: UUID4Type | None = Field(
        default=None,
        description="Limit node launches by this user to the given resource pool.",
    )
    opt_in: bool | None = Field(
        default=None,
        description="Whether we displayed a link to the contact form to a user.",
        examples=[True],
    )
    tour_version: str | None = Field(
        default=None,
        description="""
            The newest version of the introduction tour that the user has seen.
        """,
        examples=["2.7.0"],
        max_length=128,
    )


class UserUpdate(UserBase, extra="forbid"):
    password: PasswordChange | None = Field(default=None)
    pubkey: SshPubkey | None = Field(default=None)


UserUpdateBody = Annotated[UserUpdate, Body(description="The user's data.")]


class UserCreate(UserBase, extra="forbid"):
    username: UserName = Field(...)
    password: Password = Field(..., description="The cleartext password for this user.")
    pubkey: SshPubkey | None = Field(default=None)


class UserResponse(BaseDBModel, UserBase, extra="forbid"):
    """User info"""

    directory_dn: DirectoryDn | None = Field(default=None)
    labs: UUID4ArrayType | None = Field(default=None, description="Labs owned by the user.")
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
