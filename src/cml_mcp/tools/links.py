# Copyright (c) 2025-2026  Cisco Systems, Inc.
# All rights reserved.

"""
Link management tools for CML MCP server.
"""

import logging

import httpx
from fastmcp.exceptions import ToolError

from cml_mcp.cml.simple_webserver.schemas.common import UUID4Type
from cml_mcp.cml.simple_webserver.schemas.links import LinkResponse
from cml_mcp.tools.dependencies import get_cml_client_dep

logger = logging.getLogger("cml-mcp.tools.links")


def register_tools(mcp):
    """Register all link-related tools with the FastMCP server."""

    # Source schema: LinkCreate (cml/simple_webserver/schemas/links.py)
    # Exposed: src_int, dst_int
    # Omitted: (none - all fields exposed)
    @mcp.tool(
        annotations={
            "title": "Connect Two Nodes in a CML Lab",
            "readOnlyHint": False,
            "destructiveHint": False,
        },
    )
    async def connect_two_nodes(
        lid: UUID4Type,
        src_int: UUID4Type,
        dst_int: UUID4Type,
    ) -> UUID4Type:
        """
        Create a link between two interfaces in the same lab. Returns the new link's UUID.

        Required: src_int (source interface UUID) and dst_int (destination interface UUID).
        Get interface UUIDs from get_interfaces_for_node.

        Examples:
        - "Connect router R1 to switch SW1"
        - "Link the firewall to the core router"
        - "Wire R1 Gi0/0 to R2 Gi0/0"
        """

        client = get_cml_client_dep()
        try:
            payload = {"src_int": str(src_int), "dst_int": str(dst_int)}
            resp = await client.post(f"/labs/{lid}/links", data=payload)
            return UUID4Type(resp["id"])
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error creating link between %s and %s", src_int, dst_int)
            raise ToolError(e)

    @mcp.tool(
        annotations={
            "title": "Get All Links for a CML Lab",
            "readOnlyHint": True,
        },
    )
    async def get_all_links_for_lab(lid: UUID4Type) -> list[LinkResponse]:
        """
        List all links in a lab by lab UUID. Returns id, label, interface_a, interface_b,
        node_a, node_b, state, and capture_key (for packet capture).

        Examples:
        - "Show all links in lab abc123"
        - "List the connections in my topology"
        - "What's wired up in my OSPF lab?"
        """
        client = get_cml_client_dep()
        try:
            resp = await client.get(f"/labs/{lid}/links", params={"data": True})
            return [LinkResponse(**link).model_dump(exclude_unset=True) for link in resp]
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error getting links for lab %s", lid)
            raise ToolError(e)

    # Source schema: LinkConditionConfiguration (cml/simple_webserver/schemas/links.py)
    # Exposed: enabled, bandwidth, latency, delay_corr, limit, loss, loss_corr, gap, duplicate,
    #          duplicate_corr, jitter, reorder_prob, reorder_corr, corrupt_prob, corrupt_corr
    # Omitted: (none - all fields exposed)
    @mcp.tool(
        annotations={"title": "Apply Link Conditioning", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True},
    )
    async def apply_link_conditioning(
        lid: UUID4Type,
        link_id: UUID4Type,
        enabled: bool | None = None,
        bandwidth: int | None = None,
        latency: int | None = None,
        delay_corr: float | int | None = None,
        limit: int | None = None,
        loss: float | int | None = None,
        loss_corr: float | int | None = None,
        gap: int | None = None,
        duplicate: float | int | None = None,
        duplicate_corr: float | int | None = None,
        jitter: int | None = None,
        reorder_prob: float | int | None = None,
        reorder_corr: float | int | None = None,
        corrupt_prob: float | int | None = None,
        corrupt_corr: float | int | None = None,
    ) -> bool:
        """
        Apply network impairment to a link (bandwidth limit, latency, loss, jitter, etc.) by
        lab and link UUID. Omitted fields keep their existing value.

        Optional: enabled (bool), bandwidth (kbps, 0-10M), latency (ms, 0-10K), loss (%, 0-100),
        jitter (ms, 0-10K), duplicate (%), corrupt_prob (%), gap (ms), limit (ms),
        reorder_prob (%), delay_corr/loss_corr/duplicate_corr/reorder_corr/corrupt_corr (%).

        Examples:
        - "Add 100ms latency to the link between R1 and R2"
        - "Limit the WAN link to 1 Mbps with 1% packet loss"
        - "Simulate a flaky connection on link xyz"
        """
        client = get_cml_client_dep()
        try:
            payload: dict = {}
            for key, value in (
                ("enabled", enabled),
                ("bandwidth", bandwidth),
                ("latency", latency),
                ("delay_corr", delay_corr),
                ("limit", limit),
                ("loss", loss),
                ("loss_corr", loss_corr),
                ("gap", gap),
                ("duplicate", duplicate),
                ("duplicate_corr", duplicate_corr),
                ("jitter", jitter),
                ("reorder_prob", reorder_prob),
                ("reorder_corr", reorder_corr),
                ("corrupt_prob", corrupt_prob),
                ("corrupt_corr", corrupt_corr),
            ):
                if value is not None:
                    payload[key] = value
            await client.patch(f"/labs/{lid}/links/{link_id}/condition", data=payload)
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error conditioning link %s in lab %s", link_id, lid)
            raise ToolError(e)

    @mcp.tool(
        annotations={
            "title": "Start a CML Link",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def start_cml_link(lid: UUID4Type, link_id: UUID4Type) -> bool:
        """
        Start a link (enable connectivity) by lab and link UUID.

        Examples:
        - "Start the link between R1 and R2"
        - "Enable link xyz"
        - "Bring up the WAN connection"
        """
        client = get_cml_client_dep()
        try:
            await client.put(f"/labs/{lid}/links/{link_id}/state/start")
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error starting CML link %s in lab %s", link_id, lid)
            raise ToolError(e)

    @mcp.tool(
        annotations={
            "title": "Stop a CML Link",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def stop_cml_link(lid: UUID4Type, link_id: UUID4Type) -> bool:
        """
        Stop a link (disable connectivity, simulate cable pull) by lab and link UUID.

        Examples:
        - "Stop the link between R1 and R2"
        - "Disable link xyz"
        - "Simulate a cable pull on the WAN link"
        """
        client = get_cml_client_dep()
        try:
            await client.put(f"/labs/{lid}/links/{link_id}/state/stop")
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error stopping CML link %s in lab %s", link_id, lid)
            raise ToolError(e)
