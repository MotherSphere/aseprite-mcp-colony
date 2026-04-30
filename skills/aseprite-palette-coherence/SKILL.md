---
name: aseprite-palette-coherence
description: Workflow for keeping Aseprite sprites visually coherent with a reference. Use when art needs to match an existing palette (Bloodborne / Stalker / dark fantasy ref), when forcing AI-generated images onto a project palette, or when generating shading ramps from a base color. Requires the aseprite-mcp-colony MCP server.
---

# Aseprite Palette Coherence

Use this when new art must match an existing color space.

## Pipeline

1. **Extract** a palette from a reference image:
   - `extract_palette_from_image(image_path, num_colors=16, output_gpl="...", sort_by="luminance")`
   - Returns hex list and writes a `.gpl` you can reuse.
   - Alpha-aware: transparent pixels do not pollute the palette.

   OR pick a bundled preset palette - 45 are shipped:
   - `list_preset_palettes(curated_set="dark_fantasy_vn")` -> 12 moody fits (Steam Lords, Lost Century, NYX8...)
   - `list_preset_palettes(curated_set="vn_full_color")` -> 6 painterly large palettes
   - `apply_preset_palette(slug, target_aseprite)` for direct application
   - `get_preset_palette_info(slug)` for the abs `.gpl` path to feed `quantize_image_to_palette`

2. **Apply** that palette to a target sprite:
   - `apply_gpl_palette(gpl_path, target_aseprite)` if you saved a `.gpl`.
   - `apply_preset_palette(slug, target_aseprite)` for a bundled preset.
   - Or `set_palette(filename, colors)` directly with a hex list.

3. **Snap** externally-generated art onto the palette:
   - `quantize_image_to_palette(image_path, output_path, gpl_path=...)` (or `palette=[...]`).
   - Each pixel is replaced by its nearest palette color.

4. **Generate ramps** for shading from a base color:
   - `generate_palette_ramp(base_hex, steps=5, base_position=2, hue_shift=4.0, saturation_drop=0.03)`.
   - Slynyrd-style: warm highlights, cool shadows, slight desaturation at extremes.

## Defaults that work for dark fantasy

- 16 colors is the sweet spot. 8 if minimalist.
- Sort by `"luminance"` so the palette reads dark to light in Aseprite.
- Ramps: `lightness_step=0.10` to `0.15`, `hue_shift=3` to `5`, `saturation_drop=0.02` to `0.05`.
- For pixel art, always `dither="none"` when quantizing; only use `floyd_steinberg` for smooth gradients.

## Where to save palettes

- Project palettes go in the asset library, not in the repo.
- Suggested layout: `/mnt/Jeux/Project/Aseprite/palettes/<theme>/<name>.gpl`.

## Common gotchas

- "Image has no opaque pixels" when extracting: the source is fully transparent; pass an opaque ref or lower `alpha_threshold`.
- "PIL palette mode supports at most 256 colors": cap palette size at 256 when quantizing.
- Need exactly N colors but the source has fewer distinct ones? PIL's median-cut returns at most as many as it finds. Either provide a richer source or accept the smaller output.
