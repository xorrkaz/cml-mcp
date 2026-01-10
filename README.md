# Model Context Protocol (MCP) Server for Cisco Modeling Labs (CML)

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/xorrkaz/cml-mcp)

mcp-name: io.github.xorrkaz/cml-mcp

## Overview

`cml-mcp` is a server implementation of the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/docs/getting-started/intro) designed for [Cisco Modeling Labs (CML)](https://www.cisco.com/c/en/us/products/cloud-systems-management/modeling-labs/index.html). It is built using [FastMCP 2.0](https://gofastmcp.com/getting-started/welcome) and designed to provide a set of tools for LLM apps like Claude Desktop, Claude Code, and Cursor to interact with CML.

## Features

- **Create Lab Topologies:** Tools to create new labs and define network topologies from scratch or using full topology definitions.
- **Query Status:** Tools to retrieve detailed status information for labs, nodes, links, annotations, and the CML server itself.
- **Control Labs and Nodes:** Tools to start, stop, and wipe labs or individual nodes as needed.
- **Manage CML Users and Groups:** Tools to list, create, and delete local users and groups (requires admin privileges).
- **Visual Annotations:** Add visual elements (text, rectangles, ellipses, lines) to lab topologies for documentation and organization.
- **Link Management:** Connect nodes, configure link conditioning (bandwidth, latency, jitter, loss), and control link states.
- **Node Configuration:** Configure node startup configurations and send CLI commands to running devices.
- **Run Commands on Devices:** Using [PyATS](https://developer.cisco.com/pyats/), MCP clients can execute commands on virtual devices within CML labs.
- **Console Log Access:** Retrieve console logs from running nodes for troubleshooting and monitoring.

## Quick Start

### Installation

The easiest way to get started is using `uvx` with Claude Desktop. Add this to your `claude_desktop_config.json`:

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

For CLI command support, use `cml-mcp[pyats]` instead. See [INSTALLATION.md](INSTALLATION.md) for detailed installation instructions including Docker, WSL, and HTTP transport options.

### Requirements

- **Python 3.12 or later**
- **Cisco Modeling Labs (CML) 2.9 or later**
- **[uv](https://docs.astral.sh/uv/)** - Python package manager

## Available MCP Tools

The server provides 40 MCP tools organized into the following categories:

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

The tools show up automatically in your MCP client, and you can chat with the LLM to invoke them as needed. For example,
the following sequence of prompts demonstrates the server's capabilities:

- Create a new CML lab called "Joe's MCP Lab".
- Add two IOL nodes, a unmanaged switch, and an external connector to this lab.
- Connect the two IOL nodes to the unmanaged switch and the unmanaged switch to the external connector.
- Configure the routers so that their connected interfaces have IPs in the 192.0.2.0/24 subnet. Configure OSPF on them. Then start the lab and validate OSPF is working correctly.
- Add a box annotation around the two IOL nodes that indicates they speak OSPF. Make it a green box.

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

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

For development setup, testing, and code style information, see [DEVELOPMENT.md](DEVELOPMENT.md).

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

For more troubleshooting help, see [INSTALLATION.md](INSTALLATION.md).

### Getting Help

- Check the [Issues](https://github.com/xorrkaz/cml-mcp/issues) page for known problems
- See [CONTRIBUTING.md](CONTRIBUTING.md) for how to report bugs

## Documentation

- **[INSTALLATION.md](INSTALLATION.md)** - Detailed installation instructions for all platforms and transport modes
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Development setup, testing, and contribution guidelines
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - How to contribute to the project

## License

The MCP server portion of this project is licensed under the [BSD 2-Clause "Simplified" License](LICENSE).  However, it leverages the pydantic
schema typing code from CML itself, which is covered under a [proprietary Cisco license](CISCO_LICENSE.md).
