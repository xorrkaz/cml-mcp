# Model Context Protocol (MCP) Server for Cisco Modeling Labs (CML)

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/xorrkaz/cml-mcp)

mcp-name: io.github.xorrkaz/cml-mcp

## Overview

`cml-mcp` is a server implementation of the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/docs/getting-started/intro) designed
for [Cisco Modeling Labs (CML)](https://www.cisco.com/c/en/us/products/cloud-systems-management/modeling-labs/index.html). It is built using [FastMCP 2.0](https://gofastmcp.com/getting-started/welcome) and designed to provide a set of tools for LLM apps like Claude Desktop, Claude Code, and Cursor to interact with CML.

## Features

- **Create Lab Topologies:** Tool for create new labs and define network topologies.
- **Query Status:** Tools to retrieve status information for labs, nodes, and the CML server itself.
- **Control Labs and Nodes:** Tools to start and stop labs or individual nodes as needed.
- **Manage CML Users and Groups** Tools to list, create, and delete local users and groups.
- **Run Commands on Devices:** Using [PyATS](https://developer.cisco.com/pyats/), MCP clients can execute commands on virtual devices within CML labs.

## Requirements

- Python 3.12+
- Cisco Modeling Labs (CML) 2.9 or later
- PyATS (optional; used for device CLI command execution)
- The [uv](https://docs.astral.sh/uv/) Python package/project manager

## Windows Requirements

If you do not want to run CLI commands on devices running in CML, you don't need to do anything else other than install the base `cml-mcp` package.  However,
if you want full support, Windows users also require either Windows Subsystem for Linux (WSL) with Python and `uv` installed within WSL or a Docker environment running on the Windows machine.

## Getting Started

You have several options to run this server, depending on your needs and platform:

### Option 1: Standard I/O (stdio) Transport

This is the traditional way to run the server, where it communicates directly with the MCP client via standard input/output streams.

#### Using uvx (Easiest - No CLI Support)

The easiest way is to use `uvx`, which downloads the server from PyPi and runs it in a standalone environment.  This works for Linux, Mac, and Windows users but does **not** provide CLI command support.  Edit your client's config and add something like the following.  This example is for Claude Desktop:

```json
{
  "mcpServers": {
    "Cisco Modeling Labs (CML)": {
      "command": "uvx",
      "args": [
        "cml-mcp"
      ],
      "env": {
        "CML_URL": "<URL_OF_CML_SERVER>",
        "CML_USERNAME": "<USERNAME_ON_CML_SERVER>",
        "CML_PASSWORD": "<PASSWORD_ON_CML_SERVER>"
      }
    }
  }
}
```

In order to execute CLI commands on devices running within CML, Linux and Mac users will need to change the "args" to `cml-mcp[pyats]`.  For example:

```json
{
  "mcpServers": {
    "Cisco Modeling Labs (CML)": {
      "command": "uvx",
      "args": [
        "cml-mcp[pyats]"
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

The additional `PYATS` environment variables are needed to let the MCP server know how to login to those running devices.

Windows users that want CLI command support and are using Windows Subsystem for Linux (WSL) should configure:

```json
{
  "mcpServers": {
    "Cisco Modeling Labs (CML)": {
      "command": "wsl",
      "args": [
        "uvx",
        "cml-mcp[pyats]"
      ],
      "env": {
        "CML_URL": "<URL_OF_CML_SERVER>",
        "CML_USERNAME": "<USERNAME_ON_CML_SERVER>",
        "CML_PASSWORD": "<PASSWORD_ON_CML_SERVER>",
        "PYATS_USERNAME": "<DEVICE_USERNAME>",
        "PYATS_PASSWORD": "<DEVICE_PASSWORD>",
        "PYATS_AUTH_PASS": "<DEVICE_ENABLE_PASSWORD>",
        "WSLENV": "CML_URL/u:CML_USERNAME/u:CML_PASSWORD/u:PYATS_USERNAME/u:PYATS_PASSWORD/u:PYATS_AUTH_PASS/u:PYATS_AUTH_PASS/u"
      }
    }
  }
}
```

Windows (and really Mac and Linux users, too) that want CLI command support and are using Docker should configure:

```json
{
  "mcpServers": {
    "Cisco Modeling Labs (CML)": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--pull",
        "always",
        "-e",
        "CML_URL",
        "-e",
        "CML_USERNAME",
        "-e",
        "CML_PASSWORD",
        "-e",
        "PYATS_USERNAME",
        "-e",
        "PYATS_PASSWORD",
        "-e",
        "PYATS_AUTH_PASS",
        "xorrkaz/cml-mcp:latest"
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

#### Using FastMCP CLI

An alternative is to use FastMCP CLI to install the server into your favorite client.  FastMCP CLI supports Claude Desktop, Claude Code, Cursor, and manual JSON generation.  To use FastMCP, do the following:

1. Clone this repository:

    ```sh
    git clone https://github.com/xorrkaz/cml-mcp.git
    ```

1. Change directory to the cloned repository.

1. Run `uv sync` to install all the correct dependencies, including FastMCP 2.0.  **Note:** on Linux and Mac, run `uv sync --all-extras` to get CLI command support.

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

### Option 2: HTTP Transport (Streaming)

The server now supports HTTP streaming transport, which is useful for running the MCP server as a standalone service that can be accessed by multiple clients or when you want to run it in a containerized or remote environment. This mode uses HTTP Server-Sent Events (SSE) for real-time communication.

#### Running the HTTP Server

To run the server in HTTP mode, set the `CML_MCP_TRANSPORT` environment variable to `http`. You can also configure the bind address and port.

First, install the package:

```sh
uv venv
source .venv/bin/activate
uv pip install cml-mcp # or cml-mcp\[pyats] to get CLI command support
```

Or for development, clone the repository and sync dependencies:

```sh
git clone https://github.com/xorrkaz/cml-mcp.git
cd cml-mcp
uv sync # add --all-extras to get CLI command support
```

Then run the server using `uvicorn`:

```sh
# Set environment variables
export CML_URL=<URL_OF_CML_SERVER>
export CML_MCP_TRANSPORT=http
export CML_MCP_BIND=0.0.0.0  # Optional, defaults to 0.0.0.0
export CML_MCP_PORT=9000     # Optional, defaults to 9000

# Run the server with uvicorn
uvicorn cml_mcp.server:app --host 0.0.0.0 --port 9000
```

Or create a `.env` file with these settings:

```sh
CML_URL=<URL_OF_CML_SERVER>
CML_MCP_TRANSPORT=http
CML_MCP_BIND=0.0.0.0
CML_MCP_PORT=9000
```

Then run:

```sh
cml-mcp
```

The server will start and listen for HTTP connections at `http://0.0.0.0:9000`.

#### Authentication in HTTP Mode

When using HTTP transport, authentication is handled differently than stdio mode:

- **CML Credentials**: Instead of being set via environment variables, CML credentials are provided via the `X-Authorization` HTTP header using Basic authentication format.
- **PyATS Credentials**: For CLI command execution, PyATS credentials can be provided via the `X-PyATS-Authorization` header (Basic auth) and the enable password via the `X-PyATS-Enable` header

Example headers:

```http
X-Authorization: Basic <base64_encoded_cml_username:cml_password>
X-PyATS-Authorization: Basic <base64_encoded_device_username:device_password>
X-PyATS-Enable: Basic <base64_encoded_enable_password>
```

#### Configuring MCP Clients for HTTP

To use the HTTP server with an MCP client, you'll need to use the `mcp-remote` tool to connect to the HTTP endpoint. Most MCP clients like Claude Desktop don't natively support HTTP streaming, so `mcp-remote` acts as a bridge between the client (which expects stdio) and the HTTP server.  This bridge requires [Node.js](https://nodejs.org/en/download/) to be installed
on your client machine.  Node.js includes the `npx` utility that allows you to run Javascript/Typescript applications in
a dedicated environment.

Add the following configuration to your MCP client config (e.g., Claude Desktop's `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "Cisco Modeling Labs (CML)": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://<server_host>:9000/mcp",
        "--header",
        "X-Authorization: Basic <base64_encoded_cml_credentials>",
        "--header",
        "X-PyATS-Authorization: Basic <base64_encoded_device_credentials>"
      ]
    }
  }
}
```

Replace the placeholders with your actual values:

- `<server_host>`: The hostname or IP address where your HTTP server is running
- `<base64_encoded_cml_credentials>`: Base64-encoded `username:password` for CML
- `<base64_encoded_device_credentials>`: Base64-encoded `username:password` for device access

Example:

```json
{
  "mcpServers": {
    "Cisco Modeling Labs (CML)": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://192.168.10.210:8443/mcp",
        "--header",
        "X-Authorization: Basic <base64_encoded_cml_credentials>",
        "--header",
        "X-PyATS-Authorization: Basic <base64_encoded_device_credentials>"
      ]
    }
  }
}
```

**Note**: When using HTTPS with a self-signed certificate, you'll need to disable TLS certificate validation by adding an `env` section:

```json
{
  "mcpServers": {
    "Cisco Modeling Labs (CML)": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://192.168.10.210:8443/mcp",
        "--header",
        "X-Authorization: Basic <base64_encoded_cml_credentials>",
        "--header",
        "X-PyATS-Authorization: Basic <base64_encoded_device_credentials>"
      ],
      "env": {
        "NODE_TLS_REJECT_UNAUTHORIZED": "0"
      }
    }
  }
}
```

To encode your credentials in Base64:

**Linux/Mac:**

```sh
# For CML credentials
echo -n "username:password" | base64

# For device credentials  
echo -n "device_username:device_password" | base64

# For enable password (if needed)
echo -n "enable_password" | base64
```

**Windows (use WSL):**

```sh
wsl bash -c 'echo -n "username:password" | base64'
wsl bash -c 'echo -n "device_username:device_password" | base64'
wsl bash -c 'echo -n "enable_password" | base64'
```

Alternatively, you can use online Base64 encoders or PowerShell:

```powershell
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("username:password"))
```

If you need to specify an enable password, add another header:

```json
"--header",
"X-PyATS-Enable: Basic <base64_encoded_enable_password>"
```

#### Docker with HTTP Transport

You can also run the server in HTTP mode using Docker:

```sh
docker run -d \
  --rm \
  --name cml-mcp \
  -p 9000:9000 \
  -e CML_URL=<URL_OF_CML_SERVER> \
  -e CML_MCP_TRANSPORT=http \
  xorrkaz/cml-mcp:latest
```

This exposes the HTTP server on port 9000, allowing external MCP clients to connect.

## Usage

The tools should show up automatically in your MCP client, and you can chat with the LLM to get it to invoke tools as needed.  For example,
the following sequence of prompts nicely shows off some of the server's capabilities:

- Create a new CML lab called "Joe's MCP Lab".
- Add two IOL nodes, a unmanaged switch, and an external connector to this lab.
- Connect the two IOL nodes to the unmanaged switch and the unmanaged switch to the external connector.
- Configure the routers so that their connected interfaces have IPs in the 192.0.2.0/24 subnet.  Configure OSPF on them.  Then start the lab and validate OSPF is working correctly.
- Add a box annotation around the two IOL nodes that indicates they speak OSPF.  Make it a green box.

And here is an obligatory demo GIF to show it working in Claude Desktop:

![Animated demonstration showing Claude Desktop creating a network topology in Cisco Modeling Labs through natural language commands. The sequence shows a user typing prompts to create a lab, add network devices including two IOL routers, an unmanaged switch, and an external connector, then configure OSPF routing between the devices. The interface displays both the chat conversation on the left and the resulting network diagram on the right, with nodes being added and connected in real-time as the AI processes each command.](img/cml_mcp.gif)

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
