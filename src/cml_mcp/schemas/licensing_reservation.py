#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#
from typing import Annotated

from fastapi import Body
from pydantic import Field

LicensingReservationModeBodyParameter = Annotated[bool, Body(description="The license reservation feature status.")]

LicensingReservationRequestCode = Annotated[str, Field(description="Reservation request code for the CSSM.")]

LicensingAuthorizationCodeBodyParameter = Annotated[
    str,
    Body(
        description="Authorization request code from the CSSM.",
        pattern=r"^[a-zA-Z0-9,_.:<>=/+ -]{1,8192}$",
    ),
]

LicensingConfirmationCode = Annotated[str | None, Field(description="The confirmation code from a completed reservation.")]

LicensingReturnCode = Annotated[str | None, Field(description="The return code from a released reservation.")]

LicensingDiscardCode = Annotated[str, Field(description="The discard code for an already cancelled reservation.")]
