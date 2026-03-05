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
| `nodes.py` | get_nodes_for_cml_lab, add_node_to_cml_lab, configure_cml_node, start/stop/wipe/delete_cml_node, get_console_log, send_cli_command |
| `node_definitions.py` | get_cml_node_definitions, get_node_definition_detail |
| `interfaces.py` | add_interface_to_node, get_interfaces_for_node |
| `links.py` | connect_two_nodes, get_all_links_for_lab, apply_link_conditioning, start/stop_cml_link |
| `annotations.py` | get_annotations_for_cml_lab, add_annotation_to_cml_lab, delete_annotation_from_lab |
| `pcap.py` | start/stop_packet_capture, check_packet_capture_status, get_captured_packet_overview, get_packet_capture_data |
| `users_groups.py` | get_cml_users/groups, create/delete_cml_user/group |
| `system.py` | get_cml_information, get_cml_status, get_cml_statistics, get_cml_licensing_details |
| `cli.py` | send_cli_command (PyATS/Unicon), get_console_log |

## Key Conventions

- **Object arguments** — Tools that accept a Pydantic model also accept a `dict`. The type annotation (`SomeModel | dict`) is authoritative; never pass a JSON-encoded string.
- **Destructive tools** — `wipe_*` and `delete_*` tools call `ctx.elicit()` for interactive confirmation. When `elicit` is unsupported (stateless HTTP or older clients) they proceed without a prompt; docstrings carry a `CRITICAL:` notice so LLMs still ask the user.
- **Admin-only tools** — `create_cml_user`, `delete_cml_user`, `create_cml_group`, `delete_cml_group` check `client.is_admin()` at runtime and raise if the caller is not an admin.
- **CLI commands** — `send_cli_command` uses PyATS (via `virl2_client.ClPyats`) or Unicon (`termws` binary). `config_command=true` enters configuration mode; omit `configure terminal` / `end`. `label` is the node label, not the UUID.
- **Packet capture data** — `get_packet_capture_data` returns a base64-encoded PCAP binary. Decode and save as `.pcap` for Wireshark/tcpdump.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `CML_URL` | Yes | CML server URL |
| `CML_USERNAME` | Yes | CML login username |
| `CML_PASSWORD` | Yes | CML login password |
| `CML_VERIFY_SSL` | No | Set `false` for self-signed certs |
| `PYATS_USERNAME` | No | Device login username |
| `PYATS_PASSWORD` | No | Device login password |
| `PYATS_AUTH_PASS` | No | Device enable password |

## Transport Modes

- **stdio** (default) — run via `uvx cml-mcp` or `uvx cml-mcp[pyats]`
- **HTTP** — run `cml-mcp --transport http`; optionally enable ACL via `--acl-file acl.yaml`

### ACL File (HTTP mode only)

`acl.yaml` lists users with optional `enabled_tools` or `disabled_tools` lists. Users not listed are denied by default when `default_enabled: false`.

## Development Workflow

```sh
uv sync --all-extras      # install all deps including dev + pyats
just test                 # offline tests (USE_MOCKS=true, no CML needed)
just test-live            # live tests against a real CML server
just build                # build wheel + Docker multi-arch image
just publish              # publish to PyPI, MCP registry, and Docker Hub
```

Linting must pass before committing:
```sh
black src/ tests/
isort src/ tests/
flake8 src/ tests/
```

Line length is 140. Auto-generated schemas under `src/cml_mcp/cml/` are excluded from formatting.

## Testing

Tests live in `tests/test_cml_mcp.py`. Mock JSON fixtures are in `tests/mocks/`. Set `USE_MOCKS=false` to run against a live CML server (creates and deletes real resources). Requires CML 2.9+.

## Dependencies

Core: `httpx`, `fastmcp>=2.13.1,<3.0.0`, `fastapi`, `pydantic_strict_partial`, `typer`, `virl2_client`  
Optional: `pyats`, `genie` (install as `cml-mcp[pyats]`)
