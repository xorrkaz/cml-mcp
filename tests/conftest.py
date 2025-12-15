# Copyright (c) 2025  Cisco Systems, Inc.
# All rights reserved.

"""Shared test fixtures for cml-mcp tests."""

from __future__ import annotations

from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_cml_client() -> MagicMock:
    """Create a mock CMLClient for testing."""
    client = MagicMock()
    client.username = "testuser"
    client.password = "testpass"
    client.base_url = "https://cml.example.com"
    client.api_base = "https://cml.example.com/api/v0"
    client.token = None
    client.admin = None
    client.vclient = MagicMock()
    client.vclient.username = "testuser"
    client.vclient.password = "testpass"
    client.close = AsyncMock()
    client.get = AsyncMock(return_value={})
    client.post = AsyncMock(return_value={})
    client.put = AsyncMock(return_value={})
    client.patch = AsyncMock(return_value={})
    client.delete = AsyncMock(return_value={})
    client.check_authentication = AsyncMock()
    client.is_admin = AsyncMock(return_value=False)
    return client


@pytest.fixture
def mock_cml_client_factory(mock_cml_client: MagicMock) -> Generator[MagicMock, None, None]:
    """Patch CMLClient constructor to return a mock."""
    # Patch at cml_mcp.cml_client since that's where it's imported from
    with patch("cml_mcp.cml_client.CMLClient") as mock_cls:
        mock_cls.return_value = mock_cml_client
        yield mock_cls


@pytest.fixture
def sample_urls() -> dict[str, str]:
    """Sample URLs for testing."""
    return {
        "server1": "https://cml1.example.com",
        "server2": "https://cml2.example.com",
        "server3": "https://cml3.example.com:8443",
        "with_port": "https://cml.example.com:443",
        "http": "http://cml.example.com",
        "with_path": "https://cml.example.com/api",
        "uppercase": "HTTPS://CML.EXAMPLE.COM",
    }


@pytest.fixture
def sample_credentials() -> dict[str, str]:
    """Sample credentials for testing."""
    return {
        "username": "testuser",
        "password": "testpassword",
    }
