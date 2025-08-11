#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#
import re
from typing import Annotated, Literal

from fastapi import Body
from pydantic import BaseModel, Field, model_validator

from cml_mcp.schemas.common import (
    DOMAIN_REG,
    PORT_REG,
    GroupName,
    UserName,
    UUID4Type,
)

from .users import Password


class UserAuthData(BaseModel):
    """Name and password of the user to be tested."""

    username: UserName = Field(...)
    password: Password = Field(...)


AuthDataBody = Annotated[
    UserAuthData,
    Body(
        description="This request body is a JSON object that holds authentication data."
    ),
]


CNArray = Annotated[
    list[str],
    Field(description="An array of LDAP CNs.", examples=["group-1", "group-2"]),
]


PublicCertificate = Annotated[
    str,
    Field(
        description="Contents of the public certificate in PEM format.",
        examples=[
            """
                -----BEGIN CERTIFICATE-----
                MIIDGzCCAgOgAwIBAgIBATANBgkq
                gno5gnopebgtAOFFHUnrr35n52/4
                //shortened
                xlJQaTOM9rpsuO/Q==
                -----END CERTIFICATE-----
                """
        ],
    ),
]

JwtToken = Annotated[
    str,
    Field(
        description="JWT token",
        pattern="^[A-Za-z0-9-_]+.[A-Za-z0-9-_]+.[A-Za-z0-9-_]+$",
        examples=[
            (
                "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJjb20uY2lzY28udmlybCIsI"
                "mlhdCI6MTYxMzc1MDgxNSwiZXhwIjoxNjEzODM3MjE1LCJzdWIiOiIwNDg5MDcxNS00YWE"
                "3LTRhNDAtYWQzZS1jZThmY2JkNGQ3YWEifQ.Q4heV5TTYQ6yhpJ5GKLm_Bf9D9NL-wDxL9"
                "Orz1ByxWs"
            )
        ],
    ),
]


class GroupAuthData(BaseModel):
    """Name of the group to be tested."""

    group_name: GroupName = Field(...)


class SystemAuthConfigBase(BaseModel, extra="allow"):
    """System Authentication Configuration Object."""

    method: Literal["ldap", "local"] = Field(..., description="What authentication method should be used.")
    server_urls: str = Field(
        default=None,
        max_length=256,
        description="URI of LDAP server, either LDAP or LDAPS,"
        "multiple servers can be specified, separate with space.",
        examples=["ldaps://ad.corp.com:3269"],
        pattern=re.compile(
            rf"^(?:(?: (?=l))?ldaps?://(?:{DOMAIN_REG})(?::{PORT_REG})?)*(?![\n\r])$"
        ),
    )
    verify_tls: bool = Field(
        default=None,
        description="Set to `false` if certificates should not be verified.",
    )
    cert_data_pem: PublicCertificate = Field(
        default=None, description="Reference to a public certificate."
    )
    use_ntlm: bool = Field(
        default=None,
        description="If `true` then password for manager user"
        " will be stored as NTLM hash. "
        "Only works with ActiveDirectory servers.",
    )
    root_dn: str = Field(
        default=None,
        max_length=256,
        description="The root DN that will be applied.",
        examples=["DC=corp,DC=com"],
    )
    user_search_base: str = Field(
        default=None,
        max_length=256,
        description="The user search base where users should be looked up. "
        "Typically a OU or CN. Will be combined with the root DN.",
        examples=["CN=users,CN=accounts"],
    )
    user_search_filter: str = Field(
        default=None,
        max_length=1024,
        description="The filter that will be applied to the user. "
        "Must have a placeholder `{0}` replaced with the username.",
        examples=[
            "(&(uid={0})(memberOf=CN=cmlusers,CN=groups,CN=accounts,DC=corp,DC=com))"
        ],
    )
    admin_search_filter: str = Field(
        default=None,
        max_length=1024,
        description="Same as for the user search filter. "
        "Grants admin rights if matched.",
        examples=[
            "(&(uid={0})(memberOf=CN=cmladmins,CN=groups,CN=accounts,DC=corp,DC=com))"
        ],
    )
    group_search_base: str = Field(
        default=None,
        max_length=256,
        description="The group search base where groups should be looked up. "
        "Typically a OU or CN. Will be combined with the root DN.",
        examples=["CN=groups,CN=accounts"],
    )
    group_search_filter: str = Field(
        default=None,
        max_length=1024,
        description="The filter applied to groups. "
        "Must have a placeholder `{0}` replaced with the group name.",
        examples=["(&(cn={0})(objectclass=posixgroup))"],
    )
    group_via_user: bool = Field(
        default=None,
        description="If `true`, use `group_user_attribute` "
        "to determine user group memberships.",
    )
    group_user_attribute: str = Field(
        default=None,
        max_length=64,
        description="Attribute of the user that holds group memberships.",
        examples=["memberOf"],
    )
    group_membership_filter: str = Field(
        default=None,
        max_length=1024,
        description="Filter to apply to groups specifying the user.",
        examples=["(member={0})"],
    )
    manager_dn: str = Field(
        default=None,
        max_length=256,
        description="Manager user DN for lookup if anonymous search is not allowed.",
        examples=["uid=someuser,cn=users,cn=accounts,dc=corp,dc=com"],
    )
    display_attribute: str = Field(
        default=None,
        max_length=256,
        description="User attribute for displaying the logged in user.",
        examples=["displayName"],
    )
    group_display_attribute: str = Field(
        default=None,
        max_length=256,
        description="Group attribute for displaying group description.",
        examples=["description"],
    )
    email_address_attribute: str = Field(
        default=None,
        max_length=64,
        description="User attribute for displaying the email address.",
        examples=["mail"],
    )
    resource_pool: UUID4Type | None = Field(
        default=None, description="Resource pool or template ID for new user accounts."
    )


class SystemAuthConfigRequest(SystemAuthConfigBase, extra="forbid"):
    manager_password: str = Field(
        default=None,
        max_length=256,
        description="""
          The password for the management user. If `use_ntlm` is `true` then the
          password will be converted to a NTLM hash and the hash is stored.
          Otherwise, the cleartext password will be stored using obfuscation.
          """,
    )


class SystemAuthConfigResponse(SystemAuthConfigBase, extra="forbid"):
    pass


class SystemAuthTestData(BaseModel, extra="forbid"):
    """
    Test Configuration Data which includes the system authentication
    configuration, and either a username and a password, or a group name.
    """

    auth_config: SystemAuthConfigRequest = Field(..., alias="auth-config")
    auth_data: UserAuthData = Field(default=None, alias="auth-data")
    group_data: GroupAuthData = Field(default=None, alias="group-data")

    @model_validator(mode="after")
    def check_any_of(self):
        if self.auth_data is None and self.group_data is None:
            raise ValueError("Either auth_data or group_data must be provided.")
        return self


class AuthTestAttributes(BaseModel, extra="allow"):
    pass


class AuthTestUserResponse(BaseModel):
    auth_ok: bool = Field(
        default=None,
        description="The user has access to the system and the user filter matches.",
    )
    is_admin: bool = Field(
        default=None,
        description="The user has admin rights. If LDAP is configured, "
        "then the admin filter must match.",
    )
    display: str = Field(
        default=None,
        description="The user's display name, if the configured attribute was found.",
    )
    email: str = Field(
        default=None,
        description="The user's email address, if the configured attribute was found.",
    )
    attributes: AuthTestAttributes = Field(
        default=None,
        description=(
            "If the user auth'ed OK, then this object holds the dictionary of user attributes, "
            "independent of having CML access or admin access or other privileges. "
            "If an error occurred (config/server problem), then the error message will be included "
            "in the attributes."
        ),
    )


class AuthTestGroupResponse(BaseModel):
    group_ok: bool = Field(
        default=None,
        description="The group exists on the server and the group filter matches.",
    )
    is_member: bool = Field(
        default=None,
        description=(
            "Whether the given user is a member of the given group. Will default to false "
            "if either the user or the group could not be found on the LDAP server."
        ),
    )
    display: str = Field(
        default=None,
        description="The group's display name, if the configured attribute was found.",
    )
    attributes: AuthTestAttributes = Field(
        default=None,
        description=(
            "If the group was found OK, then this object holds the dictionary of group attributes, "
            "independent of having CML access or admin access or other privileges. "
            "If an error occurred (config/server problem), then the error message will be included "
            "in the attributes."
        ),
    )


class AuthTestResponse(BaseModel, extra="forbid"):
    """System Authentication Test response."""

    user: AuthTestUserResponse = Field(
        default=None, description="Results for the user."
    )
    group: AuthTestGroupResponse = Field(
        default=None, description="Results for the group."
    )


class AuthenticateResponse(BaseModel):
    """Authenticate response."""

    username: str = Field(default=None, examples=["admin"])
    id: UUID4Type = Field(default=None, description="ID of a user")
    token: JwtToken = Field(default=None)
    admin: bool = Field(default=None, examples=[False])
    error: str | None = Field(
        default=None,
        description="Error messages for errors that occurred while authenticating, "
        "but did not interrupt the login, such as LDAP group membership "
        "refresh errors.",
        examples=[
            "Could not refresh LDAP group memberships "
            "(Invalid base DN or root DN format)"
        ],
    )
