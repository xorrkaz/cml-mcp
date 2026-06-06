# Topology schema for `create_full_lab_topology`

Read this only when importing a complete, user-supplied topology in one call. For everything else, use the incremental workflow in `SKILL.md` — it is more forgiving.

`topology` must be a structured object (or JSON-encoded object string) with top-level keys `lab`, `nodes`, `links`, and optionally `annotations` / `smart_annotations`. A raw title string, a YAML blob, or a non-Topology JSON string will fail.

## Minimal valid model

```json
{
  "lab":   { "title": "Triangle", "version": "0.3.0" },
  "nodes": [
    { "id": "n0", "label": "R1", "node_definition": "iol-xe", "x": 0,   "y": 0,
      "interfaces": [ { "id": "n0i0", "type": "physical", "slot": 0 } ] },
    { "id": "n1", "label": "R2", "node_definition": "iol-xe", "x": 200, "y": 0,
      "interfaces": [ { "id": "n1i0", "type": "physical", "slot": 0 } ] }
  ],
  "links": [
    { "id": "l0", "n1": "n0", "n2": "n1", "i1": "n0i0", "i2": "n1i0" }
  ]
}
```

## Field notes

- `lab.version` is **required** and must be one of the supported schema versions (e.g. `0.3.0`). When unsure, use the newest the server reports.
- Node `id` and interface `id` are *your* local identifiers, referenced by links. They are not the UUIDs CML returns; CML assigns real UUIDs on import.
- Each link's `n1`/`n2` are node ids and `i1`/`i2` are the interface ids on those nodes. The referenced interfaces must exist in the corresponding node's `interfaces` array.
- Interface `type` is `physical` or `loopback`. Physical interfaces consume slots; create enough for the links you define.
- Optional per-node: `ram` (MB), `cpus`, `cpu_limit` (20–100), `data_volume`/`boot_disk_size` (GB), `image_definition`, `tags`, `parameters`, `priority`, `configuration` (initial startup config as a string, or `[{ "name": "day0-config", "content": "..." }]`).
- Optional per-link: `label`, and `conditioning` (see `operations.md` for the impairment fields).

## Validation discipline

Before importing, cross-check that every `i1`/`i2` in `links` appears as an interface `id` in the named node, and that every `n1`/`n2` matches a node `id`. A dangling reference fails the whole import. If an import fails, fall back to the incremental path rather than blindly retrying the object.
