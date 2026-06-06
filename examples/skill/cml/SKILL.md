---
name: cml-topology-builder
description: Build, edit, and operate Cisco Modeling Labs (CML) virtual network topologies through the CML MCP server. Use whenever the user wants to create or modify a CML lab, add or connect network devices (routers, switches, firewalls, hosts), apply device configurations, start or stop nodes, run CLI commands against simulated devices, or arrange a topology on the canvas — even when phrased loosely as "build me a lab," "spin up a network," "set up an OSPF practice topology," or referencing an existing CML/VIRL lab. Prefer this skill over recalling CML API models from memory; the tool argument conventions are easy to get wrong.
---

# CML Topology Builder

Build and operate CML labs through the CML MCP tools. The guidance below covers the conventions and pitfalls an agent will not infer correctly on its own. General networking knowledge (e.g., what OSPF is, how a switch works) is assumed and not repeated here.

When an MCP tool returns any identifier (UUID, node ID, interface ID, etc.), you MUST use that exact value in all subsequent tool calls. These values are opaque — they have no structure you can infer or reconstruct from context.

Rules:
- Never retype an ID from memory
- Never guess or reconstruct an ID if you are uncertain
- If you are unsure of an ID, call the appropriate listing or lookup tool to retrieve it again

BAD (reconstructed from memory):
  tool_call(node_id_="6d87b926-26ae-419ca-a8b3-726fe46f1289")  ← character added

GOOD (copied exactly from prior tool result):
  tool_call(node_id_="6d87b926-26ae-419a-a8b3-726fe46f1289")

Violating this will cause tool calls to fail. When in doubt, look it up again. 

## Default approach: build incrementally, never one-shot the full model **unless** a topology file is provided

Build a lab by composing small, verifiable steps. **Do not** try to hand-assemble a complete topology object and import it in one call unless the user has explicitly provided a finished model.

Default sequence:

1. `create_empty_lab` (title, optional description/notes) → capture the returned `lab_id`.
2. `get_cml_node_definitions` once, to learn valid `node_definition` values for this server. Do not guess names like `csr1000v`/`iosv` — servers differ in what's installed.
3. `add_node_to_cml_lab` per device. Set `label`, `node_definition`, and `x`/`y` (see Layout). Each add auto-creates that definition's default interfaces.
4. Wire nodes (see Wiring — this is the step most often done wrong).
5. Apply configuration (see Configuration).
6. Start nodes when the user wants the lab running.

**Why incremental beats `create_full_lab_topology`:** the full-import tool requires a complete, schema-valid Topology object — exact `version`, every node `id`, every interface `id`, and links referencing those interface IDs by hand. A single mismatch fails the whole import with little to localize the error. The incremental tools validate and return real UUIDs at each step, so failures are isolated and self-correcting.

**Escape hatch:** use `create_full_lab_topology` only when the user supplies a complete topology (e.g. an exported model, or a precise spec of every node/link they want created atomically). When you do, load `references/topology-schema.md` first.

## Connecting nodes (prescriptive — follow exactly)

`connect_two_nodes` takes **interface UUIDs**, not node UUIDs. You cannot connect two nodes from their node IDs alone.

For each link:

1. `get_interfaces_for_node(lab_id, node_id)` for both endpoints.
2. Pick a free interface on each (default interfaces exist after `add_node_to_cml_lab`).
3. `connect_two_nodes(lab_id, src_int=<iface UUID>, dst_int=<iface UUID>)`.
4. If a node has no free interface left, `add_interface_to_node` first, then re-fetch.

After wiring, optionally `get_all_links_for_lab` to confirm the topology matches intent before configuring or starting.

## Layout: arrange for a human who will open the canvas

Unless the user specifies coordinates, place nodes so a person opening the lab in the CML UI sees a readable diagram they can manipulate — not an overlapping pile. Set `x`/`y` on every node at creation time (range −15000..15000; keeping things near the origin is fine).

The goal, not rigid rules: legible, conventional, minimal crossings. In practice that means:

- Reflect network hierarchy spatially: core/spine devices toward the top or center, distribution in the middle, access/edge and end hosts toward the periphery.
- Give neighbors real breathing room — roughly 150–200 units between adjacent devices — so labels and links don't overlap.
- Align peers on a shared row/column (e.g. two core routers at the same `y`) and keep the layout roughly symmetric.
- Route to minimize link crossings; if two valid placements exist, prefer the one with fewer crossings.

For labs with distinct functional zones (Core, DMZ, Branch, etc.), group them visually with annotations so the human can read structure at a glance. `smart_annotations` (tag-based, auto-enclosing) are the lightest way to box and label a group; plain `rectangle` + `text` annotations work when you need manual placement. See `references/annotations-and-layout.md` for coordinate recipes and annotation arguments.

## Configuration: match the method to node state

Two ways to get config onto a device — they have different state requirements, and mixing them up is a common failure:

- **Startup config (preferred for initial setup):** `configure_cml_node(lab_id, node_id, config)`. Requires the node in **CREATED** state (freshly added or freshly wiped). Faster than booting, and survives wipes-to-config. `config` is a plain string of CLI lines. Use this to seed hostnames, interfaces, and protocols before first boot.
- **Live CLI (for a running device):** `send_cli_command`. Identifies the node by **`label`, not UUID** (unlike every other tool here), and requires the node **BOOTED**. With `config_command=true`, send config lines *without* `configure terminal`/`end` — the tool handles mode entry. With `config_command=false` (default) it runs exec commands like `show ip route`.

When the user just wants a working baseline, prefer seeding startup configs on CREATED nodes, then start the lab — rather than booting everything and configuring live.

## Verifying and troubleshooting

- `get_nodes_for_cml_lab` / `get_all_links_for_lab` to confirm structure and read node state.
- After starting a node, `get_console_log(lab_id, node_id)` to watch boot progress; pass `console=1` for the second serial port on multi-console nodes (some container nodes).
- `start_cml_node(..., wait_for_convergence=true)` when a later step depends on the node being stable.

## Destructive operations — confirm first

`wipe_cml_node`, `wipe_cml_lab`, `delete_cml_node`, and `delete_cml_lab` are irreversible. Always state exactly what will be destroyed and get an explicit "yes" before calling. Never wipe/delete as an implicit cleanup step.

## Gotchas

- `connect_two_nodes` wants **interface UUIDs**, not node UUIDs. Always `get_interfaces_for_node` first.
- `send_cli_command` identifies the node by **`label`**; nearly every other tool uses the node **UUID**. Don't pass a UUID where a label is expected or vice versa.
- `configure_cml_node` needs the node in **CREATED** state; `send_cli_command` needs **BOOTED**. Check/sequence state before configuring.
- Valid `node_definition` values are server-specific. Call `get_cml_node_definitions` (and `get_node_definition_detail` for interface counts/defaults) instead of assuming a device exists.
- `add_node_to_cml_lab` auto-creates default interfaces; only `add_interface_to_node` when you've exhausted them.
- With `send_cli_command` + `config_command=true`, omit `configure terminal` and `end`.
- Node coordinates and most resources are optional, but **set `x`/`y` anyway** — unplaced nodes stack at the origin and produce an unreadable canvas.

## Reference files (load on demand)

- `references/topology-schema.md` — the full `create_full_lab_topology` object shape. Read this **only** when doing a one-shot bulk import of a complete, user-supplied topology.
- `references/annotations-and-layout.md` — coordinate recipes for common layouts (hub-spoke, spine-leaf, linear) and the argument shapes for text/shape/smart annotations and link conditioning. Read when laying out a non-trivial topology or adding visual grouping.
- `references/operations.md` — lifecycle (start/stop lab), packet capture on links, link conditioning (latency/loss/jitter), and user/group/permission admin. Read when the task goes beyond building and configuring.
