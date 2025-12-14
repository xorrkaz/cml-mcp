# Configuration

This document describes all configuration options for the cml-mcp server.

## Environment Variables

The server is configured entirely through environment variables. You can set these in your shell, in a `.env` file, or pass them through your MCP client configuration.

### Core Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CML_URL` | Yes | - | URL of the CML server |
| `CML_USERNAME` | stdio only | - | Username for CML authentication |
| `CML_PASSWORD` | stdio only | - | Password for CML authentication |

### Transport Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `CML_MCP_TRANSPORT` | `stdio` | Transport mode: `stdio` or `http` |
| `CML_MCP_BIND` | `0.0.0.0` | IP address to bind (HTTP mode) |
| `CML_MCP_PORT` | `9000` | Port to bind (HTTP mode) |

### Security Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `CML_VERIFY_SSL` | `false` | Verify SSL certificates |

### PyATS Settings

Required for executing CLI commands on running devices:

| Variable | Default | Description |
|----------|---------|-------------|
| `PYATS_USERNAME` | `cisco` | Device login username |
| `PYATS_PASSWORD` | `cisco` | Device login password |
| `PYATS_AUTH_PASS` | `cisco` | Device enable password |

### Debug Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Enable debug logging |

## Configuration File (.env)

Create a `.env` file in the project root:

```bash
# =============================================================================
# CML-MCP Configuration
# =============================================================================

# CML Server Connection (Required)
CML_URL=https://cml.example.com
CML_USERNAME=admin
CML_PASSWORD=your_secure_password

# SSL Verification (set to false for self-signed certificates)
CML_VERIFY_SSL=false

# Transport Configuration
CML_MCP_TRANSPORT=stdio    # Options: stdio, http
CML_MCP_BIND=0.0.0.0       # HTTP mode only
CML_MCP_PORT=9000          # HTTP mode only

# PyATS Device Credentials (for CLI command execution)
PYATS_USERNAME=cisco
PYATS_PASSWORD=cisco
PYATS_AUTH_PASS=cisco

# Logging
DEBUG=false
```

## Settings Class

Configuration is managed by the `Settings` class in `settings.py`:

```python
class TransportEnum(StrEnum):
    HTTP = "http"
    STDIO = "stdio"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="",
    )

    cml_url: AnyHttpUrl | None = Field(default=None)
    cml_username: str | None = Field(default=None)
    cml_password: str | None = Field(default=None)
    cml_verify_ssl: bool = Field(default=False)
    cml_mcp_transport: TransportEnum = Field(default=TransportEnum.STDIO)
    cml_mcp_bind: IPvAnyAddress = Field(default_factory=lambda: IPv4Address("0.0.0.0"))
    cml_mcp_port: int = Field(default=9000)
    debug: bool = Field(default=False)
```

### Validation Rules

1. **`CML_URL`** is always required
2. **`CML_USERNAME`** and **`CML_PASSWORD`** are required for stdio transport
3. In HTTP mode, credentials come from request headers (see [Transport Modes](transport-modes.md))

## MCP Client Configuration

### Claude Desktop / Claude Code

Edit `~/.config/claude/claude_desktop_config.json` (Linux/macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "Cisco Modeling Labs": {
      "command": "uvx",
      "args": ["cml-mcp"],
      "env": {
        "CML_URL": "https://cml.example.com",
        "CML_USERNAME": "admin",
        "CML_PASSWORD": "secret123"
      }
    }
  }
}
```

### With Full Options

```json
{
  "mcpServers": {
    "Cisco Modeling Labs": {
      "command": "uvx",
      "args": ["cml-mcp[pyats]"],
      "env": {
        "CML_URL": "https://cml.example.com",
        "CML_USERNAME": "admin",
        "CML_PASSWORD": "secret123",
        "CML_VERIFY_SSL": "false",
        "PYATS_USERNAME": "cisco",
        "PYATS_PASSWORD": "cisco",
        "PYATS_AUTH_PASS": "cisco",
        "DEBUG": "false"
      }
    }
  }
}
```

### Docker Configuration

```json
{
  "mcpServers": {
    "Cisco Modeling Labs": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm", "--pull", "always",
        "-e", "CML_URL",
        "-e", "CML_USERNAME",
        "-e", "CML_PASSWORD",
        "-e", "CML_VERIFY_SSL",
        "-e", "PYATS_USERNAME",
        "-e", "PYATS_PASSWORD",
        "-e", "PYATS_AUTH_PASS",
        "xorrkaz/cml-mcp:latest"
      ],
      "env": {
        "CML_URL": "https://cml.example.com",
        "CML_USERNAME": "admin",
        "CML_PASSWORD": "secret123",
        "CML_VERIFY_SSL": "false",
        "PYATS_USERNAME": "cisco",
        "PYATS_PASSWORD": "cisco",
        "PYATS_AUTH_PASS": "cisco"
      }
    }
  }
}
```

## HTTP Mode Headers

When using HTTP transport, authentication is provided via request headers:

| Header | Format | Description |
|--------|--------|-------------|
| `X-Authorization` | `Basic <base64(user:pass)>` | CML credentials |
| `X-PyATS-Authorization` | `Basic <base64(user:pass)>` | Device credentials |
| `X-PyATS-Enable` | `Basic <base64(password)>` | Enable password |

### Encoding Credentials

```bash
# Linux/macOS
echo -n "username:password" | base64
# Output: dXNlcm5hbWU6cGFzc3dvcmQ=

# Windows PowerShell
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("username:password"))
```

## Precedence

Configuration values are loaded in this order (later sources override earlier):

1. Default values in `Settings` class
2. `.env` file in the current directory
3. Environment variables
4. (HTTP mode) Request headers

## Common Configuration Scenarios

### Development with Local CML

```bash
CML_URL=https://192.168.1.100
CML_USERNAME=admin
CML_PASSWORD=admin
CML_VERIFY_SSL=false
DEBUG=true
```

### Production HTTP Server

```bash
CML_URL=https://cml.company.com
CML_MCP_TRANSPORT=http
CML_MCP_BIND=0.0.0.0
CML_MCP_PORT=9000
CML_VERIFY_SSL=true
DEBUG=false
```

### Docker Compose

See [Docker](docker.md) for complete docker-compose configuration.
