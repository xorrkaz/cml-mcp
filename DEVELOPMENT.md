# Development Guide

This guide covers how to set up a development environment and contribute to the CML MCP server.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Development Tasks](#development-tasks)
- [Testing](#testing)
- [Code Style](#code-style)
- [Project Structure](#project-structure)
- [Publishing and Release](#publishing-and-release)

## Prerequisites

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/) - Python package/project manager
- [just](https://github.com/casey/just) - Command runner (optional but recommended)
- [direnv](https://direnv.net/) - Environment variable manager (optional but recommended)

## Quick Start

1. Clone the repository:

    ```sh
    git clone https://github.com/xorrkaz/cml-mcp.git
    cd cml-mcp
    ```

2. (Optional) If using direnv, allow it to set up your environment:

    ```sh
    direnv allow
    ```

    This will automatically create a virtual environment and install dependencies when you `cd` into the directory.

3. If not using direnv, manually install dependencies:

    ```sh
    uv sync --all-extras
    source .venv/bin/activate
    ```

4. Create a `.env` file with your CML server credentials:

    ```sh
    CML_URL=https://your-cml-server.example.com
    CML_USERNAME=your_username
    CML_PASSWORD=your_password
    CML_VERIFY_SSL=false
    DEBUG=true
    # Optional for CLI command support
    PYATS_USERNAME=device_username
    PYATS_PASSWORD=device_password
    PYATS_AUTH_PASS=enable_password
    ```

## Development Tasks

The project uses `just` as a task runner. Common commands:

```sh
# Show all available commands
just

# Run tests with mocks (fast, no CML server needed)
just test

# Run tests against a live CML server
just test-live

# Install/update dependencies
just install

# Update all dependencies to latest versions
just update

# Build the package
just build

# Clean temporary files
just clean

# Full clean and reinstall
just fresh
```

## Testing

The project includes comprehensive tests that can run in two modes:

### Mock Mode (Default)

Fast tests using pre-recorded API responses:

```sh
# Using pytest directly
pytest tests/

# Using just
just test

# Run specific test file
just test tests/test_cml_mcp.py
```

### Live Mode

Tests against a real CML server:

```sh
# Requires CML_URL, CML_USERNAME, CML_PASSWORD in environment
export USE_MOCKS=false
pytest tests/

# Or using just
just test-live
```

See [tests/README.md](https://github.com/xorrkaz/cml-mcp/blob/main/tests/README.md) for more details on the testing framework.

## Code Style

The project uses:

- **black** - Code formatting
- **isort** - Import sorting
- **flake8** - Linting

These are configured in [pyproject.toml](pyproject.toml) with a 140-character line length.

Before committing, ensure your code is properly formatted:

```sh
black src/ tests/
isort src/ tests/
flake8 src/ tests/
```

## Project Structure

```text
cml-mcp/
├── src/cml_mcp/          # Main source code
│   ├── server.py         # FastMCP server initialization and tool registration
│   ├── cml_client.py     # CML API client wrapper
│   ├── settings.py       # Configuration management
│   ├── types.py          # Type definitions
│   ├── cml/              # CML API schema definitions (Pydantic models)
│   └── tools/            # Modular tool implementations
│       ├── __init__.py
│       ├── dependencies.py    # Shared dependencies (CML client)
│       ├── middleware.py      # HTTP middleware and ACL support
│       ├── system.py          # System information tools
│       ├── users_groups.py    # User and group management
│       ├── node_definitions.py # Node type queries
│       ├── labs.py            # Lab lifecycle management
│       ├── nodes.py           # Node operations
│       ├── interfaces.py      # Interface management
│       ├── links.py           # Link operations
│       ├── annotations.py     # Visual annotations
│       ├── pcap.py            # Packet capture tools
│       └── cli.py             # CLI command execution (PyATS)
├── tests/                # Test suite
│   ├── conftest.py       # pytest configuration and fixtures
│   ├── test_cml_mcp.py   # Main test file
│   ├── mocks/            # Mock API responses for testing
│   ├── input_data/       # Test input files
│   ├── README.md         # Test documentation
│   ├── QUICK_START.md    # Quick testing guide
│   └── MOCK_FRAMEWORK.md # Mock framework details
├── Justfile              # Task automation
├── pyproject.toml        # Python project configuration
├── Dockerfile            # Container image definition
└── .envrc                # direnv configuration
```

### Modular Tool Architecture

The server uses a modular architecture where tools are organized by functional category:

- **Each module** (e.g., `labs.py`, `nodes.py`) contains related tools
- **Each module** exports a `register_tools(mcp)` function that registers its tools with the FastMCP server
- **Dependencies** are centralized in `dependencies.py` (e.g., CML client singleton)
- **Middleware** in `middleware.py` provides HTTP transport support and ACL enforcement

This design allows for:

- Easy addition of new tools in appropriate modules
- Clear separation of concerns
- Simplified testing of individual tool categories
- Better code organization and maintainability

Example module structure:

```python
# src/cml_mcp/tools/example.py
from fastmcp import FastMCP
from cml_mcp.tools.dependencies import get_cml_client_dep

def register_tools(mcp: FastMCP):
    @mcp.tool()
    async def my_tool(param: str) -> dict:
        client = get_cml_client_dep()
        # Tool implementation
        ...
```

## Publishing and Release

> **Note:** This section is for project maintainers only.

The project uses `just` to streamline the publishing process:

```sh
# Build package and Docker images
just build

# Publish to PyPI (prompts for token)
just publish_pypi

# Publish to MCP registry
just publish_mcp

# Publish Docker images
just publish_docker

# Do all of the above
just publish
```

**Note:** Version numbers are defined in [pyproject.toml](pyproject.toml). Update the version before publishing a new release.
