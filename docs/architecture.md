# Architecture

This document describes the architecture and design of the cml-mcp server for developers and contributors.

## System Overview

```mermaid
graph TB
    subgraph "MCP Clients"
        CD[Claude Desktop]
        CC[Claude Code]
        CU[Cursor]
    end
    
    subgraph "cml-mcp Server"
        direction TB
        EP[Entry Point<br/>__main__.py]
        FM[FastMCP Server<br/>server.py]
        MW[Auth Middleware<br/>HTTP only]
        CL[CML Client<br/>cml_client.py]
        SC[Schemas<br/>schemas/]
    end
    
    subgraph "External Services"
        CML[CML Server<br/>REST API]
        DEV[Virtual Devices<br/>via PyATS]
    end
    
    CD & CC & CU -->|MCP Protocol| EP
    EP --> FM
    FM --> MW
    MW --> CL
    CL --> SC
    CL -->|httpx| CML
    CL -->|virl2_client| DEV
```

## Component Details

### Entry Point (`__main__.py`)

Determines transport mode and starts the appropriate server:

```python
def main():
    if settings.cml_mcp_transport == "stdio":
        asyncio.run(run())  # FastMCP async runner
    else:
        uvicorn.run(app, host=str(settings.cml_mcp_bind), port=settings.cml_mcp_port)
```

- **stdio mode**: Uses FastMCP's built-in async runner
- **HTTP mode**: Uses Uvicorn to serve the FastAPI application

### FastMCP Server (`server.py`)

The core module containing:

1. **Server initialization** with FastMCP 2.0
2. **39 MCP tool definitions** as decorated async functions
3. **Authentication middleware** for HTTP mode
4. **CML client** singleton instance

#### Server Initialization

```python
# Enable stateless mode for HTTP transport
if settings.cml_mcp_transport == "http":
    fastmcp_settings.stateless_http = True

# Create FastMCP server instance
server_mcp = FastMCP("Cisco Modeling Labs (CML)")

# Add middleware and create HTTP app for HTTP mode
if settings.cml_mcp_transport == "http":
    server_mcp.add_middleware(CustomRequestMiddleware())
    app = server_mcp.http_app()
```

#### Tool Definition Pattern

All tools follow a consistent pattern:

```python
@server_mcp.tool(
    annotations={
        "title": "Human-readable title",
        "readOnlyHint": True,  # or False
        "destructiveHint": False,  # or True
        "idempotentHint": True,  # optional
    }
)
async def tool_name(param1: Type1, param2: Type2 = default) -> ReturnType:
    """
    Tool description for LLM understanding.
    """
    try:
        result = await cml_client.get("/endpoint")
        return ResultModel(**result)
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error message: {str(e)}", exc_info=True)
        raise ToolError(e)
```

#### Destructive Operations

Tools that modify or delete data use MCP's elicit feature for confirmation:

```python
@server_mcp.tool(annotations={"destructiveHint": True})
async def delete_cml_lab(lid: UUID4Type, ctx: Context) -> bool:
    try:
        elicit_supported = True
        try:
            result = await ctx.elicit("Are you sure you want to delete?", response_type=None)
        except McpError as me:
            if me.error.code == METHOD_NOT_FOUND:
                elicit_supported = False
            else:
                raise me
        
        if not elicit_supported or result.action == "accept":
            # Perform destructive action
            await cml_client.delete(f"/labs/{lid}")
            return True
        else:
            raise Exception("Operation cancelled by user.")
    except Exception as e:
        raise ToolError(e)
```

### CML Client (`cml_client.py`)

Async HTTP client wrapping the CML REST API:

```python
class CMLClient:
    def __init__(
        self, 
        host: str, 
        username: str, 
        password: str, 
        transport: str = "stdio",
        verify_ssl: bool = False
    ):
        self.base_url = host.rstrip("/")
        self.api_base = f"{self.base_url}/api/v0"
        self.client = httpx.AsyncClient(verify=verify_ssl, timeout=API_TIMEOUT)
        self.vclient = virl2_client.ClientLibrary(...)  # For PyATS
```

#### HTTP Methods

| Method | Description |
|--------|-------------|
| `get(endpoint, params)` | HTTP GET request |
| `post(endpoint, data, params)` | HTTP POST request |
| `put(endpoint, data)` | HTTP PUT request |
| `patch(endpoint, data)` | HTTP PATCH request |
| `delete(endpoint)` | HTTP DELETE request |

#### Authentication Flow

```mermaid
sequenceDiagram
    participant T as MCP Tool
    participant C as CMLClient
    participant A as CML API

    T->>C: Request (e.g., get_cml_labs)
    C->>C: check_authentication()
    
    alt No token or expired
        C->>A: POST /authenticate
        A-->>C: JWT Token
        C->>C: Store token
    end
    
    C->>A: GET /labs (with token)
    A-->>C: Response
    C-->>T: Parsed result
```

### Settings (`settings.py`)

Pydantic-based configuration:

```python
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

### Schemas (`schemas/`)

Pydantic models for CML API request/response validation:

```
schemas/
├── common.py              # UUID4Type, UserName, DefinitionID, etc.
├── labs.py                # Lab, LabCreate, LabTopology
├── nodes.py               # Node, NodeCreate, NodeTopology
├── links.py               # Link, LinkCreate, LinkConditionConfiguration
├── interfaces.py          # InterfaceCreate, InterfaceResponse
├── topologies.py          # Topology (for full lab import)
├── annotations.py         # TextAnnotation, RectangleAnnotation, etc.
├── users.py               # UserCreate, UserResponse
├── groups.py              # GroupCreate, GroupInfoResponse
├── system.py              # SystemInformation, SystemHealth, SystemStats
└── simple_core/           # State enums and type hints
```

## Data Flow

### stdio Mode

```mermaid
sequenceDiagram
    participant U as User
    participant C as Claude Desktop
    participant M as cml-mcp (stdio)
    participant A as CML API

    U->>C: "Create a lab with 2 routers"
    C->>M: JSON-RPC (stdin)
    M->>A: POST /labs
    A-->>M: Lab created
    M->>A: POST /labs/{id}/nodes
    A-->>M: Node created (x2)
    M-->>C: JSON-RPC (stdout)
    C-->>U: "Created lab with 2 routers"
```

### HTTP Mode

```mermaid
sequenceDiagram
    participant U as User
    participant C as Claude Desktop
    participant R as mcp-remote
    participant M as cml-mcp (HTTP)
    participant A as CML API

    U->>C: "Create a lab with 2 routers"
    C->>R: JSON-RPC (stdin)
    R->>M: HTTP POST /mcp<br/>X-Authorization: Basic ...
    M->>M: Validate credentials
    M->>A: POST /authenticate
    A-->>M: JWT Token
    M->>A: POST /labs
    A-->>M: Lab created
    M-->>R: SSE Response
    R-->>C: JSON-RPC (stdout)
    C-->>U: "Created lab with 2 routers"
```

## Error Handling

All tools use consistent error handling:

```python
try:
    # Tool implementation
    result = await cml_client.get("/endpoint")
    return result
except httpx.HTTPStatusError as e:
    # HTTP errors from CML API
    raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
except Exception as e:
    # Log for debugging
    logger.error(f"Error message: {str(e)}", exc_info=True)
    # Raise as ToolError for MCP protocol
    raise ToolError(e)
```

## PyATS Integration

For CLI command execution on running devices:

```mermaid
sequenceDiagram
    participant T as send_cli_command
    participant P as ClPyats
    participant L as CML Lab
    participant D as Virtual Device

    T->>P: Create ClPyats(lab)
    P->>L: sync_testbed()
    L-->>P: Testbed with devices
    T->>P: run_command(label, commands)
    P->>D: SSH connect
    P->>D: Execute command
    D-->>P: Output
    P-->>T: Command results
```

The integration uses:

- **virl2_client**: CML SDK for lab access
- **PyATS/Genie**: Cisco test automation framework
- **ClPyats**: Bridge between CML and PyATS

## Dependencies

```mermaid
graph LR
    subgraph Core
        FM[fastmcp]
        FA[fastapi]
        UV[uvicorn]
    end
    
    subgraph HTTP
        HX[httpx]
    end
    
    subgraph CML
        V2[virl2_client]
    end
    
    subgraph Validation
        PD[pydantic]
        PS[pydantic-settings]
    end
    
    subgraph Optional
        PA[pyats]
        GE[genie]
    end
    
    cml-mcp --> FM & HX & V2 & PD
    FM --> FA & UV
    V2 --> PA & GE
```

## Extension Points

### Adding a New Tool

1. Define the tool function in `server.py`:

```python
@server_mcp.tool(
    annotations={
        "title": "My New Tool",
        "readOnlyHint": True,
    }
)
async def my_new_tool(param: str) -> dict:
    """Tool description."""
    result = await cml_client.get(f"/my-endpoint/{param}")
    return result
```

2. Add any required schemas to `schemas/`

3. Update documentation

### Adding a New Schema

1. Create or update schema file in `schemas/`
2. Import in `schemas/__init__.py`
3. Use in tool definitions
