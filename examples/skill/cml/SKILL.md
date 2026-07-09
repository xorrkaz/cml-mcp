---
name: cml
description: Build, edit, and operate Cisco Modeling Labs (CML) virtual network topologies through the CML MCP server. Use whenever the user wants to create or modify a CML lab, add or connect network devices (routers, switches, firewalls, hosts), apply device configurations, start or stop nodes, run CLI commands against simulated devices, or arrange a topology on the canvas — even when phrased loosely as "build me a lab," "spin up a network," "set up an OSPF practice topology," or referencing an existing CML/VIRL lab. Prefer this skill over recalling CML API models from memory; the tool argument conventions are easy to get wrong.
---

# CML

Build and operate CML labs through the CML MCP tools. The guidance below covers the conventions and pitfalls an agent will not infer correctly on its own. General networking knowledge (e.g., what OSPF is, how a switch works) is assumed and not repeated here.

**IDs are opaque — copy them, never reconstruct them.** When a tool returns an identifier (lab, node, interface, or link UUID), pass that exact value to later calls. Never retype an ID from memory or rebuild one from context; a single altered character makes the call fail, and the corrupted value can still look well-formed, so you cannot catch the error by inspecting it. If you are not certain you have the exact value, re-fetch it with the relevant listing tool (`get_nodes_for_cml_lab`, `get_interfaces_for_node`, `get_all_links_for_lab`) rather than guessing. **One exception:** `send_cli_command` identifies its node by `label`, not UUID — see Configuration.

## Default approach: build incrementally, not in one shot

Build a lab by composing small, verifiable steps. **Do not** try to hand-assemble a complete topology object and import it in one call unless the user has explicitly provided a finished model.

Default sequence:

1. `create_empty_lab` (title, optional description/notes) → capture the returned `lab_id`. Lab notes are rendered as Markdown in the CML UI, so record the topology's purpose / high-level description there — it's what a human sees when they open the lab.
2. `get_cml_node_definitions` once, to learn valid `node_definition` values for this server. Do not guess names like `csr1000v`/`iosv` — servers differ in what's installed. If `get_cml_node_definitions` returns an error or an empty list, stop immediately and tell the user: the server returned no node definitions and you cannot proceed without them. Do not guess any `node_definition` value. **If the device type the user asked for isn't in the returned list, stop and tell them** — name the closest available definitions and let them choose. Never silently substitute a different device type. **If `get_cml_node_definitions` returns 2 or more definitions whose names or descriptions could reasonably satisfy the user's request** (i.e., they are the same device family or serve the same functional role — e.g. "a Cisco router" matching `iol-xe`, `iosv`, `csr1000v`, `cat8000v`), list every matching definition by its exact name and ask the user to pick one before proceeding. Do not silently choose the first match. For which definition to recommend as the default among installed options (e.g. `iol-xe` for routers, `ioll2-xe` for switches), see `references/node_selection_guidance.md`.
3. `add_node_to_cml_lab` per device. Set `label`, `node_definition`, and `x`/`y` (see Layout). Each add auto-creates that definition's default interfaces.
4. Connect nodes (see Connecting nodes — this is the step most often done wrong).
5. Apply configuration (see Configuration).
6. Start nodes when the user wants the lab running. To start an entire lab, use `start_cml_lab(lab_id)`. To start nodes in a specific order (e.g., core infrastructure before edge devices), call `start_cml_node(lab_id, node_id)` sequentially, using `wait_for_convergence=true` on each node before starting the next when a later node depends on an earlier one being reachable. See `references/operations.md` for full lifecycle details.

**Why incremental beats `create_full_lab_topology`:** the full-import tool requires a complete, schema-valid Topology object — exact `version`, every node `id`, every interface `id`, and links referencing those interface IDs by hand. A single mismatch fails the whole import with little to localize the error. The incremental tools validate and return real UUIDs at each step, so failures are isolated and self-correcting.

**Escape hatch:** use `create_full_lab_topology` only when (a) the user provides a complete, schema-valid topology object (e.g. an exported/serialized model, or the equivalent complete `lab`/`nodes`/`links` object) **or** (b) the user explicitly demands a single atomic import. In both cases, load `references/topology-schema.md` before constructing or validating the topology object. A detailed request _described in prose_ ("three routers in a triangle, each running OSPF") is **not** a reason to one-shot it; build those incrementally too.

## Working with existing labs

If the user references an existing lab by name or description, call `get_cml_labs` (or `get_cml_lab_by_title`) to retrieve its `lab_id` before any modification. Never create a new lab when the user intends to extend an existing one. Once you have the `lab_id`, resume at whatever step of the default sequence is appropriate (e.g., step 3 to add nodes, step 4 to connect them).

## Connecting nodes (prescriptive — follow exactly)

`connect_two_nodes` takes **interface UUIDs**, not node UUIDs. You cannot connect two nodes from their node IDs alone.

For each link:

1. `get_interfaces_for_node(lab_id, node_id)` for both endpoints.
2. Pick a free interface on each. **Free means `is_connected == false` on the interface object returned by `get_interfaces_for_node`** — never just take the first interface in the list. Also skip loopbacks (e.g. `Loopback0`) and any management-only interface; pick a physical data interface (e.g. `Ethernet0/0`, `GigabitEthernet0/1`).
3. `connect_two_nodes(lab_id, src_int=<iface UUID>, dst_int=<iface UUID>)`.
4. If every physical interface on a node is already connected, `add_interface_to_node` first, then re-fetch.

If `connect_two_nodes` fails, re-fetch interfaces on both nodes (the one you picked may have just been linked), choose genuinely free ones, and retry once. If it fails again, stop and report to the user: state which two nodes you were trying to connect, the interface UUIDs you selected, the exact error returned by the tool, and the current interface availability on both nodes (from the re-fetched list). Do not attempt further retries.

After connecting, optionally `get_all_links_for_lab` to confirm the topology matches intent before configuring or starting.

## Layout: arrange for a human who will open the canvas

Unless the user specifies coordinates, place nodes so a person opening the lab in the CML UI sees a readable diagram they can manipulate — not an overlapping pile. Set `x`/`y` on every node at creation time (range −15000..15000; keeping things near the origin is fine).

The goal, not rigid rules: legible, conventional, minimal crossings. In practice that means:

- Reflect network hierarchy spatially: core/spine devices toward the top or center, distribution in the middle, access/edge and end hosts toward the periphery.
- Give nodes real breathing room — keep at least 150–200 units between any two nodes regardless of whether they are linked, as a universal minimum so icons and labels never overlap. For nodes on the same row or column, use at least 200 units of separation.
- Align peers on a shared row/column (e.g. two core routers at the same `y`) and keep the layout roughly symmetric.
- Route to minimize link crossings; if two valid placements exist, prefer the one with fewer crossings.

For labs with distinct functional zones (Core, DMZ, Branch, etc.), group them visually with annotations so the human can read structure at a glance. `smart_annotations` (tag-based, auto-enclosing) are the lightest way to box and label a group; plain `rectangle` + `text` annotations work when you need manual placement. See `references/annotations-and-layout.md` for coordinate recipes and annotation arguments.

## Configuration: match the method to node state

Pick the tool by scenario; each row is independent:

| Scenario | Tool | Node state required | Node identity arg | `config_command` flag |
|---|---|---|---|---|
| Initial/startup config | `configure_cml_node` | CREATED | UUID (`node_id`) | N/A |
| Live incremental config | `send_cli_command` | BOOTED | `label` | `true` |
| Live exec/show commands | `send_cli_command` | BOOTED | `label` | `false` (default) |

Notes: `configure_cml_node`'s `config` arg is a plain string of CLI lines. With `send_cli_command` and `config_command=true`, send config lines _without_ `configure terminal`/`end` — the tool handles mode entry.

When the user just wants a working baseline, prefer seeding startup configs on CREATED nodes, then start the lab — rather than booting everything and configuring live.

**Generating the baseline:** `scripts/base_config.py` emits a minimal, valid startup config for common node types (`iol-xe`, `ioll2-xe`, and the Alpine-based `alpine`/`server`/`desktop`) — setting the hostname, a `cisco`/`cisco` admin user, and `example.com` domain. Run `uv run scripts/base_config.py --node-type <type> --hostname <name> --interface-count <n>` and feed the output to `configure_cml_node`, then layer task-specific config on top. It matters most for `iol-xe`: IOS XE drops into the interactive initial-configuration dialog on first boot unless every ethernet interface already has some config present, and the script pre-seeds those interface stanzas (grouped in modules of 4) to prevent it. Alpine-based nodes get a shell script sourced at boot, not IOS CLI — configure their IP addresses with the Linux `ip` command.

**Changing config after a node has booted:** `configure_cml_node` won't work on a running node — it needs CREATED state. Two options: for incremental changes to a live device, use `send_cli_command` (this is the usual path — don't wipe just to tweak config). To replace the _startup_ config wholesale, the node must return to CREATED, which means wiping it — a destructive step: confirm with the user, then `stop_cml_node` → `wipe_cml_node` → `configure_cml_node` → `start_cml_node`.

## Verifying and troubleshooting

- `get_nodes_for_cml_lab` / `get_all_links_for_lab` to confirm structure and read node state.
- After starting a node, `get_console_log(lab_id, node_id)` to watch boot progress; pass `console=1` for the second serial port on multi-console nodes (some container nodes).
- `start_cml_node(..., wait_for_convergence=true)` when a later step depends on the node being stable.

## Destructive operations — confirm first

`wipe_cml_node`, `wipe_cml_lab`, `delete_cml_node`, and `delete_cml_lab` are irreversible. Always state exactly what will be destroyed and get an explicit "yes" before calling. Never wipe/delete as an implicit cleanup step.

## Gotchas

- `connect_two_nodes` wants **interface UUIDs**, not node UUIDs. Always `get_interfaces_for_node` first.
- Applying config has two traps that differ by tool — node **state** (`configure_cml_node` needs CREATED, `send_cli_command` needs BOOTED) and node **identity** (`send_cli_command` takes the `label`; nearly everything else takes the UUID). See **Configuration** for the full rules.
- Valid `node_definition` values are server-specific. Call `get_cml_node_definitions` (and `get_node_definition_detail` for interface counts/defaults) instead of assuming a device exists.
- `add_node_to_cml_lab` auto-creates default interfaces; only `add_interface_to_node` when you've exhausted them.
- Node coordinates and most resources are optional, but **set `x`/`y` anyway** — unplaced nodes stack at the origin and produce an unreadable canvas.

## Reference files (load on demand)

- `references/node_selection_guidance.md` — which `node_definition` to prefer for a given role (routers, switches, hosts, firewalls, special nodes) and how to map loose requests ("a Nexus switch") to installed definitions. Read when picking node types or when the user names a device family rather than an exact definition.
- `references/topology-schema.md` — the full `create_full_lab_topology` object shape. Read this only when calling `create_full_lab_topology` — either because the user supplied an already-structured topology object, or because the user explicitly demanded a single atomic import.
- `references/annotations-and-layout.md` — coordinate recipes for common layouts (hub-spoke, spine-leaf, linear) and the argument shapes for text/shape/smart annotations and link conditioning. Read when laying out a non-trivial topology or adding visual grouping.
- `references/operations.md` — lifecycle (start/stop lab), packet capture on links, link conditioning (latency/loss/jitter), and user/group/permission admin. Read when the task goes beyond building and configuring.

## Helper scripts

- `scripts/base_config.py` — generates a minimal, boot-safe startup config for `iol-xe`, `ioll2-xe`, and Alpine-based (`alpine`/`server`/`desktop`) nodes. Run `uv run scripts/base_config.py --node-type <type> --hostname <name> --interface-count <n>` and pass the output to `configure_cml_node`. See **Configuration** for when to use it.
