FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Set Python unbuffered mode
ENV PYTHONUNBUFFERED=1

ADD . /app
WORKDIR /app
RUN uv sync --all-extras --locked && \
    uv build

CMD ["uv", "run", "cml-mcp"]