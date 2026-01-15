# Copyright (c) 2025-2026  Cisco Systems, Inc.
# All rights reserved.

"""
Packet capture (PCAP) tools for CML MCP server.
"""

import base64
import logging

import httpx
from fastmcp.exceptions import ToolError

from cml_mcp.cml.simple_webserver.schemas.common import UUID4Type
from cml_mcp.cml.simple_webserver.schemas.pcap import PCAPItem, PCAPStart, PCAPStatusResponse
from cml_mcp.cml_client import CMLClient
from cml_mcp.tools.dependencies import get_cml_client_dep

logger = logging.getLogger("cml-mcp.tools.pcap")


async def get_capture_key(lid: UUID4Type, link_id: UUID4Type, client: CMLClient) -> str:
    """
    Get the capture key for the link.
    """
    key = await client.get(f"/labs/{lid}/links/{link_id}/capture/key")
    if not key:
        raise ToolError("No packet capture found for the specified link.")
    return key


def register_tools(mcp):
    """Register all packet capture tools with the FastMCP server."""

    @mcp.tool(
        annotations={"title": "Start a Packet Capture on a Link", "readOnlyHint": False, "destructiveHint": False},
    )
    async def start_packet_capture(lid: UUID4Type, link_id: UUID4Type, pcap: PCAPStart) -> bool:
        """
        Start a packet capture by lab and link UUID. At least one of maxtime or maxpackets is
        required in pcap.  Returns true if successful.
        """
        client = get_cml_client_dep()
        try:
            await client.put(f"/labs/{lid}/links/{link_id}/capture/start", data=pcap.model_dump(mode="json", exclude_none=True))
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error starting packet capture on link {link_id} in lab {lid}: {str(e)}", exc_info=True)
            raise ToolError(e)

    @mcp.tool(
        annotations={"title": "Stop a Packet Capture on a Link", "readOnlyHint": False, "destructiveHint": False},
    )
    async def stop_packet_capture(lid: UUID4Type, link_id: UUID4Type) -> bool:
        """
        Stop a packet capture by lab and link UUID.  Returns true if successful.
        """
        client = get_cml_client_dep()
        try:
            await client.put(f"/labs/{lid}/links/{link_id}/capture/stop")
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error stopping packet capture on link {link_id} in lab {lid}: {str(e)}", exc_info=True)
            raise ToolError(e)

    @mcp.tool(
        annotations={"title": "Check Packet Capture Status on a Link", "readOnlyHint": True},
    )
    async def check_packet_capture_status(lid: UUID4Type, link_id: UUID4Type) -> PCAPStatusResponse:
        """
        Check if a packet capture is active on a link by lab and link UUID.
        Returns object capture config, and number of packets captured.
        """
        client = get_cml_client_dep()
        try:
            status = await client.get(f"/labs/{lid}/links/{link_id}/capture/status")
            return PCAPStatusResponse(**status).model_dump(exclude_unset=True)
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error checking packet capture status on link {link_id} in lab {lid}: {str(e)}", exc_info=True)
            raise ToolError(e)

    @mcp.tool(
        annotations={"title": "Get packet capture overview", "readOnlyHint": True},
    )
    async def get_captured_packet_overview(lid: UUID4Type, link_id: UUID4Type) -> list[PCAPItem]:
        """
        Get a brief summary of each packet captured on a link by lab and link UUID. Returns list of PCAPItem objects.
        """
        client = get_cml_client_dep()
        try:
            key = await get_capture_key(lid, link_id, client)
            packets = await client.get(f"/pcap/{key}/packets")
            return [PCAPItem(**packet).model_dump(exclude_unset=True) for packet in packets]
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error getting packet capture overview on link {link_id} in lab {lid}: {str(e)}", exc_info=True)
            raise ToolError(e)

    @mcp.tool(
        annotations={"title": "Get Full Packets from a Packet Capture", "readOnlyHint": True},
    )
    async def get_packet_capture_data(lid: UUID4Type, link_id: UUID4Type) -> str:
        """
        Download complete packet capture by lab and link UUID. Returns base64-encoded PCAP file.
        Decode and save as .pcap file for use with Wireshark, tcpdump, or other packet analysis tools.
        """
        client = get_cml_client_dep()
        try:
            # Get the capture key for the link
            key = await get_capture_key(lid, link_id, client)
            # Download the PCAP data using the capture key
            pcap_data = await client.get(f"/pcap/{key}", is_binary=True)
            # Encode the binary PCAP data to a base64 string
            encoded_pcap = base64.b64encode(pcap_data).decode("utf-8")
            return encoded_pcap
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error getting packet capture data from link {link_id} in lab {lid}: {str(e)}", exc_info=True)
            raise ToolError(e)
