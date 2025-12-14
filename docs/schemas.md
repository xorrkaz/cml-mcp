# Schemas

This document describes the Pydantic data models used throughout the cml-mcp server.

!!! note "License"
    The schema definitions in `src/cml_mcp/schemas/` are derived from Cisco's CML API and are covered under a [proprietary Cisco license](https://github.com/xorrkaz/cml-mcp/blob/main/src/cml_mcp/schemas/LICENSE).

## Schema Organization

```
schemas/
├── common.py              # Shared types and base models
├── labs.py                # Lab models
├── nodes.py               # Node models
├── links.py               # Link models
├── interfaces.py          # Interface models
├── topologies.py          # Topology import/export
├── annotations.py         # Visual annotations
├── smart_annotations.py   # Smart annotations
├── users.py               # User models
├── groups.py              # Group models
├── system.py              # System info/health
├── node_definitions.py    # Node type definitions
├── image_definitions.py   # Image definitions
└── simple_core/           # State enums and type hints
    └── common/
        ├── events.py      # Event types
        ├── states.py      # State enums
        └── type_hints.py  # Type definitions
```

---

## Common Types

### UUID4Type

Standard UUID format for CML resources.

```python
UUID4Type = Annotated[
    str,
    Field(
        description="A UUID4",
        examples=["90f84e38-a71c-4d57-8d90-00fa8a197385"],
        pattern=r"^[\da-f]{8}-[\da-f]{4}-4[\da-f]{3}-[89ab][\da-f]{3}-[\da-f]{12}$",
    ),
]
```

### UserName

```python
UserName = Annotated[
    str,
    Field(
        description="The name of the user.",
        examples=["admin"],
        min_length=1,
        max_length=32,
    ),
]
```

### DefinitionID

Node or image definition identifier.

```python
DefinitionID = Annotated[
    str,
    Field(
        min_length=1,
        max_length=250,
        description="A node or image definition ID.",
        examples=["iosv", "csr1000v", "alpine"],
    ),
]
```

### Coordinate

Position coordinate for nodes and annotations.

```python
Coordinate = Annotated[int, Field(ge=-15000, le=15000)]
```

### Label

Name label with length constraints.

```python
Label = Annotated[str, Field(min_length=1, max_length=128)]
```

---

## Lab Models

### Lab

Represents a CML lab with current state.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID4Type` | Lab unique identifier |
| `lab_title` | `str` | Lab title (1-64 chars) |
| `lab_description` | `str` | Description (max 4096 chars) |
| `lab_notes` | `str` | Notes (max 32768 chars) |
| `owner` | `UUID4Type` | Owner user ID |
| `owner_username` | `str` | Owner username |
| `state` | `State` | Lab state (STOPPED, STARTED, etc.) |
| `node_count` | `int` | Number of nodes |
| `link_count` | `int` | Number of links |
| `groups` | `list[LabGroup]` | Associated groups |

### LabCreate

Used when creating or updating a lab.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | `str` | No | Title (1-64 chars) |
| `owner` | `UUID4Type` | No | Owner user ID |
| `description` | `str` | No | Description |
| `notes` | `str` | No | Notes |
| `associations` | `LabAssociations` | No | Permissions |

### LabAssociations

Group and user permission associations.

```python
class LabAssociations(BaseModel):
    groups: list[LabGroupAssociation] = None
    users: list[LabUserAssociation] = None

class LabGroupAssociation(BaseModel):
    id: UUID4Type  # Group ID
    permissions: list[str]  # ["lab_admin", "lab_edit", "lab_exec", "lab_view"]

class LabUserAssociation(BaseModel):
    id: UUID4Type  # User ID
    permissions: list[str]
```

---

## Node Models

### Node

Represents a node in a CML lab.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID4Type` | Node identifier |
| `label` | `str` | Node label |
| `node_definition` | `str` | Node type (e.g., `iosv`) |
| `x`, `y` | `int` | Canvas position |
| `state` | `NodeStates` | Node state |
| `boot_progress` | `str` | Boot progress percentage |
| `image_definition` | `str` | Image definition |
| `ram` | `int` | RAM in MB |
| `cpus` | `int` | Number of CPUs |
| `tags` | `list[str]` | Tags |

### NodeCreate

Used when adding a node to a lab.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `x` | `int` | Yes | - | X coordinate (-15000 to 15000) |
| `y` | `int` | Yes | - | Y coordinate |
| `label` | `str` | Yes | - | Node label (1-128 chars) |
| `node_definition` | `str` | Yes | - | Node type ID |
| `image_definition` | `str` | No | - | Image ID |
| `ram` | `int` | No | - | RAM in MB |
| `cpus` | `int` | No | - | CPU count |
| `configuration` | `str` | No | - | Initial config |
| `tags` | `list[str]` | No | `[]` | Tags |

### NodeStates

```python
class NodeStates(str, Enum):
    STOPPED = "STOPPED"
    STARTED = "STARTED"
    QUEUED = "QUEUED"
    BOOTED = "BOOTED"
    CREATED = "CREATED"
```

---

## Link Models

### Link

Represents a connection between two interfaces.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID4Type` | Link identifier |
| `interface_a` | `UUID4Type` | First interface |
| `interface_b` | `UUID4Type` | Second interface |
| `label` | `str` | Link label |
| `state` | `str` | Link state |
| `conditioning` | `dict` | Link conditioning config |

### LinkCreate

Used when creating a link.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `src_int` | `UUID4Type` | Yes | Source interface ID |
| `dst_int` | `UUID4Type` | Yes | Destination interface ID |

### LinkConditionConfiguration

Network conditioning parameters.

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `enabled` | `bool` | - | Enable conditioning |
| `bandwidth` | `int` | 0-10,000,000 | Bandwidth (kbps) |
| `latency` | `int` | 0-10,000 | Delay (ms) |
| `loss` | `float` | 0-100 | Packet loss (%) |
| `jitter` | `int` | 0-10,000 | Jitter (ms) |
| `duplicate` | `float` | 0-100 | Duplicate (%) |
| `corrupt_prob` | `float` | 0-100 | Corruption (%) |
| `reorder_prob` | `float` | 0-100 | Reorder (%) |

---

## Interface Models

### InterfaceCreate

Used when adding an interface to a node.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `node` | `UUID4Type` | Yes | Node ID |
| `slot` | `int` | No | Slot number (0-128) |
| `mac_address` | `str` | No | MAC address |

### SimplifiedInterfaceResponse

| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID4Type` | Interface identifier |
| `label` | `str` | Interface label |
| `slot` | `int` | Slot number |
| `type` | `str` | Interface type |
| `mac_address` | `str` | MAC address |
| `is_connected` | `bool` | Connection status |

---

## Topology Models

### Topology

Complete lab topology for import.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `lab` | `LabTopology` | Yes | Lab metadata |
| `nodes` | `list[NodeTopology]` | Yes | Node definitions |
| `links` | `list[LinkTopology]` | Yes | Link definitions |
| `annotations` | `list[Annotation]` | No | Visual annotations |
| `smart_annotations` | `list[SmartAnnotationBase]` | No | Smart annotations |

### LabTopology

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | `str` | No | Schema version |
| `title` | `str` | No | Lab title |
| `description` | `str` | No | Description |
| `notes` | `str` | No | Notes |

---

## Annotation Models

### TextAnnotation

| Field | Type | Description |
|-------|------|-------------|
| `type` | `"text"` | Annotation type |
| `x1`, `y1` | `int` | Anchor coordinates |
| `text_content` | `str` | Text (max 8192 chars) |
| `text_font` | `str` | Font name |
| `text_size` | `int` | Size (1-128) |
| `color` | `str` | Fill color |
| `rotation` | `int` | Rotation (0-360) |

### RectangleAnnotation

| Field | Type | Description |
|-------|------|-------------|
| `type` | `"rectangle"` | Annotation type |
| `x1`, `y1` | `int` | Start coordinates |
| `x2`, `y2` | `int` | End coordinates |
| `color` | `str` | Fill color |
| `border_color` | `str` | Border color |
| `border_radius` | `int` | Corner radius (0-128) |

### EllipseAnnotation

| Field | Type | Description |
|-------|------|-------------|
| `type` | `"ellipse"` | Annotation type |
| `x1`, `y1` | `int` | Center coordinates |
| `x2`, `y2` | `int` | Radius |
| `color` | `str` | Fill color |
| `border_color` | `str` | Border color |

### LineAnnotation

| Field | Type | Description |
|-------|------|-------------|
| `type` | `"line"` | Annotation type |
| `x1`, `y1` | `int` | Start coordinates |
| `x2`, `y2` | `int` | End coordinates |
| `line_start` | `str` | Start style (arrow, square, circle) |
| `line_end` | `str` | End style |

---

## User & Group Models

### UserCreate

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | `str` | Yes | Username |
| `password` | `str` | Yes | Password |
| `fullname` | `str` | No | Full name |
| `email` | `str` | No | Email address |
| `admin` | `bool` | No | Admin privileges |
| `groups` | `list[str]` | No | Group IDs |

### UserResponse

| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID4Type` | User identifier |
| `username` | `str` | Username |
| `fullname` | `str` | Full name |
| `email` | `str` | Email address |
| `admin` | `bool` | Admin status |

### GroupCreate

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `str` | Yes | Group name |
| `description` | `str` | No | Description |
| `members` | `list[str]` | No | User IDs |

### GroupInfoResponse

| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID4Type` | Group identifier |
| `name` | `str` | Group name |
| `description` | `str` | Description |
| `members` | `list[str]` | Member user IDs |

---

## System Models

### SystemInformation

| Field | Type | Description |
|-------|------|-------------|
| `version` | `str` | CML version |
| `build` | `str` | Build number |
| `hostname` | `str` | Server hostname |

### SystemHealth

| Field | Type | Description |
|-------|------|-------------|
| `status` | `str` | Health status |
| `compute` | `dict` | Compute resources |
| `memory` | `dict` | Memory usage |

### SystemStats

| Field | Type | Description |
|-------|------|-------------|
| `labs` | `int` | Total labs |
| `nodes` | `int` | Total nodes |
| `users` | `int` | Total users |
