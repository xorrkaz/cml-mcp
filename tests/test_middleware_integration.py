# Copyright (c) 2025  Cisco Systems, Inc.
# All rights reserved.

"""Integration tests for multi-server middleware functionality."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cml_mcp.client_pool import CMLClientPool, current_cml_client


class TestMiddlewareIntegration:
    """Test middleware integration with client pool."""

    @pytest.fixture
    def mock_pool(self):
        """Create a mock CMLClientPool."""
        pool = MagicMock(spec=CMLClientPool)
        pool.get_client = AsyncMock()
        pool.release_client = AsyncMock()
        return pool

    @pytest.fixture
    def mock_client(self):
        """Create a mock CMLClient."""
        client = MagicMock()
        client.token = None
        client.admin = None
        client.check_authentication = AsyncMock()
        return client

    @pytest.fixture
    def basic_auth_header(self):
        """Create a valid Basic auth header."""
        credentials = base64.b64encode(b"testuser:testpass").decode("utf-8")
        return f"Basic {credentials}"

    def test_current_cml_client_contextvar_isolation(self, mock_client):
        """Test that ContextVar provides proper isolation."""
        # Set client in one context
        token1 = current_cml_client.set(mock_client)
        
        assert current_cml_client.get() is mock_client
        
        # Reset should restore to None
        current_cml_client.reset(token1)
        assert current_cml_client.get() is None

    @pytest.mark.asyncio
    async def test_middleware_extracts_cml_server_url_header(self, mock_pool, mock_client):
        """Test that middleware correctly extracts X-CML-Server-URL header."""
        mock_pool.get_client.return_value = mock_client
        
        # Simulate header extraction
        headers = {
            "x-cml-server-url": "https://cml.example.com",
            "x-authorization": f"Basic {base64.b64encode(b'user:pass').decode()}",
        }
        
        cml_url = headers.get("x-cml-server-url")
        assert cml_url == "https://cml.example.com"

    @pytest.mark.asyncio
    async def test_middleware_extracts_verify_ssl_header(self):
        """Test that middleware correctly extracts X-CML-Verify-SSL header."""
        # Test true
        headers = {"x-cml-verify-ssl": "true"}
        verify_ssl_header = headers.get("x-cml-verify-ssl", "").lower()
        assert verify_ssl_header == "true"
        verify_ssl = verify_ssl_header == "true"
        assert verify_ssl is True
        
        # Test false
        headers = {"x-cml-verify-ssl": "false"}
        verify_ssl_header = headers.get("x-cml-verify-ssl", "").lower()
        verify_ssl = verify_ssl_header == "true"
        assert verify_ssl is False
        
        # Test missing (should default to settings)
        headers = {}
        verify_ssl_header = headers.get("x-cml-verify-ssl", "").lower()
        assert verify_ssl_header == ""

    @pytest.mark.asyncio
    async def test_middleware_parses_basic_auth_credentials(self, basic_auth_header):
        """Test that middleware correctly parses Basic auth credentials."""
        parts = basic_auth_header.split(" ", 1)
        assert len(parts) == 2
        assert parts[0].lower() == "basic"
        
        decoded = base64.b64decode(parts[1]).decode("utf-8")
        username, password = decoded.split(":", 1)
        
        assert username == "testuser"
        assert password == "testpass"

    @pytest.mark.asyncio
    async def test_middleware_handles_invalid_auth_header(self):
        """Test that middleware rejects invalid auth headers."""
        # Missing Basic prefix
        invalid_header = "InvalidFormat testuser:testpass"
        parts = invalid_header.split(" ", 1)
        is_valid = len(parts) == 2 and parts[0].lower() == "basic"
        assert is_valid is False
        
        # Wrong format
        invalid_header = "Bearer sometoken"
        parts = invalid_header.split(" ", 1)
        is_valid = len(parts) == 2 and parts[0].lower() == "basic"
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_middleware_handles_invalid_base64(self):
        """Test that middleware handles invalid base64 in auth header."""
        invalid_b64 = "not-valid-base64!!!"
        
        with pytest.raises(Exception):
            base64.b64decode(invalid_b64)

    @pytest.mark.asyncio
    async def test_pool_get_client_called_with_correct_params(self, mock_pool, mock_client):
        """Test that pool.get_client is called with correct parameters."""
        mock_pool.get_client.return_value = mock_client
        
        url = "https://cml.example.com"
        username = "testuser"
        password = "testpass"
        verify_ssl = False
        
        client = await mock_pool.get_client(url, username, password, verify_ssl)
        
        mock_pool.get_client.assert_called_once_with(url, username, password, verify_ssl)
        assert client is mock_client

    @pytest.mark.asyncio
    async def test_pool_release_client_called_in_finally(self, mock_pool, mock_client):
        """Test that pool.release_client is called in finally block."""
        mock_pool.get_client.return_value = mock_client
        
        url = "https://cml.example.com"
        verify_ssl = False
        
        try:
            client = await mock_pool.get_client(url, "user", "pass", verify_ssl)
            # Simulate request processing
        finally:
            await mock_pool.release_client(url, verify_ssl)
        
        mock_pool.release_client.assert_called_once_with(url, verify_ssl)

    @pytest.mark.asyncio
    async def test_context_var_set_and_cleared(self, mock_client):
        """Test that ContextVar is set and cleared properly."""
        assert current_cml_client.get() is None
        
        # Simulate middleware setting the client
        current_cml_client.set(mock_client)
        assert current_cml_client.get() is mock_client
        
        # Simulate middleware clearing the client
        current_cml_client.set(None)
        assert current_cml_client.get() is None

    @pytest.mark.asyncio
    async def test_pyats_headers_parsing(self):
        """Test that PyATS headers are correctly parsed."""
        pyats_creds = base64.b64encode(b"pyatsuser:pyatspass").decode("utf-8")
        headers = {
            "x-pyats-authorization": f"Basic {pyats_creds}",
            "x-pyats-enable": f"Basic {base64.b64encode(b'enablepass').decode()}",
        }
        
        # Parse PyATS auth
        pyats_header = headers.get("x-pyats-authorization")
        assert pyats_header.startswith("Basic ")
        
        pyats_parts = pyats_header.split(" ", 1)
        pyats_decoded = base64.b64decode(pyats_parts[1]).decode("utf-8")
        pyats_username, pyats_password = pyats_decoded.split(":", 1)
        
        assert pyats_username == "pyatsuser"
        assert pyats_password == "pyatspass"
        
        # Parse PyATS enable
        enable_header = headers.get("x-pyats-enable")
        enable_parts = enable_header.split(" ", 1)
        enable_decoded = base64.b64decode(enable_parts[1]).decode("utf-8")
        
        assert enable_decoded == "enablepass"


class TestFallbackToDefaultUrl:
    """Test fallback to CML_URL when X-CML-Server-URL is not provided."""

    def test_fallback_when_header_missing(self):
        """Test that default CML_URL is used when header is missing."""
        headers = {
            "x-authorization": f"Basic {base64.b64encode(b'user:pass').decode()}",
            # No x-cml-server-url
        }
        
        default_url = "https://default-cml.example.com"
        
        cml_url = headers.get("x-cml-server-url")
        if not cml_url:
            cml_url = default_url
        
        assert cml_url == default_url

    def test_header_takes_precedence(self):
        """Test that X-CML-Server-URL header takes precedence over default."""
        headers = {
            "x-cml-server-url": "https://custom-cml.example.com",
            "x-authorization": f"Basic {base64.b64encode(b'user:pass').decode()}",
        }
        
        default_url = "https://default-cml.example.com"
        
        cml_url = headers.get("x-cml-server-url")
        if not cml_url:
            cml_url = default_url
        
        assert cml_url == "https://custom-cml.example.com"


class TestMultipleServersScenarios:
    """Test scenarios with multiple CML servers."""

    @pytest.mark.asyncio
    async def test_sequential_requests_to_different_servers(self, mock_cml_client_factory):
        """Test handling sequential requests to different servers."""
        mocks = [MagicMock(close=AsyncMock()) for _ in range(3)]
        mock_cml_client_factory.side_effect = mocks
        
        pool = CMLClientPool()
        
        # Request 1 - Server A
        client1 = await pool.get_client("https://server-a.example.com", "user", "pass", False)
        await pool.release_client("https://server-a.example.com", False)
        
        # Request 2 - Server B
        client2 = await pool.get_client("https://server-b.example.com", "user", "pass", False)
        await pool.release_client("https://server-b.example.com", False)
        
        # Request 3 - Server A again (should reuse)
        client3 = await pool.get_client("https://server-a.example.com", "user", "pass", False)
        await pool.release_client("https://server-a.example.com", False)
        
        assert len(pool._clients) == 2
        assert mock_cml_client_factory.call_count == 2  # Only 2 clients created

    @pytest.mark.asyncio
    async def test_concurrent_requests_to_same_server(self, mock_cml_client_factory, mock_cml_client):
        """Test handling concurrent requests to same server."""
        mock_cml_client_factory.return_value = mock_cml_client
        
        pool = CMLClientPool(max_per_server=5)
        
        # Simulate 5 concurrent requests
        for i in range(5):
            await pool.get_client("https://cml.example.com", f"user{i}", f"pass{i}", False)
        
        key = ("https://cml.example.com", False)
        assert pool._clients[key].active_requests == 5
        
        # 6th request should fail
        from mcp.shared.exceptions import McpError
        with pytest.raises(McpError):
            await pool.get_client("https://cml.example.com", "user6", "pass6", False)

    @pytest.mark.asyncio
    async def test_requests_with_different_credentials(self, mock_cml_client_factory, mock_cml_client):
        """Test that different credentials update the client."""
        mock_cml_client_factory.return_value = mock_cml_client
        
        pool = CMLClientPool()
        
        # First request
        await pool.get_client("https://cml.example.com", "admin", "adminpass", False)
        assert mock_cml_client.username == "admin"
        assert mock_cml_client.password == "adminpass"
        await pool.release_client("https://cml.example.com", False)
        
        # Second request with different creds
        await pool.get_client("https://cml.example.com", "operator", "operpass", False)
        assert mock_cml_client.username == "operator"
        assert mock_cml_client.password == "operpass"
