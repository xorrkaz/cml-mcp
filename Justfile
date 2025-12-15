set dotenv-load
set shell := ['bash', '-c']

@_:
    just --list

# Run tests
[group('qa')]
test:
    uv run -m pytest

[group('build')]
build:
    uv build
    docker buildx build --platform linux/amd64,linux/arm64 -t xorrkaz/cml-mcp:latest -t xorrkaz/cml-mcp:$(uv version --short) .

# Update dependencies
[group('lifecycle')]
update:
    uv sync --upgrade --all-extras

# Ensure project virtualenv is up to date
[group('lifecycle')]
install:
    uv sync --all-extras

[group('lifecycle')]
publish_pypi:
    @echo -n PyPi Token: ; \
    read -s token ; \
    echo ; \
    echo "Publishing package to PyPi..." ; \
    uv publish --token "$token"

[group('lifecycle')]
publish_mcp:
    mcp-publisher login github
    mcp-publisher publish

[group('lifecycle')]
publish_docker:
    docker login
    docker buildx build --platform linux/amd64,linux/arm64 -t xorrkaz/cml-mcp:latest -t xorrkaz/cml-mcp:$(uv version --short) --push .

[group('lifecycle')]
publish: build publish_pypi publish_mcp publish_docker

# Remove temporary files
[group('lifecycle')]
[confirm("This will delete .venv, caches, and __pycache__ directories. Continue?")]
clean:
    rm -rf .venv .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
    find . -type d -name "__pycache__" -exec rm -r {} +

[group('lifecycle')]
distclean:
    rm -rf dist

# Recreate project virtualenv from nothing
[group('lifecycle')]
[confirm("This will delete and recreate the entire virtual environment. Continue?")]
fresh: clean install

# --- Docker Compose ---
# All commands use -p cml-mcp to ensure isolation from other stacks

project := "cml-mcp"

# Start HTTP server (default profile)
[group('docker')]
up *args:
    docker compose -p {{project}} --profile http up -d {{args}}

# Stop all services
[group('docker')]
down *args:
    docker compose -p {{project}} --profile http down {{args}}

# View logs (follow mode)
[group('docker')]
logs *args:
    docker compose -p {{project}} logs -f {{args}}

# Rebuild and restart services
[group('docker')]
restart: down
    docker compose -p {{project}} up -d --build

# Run interactive stdio mode
[group('docker')]
stdio:
    docker compose -p {{project}} --profile stdio run --rm cml-mcp-stdio

# Start development mode (mounts local source)
[group('docker')]
dev:
    docker compose -p {{project}} --profile dev up cml-mcp-dev

# Show service status
[group('docker')]
ps:
    docker compose -p {{project}} ps -a

# Build Docker image locally
[group('docker')]
docker-build tag="local":
    docker build -t cml-mcp:{{tag}} .

# Shell into running container
[group('docker')]
shell service="cml-mcp-http":
    docker compose -p {{project}} exec {{service}} /bin/bash

# Show container resource usage
[group('docker')]
stats:
    docker compose -p {{project}} stats --no-stream

# Clean up Docker resources (containers, images, volumes) for THIS project only
[group('docker')]
[confirm("⚠️  This will remove cml-mcp containers, local images, and volumes. Continue?")]
docker-clean:
    docker compose -p {{project}} down -v --rmi local

# Remove ALL unused Docker resources system-wide (affects other projects!)
[group('docker')]
[confirm("🚨 WARNING: This will prune ALL unused Docker images, containers, networks, and volumes SYSTEM-WIDE.\nThis may affect OTHER projects not currently running. Are you sure?")]
docker-prune:
    docker system prune -af --volumes

# --- Documentation (MkDocs) ---

# Install documentation dependencies
[group('docs')]
docs-install:
    uv sync --group docs

# Serve documentation locally with hot reload
[group('docs')]
docs-serve port="8000":
    uv run --group docs mkdocs serve -a localhost:{{port}}

# Build documentation site
[group('docs')]
docs-build:
    uv run --group docs mkdocs build --strict

# Deploy documentation to GitHub Pages
[group('docs')]
docs-deploy:
    uv run --group docs mkdocs gh-deploy --force

# Clean documentation build artifacts
[group('docs')]
docs-clean:
    rm -rf site/
