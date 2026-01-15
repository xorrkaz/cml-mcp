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
Main server module for CML MCP.
This module initializes the FastMCP server and registers all tools from modular components.
"""

import logging
import os

from fastmcp import FastMCP

from cml_mcp.settings import settings

# Import dependencies first to ensure global client initialization happens before other imports
from cml_mcp.tools import dependencies  # noqa: F401 - imported for side effects (global client init)
from cml_mcp.tools import annotations, cli, interfaces, labs, links, middleware, node_definitions, nodes, pcap, system, users_groups

# Set up root logging for cml-mcp and all submodules
logger = logging.getLogger("cml-mcp")
loglevel = logging.DEBUG if os.getenv("DEBUG", "false").lower() == "true" else logging.INFO
logger.setLevel(loglevel)
# Configure handler with format that will cascade to all cml-mcp.* loggers
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(threadName)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    # Allow propagation to ensure all child loggers (cml-mcp.*) inherit this configuration
    logger.propagate = False  # Don't propagate to root, but children will inherit our handler

# Load ACL configuration if using HTTP transport
if settings.cml_mcp_transport == "http":
    middleware.load_acl_data()

# Initialize FastMCP server
server_mcp = FastMCP(
    name="Cisco Modeling Labs (CML)",
    website_url="https://www.cisco.com/go/cml",
    # icons=[Icon(src="https://www.marcuscom.com/cml-mcp/img/cml_icon.png", mimeType="image/png", sizes=["any"])],
)

# Add middleware for HTTP transport
app = None
if settings.cml_mcp_transport == "http":
    server_mcp.add_middleware(middleware.CustomHttpRequestMiddleware())
    app = server_mcp.http_app()

# Register all tools from modules
logger.info("Registering tools...")
system.register_tools(server_mcp)
users_groups.register_tools(server_mcp)
node_definitions.register_tools(server_mcp)
labs.register_tools(server_mcp)
nodes.register_tools(server_mcp)
interfaces.register_tools(server_mcp)
links.register_tools(server_mcp)
annotations.register_tools(server_mcp)
pcap.register_tools(server_mcp)
cli.register_tools(server_mcp)
logger.info("All tools registered successfully")
