# Copyright (c) 2025  Cisco Systems, Inc.
# All rights reserved.

"""End-to-end tests for multi-server functionality."""

from __future__ import annotations

import asyncio
import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cml_mcp.client_pool import CMLClientPool, current_cml_client, get_cml_client


class TestE2ERequestFlow:
    """End-to-end tests for complete request flow."""

    @pytest.fixture
    def mock_cml_client(self):
        """Create a comprehensive mock CMLClient."""
        client = MagicMock()
        client.username = "testuser"
        client.password = "testpass"
        client.base_url = "https://cml.example.com"
        client.token = None
        client.admin = None
        client.vclient = MagicMock()
        client.vclient.username = "testuser"
        client.vclient.password = "testpass"
        client.close = AsyncMock()
        client.get = AsyncMock(return_value=[])
        client.post = AsyncMock(return_value={"id": "test-lab-uuid"})
        client.put = AsyncMock()
        client.patch = AsyncMock()
        client.delete = AsyncMock()
        client.check_authentication = AsyncMock()
        client.is_admin = AsyncMock(return_value=False)
        return client

    @pytest.mark.asyncio
    async def test_complete_request_lifecycle(self, mock_cml_client):
        """Test complete lifecycle: auth -> get client -> use -> release."""
        with patch("cml_mcp.cml_client.CMLClient", return_value=mock_cml_client):
            pool = CMLClientPool()
            
            # Simulate middleware flow
            url = "https://cml.example.com"
            username = "testuser"
            password = "testpass"
            verify_ssl = False
            
            # 1. Get client from pool
            client = await pool.get_client(url, username, password, verify_ssl)
            assert client is mock_cml_client
            
            # 2. Set in ContextVar
            token = current_cml_client.set(client)
            
            try:
                # 3. Authenticate
                client.token = None
                client.admin = None
                await client.check_authentication()
                mock_cml_client.check_authentication.assert_called_once()
                
                # 4. Tool uses get_cml_client()
                tool_client = get_cml_client()
                assert tool_client is client
                
                # 5. Tool makes API call
                labs = await tool_client.get("/labs")
                mock_cml_client.get.assert_called_with("/labs")
                
            finally:
                # 6. Cleanup
                await pool.release_client(url, verify_ssl)
                current_cml_client.reset(token)
            
            # Verify cleanup
            assert current_cml_client.get() is None
            key = (url, verify_ssl)
            assert pool._clients[key].active_requests == 0

    @pytest.mark.asyncio
    async def test_multiple_requests_different_servers(self, mock_cml_client):
        """Test handling multiple requests to different CML servers."""
        clients = {}
        
        def create_client(**kwargs):
            url = kwargs.get("host", "unknown")
            client = MagicMock()
            client.username = kwargs.get("username")
            client.password = kwargs.get("password")
            client.base_url = url
            client.vclient = MagicMock()
            client.vclient.username = kwargs.get("username")
            client.vclient.password = kwargs.get("password")
            client.close = AsyncMock()
            client.get = AsyncMock(return_value={"server": url})
            clients[url] = client
            return client
        
        with patch("cml_mcp.cml_client.CMLClient", side_effect=create_client):
            pool = CMLClientPool()
            
            # Request to Server 1
            client1 = await pool.get_client("https://cml1.example.com", "user1", "pass1", False)
            token1 = current_cml_client.set(client1)
            
            try:
                result1 = await get_cml_client().get("/labs")
                assert result1["server"] == "https://cml1.example.com"
            finally:
                await pool.release_client("https://cml1.example.com", False)
                current_cml_client.reset(token1)
            
            # Request to Server 2
            client2 = await pool.get_client("https://cml2.example.com", "user2", "pass2", False)
            token2 = current_cml_client.set(client2)
            
            try:
                result2 = await get_cml_client().get("/labs")
                assert result2["server"] == "https://cml2.example.com"
            finally:
                await pool.release_client("https://cml2.example.com", False)
                current_cml_client.reset(token2)
            
            # Both clients should be in pool
            assert len(pool._clients) == 2

    @pytest.mark.asyncio
    async def test_request_with_url_validation(self, mock_cml_client):
        """Test request flow with URL validation."""
        with patch("cml_mcp.cml_client.CMLClient", return_value=mock_cml_client):
            # Pool with allowlist
            pool = CMLClientPool(
                allowed_urls=["https://allowed1.example.com", "https://allowed2.example.com"]
            )
            
            # Allowed URL should work
            client = await pool.get_client("https://allowed1.example.com", "user", "pass", False)
            assert client is mock_cml_client
            await pool.release_client("https://allowed1.example.com", False)
            
            # Denied URL should fail
            from mcp.shared.exceptions import McpError
            with pytest.raises(McpError) as exc_info:
                await pool.get_client("https://denied.example.com", "user", "pass", False)
            assert "not in allowlist" in str(exc_info.value.error.message)

    @pytest.mark.asyncio
    async def test_request_with_pattern_validation(self, mock_cml_client):
        """Test request flow with URL pattern validation."""
        with patch("cml_mcp.cml_client.CMLClient", return_value=mock_cml_client):
            # Pool with pattern
            pool = CMLClientPool(
                url_pattern=r"^https://cml[0-9]+\.corp\.example\.com$"
            )
            
            # Matching pattern should work
            client = await pool.get_client("https://cml1.corp.example.com", "user", "pass", False)
            assert client is mock_cml_client
            await pool.release_client("https://cml1.corp.example.com", False)
            
            # Non-matching pattern should fail
            from mcp.shared.exceptions import McpError
            with pytest.raises(McpError) as exc_info:
                await pool.get_client("https://cml.other.com", "user", "pass", False)
            assert "does not match allowed pattern" in str(exc_info.value.error.message)


class TestE2EErrorHandling:
    """End-to-end tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_error_during_request_still_releases_client(self):
        """Test that client is released even when request fails."""
        mock_client = MagicMock()
        mock_client.vclient = MagicMock()
        mock_client.close = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("API Error"))
        
        with patch("cml_mcp.cml_client.CMLClient", return_value=mock_client):
            pool = CMLClientPool()
            
            url = "https://cml.example.com"
            client = await pool.get_client(url, "user", "pass", False)
            token = current_cml_client.set(client)
            
            try:
                try:
                    await get_cml_client().get("/labs")
                except Exception:
                    pass  # Expected error
            finally:
                await pool.release_client(url, False)
                current_cml_client.reset(token)
            
            # Client should be released despite error
            key = (url, False)
            assert pool._clients[key].active_requests == 0

    @pytest.mark.asyncio
    async def test_concurrent_request_limit_handling(self):
        """Test handling of concurrent request limits."""
        mock_client = MagicMock()
        mock_client.vclient = MagicMock()
        mock_client.close = AsyncMock()
        
        with patch("cml_mcp.cml_client.CMLClient", return_value=mock_client):
            pool = CMLClientPool(max_per_server=2)
            
            url = "https://cml.example.com"
            
            # Acquire 2 clients (limit)
            client1 = await pool.get_client(url, "user", "pass", False)
            client2 = await pool.get_client(url, "user", "pass", False)
            
            # Third should fail
            from mcp.shared.exceptions import McpError
            with pytest.raises(McpError) as exc_info:
                await pool.get_client(url, "user", "pass", False)
            assert "Too many concurrent requests" in str(exc_info.value.error.message)
            
            # Release one
            await pool.release_client(url, False)
            
            # Now should succeed
            client3 = await pool.get_client(url, "user", "pass", False)
            assert client3 is mock_client


class TestE2EBackwardCompatibility:
    """Test backward compatibility with stdio mode."""

    def test_stdio_mode_uses_global_client(self):
        """Test that stdio mode uses global client via get_cml_client()."""
        # Ensure ContextVar is None (as it would be in stdio mode)
        current_cml_client.set(None)
        
        mock_global = MagicMock(name="global_stdio_client")
        
        # Mock the server module
        import sys
        mock_server = MagicMock()
        mock_server.cml_client = mock_global
        sys.modules["cml_mcp.server"] = mock_server
        
        try:
            client = get_cml_client()
            assert client is mock_global
        finally:
            del sys.modules["cml_mcp.server"]

    def test_http_mode_ignores_global_client(self):
        """Test that HTTP mode uses ContextVar client, not global."""
        mock_context = MagicMock(name="http_context_client")
        mock_global = MagicMock(name="global_client")
        
        # Set ContextVar
        token = current_cml_client.set(mock_context)
        
        try:
            client = get_cml_client()
            # Should use context client, not global
            assert client is mock_context
            assert client is not mock_global
        finally:
            current_cml_client.reset(token)


class TestE2EPoolEviction:
    """End-to-end tests for pool eviction scenarios."""

    @pytest.mark.asyncio
    async def test_lru_eviction_preserves_active_clients(self):
        """Test that LRU eviction doesn't evict clients with active requests."""
        clients = []
        
        def create_client(**kwargs):
            client = MagicMock()
            client.vclient = MagicMock()
            client.close = AsyncMock()
            clients.append(client)
            return client
        
        with patch("cml_mcp.cml_client.CMLClient", side_effect=create_client):
            pool = CMLClientPool(max_size=2)
            
            # Get client 1 and keep it active
            url1 = "https://cml1.example.com"
            client1 = await pool.get_client(url1, "user", "pass", False)
            # Don't release - keep active
            
            # Get client 2 and release
            url2 = "https://cml2.example.com"
            client2 = await pool.get_client(url2, "user", "pass", False)
            await pool.release_client(url2, False)
            
            # Get client 3 - should evict client2 (not client1 which is active)
            url3 = "https://cml3.example.com"
            client3 = await pool.get_client(url3, "user", "pass", False)
            
            # Client1 should still be in pool
            assert (url1, False) in pool._clients
            # Client2 should be evicted
            assert (url2, False) not in pool._clients
            # Client3 should be in pool
            assert (url3, False) in pool._clients

    @pytest.mark.asyncio
    async def test_pool_cleanup_on_shutdown(self):
        """Test that close_all properly cleans up all clients."""
        clients = []
        
        def create_client(**kwargs):
            client = MagicMock()
            client.vclient = MagicMock()
            client.close = AsyncMock()
            clients.append(client)
            return client
        
        with patch("cml_mcp.cml_client.CMLClient", side_effect=create_client):
            pool = CMLClientPool()
            
            # Create multiple clients
            await pool.get_client("https://cml1.example.com", "user", "pass", False)
            await pool.get_client("https://cml2.example.com", "user", "pass", False)
            await pool.get_client("https://cml3.example.com", "user", "pass", False)
            
            assert len(pool._clients) == 3
            
            # Shutdown
            await pool.close_all()
            
            # All should be closed and cleared
            assert len(pool._clients) == 0
            for client in clients:
                client.close.assert_called_once()


class TestE2EHeaderParsing:
    """End-to-end tests for HTTP header parsing scenarios."""

    def test_auth_header_with_special_characters_in_password(self):
        """Test parsing credentials with special characters."""
        # Password with special chars: P@ss:word!#$
        username = "admin"
        password = "P@ss:word!#$"
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        header = f"Basic {credentials}"
        
        parts = header.split(" ", 1)
        decoded = base64.b64decode(parts[1]).decode("utf-8")
        parsed_user, parsed_pass = decoded.split(":", 1)
        
        assert parsed_user == username
        assert parsed_pass == password

    def test_auth_header_with_unicode_characters(self):
        """Test parsing credentials with unicode characters."""
        username = "用户"
        password = "密码123"
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        header = f"Basic {credentials}"
        
        parts = header.split(" ", 1)
        decoded = base64.b64decode(parts[1]).decode("utf-8")
        parsed_user, parsed_pass = decoded.split(":", 1)
        
        assert parsed_user == username
        assert parsed_pass == password

    def test_url_header_normalization_cases(self):
        """Test various URL normalization edge cases."""
        pool = CMLClientPool()
        
        test_cases = [
            ("https://CML.EXAMPLE.COM", "https://cml.example.com"),
            ("https://cml.example.com:443", "https://cml.example.com"),
            ("http://cml.example.com:80", "http://cml.example.com"),
            ("https://cml.example.com:8443", "https://cml.example.com:8443"),
            ("https://cml.example.com/", "https://cml.example.com"),
            ("https://192.168.1.100:443", "https://192.168.1.100"),
            ("https://192.168.1.100:8443", "https://192.168.1.100:8443"),
        ]
        
        for input_url, expected in test_cases:
            result = pool._normalize_url(input_url)
            assert result == expected, f"Failed for {input_url}: got {result}, expected {expected}"
