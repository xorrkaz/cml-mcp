#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#
import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, field_serializer

from cml_mcp.schemas.simple_common.models import DefaultPermissions

LINT_REG = r"[\da-z-]{1,15}"
UUID4_REG = (
    r"^[\da-f]{8}-[\da-f]{4}-4[\da-f]{3}-[89ab][\da-f]{3}-[\da-f]{12}(?![\n\r])$"
)

IPV4_REG = r"(\d{1,3}.){3}\d{1,3}"
IPV6_REG = r"[\da-fA-F:]{3,39}" + f"(%{LINT_REG})?"
IP_REG = rf"^({IPV4_REG}|{IPV6_REG})(?![\n\r])$"
HOSTNAME_REG = r"[a-zA-Z\d.-]{1,64}"
PORT_REG = r"\d{1,5}"
HOST_REG = rf"^{HOSTNAME_REG}(?![\n\r])$"
DOMAIN_REG = rf"{IPV4_REG}|\[{IPV6_REG}\]|{HOSTNAME_REG}"
ORIGIN_REG = rf"https?://({DOMAIN_REG})(:{PORT_REG})?"
HTTP_URL_REG = rf"^{ORIGIN_REG}(/[\w.-]+)+(?![\n\r])$"


def _remove_duplicates(lst: list) -> list:
    return list(set(lst))


FilePath = Annotated[
    str,
    Field(
        min_length=1,
        max_length=255,
        pattern=re.compile(r"^(?![.])[^!@#%^&*();$\n\r\t/\\]{1,255}(?![\n\r])$"),
    ),
]


UUID4Type = Annotated[
    str,
    Field(
        description="A UUID4",
        examples=["90f84e38-a71c-4d57-8d90-00fa8a197385"],
        pattern=re.compile(UUID4_REG),
    ),
]


UUID4ArrayType = Annotated[
    list[UUID4Type],
    Field(
        examples=[
            [
                "90f84e38-a71c-4d57-8d90-00fa8a197385",
                "60f84e39-ffff-4d99-8a78-00fa8aaf5666",
            ]
        ],
    ),
]


GenericDescription = Annotated[str, Field(max_length=4096)]

NullableGenericDescription = Annotated[str | None, Field(max_length=4096)]

UserName = Annotated[
    str,
    Field(
        description="The name of the user.",
        examples=["admin"],
        min_length=1,
        max_length=32,
    ),
]


UserFullName = Annotated[
    str,
    Field(
        description="The full name of the user.",
        examples=["Dr. Super User"],
        max_length=128,
    ),
]

GroupName = Annotated[
    str,
    Field(
        description="The full name of the group.",
        examples=["CCNA Study Group Class of 21"],
        min_length=1,
        max_length=64,
    ),
]

IPAddress = Annotated[
    str,
    Field(
        pattern=re.compile(IP_REG),
        description="An IPv4 or IPv6 host address.",
    ),
]

IPv4Address = Annotated[
    str,
    Field(
        pattern=re.compile(IPV4_REG),
        description="An IPv4 host address.",
    ),
]

IPv6Address = Annotated[
    str,
    Field(
        pattern=re.compile(IPV6_REG),
        description="An IPv6 host address.",
    ),
]

IPNetwork = Annotated[
    str,
    Field(
        pattern=re.compile(rf"^({IPV4_REG}|{IPV6_REG})" r"/\d{1,3}(?![\n\r])$"),
        description="An IPv4 or IPv6 network prefix.",
    ),
]

MACAddress = Annotated[
    str | None,
    Field(
        pattern=re.compile(r"^[a-fA-F\d]{2}(:[a-fA-F\d]{2}){5}(?![\n\r])$"),
        description="MAC address in Linux format.",
        examples=["00:11:22:33:44:55"],
    ),
]

Hostname = Annotated[
    str,
    Field(
        pattern=re.compile(HOST_REG),
        description="A Linux hostname (not FQDN).",
    ),
]

LinuxInterfaceName = Annotated[
    str,
    Field(
        pattern=re.compile(rf"^{LINT_REG}(?![\n\r])$"),
        description="Interface name or number in a Linux host.",
    ),
]


class OldPermission(StrEnum):
    READ_ONLY = DefaultPermissions.READ_ONLY
    READ_WRITE = DefaultPermissions.READ_WRITE


class Permission(StrEnum):
    LAB_ADMIN = DefaultPermissions.LAB_ADMIN
    LAB_EDIT = DefaultPermissions.LAB_EDIT
    LAB_EXEC = DefaultPermissions.LAB_EXEC
    LAB_VIEW = DefaultPermissions.LAB_VIEW


Permissions = Annotated[
    list[Permission],
    Field(
        ...,
        description="Permission array.",
        examples=[[Permission.LAB_ADMIN, Permission.LAB_EXEC]],
    ),
    AfterValidator(_remove_duplicates),
]

EffectivePermissions = Annotated[
    Permissions,
    Field(
        description="Effective permissions for the current user.",
    ),
]


class BorderStyle(StrEnum):
    SOLID = ""
    DOTTED = "2,2"
    DASHED = "4,2"


COLOR_EXAMPLES = ["#FF00FF", "rgba(255, 0, 0, 0.5)", "lightgoldenrodyellow"]
COLOR_EXAMPLES_STR = f"(e.g.,`{'` or `'.join(COLOR_EXAMPLES)}`)"

AnnotationColor = Annotated[
    str, Field(min_length=0, max_length=32, examples=COLOR_EXAMPLES)
]


DateTimeString = Annotated[
    datetime,
    Field(
        description="Datetime string in ISO8601 format.",
        examples=["2021-02-28T07:33:47+00:00"],
    ),
]

Label = Annotated[
    str,
    Field(
        min_length=1,
        max_length=128,
        description="A label.",
        examples=["Any human-readable text"],
    ),
]


DefinitionID = Annotated[
    str,
    Field(
        min_length=1,
        max_length=250,
        pattern=re.compile(r"^(?![.])[^!@#%^&*();$\n\r\t/\\]{1,250}(?![\n\r])$"),
        description="Name of the node or image definition (max 250 UTF-8 bytes).",
        examples=["server"],
    ),
]

Tag = Annotated[str, Field(max_length=64, description="A tag.")]

TagArray = Annotated[list[Tag], Field(description="Array of string tags.")]

Coordinate = Annotated[int, Field(description="A coordinate.", ge=-15000, le=15000)]

PinnedComputeID = Annotated[
    UUID4Type | None,
    Field(
        description="The ID of the compute host where this node is to be exclusively deployed."
    ),
]


class States(StrEnum):
    DEFINED_ON_CORE = "DEFINED_ON_CORE"
    STOPPED = "STOPPED"
    STARTED = "STARTED"


State = Annotated[States, Field(description="The state of the element.")]


class BaseDBModel(BaseModel):
    """Base class for all database based models."""

    id: UUID4Type = Field(default=None)
    created: DateTimeString = Field(
        default=None,
        description="The create date of the object, a string in ISO8601 format.",
    )
    modified: DateTimeString = Field(
        default=None,
        description="Last modification date of the object, a string in ISO8601 format.",
    )

    @field_serializer("created", "modified")
    def serialize_datetime(self, field: datetime) -> str:
        return field.astimezone(UTC).isoformat(timespec="seconds")


class FreeFormSchema(BaseModel, extra="allow"):
    """A freeform JSON object."""

    pass
