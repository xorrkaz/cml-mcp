# Copyright (c) 2025-2026  Cisco Systems, Inc.
# All rights reserved.

"""
CLI command and console log tools for CML MCP server.
"""

import asyncio
import logging
import os
import re
import tempfile

import httpx
from fastmcp.exceptions import ToolError
from virl2_client.models.cl_pyats import ClPyats, PyatsNotInstalled

from cml_mcp.cml.simple_webserver.schemas.common import UUID4Type
from cml_mcp.cml.simple_webserver.schemas.nodes import NodeLabel
from cml_mcp.cml_client import CMLClient
from cml_mcp.tools.dependencies import _pyats_auth_pass, _pyats_password, _pyats_username, get_cml_client_dep
from cml_mcp.types import ConsoleLogOutput

logger = logging.getLogger("cml-mcp.tools.cli")


def _send_cli_command_sync(
    client: CMLClient,
    lid: UUID4Type,
    label: NodeLabel,  # pyright: ignore[reportInvalidTypeForm]
    commands: str,
    config_command: bool,
) -> str:
    """
    Synchronous helper for send_cli_command to isolate blocking operations in a thread.
    This prevents os.chdir() race conditions and event loop blocking.
    """
    cwd = os.getcwd()  # Save the current working directory
    try:
        os.chdir(tempfile.gettempdir())  # Change to a writable directory (required by pyATS/ClPyats)
        lab = client.vclient.join_existing_lab(str(lid))  # Join the existing lab using the provided lab ID
        try:
            pylab = ClPyats(lab)  # Create a ClPyats object for interacting with the lab
            pylab.sync_testbed(client.vclient.username, client.vclient.password)  # Sync the testbed with CML credentials

            # Set the credentials for all devices other than the Terminal Server
            # For HTTP transport: use contextvars (request-scoped, prevents race conditions)
            # For stdio transport: fall back to environment variables
            for device in pylab._testbed.devices.values():
                if device.name != "terminal_server":
                    device.credentials.default.username = _pyats_username.get() or os.getenv("PYATS_USERNAME", "cisco")
                    device.credentials.default.password = _pyats_password.get() or os.getenv("PYATS_PASSWORD", "cisco")
                    device.credentials.enable.password = (
                        _pyats_auth_pass.get() or os.getenv("PYATS_AUTH_PASS") or device.credentials.default.password
                    )

        except PyatsNotInstalled:
            raise ImportError(
                "PyATS and Genie are required to send commands to running devices.  See the documentation on how to install them."
            )
        if config_command:
            # Send the command as a configuration command
            results = pylab.run_config_command(str(label), commands)
        else:
            # Send the command as an exec/operational command
            results = pylab.run_command(str(label), commands)

        # Genie may return dict output where the key is the command and the value is its output.
        if isinstance(results, dict):
            output = ""
            for cmd, cmd_output in results.items():
                output += f"Command: {cmd}\nOutput:\n{cmd_output}\n"
        else:
            output = str(results)

        return output
    finally:
        os.chdir(cwd)  # Restore the original working directory


def register_tools(mcp):
    """Register all CLI and console tools with the FastMCP server."""

    @mcp.tool(
        annotations={"title": "Get Console Logs for a CML Node", "readOnlyHint": True},
    )
    async def get_console_log(
        lid: UUID4Type,
        nid: UUID4Type,
    ) -> list[ConsoleLogOutput]:
        """
        Get console output history by lab and node UUID. Node must be started.
        Returns log entries from the selected serial console (default 0) with
        time (ms since start) and message.  Note: some nodes (like Docker-based nodes)
        use both serial 0 and serial 1.
        Useful for troubleshooting, monitoring boot progress, and verifying CLI command results.
        """
        client = get_cml_client_dep()
        return_lines = []
        try:
            resp = await client.get(f"/labs/{lid}/nodes/{nid}/consoles/{console}/log")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                raise ToolError(f"Console index {console} does not exist for node {nid}")
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error getting console log for node %s in lab %s", nid, lid)
            raise ToolError(e)
        lines = re.split(r"\r?\n", resp)
        for line in lines:
            if not line.startswith("|"):
                if len(return_lines) > 0:
                    # Append to the last message if the line does not start with a timestamp
                    return_lines[-1].message += "\n" + line
                continue
            _, log_time, msg = line.split("|", 2)
            return_lines.append(ConsoleLogOutput(time=int(log_time), message=msg))
        return return_lines

    @mcp.tool(
        annotations={"title": "Send CLI Command to CML Node", "readOnlyHint": False, "destructiveHint": True},
    )
    async def send_cli_command(
        lid: UUID4Type,
        label: NodeLabel,  # pyright: ignore[reportInvalidTypeForm]
        commands: str,
        config_command: bool = False,
    ) -> str:
        """
        Send CLI commands to running node by lab UUID and node label (not UUID). Node must be in BOOTED state.
        CRITICAL: Can modify device state. Review commands before executing, especially with config_command=true.
        Separate multiple commands with newlines.
        config_command=false (default): exec/operational mode. config_command=true: config mode (omit "configure terminal"/"end").
        Returns command output text.
        """
        client = get_cml_client_dep()

        # Verify vclient is available
        if client.vclient is None:
            raise ToolError(
                "PyATS CLI commands require the virl2_client library. Ensure the CML client was initialized with valid credentials."
            )

        # Use asyncio.to_thread to prevent blocking the event loop with synchronous operations
        # and to avoid os.chdir() race conditions between concurrent requests
        try:
            output = await asyncio.to_thread(_send_cli_command_sync, client, lid, label, commands, config_command, console)
            return output
        except Exception as e:
            logger.exception("Error sending CLI command to node %s in lab %s", label, lid)
            raise ToolError(e)
