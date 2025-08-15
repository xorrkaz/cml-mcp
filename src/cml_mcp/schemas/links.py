#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#
from typing import Annotated

from fastapi import Body
from pydantic import BaseModel, Field

from cml_mcp.schemas.common import Label, State, UUID4Type

LinkLabel = Annotated[Label, Field(..., description="A link label.")]


class LinkCreate(BaseModel, extra="forbid"):
    src_int: UUID4Type = Field(...)
    dst_int: UUID4Type = Field(...)


class LinkConnectionInfo(BaseModel, extra="forbid"):
    interface_a: UUID4Type = Field(default=None, description="ID of the interface A.")
    interface_b: UUID4Type = Field(default=None, description="ID of the interface B.")
    node_a: UUID4Type = Field(default=None, description="ID of the node A.")
    node_b: UUID4Type = Field(default=None, description="ID of the node B.")


class Link(LinkConnectionInfo, extra="forbid"):
    """Link object."""

    id: UUID4Type = Field(default=None, description="ID of the link.")
    label: LinkLabel = Field(default=None)
    lab_id: UUID4Type = Field(default=None, description="ID of the lab.")
    link_capture_key: str = Field(default=None, max_length=64, description="The link capture key.")
    state: State = Field(default=None, description="The status of the link in the lab.")


class LinkCondition(BaseModel):
    bandwidth: int | None = Field(default=None, description="Bandwidth of the link in kbps.", ge=0, le=10000000)
    latency: int | None = Field(default=None, description="Delay of the link in ms.", ge=0, le=10000)
    delay_corr: float | int | None = Field(default=None, description="Loss correlation in percent.", ge=0, le=100)
    limit: int | None = Field(default=None, description="Limit in ms.", ge=0, le=10000)
    loss: float | int | None = Field(default=None, description="Loss of the link in percent.", ge=0, le=100)
    loss_corr: float | int | None = Field(default=None, description="Loss correlation in percent.", ge=0, le=100)
    gap: int | None = Field(default=None, description="Gap between packets in ms.", ge=0, le=10000)
    duplicate: float | int | None = Field(default=None, description="Probability of duplicates in percent.", ge=0, le=100)
    duplicate_corr: float | int | None = Field(default=None, description="Correlation of duplicates in percent.", ge=0, le=100)
    jitter: int | None = Field(default=None, description="Jitter of the link in ms.", ge=0, le=10000)
    reorder_prob: float | int | None = Field(default=None, description="Probability of re-orders in percent.", ge=0, le=100)
    reorder_corr: float | int | None = Field(default=None, description="Re-order correlation in percent.", ge=0, le=100)
    corrupt_prob: float | int | None = Field(
        default=None,
        description="Probability of corrupted frames in percent.",
        ge=0,
        le=100,
    )
    corrupt_corr: float | int | None = Field(default=None, description="Corruption correlation in percent.", ge=0, le=100)


class LinkConditionConfiguration(LinkCondition, extra="forbid"):
    enabled: bool = Field(default=True, description="Whether the conditioning is currently enabled.")


class LinkWithConditionConfig(LinkConnectionInfo, extra="forbid"):
    id: UUID4Type = Field(default=None, description="ID of the link.")
    label: LinkLabel = Field(default=None)
    conditioning: LinkConditionConfiguration = Field(default=None)


class LinkConditionStricted(LinkCondition, extra="forbid"):
    pass


class ConditionResponse(LinkConditionConfiguration, extra="forbid"):
    operational: LinkConditionStricted | None = Field(
        default=None,
        description="Additional operational data associated with the link conditioning.",
    )


LinkCreateBody = Annotated[
    LinkCreate,
    Body(description="The body is a JSON object that indicates the source " "and destination interfaces of the link to be created."),
]

LinkResponse = Annotated[Link, Field(description="The response body is a JSON link object.")]
