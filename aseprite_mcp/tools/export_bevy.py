"""Export a sprite-sheet plus a Bevy-friendly TextureAtlas JSON for Project VN."""
import json
import os
import subprocess
import tempfile
from typing import Literal

from ..core.commands import AsepriteCommand
from .. import mcp


def _run_aseprite_export(
    aseprite_file: str,
    sheet_png: str,
    sheet_data: str,
    sheet_type: str,
    ignore_empty: bool,
) -> tuple[bool, str]:
    args = [
        "--batch",
        aseprite_file,
        "--sheet",
        sheet_png,
        "--data",
        sheet_data,
        "--format",
        "json-array",
        "--list-tags",
        "--sheet-type",
        sheet_type,
    ]
    if ignore_empty:
        args.append("--ignore-empty")
    return AsepriteCommand.run_command(args)


@mcp.tool()
async def export_bevy_atlas(
    aseprite_file: str,
    output_png: str,
    output_json: str | None = None,
    sheet_type: Literal["rows", "columns"] = "rows",
    ignore_empty: bool = True,
) -> str:
    """Export a sprite-sheet PNG plus a Bevy-friendly TextureAtlas JSON.

    Runs Aseprite CLI to produce a regular-grid sheet (one tile per frame,
    all same size) and a sidecar JSON with tile size, grid shape, frame
    durations, and animation tags reshaped for Bevy 0.18 consumers.

    Args:
        aseprite_file: Source .aseprite path.
        output_png: Destination sprite-sheet PNG.
        output_json: Bevy JSON path (defaults to <output_png>.json).
        sheet_type: 'rows' for horizontal-major grid, 'columns' for vertical.
        ignore_empty: Drop fully-transparent frames before packing.

    Returns:
        JSON summary with atlas dimensions, frame count, and animations.
    """
    if not os.path.exists(aseprite_file):
        return f"aseprite_file {aseprite_file} not found"

    if output_json is None:
        output_json = output_png + ".json"

    parent_png = os.path.dirname(os.path.abspath(output_png))
    parent_json = os.path.dirname(os.path.abspath(output_json))
    for p in (parent_png, parent_json):
        if p:
            os.makedirs(p, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tmp:
        raw_json = tmp.name

    try:
        success, output = _run_aseprite_export(
            aseprite_file, output_png, raw_json, sheet_type, ignore_empty
        )
        if not success:
            return f"Aseprite export failed: {output}"

        with open(raw_json) as f:
            data = json.load(f)
    except subprocess.SubprocessError as e:
        return f"Aseprite subprocess error: {e}"
    except json.JSONDecodeError as e:
        return f"Failed to parse Aseprite JSON: {e}"
    finally:
        if os.path.exists(raw_json):
            os.remove(raw_json)

    frames = data.get("frames", [])
    meta = data.get("meta", {})
    if not frames:
        return "No frames exported (sprite may be empty after ignore_empty)"

    sizes = {(f["frame"]["w"], f["frame"]["h"]) for f in frames}
    if len(sizes) != 1:
        return (
            "Frames have non-uniform size - Bevy TextureAtlas needs a regular grid. "
            "Check for trim or hidden layers expanding bounds."
        )
    tile_w, tile_h = sizes.pop()

    sheet_w = meta.get("size", {}).get("w")
    sheet_h = meta.get("size", {}).get("h")
    if not (sheet_w and sheet_h):
        return "Aseprite meta is missing sheet size"

    columns = sheet_w // tile_w
    rows = sheet_h // tile_h
    if columns * rows < len(frames):
        return (
            f"Computed grid {columns}x{rows} cannot hold {len(frames)} frames; "
            "this is unexpected for sheet-type rows/columns."
        )

    durations_ms = [f.get("duration", 100) for f in frames]

    animations: dict[str, dict] = {}
    for tag in meta.get("frameTags", []):
        name = tag.get("name") or "untagged"
        start = int(tag.get("from", 0))
        end = int(tag.get("to", start))
        direction = tag.get("direction", "forward")
        animations[name] = {
            "frames": list(range(start, end + 1)),
            "frame_durations_ms": durations_ms[start : end + 1],
            "direction": direction,
        }

    bevy = {
        "image": os.path.basename(output_png),
        "tile_size": [tile_w, tile_h],
        "columns": columns,
        "rows": rows,
        "padding": [0, 0],
        "offset": [0, 0],
        "frame_count": len(frames),
        "frame_durations_ms": durations_ms,
        "animations": animations,
    }

    with open(output_json, "w") as f:
        json.dump(bevy, f, indent=2)

    return json.dumps(
        {
            "png": os.path.abspath(output_png),
            "json": os.path.abspath(output_json),
            "tile_size": [tile_w, tile_h],
            "grid": [columns, rows],
            "frame_count": len(frames),
            "animations": list(animations.keys()),
        }
    )
