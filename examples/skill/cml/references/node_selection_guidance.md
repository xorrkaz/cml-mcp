# Node selection guidance

Read when choosing which `node_definition` to use for a device role, or when the user names a device family ("a router", "a Nexus switch") rather than an exact definition.

These are **preference defaults**, not overrides of the SKILL.md workflow. Always confirm a definition actually exists on this server with `get_cml_node_definitions` first — installed sets differ. When several installed definitions could satisfy a generic request, follow SKILL.md: present the recommended default below *and* name the other matches, and let the user choose. Use `get_node_definition_detail` for a definition's interface names and counts.

CML users draw node types from three sources: standard reference platforms (shipped, low-resource), supplemental reference platforms (shipped but heavier, not always installed), and community node types (user-added). A definition being "preferred" here only helps if it's in the `get_cml_node_definitions` list.

## Switches

- `ioll2-xe` — **preferred default.** Low resource, high performance, IOS XE switch experience, present on almost all CML instances.
  - `iosvl2` — older IOS switch, largely superseded by `ioll2-xe`; use only when a feature needs the older image.
- NX-OS / Nexus requested → prefer `nxosv9300`; fall back to `nxosv9000`.
- Catalyst 9000 explicitly requested → `cat9000v-q200` or `cat9000v-uadp`. If the user doesn't specify, prefer `cat9000v-q200` (lower resources).
- `unmanaged_switch` — a simple, zero-config layer-2 segment. Handy for fanning out extra host interfaces off a single router interface.

## Routers

- `iol-xe` — **preferred default.** Low resource, high performance, IOS XE router experience, present on almost all CML instances.
  - `iosv` — older IOS router, largely superseded by `iol-xe`; use only when a feature needs the older image.
- Catalyst 8000 / 8000v / Catalyst 8000v requested → `cat8000v` (production-grade IOS XE router).
- IOS XR / XR requested → prefer any `xrd-###` (containerized, low resource); fall back to `iosxrv9000`.

## Servers, desktops, hosts

- `alpine` — good default for a general-purpose network client (Alpine Linux).
- `desktop` — when a graphical desktop (VNC) is needed.
- `server` — even lighter than `alpine` when resource use is a top concern.

## Firewalls

- `asav` — basic firewall, low resources.
- `ftd` / `fmc` — modern but heavy; use only when Firepower, Firewall Management Center, or Threat Defense is explicitly requested, and only if installed.

## Special

- `external_connector` — bridges the topology to an outside network. Most commonly configured in NAT mode to give the simulated network internet access.
