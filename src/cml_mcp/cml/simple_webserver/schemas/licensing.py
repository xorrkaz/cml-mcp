#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#
from datetime import datetime
from typing import Annotated

from fastapi import Body
from pydantic import BaseModel, Field, conlist

from simple_webserver.schemas.common import (
    DOMAIN_REG,
    HTTP_URL_REG,
    GenericDescription,
    Hostname,
    OneLineStr,
)


class LicensingTimeInfo(BaseModel):
    """Timing information on communication with SSMS."""

    succeeded: datetime | None = Field(
        ...,
        description="The time when the given request last completed with success.",
    )
    attempted: datetime | None = Field(
        ..., description="The time when the given request was last made."
    )
    scheduled: datetime | None = Field(
        ...,
        description="The time when the given request will be made next without intervention.",
    )
    status: OneLineStr | None = Field(
        ..., description="The status result of the last attempt."
    )
    failure: OneLineStr | None = Field(
        ..., description="The failure reason of the last attempt."
    )
    success: OneLineStr | None = Field(
        ..., description="The status of the last communication attempt."
    )


class LicensingFeatureIdMixIn(BaseModel):
    """Individually licensed feature description."""

    id: OneLineStr = Field(
        ...,
        description="Identification tag of the feature.",
        pattern=r"^[a-zA-Z\d._,-]{1,128}$",
        examples=[
            "regid.2019-10.com.cisco.CML_NODE_COUNT,1.0_2607650b-6ca8-46d5-81e5-e6688b7383c4"
        ],
    )


LicensingProductLicenseBodyParameter = Annotated[
    OneLineStr,
    Body(
        description="Product license.",
        pattern=r"^[a-zA-Z0-9_]{1,20}$",
    ),
]


class LicensingTransportProxy(BaseModel, extra="forbid"):
    """HTTP Proxy to contact SSMS."""

    server: OneLineStr | None = Field(
        ...,
        description="Domain name of the HTTP proxy server.",
        examples=["lab-proxy.example.com"],
        pattern=rf"^({DOMAIN_REG})$",
        min_length=1,
        max_length=256,
    )
    port: int | None = Field(
        ...,
        description="Port of the HTTP proxy server.",
        ge=1,
        le=65535,
        examples=[80],
    )


class Udi(BaseModel, extra="forbid"):
    hostname: Hostname = Field(
        default=None,
        description="Hostname of this product instance within SSMS associated with registration.",
    )
    product_uuid: OneLineStr = Field(
        default=None,
        description="ID of this product instance within SSMS associated with registration.",
    )


class Registration(BaseModel, extra="forbid"):
    status: OneLineStr = Field(
        default=None,
        description="The current registration status of this product instance.",
    )
    smart_account: OneLineStr | None = Field(
        default=None,
        description="Name of the customer Smart Account associated with registration.",
    )
    virtual_account: OneLineStr | None = Field(
        default=None,
        description="Name of the virtual sub-account associated with registration.",
    )
    register_time: LicensingTimeInfo = Field(default=None)
    renew_time: LicensingTimeInfo = Field(default=None)
    expires: datetime | None = Field(
        default=None,
        description="The time current valid registration is due to expire.",
    )


class Authorization(BaseModel, extra="forbid"):
    status: OneLineStr = Field(
        default=None,
        description="The current authorization status of this product instance.",
    )
    renew_time: LicensingTimeInfo = Field(default=None)
    expires: datetime | None = Field(
        default=None,
        description="The time current valid authorization is due to expire.",
    )


class ProductLicense(BaseModel, extra="forbid"):
    active: OneLineStr = Field(
        default=None, description="Currently active product license."
    )
    is_enterprise: bool = Field(
        default=None,
        description="Whether the active product license includes enterprise features.",
    )


class LicensingFeature(LicensingFeatureIdMixIn, extra="forbid"):
    name: OneLineStr = Field(default=None, description="Short name of the feature.")
    description: GenericDescription = Field(
        default=None, description="Description of the feature."
    )
    version: OneLineStr = Field(default=None, description="Version of the feature.")
    in_use: int = Field(
        default=None,
        description="Currently requested count of uses for this feature.",
    )
    status: OneLineStr = Field(
        default=None,
        description="Current authorization status for this individual feature.",
    )
    min: int = Field(
        default=None, description="The minimal count for this individual feature.", ge=0
    )
    max: int = Field(
        default=None, description="The maximal count for this individual feature.", ge=0
    )
    # ruff N815: camelCase required to match Smart Licensing API response
    minEndDate: datetime | None = Field(
        default=None,
        description="First date in which a valid license reservation expires.",
    )
    # ruff N815: camelCase required to match Smart Licensing API response
    maxEndDate: datetime | None = Field(
        default=None,
        description="Last date in which a valid license reservation expires.",
    )


class LicensingTransportBase(BaseModel):
    """Configuration for Smart Licensing transport."""

    proxy: LicensingTransportProxy = Field(...)
    ssms: OneLineStr | None = Field(
        default="https://smartreceiver.cisco.com/licservice/license",
        description="The URL.",
        pattern=HTTP_URL_REG,
        min_length=1,
        max_length=256,
        examples=[
            "https://ssms-satellite.example.com:8443/Transportgateway/services/DeviceRequestHandler"
        ],
    )


class LicensingTransport(LicensingTransportBase, extra="forbid"):
    pass


class LicensingTransportResponse(LicensingTransportBase, extra="forbid"):
    default_ssms: OneLineStr = Field(
        ...,
        description="The main production URL which shall be set unless changed by user.",
    )


class LicensingStatus(BaseModel, extra="forbid"):
    """Configuration and status of Smart Licensing."""

    udi: Udi = Field(default=None, description="The product instance identifier.")
    registration: Registration = Field(
        default=None, description="Product registration status."
    )
    authorization: Authorization = Field(
        default=None, description="Product overall feature authorization status."
    )
    reservation_mode: bool = Field(
        default=None, description="The current reservation mode status."
    )
    features: list[LicensingFeature] = Field(default_factory=list)
    product_license: ProductLicense = Field(default=None)
    transport: LicensingTransportResponse = Field(default=None)


class LicensingFeatureCount(LicensingFeatureIdMixIn, extra="forbid"):
    count: int = Field(..., description="Requested count of this feature.", ge=0)


LicensingFeatureCounts = Annotated[
    conlist(LicensingFeatureCount, min_length=1, max_length=2),
    Field(description="List of individual feature explicit counts."),
]


class LicensingRegistration(BaseModel, extra="forbid"):
    token: OneLineStr = Field(
        ...,
        description="A token generated by the target SSMS instance to authorize product to it.",
        pattern=r"^[a-zA-Z\d+/%=-]{1,256}$",
    )
    reregister: bool = Field(
        default=False, description="Request reregistration from the current SSMS."
    )


LicensingRegistrationBody = Annotated[LicensingRegistration, Body(...)]
