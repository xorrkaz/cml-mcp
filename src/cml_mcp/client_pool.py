# Copyright (c) 2025  Cisco Systems, Inc.
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.

# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

"""
CML Client Pool for per-request server configuration.

This module provides:
- CMLClientPool: Thread-safe pool with LRU, TTL, and per-server limits
- ContextVar for request-scoped client access
- Helper function get_cml_client() for tool usage
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections import OrderedDict
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from mcp.shared.exceptions import McpError
from mcp.types import ErrorData

if TYPE_CHECKING:
    from cml_mcp.cml_client import CMLClient

logger = logging.getLogger(__name__)

# Request-scoped context variable for the current CML client
current_cml_client: ContextVar[CMLClient | None] = ContextVar("current_cml_client", default=None)


@dataclass
class PooledClient:
    """Wrapper for a pooled CML client with metadata."""

    client: CMLClient
    last_used: float = field(default_factory=time.time)
    active_requests: int = 0


class CMLClientPool:
    """
    Thread-safe pool of CMLClient instances.

    Features:
    - LRU eviction when pool reaches max_size
    - TTL-based eviction for idle clients
    - Per-server concurrent request limits
    - URL validation against allowlist and/or pattern

    Usage:
        pool = CMLClientPool(max_size=50, ttl_seconds=300)
        client = await pool.get_client(url, user, pass, ssl)
        try:
            # Use client...
        finally:
            await pool.release_client(url, ssl)
    """

    def __init__(
        self,
        max_size: int = 50,
        ttl_seconds: int = 300,
        max_per_server: int = 5,
        allowed_urls: list[str] | None = None,
        url_pattern: str | None = None,
    ):
        """
        Initialize the client pool.

        Args:
            max_size: Maximum number of clients in the pool
            ttl_seconds: Seconds after which idle clients are evicted
            max_per_server: Maximum concurrent requests per server
            allowed_urls: List of allowed CML server URLs (empty = no restriction)
            url_pattern: Regex pattern for allowed URLs (None = no restriction)
        """
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._max_per_server = max_per_server
        self._allowed_urls = {self._normalize_url(u) for u in (allowed_urls or [])} if allowed_urls else set()
        self._url_pattern = re.compile(url_pattern) if url_pattern else None

        # LRU-ordered dict: (normalized_url, verify_ssl) -> PooledClient
        self._clients: OrderedDict[tuple[str, bool], PooledClient] = OrderedDict()
        self._lock = asyncio.Lock()

        logger.info(
            f"CMLClientPool initialized: max_size={max_size}, ttl={ttl_seconds}s, "
            f"max_per_server={max_per_server}, allowed_urls={len(self._allowed_urls)}, "
            f"pattern={'set' if url_pattern else 'none'}"
        )

    @staticmethod
    def _normalize_url(url: str) -> str:
        """
        Normalize URL for consistent comparison and caching.

        - Lowercase scheme and host
        - Remove default ports (443 for https, 80 for http)
        - Remove trailing slashes
        """
        parsed = urlparse(url)
        host = parsed.hostname or ""
        port = parsed.port

        # Remove default ports
        if port == 443 and parsed.scheme == "https":
            port = None
        if port == 80 and parsed.scheme == "http":
            port = None

        normalized = f"{parsed.scheme}://{host.lower()}"
        if port:
            normalized += f":{port}"
        return normalized.rstrip("/")

    def validate_url(self, url: str) -> str:
        """
        Validate URL against allowlist and pattern.

        Args:
            url: The CML server URL to validate

        Returns:
            Normalized URL if valid

        Raises:
            McpError: If URL is not allowed
        """
        normalized = self._normalize_url(url)

        # Check allowlist (if configured)
        if self._allowed_urls and normalized not in self._allowed_urls:
            logger.warning(f"URL not in allowlist: {url}")
            raise McpError(
                ErrorData(
                    message=f"CML server URL not in allowlist: {url}",
                    code=-31003,
                )
            )

        # Check pattern (if configured)
        if self._url_pattern and not self._url_pattern.match(url):
            logger.warning(f"URL does not match pattern: {url}")
            raise McpError(
                ErrorData(
                    message=f"CML server URL does not match allowed pattern: {url}",
                    code=-31003,
                )
            )

        return normalized

    async def get_client(
        self,
        url: str,
        username: str,
        password: str,
        verify_ssl: bool = False,
    ) -> CMLClient:
        """
        Get or create a CMLClient for the given configuration.

        The client's credentials are updated to match the request.
        The client is marked as having an active request.

        Args:
            url: CML server URL
            username: CML username
            password: CML password
            verify_ssl: Whether to verify SSL certificates

        Returns:
            CMLClient configured for the given server

        Raises:
            McpError: If URL validation fails or per-server limit reached
        """
        from cml_mcp.cml_client import CMLClient

        normalized_url = self.validate_url(url)
        key = (normalized_url, verify_ssl)

        async with self._lock:
            # Evict expired clients first
            await self._evict_expired()

            if key in self._clients:
                # Move to end (most recently used)
                self._clients.move_to_end(key)
                pooled = self._clients[key]

                # Check per-server limit
                if pooled.active_requests >= self._max_per_server:
                    logger.warning(f"Per-server limit reached for {url}")
                    raise McpError(
                        ErrorData(
                            message=f"Too many concurrent requests to {url} (max: {self._max_per_server})",
                            code=-31004,
                        )
                    )

                logger.debug(f"Reusing pooled client for {normalized_url}")
            else:
                # Evict LRU if at capacity
                if len(self._clients) >= self._max_size:
                    await self._evict_lru()

                # Create new client
                logger.info(f"Creating new client for {normalized_url}")
                client = CMLClient(
                    host=normalized_url,
                    username=username,
                    password=password,
                    transport="http",
                    verify_ssl=verify_ssl,
                )
                pooled = PooledClient(client=client)
                self._clients[key] = pooled

            # Update credentials for this request
            pooled.client.username = username
            pooled.client.password = password
            pooled.client.vclient.username = username
            pooled.client.vclient.password = password
            pooled.last_used = time.time()
            pooled.active_requests += 1

            logger.debug(f"Client {normalized_url}: active_requests={pooled.active_requests}")
            return pooled.client

    async def release_client(self, url: str, verify_ssl: bool = False) -> None:
        """
        Release a client back to the pool (decrement active request count).

        Args:
            url: CML server URL
            verify_ssl: SSL verification setting (must match get_client call)
        """
        normalized_url = self._normalize_url(url)
        key = (normalized_url, verify_ssl)

        async with self._lock:
            if key in self._clients:
                self._clients[key].active_requests = max(0, self._clients[key].active_requests - 1)
                logger.debug(f"Released client {normalized_url}: active_requests={self._clients[key].active_requests}")

    async def _evict_expired(self) -> None:
        """Evict clients that have been idle longer than TTL."""
        now = time.time()
        expired_keys = [
            key
            for key, pooled in self._clients.items()
            if (now - pooled.last_used) > self._ttl_seconds and pooled.active_requests == 0
        ]
        for key in expired_keys:
            pooled = self._clients.pop(key)
            await pooled.client.close()
            logger.info(f"Evicted expired client: {key[0]}")

    async def _evict_lru(self) -> None:
        """Evict the least recently used client with no active requests."""
        for key in list(self._clients.keys()):
            if self._clients[key].active_requests == 0:
                pooled = self._clients.pop(key)
                await pooled.client.close()
                logger.info(f"Evicted LRU client: {key[0]}")
                return

        # If all clients have active requests, evict the oldest anyway
        if self._clients:
            key = next(iter(self._clients))
            pooled = self._clients.pop(key)
            await pooled.client.close()
            logger.warning(f"Force-evicted active client: {key[0]}")

    async def close_all(self) -> None:
        """Close all pooled clients. Call during shutdown."""
        async with self._lock:
            for pooled in self._clients.values():
                await pooled.client.close()
            self._clients.clear()
            logger.info("Closed all pooled clients")

    @property
    def stats(self) -> dict:
        """Return pool statistics for monitoring."""
        return {
            "total_clients": len(self._clients),
            "max_size": self._max_size,
            "clients": {
                key[0]: {
                    "verify_ssl": key[1],
                    "active_requests": pooled.active_requests,
                    "idle_seconds": int(time.time() - pooled.last_used),
                }
                for key, pooled in self._clients.items()
            },
        }


def get_cml_client() -> CMLClient:
    """
    Get the CML client for the current request.

    In HTTP mode, returns the request-scoped client from ContextVar.
    In stdio mode, returns the global client.

    Returns:
        CMLClient for the current request/session

    Raises:
        RuntimeError: If no client is available
    """
    client = current_cml_client.get()
    if client is not None:
        return client

    # Fallback to global client (stdio mode)
    # Import here to avoid circular import at module load
    from cml_mcp.server import cml_client as global_client

    if global_client is None:
        raise RuntimeError("No CML client available")

    return global_client
