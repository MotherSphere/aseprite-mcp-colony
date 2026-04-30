---
name: aseprite-presets-tour
description: Tour and recipes for the aseprite-mcp-colony preset library (palettes, dither, tile templates, animation cycles, reference docs). Use when starting a new pixel-art asset and you want a known-good launchpad instead of guessing palette/structure/timing.
---

# aseprite-mcp-colony preset library tour

The MCP ships a curated catalog of creative presets so you stop blank-canvas guessing.
Five categories, all backed by tools that begin with `list_`, `get_`, `apply_` or `instantiate_`.

## TL;DR start

Call `presets_overview` to see counts and curated bundles for every category.

## Category 1: Palettes (45 .gpl files)

Bundled from Lospec with creator credit preserved.

- `list_preset_palettes(curated_set="dark_fantasy_vn")` -> 12 palettes Slynyrd / Bestiarium / GameBoy moody
- `list_preset_palettes(curated_set="vn_full_color")` -> 6 large painterly palettes (Apollo, Resurrect-64, AAP-Splendor128, Aurora...)
- `list_preset_palettes(curated_set="starter_kit_small")` -> 5 classics (PICO-8, Sweetie 16, EDG32, DB16, Arne 16)
- `list_preset_palettes(curated_set="gameboy_likes")` -> 7 4-color GB-style palettes
- `list_preset_palettes(tag="dark-fantasy")` / `tag="moody"` / `tag="warm"` -> filter by tag
- `get_preset_palette_info(slug)` -> creator, source URL, color count, best_for, abs file path
- `apply_preset_palette(slug, target_aseprite)` -> set the active sprite's palette in-place

For Project VN dark fantasy work, the top picks are:
- `steam-lords` (Slynyrd, 16 col) - the most "Bloodborne"
- `lost-century` (16 col) - parchment/Bestiarium look, top fit for grimoire UI
- `nyx8` (8 col) - moonlit dungeons in 8 colors flat
- `dawnbringer-32` (32) - all-purpose moody fantasy classic
- `apollo` (46) or `resurrect-64` (64) when more nuance is needed

## Category 2: Dither (14 binary patterns + 6 perceptual kernels)

Two complementary catalogs. Hand-painted vs perceptual.

- `list_dither_patterns()` -> binary 0/1 tile patterns (checker, hatch, brick, scales, stipple, waves)
- `list_dither_kernels()` -> Bayer 2x2/4x4/8x8 + Floyd-Steinberg, JJN, Stucki, Burkes, Sierra-Lite, Atkinson
- `get_dither_guidance()` -> decision tree + recipes (smooth skin, AI image conversion, scanlines, water, grimoire engraving)

Quick choice: external image -> `atkinson`. 50% mix area painted by hand -> `checker_2`. Retro low-res grain -> `bayer_4x4`.

## Category 3: Tile templates (12 structures)

Each template = 16x16 skeleton with GUIDE layer (drawing rules), pre-filled mortar/seam, and a multi-layer paint-ready stack.

- `list_tile_templates()` -> brick_7-1, cobble_irregular, stone_wall_block, plank_horizontal, grass_blob, dirt_speckle, sand_dune, ice_block, roof_shingle, metal_grate, water_anim_4f, lava_anim_4f
- `list_tile_templates(tag="floor")` / `"wall"` / `"animated"` / `"dark-fantasy"`
- `get_tile_template_info(slug)` -> full canvas + layer + guide pixel definition
- `instantiate_tile_template(slug, dest_path)` -> creates a fresh .aseprite ready to paint, with the GUIDE layer hidden but present, mortar pre-painted at canonical positions, plus 3-5 named paint layers.

The output also returns `palette_tags_recommended` and `color_hint_swatches` you can pair with `apply_preset_palette` for instant on-style.

## Category 4: Animation cycles (24 presets, 5 curated bundles)

Each cycle = (frame_count, durations_ms, key_poses, loop_type, tag_role).

- `list_animation_presets(curated_set="hero_complete")` -> idle_wait_8f, walk_8f, run_6f, attack_swing_6f, cast_4f, hurt_3f, death_6f, dodge_3f, jump_5f, victory_4f
- `list_animation_presets(curated_set="minor_enemy")` -> minimal NES-era set (5 cycles)
- `list_animation_presets(curated_set="boss")` -> wait/walk/attack/channel/hurt/death/spawn (7 cycles)
- `list_animation_presets(curated_set="npc_dialog")` -> idle/talk/blink (3 cycles)
- `list_animation_presets(curated_set="jrpg_classic")` -> SNES JRPG set (7 cycles)
- `get_animation_preset_info(slug)` -> full poses + durations + recommended_for
- `apply_animation_preset(slug, target_aseprite)` -> appends frames + tag + durations to existing sprite
- `instantiate_animation_preset(slug, dest_path, w, h)` -> new sprite pre-rigged with the cycle

## Category 5: Reference knowledge (6 topics)

Structured JSON, designed to be consumed by both Claude and tools:

- `list_reference_topics()` -> index
- `get_reference("pixel_art_principles")` -> hue shift, jaggies, banding, AA clusters, edge bevels, process order, common mistakes
- `get_reference("sprite_size_conventions")` -> tile/character/portrait/UI sizes per era, with Project VN specific recommendations
- `get_reference("color_theory")` -> harmonies, hue shift table, temperature, narrative color associations (dark fantasy specific)
- `get_reference("easing_curves")` -> 25 Penner functions with pixel-art minimum frame counts and tween recipes
- `get_reference("dither_guidance")` -> mirror of `get_dither_guidance`
- `get_reference("animation_principles")` -> 12 Disney principles adapted to low-res pixel art, frame economy, shape keys, hold frames

Read these BEFORE drawing - they shortcut most common mistakes.

## Recipe: new dark-fantasy floor tile from scratch

```
1. instantiate_tile_template("brick_7-1", "tilesets/dungeon/floor_basalt.aseprite")
   -> returns palette_tags_recommended=["dark-fantasy", "moody"]
2. apply_preset_palette("steam-lords", "tilesets/dungeon/floor_basalt.aseprite")
3. (optional) get_reference("pixel_art_principles") to refresh hue shift / clustering rules
4. Paint the "stone" layer in Aseprite (live mode shows changes instantly)
5. ensure_layers_present + audit_animation when ready
```

## Recipe: rig a hero character with full anim set

```
1. create_canvas(32, 32, "characters/hero.aseprite")
2. apply_preset_palette("apollo", "characters/hero.aseprite")
3. for slug in list_animation_presets(curated_set="hero_complete"):
       apply_animation_preset(slug, "characters/hero.aseprite")
   (creates 10 tags spanning 64 total frames, all with proper durations)
4. Now paint each tag's frames per the cycle's key_poses.
```

## Recipe: convert AI / photo image to pixel art on a project palette

```
1. get_dither_guidance() -> picks atkinson kernel + 32-color palette
2. get_preset_palette_info("steam-lords") -> abs_file path
3. quantize_image_to_palette(input_path, output_path,
       gpl_path="<abs_file>", dither="floyd_steinberg")
4. Optionally feed result through pyxelate first for downsample, see session_resume notes.
```
