# Build stage
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE CISCO_LICENSE.md ./
COPY src/ ./src/
RUN uv sync --all-extras --no-dev --locked

# Runtime stage
FROM python:3.13-slim-bookworm

# Set Python unbuffered mode
ENV PYTHONUNBUFFERED=1

ENV CML_URL=https://cml.host.internal
ENV CML_MCP_TRANSPORT=stdio
ENV DEBUG=false
# This should not need to change.  Just bind mount it if needed.
ENV CML_MCP_ACL_FILE=/app/acl.yaml

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    && rm -rf /var/lib/apt/lists/* && apt-get clean

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY src/ ./src/
COPY entrypoint.sh ./
RUN chmod +x /app/entrypoint.sh

ENV PATH="/app/.venv/bin:$PATH"
ENTRYPOINT ["/app/entrypoint.sh"]
