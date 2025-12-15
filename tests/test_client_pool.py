# Copyright (c) 2025  Cisco Systems, Inc.
# All rights reserved.

"""Unit tests for client_pool.py - CMLClientPool and related functionality."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.shared.exceptions import McpError

from cml_mcp.client_pool import CMLClientPool, PooledClient, current_cml_client, get_cml_client


def create_mock_client():
    """Create a mock CMLClient instance."""
    client = MagicMock()
    client.username = "testuser"
    client.password = "testpass"
    client.vclient = MagicMock()
    client.vclient.username = "testuser"
    client.vclient.password = "testpass"
    client.close = AsyncMock()  # Must be AsyncMock for await
    client.get = AsyncMock(return_value={})
    client.post = AsyncMock(return_value={})
    return client


class TestUrlNormalization:
    """Test URL normalization logic."""

    def test_normalize_basic_https_url(self):
        """Test normalizing a basic HTTPS URL."""
        pool = CMLClientPool()
        result = pool._normalize_url("https://cml.example.com")
        assert result == "https://cml.example.com"

    def test_normalize_removes_trailing_slash(self):
        """Test that trailing slashes are removed."""
        pool = CMLClientPool()
        result = pool._normalize_url("https://cml.example.com/")
        assert result == "https://cml.example.com"

    def test_normalize_removes_default_https_port(self):
        """Test that default HTTPS port 443 is removed."""
        pool = CMLClientPool()
        result = pool._normalize_url("https://cml.example.com:443")
        assert result == "https://cml.example.com"

    def test_normalize_removes_default_http_port(self):
        """Test that default HTTP port 80 is removed."""
        pool = CMLClientPool()
        result = pool._normalize_url("http://cml.example.com:80")
        assert result == "http://cml.example.com"

    def test_normalize_preserves_non_default_port(self):
        """Test that non-default ports are preserved."""
        pool = CMLClientPool()
        result = pool._normalize_url("https://cml.example.com:8443")
        assert result == "https://cml.example.com:8443"

    def test_normalize_lowercases_host(self):
        """Test that hostname is lowercased."""
        pool = CMLClientPool()
        result = pool._normalize_url("https://CML.EXAMPLE.COM")
        assert result == "https://cml.example.com"

    def test_normalize_lowercases_scheme(self):
        """Test that scheme is lowercased."""
        pool = CMLClientPool()
        result = pool._normalize_url("HTTPS://cml.example.com")
        assert result == "https://cml.example.com"

    def test_normalize_ip_address(self):
        """Test normalizing IP address URLs."""
        pool = CMLClientPool()
        result = pool._normalize_url("https://192.168.1.100")
        assert result == "https://192.168.1.100"

    def test_normalize_ip_address_with_port(self):
        """Test normalizing IP address URLs with non-default port."""
        pool = CMLClientPool()
        result = pool._normalize_url("https://192.168.1.100:8443")
        assert result == "https://192.168.1.100:8443"


class TestUrlValidation:
    """Test URL validation against allowlist and pattern."""

    def test_validate_url_no_restrictions(self):
        """Test validation with no allowlist or pattern configured."""
        pool = CMLClientPool()
        result = pool.validate_url("https://any.server.com")
        assert result == "https://any.server.com"

    def test_validate_url_allowlist_pass(self):
        """Test validation passes when URL is in allowlist."""
        pool = CMLClientPool(allowed_urls=["https://cml.example.com", "https://cml2.example.com"])
        result = pool.validate_url("https://cml.example.com")
        assert result == "https://cml.example.com"

    def test_validate_url_allowlist_fail(self):
        """Test validation fails when URL is not in allowlist."""
        pool = CMLClientPool(allowed_urls=["https://cml.example.com"])
        with pytest.raises(McpError) as exc_info:
            pool.validate_url("https://other.server.com")
        assert "not in allowlist" in str(exc_info.value.error.message)
        assert exc_info.value.error.code == -31003

    def test_validate_url_allowlist_normalized_match(self):
        """Test that allowlist comparison uses normalized URLs."""
        pool = CMLClientPool(allowed_urls=["https://cml.example.com:443"])  # With explicit default port
        # Should match because both normalize to same URL
        result = pool.validate_url("https://cml.example.com")  # Without port
        assert result == "https://cml.example.com"

    def test_validate_url_pattern_pass(self):
        """Test validation passes when URL matches pattern."""
        pool = CMLClientPool(url_pattern=r"^https://cml[0-9]+\.example\.com$")
        result = pool.validate_url("https://cml1.example.com")
        assert result == "https://cml1.example.com"

    def test_validate_url_pattern_fail(self):
        """Test validation fails when URL doesn't match pattern."""
        pool = CMLClientPool(url_pattern=r"^https://cml[0-9]+\.example\.com$")
        with pytest.raises(McpError) as exc_info:
            pool.validate_url("https://other.server.com")
        assert "does not match allowed pattern" in str(exc_info.value.error.message)
        assert exc_info.value.error.code == -31003

    def test_validate_url_both_allowlist_and_pattern(self):
        """Test that both allowlist AND pattern must pass when both configured."""
        pool = CMLClientPool(allowed_urls=["https://cml1.example.com"], url_pattern=r"^https://.*\.example\.com$")
        # In allowlist and matches pattern - should pass
        result = pool.validate_url("https://cml1.example.com")
        assert result == "https://cml1.example.com"

    def test_validate_url_in_allowlist_but_not_pattern(self):
        """Test URL in allowlist but not matching pattern fails."""
        pool = CMLClientPool(
            allowed_urls=["https://cml.other.com"], url_pattern=r"^https://.*\.example\.com$"  # In allowlist  # But doesn't match pattern
        )
        with pytest.raises(McpError) as exc_info:
            pool.validate_url("https://cml.other.com")
        assert "does not match allowed pattern" in str(exc_info.value.error.message)


class TestPooledClient:
    """Test PooledClient dataclass."""

    def test_pooled_client_defaults(self):
        """Test PooledClient default values."""
        mock_client = create_mock_client()
        pooled = PooledClient(client=mock_client)
        assert pooled.client == mock_client
        assert pooled.active_requests == 0
        assert pooled.last_used > 0  # Should be set to current time

    def test_pooled_client_custom_values(self):
        """Test PooledClient with custom values."""
        mock_client = create_mock_client()
        pooled = PooledClient(client=mock_client, last_used=1000.0, active_requests=3)
        assert pooled.last_used == 1000.0
        assert pooled.active_requests == 3


class TestCMLClientPoolInit:
    """Test CMLClientPool initialization."""

    def test_pool_default_init(self):
        """Test pool initialization with defaults."""
        pool = CMLClientPool()
        assert pool._max_size == 50
        assert pool._ttl_seconds == 300
        assert pool._max_per_server == 5
        assert pool._allowed_urls == set()
        assert pool._url_pattern is None
        assert len(pool._clients) == 0

    def test_pool_custom_init(self):
        """Test pool initialization with custom values."""
        pool = CMLClientPool(
            max_size=100, ttl_seconds=600, max_per_server=10, allowed_urls=["https://cml.example.com"], url_pattern=r"^https://.*$"
        )
        assert pool._max_size == 100
        assert pool._ttl_seconds == 600
        assert pool._max_per_server == 10
        assert "https://cml.example.com" in pool._allowed_urls
        assert pool._url_pattern is not None

    def test_pool_stats_empty(self):
        """Test stats property on empty pool."""
        pool = CMLClientPool()
        stats = pool.stats
        assert stats["total_clients"] == 0
        assert stats["max_size"] == 50
        assert stats["clients"] == {}


class TestCMLClientPoolGetClient:
    """Test CMLClientPool.get_client() method."""

    @pytest.mark.asyncio
    async def test_get_client_creates_new_client(self):
        """Test that get_client creates a new client when none exists."""
        mock_client = create_mock_client()

        with patch("cml_mcp.cml_client.CMLClient", return_value=mock_client):
            pool = CMLClientPool()

            client = await pool.get_client(url="https://cml.example.com", username="user", password="pass", verify_ssl=False)

            assert client is mock_client
            assert len(pool._clients) == 1

    @pytest.mark.asyncio
    async def test_get_client_reuses_existing_client(self):
        """Test that get_client reuses existing client for same URL."""
        mock_client = create_mock_client()

        with patch("cml_mcp.cml_client.CMLClient", return_value=mock_client) as mock_cls:
            pool = CMLClientPool()

            # First call - creates client
            await pool.get_client(url="https://cml.example.com", username="user1", password="pass1", verify_ssl=False)

            # Second call - should reuse
            await pool.get_client(url="https://cml.example.com", username="user2", password="pass2", verify_ssl=False)

            # Should only create one client
            assert mock_cls.call_count == 1
            assert len(pool._clients) == 1
            # Active requests should be 2
            key = ("https://cml.example.com", False)
            assert pool._clients[key].active_requests == 2

    @pytest.mark.asyncio
    async def test_get_client_different_urls_create_different_clients(self):
        """Test that different URLs create different clients."""
        mock_client1 = create_mock_client()
        mock_client2 = create_mock_client()

        with patch("cml_mcp.cml_client.CMLClient", side_effect=[mock_client1, mock_client2]) as mock_cls:
            pool = CMLClientPool()

            await pool.get_client("https://cml1.example.com", "user", "pass", False)
            await pool.get_client("https://cml2.example.com", "user", "pass", False)

            assert mock_cls.call_count == 2
            assert len(pool._clients) == 2

    @pytest.mark.asyncio
    async def test_get_client_different_ssl_settings_create_different_clients(self):
        """Test that different SSL settings create different clients."""
        mock_client1 = create_mock_client()
        mock_client2 = create_mock_client()

        with patch("cml_mcp.cml_client.CMLClient", side_effect=[mock_client1, mock_client2]) as mock_cls:
            pool = CMLClientPool()

            await pool.get_client("https://cml.example.com", "user", "pass", verify_ssl=False)
            await pool.get_client("https://cml.example.com", "user", "pass", verify_ssl=True)

            assert mock_cls.call_count == 2
            assert len(pool._clients) == 2

    @pytest.mark.asyncio
    async def test_get_client_updates_credentials(self):
        """Test that get_client updates credentials on existing client."""
        mock_client = create_mock_client()

        with patch("cml_mcp.cml_client.CMLClient", return_value=mock_client):
            pool = CMLClientPool()

            # First call
            await pool.get_client("https://cml.example.com", "user1", "pass1", False)

            # Second call with different credentials
            await pool.get_client("https://cml.example.com", "user2", "pass2", False)

            # Credentials should be updated to user2
            assert mock_client.username == "user2"
            assert mock_client.password == "pass2"

    @pytest.mark.asyncio
    async def test_get_client_per_server_limit_exceeded(self):
        """Test that per-server limit raises error when exceeded."""
        mock_client = create_mock_client()

        with patch("cml_mcp.cml_client.CMLClient", return_value=mock_client):
            pool = CMLClientPool(max_per_server=2)

            # Get client twice (active_requests = 2)
            await pool.get_client("https://cml.example.com", "user", "pass", False)
            await pool.get_client("https://cml.example.com", "user", "pass", False)

            # Third call should fail
            with pytest.raises(McpError) as exc_info:
                await pool.get_client("https://cml.example.com", "user", "pass", False)

            assert "Too many concurrent requests" in str(exc_info.value.error.message)
            assert exc_info.value.error.code == -31004

    @pytest.mark.asyncio
    async def test_get_client_url_validation_failure(self):
        """Test that invalid URL raises error."""
        pool = CMLClientPool(allowed_urls=["https://allowed.example.com"])

        with pytest.raises(McpError) as exc_info:
            await pool.get_client("https://denied.example.com", "user", "pass", False)

        assert "not in allowlist" in str(exc_info.value.error.message)


class TestCMLClientPoolReleaseClient:
    """Test CMLClientPool.release_client() method."""

    @pytest.mark.asyncio
    async def test_release_client_decrements_active_requests(self):
        """Test that release_client decrements active_requests."""
        mock_client = create_mock_client()

        with patch("cml_mcp.cml_client.CMLClient", return_value=mock_client):
            pool = CMLClientPool()

            await pool.get_client("https://cml.example.com", "user", "pass", False)

            key = ("https://cml.example.com", False)
            assert pool._clients[key].active_requests == 1

            await pool.release_client("https://cml.example.com", False)
            assert pool._clients[key].active_requests == 0

    @pytest.mark.asyncio
    async def test_release_client_does_not_go_negative(self):
        """Test that active_requests doesn't go below 0."""
        mock_client = create_mock_client()

        with patch("cml_mcp.cml_client.CMLClient", return_value=mock_client):
            pool = CMLClientPool()

            await pool.get_client("https://cml.example.com", "user", "pass", False)

            key = ("https://cml.example.com", False)

            # Release twice
            await pool.release_client("https://cml.example.com", False)
            await pool.release_client("https://cml.example.com", False)

            assert pool._clients[key].active_requests == 0

    @pytest.mark.asyncio
    async def test_release_client_nonexistent_url_no_error(self):
        """Test that releasing nonexistent URL doesn't raise error."""
        pool = CMLClientPool()

        # Should not raise
        await pool.release_client("https://nonexistent.example.com", False)


class TestCMLClientPoolEviction:
    """Test CMLClientPool eviction logic."""

    @pytest.mark.asyncio
    async def test_lru_eviction_at_max_capacity(self):
        """Test that LRU client is evicted when pool is at capacity."""
        # Create unique mocks for each client
        mocks = [create_mock_client() for _ in range(3)]

        with patch("cml_mcp.cml_client.CMLClient", side_effect=mocks):
            pool = CMLClientPool(max_size=2)

            # Add two clients
            await pool.get_client("https://cml1.example.com", "user", "pass", False)
            await pool.release_client("https://cml1.example.com", False)

            await pool.get_client("https://cml2.example.com", "user", "pass", False)
            await pool.release_client("https://cml2.example.com", False)

            assert len(pool._clients) == 2

            # Add third client - should evict cml1 (LRU)
            await pool.get_client("https://cml3.example.com", "user", "pass", False)

            assert len(pool._clients) == 2
            assert ("https://cml1.example.com", False) not in pool._clients
            assert ("https://cml2.example.com", False) in pool._clients
            assert ("https://cml3.example.com", False) in pool._clients

            # First client should have been closed
            mocks[0].close.assert_called_once()

    @pytest.mark.asyncio
    async def test_ttl_eviction_expired_clients(self):
        """Test that expired clients are evicted."""
        mock1 = create_mock_client()
        mock2 = create_mock_client()

        with patch("cml_mcp.cml_client.CMLClient", side_effect=[mock1, mock2]):
            pool = CMLClientPool(ttl_seconds=1)  # 1 second TTL

            await pool.get_client("https://cml.example.com", "user", "pass", False)
            await pool.release_client("https://cml.example.com", False)

            # Manually set last_used to past
            key = ("https://cml.example.com", False)
            pool._clients[key].last_used = time.time() - 10  # 10 seconds ago

            # Trigger eviction by getting another client
            await pool.get_client("https://cml2.example.com", "user", "pass", False)

            # Original client should be evicted
            assert key not in pool._clients
            mock1.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_eviction_of_active_clients_during_ttl(self):
        """Test that clients with active requests are not evicted during TTL check."""
        mock1 = create_mock_client()
        mock2 = create_mock_client()

        with patch("cml_mcp.cml_client.CMLClient", side_effect=[mock1, mock2]):
            pool = CMLClientPool(ttl_seconds=1)

            await pool.get_client("https://cml.example.com", "user", "pass", False)
            # Don't release - keep active

            key = ("https://cml.example.com", False)
            pool._clients[key].last_used = time.time() - 10  # 10 seconds ago

            # Trigger eviction check
            await pool.get_client("https://cml2.example.com", "user", "pass", False)

            # Original client should NOT be evicted (has active request)
            assert key in pool._clients
            mock1.close.assert_not_called()


class TestCMLClientPoolCloseAll:
    """Test CMLClientPool.close_all() method."""

    @pytest.mark.asyncio
    async def test_close_all_closes_all_clients(self):
        """Test that close_all closes all pooled clients."""
        mocks = [create_mock_client() for _ in range(3)]

        with patch("cml_mcp.cml_client.CMLClient", side_effect=mocks):
            pool = CMLClientPool()

            await pool.get_client("https://cml1.example.com", "user", "pass", False)
            await pool.get_client("https://cml2.example.com", "user", "pass", False)
            await pool.get_client("https://cml3.example.com", "user", "pass", False)

            await pool.close_all()

            assert len(pool._clients) == 0
            for mock in mocks:
                mock.close.assert_called_once()


class TestGetCmlClient:
    """Test get_cml_client() helper function."""

    def test_get_cml_client_returns_context_var_client(self):
        """Test that get_cml_client returns client from ContextVar when set."""
        mock_client = create_mock_client()
        token = current_cml_client.set(mock_client)
        try:
            result = get_cml_client()
            assert result is mock_client
        finally:
            current_cml_client.reset(token)

    def test_get_cml_client_raises_when_no_client(self):
        """Test that get_cml_client raises RuntimeError when no client available."""
        current_cml_client.set(None)

        # Mock the server module import to return None for cml_client
        with patch.dict("sys.modules", {"cml_mcp.server": MagicMock(cml_client=None)}):
            with pytest.raises(RuntimeError, match="No CML client available"):
                get_cml_client()


class TestPoolStats:
    """Test pool statistics functionality."""

    @pytest.mark.asyncio
    async def test_stats_reflects_pool_state(self):
        """Test that stats property reflects current pool state."""
        mock_client1 = create_mock_client()
        mock_client2 = create_mock_client()

        with patch("cml_mcp.cml_client.CMLClient", side_effect=[mock_client1, mock_client2]):
            pool = CMLClientPool(max_size=10)

            await pool.get_client("https://cml1.example.com", "user", "pass", False)
            await pool.get_client("https://cml2.example.com", "user", "pass", True)

            stats = pool.stats

            assert stats["total_clients"] == 2
            assert stats["max_size"] == 10
            assert "https://cml1.example.com" in stats["clients"]
            assert "https://cml2.example.com" in stats["clients"]
            assert stats["clients"]["https://cml1.example.com"]["verify_ssl"] is False
            assert stats["clients"]["https://cml2.example.com"]["verify_ssl"] is True
            assert stats["clients"]["https://cml1.example.com"]["active_requests"] == 1
