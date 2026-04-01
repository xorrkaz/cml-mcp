# Copyright (c) 2025-2026  Cisco Systems, Inc.
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

"""Definitions for a cache for session management."""

import logging
import time
from dataclasses import dataclass, field
from asyncio import Lock
from typing import Dict, Optional

from cml_mcp.cml_client import CMLClient

logger = logging.getLogger("cml-mcp.cache")


@dataclass
class CacheEntry:
    """Represents a cache entry with a value and an expiration time."""

    value: CMLClient
    timestamp: float = field(default_factory=time.time)

    def is_expired(self, ttl: int) -> bool:
        """Check if cache entry has exceeded TTL."""
        return (time.time() - self.timestamp) > ttl


class ThreadSafeCache:
    """Thread-safe cache with TTL support."""

    def __init__(self, ttl: int = 3600):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._ttl = ttl

    async def get(self, key: str) -> Optional[CMLClient]:
        """Retrieve value from cache if not expired."""
        async with self._lock:
            entry = self._cache.get(key)
            if entry and not entry.is_expired(self._ttl):
                return entry.value
            elif entry:
                logger.debug("Cache entry for key %s has expired", key)
                del self._cache[key]
            return None

    async def set(self, key: str, value: CMLClient) -> None:
        """Store value in cache with current timestamp."""
        async with self._lock:
            self._cache[key] = CacheEntry(value=value)

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            logger.debug("Clearing entire cache")
            self._cache.clear()

    async def invalidate(self, key: str) -> None:
        """Remove specific cache entry."""
        async with self._lock:
            logger.debug("Invalidating cache entry for key: %s", key)
            self._cache.pop(key, None)
