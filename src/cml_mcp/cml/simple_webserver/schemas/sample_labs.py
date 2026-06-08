#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#

from typing import Annotated

from fastapi import Path
from pydantic import BaseModel, Field

from simple_webserver.schemas.common import (
    HTTP_URL_REG,
    DefinitionID,
    OneLineStr,
    UUID4Type,
)
from simple_webserver.schemas.labs import LabDescription, LabTitle

GitUrl = Annotated[
    OneLineStr, Field(pattern=HTTP_URL_REG, description="An HTTPS git URL")
]

RepoName = Annotated[
    OneLineStr,
    Field(
        description="The name of the repository.",
        examples=["cml-labs"],
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-][a-zA-Z0-9_.-]{0,63}$",
    ),
]

RepoFolder = Annotated[
    OneLineStr,
    Field(
        description="The name of the folder to clone in the repository.",
        examples=["cml-community"],
        min_length=1,
        max_length=255,
        pattern=r"^[a-zA-Z0-9_-][a-zA-Z0-9_./-]{0,254}$",
    ),
]

RepoIdPathParameter = Annotated[
    UUID4Type, Path(description="The ID of an available lab repository.")
]

SampleLabIdPathParameter = Annotated[
    UUID4Type, Path(description="The ID of the specified sample lab.")
]


class CreateLabRepo(BaseModel, extra="forbid"):
    """Lab repository creation"""

    url: GitUrl = Field(..., description="The URL of the repository.")
    name: RepoName = Field(..., description="The name of repository.")
    folder: RepoFolder | None = Field(
        default=None,
        description="Limit the git pull to a single folder in the repository.",
    )


class LabRepoResponse(CreateLabRepo, extra="forbid"):
    id: UUID4Type = Field(..., description="ID of the lab repository.")


class SampleLabResponse(BaseModel, extra="forbid"):
    id: UUID4Type
    title: LabTitle
    description: LabDescription
    name: RepoName
    node_types: list[DefinitionID]
    file_path: OneLineStr = Field(
        ..., description="The relative path of the sample lab."
    )


class LabRepoRefreshStatus(BaseModel, extra="forbid"):
    success: bool = Field(..., description="The status of the repository refresh.")
    message: OneLineStr = Field(
        ..., description="Description of the status of the repository refresh."
    )
    index: list[OneLineStr] = Field(
        default="Index file updated successfully",
        description="The index file status of the repository.",
    )
