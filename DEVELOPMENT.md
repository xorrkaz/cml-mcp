# Development Guide

This guide covers how to set up a development environment, common workflows, and best practices for contributing to the CML MCP server.

> **Looking for design conventions?** [AGENTS.md](AGENTS.md) is the single source of truth for tool authoring patterns (flat primitive arguments, schema-drift audits, error handling, etc.). Read it before adding or modifying any `@mcp.tool`.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Daily Workflow](#daily-workflow)
- [Adding a New Tool](#adding-a-new-tool)
- [Recording Mock Responses](#recording-mock-responses)
- [Bumping `virl2_client` / Regenerating CML Schemas](#bumping-virl2_client--regenerating-cml-schemas)
- [Debugging and Inspecting the Server](#debugging-and-inspecting-the-server)
- [Testing](#testing)
- [Code Style](#code-style)
- [Project Structure](#project-structure)
- [Branching, Commits, and Pull Requests](#branching-commits-and-pull-requests)
- [Publishing and Release](#publishing-and-release)

## Prerequisites

- Python 3.12 or 3.13
- [uv](https://docs.astral.sh/uv/) - Python package/project manager
- [just](https://github.com/casey/just) - Command runner (strongly recommended; every workflow in this guide uses it)
- [direnv](https://direnv.net/) - Environment variable manager (optional)
- A reachable CML 2.9+ server for live testing (optional; mock tests cover the basics)

## Quick Start

1. Fork and clone the repository:

    ```sh
    git clone https://github.com/<your-fork>/cml-mcp.git
    cd cml-mcp
    ```

2. (Optional) If using direnv, allow it to set up your environment:

    ```sh
    direnv allow
    ```

    direnv creates a virtual environment and installs production dependencies on `cd`. You'll still need `just dev-install` for dev tooling (pytest, black, isort, flake8).

3. Otherwise install everything manually:

    ```sh
    just dev-install        # → uv sync --all-extras
    source .venv/bin/activate
    ```

4. Create a `.env` file with your CML server credentials (only needed for live tests / running the server):

    ```sh
    CML_URL=https://your-cml-server.example.com
    CML_USERNAME=your_username
    CML_PASSWORD=your_password
    CML_VERIFY_SSL=false
    DEBUG=true
    # Optional, for CLI command (PyATS) tools
    PYATS_USERNAME=device_username
    PYATS_PASSWORD=device_password
    PYATS_AUTH_PASS=enable_password
    ```

5. Verify your setup:

    ```sh
    just check    # lint
    just test     # mock tests (no CML server needed)
    ```

Both should pass before you make any changes.

## Daily Workflow

The project uses [`just`](https://github.com/casey/just) as its task runner. **Always prefer `just` recipes over invoking `uv`, `pytest`, `black`, etc. directly** — recipes wrap commands in `uv run` and apply project-standard arguments. List recipes with `just` (no args) or `just --list`.

| Recipe | Purpose |
| --- | --- |
| `just dev-install` | Sync the venv with all extras + dev deps |
| `just install` | Sync prod-only deps |
| `just update` | Upgrade all dependencies |
| `just test [args]` | Run the offline test suite (mocks). Pass pytest args, e.g. `just test "-x -k packet"` |
| `just test-live [args]` | Run tests against a real CML server (`USE_MOCKS=false`) |
| `just check` | `black --check`, `isort --check-only`, `flake8` over `src/` and `tests/` |
| `just build` | Build wheel + multi-arch Docker image |
| `just clean` / `just fresh` | Remove caches/venv (prompts for confirmation) |

If `just check` reports formatting drift, fix it with:

```sh
uv run black src/ tests/
uv run isort src/ tests/
```

The line length is **140**. Auto-generated schemas under `src/cml_mcp/cml/` are excluded from formatting and lint.

**Before opening a PR, both `just check` and `just test` must be green.**

## Adding a New Tool

This is the most common contribution. The full conventions live in [AGENTS.md](AGENTS.md#tool-authoring-conventions); the short version:

1. **Pick the right module** under `src/cml_mcp/tools/` (one module per functional area — labs, nodes, pcap, etc.). Add a new module only if the tool genuinely doesn't fit.
2. **Identify the source schema** in `src/cml_mcp/cml/simple_webserver/schemas/` (e.g. `LabRequest`, `NodeCreate`). Read its fields — required vs optional, types, constraints.
3. **Write the tool with flat primitive arguments**, not a nested object. Required schema fields → required tool params; optional → kwargs with `None` defaults. Build the request as a plain `dict` inside the tool body, omitting `None` values:

    ```python
    from typing import Annotated

    from cml_mcp.cml.simple_webserver.schemas.labs import LabRequest
    from cml_mcp.tools.model_helpers import build_payload, field_from

    # Source schema: LabRequest (cml/simple_webserver/schemas/labs.py)
    # Exposed: title, description, notes, owner
    # Omitted: associations (use set_cml_lab_permissions instead)
    @mcp.tool(
        annotations={
            "title": "Create an Empty Lab",
            "readOnlyHint": False,
            "destructiveHint": False,
        },
    )
    async def create_empty_lab(
        title:       Annotated[str | None,       field_from(LabRequest, "title")]       = None,
        description: Annotated[str | None,       field_from(LabRequest, "description")] = None,
        notes:       Annotated[str | None,       field_from(LabRequest, "notes")]       = None,
        owner:       Annotated[UUID4Type | None, field_from(LabRequest, "owner")]       = None,
    ) -> UUID4Type:
        """One-line action summary.

        Required: ...  Optional: ...
        Returns: ...

        Examples:
        - "Create a new empty lab called 'OSPF Practice'"
        - ...
        """
        client = get_cml_client_dep()
        try:
            payload = build_payload(
                title=title,
                description=description,
                notes=notes,
                owner=str(owner) if owner is not None else None,
            )
            resp = await client.post("/labs", data=payload)
            return UUID4Type(resp["id"])
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.exception("Error creating empty lab")
            raise ToolError(e)
    ```

    > **Why `Annotated[T, field_from(Source, "name")]` instead of bare `T`?** FastMCP turns each parameter into a JSON Schema property exposed to the MCP client. A bare `int | None` tells a tool-calling LLM nothing about valid ranges; the source `Field(ge=1, le=86400, description="...")` does. Pulling the `FieldInfo` straight from the source schema propagates `description`, numeric/string constraints, and `examples` into the wire schema with zero hand-copying — and `tests/test_schema_drift.py::test_constraint_coverage` enforces that they stay in sync.

    > **Why dicts and not Pydantic models for the request payload?** The auto-generated CML schemas are strict and frequently reject `None` even for fields that nominally default to `None`. Building a dict and letting the CML server validate avoids brittle re-typing in our tool layer. The exception is `create_full_lab_topology`, which accepts `Topology | dict | str` because the structure is genuinely deeply nested.

4. **Annotate destructive/read-only behavior** in the `@mcp.tool(annotations={...})` block. Use `readOnlyHint`, `destructiveHint`, `idempotentHint`, `title`.
5. **Destructive tools** (`wipe_*`, `delete_*`) must call `await elicit_confirmation(ctx, "...")` and include a `CRITICAL:` line in the docstring.
6. **Admin-only tools** must gate with `if not await client.is_admin(): raise ValueError(...)`.
7. **Register the tool** — if you added a new module, add a `register_tools(mcp)` call in `src/cml_mcp/server.py`. Tools inside an existing module are picked up automatically.
8. **Add a mock fixture** if the tool calls a new CML REST endpoint — see [Recording Mock Responses](#recording-mock-responses).
9. **Add a test** in `tests/test_cml_mcp.py`. Mark it `@pytest.mark.live_only` if it requires a real CML server.
10. **Update the tool count** in `tests/test_cml_mcp.py::test_list_tools`, and the `README.md` ("provides N MCP tools") and `AGENTS.md` tool table if applicable.
11. Run `just check && just test` until both are green.

`tests/test_schema_drift.py` will catch the case where you forget to expose a required field of the source schema — make sure it stays green too.

### Object-typed return values

If a tool's return annotation is a Pydantic response model (e.g. `Lab`, `Node`, `LinkResponse`, `SimplifiedInterfaceResponse`, `PCAPStatusResponse`) or a list of one, the **runtime** return value must be `Model(**raw).model_dump(exclude_unset=True)` (a plain dict), even though the type annotation stays as the Pydantic model.

```python
async def get_nodes_for_cml_lab(lid: UUID4Type) -> list[Node]:
    ...
    # Annotation: list[Node]   Runtime: list[dict]
    return [Node(**n).model_dump(exclude_unset=True) for n in raw_nodes]
```

**Why the mismatch?** FastMCP double-marshals returned Pydantic instances (Pydantic instance → dict → JSON via FastMCP's own serializer), and some auto-generated CML schemas validate fields they cannot faithfully round-trip through that second pass. Constructing the model coerces/validates incoming data; `model_dump` then emits a stable dict that FastMCP serializes verbatim. Keeping the annotation as the Pydantic model still gives MCP clients a rich, typed output schema for tool discovery.

**Dump-flag guidance:**

- `exclude_unset=True` — always; drops fields the server did not set, keeping the payload tight.
- `exclude_none=True` — add when the response model declares many `Optional[...]` fields whose `None` value carries no signal.
- `exclude_defaults=True` — only when defaults are clearly noise (rare; risk: hides a server value that happens to equal the default).

Add a brief one-line comment at the return site pointing back here (`# See DEVELOPMENT.md "Object-typed return values" ...`) so future contributors don't "clean up" the apparent redundancy.

## Recording Mock Responses

Mock tests live under `tests/mocks/`, one JSON file per tool. To record a new one against a live CML server:

1. Set up `.env` with valid `CML_URL`/`CML_USERNAME`/`CML_PASSWORD`.
2. Run the relevant tool against the live server (either via `just test-live -k <name>` or by adding a small ad-hoc script that imports the CML client and dumps the response).
3. Save the prettified JSON response into `tests/mocks/<tool_name>.json`.
4. Re-run `just test` (mock mode) to verify the mock plays back correctly.

See [tests/MOCK_FRAMEWORK.md](tests/MOCK_FRAMEWORK.md) for the full mock dispatch pattern.

## Bumping `virl2_client` / Regenerating CML Schemas

When you upgrade `virl2_client` (or otherwise refresh `src/cml_mcp/cml/`), some Pydantic models may gain, lose, or change fields. Each flattened tool that mirrors one of those models needs a corresponding update.

[AGENTS.md](AGENTS.md#sample-prompt-for-agents-auditing-a-schema-bump) contains a step-by-step prompt you can paste into your agent of choice (or follow manually). The high-level checklist:

1. `git diff <previous-tag>..HEAD -- src/cml_mcp/cml/` — list every changed `*Request` / `*Create` / `*Update` model.
2. Cross-reference each against `FLAT_TOOL_SCHEMAS` in [tests/test_schema_drift.py](tests/test_schema_drift.py) and the `# Source schema:` comments in `src/cml_mcp/tools/`.
3. For each affected tool: add new primitive kwargs for added fields, deprecate kwargs for removed fields (one release before deletion), update docstrings for type/constraint changes, and refresh the `# Exposed:` / `# Omitted:` comment block.
4. Run `just check && just test`. `tests/test_schema_drift.py::test_schema_coverage` must remain green.
5. Update tool counts (`README.md`, `AGENTS.md`, `tests/test_cml_mcp.py::test_list_tools`) if any tool was added or removed.

## Debugging and Inspecting the Server

### Run the server locally

```sh
# stdio transport (what most MCP clients use)
uv run cml-mcp

# HTTP transport (useful for browser-based debugging)
CML_MCP_TRANSPORT=http uv run cml-mcp
```

In HTTP mode the server listens on `http://localhost:8000/mcp/` by default.

### Use the MCP Inspector

The official [MCP Inspector](https://github.com/modelcontextprotocol/inspector) is the easiest way to invoke tools manually and see the JSON Schema each tool exposes — invaluable when debugging argument shape mismatches.

```sh
npx @modelcontextprotocol/inspector uv run cml-mcp
```

### Verbose logging

Set `DEBUG=true` in `.env` (or export it). All tool modules log under the `cml-mcp.tools.*` namespace; `cml_client.py` logs HTTP requests/responses.

### Inspecting the live tool surface from Python

```python
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport
from cml_mcp.server import mcp

async with Client(FastMCPTransport(mcp)) as c:
    for tool in await c.list_tools():
        print(tool.name, tool.inputSchema)
```

This is exactly what `tests/test_schema_drift.py` does and is the fastest way to confirm what an LLM client will see.

## Testing

Tests live in `tests/test_cml_mcp.py` and run in two modes via the `USE_MOCKS` env var (default `true`).

- **Mock mode** (`just test`) — Fast, no CML server, uses pre-recorded JSON in `tests/mocks/`. CI runs this.
- **Live mode** (`just test-live`) — Hits a real CML 2.9+ server using credentials from `.env`. Creates and deletes real labs/nodes/users/groups; safe but slower.

Tests marked `@pytest.mark.live_only` are skipped in mock mode, and `@pytest.mark.mock_only` tests are skipped in live mode (see fixtures in `tests/conftest.py`).

To run a subset:

```sh
just test "-k packet"             # only packet capture tests
just test "-x"                    # stop on first failure
just test "tests/test_schema_drift.py"
```

See [tests/README.md](tests/README.md) and [tests/QUICK_START.md](tests/QUICK_START.md) for more.

## Code Style

- **black** — formatting (line length 140)
- **isort** — import sorting
- **flake8** — linting

All three are configured in [pyproject.toml](pyproject.toml). Auto-generated schemas under `src/cml_mcp/cml/` are excluded.

`just check` runs all three in `--check` mode. To auto-fix formatting:

```sh
uv run black src/ tests/
uv run isort src/ tests/
```

## Project Structure

```text
cml-mcp/
├── src/cml_mcp/
│   ├── server.py                  # FastMCP app; registers all tool modules
│   ├── cml_client.py              # Async HTTP wrapper around the CML REST API
│   ├── settings.py                # Pydantic-settings config (env vars)
│   ├── types.py                   # Shared response types
│   ├── cml/                       # Auto-generated Pydantic schemas (Cisco license; do not hand-edit)
│   └── tools/                     # One module per functional area
│       ├── dependencies.py        # Shared CML client dep + elicitation helper
│       ├── cache.py               # Async session cache for HTTP mode
│       ├── middleware.py          # HTTP middleware + ACL enforcement
│       ├── model_helpers.py       # lenient_construct (only used by create_full_lab_topology)
│       ├── system.py
│       ├── users_groups.py
│       ├── node_definitions.py
│       ├── labs.py
│       ├── nodes.py
│       ├── interfaces.py
│       ├── links.py
│       ├── annotations.py
│       ├── pcap.py
│       └── cli.py
├── tests/
│   ├── conftest.py                # Fixtures; USE_MOCKS toggles mock ↔ live mode
│   ├── test_cml_mcp.py            # Main test suite
│   ├── test_schema_drift.py       # Catches CML schema drift in flattened tools
│   ├── mocks/                     # Pre-recorded JSON responses
│   └── input_data/                # Sample topology YAML
├── AGENTS.md                      # Canonical tool authoring conventions
├── DEVELOPMENT.md                 # This file
├── INSTALLATION.md                # End-user install / configuration
├── README.md                      # Project overview + tool catalog
├── Justfile                       # Task automation
├── pyproject.toml                 # Build config + linter rules
└── Dockerfile
```

### Modular tool architecture

- Each `tools/*.py` module exports a `register_tools(mcp)` function called from `server.py`.
- Tools obtain the CML client through `get_cml_client_dep()` (never instantiate `CMLClient` directly inside a tool).
- The session cache in `cache.py` keeps authenticated `CMLClient` instances warm across HTTP requests, keyed by `username:pwd_hash:cml_url:verify_ssl` with an idle TTL (default 1 hour).
- Middleware in `middleware.py` enforces optional ACLs in HTTP mode (see `acl.yaml.example`).

### Why this layout

- New tools land in the right module by topic.
- `tests/test_schema_drift.py` provides a structural safety net — it catches missing required fields before they hit production.
- `AGENTS.md` is intentionally agent-oriented but doubles as the human conventions doc; keeping a single source of truth avoids drift.

## Branching, Commits, and Pull Requests

1. Branch off `main` with a descriptive name (`feature/add-resource-pools`, `fix/pcap-stop-error`, `chore/bump-virl2-client`).
2. Keep commits focused. Reasonable commit messages explain the *why* — the diff already shows the *what*.
3. Run `just check && just test` before pushing. CI runs both; failing checks block merge.
4. Open a PR against `main`. Reference any related issue. The PR description should call out:
   - Whether the change adds, removes, or modifies any tools (so the tool count and ACL examples can be updated).
   - Whether new mock fixtures were added.
   - Whether any docs (`README.md`, `INSTALLATION.md`, `AGENTS.md`, `DEVELOPMENT.md`) need updating — and that you've updated them.
5. Squash-merge unless there's a good reason to preserve individual commits.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the project's contribution policy.

## Publishing and Release

> **Note:** Maintainer-only.

```sh
# Build package + Docker images
just build

# Publish individually
just publish_pypi
just publish_mcp
just publish_docker

# Or all of the above
just publish
```

**Bump the version in [pyproject.toml](pyproject.toml) and tag the release** before publishing. Update the relevant entries in `README.md` (tool count, what's new) and `AGENTS.md` (tool table) so the published artifacts match.
