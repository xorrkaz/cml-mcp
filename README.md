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

You have a couple of choices to hook this server up to your favorite MCP client.  Probably the easiest way is to use `uvx`, which downloads the server from PyPi and runs it in a standalone environment.  For that, you need to edit your client's config and add something like the following.  This example is for Claude Desktop:

```json
{
  "mcpServers": {
    "Cisco Modeling Labs MCP Server": {
      "command": "uvx",
      "args": [
        "cml-mcp"
      ],
      "env": {
        "CML_URL": "<URL_OF_CML_SERVER>",
        "CML_USERNAME": "<USERNAME_ON_CML_SERVER>",
        "CML_PASSWORD": "<PASSWORD_ON_CML_SERVER>",
        "PYATS_USERNAME": "<DEVICE_USERNAME>",
        "PYATS_PASSWORD": "<DEVICE_PASSWORD>",
        "PYATS_AUTH_PASS": "<DEVICE_ENABLE_PASSWORD>"
      }
    }
  }
}
```

The `PYATS` environment variables are optional but will be required if you want to run commands on the devices running within CML.

An alternative is to use FastMCP CLI to install the server into your favorite client.  FastMCP CLI supports Claude Desktop, Claude Code, Cursor, and manual JSON generation.  To use FastMCP, do the following:

1. Clone this repository:

    ```sh
    git clone https://github.com/xorrkaz/cml-mcp.git
    ```

1. Change directory to the cloned repository.

1. Run `uv sync` to install all the correct dependencies, including FastMCP 2.0.

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

1. Run the FastMCP CLI command to install the server.  For example:

    ```sh
    fastmcp install claude-desktop src/cml_mcp/server.py:server_mcp --project `realpath .` --env-file .env
    ```

## Usage

The tools should show up automatically in your MCP client, and you can chat with the LLM to get it to invoke tools as needed.  For example,
the following sequence of prompts nicely shows off some of the server's capabilities:

- Create a new CML lab called "Joe's MCP Lab".
- Add two IOL nodes, a unmanaged switch, and an external connector to this lab.
- Connect the two IOL nodes to the unmanaged switch and the unmanaged switch to the external connector.
- Configure the routers so that their connected interfaces have IPs in the 192.0.2.0/24 subnet.  Configure OSPF on them.  Then start the lab and validate OSPF is working correctly.
- Add a box annotation around the two IOL nodes that indicates they speak OSPF.  Make it a green box.

And here is an obligatory demo GIF to show it working in Claude Desktop:

![Topology Creation Example](img/cml_mcp.gif)

### System Prompt

If your LLM tool supports a system prompt, or you want to provide some richer initial context, here's a good example courtesy of Hank Preston:

>You are a network lab assistant specializing in supporting Cisco Modeling Labs (CML). You provide a natural language interface for many common lab activities such as:
>
>- Creating new lab
>- Adding nodes to a lab
>- Creating interfaces between nodes
>- Configuring nodes
>- Creating annotations
>
>You have access to tools to access the CML server.

## License

The MCP server portion of this project is licensed under the [BSD 2-Clause "Simplified" License](LICENSE).  However, it leverages the pydantic
schema typing code from CML itself, which is covered under a [proprietary Cisco license](src/cml_mcp/schemas/LICENSE).
