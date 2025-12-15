# Copyright (c) 2025  Cisco Systems, Inc.
# All rights reserved.

"""Unit tests for settings.py - multi-server configuration fields.

These tests focus on the Settings class directly without module-level
reload, which is problematic due to the module-level validation code.
"""

from __future__ import annotations


class TestMultiServerSettingsDefaults:
    """Test the default values for multi-server configuration fields."""

    def test_default_pool_max_size(self):
        """Test default value for cml_pool_max_size is 50."""
        from cml_mcp.settings import Settings

        # Create settings with minimal required fields
        s = Settings(cml_url="https://cml.example.com")
        assert s.cml_pool_max_size == 50

    def test_default_pool_ttl_seconds(self):
        """Test default value for cml_pool_ttl_seconds is 300."""
        from cml_mcp.settings import Settings

        s = Settings(cml_url="https://cml.example.com")
        assert s.cml_pool_ttl_seconds == 300

    def test_default_pool_max_per_server(self):
        """Test default value for cml_pool_max_per_server is 5."""
        from cml_mcp.settings import Settings

        s = Settings(cml_url="https://cml.example.com")
        assert s.cml_pool_max_per_server == 5

    def test_default_allowed_urls_empty(self):
        """Test default value for cml_allowed_urls is empty list."""
        from cml_mcp.settings import Settings

        s = Settings(cml_url="https://cml.example.com")
        assert s.cml_allowed_urls == []

    def test_default_url_pattern_none(self):
        """Test default value for cml_url_pattern is None."""
        from cml_mcp.settings import Settings

        s = Settings(cml_url="https://cml.example.com")
        assert s.cml_url_pattern is None


class TestMultiServerSettingsCustomValues:
    """Test custom values for multi-server configuration fields."""

    def test_custom_pool_max_size(self):
        """Test custom value for cml_pool_max_size."""
        from cml_mcp.settings import Settings

        s = Settings(
            cml_url="https://cml.example.com",
            cml_pool_max_size=100,
        )
        assert s.cml_pool_max_size == 100

    def test_custom_pool_ttl_seconds(self):
        """Test custom value for cml_pool_ttl_seconds."""
        from cml_mcp.settings import Settings

        s = Settings(
            cml_url="https://cml.example.com",
            cml_pool_ttl_seconds=600,
        )
        assert s.cml_pool_ttl_seconds == 600

    def test_custom_pool_max_per_server(self):
        """Test custom value for cml_pool_max_per_server."""
        from cml_mcp.settings import Settings

        s = Settings(
            cml_url="https://cml.example.com",
            cml_pool_max_per_server=10,
        )
        assert s.cml_pool_max_per_server == 10

    def test_custom_allowed_urls(self):
        """Test custom value for cml_allowed_urls."""
        from cml_mcp.settings import Settings

        s = Settings(
            cml_url="https://cml.example.com",
            cml_allowed_urls=[
                "https://cml1.example.com",
                "https://cml2.example.com",
            ],
        )
        assert len(s.cml_allowed_urls) == 2
        # AnyHttpUrl normalizes URLs
        assert str(s.cml_allowed_urls[0]) == "https://cml1.example.com/"
        assert str(s.cml_allowed_urls[1]) == "https://cml2.example.com/"

    def test_custom_url_pattern(self):
        """Test custom value for cml_url_pattern."""
        from cml_mcp.settings import Settings

        pattern = r"^https://cml[0-9]+\.example\.com$"
        s = Settings(
            cml_url="https://cml.example.com",
            cml_url_pattern=pattern,
        )
        assert s.cml_url_pattern == pattern


class TestSettingsFieldCombinations:
    """Test combinations of settings fields."""

    def test_all_pool_settings_together(self):
        """Test setting all pool configuration together."""
        from cml_mcp.settings import Settings

        s = Settings(
            cml_url="https://cml.example.com",
            cml_pool_max_size=200,
            cml_pool_ttl_seconds=900,
            cml_pool_max_per_server=20,
        )
        assert s.cml_pool_max_size == 200
        assert s.cml_pool_ttl_seconds == 900
        assert s.cml_pool_max_per_server == 20

    def test_url_restrictions_together(self):
        """Test both URL restriction methods together."""
        from cml_mcp.settings import Settings

        s = Settings(
            cml_url="https://cml.example.com",
            cml_allowed_urls=["https://cml1.example.com"],
            cml_url_pattern=r"^https://cml.*\.example\.com$",
        )
        assert len(s.cml_allowed_urls) == 1
        assert s.cml_url_pattern is not None


class TestSettingsTransportModes:
    """Test settings interaction with transport modes."""

    def test_http_transport_mode(self):
        """Test HTTP transport mode settings."""
        from cml_mcp.settings import Settings, TransportEnum

        s = Settings(
            cml_url="https://cml.example.com",
            cml_mcp_transport=TransportEnum.HTTP,
        )
        assert s.cml_mcp_transport == TransportEnum.HTTP

    def test_stdio_transport_mode(self):
        """Test STDIO transport mode settings."""
        from cml_mcp.settings import Settings, TransportEnum

        s = Settings(
            cml_url="https://cml.example.com",
            cml_mcp_transport=TransportEnum.STDIO,
            cml_username="testuser",
            cml_password="testpass",
        )
        assert s.cml_mcp_transport == TransportEnum.STDIO


class TestSettingsFieldTypes:
    """Test that settings fields have correct types."""

    def test_pool_max_size_is_int(self):
        """Test cml_pool_max_size is integer."""
        from cml_mcp.settings import Settings

        s = Settings(cml_url="https://cml.example.com")
        assert isinstance(s.cml_pool_max_size, int)

    def test_pool_ttl_seconds_is_int(self):
        """Test cml_pool_ttl_seconds is integer."""
        from cml_mcp.settings import Settings

        s = Settings(cml_url="https://cml.example.com")
        assert isinstance(s.cml_pool_ttl_seconds, int)

    def test_pool_max_per_server_is_int(self):
        """Test cml_pool_max_per_server is integer."""
        from cml_mcp.settings import Settings

        s = Settings(cml_url="https://cml.example.com")
        assert isinstance(s.cml_pool_max_per_server, int)

    def test_allowed_urls_is_list(self):
        """Test cml_allowed_urls is list."""
        from cml_mcp.settings import Settings

        s = Settings(cml_url="https://cml.example.com")
        assert isinstance(s.cml_allowed_urls, list)

    def test_url_pattern_is_string_or_none(self):
        """Test cml_url_pattern is string or None."""
        from cml_mcp.settings import Settings

        s = Settings(cml_url="https://cml.example.com")
        assert s.cml_url_pattern is None or isinstance(s.cml_url_pattern, str)
