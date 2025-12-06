#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#
from __future__ import annotations

import attr


@attr.s
class HostPort:
    host: str = attr.ib()
    port: int = attr.ib()
    is_ipv6: bool = attr.ib(default=False)

    @classmethod
    def parse(cls, hostname: str, port: int, force=True) -> HostPort:
        """Return hostport, using port from hostname if present and not forced"""
        is_ipv6 = False
        if hostname.startswith("["):
            index = hostname.find("]")
            if index > 0:
                is_ipv6 = True
                host = hostname[1:index]
                hostname = hostname[index:]
            else:
                raise ValueError("Missing right bracket for IPv6 address")

        index = hostname.rfind(":")
        if index > 0:
            if not force:
                port = int(hostname[index + 1 :])
            hostname = hostname[:index]
        if not is_ipv6:
            host = hostname
        return HostPort(host, port, is_ipv6)

    @property
    def url_host(self) -> str:
        if self.is_ipv6:
            return f"[{self.host}]"
        return self.host

    @property
    def url(self) -> str:
        return f"{self.url_host}:{self.port}"
