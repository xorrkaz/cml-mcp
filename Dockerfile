FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Set Python unbuffered mode
ENV PYTHONUNBUFFERED=1

# Default environment variables (can be overridden)
ENV CML_URL=https://cml.example.com
ENV CML_MCP_TRANSPORT=http
ENV CML_MCP_BIND=0.0.0.0
ENV CML_MCP_PORT=9000
ENV CML_VERIFY_SSL=false
ENV DEBUG=false

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    curl \
    && rm -rf /var/lib/apt/lists/* && apt-get clean

ADD . /app
WORKDIR /app
RUN uv sync --all-extras --locked && \
    uv build

# Expose the default HTTP port
EXPOSE 9000

# Health check for HTTP mode
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${CML_MCP_PORT:-9000}/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
