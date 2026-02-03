#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#
from typing import Annotated

from fastapi import Body
from pydantic import BaseModel, Field
from simple_webserver.schemas.common import (
    COLOR_EXAMPLES_STR,
    AnnotationColor,
    BorderStyle,
    UUID4Type,
)


class SmartAnnotationBase(BaseModel):
    """Configuration for a smart annotation with various styling and positioning
    attributes."""

    is_on: bool = Field(default=True, description="Indicates if the smart annotation is active or not.")
    padding: int = Field(default=35, ge=1, le=200, description="Padding around the smart annotation.")
    tag: str = Field(
        default=None,
        min_length=1,
        max_length=64,
        description="A tag associated with the smart annotation.",
    )
    label: str = Field(
        default=None,
        min_length=0,
        max_length=256,
        description="A label of the smart annotation. Defaults to the tag.",
    )
    tag_offset_x: int = Field(
        default=0,
        ge=-1000,
        le=1000,
        description="Horizontal offset of the smart annotation's tag.",
    )
    tag_offset_y: int = Field(
        default=0,
        ge=-1000,
        le=1000,
        description="Vertical offset of the smart annotation's tag.",
    )
    tag_size: int = Field(
        default=14,
        ge=1,
        le=128,
        description="Font size of the smart annotation's tag text.",
    )
    group_distance: int = Field(
        default=400,
        ge=0,
        le=10000,
        description="Distance between grouped smart annotations.",
    )
    thickness: int = Field(
        default=1,
        ge=1,
        le=32,
        description="Thickness of the smart annotation’s border or line.",
    )
    border_style: BorderStyle = Field(
        default=BorderStyle.SOLID,
        description=(
            "Border style of the smart annotation - 3 values corresponding "
            'to UI values are allowed ("" - solid; "2,2" - dotted; "4,2" - dashed).'
        ),
    )
    fill_color: AnnotationColor = Field(
        default=None,
        description=f"Fill color of the smart annotation {COLOR_EXAMPLES_STR}.",
    )
    border_color: AnnotationColor = Field(
        default="#00000080",
        description=f"Border color of the smart annotation {COLOR_EXAMPLES_STR}.",
    )
    z_index: int = Field(
        default=0,
        ge=-10240,
        le=10240,
        description="Z-index of the smart annotation for stacking order.",
    )


class SmartAnnotation(SmartAnnotationBase, extra="forbid"):
    """Smart annotation element data."""

    id: UUID4Type = Field(None, description="Unique identifier for the smart annotation.")


class SmartAnnotationUpdate(SmartAnnotationBase, extra="forbid"):
    """Parameters that the smart annotation will be updated with."""

    pass


SmartAnnotationUpdateBody = Annotated[
    SmartAnnotationUpdate,
    Body(description="A JSON object with properties to update a smart annotation. " "Only supplied properties will be updated."),
]

SmartAnnotationResponse = Annotated[SmartAnnotation, Field(description="The response body is a JSON annotation object.")]
