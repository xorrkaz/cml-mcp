#!/usr/bin/env bash
set -e

# Environment variables with defaults
CML_URL=${CML_URL:-https://cml.host.internal}
CML_MCP_TRANSPORT=${CML_MCP_TRANSPORT:-stdio}
CML_MCP_BIND=${CML_MCP_BIND:-0.0.0.0}
CML_MCP_PORT=${CML_MCP_PORT:-9000}
DEBUG=${DEBUG:-false}

# Export for Python to pick up
export CML_URL
export CML_MCP_TRANSPORT
export CML_MCP_BIND
export CML_MCP_PORT
export DEBUG

if [ "$CML_MCP_TRANSPORT" = "stdio" ]; then
  # stdio mode requires credentials in environment
  if [ -z "$CML_USERNAME" ] || [ -z "$CML_PASSWORD" ]; then
    echo "ERROR: CML_USERNAME and CML_PASSWORD must be set for stdio transport."
    echo "       In HTTP mode, credentials are provided via X-Authorization header."
    exit 1
  fi
  echo "Starting CML-MCP in stdio mode..."
  exec uv run cml-mcp
else
  # HTTP mode - credentials provided per-request via headers
  echo "Starting CML-MCP HTTP server on ${CML_MCP_BIND}:${CML_MCP_PORT}..."
  exec $(realpath .)/.venv/bin/uvicorn cml_mcp.server:app \
    --host "${CML_MCP_BIND}" \
    --port "${CML_MCP_PORT}" \
    --workers 4 \
    --access-log
fi
