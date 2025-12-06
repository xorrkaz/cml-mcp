set dotenv-load
set shell := ['bash', '-c']

@_:
    just --list

# Run tests
[group('qa')]
test args='':
    uv run -m pytest {{args}}

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
clean:
    rm -rf .venv .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
    find . -type d -name "__pycache__" -exec rm -r {} +

[group('lifecycle')]
distclean:
    rm -rf dist

# Recreate project virtualenv from nothing
[group('lifecycle')]
fresh: clean install
