#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#
import re
from typing import Annotated, Literal

from fastapi import Body
from pydantic import BaseModel, Field, model_serializer, model_validator

from simple_webserver.schemas.common import (
    DOMAIN_REG,
    PORT_REG,
    GroupName,
    MultiLineStr,
    OneLineStr,
    Password,
    Timeout,
    UserName,
    UUID4Type,
)

RESOURCE_POOL_DESCRIPTION = "Resource pool or template ID for new user accounts."
LDAP_SERVER_URLS_PATTERN = rf"^(?:ldaps?://(?:{DOMAIN_REG})(?::{PORT_REG})?)(?: ldaps?://(?:{DOMAIN_REG})(?::{PORT_REG})?)*$"


class UserAuthData(BaseModel, extra="forbid"):
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
    list[OneLineStr],
    Field(description="An array of LDAP CNs.", examples=["group-1", "group-2"]),
]

# length validation moved to backend so it does not return entered certificate
# in response on unsuccessful validation
PublicCertificate = Annotated[
    MultiLineStr,
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
    OneLineStr,
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


class GroupAuthData(BaseModel, extra="forbid"):
    """Name of the group to be tested."""

    group_name: GroupName = Field(...)


# --- MODULAR AUTH CONFIG SECTION ---
class LocalAuthConfig(BaseModel, extra="forbid"):
    method: Literal["local"]


class LDAPAuthConfigResponse(BaseModel, extra="forbid"):
    method: Literal["ldap"]
    manager_password: OneLineStr | None = Field(
        default=None,
        max_length=256,
        description="""
          The password for the management user. If `use_ntlm` is `true` then the
          password will be converted to a NTLM hash and the hash is stored.
          Otherwise, the cleartext password will be stored using obfuscation.
        """,
    )
    server_urls: OneLineStr | None = Field(
        default=None,
        max_length=256,
        description="URI of LDAP server, either LDAP or LDAPS, multiple servers can be specified, separate with space.",
        examples=["ldaps://ad.corp.com:3269"],
        pattern=LDAP_SERVER_URLS_PATTERN,
    )
    verify_tls: bool | None = Field(
        default=None,
        description="Set to `false` if certificates should not be verified.",
    )
    cert_data_pem: PublicCertificate | None = Field(
        default=None, description="Reference to a public certificate."
    )
    use_ntlm: bool | None = Field(
        default=None,
        description="If `true` then password for manager user will be stored as NTLM hash. Only works with ActiveDirectory servers.",
    )
    root_dn: OneLineStr | None = Field(
        default=None,
        max_length=256,
        description="The root DN that will be applied.",
        examples=["DC=corp,DC=com"],
    )
    user_search_base: OneLineStr | None = Field(
        default=None,
        max_length=256,
        description="The user search base where users should be looked up. Typically a OU or CN. Will be combined with the root DN.",
        examples=["CN=users,CN=accounts"],
    )
    user_search_filter: OneLineStr | None = Field(
        default=None,
        max_length=1024,
        description="The filter that will be applied to the user. Must have a placeholder `{0}` replaced with the username.",
        examples=[
            "(&(uid={0})(memberOf=CN=cmlusers,CN=groups,CN=accounts,DC=corp,DC=com))"
        ],
    )
    admin_search_filter: OneLineStr | None = Field(
        default=None,
        max_length=1024,
        description="Same as for the user search filter. Grants admin rights if matched.",
        examples=[
            "(&(uid={0})(memberOf=CN=cmladmins,CN=groups,CN=accounts,DC=corp,DC=com))"
        ],
    )
    group_search_base: OneLineStr | None = Field(
        default=None,
        max_length=256,
        description="The group search base where groups should be looked up. Typically a OU or CN. Will be combined with the root DN.",
        examples=["CN=groups,CN=accounts"],
    )
    group_search_filter: OneLineStr | None = Field(
        default=None,
        max_length=1024,
        description="The filter applied to groups. Must have a placeholder `{0}` replaced with the group name.",
        examples=["(&(cn={0})(objectclass=posixgroup))"],
    )
    group_via_user: bool | None = Field(
        default=None,
        description="If `true`, use `group_user_attribute` to determine user group memberships.",
    )
    group_user_attribute: OneLineStr | None = Field(
        default=None,
        max_length=64,
        description="Attribute of the user that holds group memberships.",
        examples=["memberOf"],
    )
    group_membership_filter: OneLineStr | None = Field(
        default=None,
        max_length=1024,
        description="Filter to apply to groups specifying the user.",
        examples=["(member={0})"],
    )
    manager_dn: OneLineStr | None = Field(
        default=None,
        max_length=256,
        description="Manager user DN for lookup if anonymous search is not allowed.",
        examples=["uid=someuser,cn=users,cn=accounts,dc=corp,dc=com"],
    )
    timeout: Timeout
    display_attribute: OneLineStr | None = Field(
        default=None,
        max_length=256,
        description="User attribute for displaying the logged in user.",
        examples=["displayName"],
    )
    group_display_attribute: OneLineStr | None = Field(
        default=None,
        max_length=256,
        description="Group attribute for displaying group description.",
        examples=["description"],
    )
    email_address_attribute: OneLineStr | None = Field(
        default=None,
        max_length=64,
        description="User attribute for displaying the email address.",
        examples=["mail"],
    )
    resource_pool: UUID4Type | None = Field(
        default=None, description=RESOURCE_POOL_DESCRIPTION
    )


# makes server_urls required for request model.
class LDAPAuthConfigRequest(LDAPAuthConfigResponse, extra="forbid"):
    server_urls: OneLineStr = Field(
        ...,
        max_length=256,
        description="URI of LDAP server, either LDAP or LDAPS, multiple servers can be specified, separate with space.",
        examples=["ldaps://ad.corp.com:3269"],
        pattern=LDAP_SERVER_URLS_PATTERN,
    )


class RadiusAuthConfigBase(BaseModel, extra="forbid"):
    method: Literal["radius"]
    port: int = Field(
        default=1812,
        ge=1,
        le=65535,
        description="Default RADIUS server port (used when entry has no ':port').",
    )
    timeout: Timeout
    nas_identifier: OneLineStr | None = Field(
        default=None,
        max_length=256,
        description="NAS-Identifier to include in requests (optional).",
    )
    resource_pool: UUID4Type | None = Field(
        default=None,
        description=RESOURCE_POOL_DESCRIPTION,
    )
    groups_key: OneLineStr | None = Field(
        default=None,
        max_length=256,
        description="RADIUS attribute key used to read group memberships.",
    )
    permitted_key: OneLineStr | None = Field(
        default=None,
        max_length=256,
        description="Optional RADIUS attribute key required for access.",
    )
    permitted_value: OneLineStr | None = Field(
        default=None,
        max_length=1024,
        description="Optional regex/value expected for permitted_key.",
    )
    admin_key: OneLineStr | None = Field(
        default=None,
        max_length=256,
        description="RADIUS attribute key used to determine admin role.",
    )
    admin_value: OneLineStr | None = Field(
        default=None,
        max_length=1024,
        description="Regex/value expected for admin_key to grant admin role.",
    )

    @classmethod
    def _validate_server_hosts_nullable(
        cls, server_hosts: str | None, allow_empty: bool
    ) -> None:
        raw = (server_hosts or "").strip()
        if not raw:
            if allow_empty:
                return
            raise ValueError("server_hosts must contain at least one host")
        for entry in raw.split():
            host, port_str = cls._split_host_port(entry)
            cls._validate_host_value(host)
            if port_str is not None:
                cls._validate_port_value(port_str)

    @staticmethod
    def _split_host_port(entry: str) -> tuple[str, str | None]:
        if ":" in entry:
            host, p = entry.rsplit(":", 1)
            return host, p
        return entry, None

    @staticmethod
    def _validate_host_value(host: str) -> None:
        if not re.match(rf"^{DOMAIN_REG}$", host):
            raise ValueError(f"Invalid host in server_hosts: {host}")

    @staticmethod
    def _validate_port_value(port_str: str) -> None:
        try:
            pi = int(port_str)
        except Exception:
            raise ValueError(f"Invalid port in server_hosts: {port_str}")
        if not (1 <= pi <= 65535):
            raise ValueError(f"Port out of range in server_hosts: {port_str}")


class RadiusAuthConfigRequest(RadiusAuthConfigBase):
    server_hosts: OneLineStr = Field(
        ...,
        max_length=1024,
        description=(
            "Space-separated list of RADIUS servers. Each entry may be 'host' or 'host:port'. "
            "Entries without ':port' use the global 'port' value."
        ),
    )
    secret: OneLineStr = Field(
        ..., max_length=256, description="Shared secret for the RADIUS server(s)."
    )

    @model_validator(mode="after")
    def validate_server_hosts(self):
        self.__class__._validate_server_hosts_nullable(
            self.server_hosts, allow_empty=False
        )
        return self


class RadiusAuthConfigResponse(RadiusAuthConfigBase):
    server_hosts: OneLineStr | None = Field(
        default=None,
        max_length=1024,
        description=(
            "Space-separated list of RADIUS servers. Each entry may be 'host' or 'host:port'. "
            "Entries without ':port' use the global 'port' value."
        ),
    )
    secret: OneLineStr | None = Field(
        default=None,
        max_length=256,
        description="Shared secret for the RADIUS server(s).",
    )

    @model_validator(mode="after")
    def validate_server_hosts(self):
        self.__class__._validate_server_hosts_nullable(
            self.server_hosts, allow_empty=True
        )
        return self


class OIDCAuthConfig(BaseModel, extra="forbid"):
    method: Literal["oidc"]
    issuer_url: OneLineStr | None = Field(default=None, max_length=512)
    client_id: OneLineStr | None = Field(default=None, max_length=256)
    client_secret: OneLineStr | None = Field(default=None, max_length=1024)
    timeout: Timeout = Field(default=10, description="HTTP timeout in seconds.")
    authorization_endpoint: OneLineStr | None = Field(default=None, max_length=512)
    token_endpoint: OneLineStr | None = Field(default=None, max_length=512)
    userinfo_endpoint: OneLineStr | None = Field(default=None, max_length=512)
    jwks_uri: OneLineStr | None = Field(default=None, max_length=512)
    redirect_uri_override: OneLineStr | None = Field(default=None, max_length=512)
    scopes: OneLineStr | None = Field(default=None, max_length=256)
    username_claim: OneLineStr | None = Field(default=None, max_length=128)
    admin_claim: OneLineStr | None = Field(default=None, max_length=128)
    admin_value: OneLineStr | None = Field(default=None, max_length=256)
    groups_claim: OneLineStr | None = Field(default=None, max_length=128)
    permitted_claim: OneLineStr | None = Field(default=None, max_length=128)
    permitted_value: OneLineStr | None = Field(default=None, max_length=256)
    resource_pool: UUID4Type | None = Field(
        default=None, description=RESOURCE_POOL_DESCRIPTION
    )


class OAuth2AuthConfig(BaseModel, extra="forbid"):
    method: Literal["oauth2"]
    provider: OneLineStr | None = Field(default=None, max_length=64)
    timeout: Timeout = Field(default=30, description="HTTP timeout in seconds.")
    authorization_endpoint: OneLineStr | None = Field(default=None, max_length=512)
    token_endpoint: OneLineStr | None = Field(default=None, max_length=512)
    client_id: OneLineStr | None = Field(default=None, max_length=256)
    client_secret: OneLineStr | None = Field(default=None, max_length=1024)
    scopes: OneLineStr | None = Field(default=None, max_length=256)
    user_info_endpoint: OneLineStr | None = Field(default=None, max_length=512)
    groups_endpoint: OneLineStr | None = Field(default=None, max_length=512)
    username_field: OneLineStr | None = Field(default=None, max_length=128)
    email_field: OneLineStr | None = Field(default=None, max_length=128)
    groups_field: OneLineStr | None = Field(default=None, max_length=128)
    admin_group: OneLineStr | None = Field(default=None, max_length=256)
    permitted_claim: OneLineStr | None = Field(default=None, max_length=128)
    permitted_value: OneLineStr | None = Field(default=None, max_length=256)
    resource_pool: UUID4Type | None = Field(
        default=None, description=RESOURCE_POOL_DESCRIPTION
    )
    redirect_uri_override: OneLineStr | None = Field(default=None, max_length=512)


class SAMLAuthConfig(BaseModel, extra="forbid"):
    method: Literal["saml"]
    sp_entity_id: OneLineStr | None = Field(default=None, max_length=512)
    sp_acs_url: OneLineStr | None = Field(default=None, max_length=512)
    sp_sls_url: OneLineStr | None = Field(default=None, max_length=512)
    sp_cert: MultiLineStr | None = Field(default=None)
    sp_private_key: MultiLineStr | None = Field(default=None)
    idp_entity_id: OneLineStr | None = Field(default=None, max_length=512)
    idp_sso_url: OneLineStr | None = Field(default=None, max_length=512)
    idp_slo_url: OneLineStr | None = Field(default=None, max_length=512)
    idp_cert: MultiLineStr | None = Field(default=None)
    username_attribute: OneLineStr | None = Field(default=None, max_length=128)
    email_attribute: OneLineStr | None = Field(default=None, max_length=128)
    groups_attribute: OneLineStr | None = Field(default=None, max_length=128)
    admin_group: OneLineStr | None = Field(default=None, max_length=256)
    permitted_attribute: OneLineStr | None = Field(default=None, max_length=128)
    permitted_value: OneLineStr | None = Field(default=None, max_length=256)
    want_assertions_signed: bool | None = Field(default=None)
    want_messages_signed: bool | None = Field(default=None)
    resource_pool: UUID4Type | None = Field(
        default=None, description=RESOURCE_POOL_DESCRIPTION
    )


class SAMLDiscoverResponse(BaseModel, extra="forbid"):
    success: bool
    metadata: MultiLineStr | None = None
    idp_entity_id: OneLineStr | None = Field(default=None, max_length=512)
    idp_sso_url: OneLineStr | None = Field(default=None, max_length=512)
    error: MultiLineStr | None = None


class OAuthAuthorizationUrlResponse(BaseModel, extra="forbid"):
    authorization_url: OneLineStr
    state: OneLineStr


class SamlLoginUrlResponse(BaseModel, extra="forbid"):
    authorization_url: OneLineStr
    relay_state: OneLineStr


class OIDCDiscoverResponse(BaseModel, extra="forbid"):
    success: bool
    issuer: OneLineStr | None = Field(default=None, max_length=512)
    authorization_endpoint: OneLineStr | None = Field(default=None, max_length=512)
    token_endpoint: OneLineStr | None = Field(default=None, max_length=512)
    userinfo_endpoint: OneLineStr | None = Field(default=None, max_length=512)
    jwks_uri: OneLineStr | None = Field(default=None, max_length=512)
    claims_supported: list[OneLineStr] | None = None
    scopes_supported: list[OneLineStr] | None = None
    claim_warnings: list[OneLineStr] | None = None
    error: MultiLineStr | None = None


class OAuth2TestResponse(BaseModel, extra="forbid"):
    success: bool
    provider: OneLineStr | None = Field(default=None, max_length=64)
    authorization_endpoint: OneLineStr | None = Field(default=None, max_length=512)
    token_endpoint: OneLineStr | None = Field(default=None, max_length=512)
    user_info_endpoint: OneLineStr | None = Field(default=None, max_length=512)
    groups_endpoint: OneLineStr | None = Field(default=None, max_length=512)
    error: MultiLineStr | None = None


# Flat discriminated unions used by API
SystemAuthConfigRequest = Annotated[
    LocalAuthConfig
    | LDAPAuthConfigRequest
    | RadiusAuthConfigRequest
    | OIDCAuthConfig
    | OAuth2AuthConfig
    | SAMLAuthConfig,
    Field(discriminator="method"),
]
SystemAuthConfigResponse = Annotated[
    LocalAuthConfig
    | LDAPAuthConfigResponse
    | RadiusAuthConfigResponse
    | OIDCAuthConfig
    | OAuth2AuthConfig
    | SAMLAuthConfig,
    Field(discriminator="method"),
]


# Compatibility wrapper for tests that instantiate SystemAuthConfigBase directly
class SystemAuthConfigBase(BaseModel):
    config: (
        LDAPAuthConfigRequest
        | RadiusAuthConfigRequest
        | OIDCAuthConfig
        | OAuth2AuthConfig
        | SAMLAuthConfig
    )

    @model_validator(mode="before")
    @classmethod
    def _wrap_union(cls, v):
        # Allow constructing with top-level union fields
        if isinstance(v, dict) and "config" not in v and v.get("method") is not None:
            return {"config": v}
        return v

    @model_serializer(mode="wrap")
    def _ser(self, handler):
        # Flatten wrapper to inner union on serialization
        return handler(self.config)

    def __getattr__(self, item):
        # Delegate attribute access to inner model for compatibility
        return getattr(self.config, item)


class SystemAuthTestData(BaseModel, extra="forbid"):
    """
    Test Configuration Data which includes the system authentication
    configuration, and either a username and a password, or a group name.
    """

    auth_config: SystemAuthConfigBase
    auth_data: UserAuthData | None = None
    group_data: GroupAuthData | None = None

    @model_validator(mode="before")
    @classmethod
    def _map_aliases(cls, v):
        """
        normalize hyphenated input keys to field names.

        pydantic v2 emits warnings when using Field(alias=...) on union-typed
        fields. clients/tests send 'auth-config', 'auth-data', and
        'group-data'; we rewrite them to 'auth_config', 'auth_data', and
        'group_data' before validation to preserve input compatibility without
        triggering alias warnings.

        and then I wonder why we created hyphenated keys to begin with...
        But... need to maintain backwards-compatibility!
        """
        if isinstance(v, dict):
            if "auth-config" in v and "auth_config" not in v:
                v["auth_config"] = v.pop("auth-config")
            if "auth-data" in v and "auth_data" not in v:
                v["auth_data"] = v.pop("auth-data")
            if "group-data" in v and "group_data" not in v:
                v["group_data"] = v.pop("group-data")
        return v

    @model_validator(mode="after")
    def check_any_of(self):
        if self.auth_data is None and self.group_data is None:
            raise ValueError("Either auth_data or group_data must be provided.")
        return self


AuthTestAttributes = dict[str, MultiLineStr | list[MultiLineStr]]


class AuthTestUserResponse(BaseModel, extra="forbid"):
    auth_ok: bool | None = Field(
        default=None,
        description="The user has access to the system and the user filter matches.",
    )
    is_admin: bool = Field(
        default=False,
        description="The user has admin rights. If LDAP is configured, then the admin filter must match.",
    )
    display: OneLineStr = Field(
        default="",
        description="The user's display name, if the configured attribute was found.",
    )
    email: OneLineStr = Field(
        default="",
        description="The user's email address, if the configured attribute was found.",
    )
    attributes: AuthTestAttributes = Field(
        default_factory=dict,
        description=(
            "If the user auth'ed OK, then this object holds the dictionary of user attributes, "
            "independent of having CML access or admin access or other privileges. "
            "If an error occurred (config/server problem), then the error message will be included "
            "in the attributes."
        ),
    )


class AuthTestGroupResponse(BaseModel, extra="forbid"):
    group_ok: bool | None = Field(
        default=None,
        description="The group exists on the server and the group filter matches.",
    )
    is_member: bool = Field(
        default=False,
        description=(
            "Whether the given user is a member of the given group. Will default to false "
            "if either the user or the group could not be found on the LDAP server."
        ),
    )
    display: OneLineStr = Field(
        default="",
        description="The group's display name, if the configured attribute was found.",
    )
    attributes: AuthTestAttributes = Field(
        default_factory=dict,
        description=(
            "If the group was found OK, then this object holds the dictionary of group attributes, "
            "independent of having CML access or admin access or other privileges. "
            "If an error occurred (config/server problem), then the error message will be included "
            "in the attributes."
        ),
    )


class AuthTestResponse(BaseModel, extra="forbid"):
    """System Authentication Test response."""

    user: AuthTestUserResponse = Field(..., description="Results for the user.")
    group: AuthTestGroupResponse = Field(..., description="Results for the group.")


class AuthenticateResponse(BaseModel, extra="forbid"):
    """Authenticate response."""

    username: OneLineStr | None = Field(default=None, examples=["admin"])
    id: UUID4Type | None = Field(default=None, description="ID of a user")
    token: JwtToken | None = Field(default=None)
    admin: bool | None = Field(default=None, examples=[False])
    error: MultiLineStr | None = Field(
        default=None,
        description="Error messages for errors that occurred while authenticating, "
        "but did not interrupt the login, such as LDAP group membership "
        "refresh errors. May span multiple lines when the underlying "
        "exception (e.g. LDAPExceptionError) carries a multi-line "
        "diagnostic message.",
        examples=[
            "Could not refresh LDAP group memberships "
            "(Invalid base DN or root DN format)"
        ],
    )
