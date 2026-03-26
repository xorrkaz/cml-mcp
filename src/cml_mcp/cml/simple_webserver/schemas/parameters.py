#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#
import re
from enum import StrEnum
from typing import Annotated

from fastapi import Path, Query

from simple_webserver.schemas.common import DOMAIN_REG, PORT_REG, Permission, UUID4Type

LabIdPathParameter = Annotated[
    UUID4Type,
    Path(
        description="The unique ID of a lab on this controller.",
        examples=["90f84e38-a71c-4d57-8d90-00fa8a197385"],
    ),
]


AnnotationIdPathParameter = Annotated[
    UUID4Type,
    Path(
        description="The unique ID of an annotation on this controller.",
        examples=["90f84e38-a71c-4d57-8d90-00fa8a197385"],
    ),
]


SmartAnnotationIdPathParameter = Annotated[
    UUID4Type,
    Path(description="The unique ID of a Smart annotation on this controller."),
]


ExternalConnectorIdPathParameter = Annotated[
    UUID4Type,
    Path(description="The unique ID of an external connector on a controller."),
]


NoticeIdPathParameter = Annotated[
    UUID4Type, Path(description="The unique ID of a notice to users.")
]


ResourcePoolIdPathParameter = Annotated[
    UUID4Type, Path(description="The unique ID of a resource pool on this controller.")
]


NodeIdPathParameter = Annotated[
    UUID4Type, Path(description="The unique ID of a node within a particular lab.")
]


InterfaceIdPathParameter = Annotated[
    UUID4Type,
    Path(description="The unique ID of an interface within a particular lab."),
]


LinkIdPathParameter = Annotated[
    UUID4Type, Path(description="The unique ID of a link within a particular lab.")
]


ComputeIdPathParameter = Annotated[
    UUID4Type,
    Path(description="The unique ID of a compute host managed by this controller."),
]


SearchQueryPathParameter = Annotated[
    str, Path(description="The search query parameter.", examples=["iosv-1"])
]


TagPathParameter = Annotated[
    str, Path(description="The unique tag path parameter.", examples=["Core"])
]


ConsoleIdPathParameter = Annotated[
    int,
    Path(
        description="The unique ID of a console line for a node.",
        examples=[0],
        ge=0,
        le=64,
    ),
]


DefinitionIDPathParameter = Annotated[
    str,
    Path(
        description="ID of the requested definition.",
        min_length=1,
        max_length=250,
        pattern=re.compile(r"^(?![.])[^!@#%^&*();$\n\r\t/\\]{1,250}(?![\n\r])$"),
        examples=["server"],
    ),
]

IsJsonQueryParameter = Annotated[
    bool,
    Query(description="Switch to fetch in JSON format.", alias="json"),
]


DataQueryParameter = Annotated[
    bool,
    Query(
        description="""
        Specify `true` if the service should include data
        about each element instead of just the UUID4Type array.
        """
    ),
]


ShowAllQueryParameter = Annotated[
    bool,
    Query(
        description="""
        Specify `true` if the service should include items
        which belong to all accessible labs or just owned labs.
        """
    ),
]


OperationalQueryParameter = Annotated[
    bool,
    Query(
        description="""
        Specify `true` if the service should include operational data
        about each element instead of just configuration.
        This parameter defaults to `true`,
        but may be switched to `false` in a later version of the API.
        if set to `false` `operational` field will be returned as `null`
        """
    ),
]

ExcludeConfigurationsQueryParameter = Annotated[
    bool,
    Query(
        description="""
        Specify `true` if the node configuration should be excluded.
        Specify `false` if all node configurations should be included.
        """
    ),
]


UserIdPathParameter = Annotated[
    UUID4Type, Path(description="The unique ID of a user on this controller.")
]


UsernamePathParameter = Annotated[
    str,
    Path(
        examples=["admin"],
        min_length=1,
        max_length=32,
        description="The username of a user on this controller.",
    ),
]

HostNameQueryParameter = Annotated[
    str,
    Query(
        min_length=1,
        max_length=128,
        pattern=re.compile(rf"^({DOMAIN_REG})(:{PORT_REG})?(?![\n\r])$"),
        description="A hostname or IP address with optional L4 port number.",
        examples=[
            {
                "hostname": {
                    "value": "port-forwarder.example.com:12250",
                    "summary": "A port forwarder points to the terminal ssh server of the controller.",
                }
            },
            {
                "ipv4_address": {
                    "value": "10.111.23.23:22",
                    "summary": "IP address of the controller, default port 22 can be omitted.",
                }
            },
            {
                "ipv6_address": {
                    "value": "[2001:420:7357::1]:12250",
                    "summary": "IPv6 address of the controller, in brackets.",
                }
            },
            {
                "link_local_ipv6_address": {
                    "value": r"[fe80:420:7357::%ens224]:12250",
                    "summary": "A link-local IPv6 address of the controller, via client's ens224 interface.",
                }
            },
        ],
    ),
]

AuthGroupFilterQueryParameter = Annotated[
    str | None,
    Query(
        description="An optional filter that will be applied to the groups.",
        examples=[
            "(& (memberof=CN=parent_group,OU=groups,DC=corp,DC=com) "
            "(objectclass=group) )"
        ],
        max_length=1024,
        alias="filter",
    ),
]


PermissionQueryParameter = Annotated[
    Permission,
    Query(description="A lab resource permission."),
]


class Service(StrEnum):
    CONSOLE = "Console"
    PCAP = "PCAP"
    VNC = "VNC"


ServiceQueryParameter = Annotated[
    Service,
    Query(description="A lab resource service type."),
]


ServiceUUID4QueryParameter = Annotated[
    UUID4Type,
    Query(description="The unique key of a lab service."),
]


WirelessPcapPathParameter = Annotated[
    UUID4Type,
    Path(description="The unique key of a wireless PCAP capture session."),
]
