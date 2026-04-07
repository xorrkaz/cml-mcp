# CML Fork Maintenance

This repository (`tmikuska/cml-mcp`) is a fork of the upstream open-source
MCP server (`xorrkaz/cml-mcp`). It contains CML-internal additions that are
not suitable for the public repo.

## Remotes

| Name       | URL                                    | Purpose                      |
| ---------- | -------------------------------------- | ---------------------------- |
| `origin`   | `https://github.com/xorrkaz/cml-mcp`  | Upstream open-source repo    |
| `tmikuska` | `git@github.com:tmikuska/cml-mcp.git` | CML fork (our working repo)  |

## Branch layout

| Branch             | Base            | Purpose                                                |
| ------------------ | --------------- | ------------------------------------------------------ |
| `origin/main`      | —               | Upstream: bundled schemas, standalone users             |
| `cleanup-origin`   | `origin/main`   | PR branch → `origin/main`; includes 2.9 compat patches |
| `tmikuska/main`    | `origin/main`   | CML release: import hook, internal additions, 2.10+    |
| `dev`              | `cleanup-origin` | Working branch → `tmikuska/main`                       |

Once `cleanup-origin` is merged into `origin/main`, `dev` merges into
`tmikuska/main`, which is then rebased from `origin/main`.

## What lives where

### `origin/main` (upstream, standalone)

- Bundled schema copies under `src/cml_mcp/cml/`
- Old version compatibility patches (currently CML 2.9):
  - Schema relaxations in `system.py`, `users.py`, `groups.py`, `links.py`
  - `field_validator` for `opt_in` boolean coercion
  - `exclude_defaults=True` in `tools/labs.py` and `tools/users_groups.py`

### `tmikuska/main` (CML internal, 2.10+ only)

Everything from `origin/main` **except** old version patches, **plus**:

- **Import hook** in `__init__.py` (`_CMLSchemaFinder`) — redirects
  `cml_mcp.cml.*` imports to the real `simple_common` / `simple_webserver`
  packages at runtime. No bundled schema copies on this branch.
- **`unicon_cli.py`** — CLI command execution via the internal `termws` binary
  and Unicon, used when PyATS testbed loader is unavailable.
- **`cli.py` unicon fallback** — logic to detect `TERMWS_BINARY` and fall back
  to `unicon_send_cli_command_sync` when `PyatsTFLoader` is not available.
- **`cml_mcp_remote_server_url`** in `settings.py` — setting for CML
  integration tests that connect to a running MCP server instance.
- **Remote test fixture** in `conftest.py` — `custom_httpx_client_factory` and
  the conditional `main_mcp_client` override that uses
  `cml_mcp_remote_server_url`.
- **`allow_http=True`** in `cml_client.py` — enables HTTP connections for
  internal CML environments that do not use TLS.
- **`build-cml` Justfile target** — builds the wheel via `pip wheel --no-deps`
  for the CML CI pipeline.

## How the import hook works

On `tmikuska/main` the `src/cml_mcp/cml/` directory does **not** exist.
All schema imports of the form:

```python
from cml_mcp.cml.simple_webserver.schemas.X import Y
```

are intercepted by `_CMLSchemaFinder` (a `sys.meta_path` finder registered in
`__init__.py`) and transparently redirected to:

```python
from simple_webserver.schemas.X import Y
```

This means the MCP server uses the real CML schema packages that are installed
in the environment. No build-time `sed`, `rm`, or schema copying is required.

On `origin/main` (upstream), bundled schema copies under `src/cml_mcp/cml/`
**do** exist and are used by standalone (non-CML) users. When the import hook
detects that the real packages are available, it prefers them; otherwise the
bundled copies serve as a fallback.

## Schema update flow

Schemas originate in the `simple` repo (`webserver/simple_webserver/schemas/`).
When schemas change:

1. Update bundled copies in `origin/main` (or a PR branch like `cleanup-origin`)
2. Re-apply old version compat patches on top of the new schemas
3. Rebase `tmikuska/main` from `origin/main` (import hook picks up changes
   automatically from the installed `simple_webserver` package)
4. Preserve internal additions during rebase

**Open question:** the best workflow for keeping old version patches and
internal additions clean across schema updates is still being evaluated.
Options include `git format-patch`/`git am`, maintaining a patch series, or
structured rebasing. Tests (including pyATS, SSH proxy options) will be added
later to make this safer.

## Fetching upstream changes

```bash
git fetch origin
git log --oneline origin/main..tmikuska/main   # fork-only commits
git log --oneline tmikuska/main..origin/main    # upstream-only commits
```

Review upstream-only commits and rebase `tmikuska/main`:

```bash
git checkout main
git rebase origin/main
```

Resolve any conflicts, then verify:

```bash
just test
```

## CML CI build

The Jenkins pipeline builds the MCP server wheel with:

```bash
pip wheel --no-deps -w packaging/wheelhouse/ packaging/mcp_server/
```

No source patching is needed. The import hook handles schema resolution at
runtime.
