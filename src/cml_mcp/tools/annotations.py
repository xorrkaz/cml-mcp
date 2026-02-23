# Copyright (c) 2025-2026  Cisco Systems, Inc.
# All rights reserved.

"""
Annotation management tools for CML MCP server.
"""

import logging

import httpx
from fastmcp import Context
from fastmcp.exceptions import ToolError
from mcp.shared.exceptions import McpError
from mcp.types import INVALID_REQUEST, METHOD_NOT_FOUND

from cml_mcp.cml.simple_webserver.schemas.annotations import (
    AnnotationResponse,
    EllipseAnnotation,
    EllipseAnnotationResponse,
    LineAnnotation,
    LineAnnotationResponse,
    RectangleAnnotation,
    RectangleAnnotationResponse,
    TextAnnotation,
    TextAnnotationResponse,
)
from cml_mcp.cml.simple_webserver.schemas.common import UUID4Type
from cml_mcp.tools.dependencies import get_cml_client_dep

logger = logging.getLogger("cml-mcp.tools.annotations")


def register_tools(mcp):
    """Register all annotation-related tools with the FastMCP server."""

    @mcp.tool(
        annotations={
            "title": "Get all annotations for a CML Lab",
            "readOnlyHint": True,
        },
    )
    async def get_annotations_for_cml_lab(lid: UUID4Type) -> list[AnnotationResponse]:
        """
        Get all visual annotations for a lab by lab UUID. Returns list of AnnotationResponse objects.
        """
        client = get_cml_client_dep()
        try:
            resp = await client.get(f"/labs/{lid}/annotations")
            ann_list = []
            for annotation in resp:
                if annotation.get("type") == "text":
                    annotation_obj = TextAnnotationResponse(**annotation)
                elif annotation.get("type") == "rectangle":
                    annotation_obj = RectangleAnnotationResponse(**annotation)
                elif annotation.get("type") == "ellipse":
                    annotation_obj = EllipseAnnotationResponse(**annotation)
                elif annotation.get("type") == "line":
                    annotation_obj = LineAnnotationResponse(**annotation)
                else:
                    raise ValueError(
                        f"Invalid annotation type: {annotation.get('type')}. Must be one of 'text', 'rectangle', 'ellipse', or 'line'."
                    )
                ann_list.append(annotation_obj.model_dump(exclude_unset=True))
            return ann_list
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error getting annotations for lab {lid}: {str(e)}", exc_info=True)
            raise ToolError(e)

    @mcp.tool(
        annotations={
            "title": "Add an Annotation to a CML Lab",
            "readOnlyHint": False,
            "destructiveHint": False,
        },
    )
    async def add_annotation_to_cml_lab(
        lid: UUID4Type,
        annotation: EllipseAnnotation | LineAnnotation | RectangleAnnotation | TextAnnotation | dict,
    ) -> UUID4Type:
        """
        Add visual annotation to lab. Returns annotation UUID.
        Input: annotation object. Prefer a JSON object; JSON-encoded object strings are accepted.
        Required field: type ("text"/"rectangle"/"ellipse"/"line").

        Common fields: x1, y1 (coords -15000 to 15000), color, border_color, border_style (""/"2,2"/"4,2"),
        thickness (1-32), z_index (-10240 to 10240).

        Rectangle/Ellipse: x2, y2 are WIDTH and HEIGHT from x1,y1, NOT corners! For box (-200,-100) to (200,-50),
        use x1=-200, y1=-100, x2=400, y2=50. Also: rotation (0-360), border_radius (0-128, rectangles only).

        Line: x2, y2 are absolute endpoint coords (unlike rectangles). line_start/line_end: "arrow"/"square"/"circle"/null.

        Text: text_content (max 8192 chars), text_font (required), text_size (1-128), text_unit ("pt"/"px"/"em"),
        text_bold/text_italic (bool), rotation (0-360).
        """
        client = get_cml_client_dep()
        try:
            # XXX The dict usage is a workaround for some LLMs that pass a JSON string
            # representation of the argument object.
            if isinstance(annotation, dict):
                if annotation["type"] == "text":
                    annotation = TextAnnotation(**annotation)
                elif annotation["type"] == "rectangle":
                    annotation = RectangleAnnotation(**annotation)
                elif annotation["type"] == "ellipse":
                    annotation = EllipseAnnotation(**annotation)
                elif annotation["type"] == "line":
                    annotation = LineAnnotation(**annotation)
                else:
                    raise ValueError(
                        f"Invalid annotation type: {annotation['type']}. Must be one of 'text', 'rectangle', 'ellipse', or 'line'."
                    )
            resp = await client.post(f"/labs/{lid}/annotations", data=annotation.model_dump(mode="json", exclude_defaults=True))
            return UUID4Type(resp["id"])
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error adding annotation to lab {lid}: {str(e)}", exc_info=True)
            raise ToolError(e)

    @mcp.tool(
        annotations={
            "title": "Delete an Annotation from a CML Lab",
            "readOnlyHint": False,
            "destructiveHint": True,
        },
    )
    async def delete_annotation_from_lab(
        lid: UUID4Type,
        annotation_id: UUID4Type,
        ctx: Context,
    ) -> bool:
        """
        Delete annotation by lab and annotation UUID. CRITICAL: Always ask "Confirm deletion of [item]?" and wait for
        user's "yes" before deleting.
        """
        client = get_cml_client_dep()
        try:
            elicit_supported = True
            try:
                result = await ctx.elicit("Are you sure you want to delete the annotation?", response_type=None)
            except McpError as me:
                if me.error.code == METHOD_NOT_FOUND or me.error.code == INVALID_REQUEST:
                    elicit_supported = False
                else:
                    raise me
            except Exception as e:
                # Handle stream closure errors (common in stateless HTTP when client disconnects)
                # Treat as if elicit is not supported and proceed without confirmation
                logger.debug(f"elicit() failed (possibly client disconnect): {type(e).__name__}: {e}")
                elicit_supported = False
            if elicit_supported and result.action != "accept":
                raise Exception("Delete operation cancelled by user.")
            await client.delete(f"/labs/{lid}/annotations/{annotation_id}")
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error deleting annotation {annotation_id} from lab {lid}: {str(e)}", exc_info=True)
            raise ToolError(e)
