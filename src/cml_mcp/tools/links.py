# Copyright (c) 2025-2026  Cisco Systems, Inc.
# All rights reserved.

"""
Link management tools for CML MCP server.
"""

import logging

import httpx
from fastmcp.exceptions import ToolError

from cml_mcp.cml.simple_webserver.schemas.common import UUID4Type
from cml_mcp.cml.simple_webserver.schemas.links import LinkConditionConfiguration, LinkCreate, LinkResponse
from cml_mcp.tools.dependencies import get_cml_client_dep

logger = logging.getLogger("cml-mcp.tools.links")


def register_tools(mcp):
    """Register all link-related tools with the FastMCP server."""

    @mcp.tool(
        annotations={
            "title": "Connect Two Nodes in a CML Lab",
            "readOnlyHint": False,
            "destructiveHint": False,
        },
    )
    async def connect_two_nodes(
        lid: UUID4Type,
        link_info: LinkCreate | dict,
    ) -> UUID4Type:
        """
        Create link between two interfaces. Returns link UUID.
        Input: link object. Prefer a JSON object; JSON-encoded object strings are accepted.
        Required: src_int (source interface UUID), dst_int (destination interface UUID).
        Use interface UUIDs from get_interfaces_for_node.
        """
        client = get_cml_client_dep()
        try:
            # XXX The dict usage is a workaround for some LLMs that pass a JSON string
            # representation of the argument object.
            if isinstance(link_info, dict):
                link_info = LinkCreate(**link_info)
            resp = await client.post(f"/labs/{lid}/links", data=link_info.model_dump(mode="json"))
            return UUID4Type(resp["id"])
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error creating link for {link_info}: {str(e)}", exc_info=True)
            raise ToolError(e)

    @mcp.tool(
        annotations={
            "title": "Get All Links for a CML Lab",
            "readOnlyHint": True,
        },
    )
    async def get_all_links_for_lab(lid: UUID4Type) -> list[LinkResponse]:
        """
        Get lab links by UUID. Returns list with id, label, interface_a, interface_b, node_a, node_b, state, and capture_key.
        """
        client = get_cml_client_dep()
        try:
            resp = await client.get(f"/labs/{lid}/links", params={"data": True})
            return [LinkResponse(**link).model_dump(exclude_unset=True) for link in resp]
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error getting links for lab {lid}: {str(e)}", exc_info=True)
            raise ToolError(e)

    @mcp.tool(
        annotations={"title": "Apply Link Conditioning", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True},
    )
    async def apply_link_conditioning(
        lid: UUID4Type,
        link_id: UUID4Type,
        condition: LinkConditionConfiguration | dict,
    ) -> bool:
        """
        Configure link network conditions by lab and link UUID.
        Input: condition object. Prefer a JSON object; JSON-encoded object strings are accepted.
        Omit fields to leave existing values unchanged.
        Fields (all optional): bandwidth (kbps, 0-10M), latency (ms, 0-10K), loss (%, 0-100), jitter (ms, 0-10K),
        duplicate (%, 0-100), corrupt_prob (%, 0-100), gap (ms), limit (ms), reorder_prob (%, 0-100),
        delay_corr/loss_corr/duplicate_corr/reorder_corr/corrupt_corr (%, 0-100), enabled (bool).
        """
        client = get_cml_client_dep()
        try:
            # XXX The dict usage is a workaround for some LLMs that pass a JSON string
            # representation of the argument object.
            if isinstance(condition, dict):
                condition = LinkConditionConfiguration(**condition)
            await client.patch(f"/labs/{lid}/links/{link_id}/condition", data=condition.model_dump(mode="json", exclude_none=True))
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error conditioning link {link_id} in lab {lid}: {str(e)}", exc_info=True)
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
        Start link by lab and link UUID. Enables connectivity.
        """
        client = get_cml_client_dep()
        try:
            await client.put(f"/labs/{lid}/links/{link_id}/state/start")
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error starting CML link {link_id} in lab {lid}: {str(e)}", exc_info=True)
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
        Stop link by lab and link UUID. Disables connectivity.
        """
        client = get_cml_client_dep()
        try:
            await client.put(f"/labs/{lid}/links/{link_id}/state/stop")
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error stopping CML link {link_id} in lab {lid}: {str(e)}", exc_info=True)
            raise ToolError(e)
