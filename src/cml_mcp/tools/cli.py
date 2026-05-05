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
    lab_id: UUID4Type,
    label: NodeLabel,  # pyright: ignore[reportInvalidTypeForm]
    commands: str,
    config_command: bool,
    console: int,
) -> str:
    """
    Synchronous helper for send_cli_command to isolate blocking operations in a thread.
    This prevents os.chdir() race conditions and event loop blocking.
    """
    cwd = os.getcwd()  # Save the current working directory
    try:
        os.chdir(tempfile.gettempdir())  # Change to a writable directory (required by pyATS/ClPyats)
        lab = client.vclient.join_existing_lab(str(lab_id))  # Join the existing lab using the provided lab ID
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

        if console != 0:
            pylab.switch_serial_console(str(label), console)

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
        lab_id: UUID4Type,
        node_id: UUID4Type,
        console: int = 0,
    ) -> list[ConsoleLogOutput]:
        """
        Get the console output history for a node by lab and node UUID. The node must be started.

        Returns log entries (time in ms since start + message) from the selected serial console
        (default 0). Some nodes (e.g. Docker-based) expose multiple consoles -- use console=1 for
        the second port. Useful for boot troubleshooting and verifying CLI command results.

        Examples:
        - "Show me the console output for router R1"
        - "Get the boot log for the firewall node"
        - "Tail the second console (console 1) on the Alpine container"
        """

        client = get_cml_client_dep()
        return_lines = []
        try:
            resp = await client.get(f"/labs/{lab_id}/nodes/{node_id}/consoles/{console}/log")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                raise ToolError(f"Console index {console} does not exist for node {node_id}")
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error getting console log for node %s in lab %s", node_id, lab_id)
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
        # See DEVELOPMENT.md "Object-typed return values": dump after construction so FastMCP doesn't double-marshal.
        return [entry.model_dump(exclude_unset=True) for entry in return_lines]

    @mcp.tool(
        annotations={"title": "Send CLI Command to CML Node", "readOnlyHint": False, "destructiveHint": True},
    )
    async def send_cli_command(
        lab_id: UUID4Type,
        label: NodeLabel,  # pyright: ignore[reportInvalidTypeForm]
        commands: str,
        config_command: bool = False,
        console: int = 0,
    ) -> str:
        """
        Send CLI commands to a running node via PyATS/Unicon. Identify the node by lab UUID and
        node label (NOT node UUID). Node must be in BOOTED state. Returns command output text.

        - Separate multiple commands with newlines.
        - config_command=false (default): exec/operational mode (e.g. "show version").
        - config_command=true: configuration mode -- DO NOT include "configure terminal" or "end".
        - Optional console: pick a non-default serial console (e.g. console=1 for some Docker nodes).

        CRITICAL: Can modify device state. Review commands carefully before executing, especially
        when config_command=true.

        Examples:
        - "Run 'show ip route' on router R1 in lab abc123"
        - "Configure interface Gi0/1 with IP 10.0.0.1/24 on R1"
        - "Show the running config of the firewall"
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
            output = await asyncio.to_thread(_send_cli_command_sync, client, lab_id, label, commands, config_command, console)
            return output
        except Exception as e:
            logger.exception("Error sending CLI command to node %s in lab %s", label, lab_id)
            raise ToolError(e)
