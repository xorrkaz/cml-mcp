#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#

import re
from typing import Annotated

from fastapi import Path
from pydantic import BaseModel, Field, model_validator

from cml_mcp.schemas.simple_common.constants import BASE_DIR
from cml_mcp.schemas.common import HTTP_URL_REG, DefinitionID, UUID4Type
from cml_mcp.schemas.labs import LabDescription, LabTitle

GitUrl = Annotated[str, Field(pattern=re.compile(HTTP_URL_REG), description="An HTTPS git URL")]

RepoName = Annotated[
    str,
    Field(
        description="The name of the repository.",
        examples=["cml-labs"],
        min_length=1,
        max_length=64,
        pattern=re.compile(r"^(?![/.])[\w.-]{1,64}(?![\n\r])$"),
    ),
]

RepoFolder = Annotated[
    str,
    Field(
        description="The name of the folder to clone in the repository.",
        examples=["cml-community"],
        min_length=1,
        max_length=255,
        pattern=re.compile(r"^(?![/.])[\w./-]{1,255}(?![\n\r])$"),
    ),
]

RepoIdPathParameter = Annotated[UUID4Type, Path(description="The ID of an available lab repository.")]

SampleLabIdPathParameter = Annotated[UUID4Type, Path(description="The ID of the specified sample lab.")]


class CreateLabRepo(BaseModel, extra="forbid"):
    """Lab repository creation"""

    url: GitUrl = Field(..., description="The URL of the repository.")
    name: RepoName = Field(..., description="The name of repository.")
    folder: RepoFolder | None = Field(
        default=None,
        description="Limit the git pull to a single folder in the repository.",
    )

    @model_validator(mode="after")
    def repo_path_validation(self):
        root = (BASE_DIR / "sample-labs").resolve()
        repo = (root / self.name).resolve()
        if not repo.is_relative_to(root):
            raise ValueError("Name is not relative the repository root.")
        if self.folder and not (repo / self.folder).resolve().is_relative_to(repo):
            raise ValueError("Folder is not relative to the repository.")
        return self


class LabRepoResponse(CreateLabRepo, extra="forbid"):
    id: UUID4Type = Field(..., description="ID of the lab repository.")


class SampleLabResponse(BaseModel, extra="forbid"):
    id: UUID4Type
    title: LabTitle
    description: LabDescription
    name: RepoName
    node_types: list[DefinitionID]
    file_path: str = Field(..., description="The relative path of the sample lab.")


class LabReposRefreshStatus(BaseModel, extra="forbid"):
    success: bool = Field(..., description="The status of the repository refresh.")
    message: str = Field(..., description="Description of the status of the repository refresh.")
    index: str = Field(
        default="Index file updated successfully",
        description="The index file status of the repository.",
    )
