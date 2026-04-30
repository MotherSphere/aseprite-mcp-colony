"""MCP tools exposing the bundled creative presets (palettes, dither, tiles, animation, reference).

These tools are pure data accessors plus a few Aseprite-touching instantiators.
Heavy logic (palette parsing, image dithering) reuses palette_apply helpers.
"""
from __future__ import annotations

import json
import os
from typing import Any

from .. import mcp
from ..presets import (
    category_dir,
    entry_file,
    find_entry,
    list_entries,
    load_json,
    load_manifest,
    load_reference,
    presets_dir,
    reference_topics,
)
from ..core.commands import AsepriteCommand, lua_escape, reject_traversal
from .palette_apply import _parse_gpl


# ----------------------------- palettes -----------------------------

@mcp.tool()
async def list_preset_palettes(
    tag: str | None = None,
    search: str | None = None,
    curated_set: str | None = None,
) -> str:
    """List bundled palette presets.

    Args:
        tag: Filter to entries having this tag (e.g. 'dark-fantasy', 'gameboy').
        search: Substring search across name/slug/description/creator/tags (case-insensitive).
        curated_set: Use a curated bundle name from the manifest (e.g. 'dark_fantasy_vn',
            'vn_full_color', 'starter_kit_small', 'gameboy_likes', 'tiny_under_8').

    Returns:
        JSON list of {slug, name, color_count, creator, tags, description}.
    """
    manifest = load_manifest("palettes")
    if curated_set:
        slugs = manifest.get("curated_sets", {}).get(curated_set)
        if slugs is None:
            return json.dumps({"error": f"unknown curated_set {curated_set!r}", "available": list(manifest.get("curated_sets", {}).keys())})
        entries = [e for e in manifest["entries"] if e["slug"] in slugs]
    else:
        entries = list_entries("palettes", tag=tag, search=search)
    summary = [
        {
            "slug": e["slug"],
            "name": e["name"],
            "color_count": e.get("color_count"),
            "creator": e.get("creator"),
            "tags": e.get("tags", []),
            "description": e.get("description"),
        }
        for e in entries
    ]
    return json.dumps({"count": len(summary), "palettes": summary})


@mcp.tool()
async def get_preset_palette_info(slug: str) -> str:
    """Get full metadata for a palette preset (creator, source URL, tags, best_for, file path).

    Args:
        slug: Palette slug (e.g. 'pico-8', 'steam-lords'). See list_preset_palettes.
    """
    entry = find_entry("palettes", slug)
    if entry is None:
        return json.dumps({"error": f"unknown palette slug {slug!r}"})
    out = dict(entry)
    out["abs_file"] = str(entry_file("palettes", slug))
    return json.dumps(out)


@mcp.tool()
async def apply_preset_palette(slug: str, target_aseprite: str) -> str:
    """Apply a bundled preset palette (.gpl) to an existing .aseprite sprite.

    Args:
        slug: Palette slug (e.g. 'steam-lords', 'pico-8').
        target_aseprite: Path to the .aseprite file to modify in place.
    """
    if not os.path.exists(target_aseprite):
        return f"target_aseprite {target_aseprite} not found"
    try:
        gpl = entry_file("palettes", slug)
    except (KeyError, FileNotFoundError) as e:
        return f"Palette preset error: {e}"
    try:
        colors = _parse_gpl(str(gpl))
    except Exception as e:
        return f"Failed to parse bundled GPL {gpl}: {e}"

    palette_entries = "\n".join(
        f"    pal:setColor({i}, Color({r}, {g}, {b}))"
        for i, (r, g, b) in enumerate(colors)
    )
    script = f"""
    local spr = app.activeSprite
    if not spr then return "No active sprite" end
    local pal = Palette({len(colors)})
{palette_entries}
    spr:setPalette(pal)
    spr:saveAs(spr.filename)
    return "Palette set"
    """
    success, output = AsepriteCommand.execute_lua_script(script, target_aseprite)
    if not success:
        return f"Failed to apply preset palette: {output}"
    return json.dumps({
        "applied_slug": slug,
        "applied_to": target_aseprite,
        "color_count": len(colors),
        "source_gpl": str(gpl),
    })


# ----------------------------- dither -----------------------------

@mcp.tool()
async def list_dither_patterns() -> str:
    """List bundled binary dither patterns (hand-painted style).

    Returns:
        JSON of {slug, size, use, tags, matrix} for each pattern.
    """
    data = load_json("dither", "patterns.json")
    return json.dumps(data)


@mcp.tool()
async def list_dither_kernels() -> str:
    """List bundled perceptual dither kernels (Bayer + error-diffusion).

    Returns:
        JSON with 'ordered' (Bayer matrices) and 'error_diffusion' (kernels with weights).
    """
    data = load_json("dither", "kernels.json")
    return json.dumps(data)


@mcp.tool()
async def get_dither_guidance() -> str:
    """Decision tree + recipes for picking the right dither approach.

    Returns:
        JSON with decision_tree, common_recipes, anti_patterns, kernel_comparison.
    """
    data = load_reference("dither_guidance")
    return json.dumps(data)


# ----------------------------- tiles -----------------------------

@mcp.tool()
async def list_tile_templates(tag: str | None = None) -> str:
    """List bundled tile structure templates (brick, cobble, plank, grass, water, lava, etc).

    Args:
        tag: Optional filter (e.g. 'wall', 'floor', 'animated', 'dark-fantasy').
    """
    entries = list_entries("tiles", tag=tag)
    summary = [
        {"slug": e["slug"], "name": e["name"], "tile_size": e.get("tile_size"), "frames": e.get("frames", 1), "tags": e.get("tags", []), "description": e.get("description")}
        for e in entries
    ]
    return json.dumps({"count": len(summary), "tiles": summary})


@mcp.tool()
async def get_tile_template_info(slug: str) -> str:
    """Get full template definition for a tile preset (canvas, layers, guide pixels, palette hints)."""
    entry = find_entry("tiles", slug)
    if entry is None:
        return json.dumps({"error": f"unknown tile template {slug!r}"})
    full = load_json("tiles", entry["file"])
    return json.dumps(full)


def _build_tile_lua(tpl: dict[str, Any], dest_abs: str) -> str:
    """Generate a Lua script that creates a fresh sprite according to the template definition."""
    canvas = tpl.get("canvas", {})
    width = int(canvas.get("width", 16))
    height = int(canvas.get("height", 16))
    frames = int(canvas.get("frames", 1))
    frame_dur_ms = int(canvas.get("frame_duration_ms", 100))
    safe_path = lua_escape(dest_abs.replace("\\", "/"))

    layers = tpl.get("layers", [])
    tags_anim = tpl.get("tags_animation", [])

    # Pre-compute guide pixel literal (used by pixels_from_guide).
    guide_pixels: list[list[int]] = []
    for L in layers:
        if L.get("name") == "GUIDE":
            guide_pixels = L.get("pixels", [])
            break
    guide_lua = ", ".join(f"{{{p[0]},{p[1]}}}" for p in guide_pixels)

    layer_blocks: list[str] = []
    for li, L in enumerate(layers):
        name = lua_escape(L.get("name", f"layer_{li}"))
        visible = "true" if L.get("visible", True) else "false"
        opacity = int(L.get("opacity", 255))
        purpose = lua_escape(L.get("purpose", ""))

        # Decide painting strategy.
        fill_all_color = L.get("fill_all")
        fill_all_frames_color = L.get("fill_all_frames")
        pixels = L.get("pixels", [])
        pixels_color = L.get("pixels_color")
        pixels_from_guide = bool(L.get("pixels_from_guide"))

        paint_lua = ""
        if fill_all_frames_color:
            r, g, b = _hex_to_rgb(fill_all_frames_color)
            paint_lua = f"""
            for fi = 1, #spr.frames do
                local cel = layer:cel(fi) or spr:newCel(layer, spr.frames[fi])
                local img = cel.image:clone()
                for y = 0, {height-1} do
                    for x = 0, {width-1} do
                        img:putPixel(x, y, app.pixelColor.rgba({r},{g},{b},255))
                    end
                end
                cel.image = img
            end
            """
        elif fill_all_color:
            r, g, b = _hex_to_rgb(fill_all_color)
            paint_lua = f"""
            local cel = layer:cel(1) or spr:newCel(layer, spr.frames[1])
            local img = cel.image:clone()
            for y = 0, {height-1} do
                for x = 0, {width-1} do
                    img:putPixel(x, y, app.pixelColor.rgba({r},{g},{b},255))
                end
            end
            cel.image = img
            """
        elif pixels_color and (pixels_from_guide or pixels):
            r, g, b = _hex_to_rgb(pixels_color)
            if pixels_from_guide:
                pix_literal = guide_lua
            else:
                pix_literal = ", ".join(f"{{{p[0]},{p[1]}}}" for p in pixels)
            paint_lua = f"""
            local cel = layer:cel(1) or spr:newCel(layer, spr.frames[1])
            local img = cel.image:clone()
            local pts = {{ {pix_literal} }}
            for _, p in ipairs(pts) do
                img:putPixel(p[1], p[2], app.pixelColor.rgba({r},{g},{b},255))
            end
            cel.image = img
            """
        # else: leave empty for the artist to paint.

        layer_block = f"""
        do
            local layer
            if {1 if li == 0 else 0} == 1 then
                -- first layer reuses the default sprite layer
                layer = spr.layers[1]
            else
                layer = spr:newLayer()
            end
            layer.name = "{name}"
            layer.isVisible = {visible}
            layer.opacity = {opacity}
            layer.data = "{purpose}"
            {paint_lua}
        end
        """
        layer_blocks.append(layer_block)

    layers_lua = "\n".join(layer_blocks)

    # Add frames if needed.
    add_frames_lua = ""
    if frames > 1:
        add_frames_lua = f"""
        for i = 2, {frames} do spr:newFrame() end
        for i = 1, #spr.frames do
            spr.frames[i].duration = {frame_dur_ms} / 1000.0
        end
        """

    # Tags.
    tags_lua = ""
    for t in tags_anim:
        tn = lua_escape(t.get("name", "loop"))
        f1 = int(t.get("from", 1))
        f2 = int(t.get("to", frames))
        tags_lua += f"""
        do
            local tag = spr:newTag({f1}, {f2})
            tag.name = "{tn}"
        end
        """

    return f"""
    local spr = Sprite({width}, {height})
    app.transaction(function()
        {add_frames_lua}
        {layers_lua}
        {tags_lua}
    end)
    spr:saveAs("{safe_path}")
    return "Tile template instantiated"
    """


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"Bad hex color: {hex_color}")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


@mcp.tool()
async def instantiate_tile_template(slug: str, dest_path: str) -> str:
    """Create a new .aseprite from a bundled tile template (canvas + layers + guide + pre-fills).

    Args:
        slug: Tile template slug (e.g. 'brick_7-1', 'cobble_irregular', 'water_anim_4f').
        dest_path: Output .aseprite file path.
    """
    err = reject_traversal(dest_path)
    if err:
        return err

    entry = find_entry("tiles", slug)
    if entry is None:
        return json.dumps({"error": f"unknown tile template {slug!r}"})
    tpl = load_json("tiles", entry["file"])
    abs_dest = os.path.abspath(dest_path)
    parent = os.path.dirname(abs_dest)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)

    script = _build_tile_lua(tpl, abs_dest)
    success, output = AsepriteCommand.execute_lua_script(script)
    if not success:
        return f"Failed to instantiate template: {output}"
    return json.dumps({
        "instantiated": slug,
        "dest_path": abs_dest,
        "tile_size": tpl.get("canvas", {}),
        "layers": [L.get("name") for L in tpl.get("layers", [])],
        "palette_tags_recommended": tpl.get("palette_tags_recommended", []),
        "color_hint_swatches": tpl.get("color_hint_swatches", []),
        "rule_summary": tpl.get("rule_summary"),
    })


# ----------------------------- animation -----------------------------

@mcp.tool()
async def list_animation_presets(tag: str | None = None, curated_set: str | None = None) -> str:
    """List bundled animation cycle presets (idle, walk, run, attack, hurt, death, etc).

    Args:
        tag: Optional filter (e.g. 'walk', 'attack', 'jrpg', 'boss').
        curated_set: Use a curated bundle ('hero_complete', 'minor_enemy', 'boss', 'npc_dialog', 'jrpg_classic').
    """
    manifest = load_manifest("animation")
    if curated_set:
        slugs = manifest.get("curated_sets", {}).get(curated_set)
        if slugs is None:
            return json.dumps({"error": f"unknown curated_set {curated_set!r}", "available": list(manifest.get("curated_sets", {}).keys())})
        entries = [e for e in manifest["entries"] if e["slug"] in slugs]
    else:
        entries = list_entries("animation", tag=tag)
    return json.dumps({"count": len(entries), "presets": entries})


@mcp.tool()
async def get_animation_preset_info(slug: str) -> str:
    """Get full cycle definition (frame_count, durations, key_poses, loop type, recommended_for)."""
    cycles = load_json("animation", "cycles.json")
    cycle = cycles.get("cycles", {}).get(slug)
    if cycle is None:
        return json.dumps({"error": f"unknown animation preset {slug!r}", "available": list(cycles.get("cycles", {}).keys())})
    return json.dumps({"slug": slug, **cycle})


def _animation_lua(slug: str, cycle: dict[str, Any], add_to_existing: bool, w: int = 32, h: int = 32, dest_abs: str | None = None) -> str:
    n = int(cycle["frame_count"])
    durations = cycle.get("durations_ms", [100] * n)
    name = lua_escape(cycle.get("tag_role", slug))

    # Build duration assignments.
    if add_to_existing:
        prelude = """
        local spr = app.activeSprite
        if not spr then return "No active sprite" end
        local start_count = #spr.frames
        """
        save_line = "spr:saveAs(spr.filename)"
    else:
        safe_path = lua_escape((dest_abs or f"{slug}.aseprite").replace("\\", "/"))
        prelude = f"""
        local spr = Sprite({w}, {h})
        local start_count = 0
        """
        save_line = f'spr:saveAs("{safe_path}")'

    # Add (n) new frames; first existing frame counts as frame 1 of cycle when start_count==0.
    # When add_to_existing, we add n frames after the current count and tag those.
    add_frames_block = f"""
        for i = 1, ({n} - (start_count == 0 and 1 or 0)) do
            spr:newFrame()
        end
    """
    duration_lines = "\n".join(
        f"        spr.frames[start_count + {i+1}].duration = {durations[i] if i < len(durations) else 100} / 1000.0"
        for i in range(n)
    )

    return f"""
    {prelude}
    app.transaction(function()
        {add_frames_block}
{duration_lines}
        local tag = spr:newTag(start_count + 1, start_count + {n})
        tag.name = "{name}"
    end)
    {save_line}
    return "Animation preset applied"
    """


@mcp.tool()
async def apply_animation_preset(slug: str, target_aseprite: str) -> str:
    """Add frames + tag + per-frame durations from a bundled cycle preset to an EXISTING sprite.

    Frames are appended after current frames. A new tag is created spanning the new frames.

    Args:
        slug: Animation preset slug (e.g. 'walk_4f', 'attack_swing_6f').
        target_aseprite: Path to existing .aseprite file.
    """
    if not os.path.exists(target_aseprite):
        return f"target_aseprite {target_aseprite} not found"
    cycles = load_json("animation", "cycles.json")
    cycle = cycles.get("cycles", {}).get(slug)
    if cycle is None:
        return json.dumps({"error": f"unknown animation preset {slug!r}"})
    script = _animation_lua(slug, cycle, add_to_existing=True)
    success, output = AsepriteCommand.execute_lua_script(script, target_aseprite)
    if not success:
        return f"Failed to apply animation preset: {output}"
    return json.dumps({"applied_slug": slug, "target": target_aseprite, "frame_count_added": cycle["frame_count"]})


@mcp.tool()
async def instantiate_animation_preset(
    slug: str,
    dest_path: str,
    width: int = 32,
    height: int = 32,
) -> str:
    """Create a new .aseprite sprite pre-populated with frames + tag + durations for a cycle preset.

    Args:
        slug: Animation preset slug (e.g. 'walk_4f').
        dest_path: Output .aseprite file path.
        width: Canvas width (default 32).
        height: Canvas height (default 32).
    """
    err = reject_traversal(dest_path)
    if err:
        return err
    cycles = load_json("animation", "cycles.json")
    cycle = cycles.get("cycles", {}).get(slug)
    if cycle is None:
        return json.dumps({"error": f"unknown animation preset {slug!r}"})

    abs_dest = os.path.abspath(dest_path)
    parent = os.path.dirname(abs_dest)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    script = _animation_lua(slug, cycle, add_to_existing=False, w=width, h=height, dest_abs=abs_dest)
    success, output = AsepriteCommand.execute_lua_script(script)
    if not success:
        return f"Failed to instantiate animation preset: {output}"
    return json.dumps({
        "instantiated": slug,
        "dest_path": abs_dest,
        "frame_count": cycle["frame_count"],
        "key_poses": cycle.get("key_poses"),
        "tag_role": cycle.get("tag_role"),
    })


# ----------------------------- reference -----------------------------

@mcp.tool()
async def list_reference_topics() -> str:
    """List available reference knowledge topics (pixel art principles, color theory, easing, etc)."""
    manifest = load_manifest("reference")
    topics = manifest.get("topics", [])
    return json.dumps({"count": len(topics), "topics": [{"slug": t["slug"], "name": t["name"], "description": t.get("description")} for t in topics]})


@mcp.tool()
async def get_reference(topic: str) -> str:
    """Fetch a structured reference document.

    Args:
        topic: Topic slug. Available: 'pixel_art_principles', 'sprite_size_conventions',
            'color_theory', 'easing_curves', 'dither_guidance', 'animation_principles'.
    """
    try:
        data = load_reference(topic)
    except FileNotFoundError:
        return json.dumps({"error": f"unknown reference topic {topic!r}", "available": reference_topics()})
    return json.dumps(data)


# ----------------------------- meta -----------------------------

@mcp.tool()
async def presets_overview() -> str:
    """Top-level summary of every bundled preset category. Start here."""
    out: dict[str, Any] = {"presets_dir": str(presets_dir())}
    for cat in ("palettes", "dither", "tiles", "animation", "reference"):
        try:
            m = load_manifest(cat)
        except Exception:
            continue
        n_entries = len(m.get("entries") or m.get("topics") or [])
        out[cat] = {
            "count": n_entries,
            "description": m.get("description", "").strip()[:200],
        }
        if "curated_sets" in m:
            out[cat]["curated_sets"] = list(m["curated_sets"].keys())
    return json.dumps(out, indent=2)
