#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#
from __future__ import annotations

from enum import StrEnum


class OpenAPIExtension(StrEnum):
    CML_INTRODUCED = "x-cml-introduced"
    CML_CHANGED = "x-cml-changed"
    CML_CHANGE_NOTE = "x-cml-change-note"
    CML_DEPRECATED = "x-cml-deprecated"
    CML_DEPRECATION_NOTE = "x-cml-deprecation-note"


type VersionExtra = dict[OpenAPIExtension, str]


class CMLVersion(StrEnum):
    V2_10 = "2.10"

    def introduced(self) -> VersionExtra:
        return {OpenAPIExtension.CML_INTRODUCED: self}

    def changed(self, note: str | None = None) -> VersionExtra:
        result: VersionExtra = {OpenAPIExtension.CML_CHANGED: self}
        if note:
            result[OpenAPIExtension.CML_CHANGE_NOTE] = note
        return result

    def deprecated(self, note: str | None = None) -> VersionExtra:
        result: VersionExtra = {OpenAPIExtension.CML_DEPRECATED: self}
        if note:
            result[OpenAPIExtension.CML_DEPRECATION_NOTE] = note
        return result
