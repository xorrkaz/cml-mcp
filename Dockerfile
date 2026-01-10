FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Set Python unbuffered mode
ENV PYTHONUNBUFFERED=1

ENV CML_URL=https://cml.host.internal
ENV CML_MCP_TRANSPORT=stdio
ENV DEBUG=false

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    && rm -rf /var/lib/apt/lists/* && apt-get clean

ADD . /app
WORKDIR /app
RUN uv sync --all-extras --no-dev --locked && \
    uv build

ENTRYPOINT ["/app/entrypoint.sh"]
