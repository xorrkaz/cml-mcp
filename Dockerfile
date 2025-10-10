FROM ghcr.io/astral-sh/uv:debian

# Set Python unbuffered mode
ENV PYTHONUNBUFFERED=1

COPY uv.lock /app/uv.lock
COPY pyproject.toml /app/pyproject.toml
COPY README.md /app/README.md
COPY src /app/src
WORKDIR /app
RUN uv sync --all-extras --locked
RUN uv build

CMD ["uv", "run", "cml-mcp"]