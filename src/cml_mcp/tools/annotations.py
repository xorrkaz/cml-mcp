# Copyright (c) 2025-2026  Cisco Systems, Inc.
# All rights reserved.

"""
Annotation management tools for CML MCP server.
"""

import logging

import httpx
from fastmcp import Context
from fastmcp.exceptions import ToolError

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
from cml_mcp.tools.dependencies import elicit_confirmation, get_cml_client_dep

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
        Get all visual annotations (text labels, shapes, lines) on a lab's canvas by lab UUID.

        Examples:
        - "Show me the annotations on my lab"
        - "List all labels and shapes in lab abc123"
        - "What's drawn on the OSPF lab canvas?"
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
            logger.exception("Error getting annotations for lab %s", lid)
            raise ToolError(e)

    # Source schema: TextAnnotation (cml/simple_webserver/schemas/annotations.py)
    # Exposed: x1, y1, border_color, border_style, color, thickness, z_index, rotation,
    #          text_bold, text_content, text_font, text_italic, text_size, text_unit
    # Omitted: type (injected as "text")
    @mcp.tool(
        annotations={
            "title": "Add Text Annotation",
            "readOnlyHint": False,
            "destructiveHint": False,
        },
    )
    async def add_text_annotation(
        lid: UUID4Type,
        x1: float,
        y1: float,
        text_content: str,
        text_font: str,
        text_size: int,
        text_unit: str,
        text_bold: bool,
        text_italic: bool,
        border_color: str,
        border_style: str,
        color: str,
        thickness: int,
        z_index: int,
        rotation: int,
    ) -> UUID4Type:
        """
        Add a text label annotation to a lab canvas. Returns the annotation UUID.

        Required: x1, y1 (coords -15000 to 15000), text_content (0-8192 chars), text_font (0-128 chars),
        text_size (1-128), text_unit ("pt"/"px"/"em"), text_bold, text_italic (bool),
        border_color, color (e.g., "#FF0000"), border_style (""/"2,2"/"4,2"), thickness (1-32),
        z_index (-10240 to 10240), rotation (0-360 degrees).

        Examples:
        - "Add a 'Core Network' text label at position 0,0 in my lab"
        - "Label the router cluster at coordinates 100,200"
        - "Put a bold red 'IMPORTANT' note at -50,-50"
        """
        client = get_cml_client_dep()
        try:
            annotation = TextAnnotation(
                type="text",
                x1=x1,
                y1=y1,
                text_content=text_content,
                text_font=text_font,
                text_size=text_size,
                text_unit=text_unit,
                text_bold=text_bold,
                text_italic=text_italic,
                border_color=border_color,
                border_style=border_style,
                color=color,
                thickness=thickness,
                z_index=z_index,
                rotation=rotation,
            )
            resp = await client.post(
                f"/labs/{lid}/annotations",
                data=annotation.model_dump(mode="json", exclude_defaults=True, exclude_none=True),
            )
            return UUID4Type(resp["id"])
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error adding text annotation to lab %s", lid)
            raise ToolError(e)

    # Source schema: RectangleAnnotation (cml/simple_webserver/schemas/annotations.py)
    # Exposed: x1, y1, x2, y2, border_color, border_style, color, thickness, z_index, rotation, border_radius
    # Omitted: type (injected as "rectangle")
    @mcp.tool(
        annotations={
            "title": "Add Rectangle Annotation",
            "readOnlyHint": False,
            "destructiveHint": False,
        },
    )
    async def add_rectangle_annotation(
        lid: UUID4Type,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        border_color: str,
        border_style: str,
        color: str,
        thickness: int,
        z_index: int,
        rotation: int,
        border_radius: int,
    ) -> UUID4Type:
        """
        Add a rectangle shape annotation to a lab canvas. Returns the annotation UUID.

        Required: x1, y1 (anchor coords -15000 to 15000), x2, y2 (WIDTH and HEIGHT from anchor, not corners!),
        border_color, color (e.g., "#FF0000"), border_style (""/"2,2"/"4,2"), thickness (1-32),
        z_index (-10240 to 10240), rotation (0-360 degrees), border_radius (0-128).

        Examples:
        - "Draw a red rectangle around the routers in lab abc123"
        - "Add a blue box at 100,100 with width 200 height 150"
        - "Create a rounded rectangle to highlight the core switches"
        """
        client = get_cml_client_dep()
        try:
            annotation = RectangleAnnotation(
                type="rectangle",
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
                border_color=border_color,
                border_style=border_style,
                color=color,
                thickness=thickness,
                z_index=z_index,
                rotation=rotation,
                border_radius=border_radius,
            )
            resp = await client.post(
                f"/labs/{lid}/annotations",
                data=annotation.model_dump(mode="json", exclude_defaults=True, exclude_none=True),
            )
            return UUID4Type(resp["id"])
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error adding rectangle annotation to lab %s", lid)
            raise ToolError(e)

    # Source schema: EllipseAnnotation (cml/simple_webserver/schemas/annotations.py)
    # Exposed: x1, y1, x2, y2, border_color, border_style, color, thickness, z_index, rotation
    # Omitted: type (injected as "ellipse")
    @mcp.tool(
        annotations={
            "title": "Add Ellipse Annotation",
            "readOnlyHint": False,
            "destructiveHint": False,
        },
    )
    async def add_ellipse_annotation(
        lid: UUID4Type,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        border_color: str,
        border_style: str,
        color: str,
        thickness: int,
        z_index: int,
        rotation: int,
    ) -> UUID4Type:
        """
        Add an ellipse shape annotation to a lab canvas. Returns the annotation UUID.

        Required: x1, y1 (anchor coords -15000 to 15000), x2, y2 (WIDTH and HEIGHT from anchor),
        border_color, color (e.g., "#FF0000"), border_style (""/"2,2"/"4,2"), thickness (1-32),
        z_index (-10240 to 10240), rotation (0-360 degrees).

        Examples:
        - "Draw a green ellipse around the firewall cluster"
        - "Add a circle at position 50,50 with radius 100"
        - "Highlight the DMZ with a yellow oval"
        """
        client = get_cml_client_dep()
        try:
            annotation = EllipseAnnotation(
                type="ellipse",
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
                border_color=border_color,
                border_style=border_style,
                color=color,
                thickness=thickness,
                z_index=z_index,
                rotation=rotation,
            )
            resp = await client.post(
                f"/labs/{lid}/annotations",
                data=annotation.model_dump(mode="json", exclude_defaults=True, exclude_none=True),
            )
            return UUID4Type(resp["id"])
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error adding ellipse annotation to lab %s", lid)
            raise ToolError(e)

    # Source schema: LineAnnotation (cml/simple_webserver/schemas/annotations.py)
    # Exposed: x1, y1, x2, y2, border_color, border_style, color, thickness, z_index, line_start, line_end
    # Omitted: type (injected as "line")
    @mcp.tool(
        annotations={
            "title": "Add Line Annotation",
            "readOnlyHint": False,
            "destructiveHint": False,
        },
    )
    async def add_line_annotation(
        lid: UUID4Type,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        border_color: str,
        border_style: str,
        color: str,
        thickness: int,
        z_index: int,
        line_start: str | None,
        line_end: str | None,
    ) -> UUID4Type:
        """
        Add a line annotation to a lab canvas. Returns the annotation UUID.

        Required: x1, y1 (start coords -15000 to 15000), x2, y2 (absolute end coords),
        border_color, color (e.g., "#0000FF"), border_style (""/"2,2"/"4,2"), thickness (1-32),
        z_index (-10240 to 10240), line_start, line_end ("arrow"/"square"/"circle" or None).

        Examples:
        - "Add an arrow pointing from R1 to R2"
        - "Draw a line from 0,0 to 200,200 with arrow on both ends"
        - "Connect the firewall to the internet cloud with a dashed line"
        """
        client = get_cml_client_dep()
        try:
            annotation = LineAnnotation(
                type="line",
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
                border_color=border_color,
                border_style=border_style,
                color=color,
                thickness=thickness,
                z_index=z_index,
                line_start=line_start,
                line_end=line_end,
            )
            resp = await client.post(
                f"/labs/{lid}/annotations",
                data=annotation.model_dump(mode="json", exclude_defaults=True, exclude_none=True),
            )
            return UUID4Type(resp["id"])
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error adding line annotation to lab %s", lid)
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
        Delete a single annotation by lab and annotation UUID.

        CRITICAL: Destructive. Always ask "Confirm deletion of [annotation]?" and wait for the
        user's "yes" before invoking this tool.

        Examples:
        - "Delete the 'Core Network' label"
        - "Remove annotation xyz from my lab"
        - "Get rid of the red rectangle"
        """
        client = get_cml_client_dep()
        try:
            if not await elicit_confirmation(ctx, "Are you sure you want to delete the annotation?"):
                raise Exception("Delete operation cancelled by user.")
            await client.delete(f"/labs/{lid}/annotations/{annotation_id}")
            return True
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error deleting annotation %s from lab %s", annotation_id, lid)
            raise ToolError(e)
