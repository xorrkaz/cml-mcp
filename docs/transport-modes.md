# Transport Modes

cml-mcp supports two transport modes for communication with MCP clients: **stdio** and **HTTP**.

## Overview

| Feature | stdio Mode | HTTP Mode |
|---------|------------|-----------|
| Communication | stdin/stdout pipes | HTTP + Server-Sent Events |
| Authentication | Environment variables | HTTP headers (per-request) |
| Token caching | ✅ Yes | ❌ No (stateless) |
| Multi-client | ❌ No | ✅ Yes |
| Remote access | ❌ No | ✅ Yes |
| Complexity | Low | Medium |

```mermaid
graph TB
    subgraph "stdio Mode"
        A1[MCP Client] <-->|stdin/stdout| B1[cml-mcp]
        B1 --> C1[CML API]
    end

    subgraph "HTTP Mode"
        A2[MCP Client] <-->|stdio| M[mcp-remote]
        M <-->|HTTP/SSE| B2[cml-mcp]
        B2 --> C2[CML API]
    end
```

## stdio Mode (Default)

The standard MCP transport where the server reads JSON-RPC requests from stdin and writes responses to stdout.

### When to Use

- Direct integration with MCP clients (Claude Desktop, Cursor)
- Single-user, single-client scenarios
- Simplest setup and configuration
- Running locally on the same machine

### Configuration

```bash
# Environment variables
export CML_URL=https://cml.example.com
export CML_USERNAME=admin
export CML_PASSWORD=secret
# CML_MCP_TRANSPORT defaults to "stdio"

# Run
cml-mcp
```

### MCP Client Configuration

=== "uvx"

    ```json
    {
      "mcpServers": {
        "Cisco Modeling Labs": {
          "command": "uvx",
          "args": ["cml-mcp"],
          "env": {
            "CML_URL": "https://cml.example.com",
            "CML_USERNAME": "admin",
            "CML_PASSWORD": "secret"
          }
        }
      }
    }
    ```

=== "Docker"

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
            "xorrkaz/cml-mcp:latest"
          ],
          "env": {
            "CML_URL": "https://cml.example.com",
            "CML_USERNAME": "admin",
            "CML_PASSWORD": "secret"
          }
        }
      }
    }
    ```

### How It Works

```
┌─────────────────┐     stdin      ┌─────────────────┐
│   MCP Client    │ ──────────────▶│   cml-mcp       │
│ (Claude Desktop)│                │   (stdio)       │
│                 │ ◀──────────────│                 │
└─────────────────┘     stdout     └─────────────────┘
```

1. Client spawns cml-mcp as a subprocess
2. Client sends JSON-RPC requests via stdin
3. Server authenticates once, caches JWT token
4. Server processes requests and calls CML API
5. Server writes JSON-RPC responses to stdout

---

## HTTP Mode

Runs as a standalone HTTP service using Server-Sent Events (SSE) for streaming.

### When to Use

- Multiple clients connecting to the same server
- Running on a remote machine or server
- Containerized/Kubernetes deployments
- Shared infrastructure scenarios
- Clients that don't support process spawning
- **Connecting to multiple CML servers** (per-request server selection)

### Configuration

```bash
# Server configuration
export CML_URL=https://cml.example.com    # Default/fallback CML server
export CML_MCP_TRANSPORT=http
export CML_MCP_BIND=0.0.0.0
export CML_MCP_PORT=9000
# No username/password needed (provided via headers)

# Optional: Multi-server security
export CML_ALLOWED_URLS='["https://cml-prod.example.com", "https://cml-dev.example.com"]'
export CML_URL_PATTERN='^https://cml-.*\.example\.com$'

# Optional: Pool tuning
export CML_POOL_MAX_SIZE=50
export CML_POOL_TTL_SECONDS=300
export CML_POOL_MAX_PER_SERVER=5

# Run
cml-mcp

# Or with uvicorn directly (for development)
uvicorn cml_mcp.server:app --host 0.0.0.0 --port 9000 --reload
```

### Request Headers

In HTTP mode, server selection and authentication are provided on each request:

| Header | Format | Required | Purpose |
|--------|--------|----------|--------|
| `X-CML-Server-URL` | URL | No | Target CML server (falls back to `CML_URL` env var) |
| `X-Authorization` | `Basic <base64(user:pass)>` | **Yes** | CML credentials |
| `X-CML-Verify-SSL` | `true` or `false` | No | SSL verification override (defaults to `CML_VERIFY_SSL` env var) |
| `X-PyATS-Authorization` | `Basic <base64(user:pass)>` | No | Device credentials for CLI commands |
| `X-PyATS-Enable` | `Basic <base64(password)>` | No | Enable password for CLI commands |

!!! info "Header Fallback Behavior"
    - **`X-CML-Server-URL`**: If not provided, the server uses `CML_URL` environment variable as the default target.
    - **`X-CML-Verify-SSL`**: If not provided, uses `CML_VERIFY_SSL` environment variable (defaults to `false`).
    - **`X-Authorization`**: Always required in HTTP mode—there is no fallback to environment variables.

!!! warning "Security Consideration: PyATS Credentials"
    When `X-PyATS-Authorization` and `X-PyATS-Enable` headers are provided, the server temporarily sets `PYATS_USERNAME`, `PYATS_PASSWORD`, and `PYATS_AUTH_PASS` environment variables for the duration of the request. These are cleared after each request.

### Encoding Credentials

```bash
# Linux/macOS
echo -n "admin:secret" | base64
# Output: YWRtaW46c2VjcmV0

# Windows PowerShell
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("admin:secret"))
```

### MCP Client Configuration

MCP clients don't natively support HTTP. Use `mcp-remote` as a bridge:

=== "Basic"

    ```json
    {
      "mcpServers": {
        "Cisco Modeling Labs": {
          "command": "npx",
          "args": [
            "-y", "mcp-remote",
            "http://server-host:9000/mcp",
            "--header", "X-Authorization: Basic YWRtaW46c2VjcmV0"
          ]
        }
      }
    }
    ```

=== "Multi-Server"

    ```json
    {
      "mcpServers": {
        "CML Production": {
          "command": "npx",
          "args": [
            "-y", "mcp-remote",
            "http://server-host:9000/mcp",
            "--header", "X-CML-Server-URL: https://cml-prod.example.com",
            "--header", "X-Authorization: Basic YWRtaW46cHJvZHBhc3M=",
            "--header", "X-CML-Verify-SSL: true"
          ]
        },
        "CML Development": {
          "command": "npx",
          "args": [
            "-y", "mcp-remote",
            "http://server-host:9000/mcp",
            "--header", "X-CML-Server-URL: https://cml-dev.example.com",
            "--header", "X-Authorization: Basic ZGV2OnBhc3M="
          ]
        }
      }
    }
    ```

=== "With PyATS"

    ```json
    {
      "mcpServers": {
        "Cisco Modeling Labs": {
          "command": "npx",
          "args": [
            "-y", "mcp-remote",
            "http://server-host:9000/mcp",
            "--header", "X-Authorization: Basic YWRtaW46c2VjcmV0",
            "--header", "X-PyATS-Authorization: Basic Y2lzY286Y2lzY28=",
            "--header", "X-PyATS-Enable: Basic Y2lzY28="
          ]
        }
      }
    }
    ```

=== "Self-signed TLS"

    ```json
    {
      "mcpServers": {
        "Cisco Modeling Labs": {
          "command": "npx",
          "args": [
            "-y", "mcp-remote",
            "https://server-host:9000/mcp",
            "--header", "X-Authorization: Basic YWRtaW46c2VjcmV0"
          ],
          "env": {
            "NODE_TLS_REJECT_UNAUTHORIZED": "0"
          }
        }
      }
    }
    ```

### How It Works

```
┌─────────────────┐              ┌─────────────────┐              ┌─────────────────┐
│   MCP Client    │    stdio     │   mcp-remote    │   HTTP/SSE   │   cml-mcp       │
│ (Claude Desktop)│◀────────────▶│    (bridge)     │◀────────────▶│   (HTTP)        │
└─────────────────┘              └─────────────────┘              └─────────────────┘
                                                                          │
                                                                          ▼
                                                                 ┌─────────────────┐
                                                                 │  Client Pool    │
                                                                 │  ┌───┐ ┌───┐    │
                                                                 │  │P1 │ │P2 │... │
                                                                 │  └───┘ └───┘    │
                                                                 └─────────────────┘
                                                                          │
                                         ┌────────────────────────────────┼────────────────────────────────┐
                                         ▼                                ▼                                ▼
                                ┌─────────────────┐              ┌─────────────────┐              ┌─────────────────┐
                                │  CML Server 1   │              │  CML Server 2   │              │  CML Server N   │
                                └─────────────────┘              └─────────────────┘              └─────────────────┘
```

1. Client spawns `mcp-remote` as a subprocess
2. `mcp-remote` connects to cml-mcp via HTTP with headers
3. Middleware extracts `X-CML-Server-URL` (or uses default)
4. Client pool provides/creates a CMLClient for that server
5. Server authenticates with target CML on each request (stateless)
6. Responses are streamed via Server-Sent Events
7. Client is released back to pool

### Client Pool

HTTP mode uses a connection pool for efficient multi-server support:

| Feature | Description |
|---------|-------------|
| **LRU Eviction** | Removes least recently used clients when pool is full (`CML_POOL_MAX_SIZE`) |
| **TTL Eviction** | Removes idle clients after configurable timeout (`CML_POOL_TTL_SECONDS`) |
| **Per-Server Limits** | Prevents connection exhaustion to any single server (`CML_POOL_MAX_PER_SERVER`) |
| **URL Validation** | Allowlist (`CML_ALLOWED_URLS`) and/or pattern-based (`CML_URL_PATTERN`) security |
| **URL Normalization** | URLs are normalized (lowercase, default ports removed) for consistent cache keys |

!!! tip "Pool Configuration"
    For high-load environments, tune the pool settings:

    ```bash
    CML_POOL_MAX_SIZE=100        # Support more concurrent CML servers
    CML_POOL_TTL_SECONDS=600     # Keep clients alive longer (10 minutes)
    CML_POOL_MAX_PER_SERVER=10   # Allow more concurrent requests per server
    ```

### Authentication Middleware

The HTTP mode uses custom middleware to handle per-request server selection:

```python
class CustomRequestMiddleware(Middleware):
    async def on_request(self, context: MiddlewareContext, call_next) -> Any:
        headers = get_http_headers()

        # Get target CML server (with fallback to default)
        cml_url = headers.get("x-cml-server-url") or settings.cml_url

        # Extract credentials
        auth_header = headers.get("x-authorization")
        username, password = decode_basic_auth(auth_header)

        # Get client from pool (validates URL, manages connections)
        client = await cml_pool.get_client(cml_url, username, password)
        current_cml_client.set(client)  # Request-scoped via ContextVar

        try:
            await client.check_authentication()
            return await call_next(context)
        finally:
            await cml_pool.release_client(cml_url)
            current_cml_client.set(None)
```

---

## Docker Deployments

### stdio Mode

```bash
docker run -i --rm \
  -e CML_URL=https://cml.example.com \
  -e CML_USERNAME=admin \
  -e CML_PASSWORD=secret \
  xorrkaz/cml-mcp:latest
```

### HTTP Mode (Single Server)

```bash
docker run -d \
  --name cml-mcp \
  -p 9000:9000 \
  -e CML_URL=https://cml.example.com \
  -e CML_MCP_TRANSPORT=http \
  xorrkaz/cml-mcp:latest
```

### HTTP Mode (Multi-Server with Security)

```bash
docker run -d \
  --name cml-mcp \
  -p 9000:9000 \
  -e CML_URL=https://cml-prod.example.com \
  -e CML_MCP_TRANSPORT=http \
  -e CML_ALLOWED_URLS='["https://cml-prod.example.com","https://cml-dev.example.com"]' \
  -e CML_POOL_MAX_SIZE=100 \
  xorrkaz/cml-mcp:latest
```

### Docker Compose

See [Docker](docker.md) for complete docker-compose configuration with multiple profiles.

---

## Choosing a Transport

| Scenario | Recommended |
|----------|-------------|
| Desktop usage with Claude Desktop/Cursor | stdio |
| Single user, local machine | stdio |
| Multiple users/clients | HTTP |
| Running on a server | HTTP |
| Kubernetes deployment | HTTP |
| CI/CD pipelines | Either |
| Maximum simplicity | stdio |
| Maximum flexibility | HTTP |
| **Multiple CML servers** | **HTTP** |
