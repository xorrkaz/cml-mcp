import logging

import yaml
from unicon import Connection

from cml_mcp.cml_client import CMLClient
from cml_mcp.cml.simple_webserver.schemas.common import UUID4Type
from cml_mcp.cml.simple_webserver.schemas.nodes import NodeLabel

logger = logging.getLogger("cml-mcp.tools.unicon_cli")

TERMWS_BINARY = "/usr/local/bin/termws"
TIMEOUT = 300


def unicon_send_cli_command_sync(
    client: CMLClient,
    lid: UUID4Type,
    label: NodeLabel,  # pyright: ignore[reportInvalidTypeForm]
    commands: str,
    config_command: bool,
) -> str:
    resp = client.vclient._session.get(f"/labs/{lid}/pyats_testbed")
    pyats_data = yaml.safe_load(resp.text)
    device_pyats_data = pyats_data["devices"][label]

    resp = client.vclient._session.get(f"/labs/{lid}/nodes", params={"data": True, "operational": True})
    if resp.status_code != 200:
        raise Exception("Cannot retrieve node console key. Is the node running?")

    nodes = resp.json()
    for node in nodes:
        if node["label"] == label:
            consoles = node["operational"]["serial_consoles"]
            console_key = consoles[0]["console_key"]
            break
    else:
        raise Exception("Cannot retrieve node console key. Is the node running?")

    connect_command = f"{TERMWS_BINARY} -host [::1] -port 8006 -internal {console_key}"
    connection = None
    try:
        connection = Connection(
            hostname=label,
            start=[connect_command],
            os=device_pyats_data["os"],
            series=device_pyats_data.get("series"),  # can be None
            credentials=device_pyats_data["credentials"],
            log_stdout=False,
            log_buffer=True,
            learn_hostname=True,
            learn_tokens=False,
            connection_timeout=10,
            prompt_recovery=True,
        )
        connection.settings.GRACEFUL_DISCONNECT_WAIT_SEC = 0
        connection.settings.POST_DISCONNECT_WAIT_SEC = 0
        connection.settings.LEARN_DEVICE_TOKENS = False

        if config_command:
            result = connection.configure(commands, timeout=TIMEOUT)
        else:
            result = connection.execute(commands, timeout=TIMEOUT)

        return result
    except Exception as exc:
        logger.exception(f"Error sending CLI command '{commands}' to node {label} in lab {lid}: {str(exc)}")
        raise
    finally:
        if connection is not None:
            connection.disconnect()
