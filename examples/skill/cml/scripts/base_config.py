# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "click>=8.0",
# ]
# ///
#
# Run with:  uv run base_config.py --node-type iol-xe --hostname R1
# uv will automatically create an isolated environment with the required
# dependencies listed above — nothing is installed into your system Python.

import math
import logging

import click  # pyright: ignore[reportMissingImports]

# Module-level logger — callers that import this module can configure logging as needed
log = logging.getLogger(__name__)

# Node types that share the Alpine Linux shell-script boot config format
ALPINE_LIKE_NODES = ["desktop", "server", "alpine"]

# Node types supported by this script — used for CLI help text and error messages
SUPPORTED_NODE_TYPES = ["iol-xe", "ioll2-xe"] + ALPINE_LIKE_NODES


def get_initial_node_config(
    node_type: str,
    hostname: str,
    interface_count: int,
) -> str:
    """Generates a mandatory starting configuration for a given node type in CML.

    Custom configuration can be added after this base configuration for each type.

    Args:
        node_type: The type of the node (e.g., 'iol-xe', 'desktop').
        hostname: The hostname to set for the node.
        interface_count: The number of interfaces on the node.

    Returns:
        The initial configuration string for the node, or an empty string if
        the node type is not recognised.
    """
    base_config = ""

    # IOL-XE interfaces are grouped into modules of 4.
    # Pre-configuring every interface prevents IOS XE from dropping into the
    # initial configuration dialog on first boot.
    iol_xe_interface_module_count = math.ceil(interface_count / 4)

    iol_xe_interface_init_config = ""
    for mod_num in range(0, iol_xe_interface_module_count):
        iol_xe_interface_init_config += f"""
interface range Ethernet {mod_num}/0 - 3
 no ip address
 shutdown
!
"""

    iol_xe_config = f"""
!
hostname {hostname}
!
! In order to avoid entering a configuration dialog
! on boot, please ensure that all ethernet interfaces
! have some ip configuration present here such as the
! example below:
!
{iol_xe_interface_init_config}
!
ip domain name example.com
no ip domain lookup
!
username cisco privilege 15 secret cisco
!
! Add additional base configuration as needed below
"""

    ioll2_xe_config = f"""
!
hostname {hostname}
!
!
ip domain name example.com
no ip domain lookup
!
username cisco privilege 15 secret cisco
!
! Add additional base configuration as needed below
"""

    # desktop, server, and alpine nodes are all Alpine Linux-based.
    # Their "config" is a shell script sourced at boot time.
    alpine_config = f"""
# this is a shell script which will be sourced at boot
hostname {hostname}
# configurable user account
USERNAME=cisco
PASSWORD=cisco
# Standard command aliases
echo 'alias ping="ping -c 4"' >> /etc/profile.d/aliases.sh

# Add additional base configuration as needed below
"""

    if node_type == "iol-xe":
        base_config = iol_xe_config
    elif node_type == "ioll2-xe":
        base_config = ioll2_xe_config
    elif node_type in ALPINE_LIKE_NODES:
        base_config = alpine_config
    else:
        log.warning("No configuration template found for node type '%s'.", node_type)

    return base_config.strip()


@click.command()
@click.option(
    "--node-type",
    "-t",
    required=True,
    help=f"CML node type. Supported values: {', '.join(SUPPORTED_NODE_TYPES)}.",
)
@click.option(
    "--hostname",
    "-n",
    required=True,
    help="Hostname to assign to the node.",
)
@click.option(
    "--interface-count",
    "-i",
    default=4,
    show_default=True,
    type=int,
    help="Number of interfaces on the node (used to pre-configure IOL-XE interface modules).",
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Enable debug logging.",
)
def main(node_type: str, hostname: str, interface_count: int, debug: bool) -> None:
    """Generate a base node configuration for use in a Cisco Modeling Labs (CML) lab.

    The generated configuration is printed to stdout so it can be piped directly
    into the CML MCP server's configure_cml_node tool or redirected to a file.

    Example usage:

        uv run base_config.py --node-type iol-xe --hostname R1 --interface-count 8
    """
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    log.debug(
        "Generating config: node_type=%s, hostname=%s, interface_count=%d",
        node_type,
        hostname,
        interface_count,
    )

    config = get_initial_node_config(node_type, hostname, interface_count)

    if not config:
        # Surface a clear error when an unsupported node type is requested
        raise click.UsageError(
            f"No configuration template found for node type '{node_type}'. " f"Supported types: {', '.join(SUPPORTED_NODE_TYPES)}"
        )

    # Print config to stdout so the caller can capture or redirect it
    click.echo(config)


if __name__ == "__main__":
    main()  # type: ignore[call-arg]  # click decorators handle argument injection at runtime
