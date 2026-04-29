# aseprite-mcp-colony

MCP server piloting Aseprite for the Colony / Project VN sprite pipeline.

Forked from [diivi/aseprite-mcp](https://github.com/diivi/aseprite-mcp) (MIT). License preserved in `LICENSE`. This fork diverges to fit the Colony art workflow: dark fantasy palettes, Bevy-friendly sprite-sheet exports, batch ops on `.aseprite` sources stored under `/mnt/Jeux/Project/`.

## Status

Active. Upstream tools intact. Colony-specific additions live alongside in `aseprite_mcp/tools/`. Bundled as a Claude Code plugin with skills.

## Colony additions

| Tool | Purpose |
|------|---------|
| `extract_palette_from_image` | Quantize a reference image (Bloodborne/Stalker/grimdark screenshot, etc.) into a coherent palette. Outputs hex list + optional `.gpl` (Aseprite-compatible) and can apply directly to a target sprite. Alpha-aware. |
| `apply_gpl_palette` | Load a `.gpl` and apply it to a target `.aseprite`. |
| `quantize_image_to_palette` | Snap an arbitrary image (PNG/JPG, e.g. SpriteCook output) onto a fixed palette via nearest-color match. Optional Floyd-Steinberg dither. |
| `generate_palette_ramp` | Generate a shading ramp from a base color via HLS stepping with optional hue shift (warm highlights, cool shadows) and saturation drop at extremes. Slynyrd-style. |
| `export_bevy_atlas` | Export a uniform-grid sprite-sheet PNG plus a Bevy 0.18 `TextureAtlas` JSON with frame durations and animation tags. |

## Skills

| Skill | When |
|------|---------|
| `aseprite-palette-coherence` | Workflow for keeping new art coherent with a reference palette (extract -> apply -> quantize). |
| `aseprite-bevy-pipeline` | Workflow for shipping Aseprite sprites to a Bevy game with proper atlas JSON. |

## Requirements

- Aseprite (any install: Steam, AUR, source). Set `ASEPRITE_PATH` if not on `PATH`.
- Python 3.13+
- `uv`

## Install as a Claude Code plugin (recommended)

```bash
claude plugin marketplace add /path/to/aseprite-mcp-colony
claude plugin install aseprite-mcp-colony@aseprite-mcp-colony
```

The plugin auto-registers the MCP server and bundles the skills. Set `ASEPRITE_PATH` in your shell or in a project `.env` if Aseprite is not on `PATH`.

## Local install (without plugin)

```bash
uv sync
ASEPRITE_PATH=/mnt/Jeux/SteamLibrary/steamapps/common/Aseprite/aseprite \
  uv run -m aseprite_mcp
```

Or wire it up manually in your MCP config:

```json
{
  "mcpServers": {
    "aseprite": {
      "command": "/usr/bin/uv",
      "args": ["--directory", "/path/to/aseprite-mcp-colony", "run", "-m", "aseprite_mcp"],
      "env": {
        "ASEPRITE_PATH": "/path/to/aseprite"
      }
    }
  }
}
```

## Syncing upstream

```bash
git fetch upstream
git merge upstream/main
```

## License

MIT. See `LICENSE`.
