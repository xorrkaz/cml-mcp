# API Reference

This document provides a complete reference for all 39 MCP tools exposed by the cml-mcp server.

## Tool Annotations

Each tool includes annotations that describe its behavior:

| Annotation | Description |
|------------|-------------|
| `readOnlyHint` | `true` if the tool only reads data |
| `destructiveHint` | `true` if the tool deletes or wipes data |
| `idempotentHint` | `true` if calling multiple times has the same effect |

Tools with `destructiveHint: true` will prompt for user confirmation before executing.

---

## System Information

### get_cml_information

Get information about the CML server including version and build details.

| Property | Value |
|----------|-------|
| **Read-only** | ✅ Yes |
| **Returns** | `SystemInformation` |

---

### get_cml_status

Get the health status of the CML server.

| Property | Value |
|----------|-------|
| **Read-only** | ✅ Yes |
| **Returns** | `SystemHealth` |

---

### get_cml_statistics

Get usage statistics from the CML server.

| Property | Value |
|----------|-------|
| **Read-only** | ✅ Yes |
| **Returns** | `SystemStats` |

---

### get_cml_licensing_details

Get licensing information from the CML server.

| Property | Value |
|----------|-------|
| **Read-only** | ✅ Yes |
| **Returns** | `dict` |

---

## Lab Management

### get_cml_labs

Get the list of labs. Optionally filter by owner username.

| Property | Value |
|----------|-------|
| **Read-only** | ✅ Yes |
| **Returns** | `list[Lab]` |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `user` | `UserName` | No | Filter by owner username |

---

### get_cml_lab_by_title

Find a lab by its title.

| Property | Value |
|----------|-------|
| **Read-only** | ✅ Yes |
| **Returns** | `Lab` |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `title` | `LabTitle` | Yes | Lab title (1-64 characters) |

---

### create_empty_lab

Create a new empty lab topology.

| Property | Value |
|----------|-------|
| **Read-only** | ❌ No |
| **Destructive** | ❌ No |
| **Returns** | `UUID4Type` (lab ID) |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lab` | `LabCreate` | Yes | Lab configuration |

**LabCreate Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | `str` | No | Title (1-64 chars) |
| `owner` | `UUID4Type` | No | Owner user ID |
| `description` | `str` | No | Description (max 4096 chars) |
| `notes` | `str` | No | Notes (max 32768 chars) |
| `associations` | `LabAssociations` | No | Group/user permissions |

---

### create_full_lab_topology

Create a complete lab topology with nodes, links, and annotations.

| Property | Value |
|----------|-------|
| **Read-only** | ❌ No |
| **Destructive** | ❌ No |
| **Returns** | `UUID4Type` (lab ID) |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `topology` | `Topology` | Yes | Complete topology definition |

**Topology Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `lab` | `LabTopology` | Yes | Lab metadata |
| `nodes` | `list[NodeTopology]` | Yes | Node definitions |
| `links` | `list[LinkTopology]` | Yes | Link definitions |
| `annotations` | `list[Annotation]` | No | Visual annotations |
| `smart_annotations` | `list[SmartAnnotationBase]` | No | Smart annotations |

---

### modify_cml_lab

Modify an existing lab's properties.

| Property | Value |
|----------|-------|
| **Read-only** | ❌ No |
| **Idempotent** | ✅ Yes |
| **Returns** | `bool` |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lid` | `UUID4Type` | Yes | Lab ID |
| `lab` | `LabCreate` | Yes | Updated properties |

---

### start_cml_lab

Start all nodes in a lab.

| Property | Value |
|----------|-------|
| **Read-only** | ❌ No |
| **Idempotent** | ✅ Yes |
| **Returns** | `bool` |

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `lid` | `UUID4Type` | Yes | - | Lab ID |
| `wait_for_convergence` | `bool` | No | `False` | Wait for stable state |

---

### stop_cml_lab

Stop all nodes in a lab.

| Property | Value |
|----------|-------|
| **Read-only** | ❌ No |
| **Idempotent** | ✅ Yes |
| **Returns** | `bool` |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lid` | `UUID4Type` | Yes | Lab ID |

---

### wipe_cml_lab

Wipe all node data in a lab. **Requires user confirmation.**

| Property | Value |
|----------|-------|
| **Destructive** | ✅ Yes |
| **Idempotent** | ✅ Yes |
| **Returns** | `bool` |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lid` | `UUID4Type` | Yes | Lab ID |

---

### delete_cml_lab

Delete a lab. Stops and wipes first if needed. **Requires user confirmation.**

| Property | Value |
|----------|-------|
| **Destructive** | ✅ Yes |
| **Returns** | `bool` |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lid` | `UUID4Type` | Yes | Lab ID |

---

## Node Management

### get_cml_node_definitions

Get available node types from the CML server.

| Property | Value |
|----------|-------|
| **Read-only** | ✅ Yes |
| **Returns** | `list[SuperSimplifiedNodeDefinitionResponse]` |

---

### get_node_definition_detail

Get detailed information about a specific node type.

| Property | Value |
|----------|-------|
| **Read-only** | ✅ Yes |
| **Returns** | `NodeDefinition` |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `did` | `DefinitionID` | Yes | Node definition ID (e.g., `iosv`, `csr1000v`) |

---

### get_nodes_for_cml_lab

Get all nodes in a lab.

| Property | Value |
|----------|-------|
| **Read-only** | ✅ Yes |
| **Returns** | `list[Node]` |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lid` | `UUID4Type` | Yes | Lab ID |

---

### add_node_to_cml_lab

Add a new node to a lab. Automatically creates default interfaces.

| Property | Value |
|----------|-------|
| **Read-only** | ❌ No |
| **Returns** | `UUID4Type` (node ID) |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lid` | `UUID4Type` | Yes | Lab ID |
| `node` | `NodeCreate` | Yes | Node configuration |

**NodeCreate Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `x` | `int` | Yes | X coordinate (-15000 to 15000) |
| `y` | `int` | Yes | Y coordinate (-15000 to 15000) |
| `label` | `str` | Yes | Node label (1-128 chars) |
| `node_definition` | `str` | Yes | Node definition ID |
| `image_definition` | `str` | No | Image definition |
| `ram` | `int` | No | RAM in MB |
| `cpus` | `int` | No | Number of CPUs |
| `configuration` | `str` | No | Initial configuration |
| `tags` | `list[str]` | No | Tags for the node |

---

### configure_cml_node

Set configuration for a node. Node must be in CREATED state (new or wiped).

| Property | Value |
|----------|-------|
| **Read-only** | ❌ No |
| **Idempotent** | ✅ Yes |
| **Returns** | `bool` |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lid` | `UUID4Type` | Yes | Lab ID |
| `nid` | `UUID4Type` | Yes | Node ID |
| `config` | `str` | Yes | Configuration content |

---

### start_cml_node

Start a specific node.

| Property | Value |
|----------|-------|
| **Read-only** | ❌ No |
| **Idempotent** | ✅ Yes |
| **Returns** | `bool` |

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `lid` | `UUID4Type` | Yes | - | Lab ID |
| `nid` | `UUID4Type` | Yes | - | Node ID |
| `wait_for_convergence` | `bool` | No | `False` | Wait for stable state |

---

### stop_cml_node

Stop a specific node.

| Property | Value |
|----------|-------|
| **Read-only** | ❌ No |
| **Idempotent** | ✅ Yes |
| **Returns** | `bool` |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lid` | `UUID4Type` | Yes | Lab ID |
| `nid` | `UUID4Type` | Yes | Node ID |

---

### wipe_cml_node

Wipe a node's data. Node must be stopped first. **Requires confirmation.**

| Property | Value |
|----------|-------|
| **Destructive** | ✅ Yes |
| **Idempotent** | ✅ Yes |
| **Returns** | `bool` |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lid` | `UUID4Type` | Yes | Lab ID |
| `nid` | `UUID4Type` | Yes | Node ID |

---

### delete_cml_node

Delete a node from a lab. Stops and wipes first if needed. **Requires confirmation.**

| Property | Value |
|----------|-------|
| **Destructive** | ✅ Yes |
| **Returns** | `bool` |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lid` | `UUID4Type` | Yes | Lab ID |
| `nid` | `UUID4Type` | Yes | Node ID |

---

### get_console_log

Get console output from a running node.

| Property | Value |
|----------|-------|
| **Read-only** | ✅ Yes |
| **Returns** | `list[ConsoleLogOutput]` |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lid` | `UUID4Type` | Yes | Lab ID |
| `nid` | `UUID4Type` | Yes | Node ID |

**ConsoleLogOutput:**

| Field | Type | Description |
|-------|------|-------------|
| `time` | `int` | Milliseconds since node started |
| `message` | `str` | Console log message |

---

### send_cli_command

Execute CLI commands on a running node. **Requires PyATS.**

| Property | Value |
|----------|-------|
| **Destructive** | ✅ Yes |
| **Returns** | `str` |

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `lid` | `UUID4Type` | Yes | - | Lab ID |
| `label` | `NodeLabel` | Yes | - | Node label |
| `commands` | `str` | Yes | - | Commands (newline-separated) |
| `config_command` | `bool` | No | `False` | Send as config commands |

!!! warning "Prerequisites"
    - Node must be in BOOTED state
    - PyATS must be installed (`cml-mcp[pyats]`)
    - PYATS_* environment variables must be configured

---

## Interface Operations

### get_interfaces_for_node

Get all interfaces for a node.

| Property | Value |
|----------|-------|
| **Read-only** | ✅ Yes |
| **Returns** | `list[SimplifiedInterfaceResponse]` |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lid` | `UUID4Type` | Yes | Lab ID |
| `nid` | `UUID4Type` | Yes | Node ID |

---

### add_interface_to_node

Add an interface to a node.

| Property | Value |
|----------|-------|
| **Read-only** | ❌ No |
| **Returns** | `SimplifiedInterfaceResponse` |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lid` | `UUID4Type` | Yes | Lab ID |
| `intf` | `InterfaceCreate` | Yes | Interface configuration |

**InterfaceCreate Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `node` | `UUID4Type` | Yes | Node ID |
| `slot` | `int` | No | Slot number (0-128) |
| `mac_address` | `str` | No | MAC address (Linux format) |

---

## Link Operations

### connect_two_nodes

Create a link between two interfaces.

| Property | Value |
|----------|-------|
| **Read-only** | ❌ No |
| **Returns** | `UUID4Type` (link ID) |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lid` | `UUID4Type` | Yes | Lab ID |
| `link_info` | `LinkCreate` | Yes | Link configuration |

**LinkCreate Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `src_int` | `UUID4Type` | Yes | Source interface ID |
| `dst_int` | `UUID4Type` | Yes | Destination interface ID |

---

### get_all_links_for_lab

Get all links in a lab.

| Property | Value |
|----------|-------|
| **Read-only** | ✅ Yes |
| **Returns** | `list[Link]` |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lid` | `UUID4Type` | Yes | Lab ID |

---

### start_cml_link

Enable a link.

| Property | Value |
|----------|-------|
| **Idempotent** | ✅ Yes |
| **Returns** | `bool` |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lid` | `UUID4Type` | Yes | Lab ID |
| `link_id` | `UUID4Type` | Yes | Link ID |

---

### stop_cml_link

Disable a link.

| Property | Value |
|----------|-------|
| **Idempotent** | ✅ Yes |
| **Returns** | `bool` |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lid` | `UUID4Type` | Yes | Lab ID |
| `link_id` | `UUID4Type` | Yes | Link ID |

---

### apply_link_conditioning

Apply network conditions (latency, loss, bandwidth limits) to a link.

| Property | Value |
|----------|-------|
| **Idempotent** | ✅ Yes |
| **Returns** | `bool` |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lid` | `UUID4Type` | Yes | Lab ID |
| `link_id` | `UUID4Type` | Yes | Link ID |
| `condition` | `LinkConditionConfiguration` | Yes | Condition settings |

**LinkConditionConfiguration Schema:**

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `enabled` | `bool` | - | Enable conditioning |
| `bandwidth` | `int` | 0-10,000,000 | Bandwidth (kbps) |
| `latency` | `int` | 0-10,000 | Delay (ms) |
| `loss` | `float` | 0-100 | Packet loss (%) |
| `jitter` | `int` | 0-10,000 | Jitter (ms) |
| `duplicate` | `float` | 0-100 | Duplicate probability (%) |
| `corrupt_prob` | `float` | 0-100 | Corruption probability (%) |
| `reorder_prob` | `float` | 0-100 | Reorder probability (%) |

---

## Annotations

### add_annotation_to_cml_lab

Add a visual annotation to a lab topology.

| Property | Value |
|----------|-------|
| **Read-only** | ❌ No |
| **Returns** | `UUID4Type` (annotation ID) |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lid` | `UUID4Type` | Yes | Lab ID |
| `annotation` | `Annotation` | Yes | Annotation definition |

**Annotation Types:**

=== "TextAnnotation"

    | Field | Type | Description |
    |-------|------|-------------|
    | `type` | `"text"` | Required |
    | `x1`, `y1` | `int` | Anchor coordinates |
    | `text_content` | `str` | Text (max 8192 chars) |
    | `text_font` | `str` | Font name |
    | `text_size` | `int` | Size (1-128) |
    | `color` | `str` | Fill color |

=== "RectangleAnnotation"

    | Field | Type | Description |
    |-------|------|-------------|
    | `type` | `"rectangle"` | Required |
    | `x1`, `y1` | `int` | Start coordinates |
    | `x2`, `y2` | `int` | End coordinates |
    | `color` | `str` | Fill color |
    | `border_color` | `str` | Border color |
    | `border_radius` | `int` | Corner radius (0-128) |

=== "EllipseAnnotation"

    | Field | Type | Description |
    |-------|------|-------------|
    | `type` | `"ellipse"` | Required |
    | `x1`, `y1` | `int` | Center coordinates |
    | `x2`, `y2` | `int` | Radius coordinates |
    | `color` | `str` | Fill color |
    | `border_color` | `str` | Border color |

=== "LineAnnotation"

    | Field | Type | Description |
    |-------|------|-------------|
    | `type` | `"line"` | Required |
    | `x1`, `y1` | `int` | Start coordinates |
    | `x2`, `y2` | `int` | End coordinates |
    | `line_start` | `str` | Start style (arrow, square, circle) |
    | `line_end` | `str` | End style |

---

### delete_annotation_from_lab

Remove an annotation from a lab. **Requires confirmation.**

| Property | Value |
|----------|-------|
| **Destructive** | ✅ Yes |
| **Returns** | `bool` |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lid` | `UUID4Type` | Yes | Lab ID |
| `annotation_id` | `UUID4Type` | Yes | Annotation ID |

---

## User & Group Management

!!! note "Admin Only"
    These tools require admin privileges on the CML server.

### get_cml_users

List all users.

| Property | Value |
|----------|-------|
| **Read-only** | ✅ Yes |
| **Returns** | `list[UserResponse]` |

---

### create_cml_user

Create a new user.

| Property | Value |
|----------|-------|
| **Read-only** | ❌ No |
| **Returns** | `UUID4Type` (user ID) |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `user` | `UserCreate` | Yes | User configuration |

**UserCreate Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | `str` | Yes | Username |
| `password` | `str` | Yes | Password |
| `fullname` | `str` | No | Full name |
| `email` | `str` | No | Email address |
| `admin` | `bool` | No | Admin privileges |
| `groups` | `list[str]` | No | Group IDs |

---

### delete_cml_user

Delete a user. **Requires confirmation.**

| Property | Value |
|----------|-------|
| **Destructive** | ✅ Yes |
| **Returns** | `bool` |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `user_id` | `UUID4Type` | Yes | User ID |

---

### get_cml_groups

List all groups.

| Property | Value |
|----------|-------|
| **Read-only** | ✅ Yes |
| **Returns** | `list[GroupInfoResponse]` |

---

### create_cml_group

Create a new group.

| Property | Value |
|----------|-------|
| **Read-only** | ❌ No |
| **Returns** | `UUID4Type` (group ID) |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `group` | `GroupCreate` | Yes | Group configuration |

**GroupCreate Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `str` | Yes | Group name |
| `description` | `str` | No | Description |
| `members` | `list[str]` | No | User IDs |

---

### delete_cml_group

Delete a group. **Requires confirmation.**

| Property | Value |
|----------|-------|
| **Destructive** | ✅ Yes |
| **Returns** | `bool` |

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `group_id` | `UUID4Type` | Yes | Group ID |
