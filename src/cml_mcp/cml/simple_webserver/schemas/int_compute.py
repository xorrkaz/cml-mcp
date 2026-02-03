#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#
from typing import Annotated

from pydantic import BaseModel, Field, conlist
from simple_webserver.schemas.common import Hostname, IPAddress, UUID4Type

Hostpubkey = Annotated[
    str,
    Field(pattern=r"^[a-zA-Z\d_-]{1,40}(?:@openssh.com)? [a-zA-Z0-9+/=]{1,16000}$"),
]


class ComputeHostInternal(BaseModel, extra="forbid"):
    id: UUID4Type = Field(...)
    server_address: IPAddress = Field(...)
    hostname: Hostname = Field(...)
    is_simulator: bool = Field(...)
    is_connector: bool = Field(...)
    sshd_host_keys: conlist(Hostpubkey, min_length=0, max_length=5) = None
