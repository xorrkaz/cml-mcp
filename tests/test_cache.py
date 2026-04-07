# Copyright (c) 2025-2026  Cisco Systems, Inc.
# All rights reserved.

"""Unit tests for cml_mcp.tools.cache.ThreadSafeCache (mock / no-live runs)."""

from __future__ import annotations

import asyncio

import pytest

from cml_mcp.tools.cache import ThreadSafeCache

pytestmark = pytest.mark.mock_only


class _MockClient:
    def __init__(self, name: str = "") -> None:
        self.name = name
        self.closed = False

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_get_set_cache_hit():
    c = ThreadSafeCache(ttl=60)
    client = _MockClient("a")
    await c.set("k1", client)
    out = await c.get("k1")
    assert out is client
    assert not client.closed


@pytest.mark.asyncio
async def test_get_miss_after_ttl():
    """TTL expiry uses wall clock; fake time is awkward because ``field(default_factory=time.time)``
    captures ``time.time`` when the dataclass is defined (after any import of this module).
    """
    c = ThreadSafeCache(ttl=1)
    client = _MockClient()
    await c.set("k1", client)
    await asyncio.sleep(1.15)
    out = await c.get("k1")
    assert out is None
    assert client.closed


@pytest.mark.asyncio
async def test_set_replaces_key_closes_previous():
    c = ThreadSafeCache(ttl=60)
    first = _MockClient("1")
    second = _MockClient("2")
    await c.set("k", first)
    await c.set("k", second)
    assert first.closed is True
    assert await c.get("k") is second


@pytest.mark.asyncio
async def test_invalidate():
    c = ThreadSafeCache(ttl=60)
    client = _MockClient()
    await c.set("k", client)
    await c.invalidate("k")
    assert client.closed
    assert await c.get("k") is None


@pytest.mark.asyncio
async def test_clear_closes_all():
    c = ThreadSafeCache(ttl=60)
    x = _MockClient("x")
    y = _MockClient("y")
    await c.set("a", x)
    await c.set("b", y)
    await c.clear()
    assert x.closed and y.closed
