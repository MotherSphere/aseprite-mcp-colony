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

## Live mode

Every tool transparently switches between two execution modes:

- **Live**: when an Aseprite editor is open and the bundled extension is connected, every Lua script runs inside that editor. The artist sees changes appear in real time and can iterate alongside the AI.
- **Batch**: when no editor is connected, scripts run via `aseprite --batch --script` (headless). Same tools, no UI.

The MCP process hosts a WebSocket server on `127.0.0.1:12700` (override with `ASEPRITE_MCP_PORT`). The Aseprite extension under `extension/aseprite-mcp-colony/` is the WebSocket client and auto-reconnects every 5s.

To install the live-mode extension:

```bash
cp -r extension/aseprite-mcp-colony ~/.config/aseprite/extensions/
```

Then restart Aseprite. On the first connection it will prompt for permission to open `ws://127.0.0.1:12700`. Accept (and tick "do not ask again" if you prefer). The Aseprite `Edit > MCP Bridge: Status` command shows the current connection state.

Tip: Aseprite caches extension code at startup, so any change to `extension.lua` requires a full Aseprite restart.

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
