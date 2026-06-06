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
Packet capture (PCAP) tools for CML MCP server.
"""

import base64
import logging
from typing import Annotated, Literal

import httpx
from fastmcp.exceptions import ToolError

from cml_mcp.cml.simple_webserver.schemas.common import UUID4Type
from cml_mcp.cml.simple_webserver.schemas.pcap import PCAPItem, PCAPStart, PCAPStatusResponse
from cml_mcp.cml_client import CMLClient
from cml_mcp.tools.dependencies import get_cml_client_dep
from cml_mcp.tools.model_helpers import build_payload, field_from

logger = logging.getLogger("cml-mcp.tools.pcap")


async def get_capture_key(lab_id: UUID4Type, link_id: UUID4Type, client: CMLClient) -> str:
    """
    Get the capture key for the link.
    """
    key = await client.get(f"/labs/{lab_id}/links/{link_id}/capture/key")
    if not key:
        raise ToolError("No packet capture found for the specified link.")
    return key


def register_tools(mcp):
    """Register all packet capture tools with the FastMCP server."""

    # Source schema: PCAPStart (cml/simple_webserver/schemas/pcap.py)
    # Exposed: maxpackets, maxtime, bpfilter, encap
    # Omitted: (none - all fields exposed)
    @mcp.tool(
        annotations={"title": "Start a Packet Capture on a Link", "readOnlyHint": False, "destructiveHint": False},
    )
    async def start_packet_capture(
        lab_id: UUID4Type,
        link_id: UUID4Type,
        maxpackets: Annotated[int | None, field_from(PCAPStart, "maxpackets")] = None,
        maxtime: Annotated[int | None, field_from(PCAPStart, "maxtime")] = None,
        bpfilter: Annotated[str | None, field_from(PCAPStart, "bpfilter")] = None,
        encap: Annotated[
            Literal["ethernet", "frelay", "ppp", "ppp_hdlc", "pppoe", "c_hdlc", "slip", "ax25", "ieee802_11", "radiotap"] | None,
            field_from(PCAPStart, "encap"),
        ] = None,
    ) -> bool:
        """
        Start a packet capture on a link by lab and link UUID. At least one of maxtime (seconds, 1-86400)
        or maxpackets (1-1000000) is required. Returns true on success.

        Optional: bpfilter (Berkeley packet filter string, max 128 chars), encap (link encapsulation type, default "ethernet").

        Examples:
        - "Start capturing packets on the link between R1 and R2 for 60 seconds"
        - "Capture 1000 packets on link xyz"
        - "Begin a pcap on the WAN link"
        """

        client = get_cml_client_dep()
        try:
            payload = build_payload(
                maxpackets=maxpackets,
                maxtime=maxtime,
                bpfilter=bpfilter,
                encap=encap,
            )
            if "maxpackets" not in payload and "maxtime" not in payload:
                raise ValueError("Either 'maxpackets' or 'maxtime' must be specified")
            await client.put(f"/labs/{lab_id}/links/{link_id}/capture/start", data=payload)
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error starting packet capture on link %s in lab %s", link_id, lab_id)
            raise ToolError(e)

    @mcp.tool(
        annotations={"title": "Stop a Packet Capture on a Link", "readOnlyHint": False, "destructiveHint": False},
    )
    async def stop_packet_capture(lab_id: UUID4Type, link_id: UUID4Type) -> bool:
        """
        Stop an active packet capture on a link by lab and link UUID.

        Examples:
        - "Stop the packet capture on link xyz"
        - "End the pcap between R1 and R2"
        - "Stop capturing on the WAN link"
        """
        client = get_cml_client_dep()
        try:
            await client.put(f"/labs/{lab_id}/links/{link_id}/capture/stop")
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error stopping packet capture on link %s in lab %s", link_id, lab_id)
            raise ToolError(e)

    @mcp.tool(
        annotations={"title": "Check Packet Capture Status on a Link", "readOnlyHint": True},
    )
    async def check_packet_capture_status(lab_id: UUID4Type, link_id: UUID4Type) -> PCAPStatusResponse:
        """
        Check whether a packet capture is active on a link, plus its config and packet count
        so far. Returns a PCAPStatusResponse.

        Examples:
        - "Is a capture running on link xyz?"
        - "How many packets have I captured so far?"
        - "Show packet capture status for the WAN link"
        """
        client = get_cml_client_dep()
        try:
            status = await client.get(f"/labs/{lab_id}/links/{link_id}/capture/status")
            # See DEVELOPMENT.md "Object-typed return values": dump after construction so FastMCP doesn't double-marshal.
            return PCAPStatusResponse(**status).model_dump(exclude_unset=True)
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error checking packet capture status on link %s in lab %s", link_id, lab_id)
            raise ToolError(e)

    @mcp.tool(
        annotations={"title": "Get packet capture overview", "readOnlyHint": True},
    )
    async def get_captured_packet_overview(lab_id: UUID4Type, link_id: UUID4Type) -> list[PCAPItem]:
        """
        Get a brief one-line summary of each packet captured on a link (timestamps, src/dst,
        protocol). Lightweight alternative to downloading the full PCAP.

        Examples:
        - "Summarize the captured packets on link xyz"
        - "Show me a packet list for the WAN capture"
        - "What was captured between R1 and R2?"
        """
        client = get_cml_client_dep()
        try:
            key = await get_capture_key(lab_id, link_id, client)
            packets = await client.get(f"/pcap/{key}/packets")
            return [PCAPItem(**packet).model_dump(exclude_unset=True) for packet in packets]
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error getting packet capture overview on link %s in lab %s", link_id, lab_id)
            raise ToolError(e)

    @mcp.tool(
        annotations={"title": "Get Full Packets from a Packet Capture", "readOnlyHint": True},
    )
    async def get_packet_capture_data(lab_id: UUID4Type, link_id: UUID4Type) -> str:
        """
        Download the complete PCAP file for a link by lab and link UUID. Returns base64-encoded
        binary PCAP data -- decode and save as a .pcap file for Wireshark, tcpdump, or other
        analysis tools.

        Examples:
        - "Download the pcap from link xyz"
        - "Give me the capture file for the WAN link"
        - "Get the full packet capture for the link between R1 and R2"
        """
        client = get_cml_client_dep()
        try:
            # Get the capture key for the link
            key = await get_capture_key(lab_id, link_id, client)
            # Download the PCAP data using the capture key
            pcap_data = await client.get(f"/pcap/{key}", is_binary=True)
            # Encode the binary PCAP data to a base64 string
            encoded_pcap = base64.b64encode(pcap_data).decode("utf-8")
            return encoded_pcap
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error getting packet capture data from link %s in lab %s", link_id, lab_id)
            raise ToolError(e)
