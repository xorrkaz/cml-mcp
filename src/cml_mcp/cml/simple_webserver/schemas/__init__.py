#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#

# Compatibility aliases for the CML MCP server
# These provide consistent naming with the original schema exports
from simple_webserver.schemas.groups import GroupResponse as GroupInfoResponse

__all__ = ["GroupInfoResponse"]
