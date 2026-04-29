---
name: aseprite-bevy-pipeline
description: Export Aseprite sprite-sheets ready for Bevy 0.18 TextureAtlas with animation tags. Use when shipping pixel art from Aseprite to Project VN or any Bevy game. Produces a uniform-grid PNG plus a sidecar JSON that maps directly to TextureAtlasLayout::from_grid. Requires the aseprite-mcp-colony MCP server.
---

# Aseprite to Bevy Pipeline

## What it produces

`export_bevy_atlas` writes:

- A **PNG sprite-sheet** (uniform grid, all tiles same size).
- A **sidecar JSON** with `tile_size`, `columns`, `rows`, `padding`, `offset`, `frame_count`, `frame_durations_ms`, and `animations` reshaped from Aseprite tags.

The JSON maps directly to `TextureAtlasLayout::from_grid` in Bevy.

## Usage

```python
export_bevy_atlas(
    aseprite_file="hero.aseprite",
    output_png="assets/sprites/hero.png",
    output_json="assets/sprites/hero.atlas.json",
    sheet_type="rows",       # horizontal grid (default), or "columns"
    ignore_empty=True,       # drop fully-transparent frames before packing
)
```

## Animation tags

Define tags in Aseprite (or via `set_tag(filename, name, from_frame, to_frame, direction)`) before exporting.

The JSON output:
```json
"animations": {
  "idle":   { "frames": [0,1,2,3], "frame_durations_ms": [120,120,120,120], "direction": "forward" },
  "attack": { "frames": [4,5,6,7], "frame_durations_ms": [60,60,80,100],   "direction": "forward" }
}
```

Frame durations come from each frame's timing in Aseprite. Override with `set_frame_duration(filename, frame_index, ms)` or `set_frame_duration_all(filename, ms)`.

## Bevy consumer (sketch)

```rust
let layout = TextureAtlasLayout::from_grid(
    UVec2::new(json.tile_size[0], json.tile_size[1]),
    json.columns,
    json.rows,
    None,
    None,
);
```

## Conventions for Project VN

- Source `.aseprite` files live under `/mnt/Jeux/Project/Aseprite/...`, NOT in the game repo.
- Exported PNG + JSON go into the VN Engine's `assets/sprites/` folder.
- Set `ignore_empty=True` for character sheets so the artist can leave WIP empty frames.
- Set `ignore_empty=False` for tilesets where empty tiles are intentional.

## Failure modes

- "Frames have non-uniform size": Aseprite trimmed something. Disable trim per layer or expand the canvas so every frame ends up the same size.
- "No documents to export": every frame is fully transparent. Either draw something or set `ignore_empty=False`.
- "aseprite not found": `ASEPRITE_PATH` env var missing. Already configured in the MCP setup; if you forked the config, re-add it.
