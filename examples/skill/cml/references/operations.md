# Operations: lifecycle, capture, conditioning, admin

Read when the task goes beyond building and configuring a lab.

## Lifecycle

- `start_cml_lab(lab_id)` / `stop_cml_lab(lab_id)` — boot or power off every node in the lab.
- `start_cml_node` / `stop_cml_node` — single node. `start_cml_node(..., wait_for_convergence=true)` blocks until stable; use it when a following step (CLI, capture) needs the node ready.
- `start_cml_link` / `stop_cml_link` — enable/disable a single link. Stopping a link simulates a cable pull, useful for failover testing without deleting topology.
- Sequencing: seed startup configs on CREATED nodes (`configure_cml_node`) *before* starting, so devices come up configured. Only fall back to live `send_cli_command` (BOOTED state, node identified by label) for changes after boot.

## Packet capture

Capture runs on a **link**, by lab + link UUID (get link UUIDs from `get_all_links_for_lab`).

1. `start_packet_capture(lab_id, link_id)` — optionally with a capture filter.
2. `check_packet_capture_status` — confirm it's active.
3. `get_captured_packet_overview` — one-line-per-packet summary (timestamps, src/dst).
4. `get_packet_capture_data` — download the full PCAP.
5. `stop_packet_capture(lab_id, link_id)` when done.

The link should be up and traffic flowing, or the capture will be empty.

## Link conditioning (impairment)

`apply_link_conditioning(lab_id, link_id, ...)` injects realistic network impairment. Fields (all optional, set what you need):

- `bandwidth` (kbps), `latency` (ms), `jitter` (ms), `loss` (%), `corrupt_prob` (%), `duplicate` (%), plus correlation companions (`loss_corr`, `delay_corr`, etc.) and `gap`/`limit`.
- `enabled` must be true for conditioning to take effect.

Use to model WAN links, lossy wireless, or congestion.

## User / group / permission admin (requires admin privileges)

- `create_cml_user(username, password, ...)` / `create_cml_group(name, ...)` — provision accounts and groups. Returns the new UUID.
- `set_cml_lab_permissions(lab_id, ...)` — grant group/user access to a lab.
- `delete_cml_user` / `delete_cml_group` — irreversible; confirm before calling.

Only reach for these when the user explicitly asks about multi-user access or provisioning — they're orthogonal to building topologies.

## Server health (read-only, safe)

`get_cml_information`, `get_cml_status`, `get_cml_statistics`, `get_cml_licensing_details` — version, health, resource usage, and node-count limits. Check `get_cml_statistics` before building a large lab to confirm the server has capacity.
