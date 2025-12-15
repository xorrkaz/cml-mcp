# Development Guide

This guide covers setting up a development environment, coding standards, testing, and contribution guidelines.

## Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.12+ | Runtime |
| uv | Latest | Package management (recommended) |
| Poetry | Latest | Alternative package management |
| Git | Latest | Version control |
| CML | 2.9+ | Testing |
| Docker | Latest | Container builds (optional) |
| just | Latest | Task automation (optional) |

## Development Setup

### Option 1: Using uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/xorrkaz/cml-mcp.git
cd cml-mcp

# Install dependencies with all extras
uv sync --all-extras

# Create environment file
cp .env.example .env
# Edit .env with your CML credentials

# Run the server
uv run cml-mcp
```

### Option 2: Using Poetry

```bash
# Clone the repository
git clone https://github.com/xorrkaz/cml-mcp.git
cd cml-mcp

# Configure Poetry for in-project venv
poetry config virtualenvs.in-project true

# Install dependencies
poetry install

# Activate the environment
source .venv/bin/activate

# Create environment file
cp .env.example .env
```

### Option 3: Using just

If you have `just` installed:

```bash
git clone https://github.com/xorrkaz/cml-mcp.git
cd cml-mcp

# Install dependencies
just install

# Run tests
just test
```

## Project Structure

```
cml-mcp/
├── src/cml_mcp/           # Source code
│   ├── __init__.py        # Package init, version
│   ├── __main__.py        # CLI entry point
│   ├── server.py          # MCP server, 39 tool definitions
│   ├── cml_client.py      # Async HTTP client for CML API
│   ├── settings.py        # Pydantic settings configuration
│   ├── types.py           # Custom type definitions
│   └── schemas/           # Pydantic models for CML API
│       ├── common.py      # Shared types (UUID4Type, etc.)
│       ├── labs.py        # Lab models
│       ├── nodes.py       # Node models
│       ├── links.py       # Link models
│       └── ...            # Other schema modules
├── docs/                  # MkDocs documentation
├── tests/                 # Test suite
├── .github/               # GitHub Actions workflows
├── pyproject.toml         # Project configuration
├── Justfile               # Task automation
├── Dockerfile             # Container build
├── docker-compose.yml     # Multi-profile compose
├── .env.example           # Configuration template
└── README.md              # User documentation
```

## Running the Server

### Development Mode (stdio)

```bash
# Using uv
uv run cml-mcp

# Using Poetry
poetry run cml-mcp

# Direct Python
python -m cml_mcp
```

### Development Mode (HTTP)

```bash
# Set transport mode
export CML_MCP_TRANSPORT=http

# Run with uvicorn (auto-reload for development)
uvicorn cml_mcp.server:app --host 0.0.0.0 --port 9000 --reload
```

### Using Docker

```bash
# Build and run HTTP mode
just up

# View logs
just logs

# Stop
just down
```

## Code Style

### Formatting with Black

```bash
# Format a file
black src/cml_mcp/server.py

# Format all files
black src/

# Check without modifying
black --check src/
```

Configuration in `pyproject.toml`:

```toml
[tool.black]
line-length = 140
```

### Import Sorting with isort

```bash
# Sort imports in a file
isort src/cml_mcp/server.py

# Sort all imports
isort src/
```

### Pre-commit Workflow

Before committing:

```bash
# Format and lint
black src/
isort src/

# Run tests
just test
```

## Testing

### Running Tests

```bash
# Using uv
uv run -m pytest

# Using Poetry
poetry run pytest

# Using just
just test

# With coverage
pytest --cov=cml_mcp --cov-report=html
```

### Test Structure

```
tests/
├── conftest.py          # Fixtures
├── test_server.py       # Server tests
├── test_client.py       # Client tests
├── test_settings.py     # Settings tests
└── test_schemas.py      # Schema validation tests
```

### Writing Tests

```python
import pytest
from cml_mcp.settings import Settings

def test_settings_defaults():
    """Test default settings values."""
    settings = Settings(cml_url="https://example.com")
    assert settings.cml_mcp_transport == "stdio"
    assert settings.cml_mcp_port == 9000

@pytest.mark.asyncio
async def test_get_cml_labs(mock_client):
    """Test getting lab list."""
    from cml_mcp.server import get_cml_labs
    labs = await get_cml_labs()
    assert isinstance(labs, list)
```

## Adding a New Tool

1. **Define the tool** in `server.py`:

```python
@server_mcp.tool(
    annotations={
        "title": "My New Tool",
        "readOnlyHint": True,  # Set appropriately
    }
)
async def my_new_tool(param: str) -> dict:
    """
    Tool description for LLM.

    Explain what the tool does and any constraints.
    """
    try:
        result = await cml_client.get(f"/my-endpoint/{param}")
        return result
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Error in my_new_tool: {str(e)}", exc_info=True)
        raise ToolError(e)
```

2. **Add schemas** if needed in `schemas/`:

```python
# schemas/my_models.py
from pydantic import BaseModel, Field

class MyModel(BaseModel):
    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., min_length=1, max_length=100)
```

3. **Write tests**:

```python
# tests/test_my_tool.py
@pytest.mark.asyncio
async def test_my_new_tool():
    result = await my_new_tool("test-param")
    assert "expected_key" in result
```

4. **Update documentation** in `docs/api-reference.md`

## Building Documentation

```bash
# Serve documentation locally
just docs-serve

# Build static site
just docs-build
```

## Docker Development

### Building Images

```bash
# Build local image
just docker-build

# Build with custom tag
just docker-build v1.0.0
```

### Running Containers

```bash
# HTTP mode (default)
just up

# stdio mode
just stdio

# Development mode (mounts source)
just dev

# View logs
just logs

# Shell into container
just shell
```

## Justfile Commands

| Command | Description |
|---------|-------------|
| `just` | List all available recipes |
| `just install` | Install dependencies |
| `just test` | Run tests |
| `just build` | Build package and Docker image |
| `just up` | Start HTTP server |
| `just down` | Stop services |
| `just logs` | View container logs |
| `just dev` | Development mode with source mounting |
| `just stdio` | Run in stdio mode |
| `just clean` | Remove caches and venv |
| `just fresh` | Clean reinstall |
| `just docs-serve` | Serve documentation locally |
| `just docs-build` | Build documentation |

## Contributing

### Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `just test`
5. Format code: `black src/ && isort src/`
6. Commit with a descriptive message
7. Push and create a Pull Request

### Commit Message Format

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:

```
feat(tools): add support for lab cloning
fix(client): handle token expiration correctly
docs(api): update parameter descriptions
```

### Code Review Checklist

- [ ] Code follows project style guidelines
- [ ] Tests added/updated for new functionality
- [ ] Documentation updated
- [ ] No breaking changes (or documented if intentional)
- [ ] Error handling is appropriate
- [ ] Logging is sufficient for debugging

## Troubleshooting

### Import Errors

```bash
# Ensure you're in the virtual environment
source .venv/bin/activate

# Reinstall in editable mode
pip install -e .
```

### Test Failures

```bash
# Run with verbose output
pytest -v

# Run specific test
pytest tests/test_server.py::test_get_cml_labs -v

# Show print statements
pytest -s
```

### Docker Build Issues

```bash
# Clean Docker cache
just docker-clean

# Rebuild without cache
docker build --no-cache -t cml-mcp:local .
```
