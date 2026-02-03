import logging
import traceback

import yaml
from simple_webserver.schemas.common import UUID4Type
from simple_webserver.schemas.nodes import NodeLabel
from unicon import Connection

from cml_mcp.cml_client import CMLClient

_LOGGER = logging.getLogger(__name__)

TERMWS_BINARY = "/usr/local/bin/termws"
TIMEOUT = 300
LOG_PATH = "/tmp/unicon_last_connection.log"


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
        raise Exception("can not retrieve node console key. is not running?")

    lab_op_info = resp.json()

    consoles = [node["operational"]["serial_consoles"] for node in lab_op_info if node["label"] == label].pop()

    console_key = consoles[0]["console_key"]

    connect_command = f"{TERMWS_BINARY} -host [::1] -port 8006 -internal {console_key}"
    connection = None
    error = None
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
        error = traceback.TracebackException.from_exception(exc)
        raise
    finally:
        if connection is not None:
            connection.disconnect()

        _save_connection_log(connection, error)


def _save_connection_log(connection, error):
    try:
        with open(LOG_PATH, "at") as logfile:
            logfile.write("Start log of extraction: \n")
            if error:
                logfile.write("Failed with error:\n")
                logfile.writelines(error.format())
            if connection is not None and connection.log_buffer:
                logfile.write(connection.log_buffer)
            else:
                logfile.write("No connection log was retained\n")
    except Exception as exc:
        _LOGGER.exception("Failed to save unicon connection log: %s", exc)
