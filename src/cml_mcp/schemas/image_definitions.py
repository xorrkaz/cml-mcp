#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#
import re

from pydantic import BaseModel, ConfigDict, Field

from cml_mcp.schemas.common import DefinitionID, FilePath
from cml_mcp.schemas.nodes import NodeConfigurationContent


class Pyats(BaseModel, extra="forbid"):
    username: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        description="The pyATS username to be used with this image.",
    )
    password: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        description="The pyATS password to be used with this image.",
    )


class ImageDefinition(BaseModel, extra="forbid"):
    id: DefinitionID = Field(..., description="The identifier of this image definition.")
    node_definition_id: DefinitionID = Field(..., description="Node definition ID for the image definition.")
    label: str = Field(
        ...,
        description="A required label for the image definition.",
        min_length=1,
        max_length=64,
    )
    disk_image: FilePath = Field(..., description="A source image for the image definition.")
    efi_boot: bool = Field(
        default=None,
        description="Whether to use EFI for booting.",
    )
    sha256: str = Field(
        default=None,
        description="SHA256 of the disk_image (optional)",
        examples=["58ce6f1271ae1c8a2006ff7d3e54e9874d839f573d8009c20154ad0f2fb0a225"],
        min_length=64,
        max_length=64,
        pattern=re.compile(r"^[a-fA-F\d]{64}(?![\n\r])$"),
    )
    schema_version: str = Field(
        default=None,
        description="The image definition schema version.",
        examples=["0.0.1"],
        min_length=1,
        max_length=32,
    )
    description: str = Field(
        default=None,
        min_length=0,
        max_length=4096,
        description="An optional description for the image definition.",
    )
    disk_image_2: FilePath = Field(default=None, description="A second source image for the image definition.")
    disk_image_3: FilePath = Field(default=None, description="A third source image for the image definition.")
    disk_image_4: FilePath = Field(default=None, description="A fourth source image for the image definition.")
    read_only: bool = Field(
        default=None,
        description="Whether the image definition can be updated or deleted.",
    )
    configuration: NodeConfigurationContent = None
    pyats: Pyats | None = None
    ram: int | None = Field(default=None, ge=1, le=1048576, description="Memory (MiB).")
    cpus: int | None = Field(default=None, ge=1, le=128, description="CPUs.")
    cpu_limit: int | None = Field(default=None, ge=20, le=100, description="CPU Limit.")
    data_volume: int | None = Field(default=None, ge=0, le=4096, description="Data Disk Size (GiB).")
    boot_disk_size: int | None = Field(default=None, ge=0, le=4096, description="Boot Disk Size (GiB).")
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "alpine-3-10-base",
                "node_definition_id": "lxc",
                "description": "Alpine Linux and network tools",
                "label": "Alpine 3.10",
                "disk_image": "alpine-3-10-base.qcow2",
                "read_only": True,
                "ram": None,
                "cpus": None,
                "data_volume": None,
                "boot_disk_size": None,
            }
        }
    )
