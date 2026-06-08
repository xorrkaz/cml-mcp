#
# This file is part of VIRL 2
# Copyright (c) 2019-2026, Cisco Systems, Inc.
# All rights reserved.
#

import os
from pathlib import Path

DOCKER_CONFIG = "config.json"

MIME_JSON = "application/json"
MIME_TEXT = "text/plain"
MIME_YAML = "application/x-yaml"
MIME_PCAP = "application/vnd.tcpdump.pcap"

DEFAULT_VERSION = "unknown"
DEFAULT_PYATS_USERNAME = "cisco"
# ruff S105: well-known lab default for pyats/unicon, not a secret
DEFAULT_PYATS_PASSWORD = "cisco"  # noqa: S105

BYTES_IN_KB = 1024
BYTES_IN_MB = 1024**2
BYTES_IN_GB = 1024**3

HOUR_SECONDS = 3600
DAY_SECONDS = 86400

EVENT_LIMIT = 10000
EVENT_CLEAR = int(EVENT_LIMIT * 0.05)

DEFAULT_LOGIN_TIMEOUT = 10  # seconds

# from /usr/include/sys/syslog.h
# #define LOG_LOCAL6      (22<<3) /* reserved for local use */
# Python defines it like C, SyslogHandler shifts it and adds priority
TELEMETRY_LOG_LEVEL = 22

SSHD_CLUSTER_PORT = 1222

BASE_DIR = Path(os.environ.get("BASE_DIR", "/var/local/virl2"))
KNOWN_HOSTS = BASE_DIR / "secrets/admin_hosts/known_hosts"
COCKPIT_MACHINES = Path("/etc/cockpit/machines.d")
DROPFOLDER_DIRECTORY = os.environ.get(
    "DROPFOLDER_DIRECTORY", str(BASE_DIR / "dropfolder")
)
LIBVIRT_IMAGES = os.environ.get("LIBVIRT_IMAGES", "/var/lib/libvirt/images")
IMAGE_DEFINITION_DIRECTORY = f"{LIBVIRT_IMAGES}/virl-base-images"
NODE_DEFINITION_DIRECTORY = f"{LIBVIRT_IMAGES}/node-definitions"
USER_IMAGES = os.environ.get("USER_IMAGES", str(BASE_DIR / "images"))
DEFAULT_VIRL2 = "/etc/default/virl2"
IMAGES_STATE = BASE_DIR / "base_images.state"
# name of the node configuration customizer script
CONFIG_CUSTOMIZER = "cml-customizer.sh"

# keywords for libvirt XML metadata definitions
CML_NAMESPACE_URI = "http://cisco.com/cml"
CML_NS_PREFIX = "cml"
CML_ELEMENT = "cml"

# Prefix used for unmanaged switch interfaces
UMS_PREFIX = "ums-"

# Constant for IOL-specific handling
IOL = "iol"
IOL_CONFIG = "iol-config.json"
