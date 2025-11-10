FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Set Python unbuffered mode
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    && rm -rf /var/lib/apt/lists/* && apt-get clean

ADD . /app
WORKDIR /app
RUN uv sync --all-extras --locked && \
    uv build

CMD ["uv", "run", "cml-mcp"]