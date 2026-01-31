# Installation Guide

This guide will help you set up the CML MCP server so you can control Cisco Modeling Labs using AI assistants like Claude Desktop. Whether you're new to CML or an experienced power user, we'll get you up and running.

**Choose Your Installation Method:**

- **Just want to try it out?** → Use the [uvx quick start](#using-uvx-easiest) (easiest, no manual installation needed)
- **Want to run CLI commands on devices?** → See [With CLI Command Support](#with-cli-command-support-linuxmac)
- **Need to share with your team?** → Try [HTTP Transport mode](#http-transport)
- **Running on Windows?** → Check out [Windows-specific options](#with-cli-command-support-windowswsl)

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

### What You'll Need

**On Your Computer:**

- **Python 3.12 or later** - The programming language runtime ([download here](https://www.python.org/downloads/) if needed)
- **[uv](https://docs.astral.sh/uv/)** - A modern Python package manager that makes installation easy ([install instructions](https://docs.astral.sh/uv/getting-started/installation/))

**Your CML Server:**

- **Cisco Modeling Labs (CML) 2.9 or later** - You'll need access to a running CML server with valid credentials

**Optional Enhancements:**

- **PyATS support** - Automatically included when you install `cml-mcp[pyats]` - enables sending CLI commands directly to your network devices
- **Node.js** - Only needed for [HTTP Transport mode](#http-transport) with shared deployments

### Windows Users - Special Notes

**Good news:** Basic functionality (creating labs, adding nodes, configuring devices) works great on Windows!

**The catch:** If you want to execute CLI commands directly on running devices (using the `send_cli_command` tool), you'll need one of these options:

1. **Windows Subsystem for Linux (WSL)** - Recommended for most users
   - Install WSL2 and Ubuntu from the Microsoft Store
   - Install Python and `uv` inside WSL
   - Follow the [Windows/WSL instructions](#with-cli-command-support-windowswsl) below

2. **Docker Desktop** - Good if you already use containers
   - Install Docker Desktop for Windows
   - Follow the [Docker instructions](#with-cli-command-support-docker) below

3. **Basic installation without CLI** - Simplest option
   - Everything works except `send_cli_command`
   - You can still configure devices, just not execute show commands interactively
   - Follow the [basic installation](#basic-installation-no-cli-support) below

## Standard I/O (stdio) Transport

This is the standard way to connect your AI assistant (like Claude Desktop) directly to the CML MCP server. Think of it like a direct phone line between the AI and your CML server.

**When to use this:** For personal use on your own computer, or when your AI client is on the same machine where you want to run the server.

### Using uvx (Easiest)

**What is uvx?** It's a tool that automatically downloads and runs Python packages without manual installation steps. Perfect for getting started quickly!

#### Basic Installation (No CLI Support)

This configuration gives you most features and works on any platform (Linux, Mac, Windows). You'll be able to create labs, add devices, configure them, and more. The only thing you won't be able to do is execute show commands directly on running devices.

**Step 1:** Locate your MCP client's configuration file (e.g., for Claude Desktop, it's `claude_desktop_config.json`)

**Step 2:** Add this configuration:

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

**Remember to customize:**

- Replace `<URL_OF_CML_SERVER>` with your actual CML server URL (e.g., `https://cml.mylab.com` or `https://10.10.20.50`)
- Use your actual CML username and password
- Set `DEBUG` to `"true"` if you need troubleshooting information (keeps it in logs)

**Restart required:** After saving the configuration file, restart your MCP client for changes to take effect.

#### With CLI Command Support (Linux/Mac)

**What's different?** This installation includes PyATS, Cisco's Python testing framework. With it enabled, you can ask the AI to execute show commands on your routers and switches, like "Show me the OSPF neighbors on Router1" or "What's the interface status on Switch2?"

**Note:** The key difference here is `cml-mcp[pyats]` instead of just `cml-mcp`, plus three additional environment variables for device authentication.

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

**Understanding PyATS credentials:**

- `PYATS_USERNAME` and `PYATS_PASSWORD`: The username/password to log into your network devices (not your CML credentials)
- `PYATS_AUTH_PASS`: The enable password for privileged EXEC mode on your devices
- These are typically the credentials you configured in your device startup configs

**Tip for new users:** If you haven't set up device credentials yet, common defaults in lab environments are:

- Username: `admin` or `cisco`
- Password: `cisco` or `C1sco12345`
- Enable: same as password or leave blank if no enable secret is configured

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

HTTP transport mode runs the MCP server as a standalone web service that multiple people can connect to. Instead of each person running their own server, you run one central server that everyone shares.

**When to use HTTP mode:**

- ✅ You want to run the server on a dedicated machine (not your laptop)
- ✅ Multiple team members need to connect to the same CML environment
- ✅ You want to deploy in a containerized environment (Kubernetes, Docker Swarm)
- ✅ You need centralized control and logging
- ✅ You want to implement access control lists (who can delete labs, create users, etc.)

**When to use stdio mode instead:**

- ✅ You're the only user
- ✅ You want the simplest setup
- ✅ You're just trying out the tool

### Running the HTTP Server

**Quick start:** To run the server in HTTP mode, you'll set some environment variables and then start the server with `uvicorn` (a Python web server).

#### Step 1: Install the package

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

#### Step 2: Set environment variables

You can either export these directly in your shell or create a `.env` file (recommended for persistence):

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

**Important security note:** In HTTP mode, credentials work differently than stdio mode to keep your passwords secure.

**How it works:**

- Instead of storing CML passwords in environment variables (where they could be visible), each client sends their credentials securely with each request using HTTP headers
- This means different users can connect to the same server with their own CML credentials

**What you need to know:**

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

**The challenge:** Most AI clients (like Claude Desktop) expect a direct connection to the MCP server, but your server is now running as a web service.

**The solution:** Use `mcp-remote`, a small bridge program that connects your AI client to the HTTP server. It translates between the client's expected format and HTTP.

**What you need:** Node.js installed on your computer (includes the `npx` command that runs `mcp-remote`)

- [Download Node.js](https://nodejs.org/en/download/) if you don't have it

**Step 1:** Prepare your credentials (you'll need them Base64-encoded)

#### Encoding Credentials

**Why Base64?** It's a standard way to safely transmit credentials in HTTP headers. Don't worry—it's easy to generate!

**Linux/Mac - Use the terminal:**

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

**Step 2:** Configure your MCP client

Now that you have your Base64-encoded credentials, add this to your MCP client configuration (e.g., Claude Desktop's `claude_desktop_config.json`):

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

**Customize your configuration:**

- `<server_host>`: The hostname or IP address where your HTTP server is running (e.g., `192.168.1.100` or `cml-mcp.mycompany.com`)
- `<base64_encoded_cml_credentials>`: Paste the Base64 string you generated for your CML username:password
- `<base64_encoded_device_credentials>`: Paste the Base64 string you generated for your device username:password

**Tip:** Keep the `Basic` keyword before your Base64 credentials—it's required for HTTP authentication!

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

**What are ACLs and why would I use them?**

Access Control Lists let you control who can do what in your CML environment when running in HTTP mode. Think of it like permissions in a file system—you can decide which team members can delete labs, create users, or just view information.

**Real-world scenarios:**

- 🎓 **Training environment:** Students can create and manage their own labs, but can't delete other users' labs or modify system settings
- 👥 **Team environment:** Junior engineers can view and work with labs, but only senior staff can delete resources
- 🔒 **Controlled access:** Contractors can execute show commands but can't modify configurations or delete anything

**Important:** ACLs only work in HTTP transport mode. If you're using stdio mode (direct connection), everyone has full access.

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

**Lab Management:** `get_cml_labs`, `create_empty_lab`, `create_full_lab_topology`, `modify_cml_lab`, `start_cml_lab`, `stop_cml_lab`, `wipe_cml_lab`, `delete_cml_lab`, `get_cml_lab_by_title`, `download_lab_topology`, `clone_cml_lab`

**Node Management:** `get_cml_node_definitions`, `get_node_definition_detail`, `add_node_to_cml_lab`, `get_nodes_for_cml_lab`, `configure_cml_node`, `start_cml_node`, `stop_cml_node`, `wipe_cml_node`, `delete_cml_node`, `get_console_log`, `send_cli_command`

**Interface & Link Management:** `add_interface_to_node`, `get_interfaces_for_node`, `connect_two_nodes`, `get_all_links_for_lab`, `apply_link_conditioning`, `start_cml_link`, `stop_cml_link`

**Annotations:** `get_annotations_for_cml_lab`, `add_annotation_to_cml_lab`, `delete_annotation_from_lab`

**Packet Capture:** `start_packet_capture`, `stop_packet_capture`, `check_packet_capture_status`, `get_captured_packet_overview`, `get_packet_capture_data`

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
