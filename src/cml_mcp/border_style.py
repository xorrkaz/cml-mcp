# Copyright (c) 2025-2026  Cisco Systems, Inc.
# All rights reserved.

"""Annotation border_style wire conversion for MCP tools."""

from __future__ import annotations

from typing import Literal

CANONICAL_BORDER_STYLES = ("solid", "dotted", "dashed")
BorderStyleLiteral = Literal["solid", "dotted", "dashed"]

_LEGACY_TO_CANONICAL: dict[str, str] = {
    "": "solid",
    "2,2": "dotted",
    "4,2": "dashed",
}

_CANONICAL_TO_LEGACY: dict[str, str] = {v: k for k, v in _LEGACY_TO_CANONICAL.items()}


def _to_canonical(value: str) -> str:
    if value in CANONICAL_BORDER_STYLES:
        return value
    return _LEGACY_TO_CANONICAL[value]


def border_style_from_api(value: str) -> str:
    """Normalize CML REST API border_style to canonical MCP values."""
    return _to_canonical(value)


def border_style_for_api(value: str) -> str:
    """Serialize MCP border_style to legacy CML REST API wire values."""
    return _CANONICAL_TO_LEGACY[_to_canonical(value)]


def _map_topology_border_styles(payload: dict, transform) -> dict:
    for key in ("annotations", "smart_annotations"):
        for item in payload.get(key, []):
            if isinstance(item, dict) and "border_style" in item:
                item["border_style"] = transform(str(item["border_style"]))
    return payload


def wire_topology_border_styles(payload: dict) -> dict:
    """Convert canonical border_style values in a topology import payload."""
    return _map_topology_border_styles(payload, border_style_for_api)


def normalize_topology_border_styles(payload: dict) -> dict:
    """Convert legacy border_style values in a topology payload to canonical MCP values."""
    return _map_topology_border_styles(payload, border_style_from_api)
