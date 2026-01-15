# Model Context Protocol (MCP) Server for Cisco Modeling Labs (CML)

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/xorrkaz/cml-mcp)

mcp-name: io.github.xorrkaz/cml-mcp

## Overview

`cml-mcp` brings the power of AI assistants to your network lab! This tool allows you to interact with [Cisco Modeling Labs (CML)](https://www.cisco.com/c/en/us/products/cloud-systems-management/modeling-labs/index.html) using natural language through AI applications like Claude Desktop, Claude Code, and Cursor.

Instead of clicking through menus or writing scripts, simply tell the AI what you want to do in plain English—like "Create a new lab with two routers and configure OSPF" or "Show me the running config on Router1"—and watch it happen automatically.

This is accomplished through the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/docs/getting-started/intro), a standard way for AI applications to interact with external tools and services. Think of it as giving your AI assistant a direct connection to your CML server.

## Features

- **Create Lab Topologies:** Tools to create new labs and define network topologies from scratch or using full topology definitions.
- **Query Status:** Tools to retrieve detailed status information for labs, nodes, links, annotations, and the CML server itself.
- **Control Labs and Nodes:** Tools to start, stop, and wipe labs or individual nodes as needed.
- **Manage CML Users and Groups:** Tools to list, create, and delete local users and groups (requires admin privileges).
- **Visual Annotations:** Add visual elements (text, rectangles, ellipses, lines) to lab topologies for documentation and organization.
- **Link Management:** Connect nodes, configure link conditioning (bandwidth, latency, jitter, loss), and control link states.
- **Packet Capture:** Start, stop, and retrieve packet captures (PCAP) from network links for traffic analysis with Wireshark or other tools.
- **Node Configuration:** Configure node startup configurations and send CLI commands to running devices.
- **Run Commands on Devices:** Using [PyATS](https://developer.cisco.com/pyats/), MCP clients can execute commands on virtual devices within CML labs.
- **Console Log Access:** Retrieve console logs from running nodes for troubleshooting and monitoring.
- **Modular Architecture:** Tools are organized into logical modules (labs, nodes, links, pcap, etc.) for maintainability and extensibility.
- **Access Control Lists (HTTP Mode):** When running in HTTP transport mode, you can restrict which users can access which tools using a YAML-based ACL configuration file.

## Quick Start

### Installation

The easiest way to get started is using `uvx` with Claude Desktop (or other MCP-compatible clients). The `uvx` tool automatically downloads and runs the server without manual installation steps.

**Configuration:** Find and edit your Claude Desktop configuration file (`claude_desktop_config.json`). Add the following:

```json
{
  "mcpServers": {
    "Cisco Modeling Labs (CML)": {
      "command": "uvx",
      "args": ["cml-mcp"],
      "env": {
        "CML_URL": "https://your-cml-server.example.com",
        "CML_USERNAME": "your_username",
        "CML_PASSWORD": "your_password",
        "CML_VERIFY_SSL": "false"
      }
    }
  }
}
```

**Important:** Replace the placeholder values with your actual CML server details:

- `CML_URL`: Your CML server address (e.g., `https://cml.example.com` or `https://10.10.20.50`)
- `CML_USERNAME` and `CML_PASSWORD`: Your CML login credentials
- Set `CML_VERIFY_SSL` to `"false"` if using self-signed certificates (common in lab environments)

**Need more capabilities?**

- For **device CLI command execution**, use `cml-mcp[pyats]` instead of `cml-mcp` in the args
- For **Docker, Windows (WSL), or HTTP server mode**, see [INSTALLATION.md](https://github.com/xorrkaz/cml-mcp/blob/main/INSTALLATION.md)

**Where to find your configuration file:**

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

### Requirements

- **Python 3.12 or later**
- **Cisco Modeling Labs (CML) 2.9 or later**
- **[uv](https://docs.astral.sh/uv/)** - Python package manager

## Available MCP Tools

The server provides 45 MCP tools organized into the following categories:

### Lab Management

- **get_cml_labs** - Retrieve labs for a specific user or current user
- **create_empty_lab** - Create a new empty lab with optional metadata
- **create_full_lab_topology** - Create a complete lab from a topology definition
- **modify_cml_lab** - Update lab properties (title, description, notes)
- **start_cml_lab** - Start all nodes in a lab
- **stop_cml_lab** - Stop all nodes in a lab
- **wipe_cml_lab** - Wipe all node data/configurations (requires confirmation)
- **delete_cml_lab** - Delete a lab (requires confirmation)
- **get_cml_lab_by_title** - Find a lab by its title

### Node Management

- **get_cml_node_definitions** - List available node types
- **get_node_definition_detail** - Get detailed info about a specific node type
- **add_node_to_cml_lab** - Add a node to a lab
- **get_nodes_for_cml_lab** - Get all nodes in a lab with operational data
- **configure_cml_node** - Set node startup configuration
- **start_cml_node** - Start a specific node
- **stop_cml_node** - Stop a specific node
- **wipe_cml_node** - Wipe node data (requires confirmation)
- **delete_cml_node** - Delete a node (requires confirmation)
- **get_console_log** - Get console output history for a node
- **send_cli_command** - Execute CLI commands on running nodes (requires PyATS)

### Interface & Link Management

- **add_interface_to_node** - Add an interface to a node
- **get_interfaces_for_node** - Get all interfaces for a node
- **connect_two_nodes** - Create a link between two interfaces
- **get_all_links_for_lab** - Get all links in a lab
- **apply_link_conditioning** - Configure network conditions (bandwidth, latency, jitter, loss)
- **start_cml_link** - Enable connectivity on a link
- **stop_cml_link** - Disable connectivity on a link

### Annotations (Visual Elements)

- **get_annotations_for_cml_lab** - Get all visual annotations in a lab
- **add_annotation_to_cml_lab** - Add text, rectangle, ellipse, or line annotations
- **delete_annotation_from_lab** - Delete an annotation (requires confirmation)

### Packet Capture (PCAP)

- **start_packet_capture** - Start capturing packets on a link
- **stop_packet_capture** - Stop an active packet capture
- **check_packet_capture_status** - Check capture status and packet count
- **get_captured_packet_overview** - Get summary of captured packets
- **get_packet_capture_data** - Download full PCAP file (base64-encoded for Wireshark/tcpdump)

### User & Group Management

- **get_cml_users** - List all CML users
- **create_cml_user** - Create a new user (requires admin)
- **delete_cml_user** - Delete a user (requires admin, requires confirmation)
- **get_cml_groups** - List all CML groups
- **create_cml_group** - Create a new group (requires admin)
- **delete_cml_group** - Delete a group (requires admin, requires confirmation)

### System Information

- **get_cml_information** - Get CML server version and configuration
- **get_cml_status** - Get system health indicators
- **get_cml_statistics** - Get resource usage and lab/node/link counts
- **get_cml_licensing_details** - Get licensing information and limits

## Usage

Once configured, restart your MCP client (e.g., Claude Desktop) and start chatting! The AI assistant now has direct access to your CML server and can help you build and manage network labs through natural conversation.

### What Can You Do?

Here are some example prompts to try:

**Getting Started:**

- "Show me all my CML labs"
- "What node types are available in CML?"
- "Tell me about my CML server status and licensing"

**Building Labs:**

- "Create a new lab called 'OSPF Test Lab'"
- "Add two CSR1000v routers and an external connector to my lab"
- "Connect Router1's GigabitEthernet1 to Router2's GigabitEthernet1"

**Configuration & Testing:**

- "Configure OSPF area 0 on both routers"
- "Start all nodes in the lab"
- "Show me the OSPF neighbors on Router1"
- "Start a packet capture on the link between the routers"

**Complete Workflow Example:**

Here's a sequence of prompts that demonstrates building and testing a complete lab:

1. "Create a new CML lab called 'My Network Lab'"
2. "Add two IOL routers, an unmanaged switch, and an external connector to this lab"
3. "Connect the two IOL routers to the unmanaged switch and connect the switch to the external connector"
4. "Configure the routers so that their connected interfaces have IPs in the 192.0.2.0/24 subnet and configure OSPF on them"
5. "Start the lab and validate that OSPF is working correctly"
6. "Add a green box annotation around the two IOL routers with the label 'OSPF Area 0'"

Here's a demo showing it working in Claude Desktop:

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

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](https://github.com/xorrkaz/cml-mcp/blob/main/CONTRIBUTING.md) for guidelines.

For development setup, testing, and code style information, see [DEVELOPMENT.md](https://github.com/xorrkaz/cml-mcp/blob/main/DEVELOPMENT.md).

## Troubleshooting

### Common Issues

#### "Module not found" or import errors

Make sure you've installed the package with all extras if you need PyATS support:

```sh
uvx cml-mcp[pyats]  # For uvx installations
```

#### SSL Certificate Errors

If you're using a self-signed certificate on your CML server, set `CML_VERIFY_SSL=false` in your environment configuration.

#### PyATS command execution fails

1. Ensure PyATS is installed with `cml-mcp[pyats]`
2. Verify `PYATS_USERNAME`, `PYATS_PASSWORD`, and `PYATS_AUTH_PASS` are set correctly
3. On Windows, use WSL or Docker for PyATS support

For more troubleshooting help, see [INSTALLATION.md](https://github.com/xorrkaz/cml-mcp/blob/main/INSTALLATION.md).

### Getting Help

- Check the [Issues](https://github.com/xorrkaz/cml-mcp/issues) page for known problems
- See [CONTRIBUTING.md](https://github.com/xorrkaz/cml-mcp/blob/main/CONTRIBUTING.md) for how to report bugs

## Documentation

- **[INSTALLATION.md](https://github.com/xorrkaz/cml-mcp/blob/main/INSTALLATION.md)** - Detailed installation instructions for all platforms and transport modes
- **[DEVELOPMENT.md](https://github.com/xorrkaz/cml-mcp/blob/main/DEVELOPMENT.md)** - Development setup, testing, and contribution guidelines
- **[CONTRIBUTING.md](https://github.com/xorrkaz/cml-mcp/blob/main/CONTRIBUTING.md)** - How to contribute to the project

## License

The MCP server portion of this project is licensed under the [BSD 2-Clause "Simplified" License](https://github.com/xorrkaz/cml-mcp/blob/main/LICENSE).  However, it leverages the pydantic
schema typing code from CML itself, which is covered under a [proprietary Cisco license](https://github.com/xorrkaz/cml-mcp/blob/main/CISCO_LICENSE.md).
