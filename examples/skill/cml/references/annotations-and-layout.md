# Layout recipes and annotations

Read when laying out a non-trivial topology or adding visual grouping. Coordinates range −15000..15000; the recipes below assume a ~150–200 unit gap between adjacent devices, which keeps labels and links from overlapping in the CML canvas.

## Coordinate recipes

These are starting grids, not laws — adjust to reduce link crossings.

**Linear / chain (R1—R2—R3—R4):** same `y`, step `x` by ~200.
`(0,0) (200,0) (400,0) (600,0)`

**Hub-and-spoke:** hub at center, spokes on a ring around it.
Hub `(0,0)`; spokes at `(0,-200) (200,0) (0,200) (-200,0)` and the diagonals for more.

**Spine-leaf:** spines on a top row, leaves on a lower row, offset so links fan out.
Spines `y=0` at `x = 100, 400`; leaves `y=250` at `x = 0, 200, 400, 600`.

**Three-tier (core/dist/access):** stack rows top→bottom by role.
Core `y=0`, distribution `y=250`, access `y=500`, end hosts `y=700`. Keep peers in a tier aligned on the same `y` and symmetric about `x=0`.

General rules: hierarchy flows top→bottom (or center→out for hub designs); align peers; prefer the placement with fewer crossing links; leave room for labels.

## Annotations

Annotations are visual only — they don't affect connectivity. Two ways to group/label:

**Smart annotations** (preferred for grouping) auto-enclose all nodes sharing a `tag`. Tag the relevant nodes (via the node `tags` field), then add a smart annotation referencing that tag:

```json
{ "tag": "core", "label": "Core", "fill_color": "rgba(0,120,255,0.08)",
  "border_color": "#0078FF", "padding": 35 }
```

**Manual annotations** (`add_text_annotation`, `add_rectangle_annotation`, `add_ellipse_annotation`, `add_line_annotation`) when you need exact placement. Common arguments:

- All shapes: `x1`/`y1` anchor, plus `x2`/`y2` for width/height (rectangle/ellipse) or end point (line); `color` (fill), `border_color`, `border_style` (`""` solid, `"2,2"` dotted, `"4,2"` dashed), `thickness`, `z_index`.
- Text: `text_content`, `text_size`, `text_font`, `text_bold`, `text_italic`, `text_unit` (`pt`/`px`/`em`).
- Lines: `line_start`/`line_end` arrowheads (`arrow`/`square`/`circle`).
- Colors accept `#RRGGBB`, `rgba(...)`, or CSS names. Use translucent fills (low rgba alpha) for zone boxes so device icons stay visible. Put boxes on a low/negative `z_index` so they sit behind nodes.

To label a functional zone: draw a translucent rectangle behind the group (low `z_index`), then a text annotation as its title near the top-left corner.