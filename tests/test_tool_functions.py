# Copyright (c) 2025  Cisco Systems, Inc.
# All rights reserved.

"""Tests for tool functions using get_cml_client()."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cml_mcp.client_pool import current_cml_client, get_cml_client


class TestToolFunctionsUseGetCmlClient:
    """Test that tool functions correctly use get_cml_client()."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock CMLClient."""
        client = MagicMock()
        client.get = AsyncMock(return_value=[])
        client.post = AsyncMock(return_value={"id": "test-uuid"})
        client.put = AsyncMock()
        client.patch = AsyncMock()
        client.delete = AsyncMock()
        client.is_admin = AsyncMock(return_value=True)
        return client

    @pytest.fixture
    def set_mock_client(self, mock_client):
        """Set mock client in ContextVar."""
        token = current_cml_client.set(mock_client)
        yield mock_client
        current_cml_client.reset(token)

    def test_get_cml_client_returns_context_client(self, set_mock_client):
        """Test that get_cml_client returns the ContextVar client."""
        client = get_cml_client()
        assert client is set_mock_client

    @pytest.mark.asyncio
    async def test_tool_uses_context_client_for_get(self, set_mock_client):
        """Test that tool GET operations use the context client."""
        client = get_cml_client()
        await client.get("/labs")
        
        set_mock_client.get.assert_called_once_with("/labs")

    @pytest.mark.asyncio
    async def test_tool_uses_context_client_for_post(self, set_mock_client):
        """Test that tool POST operations use the context client."""
        client = get_cml_client()
        data = {"title": "Test Lab"}
        await client.post("/labs", data=data)
        
        set_mock_client.post.assert_called_once_with("/labs", data=data)

    @pytest.mark.asyncio
    async def test_tool_uses_context_client_for_put(self, set_mock_client):
        """Test that tool PUT operations use the context client."""
        client = get_cml_client()
        await client.put("/labs/test-uuid/start")
        
        set_mock_client.put.assert_called_once_with("/labs/test-uuid/start")

    @pytest.mark.asyncio
    async def test_tool_uses_context_client_for_patch(self, set_mock_client):
        """Test that tool PATCH operations use the context client."""
        client = get_cml_client()
        data = {"title": "Updated Title"}
        await client.patch("/labs/test-uuid", data=data)
        
        set_mock_client.patch.assert_called_once_with("/labs/test-uuid", data=data)

    @pytest.mark.asyncio
    async def test_tool_uses_context_client_for_delete(self, set_mock_client):
        """Test that tool DELETE operations use the context client."""
        client = get_cml_client()
        await client.delete("/labs/test-uuid")
        
        set_mock_client.delete.assert_called_once_with("/labs/test-uuid")


class TestToolFunctionPatterns:
    """Test common patterns used in tool functions."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock CMLClient."""
        client = MagicMock()
        client.get = AsyncMock()
        client.post = AsyncMock()
        client.put = AsyncMock()
        client.patch = AsyncMock()
        client.delete = AsyncMock()
        client.is_admin = AsyncMock(return_value=False)
        return client

    @pytest.fixture
    def admin_client(self):
        """Create a mock admin CMLClient."""
        client = MagicMock()
        client.get = AsyncMock()
        client.post = AsyncMock(return_value={"id": "new-uuid"})
        client.is_admin = AsyncMock(return_value=True)
        return client

    @pytest.mark.asyncio
    async def test_admin_check_pattern(self, mock_client):
        """Test the admin check pattern used in tools."""
        token = current_cml_client.set(mock_client)
        try:
            client = get_cml_client()
            
            # Pattern: Check if admin before proceeding
            is_admin = await client.is_admin()
            
            assert is_admin is False
            mock_client.is_admin.assert_called_once()
        finally:
            current_cml_client.reset(token)

    @pytest.mark.asyncio
    async def test_create_resource_pattern(self, admin_client):
        """Test the create resource pattern used in tools."""
        token = current_cml_client.set(admin_client)
        try:
            client = get_cml_client()
            
            # Pattern: Create and return ID
            data = {"name": "test-resource"}
            resp = await client.post("/resources", data=data)
            resource_id = resp["id"]
            
            assert resource_id == "new-uuid"
            admin_client.post.assert_called_once_with("/resources", data=data)
        finally:
            current_cml_client.reset(token)

    @pytest.mark.asyncio
    async def test_list_resources_pattern(self, mock_client):
        """Test the list resources pattern used in tools."""
        mock_client.get.return_value = [
            {"id": "uuid1", "name": "resource1"},
            {"id": "uuid2", "name": "resource2"},
        ]
        
        token = current_cml_client.set(mock_client)
        try:
            client = get_cml_client()
            
            # Pattern: Get list of resources
            resources = await client.get("/resources")
            
            assert len(resources) == 2
            mock_client.get.assert_called_once_with("/resources")
        finally:
            current_cml_client.reset(token)

    @pytest.mark.asyncio
    async def test_get_with_params_pattern(self, mock_client):
        """Test the GET with params pattern used in tools."""
        mock_client.get.return_value = {"detailed": "data"}
        
        token = current_cml_client.set(mock_client)
        try:
            client = get_cml_client()
            
            # Pattern: GET with query parameters
            result = await client.get("/labs/uuid/nodes", params={"data": True, "operational": True})
            
            assert result == {"detailed": "data"}
            mock_client.get.assert_called_once_with("/labs/uuid/nodes", params={"data": True, "operational": True})
        finally:
            current_cml_client.reset(token)


class TestStdioModeFallback:
    """Test fallback to global client in stdio mode."""

    def test_fallback_to_global_client(self):
        """Test that get_cml_client falls back to global when ContextVar is None."""
        # Ensure ContextVar is None
        current_cml_client.set(None)
        
        mock_global = MagicMock()
        
        # Patch the import inside get_cml_client
        with patch.object(
            __import__("cml_mcp.client_pool", fromlist=["get_cml_client"]),
            "cml_client",
            mock_global,
            create=True
        ):
            # We need to patch at the server module level
            import sys
            mock_server = MagicMock()
            mock_server.cml_client = mock_global
            sys.modules["cml_mcp.server"] = mock_server
            
            try:
                result = get_cml_client()
                assert result is mock_global
            finally:
                del sys.modules["cml_mcp.server"]

    def test_context_client_takes_precedence(self):
        """Test that ContextVar client takes precedence over global."""
        mock_context = MagicMock(name="context_client")
        mock_global = MagicMock(name="global_client")
        
        token = current_cml_client.set(mock_context)
        try:
            # Even if global exists, context client should be returned
            result = get_cml_client()
            assert result is mock_context
            assert result is not mock_global
        finally:
            current_cml_client.reset(token)


class TestClientCredentialUpdates:
    """Test that client credentials are properly updated per request."""

    @pytest.mark.asyncio
    async def test_credentials_updated_on_reuse(self, mock_cml_client_factory, mock_cml_client):
        """Test that credentials are updated when client is reused."""
        from cml_mcp.client_pool import CMLClientPool
        
        mock_cml_client_factory.return_value = mock_cml_client
        
        pool = CMLClientPool()
        
        # First request with user1
        await pool.get_client("https://cml.example.com", "user1", "pass1", False)
        assert mock_cml_client.username == "user1"
        assert mock_cml_client.password == "pass1"
        assert mock_cml_client.vclient.username == "user1"
        assert mock_cml_client.vclient.password == "pass1"
        await pool.release_client("https://cml.example.com", False)
        
        # Second request with user2 - should update credentials
        await pool.get_client("https://cml.example.com", "user2", "pass2", False)
        assert mock_cml_client.username == "user2"
        assert mock_cml_client.password == "pass2"
        assert mock_cml_client.vclient.username == "user2"
        assert mock_cml_client.vclient.password == "pass2"
