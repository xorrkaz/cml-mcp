# AGENTS.md — CML MCP Server

## Project Overview

`cml-mcp` is a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that exposes Cisco Modeling Labs (CML) operations as AI-callable tools. It is written in Python (≥ 3.12) using [FastMCP](https://github.com/jlowin/fastmcp) and the `virl2_client` library. The package is published to PyPI as `cml-mcp` and to Docker Hub as `xorrkaz/cml-mcp`.

## Repository Layout

```
src/cml_mcp/
  __main__.py          # CLI entry point (cml-mcp command)
  server.py            # FastMCP app wiring; registers all tool modules
  cml_client.py        # Async HTTP wrapper around the CML REST API
  settings.py          # Pydantic-settings config (env vars)
  types.py             # Shared response types used across tool modules
  cml/                 # Auto-generated Pydantic schemas from CML (Cisco license)
  tools/               # One module per functional area (see below)
    cache.py           # Thread-safe async session cache for HTTP mode
    dependencies.py    # Shared CML client dependency and elicitation helper
    middleware.py      # HTTP middleware and ACL enforcement
    model_helpers.py   # Lenient Pydantic construction (strips unknown fields, accepts JSON strings)
tests/
  conftest.py          # Fixtures; USE_MOCKS env var switches mock ↔ live mode
  mocks/               # Pre-recorded JSON responses for offline testing
  input_data/          # Sample topology YAML files
acl.yaml.example       # Reference for HTTP-mode ACL configuration
server.json            # MCP server registry metadata
Justfile               # Task runner (test, build, publish, clean, …)
pyproject.toml         # Build config; linters: black (140), isort, flake8
```

## Tool Modules (`src/cml_mcp/tools/`)

Each module exposes a `register_tools(mcp)` function called from `server.py`.

| Module | Tools |
|---|---|
| `labs.py` | get_cml_labs, create_empty_lab, create_full_lab_topology, modify_cml_lab, start/stop/wipe/delete_cml_lab, get_cml_lab_by_title, download_lab_topology, clone_cml_lab |
| `nodes.py` | get_nodes_for_cml_lab, add_node_to_cml_lab, configure_cml_node, start/stop/wipe/delete_cml_node |
| `node_definitions.py` | get_cml_node_definitions, get_node_definition_detail |
| `interfaces.py` | add_interface_to_node, get_interfaces_for_node |
| `links.py` | connect_two_nodes, get_all_links_for_lab, apply_link_conditioning, start/stop_cml_link |
| `annotations.py` | get_annotations_for_cml_lab, add_annotation_to_cml_lab, delete_annotation_from_lab |
| `pcap.py` | start/stop_packet_capture, check_packet_capture_status, get_captured_packet_overview, get_packet_capture_data |
| `users_groups.py` | get_cml_users/groups, create/delete_cml_user/group |
| `system.py` | get_cml_information, get_cml_status, get_cml_statistics, get_cml_licensing_details |
| `cli.py` | send_cli_command (PyATS/Unicon), get_console_log |

## Key Conventions

- **Object arguments** — Tools that accept a Pydantic model also accept a `dict` or a JSON-encoded string. `model_helpers.lenient_construct` strips unknown fields and parses strings before handing the value to the Pydantic schema, so clients that serialize arguments as strings (e.g. AI Canvas) are handled transparently.
- **Destructive tools** — `wipe_*` and `delete_*` tools call `ctx.elicit()` for interactive confirmation. When `elicit` is unsupported (stateless HTTP or older clients) they proceed without a prompt; docstrings carry a `CRITICAL:` notice so LLMs still ask the user.
- **Admin-only tools** — `create_cml_user`, `delete_cml_user`, `create_cml_group`, `delete_cml_group` check `client.is_admin()` at runtime and raise if the caller is not an admin.
- **CLI commands** — `send_cli_command` uses PyATS (via `virl2_client.ClPyats`). `config_command=true` enters configuration mode; omit `configure terminal` / `end`. `label` is the node label, not the UUID. Both `send_cli_command` and `get_console_log` accept an optional `console` integer (default `0`) to select which serial port to use; Docker-based nodes often expose a second console on index `1`.
- **Packet capture data** — `get_packet_capture_data` returns a base64-encoded PCAP binary. Decode and save as `.pcap` for Wireshark/tcpdump.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `CML_URL` | Yes | CML server URL |
| `CML_USERNAME` | Yes | CML login username |
| `CML_PASSWORD` | Yes | CML login password |
| `CML_VERIFY_SSL` | No | Set `false` for self-signed certs |
| `CML_MCP_TRANSPORT` | No | `http` for HTTP mode (default: `stdio`) |
| `CML_SESSION_TTL` | No | Idle TTL in seconds for cached HTTP sessions (default: `3600`) |
| `PYATS_USERNAME` | No | Device login username |
| `PYATS_PASSWORD` | No | Device login password |
| `PYATS_AUTH_PASS` | No | Device enable password |

## Transport Modes

- **stdio** (default) — run via `uvx cml-mcp` or `uvx cml-mcp[pyats]`
- **HTTP** — set `CML_MCP_TRANSPORT=http` and run `cml-mcp`; optionally enable ACL via `CML_MCP_ACL_FILE=/path/to/acl.yaml`

### ACL File (HTTP mode only)

`acl.yaml` lists users with optional `enabled_tools` or `disabled_tools` lists. Users not listed are denied by default when `default_enabled: false`.

## Development Workflow

This project uses [`just`](https://github.com/casey/just) as its task runner. **Always prefer `just` recipes over invoking `uv`, `pytest`, `black`, etc. directly** — recipes wrap commands in `uv run` and apply project-standard arguments. List recipes with `just` (no args) or `just --list`.

| Recipe | Purpose |
|---|---|
| `just dev-install` | Sync the venv with all extras + dev deps (`uv sync --all-extras`) |
| `just install` | Sync prod-only deps (`uv sync --all-extras --no-dev`) |
| `just update` | Upgrade all dependencies |
| `just test [args]` | Run offline test suite with mocks (default `USE_MOCKS=true`). Pass pytest args, e.g. `just test "-x -k packet"` |
| `just test-live [args]` | Run tests against a real CML server (`USE_MOCKS=false`) |
| `just check` | Run all lint/style checks: `black --check`, `isort --check-only`, `flake8` over `src/` + `tests/` |
| `just build` | Build wheel + multi-arch Docker image |
| `just publish` | Publish to PyPI, MCP registry, and Docker Hub |
| `just clean` / `just fresh` | Remove caches/venv (prompts for confirmation) |

**Before finishing any code change, run `just check` and `just test`.** Both must be green.

If `just check` reports formatting drift, fix it with:
```sh
uv run black src/ tests/
uv run isort src/ tests/
```

Line length is 140. Auto-generated schemas under `src/cml_mcp/cml/` are excluded from formatting and lint.

## Testing

Tests live in `tests/test_cml_mcp.py`; mock JSON fixtures are in `tests/mocks/`. The `USE_MOCKS` env var (default `true`) toggles between mock and live mode — `live_only` / `mock_only` markers in `conftest.py` skip tests that don't apply to the current mode. Live mode requires CML 2.9+ and creates/deletes real resources.

When adding a new tool that calls a new CML REST endpoint, capture a sample JSON response into `tests/mocks/<tool_name>.json` so the offline suite can exercise it. See [tests/MOCK_FRAMEWORK.md](tests/MOCK_FRAMEWORK.md) for the mocking pattern.

## Tool Authoring Conventions

When adding a new `@mcp.tool` to a module under `src/cml_mcp/tools/`:

1. **Get the client via the dependency helper:** `client = get_cml_client_dep()` (do not import settings or instantiate `CMLClient` directly inside a tool).
2. **Annotate destructive/read-only behavior** in the `annotations={...}` dict on `@mcp.tool` (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `title`).
3. **Accept Pydantic models leniently** — declare the parameter as `Model | dict | str` and convert with `lenient_construct(Model, value)` from `tools/model_helpers.py`. This keeps clients that JSON-encode arguments working.
4. **Wrap the body in `try/except`** — catch `httpx.HTTPStatusError` first and re-raise as `ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")`, then a generic `Exception` handler that logs with `logger.exception(...)` and re-raises as `ToolError(e)`.
5. **For destructive tools**, call `await elicit_confirmation(ctx, "...")` (from `tools/dependencies.py`) and put a `CRITICAL:` line in the docstring so LLMs ask the user even when `elicit` is unavailable.
6. **For admin-only tools**, gate with `if not await client.is_admin(): raise ValueError(...)`.
7. **Docstring format** (see existing tools for examples) — a one-line action summary, a few terse fact lines (required/optional fields, return shape, constraints), and an `Examples:` block with 2–3 sample user prompts to aid LLM tool selection on smaller models.

Register the tool by adding (or relying on) the module's `register_tools(mcp)` call in `src/cml_mcp/server.py`.

## Dependencies

Core: `httpx`, `fastmcp>=3.1.1,<4`, `fastapi`, `pydantic_strict_partial`, `typer`, `virl2_client`  
Optional: `pyats`, `genie` (install as `cml-mcp[pyats]`)
