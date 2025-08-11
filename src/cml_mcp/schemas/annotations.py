#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#
from enum import StrEnum
from typing import Annotated, Literal

from fastapi import Body
from pydantic import BaseModel, Field
from pydantic_strict_partial import create_partial_model

from cml_mcp.schemas.common import (
    COLOR_EXAMPLES_STR,
    AnnotationColor,
    BorderStyle,
    UUID4Type,
)

CoordinateFloat = Annotated[float, Field(description="A coordinate (floating point).", ge=-15000, le=15000)]


class AnnotationTypeEnum(StrEnum):
    text = "text"
    rectangle = "rectangle"
    ellipse = "ellipse"
    line = "line"


class LineStyle(StrEnum):
    ARROW = "arrow"
    SQUARE = "square"
    CIRCLE = "circle"


class AnnotationBase(BaseModel):
    type: AnnotationTypeEnum = Field(..., description="Annotation element type.")
    border_color: AnnotationColor = Field(..., description=f"Border color, of the annotation {COLOR_EXAMPLES_STR}.")
    border_style: BorderStyle = Field(
        ...,
        description=(
            "String defining border style - 3 values corresponding to UI values are allowed. "
            '("" - solid; "2,2" - dotted; "4,2" - dashed)'
        ),
    )
    color: AnnotationColor = Field(..., description=f"Fill color of the annotation {COLOR_EXAMPLES_STR}.")
    thickness: int = Field(..., ge=1, le=32, description="Line thickness.")
    x1: CoordinateFloat = Field(..., description="Element anchor X coordinate.")
    y1: CoordinateFloat = Field(..., description="Element anchor Y coordinate.")
    z_index: int = Field(..., ge=-10240, le=10240, description="Element Z layer.")


class X2Y2Mixin(BaseModel):
    x2: CoordinateFloat = Field(..., description="Additional X value (width, radius, ..., type dependent).")
    y2: CoordinateFloat = Field(..., description="Additional Y value (height, radius, ..., type dependent).")


class RotationMixin(BaseModel):
    rotation: int = Field(..., ge=0, le=360, description="Rotation of object, in degrees.")


class TextAnnotation(AnnotationBase, RotationMixin, extra="forbid"):
    type: Literal[AnnotationTypeEnum.text]
    text_bold: bool = Field(..., description="Text style bold.")
    text_content: str = Field(..., min_length=0, max_length=8192, description="Text element content.")
    text_font: str = Field(..., min_length=0, max_length=128, description="Text element font name.")
    text_italic: bool = Field(..., description="Text style italic.")
    text_size: int = Field(..., ge=1, le=128, description="Text size in the unit specified in `text_unit`.")
    text_unit: Literal["pt", "px", "em"] = Field(..., description="Unit of the given text size.")


class RectangleAnnotation(AnnotationBase, RotationMixin, X2Y2Mixin, extra="forbid"):
    type: Literal[AnnotationTypeEnum.rectangle]
    border_radius: int = Field(..., ge=0, le=128, description="Border radius for rectangles")


class EllipseAnnotation(AnnotationBase, RotationMixin, X2Y2Mixin, extra="forbid"):
    type: Literal[AnnotationTypeEnum.ellipse]


class LineAnnotation(AnnotationBase, X2Y2Mixin, extra="forbid"):
    type: Literal[AnnotationTypeEnum.line]
    line_start: LineStyle | None = Field(..., description="Line arrow start style.")
    line_end: LineStyle | None = Field(..., description="Line arrow end style.")


AnnotationCreate = Annotated[
    TextAnnotation | RectangleAnnotation | EllipseAnnotation | LineAnnotation,
    Field(discriminator="type"),
]

TextAnnotationUpdate = create_partial_model(model=TextAnnotation, required_fields=["type"])
RectangleAnnotationUpdate = create_partial_model(model=RectangleAnnotation, required_fields=["type"])
EllipseAnnotationUpdate = create_partial_model(model=EllipseAnnotation, required_fields=["type"])
LineAnnotationUpdate = create_partial_model(model=LineAnnotation, required_fields=["type"])

AnnotationUpdate = Annotated[
    TextAnnotationUpdate | RectangleAnnotationUpdate | EllipseAnnotationUpdate | LineAnnotationUpdate,
    Field(discriminator="type"),
]

AnnotationCreateBody = Annotated[
    TextAnnotation | RectangleAnnotation | EllipseAnnotation | LineAnnotation,
    Body(discriminator="type"),
]

AnnotationUpdateBody = Annotated[
    TextAnnotationUpdate | RectangleAnnotationUpdate | EllipseAnnotationUpdate | LineAnnotationUpdate,
    Body(discriminator="type"),
]

AnnotationUuidDescription = "Annotation Unique identifier."


class TextAnnotationResponse(TextAnnotation, extra="forbid"):
    id: UUID4Type = Field(..., description=AnnotationUuidDescription)


class RectangleAnnotationResponse(RectangleAnnotation, extra="forbid"):
    id: UUID4Type = Field(..., description=AnnotationUuidDescription)


class EllipseAnnotationResponse(EllipseAnnotation, extra="forbid"):
    id: UUID4Type = Field(..., description=AnnotationUuidDescription)


class LineAnnotationResponse(LineAnnotation, extra="forbid"):
    id: UUID4Type = Field(..., description=AnnotationUuidDescription)


AnnotationResponse = Annotated[
    TextAnnotationResponse | RectangleAnnotationResponse | EllipseAnnotationResponse | LineAnnotationResponse,
    Field(
        description="The response body is a JSON annotation object.",
        discriminator="type",
    ),
]
