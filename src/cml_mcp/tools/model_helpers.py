# Copyright (c) 2025-2026  Cisco Systems, Inc.
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.

# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

"""
Helper utilities for lenient Pydantic model construction from LLM-generated dicts.

When tools are called by certain clients, the LLM may:
- Include extra fields not in the schema (rejected by extra="forbid")
- Omit optional-ish fields that have no default in the schema

This module provides a ``lenient_construct`` function that strips unknown fields
before calling the model constructor, so the upstream CML schemas stay strict
while the MCP tool layer remains forgiving.
"""

import json
import logging
from typing import TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger("cml-mcp.tools.model_helpers")

T = TypeVar("T", bound=BaseModel)


def _get_all_field_names(model_cls: type[BaseModel]) -> set[str]:
    """Return all known field names for a Pydantic model (including aliases)."""
    names: set[str] = set()
    for name, field_info in model_cls.model_fields.items():
        names.add(name)
        if field_info.alias:
            names.add(field_info.alias)
        if field_info.validation_alias and isinstance(field_info.validation_alias, str):
            names.add(field_info.validation_alias)
    return names


def parse_json_arg(value: "dict | str | BaseModel") -> dict:
    """
    Ensure a tool argument is a dict.

    The ai-gateway may serialize complex tool arguments as JSON **strings**
    instead of parsed dicts.  This helper normalises both representations
    so downstream code always receives a ``dict``.
    """
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError(f"Could not parse JSON string argument: {exc}") from exc
        if not isinstance(parsed, dict):
            raise TypeError(f"Expected JSON object, got {type(parsed).__name__}")
        return parsed
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    raise TypeError(f"Expected dict, str, or BaseModel; got {type(value).__name__}")


def lenient_construct(model_cls: type[T], data: "dict | str") -> T:
    """
    Construct a Pydantic model from a dict, stripping unknown fields.

    This avoids ``extra="forbid"`` validation errors when LLMs include
    unexpected fields in tool arguments.  Unknown keys are logged at DEBUG
    level and silently discarded.

    Raises the original ``ValidationError`` (with a friendlier message) if
    required fields are still missing after stripping.
    """
    data = parse_json_arg(data)
    known = _get_all_field_names(model_cls)
    extra = {k for k in data if k not in known}
    if extra:
        logger.debug(
            "Stripping unknown fields from %s input: %s",
            model_cls.__name__,
            extra,
        )

    cleaned = {k: v for k, v in data.items() if k in known}

    try:
        return model_cls(**cleaned)
    except ValidationError as ve:
        # Re-raise with context about which model failed
        raise ValidationError.from_exception_data(
            title=model_cls.__name__,
            line_errors=ve.errors(),
        ) from ve
