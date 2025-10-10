FROM ghcr.io/astral-sh/uv:debian

# Set Python unbuffered mode
ENV PYTHONUNBUFFERED=1

ADD . /app
WORKDIR /app
RUN uv sync --all-extras --locked
RUN uv build

CMD ["uv", "run", "cml-mcp"]