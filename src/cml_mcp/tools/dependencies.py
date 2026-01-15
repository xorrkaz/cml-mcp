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
Dependency injection module for CML client management.
"""

import contextvars
import logging
from typing import Optional

from cml_mcp.cml_client import CMLClient
from cml_mcp.settings import settings

logger = logging.getLogger("cml-mcp.dependencies")

# Global singleton client for stdio transport
# Only initialize if we're using stdio transport to avoid resource waste
if settings.cml_mcp_transport == "stdio":
    cml_client = CMLClient(
        str(settings.cml_url),
        settings.cml_username,
        settings.cml_password,
        transport=str(settings.cml_mcp_transport),
        verify_ssl=settings.cml_verify_ssl,
    )
else:
    # In HTTP mode, we don't need a global client - each request creates its own
    cml_client = None  # type: ignore[assignment]

# Context variable to store request-scoped client for HTTP transport
_request_client: contextvars.ContextVar[Optional[CMLClient]] = contextvars.ContextVar("request_client", default=None)

# Context variables for PyATS credentials (per-request isolation)
_pyats_username: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("pyats_username", default=None)
_pyats_password: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("pyats_password", default=None)
_pyats_auth_pass: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("pyats_auth_pass", default=None)


async def cleanup_global_client() -> None:
    """Cleanup global CML client resources. Must be called before event loop shutdown."""
    if cml_client is not None and settings.cml_mcp_transport == "stdio":
        logger.info("Cleaning up global CML client...")
        try:
            await cml_client.close()
            logger.info("Successfully closed global CML client")
        except Exception as e:
            logger.error(f"Error closing global CML client: {e}", exc_info=True)
    else:
        logger.debug("No global CML client to clean up (HTTP mode or client is None)")


def get_cml_client_dep() -> CMLClient:
    """
    Dependency function to get the appropriate CML client.
    For HTTP transport, returns the request-scoped client.
    For stdio transport, returns the global singleton.
    """
    if settings.cml_mcp_transport == "http":
        client = _request_client.get()
        if client is None:
            raise RuntimeError(
                "No request client available in contextvar. This usually means the tool "
                "was called outside of a proper HTTP request context (e.g., from a spawned "
                "task without context propagation, or before middleware initialization). "
                "Check that async tasks properly inherit context."
            )
        return client
    else:
        if cml_client is None:
            raise RuntimeError("Global CML client is not initialized. This should never happen in stdio mode.")
        return cml_client
