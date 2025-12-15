# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **E2E Test Script**: Standalone HTTP service validation (`scripts/test_http_e2e.py`)
  - Tests health endpoint, SSE connection, MCP protocol, and tool calls
  - Uses MCP SDK with Streamable HTTP transport
  - Comprehensive documentation with architecture diagram and usage examples

- **Justfile**: New `test-e2e` command for running E2E tests against live service

- **Multi-Server Support (HTTP Mode)**: Per-request CML server configuration
  - New `X-CML-Server-URL` header to specify target CML server per request
  - New `X-CML-Verify-SSL` header for per-request SSL verification
  - Client pool with LRU eviction, TTL expiration, and per-server limits
  - URL validation via allowlist (`CML_ALLOWED_URLS`) and regex pattern (`CML_URL_PATTERN`)
  - Full backward compatibility with STDIO mode

- **New Settings**: Pool configuration environment variables
  - `CML_POOL_MAX_SIZE` - Maximum clients in pool (default: 50)
  - `CML_POOL_TTL_SECONDS` - Idle client TTL (default: 300)
  - `CML_POOL_MAX_PER_SERVER` - Concurrent requests per server (default: 5)
  - `CML_ALLOWED_URLS` - JSON array of permitted server URLs
  - `CML_URL_PATTERN` - Regex pattern for URL validation

- **New Module**: `client_pool.py` for request-scoped client management
  - `CMLClientPool` class with thread-safe async operations
  - `PooledClient` dataclass for client metadata tracking
  - `get_cml_client()` helper for transparent client access
  - ContextVar-based request isolation

- **Test Suite**: Comprehensive tests for multi-server functionality
  - Unit tests for settings, client pool, URL normalization/validation
  - Integration tests for middleware and header parsing
  - E2E tests for complete request flows and error handling
  - 99 tests with 95% coverage on new modules

- **Documentation**: Multi-server implementation guide
  - `implementation-multi-server.md` with full design details
  - Updated `architecture.md` with client pool diagrams
  - Updated `configuration.md` with new settings
  - Updated `transport-modes.md` with HTTP mode enhancements

- **Documentation**: Comprehensive documentation audit and improvements
  - Fixed transport value from `sse` to `http` across all docs (docker.md)
  - Added `X-CML-Verify-SSL` header documentation in transport-modes.md
  - Documented `get_cml_client()` and ContextVar pattern in architecture.md
  - Added Multi-Server capability to index.md feature table
  - Added HTTP mode section and troubleshooting to user-guide.md
  - Updated README.md with multi-server config and all HTTP headers
  - Added pool configuration and URL validation documentation

- **Documentation**: Complete MkDocs-based documentation site
  - New `user-guide.md` for CML end-users with practical examples
  - New `docker.md` for container deployment and production setup
  - Comprehensive `api-reference.md` covering all 39 MCP tools
  - Mermaid diagrams for architecture and auth flows
  - MkDocs Material theme with dark/light mode toggle

- **Docker**: Docker Compose configuration with multiple profiles
  - `http` profile for production HTTP/SSE transport
  - `stdio` profile for interactive single-user mode
  - `dev` profile for development with hot reload
  - `.env.example` template for configuration

- **CI/CD**: GitHub Actions workflows
  - `docker.yml` for multi-platform Docker builds (amd64/arm64)
  - `docs.yml` for automatic GitHub Pages deployment

- **Justfile**: New documentation commands
  - `docs-install` - Install mkdocs dependencies
  - `docs-serve` - Local development server
  - `docs-build` - Build static site
  - `docs-deploy` - Deploy to GitHub Pages
  - `docs-clean` - Remove build artifacts

- **Justfile**: New testing commands
  - `test` - Run pytest test suite
  - `test-cov` - Run tests with coverage report

- **Dependencies**: Added `docs` dependency group
  - mkdocs >= 1.6
  - mkdocs-material >= 9.5
  - mkdocs-mermaid2-plugin >= 1.1
  - pymdown-extensions >= 10.0

### Changed

- **Server**: All 40+ tool functions now use `get_cml_client()` for client access
  - Enables per-request server selection in HTTP mode
  - Maintains backward compatibility for STDIO mode

- **Middleware**: Enhanced HTTP middleware for multi-server support
  - Extracts `X-CML-Server-URL` and `X-CML-Verify-SSL` headers
  - Manages client pool lifecycle (get/release)
  - Sets request-scoped ContextVar for tool access

- **CMLClient**: Added `update_vclient_url()` method for URL updates

- **Documentation**: Rewrote all existing documentation files
  - `index.md` - New home page with feature overview
  - `configuration.md` - Updated with all 8 settings
  - `architecture.md` - Added Mermaid diagrams
  - `transport-modes.md` - Clarified stdio vs HTTP auth
  - `development.md` - Updated with Justfile commands
  - `schemas.md` - Documented Pydantic models

- **Settings**: Improved `settings.py` type safety
  - `cml_mcp_bind` uses `default_factory` for IPvAnyAddress
  - `cml_url` made optional with runtime validation

- **Justfile**: Docker commands now use `-p cml-mcp` for isolation

### Fixed

- IPvAnyAddress default value causing Pydantic validation errors
- Missing runtime validation for required CML_URL setting

## [0.14.3] - 2024-12-14

- Initial tracked version

[Unreleased]: https://github.com/xorrkaz/cml-mcp/compare/v0.14.3...HEAD
[0.14.3]: https://github.com/xorrkaz/cml-mcp/releases/tag/v0.14.3
