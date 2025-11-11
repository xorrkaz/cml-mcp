#!/usr/bin/env bash
set -e

CML_URL=${CML_URL:-https://cml.host.internal}
CML_MCP_TRANSPORT=${CML_MCP_TRANSPORT:-stdio}

if [ "$CML_MCP_TRANSPORT" = "stdio" ]; then
  if [ -z "$CML_USERNAME" ] || [ -z "$CML_PASSWORD" ]; then
    echo "CML_USERNAME or CML_PASSWORD is not set. Please set them for stdio transport."
    exit 1
  fi
  exec uv run cml-mcp
else
  exec $(realpath .)/.venv/bin/uvicorn cml_mcp.server:app --host ${CML_MCP_BIND:-0.0.0.0} --port ${CML_MCP_PORT:-9000} --workers 4
fi