# AGENTS.md — CML MCP Server

## Project Overview

`cml-mcp` is a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that exposes Cisco Modeling Labs (CML) operations as AI-callable tools. It is written in Python (≥ 3.12) using [FastMCP](https://github.com/jlowin/fastmcp) and the `virl2_client` library. The package is published to PyPI as `cml-mcp` and to Docker Hub as `xorrkaz/cml-mcp`.

## Compatibility Goal

**This server must work across the widest possible range of MCP clients and tool-calling LLMs** — flagship hosted models (Claude, GPT-4-class, Gemini), AI Canvas, Cursor, Claude Desktop, LM Studio, and local / open-weight models (Gemma, Llama, Qwen, etc.). Optimize the public surface for the lowest-common-denominator client. In particular, **assume the LLM may rely on the per-parameter `inputSchema` more than on the docstring** — small models often parse structured schema cheaply and skim prose. Every design decision (flat primitive args, rich per-parameter constraints, `Literal[...]` over free strings, typed return shapes) traces back to this goal.

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
| `labs.py` | get_cml_labs, create_empty_lab, create_full_lab_topology, modify_cml_lab, set_cml_lab_permissions, start/stop/wipe/delete_cml_lab, get_cml_lab_by_title, download_lab_topology, clone_cml_lab |
| `nodes.py` | get_nodes_for_cml_lab, add_node_to_cml_lab, configure_cml_node, start/stop/wipe/delete_cml_node |
| `node_definitions.py` | get_cml_node_definitions, get_node_definition_detail |
| `interfaces.py` | add_interface_to_node (returns a list — a single slot request may add multiple interfaces), get_interfaces_for_node |
| `links.py` | connect_two_nodes, get_all_links_for_lab, apply_link_conditioning, start/stop_cml_link |
| `annotations.py` | get_annotations_for_cml_lab, add_text_annotation, add_rectangle_annotation, add_ellipse_annotation, add_line_annotation, delete_annotation_from_lab |
| `pcap.py` | start/stop_packet_capture, check_packet_capture_status, get_captured_packet_overview, get_packet_capture_data |
| `users_groups.py` | get_cml_users/groups, create/delete_cml_user/group |
| `system.py` | get_cml_information, get_cml_status, get_cml_statistics, get_cml_licensing_details |
| `cli.py` | send_cli_command (PyATS/Unicon), get_console_log |

## Key Conventions

- **Object arguments** — Most tools use flat primitive parameters (str, int, bool, etc.) for better LLM compatibility, especially with smaller / open-weight models. Only `create_full_lab_topology` still accepts `Model | dict | str` and uses `model_helpers.lenient_construct` to strip unknown fields and parse JSON-encoded strings (helpful for clients like AI Canvas).
- **Destructive tools** — `wipe_*` and `delete_*` tools route confirmation through `elicit_confirmation()` in `tools/dependencies.py`. **Elicitation is currently disabled** (the helper returns `True` unconditionally) because several MCP clients — notably GitHub Copilot — either don't support `ctx.elicit()` cleanly or duplicate the prompt. While disabled, every destructive tool relies entirely on the `CRITICAL:` line in its docstring to push the LLM to ask the user for confirmation. Keep using `await elicit_confirmation(ctx, ...)` in new destructive tools so re-enabling later is a one-line change.
- **Admin-only tools** — `create_cml_user`, `delete_cml_user`, `create_cml_group`, `delete_cml_group` check `client.is_admin()` at runtime and raise if the caller is not an admin.
- **CLI commands** — `send_cli_command` uses PyATS (via `virl2_client.ClPyats`). `config_command=true` enters configuration mode; omit `configure terminal` / `end`. `label` is the node label, not the UUID. Both `send_cli_command` and `get_console_log` accept an optional `console` integer (default `0`) to select which serial port to use; Docker-based nodes often expose a second console on index `1`.
- **Packet capture data** — `get_packet_capture_data` returns a base64-encoded PCAP binary. Decode and save as `.pcap` for Wireshark/tcpdump.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `CML_URL` | Yes | CML server URL |
| `CML_USERNAME` | stdio: yes / HTTP: optional | CML login username. **HTTP mode:** acts as a fallback when the request omits `X-Authorization`. Setting it in HTTP mode lets any unauthenticated client assume these credentials — leave unset unless you specifically want a default identity. |
| `CML_PASSWORD` | stdio: yes / HTTP: optional | CML login password. Same HTTP-mode caveat as `CML_USERNAME`. |
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
3. **Prefer flat primitive parameters** — see [Flat primitive arguments](#flat-primitive-arguments) below. Reserve `Model | dict | str` parameter unions for genuinely deep recursive structures (currently only `create_full_lab_topology`'s `topology`); for those, convert with `lenient_construct(Model, value)` from `tools/model_helpers.py`.
4. **Wrap the body in `try/except`** — catch `httpx.HTTPStatusError` first and re-raise as `ToolError(f"HTTP error {e.response.status_code}: {e.response.text}")`, then a generic `Exception` handler that logs with `logger.exception(...)` and re-raises as `ToolError(e)`.
5. **For destructive tools**, call `await elicit_confirmation(ctx, "...")` (from `tools/dependencies.py`) and put a `CRITICAL:` line in the docstring so LLMs ask the user even when `elicit` is unavailable.
6. **For admin-only tools**, gate with `if not await client.is_admin(): raise ValueError(...)`.
7. **Docstring format** — docstrings are written **exclusively for LLMs**, never humans. Do NOT reference internal repo paths (e.g. `tests/input_data/...`), contributor workflows, or other developer-only context inside a tool docstring; that material belongs in `AGENTS.md` or `DEVELOPMENT.md`. Use a one-line action summary, a few terse fact lines (required/optional fields, return shape, constraints), and an `Examples:` block with 2–3 sample user prompts to aid LLM tool selection on smaller models.
8. **Object return types use `model_dump`** — any tool whose return type is a Pydantic response model (or `list[...]` thereof) MUST construct the model from the raw CML response and immediately call `.model_dump(exclude_unset=True)` (returning a plain dict), while keeping the function's annotated return type as the Pydantic model so MCP clients see a typed schema. This intentional annotation/runtime mismatch exists because FastMCP double-marshals returned Pydantic instances and some auto-generated CML schemas don't round-trip cleanly. Drop in `exclude_none=True` when the model has many `Optional` fields whose `None` carries no signal; reserve `exclude_defaults=True` for cases where defaults are clearly noise. Add a one-line comment at each return site pointing at the **"Object-typed return values"** section of [DEVELOPMENT.md](DEVELOPMENT.md) for the rationale.
9. **Always update markdown docs on every relevant code change** — when a code change affects tool count, tool names, conventions, environment variables, transport modes, or workflow, update both:
   - **Repo-root docs**: `README.md`, `INSTALLATION.md`, `DEVELOPMENT.md`, `AGENTS.md`, `server.json` (as appropriate).
   - **Tests docs**: `tests/README.md`, `tests/QUICK_START.md`, `tests/MOCK_FRAMEWORK.md` (as appropriate).
   Treat docs updates as part of the change, not a follow-up. `just check` does not catch stale docs — review them yourself before committing.

### Flat primitive arguments

Tools that wrap a CML schema model (e.g. `LabRequest`, `NodeCreate`, `UserCreate`, `LinkCreate`) MUST expose every user-meaningful, non-server-managed field of that model as a top-level **primitive** parameter (str, int, float, bool, `list[str]`, `list[dict]` for genuinely-nested small lists). Required schema fields → required tool params; optional → keyword params with `None` defaults.

**Rules:**

- Do NOT use `Model | dict | str` parameter unions for flattened tools. Reserve object-typed parameters only for genuinely deep recursive structures (currently only `create_full_lab_topology`'s `topology`).
- **Carry per-parameter constraints from the source schema into the tool signature** via `Annotated[T, field_from(SourceModel, "field_name")]` (`field_from` lives in `tools/model_helpers.py`). This propagates the source model's `description`, numeric bounds (`ge` / `le`), string constraints (`min_length` / `max_length` / `pattern`), and `examples` into the JSON Schema FastMCP exposes to MCP clients. Tool-calling LLMs — especially small / open-weight models — rely on the per-parameter `inputSchema`, not just the docstring; a bare `int | None` tells them nothing. Where the source schema already defines a reusable type alias (e.g. `NodeLabel`, `Coordinate`, `Ram`, `LabTitle`, `UUID4Type`), prefer importing and using the alias directly — same effect with less boilerplate. For enumerable string fields, prefer `Literal[...]` over a free `str` even if the source schema uses a free string.
- Build the request payload as a plain `dict` inside the tool body, omitting keys whose value is `None`, then `await client.post(..., data=payload)`. Avoid constructing the source Pydantic model when many of its fields default to `None` — strict typing in the auto-generated CML schemas often rejects `None` even when the field has `default=None`. The CML server validates the payload.
- Above each flattened tool, include a comment block listing field coverage, e.g.:
  ```python
  # Source schema: LabRequest (cml/simple_webserver/schemas/labs.py)
  # Exposed: title, description, notes, owner
  # Omitted: associations (use set_cml_lab_permissions instead)
  ```
- For PATCH operations (`modify_*` tools), only include kwargs that are not `None` in the payload to avoid overwriting server-managed fields.

**Example** (note the `Annotated[..., field_from(...)]` reuse):

```python
from typing import Annotated
from cml_mcp.cml.simple_webserver.schemas.pcap import PCAPStart
from cml_mcp.tools.model_helpers import build_payload, field_from

async def start_packet_capture(
    lid: UUID4Type,
    link_id: UUID4Type,
    maxpackets: Annotated[int | None, field_from(PCAPStart, "maxpackets")] = None,
    maxtime:    Annotated[int | None, field_from(PCAPStart, "maxtime")]    = None,
    bpfilter:   Annotated[str | None, field_from(PCAPStart, "bpfilter")]   = None,
    encap:      Annotated[str | None, field_from(PCAPStart, "encap")]      = None,
) -> bool:
    ...
```

**Schema-drift audit checklist** — run when `virl2_client` / regenerated CML schemas change:

- `git diff src/cml_mcp/cml/` — for each changed `*Request` / `*Create` model, find the wrapping tool(s).
- Add new fields as new primitive kwargs (default `None`); deprecate removed fields for one release before removal.
- Update the field-coverage comment.
- Run `just check && just test`.
- `tests/test_schema_drift.py` programmatically checks that each flattened tool's input schema (a) covers the source model's required fields and (b) carries the source field's `description` and numeric/string constraints. Drift in either trips the test.

> **Pydantic upgrade caveat:** `field_from()` in `src/cml_mcp/tools/model_helpers.py` reads the **private** `FieldInfo._attributes_set` attribute. This is the cleanest available API in Pydantic v2.x for the "explicitly-set kwargs only" use case, but a Pydantic minor-version bump may rename or remove it. When bumping `pydantic`, re-read `field_from()` and confirm `tests/test_schema_drift.py::test_constraint_coverage` still passes; if it fails, the constraints have stopped propagating and the helper needs updating.

#### Sample prompt for agents auditing a schema bump

When `virl2_client` is upgraded (or `src/cml_mcp/cml/` is regenerated), run a fresh agent with the following prompt — it forces a complete diff/update cycle and leaves no flattened tool stale:

> Audit this repo for CML schema drift after a `virl2_client` / `src/cml_mcp/cml/` update.
>
> 1. Run `git diff <previous-tag>..HEAD -- src/cml_mcp/cml/` and list every changed Pydantic model (focus on `*Request`, `*Create`, `*Update`, and any model referenced by a flattened tool — see `FLAT_TOOL_SCHEMAS` in `tests/test_schema_drift.py`).
> 2. For each changed model, find the wrapping tool(s) under `src/cml_mcp/tools/` (grep for the model name and the `# Source schema:` comment).
> 3. For each tool:
>    - Compare the model's current fields to the tool's parameter list and the `# Exposed:` / `# Omitted:` comment block.
>    - **Added field** → add a primitive kwarg (default `None` if optional, required otherwise), append it to the dict-payload builder, and update the `# Exposed:` line.
>    - **Removed field** → mark the kwarg deprecated with a `DeprecationWarning` for one release before deletion; remove from the comment block.
>    - **Type or constraint change** (e.g. min/max, enum values) → update the docstring's "Required/Optional" lines and re-run `just test` -- `tests/test_schema_drift.py::test_constraint_coverage` will fail loudly if the propagated `Annotated[..., field_from(...)]` constraints no longer match the source.
> 4. Run `just check && just test`. Both must pass; `tests/test_schema_drift.py` (both `test_schema_coverage` and `test_constraint_coverage`) must remain green.
> 5. Update the tool count in `tests/test_cml_mcp.py::test_list_tools`, `README.md` ("provides N MCP tools"), and the `AGENTS.md` tool table if any tool was added or removed.
> 6. Summarize: list each affected tool, the fields added/removed/changed, and any docstring updates.

Register the tool by adding (or relying on) the module's `register_tools(mcp)` call in `src/cml_mcp/server.py`.

## Dependencies

Core: `httpx`, `fastmcp>=3.1.1,<4`, `fastapi`, `pydantic_strict_partial`, `typer`, `virl2_client`  
Optional: `pyats`, `genie` (install as `cml-mcp[pyats]`)
