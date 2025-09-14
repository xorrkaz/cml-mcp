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

# Update dependencies
[group('lifecycle')]
update:
    uv sync --upgrade

# Ensure project virtualenv is up to date
[group('lifecycle')]
install:
    uv sync

[group('lifecycle')]
publish: build
    @echo -n PyPi Token: ; \
    read -s token ; \
    echo ; \
    echo "Publishing package to PyPi..." ; \
    uv publish --token "$token"
    mcp-publisher login github
    mcp-publisher publish

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
