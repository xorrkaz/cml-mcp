#
# This file is part of VIRL 2
# Copyright (c) 2019-2025, Cisco Systems, Inc.
# All rights reserved.
#

import os
from pathlib import Path

MIME_JSON = "application/json"
MIME_TEXT = "text/plain"
MIME_YAML = "application/x-yaml"

DEFAULT_VERSION = "unknown"
DEFAULT_PYATS_USERNAME = "cisco"
DEFAULT_PYATS_PASSWORD = "cisco"

BYTES_IN_MB = 1024**2
BYTES_IN_GB = 1024**3

EVENT_LIMIT = 10000
EVENT_CLEAR = int(EVENT_LIMIT * 0.05)


TELEMETRY_LOG_LEVEL = 22

SSHD_CLUSTER_PORT = 1222

BASE_DIR = Path(os.environ.get("BASE_DIR", "/var/local/virl2"))
KNOWN_HOSTS = BASE_DIR / "secrets/admin_hosts/known_hosts"
COCKPIT_MACHINES = Path("/etc/cockpit/machines.d")
DROPFOLDER_DIRECTORY = os.environ.get("DROPFOLDER_DIRECTORY", str(BASE_DIR / "dropfolder"))
LIBVIRT_IMAGES = os.environ.get("LIBVIRT_IMAGES", "/var/lib/libvirt/images")
IMAGE_DEFINITION_DIRECTORY = f"{LIBVIRT_IMAGES}/virl-base-images"
NODE_DEFINITION_DIRECTORY = f"{LIBVIRT_IMAGES}/node-definitions"
USER_IMAGES = os.environ.get("USER_IMAGES", str(BASE_DIR / "images"))
DEFAULT_VIRL2 = "/etc/default/virl2"
IMAGES_STATE = BASE_DIR / "base_images.state"
CONFIG_CUSTOMIZER = "cml-customizer.sh"

CML_NAMESPACE_URI = "http://cisco.com/cml"
CML_NS_PREFIX = "cml"

UMS_PREFIX = "ums-"

QCOW2 = "qcow2"
QCOW = "qcow"
IOL = "iol"
TAR = "tar"
TARGZ = "tar.gz"
SUPPORTED_IMAGE_FORMATS = [QCOW2, QCOW, IOL, TAR, TARGZ]
