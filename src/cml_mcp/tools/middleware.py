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

"""
Middleware module for HTTP request handling and ACL management.
"""

import base64
import logging
import re
from pathlib import Path
from typing import Any

import yaml
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware, MiddlewareContext
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData
from pydantic import AnyHttpUrl

from cml_mcp.cml_client import CMLClient
from cml_mcp.settings import settings

logger = logging.getLogger("cml-mcp.middleware")

# ACL data
acl_data: dict | None = None


def _validate_acl_data(raw_acl_data: dict | None) -> dict | None:
    """
    Validate and normalize ACL configuration data.

    Args:
        raw_acl_data: Raw ACL data loaded from YAML file

    Returns:
        Validated/normalized ACL data or None if invalid
    """
    if not raw_acl_data:
        return None

    # Validate default_enabled
    default_enabled = raw_acl_data.get("default_enabled", True)
    if not isinstance(default_enabled, bool):
        logger.warning("Invalid default_enabled value in ACLs; defaulting to True")
        default_enabled = True

    # Validate users structure
    users = raw_acl_data.get("users", {})
    if not isinstance(users, dict):
        logger.warning("Invalid users structure in ACLs; using default_enabled with no user-specific rules")
        users = {}

    # Validate each user's tool lists
    validated_users = {}
    for username, user_config in users.items():
        if not isinstance(user_config, dict):
            logger.warning(f"Invalid configuration for user {username} in ACLs; skipping user")
            continue

        enabled_tools = user_config.get("enabled_tools")
        disabled_tools = user_config.get("disabled_tools")

        # Validate tool lists if present
        if enabled_tools is not None and not isinstance(enabled_tools, list):
            logger.warning(f"Invalid enabled_tools for user {username} in ACLs; skipping user")
            continue
        if disabled_tools is not None and not isinstance(disabled_tools, list):
            logger.warning(f"Invalid disabled_tools for user {username} in ACLs; skipping user")
            continue

        validated_users[username] = {
            "enabled_tools": enabled_tools,
            "disabled_tools": disabled_tools,
        }

    return {
        "default_enabled": default_enabled,
        "users": validated_users,
    }


def load_acl_data() -> None:
    """Load ACL configuration from file if configured."""
    global acl_data
    if settings.cml_mcp_transport == "http":
        if settings.cml_mcp_acl_file:
            aclf = Path(settings.cml_mcp_acl_file)
            if aclf.is_file():
                try:
                    with aclf.open("r", encoding="utf-8") as f:
                        raw_acl_data = yaml.safe_load(f)
                        acl_data = _validate_acl_data(raw_acl_data)
                except Exception as e:
                    logger.error(f"Failed to load ACL file {str(aclf)}: {e}", exc_info=True)
                    acl_data = None
            else:
                logger.warning(f"ACL file {str(aclf)} does not exist or is not a file. Continuing without ACLs.")


class CustomHttpRequestMiddleware(Middleware):
    """Custom middleware for HTTP request authentication and ACL enforcement."""

    @staticmethod
    def _validate_url(url: AnyHttpUrl | str, allowed_urls: list[AnyHttpUrl], url_pattern: str | None) -> None:
        if not allowed_urls and not url_pattern:
            raise McpError(
                ErrorData(
                    message="At least one of CML_ALLOWED_URLS or CML_URL_PATTERN must be set when using HTTP transport to accept"
                    " client-provided CML server URLs",
                    code=-31003,
                )
            )
        if allowed_urls:
            for allowed_url in allowed_urls:
                if str(url).lower() == str(allowed_url).lower():
                    break
            else:
                raise McpError(
                    ErrorData(
                        message=f"CML server URL '{url}' is not in the list of allowed URLs",
                        code=-31003,
                    )
                )
        if url_pattern:
            if not re.match(url_pattern, str(url)):
                raise McpError(
                    ErrorData(
                        message=f"CML server URL '{url}' does not match the required pattern",
                        code=-31004,
                    )
                )

    @staticmethod
    async def check_tool_enabled(tool_name: str, client: CMLClient) -> bool:
        """
        Check if a tool is enabled based on ACL configuration.
        ACL data is pre-validated at startup, so this method can trust the structure.
        """
        if not acl_data:
            return True  # No ACLs defined, all tools enabled

        default_enabled = acl_data["default_enabled"]
        users = acl_data["users"]

        if client.username in users:
            user_config = users[client.username]
            enabled_tools = user_config["enabled_tools"]
            disabled_tools = user_config["disabled_tools"]

            # Prefer allow list over block list.
            if enabled_tools is not None and tool_name in enabled_tools:
                return True
            if disabled_tools is not None and tool_name in disabled_tools:
                return False
            # Tool is in neither list
            if enabled_tools is not None:
                return False  # Not in allow list
            if disabled_tools is not None:
                return True  # Not in block list

        return default_enabled

    async def on_request(self, context: MiddlewareContext, call_next) -> Any:
        # Import here to avoid circular dependency
        from cml_mcp.tools.dependencies import (
            _pyats_auth_pass,
            _pyats_password,
            _pyats_username,
            _request_client,
        )

        # Reset PyATS contextvars for this request
        _pyats_username.set(None)
        _pyats_password.set(None)
        _pyats_auth_pass.set(None)

        headers = get_http_headers()
        cml_url = headers.get("x-cml-server-url")
        if not cml_url:
            if settings.cml_url:
                cml_url = str(settings.cml_url)
            else:
                raise McpError(
                    ErrorData(
                        message="Missing X-CML-Server-URL header and no default CML_URL configured",
                        code=-31002,
                    )
                )
        else:
            # Validate the server URL is allowed.
            CustomHttpRequestMiddleware._validate_url(cml_url, settings.cml_allowed_urls, settings.cml_url_pattern)
        verify_ssl_header = headers.get("x-cml-verify-ssl", "").lower()
        verify_ssl = verify_ssl_header == "true"

        auth_header = headers.get("x-authorization")
        if not auth_header or not auth_header.startswith("Basic "):
            raise McpError(ErrorData(message="Unauthorized: Missing or invalid X-Authorization header", code=-31002))
        parts = auth_header.split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "basic":
            raise McpError(ErrorData(message="Invalid X-Authorization header format. Expected 'Basic <credentials>'", code=-31001))
        try:
            decoded = base64.b64decode(parts[1]).decode("utf-8")
            username, password = decoded.split(":", 1)
        except Exception:
            raise McpError(ErrorData(message="Failed to decode Basic authentication credentials", code=-31002))
        pyats_header = headers.get("x-pyats-authorization")
        if pyats_header and pyats_header.startswith("Basic "):
            pyats_parts = pyats_header.split(" ", 1)
            if len(pyats_parts) != 2 or pyats_parts[0].lower() != "basic":
                raise McpError(
                    ErrorData(message="Invalid X-PyATS-Authorization header format. Expected 'Basic <credentials>'", code=-31001)
                )
            try:
                pyats_decoded = base64.b64decode(pyats_parts[1]).decode("utf-8")
                pyats_username, pyats_password = pyats_decoded.split(":", 1)
                _pyats_username.set(pyats_username)
                _pyats_password.set(pyats_password)
            except Exception:
                raise McpError(ErrorData(message="Failed to decode Basic authentication credentials for PyATS", code=-31002))
            pyats_enable_header = headers.get("x-pyats-enable")
            if pyats_enable_header and pyats_enable_header.startswith("Basic "):
                pyats_enable_parts = pyats_enable_header.split(" ", 1)
                if len(pyats_enable_parts) != 2 or pyats_enable_parts[0].lower() != "basic":
                    raise McpError(ErrorData(message="Invalid X-PyATS-Enable header format. Expected 'Basic <credentials>'", code=-31001))
                try:
                    pyats_enable_decoded = base64.b64decode(pyats_enable_parts[1]).decode("utf-8")
                    pyats_enable_password = pyats_enable_decoded
                    _pyats_auth_pass.set(pyats_enable_password)
                except Exception:
                    raise McpError(ErrorData(message="Failed to decode Basic authentication credentials for PyATS Enable", code=-31002))

        # Create a new client for this request.
        request_client = CMLClient(cml_url, username, password, transport="http", verify_ssl=verify_ssl)
        try:
            await request_client.login()
        except Exception as e:
            logger.error("Authentication failed: %s", str(e), exc_info=True)
            raise McpError(ErrorData(message=f"Unauthorized: {str(e)}", code=-31002))

        # Store the client in context variable for this request
        _request_client.set(request_client)
        try:
            result = await call_next(context)
            logger.debug(f"Request to {cml_url} completed successfully")
            return result
        except Exception as request_error:
            # Log request processing errors for diagnostics
            logger.warning(
                f"Request to {cml_url} failed: {type(request_error).__name__}: {request_error}",
                exc_info=False,  # Don't need full trace for client disconnects
            )
            raise
        finally:
            # Clean up the client after the request
            try:
                await request_client.close()
                logger.debug(f"Successfully closed client for request to {cml_url}")
            except Exception as cleanup_error:
                # Log but don't raise - we don't want cleanup failures to mask the actual error
                logger.error(f"Failed to close HTTP client for {cml_url}: {cleanup_error}", exc_info=True)
            finally:
                # Always clear the context var even if cleanup fails
                _request_client.set(None)

    async def on_list_tools(self, context: MiddlewareContext, call_next) -> list:
        # Import here to avoid circular dependency
        from cml_mcp.tools.dependencies import get_cml_client_dep

        result = await call_next(context)

        client = get_cml_client_dep()
        filtered_tools = [tool for tool in result if await CustomHttpRequestMiddleware.check_tool_enabled(tool.name, client)]

        return filtered_tools

    async def on_call_tool(self, context: MiddlewareContext, call_next) -> Any:
        # Import here to avoid circular dependency
        from cml_mcp.tools.dependencies import get_cml_client_dep

        client = get_cml_client_dep()
        if not await CustomHttpRequestMiddleware.check_tool_enabled(context.message.name, client):
            raise ToolError(f"Tool '{context.message.name}' is disabled by server configuration")

        return await call_next(context)
