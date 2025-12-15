# Implementation Plan: Per-Request CML Server Configuration

**Version**: 1.0  
**Date**: December 15, 2025  
**Status**: Ready for Implementation

## Executive Summary

This document describes the implementation of per-request CML server configuration for cml-mcp HTTP mode. This feature allows each MCP request to target a different CML server by specifying the server URL in request headers, enabling multi-tenant and multi-environment scenarios.

## Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| R1 | Support dynamic CML server URL per request (HTTP mode) | Must |
| R2 | Maintain backward compatibility with `CML_URL` env var as fallback | Must |
| R3 | Support PyATS with dynamically-selected servers | Must |
| R4 | Implement URL allowlist for security | Must |
| R5 | Implement URL pattern matching for security | Must |
| R6 | Implement LRU eviction for client pool | Must |
| R7 | Implement TTL eviction for idle clients | Must |
| R8 | Implement per-server concurrent request limits | Must |
| R9 | stdio mode unchanged (global client) | Must |

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           cml-mcp Server (HTTP Mode)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────────────┐    ┌────────────────────────┐  │
│  │  settings   │    │  CustomRequestMiddleware │  │    CMLClientPool     │  │
│  │             │    │                         │    │                      │  │
│  │ • cml_url   │───▶│ • Extract headers       │───▶│ • get_client()      │  │
│  │ • allowed   │    │ • Validate URL          │    │ • release_client()  │  │
│  │ • pattern   │    │ • Get/create client     │    │ • LRU eviction      │  │
│  │ • pool cfg  │    │ • Set ContextVar        │    │ • TTL eviction      │  │
│  └─────────────┘    │ • Handle PyATS          │    │ • Per-server limits │  │
│                     └─────────────────────────┘    └────────────────────────┘  │
│                                │                              │             │
│                                ▼                              │             │
│                     ┌─────────────────────┐                   │             │
│                     │     ContextVar      │◀──────────────────┘             │
│                     │ current_cml_client  │                                 │
│                     └─────────────────────┘                                 │
│                                │                                            │
│                                ▼                                            │
│                     ┌─────────────────────┐                                 │
│                     │   get_cml_client()  │                                 │
│                     │   (helper function) │                                 │
│                     └─────────────────────┘                                 │
│                                │                                            │
│                                ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         MCP Tools (39+)                              │   │
│  │  • get_cml_labs()  • create_cml_lab()  • get_cml_nodes()  • ...     │   │
│  │  All tools call: client = get_cml_client()                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Request Flow

```
┌─────────────┐      ┌───────────────┐      ┌────────────────┐      ┌───────────┐
│   Client    │      │   Middleware  │      │  Client Pool   │      │ CML Server│
└──────┬──────┘      └───────┬───────┘      └───────┬────────┘      └─────┬─────┘
       │                     │                      │                     │
       │  POST /mcp          │                      │                     │
       │  Headers:           │                      │                     │
       │  X-CML-Server-URL   │                      │                     │
       │  X-Authorization    │                      │                     │
       │─────────────────────▶                      │                     │
       │                     │                      │                     │
       │                     │  validate_url(url)   │                     │
       │                     │──────────────────────▶                     │
       │                     │                      │                     │
       │                     │  ◀─ OK or Error ─────│                     │
       │                     │                      │                     │
       │                     │  get_client(url,     │                     │
       │                     │    user, pass, ssl)  │                     │
       │                     │──────────────────────▶                     │
       │                     │                      │                     │
       │                     │                      │── Check cache ──────│
       │                     │                      │                     │
       │                     │  ◀─ CMLClient ───────│                     │
       │                     │                      │                     │
       │                     │  current_cml_client  │                     │
       │                     │      .set(client)    │                     │
       │                     │                      │                     │
       │                     │  client.check_auth() │                     │
       │                     │──────────────────────────────────────────▶ │
       │                     │                      │                     │
       │                     │  ◀───────────────────────── JWT Token ─────│
       │                     │                      │                     │
       │                     │  [Execute MCP Tool]  │                     │
       │                     │  client = get_cml_client()                 │
       │                     │  client.get("/labs") │                     │
       │                     │──────────────────────────────────────────▶ │
       │                     │                      │                     │
       │                     │  ◀─────────────────────────── Response ────│
       │                     │                      │                     │
       │                     │  release_client(url) │                     │
       │                     │──────────────────────▶                     │
       │                     │                      │                     │
       │  ◀─ SSE Response ───│                      │                     │
       │                     │                      │                     │
```

## File Changes

### New Files

| File | Description |
|------|-------------|
| `src/cml_mcp/client_pool.py` | CMLClientPool class with eviction, ContextVar, helper function |

### Modified Files

| File | Changes |
|------|---------|
| `src/cml_mcp/settings.py` | Add URL allowlist, pattern, pool configuration fields |
| `src/cml_mcp/cml_client.py` | Add `update_vclient_url()` method for dynamic URL switching |
| `src/cml_mcp/server.py` | Update middleware, initialize pool, update all tools to use `get_cml_client()` |

---

## Detailed Implementation

### Phase 1: Settings (`settings.py`)

#### New Fields

```python
from pydantic import AnyHttpUrl, Field

class Settings(BaseSettings):
    # ... existing fields ...

    # === Per-Request Server Configuration (HTTP Mode) ===
    cml_allowed_urls: list[AnyHttpUrl] = Field(
        default_factory=list,
        description="Allowlist of permitted CML server URLs. Empty list = no allowlist restriction.",
    )
    cml_url_pattern: str | None = Field(
        default=None,
        description="Regex pattern for permitted CML server URLs (e.g., '^https://cml-.*\\.example\\.com$')",
    )

    # === Client Pool Configuration (HTTP Mode) ===
    cml_pool_max_size: int = Field(
        default=50,
        description="Maximum number of CML clients in the pool",
    )
    cml_pool_ttl_seconds: int = Field(
        default=300,
        description="Time-to-live for idle clients in seconds (default: 5 minutes)",
    )
    cml_pool_max_per_server: int = Field(
        default=5,
        description="Maximum concurrent requests per CML server",
    )
```

#### Environment Variable Examples

```bash
# Allowlist (JSON array)
CML_ALLOWED_URLS='["https://cml-prod.example.com", "https://cml-dev.example.com"]'

# Pattern (regex string)
CML_URL_PATTERN='^https://cml-.*\.example\.com$'

# Pool configuration
CML_POOL_MAX_SIZE=100
CML_POOL_TTL_SECONDS=600
CML_POOL_MAX_PER_SERVER=10
```

---

### Phase 2: Client Pool (`client_pool.py`)

Create new file `src/cml_mcp/client_pool.py`:

```python
# Copyright (c) 2025  Cisco Systems, Inc.
# All rights reserved.
# [License header...]

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


# Global pool instance (initialized in server.py for HTTP mode)
cml_pool: CMLClientPool | None = None


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
```

---

### Phase 3: CML Client Updates (`cml_client.py`)

Add method for dynamic URL switching (for PyATS `virl2_client`):

```python
# Add to CMLClient class:

def update_vclient_url(self, url: str) -> None:
    """
    Update the virl2_client URL for dynamic server switching.
    
    This recreates the virl2_client.ClientLibrary instance with the new URL
    while preserving the current credentials.
    
    Args:
        url: New CML server URL
    """
    self.base_url = url.rstrip("/")
    self.api_base = f"{self.base_url}/api/v0"
    # Recreate virl2_client with new URL
    self.vclient = virl2_client.ClientLibrary(
        url,
        self.username,
        self.password,
        ssl_verify=self.verify_ssl,
        raise_for_auth_failure=False,
    )
```

---

### Phase 4: Server Updates (`server.py`)

#### 4.1 Import Updates

```python
# Add imports:
from cml_mcp.client_pool import (
    CMLClientPool,
    cml_pool,
    current_cml_client,
    get_cml_client,
)
```

#### 4.2 Pool Initialization

```python
# After settings validation, before middleware setup:

# Global client for stdio mode (unchanged)
cml_client = CMLClient(
    str(settings.cml_url),
    settings.cml_username,
    settings.cml_password,
    transport=str(settings.cml_mcp_transport),
    verify_ssl=settings.cml_verify_ssl,
)

# Initialize pool for HTTP mode
cml_pool: CMLClientPool | None = None
if settings.cml_mcp_transport == "http":
    cml_pool = CMLClientPool(
        max_size=settings.cml_pool_max_size,
        ttl_seconds=settings.cml_pool_ttl_seconds,
        max_per_server=settings.cml_pool_max_per_server,
        allowed_urls=[str(u) for u in settings.cml_allowed_urls] if settings.cml_allowed_urls else None,
        url_pattern=settings.cml_url_pattern,
    )
```

#### 4.3 Middleware Updates

```python
class CustomRequestMiddleware(Middleware):
    async def on_request(self, context: MiddlewareContext, call_next) -> Any:
        # Reset PyATS env vars
        os.environ.pop("PYATS_USERNAME", None)
        os.environ.pop("PYATS_PASSWORD", None)
        os.environ.pop("PYATS_AUTH_PASS", None)

        headers = get_http_headers()

        # === CML Server URL (with fallback) ===
        cml_url = headers.get("x-cml-server-url")
        if not cml_url:
            # Fallback to configured default
            if settings.cml_url:
                cml_url = str(settings.cml_url)
            else:
                raise McpError(
                    ErrorData(
                        message="Missing X-CML-Server-URL header and no default CML_URL configured",
                        code=-31002,
                    )
                )

        # === SSL Verification ===
        verify_ssl_header = headers.get("x-cml-verify-ssl", "").lower()
        if verify_ssl_header:
            verify_ssl = verify_ssl_header == "true"
        else:
            verify_ssl = settings.cml_verify_ssl

        # === CML Credentials ===
        auth_header = headers.get("x-authorization")
        if not auth_header or not auth_header.startswith("Basic "):
            raise McpError(
                ErrorData(
                    message="Unauthorized: Missing or invalid X-Authorization header",
                    code=-31002,
                )
            )
        parts = auth_header.split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "basic":
            raise McpError(
                ErrorData(
                    message="Invalid X-Authorization header format. Expected 'Basic <credentials>'",
                    code=-31001,
                )
            )
        try:
            decoded = base64.b64decode(parts[1]).decode("utf-8")
            username, password = decoded.split(":", 1)
        except Exception:
            raise McpError(
                ErrorData(
                    message="Failed to decode Basic authentication credentials",
                    code=-31002,
                )
            )

        # === Get client from pool ===
        try:
            client = await cml_pool.get_client(cml_url, username, password, verify_ssl)
            current_cml_client.set(client)
        except McpError:
            raise
        except Exception as e:
            raise McpError(
                ErrorData(
                    message=f"Failed to get CML client: {str(e)}",
                    code=-31002,
                )
            )

        # === Authenticate with CML ===
        try:
            # Reset token for stateless operation
            client.token = None
            client.admin = None
            await client.check_authentication()
        except Exception as e:
            raise McpError(
                ErrorData(
                    message=f"Unauthorized: {str(e)}",
                    code=-31002,
                )
            )

        # === PyATS Headers (unchanged logic) ===
        pyats_header = headers.get("x-pyats-authorization")
        if pyats_header and pyats_header.startswith("Basic "):
            pyats_parts = pyats_header.split(" ", 1)
            if len(pyats_parts) != 2 or pyats_parts[0].lower() != "basic":
                raise McpError(
                    ErrorData(
                        message="Invalid X-PyATS-Authorization header format. Expected 'Basic <credentials>'",
                        code=-31001,
                    )
                )
            try:
                pyats_decoded = base64.b64decode(pyats_parts[1]).decode("utf-8")
                pyats_username, pyats_password = pyats_decoded.split(":", 1)
                os.environ["PYATS_USERNAME"] = pyats_username
                os.environ["PYATS_PASSWORD"] = pyats_password
            except Exception:
                raise McpError(
                    ErrorData(
                        message="Failed to decode Basic authentication credentials for PyATS",
                        code=-31002,
                    )
                )

            pyats_enable_header = headers.get("x-pyats-enable")
            if pyats_enable_header and pyats_enable_header.startswith("Basic "):
                pyats_enable_parts = pyats_enable_header.split(" ", 1)
                if len(pyats_enable_parts) != 2 or pyats_enable_parts[0].lower() != "basic":
                    raise McpError(
                        ErrorData(
                            message="Invalid X-PyATS-Enable header format. Expected 'Basic <credentials>'",
                            code=-31001,
                        )
                    )
                try:
                    pyats_enable_decoded = base64.b64decode(pyats_enable_parts[1]).decode("utf-8")
                    os.environ["PYATS_AUTH_PASS"] = pyats_enable_decoded
                except Exception:
                    raise McpError(
                        ErrorData(
                            message="Failed to decode Basic authentication credentials for PyATS Enable",
                            code=-31002,
                        )
                    )

        # === Execute request and cleanup ===
        try:
            return await call_next(context)
        finally:
            # Release client back to pool
            await cml_pool.release_client(cml_url, verify_ssl)
            current_cml_client.set(None)
```

#### 4.4 Tool Function Updates

All tool functions must be updated to use `get_cml_client()` instead of the global `cml_client`:

**Pattern:**

```python
# Before:
async def some_tool(...):
    result = await cml_client.get("/endpoint")
    # ...

# After:
async def some_tool(...):
    client = get_cml_client()
    result = await client.get("/endpoint")
    # ...
```

**Affected functions (all tools in server.py):**

- `get_all_labs()`
- `get_cml_labs()`
- `get_cml_users()`
- `create_cml_user()`
- `delete_cml_user()`
- `get_cml_groups()`
- `create_cml_group()`
- `delete_cml_group()`
- `get_system_information()`
- `get_system_health()`
- `get_system_stats()`
- `get_node_definitions()`
- `create_cml_lab()`
- `update_cml_lab()`
- `delete_cml_lab()`
- `get_cml_lab_topology()`
- `import_cml_lab_topology()`
- `get_cml_nodes()`
- `create_cml_node()`
- `update_cml_node()`
- `delete_cml_node()`
- `get_cml_node_interfaces()`
- `get_cml_links()`
- `create_cml_link()`
- `update_cml_link_condition()`
- `delete_cml_link()`
- `start_cml_lab()`
- `stop_cml_lab()`
- `wipe_cml_lab()`
- `start_cml_node()`
- `stop_cml_node()`
- `wipe_cml_node()`
- `get_node_console_log()`
- `get_node_configuration()`
- `update_node_configuration()`
- `send_cli_commands()`
- `get_cml_annotations()`
- `create_cml_annotation()`
- `update_cml_annotation()`
- `delete_cml_annotation()`

---

## New Headers Reference

| Header | Required | Default | Description |
|--------|----------|---------|-------------|
| `X-CML-Server-URL` | No | `CML_URL` env var | Target CML server URL |
| `X-Authorization` | Yes (HTTP) | - | `Basic <base64(user:pass)>` for CML authentication |
| `X-CML-Verify-SSL` | No | `CML_VERIFY_SSL` env var | `true` or `false` for SSL verification |
| `X-PyATS-Authorization` | No | - | `Basic <base64(user:pass)>` for device authentication |
| `X-PyATS-Enable` | No | - | `Basic <base64(enable_pass)>` for device enable password |

---

## New Environment Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `CML_ALLOWED_URLS` | JSON array | `[]` | Allowlist of permitted CML server URLs |
| `CML_URL_PATTERN` | String (regex) | `null` | Regex pattern for permitted CML server URLs |
| `CML_POOL_MAX_SIZE` | Integer | `50` | Maximum number of clients in the pool |
| `CML_POOL_TTL_SECONDS` | Integer | `300` | Idle timeout for pooled clients (seconds) |
| `CML_POOL_MAX_PER_SERVER` | Integer | `5` | Maximum concurrent requests per CML server |

---

## Example Configurations

### Development (No Restrictions)

```bash
# .env
CML_URL=https://cml-dev.example.com
CML_MCP_TRANSPORT=http
# No CML_ALLOWED_URLS or CML_URL_PATTERN = allow any URL
```

### Production (Allowlist)

```bash
# .env
CML_URL=https://cml-prod.example.com
CML_MCP_TRANSPORT=http
CML_ALLOWED_URLS='["https://cml-prod.example.com", "https://cml-dr.example.com"]'
CML_POOL_MAX_SIZE=100
CML_POOL_TTL_SECONDS=600
```

### Production (Pattern)

```bash
# .env
CML_URL=https://cml-prod.example.com
CML_MCP_TRANSPORT=http
CML_URL_PATTERN='^https://cml-[a-z]+\.example\.com$'
```

### MCP Client Configuration

```json
{
  "mcpServers": {
    "CML Production": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote",
        "http://mcp-server:9000/mcp",
        "--header", "X-CML-Server-URL: https://cml-prod.example.com",
        "--header", "X-Authorization: Basic YWRtaW46c2VjcmV0",
        "--header", "X-CML-Verify-SSL: true"
      ]
    },
    "CML Development": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote",
        "http://mcp-server:9000/mcp",
        "--header", "X-CML-Server-URL: https://cml-dev.example.com",
        "--header", "X-Authorization: Basic ZGV2OnBhc3M=",
        "--header", "X-CML-Verify-SSL: false"
      ]
    }
  }
}
```

---

## Testing Plan

### Unit Tests

| Test | Description |
|------|-------------|
| `test_pool_get_client_creates_new` | Verify new client creation |
| `test_pool_get_client_reuses_cached` | Verify client reuse from pool |
| `test_pool_lru_eviction` | Verify LRU eviction at max_size |
| `test_pool_ttl_eviction` | Verify TTL eviction of idle clients |
| `test_pool_per_server_limit` | Verify per-server concurrent limit |
| `test_url_validation_allowlist` | Verify allowlist validation |
| `test_url_validation_pattern` | Verify pattern validation |
| `test_url_normalization` | Verify URL normalization consistency |
| `test_get_cml_client_http_mode` | Verify ContextVar returns request client |
| `test_get_cml_client_stdio_mode` | Verify fallback to global client |

### Integration Tests

| Test | Description |
|------|-------------|
| `test_multi_server_sequential` | Sequential requests to different servers |
| `test_multi_server_concurrent` | Concurrent requests to different servers |
| `test_fallback_to_default_url` | Verify fallback when header missing |
| `test_pyats_with_dynamic_server` | PyATS commands with per-request server |

---

## Migration Guide

### Backward Compatibility

This implementation is **fully backward compatible**:

1. **stdio mode**: Unchanged behavior (global client)
2. **HTTP mode without `X-CML-Server-URL`**: Falls back to `CML_URL` environment variable
3. **Existing headers**: All existing headers continue to work

### Upgrade Steps

1. Update cml-mcp to the new version
2. (Optional) Configure URL restrictions for security
3. (Optional) Adjust pool settings for your load
4. (Optional) Update MCP client configs to use `X-CML-Server-URL` header

---

## Error Codes

| Code | Message | Cause |
|------|---------|-------|
| `-31001` | Invalid header format | Malformed Basic auth header |
| `-31002` | Unauthorized | Missing credentials or auth failure |
| `-31003` | URL not allowed | URL failed allowlist/pattern validation |
| `-31004` | Too many concurrent requests | Per-server limit exceeded |

---

## Changelog

### Version X.Y.Z

- **Added**: Per-request CML server URL via `X-CML-Server-URL` header (HTTP mode)
- **Added**: Per-request SSL verification via `X-CML-Verify-SSL` header
- **Added**: URL allowlist security (`CML_ALLOWED_URLS`)
- **Added**: URL pattern security (`CML_URL_PATTERN`)
- **Added**: Client pool with LRU/TTL eviction
- **Added**: Per-server concurrent request limits
- **Changed**: Tools now use `get_cml_client()` for request-scoped client resolution
- **Changed**: Middleware refactored to support multi-server
