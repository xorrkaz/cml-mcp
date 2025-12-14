# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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

- **Dependencies**: Added `docs` dependency group
  - mkdocs >= 1.6
  - mkdocs-material >= 9.5
  - mkdocs-mermaid2-plugin >= 1.1
  - pymdown-extensions >= 10.0

### Changed

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
