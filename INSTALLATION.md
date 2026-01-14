# Installation Guide

This guide covers all installation options for the CML MCP server.

## Table of Contents

- [Requirements](#requirements)
- [Standard I/O (stdio) Transport](#standard-io-stdio-transport)
  - [Using uvx (Easiest)](#using-uvx-easiest)
  - [Using FastMCP CLI](#using-fastmcp-cli)
- [HTTP Transport](#http-transport)
  - [Running the HTTP Server](#running-the-http-server)
  - [Configuring MCP Clients](#configuring-mcp-clients)
  - [Docker with HTTP](#docker-with-http-transport)

## Requirements

- **Python 3.12 or later** - Required for the MCP server
- **Cisco Modeling Labs (CML) 2.9 or later** - The CML server you'll connect to
- **[uv](https://docs.astral.sh/uv/)** - Python package and project manager (required for installation)
- **PyATS** (optional) - Automatically installed with `cml-mcp[pyats]` for device CLI command execution
- **Node.js** (optional) - Required only for HTTP transport mode with `mcp-remote`

### Windows Requirements

If you do not want to run CLI commands on devices running in CML, you don't need to do anything else other than install the base `cml-mcp` package. However, if you want full support, Windows users also require either Windows Subsystem for Linux (WSL) with Python and `uv` installed within WSL or a Docker environment running on the Windows machine.

## Standard I/O (stdio) Transport

This is the traditional way to run the server, where it communicates directly with the MCP client via standard input/output streams.

### Using uvx (Easiest)

The easiest way is to use `uvx`, which downloads the server from PyPI and runs it in a standalone environment.

#### Basic Installation (No CLI Support)

This works for Linux, Mac, and Windows users but does **not** provide CLI command support. Edit your client's config (e.g., Claude Desktop's `claude_desktop_config.json`):

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
        "CML_PASSWORD": "<PASSWORD_ON_CML_SERVER>",
        "CML_VERIFY_SSL": "false",
        "DEBUG": "false"
      }
    }
  }
}
```

#### With CLI Command Support (Linux/Mac)

To execute CLI commands on devices, Linux and Mac users should use `cml-mcp[pyats]`:

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
        "CML_VERIFY_SSL": "false",
        "PYATS_USERNAME": "<DEVICE_USERNAME>",
        "PYATS_PASSWORD": "<DEVICE_PASSWORD>",
        "PYATS_AUTH_PASS": "<DEVICE_ENABLE_PASSWORD>",
        "DEBUG": "false"
      }
    }
  }
}
```

#### With CLI Command Support (Windows/WSL)

Windows users wanting CLI command support should use WSL:

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
        "CML_VERIFY_SSL": "false",
        "DEBUG": "false",
        "WSLENV": "CML_URL/u:CML_USERNAME/u:CML_PASSWORD/u:CML_VERIFY_SSL/u:PYATS_USERNAME/u:PYATS_PASSWORD/u:PYATS_AUTH_PASS/u:DEBUG/u"
      }
    }
  }
}
```

#### With CLI Command Support (Docker)

For any platform using Docker:

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
        "-e",
        "CML_VERIFY_SSL",
        "-e",
        "DEBUG",
        "xorrkaz/cml-mcp:latest"
      ],
      "env": {
        "CML_URL": "<URL_OF_CML_SERVER>",
        "CML_USERNAME": "<USERNAME_ON_CML_SERVER>",
        "CML_PASSWORD": "<PASSWORD_ON_CML_SERVER>",
        "CML_VERIFY_SSL": "false",
        "PYATS_USERNAME": "<DEVICE_USERNAME>",
        "PYATS_PASSWORD": "<DEVICE_PASSWORD>",
        "PYATS_AUTH_PASS": "<DEVICE_ENABLE_PASSWORD>",
        "DEBUG": "false"
      }
    }
  }
}
```

### Using FastMCP CLI

An alternative is to use FastMCP CLI to install the server into your favorite client. FastMCP CLI supports Claude Desktop, Claude Code, Cursor, and manual JSON generation.

1. Clone this repository:

    ```sh
    git clone https://github.com/xorrkaz/cml-mcp.git
    cd cml-mcp
    ```

2. Run `uv sync` to install all the correct dependencies, including FastMCP 2.0. **Note:** on Linux and Mac, run `uv sync --all-extras` to get CLI command support.

3. Create a `.env` file with the following variables set:

    ```sh
    CML_URL=<URL_OF_CML_SERVER>
    CML_USERNAME=<USERNAME_ON_CML_SERVER>
    CML_PASSWORD=<PASSWORD_ON_CML_SERVER>
    CML_VERIFY_SSL=false  # Set to true to verify SSL certificates
    DEBUG=false  # Set to true to enable debug logging
    # Optional in order to run commands
    PYATS_USERNAME=<DEVICE_USERNAME>
    PYATS_PASSWORD=<DEVICE_PASSWORD>
    PYATS_AUTH_PASS=<DEVICE_ENABLE_PASSWORD>
    ```

4. Run the FastMCP CLI command to install the server. For example:

    ```sh
    fastmcp install claude-desktop src/cml_mcp/server.py:server_mcp --project `realpath .` --env-file .env
    ```

## HTTP Transport

The server supports HTTP streaming transport, which is useful for running the MCP server as a standalone service that can be accessed by multiple clients or when you want to run it in a containerized or remote environment. This mode uses HTTP Server-Sent Events (SSE) for real-time communication.

### Running the HTTP Server

To run the server in HTTP mode, set the `CML_MCP_TRANSPORT` environment variable to `http`. You can also configure the bind address and port.

First, install the package:

```sh
uv venv
source .venv/bin/activate
uv pip install cml-mcp # or cml-mcp[pyats] to get CLI command support
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
uvicorn cml_mcp.server:app --host 0.0.0.0 --port 9000 --workers 1
```

Or create a `.env` file with these settings:

```sh
CML_URL=<URL_OF_CML_SERVER>  # Optional in HTTP mode if using X-CML-URL header
CML_MCP_TRANSPORT=http
CML_MCP_BIND=0.0.0.0
CML_MCP_PORT=9000
CML_VERIFY_SSL=false  # Set to true to verify SSL certificates
DEBUG=false  # Set to true to enable debug logging
# For multiple CML hosts support, use one of:
CML_ALLOWED_URLS=https://cml1.example.com,https://cml2.example.com  # Comma-separated list
# OR
CML_URL_PATTERN=^https://cml\.example\.com  # Regex pattern
# Optional: Enable access control lists for tool restrictions
CML_MCP_ACL_FILE=/path/to/acl.yaml  # Path to ACL configuration file
```

Then run:

```sh
# Activate the virtual environment if not already active
source .venv/bin/activate

# Run the server
cml-mcp
```

The server will start and listen for HTTP connections at `http://0.0.0.0:9000`.

### Authentication in HTTP Mode

When using HTTP transport, authentication is handled differently than stdio mode:

- **CML Credentials**: Instead of being set via environment variables (`CML_USERNAME`/`CML_PASSWORD`), CML credentials are provided via the `X-Authorization` HTTP header using Basic authentication format.
- **PyATS Credentials**: For CLI command execution, PyATS credentials can be provided via the `X-PyATS-Authorization` header (Basic auth) instead of `PYATS_USERNAME`/`PYATS_PASSWORD` environment variables, and the enable password via the `X-PyATS-Enable` header instead of `PYATS_AUTH_PASS`.
- **Multiple CML Hosts**: When running in HTTP mode, clients can connect to different CML servers by providing the `X-CML-URL` header. For security, you must configure allowed URLs via the `CML_ALLOWED_URLS` environment variable (comma-separated list) or `CML_URL_PATTERN` (regex pattern).

Example headers:

```http
X-Authorization: Basic <base64_encoded_cml_username:cml_password>
X-PyATS-Authorization: Basic <base64_encoded_device_username:device_password>
X-PyATS-Enable: <base64_encoded_enable_password>
X-CML-URL: https://cml-server.example.com
```

**Note:** The `X-PyATS-Enable` header only needs the Base64-encoded enable password (not Basic auth format with username:password).

### Configuring MCP Clients

To use the HTTP server with an MCP client, you'll need to use the `mcp-remote` tool to connect to the HTTP endpoint. Most MCP clients like Claude Desktop don't natively support HTTP streaming, so `mcp-remote` acts as a bridge between the client (which expects stdio) and the HTTP server. This bridge requires [Node.js](https://nodejs.org/en/download/) to be installed on your client machine. Node.js includes the `npx` utility that allows you to run Javascript/Typescript applications in a dedicated environment.

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

#### Encoding Credentials

**Linux/Mac:**

```sh
# For CML credentials (X-Authorization header)
echo -n "username:password" | base64

# For device credentials (X-PyATS-Authorization header)
echo -n "device_username:device_password" | base64

# For enable password (X-PyATS-Enable header) - just the password
echo -n "enable_password" | base64
```

**Windows (use WSL):**

```sh
wsl bash -c 'echo -n "username:password" | base64'
wsl bash -c 'echo -n "device_username:device_password" | base64'
wsl bash -c 'echo -n "enable_password" | base64'
```

**Windows (PowerShell):**

```powershell
# For credentials with username:password format
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("username:password"))

# For enable password only
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("enable_password"))
```

#### HTTPS with Self-Signed Certificates

When using HTTPS with a self-signed certificate, you'll need to disable TLS certificate validation:

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

### Docker with HTTP Transport

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

#### Using ACLs with Docker

To use ACLs in Docker, mount your ACL file to `/app/acl.yaml`:

```sh
docker run -d \
  --rm \
  --name cml-mcp \
  -p 9000:9000 \
  -v /path/to/your/acl.yaml:/app/acl.yaml:ro \
  -e CML_URL=<URL_OF_CML_SERVER> \
  -e CML_MCP_TRANSPORT=http \
  xorrkaz/cml-mcp:latest
```

The Dockerfile sets `CML_MCP_ACL_FILE` to `/app/acl.yaml` by default, so you just need to mount your ACL configuration file to that path.

## Access Control Lists (HTTP Mode Only)

When running the MCP server in HTTP transport mode, you can implement fine-grained access control using a YAML-based ACL configuration file. This allows you to restrict which CML users can access which tools.

### ACL Configuration

To enable ACLs, set the `CML_MCP_ACL_FILE` environment variable to point to your ACL YAML file:

```sh
export CML_MCP_ACL_FILE=/path/to/acl.yaml
```

Or add it to your `.env` file:

```sh
CML_MCP_ACL_FILE=/path/to/acl.yaml
```

### ACL File Format

The ACL file uses the following structure:

```yaml
---
# If a user is not explicitly mentioned in the file, they are denied tool use when
# default_enabled is False. By default (when default_enabled is True or omitted),
# users not explicitly named in the file are allowed to call all tools.
default_enabled: False
users:
    # Admin is allowed to call all tools.
    admin: {}
    # jdoe is allowed all tools but delete_cml_lab and delete_cml_node.
    jdoe:
        disabled_tools:
            - delete_cml_lab
            - delete_cml_node
    # jsmith is only allowed to call send_cli_command.
    jsmith:
        enabled_tools:
            - send_cli_command
```

### Configuration Options

- **`default_enabled`** (boolean, default: `true`): Controls the default behavior for users not explicitly listed in the ACL file.
  - `true`: Users not in the ACL file can access all tools (permissive default)
  - `false`: Users not in the ACL file cannot access any tools (restrictive default)

- **`users`** (object): A mapping of CML usernames to their tool access rules. Each user can have:
  - **`enabled_tools`** (list): An allow list of tool names the user can access. If specified, the user can only access these tools.
  - **`disabled_tools`** (list): A block list of tool names the user cannot access. The user can access all other tools.
  - If both lists are specified, `enabled_tools` takes precedence
  - An empty user configuration (`{}`) allows access to all tools regardless of `default_enabled`

### ACL Behavior

The ACL system follows this evaluation order:

1. If no ACL file is configured, all users can access all tools
2. If a user has an `enabled_tools` list, they can only access those specific tools
3. If a user has a `disabled_tools` list (and no `enabled_tools`), they can access all tools except those listed
4. If a user is not in the ACL file, the `default_enabled` setting determines their access
5. If a user is in the ACL file with an empty configuration, they can access all tools

### Example Use Cases

**Restrictive Environment** - Only allow specific users:

```yaml
default_enabled: False
users:
    admin: {}  # Admin has full access
    developer:
        enabled_tools:
            - get_cml_labs
            - get_nodes_for_cml_lab
            - send_cli_command
```

**Permissive Environment** - Block specific actions:

```yaml
default_enabled: True
users:
    intern:
        disabled_tools:
            - delete_cml_lab
            - delete_cml_node
            - delete_cml_user
            - delete_cml_group
```

For a complete example, see [acl.yaml.example](https://github.com/xorrkaz/cml-mcp/blob/main/acl.yaml.example) in the repository.

### Tool Names Reference

To configure ACLs, you'll need to know the exact tool names. Here are all available tools:

**Lab Management:** `get_cml_labs`, `create_empty_lab`, `create_full_lab_topology`, `modify_cml_lab`, `start_cml_lab`, `stop_cml_lab`, `wipe_cml_lab`, `delete_cml_lab`, `get_cml_lab_by_title`

**Node Management:** `get_cml_node_definitions`, `get_node_definition_detail`, `add_node_to_cml_lab`, `get_nodes_for_cml_lab`, `configure_cml_node`, `start_cml_node`, `stop_cml_node`, `wipe_cml_node`, `delete_cml_node`, `get_console_log`, `send_cli_command`

**Interface & Link Management:** `add_interface_to_node`, `get_interfaces_for_node`, `connect_two_nodes`, `get_all_links_for_lab`, `apply_link_conditioning`, `start_cml_link`, `stop_cml_link`

**Annotations:** `get_annotations_for_cml_lab`, `add_annotation_to_cml_lab`, `delete_annotation_from_lab`

**User & Group Management:** `get_cml_users`, `create_cml_user`, `delete_cml_user`, `get_cml_groups`, `create_cml_group`, `delete_cml_group`

**System Information:** `get_cml_information`, `get_cml_status`, `get_cml_statistics`, `get_cml_licensing_details`

## Environment Variables Reference

### Required (stdio mode)

- `CML_URL` - URL of your CML server (e.g., `https://cml.example.com`)
- `CML_USERNAME` - Username for CML authentication
- `CML_PASSWORD` - Password for CML authentication

### Optional

- `CML_VERIFY_SSL` - Verify SSL certificates (default: `false`)
- `DEBUG` - Enable debug logging (default: `false`)
- `PYATS_USERNAME` - Device username for CLI commands
- `PYATS_PASSWORD` - Device password for CLI commands
- `PYATS_AUTH_PASS` - Device enable password for CLI commands

### HTTP Transport Mode

- `CML_MCP_TRANSPORT` - Set to `http` for HTTP mode (default: `stdio`)
- `CML_MCP_BIND` - IP address to bind HTTP server (default: `0.0.0.0`)
- `CML_MCP_PORT` - Port for HTTP server (default: `9000`)
- `CML_ALLOWED_URLS` - Comma-separated list of allowed CML URLs in HTTP mode
- `CML_URL_PATTERN` - Regex pattern for allowed CML URLs (alternative to `CML_ALLOWED_URLS`)
- `CML_MCP_ACL_FILE` - Path to YAML file for access control lists (tool restrictions per user)

### Test Environment Variables

- `USE_MOCKS` - Use mock data instead of live CML server (default: `true`)
