# Installing the CML Skill

This folder is an [Agent Skill](https://agentskills.io/specification) — a portable, filesystem-based bundle (`SKILL.md` + `references/*.md`) that any [skills-compatible client](https://agentskills.io/clients) can load. It complements the `cml-mcp` server: the server gives the model the *tools* to drive CML, while the skill gives the model the *judgement* — when to build incrementally vs. one-shot a topology, how to lay nodes out for a readable canvas, which config method matches each node state, and other CML-specific conventions an LLM cannot infer.

The skill **does not replace** the MCP server — your client still needs `cml-mcp` configured per [INSTALLATION.md](../../INSTALLATION.md) so the tools the skill talks about actually exist.

> **Note:** the directory containing `SKILL.md` must be named `cml` (matching the `name:` field in its frontmatter). Don't rename it during install.

## Cross-client install (Agent Skills convention)

Most modern skills-compatible clients (including Cursor and VS Code/Copilot) load skills from `.agents/skills/` automatically, so this is the lowest-effort install path:

```sh
# Project-level (skill available only inside a specific repo)
mkdir -p .agents/skills
cp -r /path/to/cml-mcp/examples/skill/cml .agents/skills/

# User-level (skill available in every project)
mkdir -p ~/.agents/skills
cp -r /path/to/cml-mcp/examples/skill/cml ~/.agents/skills/
```

If your client supports `.agents/skills/`, you can stop here. Otherwise (notably Claude Code, Claude Desktop, and any client that only scans its own native path), use the per-client steps below.

## Claude Code

Claude Code scans `.claude/skills/` (project) and `~/.claude/skills/` (user); it does **not** scan `.agents/skills/`. The skill folder name becomes the slash command (`/cml`).

```sh
# Personal — available in every project
mkdir -p ~/.claude/skills
cp -r /path/to/cml-mcp/examples/skill/cml ~/.claude/skills/

# Or project — checked into a specific repo's .claude/skills/
mkdir -p .claude/skills
cp -r /path/to/cml-mcp/examples/skill/cml .claude/skills/
```

Claude Code watches the directory for changes, so the skill activates without a restart. Confirm it's loaded by asking "what skills are available?" or by typing `/cml` directly.

Reference files under `references/` are loaded on demand by the skill itself — Claude Code only reads them when `SKILL.md` instructs it to.

## Claude Desktop / claude.ai

Custom skills are uploaded through the web/desktop UI on Pro, Max, Team, or Enterprise plans (with code execution enabled). Filesystem paths don't apply.

1. Zip the `cml` folder (the zip must contain `SKILL.md` at its root):

    ```sh
    cd examples/skill
    zip -r cml-skill.zip cml
    ```

2. Open **Settings → Capabilities → Skills → Upload skill** and select `cml-skill.zip`.
3. Enable the skill for the conversations / projects where you want it active.

The skill activates automatically when your message matches its description. Custom skills uploaded to claude.ai are per-user — each team member uploads their own copy.

## Cursor

Cursor natively supports the Agent Skills standard and scans both its own and the cross-client paths:

| Scope | Paths Cursor scans |
| --- | --- |
| Project | `.cursor/skills/`, `.agents/skills/` (also `.claude/skills/`, `.codex/skills/` for compatibility) |
| User | `~/.cursor/skills/`, `~/.agents/skills/` (also `~/.claude/skills/`, `~/.codex/skills/`) |

Pick whichever path you prefer:

```sh
# Cursor-native, project-scoped
mkdir -p .cursor/skills
cp -r /path/to/cml-mcp/examples/skill/cml .cursor/skills/
```

To verify it loaded: open **Cursor Settings (Cmd/Ctrl+Shift+J) → Rules** — the `cml` skill should appear under "Agent Decides". You can also invoke it directly by typing `/cml` in Agent chat.

## VS Code + GitHub Copilot

Copilot natively supports Agent Skills as of recent VS Code versions. It scans:

| Scope | Paths VS Code scans |
| --- | --- |
| Project | `.github/skills/`, `.claude/skills/`, `.agents/skills/` |
| User | `~/.copilot/skills/`, `~/.claude/skills/`, `~/.agents/skills/` |

Add the skill to whichever fits:

```sh
# Copilot-native, project-scoped
mkdir -p .github/skills
cp -r /path/to/cml-mcp/examples/skill/cml .github/skills/
```

To verify: open the Chat view, click **Configure Chat (gear icon) → Skills** and confirm `cml` is listed. You can also type `/` in chat to see slash-command discovery, or `/cml` to invoke it directly.

For monorepos, enable `chat.useCustomizationsInParentRepositories` so VS Code finds skills in parent directories. Additional skill folders can be added via the `chat.agentSkillsLocations` setting.

## Other clients

Many other agents implement the spec — Codex, Kiro, OpenCode, Gemini CLI, GitHub Copilot CLI, Junie, Goose, Roo Code, Amp, and others. See the [Client Showcase](https://agentskills.io/clients) for the full list and each client's setup link. Most scan `.agents/skills/` and/or their own `.<client>/skills/` directory; copy the `cml` folder into whichever your client documents.

After installing, always verify both halves of the integration:

1. The model knows the conventions in the skill (ask: "what's the right way to connect two nodes in CML?" — it should mention fetching interface UUIDs first).
2. The model can call the `cml-mcp` tools the skill references (ask: "list my CML labs" — it should call `get_cml_labs`).

If only one half works, the other half isn't installed correctly — the skill content alone can't drive CML, and the MCP server alone won't follow the skill's conventions.
