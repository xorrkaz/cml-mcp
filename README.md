# Model Context Protocol (MCP) Server for Cisco Modeling Labs (CML)

## Overview

`cml-mcp` is a server implementation of the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/docs/getting-started/intro) designed
for [Cisco Modeling Labs (CML)](https://www.cisco.com/c/en/us/products/cloud-systems-management/modeling-labs/index.html). It is built using [FastMCP 2.0](https://gofastmcp.com/getting-started/welcome) and designed to provide a set of tools for LLM apps like Claude Desktop, Claude Code, and Cursor to interact with CML.

## Features

- **Create Lab Topologies:** Tool for create new labs and define network topologies.
- **Query Status:** Tools to retrieve status information for labs, nodes, and the CML server itself.
- **Control Labs and Nodes:** Tools to start and stop labs or individual nodes as needed.
- **Run Commands on Devices:** Using [PyATS](https://developer.cisco.com/pyats/), MCP clients can execute commands on virtual devices within CML labs.

## Requirements

- Python 3.12+
- Cisco Modeling Labs (CML) instance
- PyATS (for device command execution)
- The [uv](https://docs.astral.sh/uv/) Python package/project manager

## Getting Started

1. Create a `.env` file with the following variables set:

    ```sh
    CML_URL=<URL_OF_CML_SERVER>
    CML_USERNAME=<USERNAME_ON_CML_SERVER>
    CML_PASSWORD=<PASSWORD_ON_CML_SERVER>
    # Optional in order to run commands
    PYATS_USERNAME=<DEVICE_USERNAME>
    PYATS_PASSWORD=<DEVICE_PASSWORD>
    PYATS_AUTH_PASS=<DEVICE_ENABLE_PASSWORD>
    ```

2. Configure the MCP client to start the MCP server.

## Usage

The tools should show up automatically in your MCP client, and you can chat with the LLM to get it to invoke tools as needed.  For example:

![Topology Creation Example](img/cml_mcp.gif)

## License

The MCP server portion of this project is licensed under the [BSD 2-Clause "Simplified" License](LICENSE).  However, it leverages the pydantic
schema typing code from CML itself, which is covered under a [proprietary Cisco license](src/cml_mcp/schemas/LICENSE).
