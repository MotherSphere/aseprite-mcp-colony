# aseprite-mcp-colony

MCP server piloting Aseprite for the Colony / Project VN sprite pipeline.

Forked from [diivi/aseprite-mcp](https://github.com/diivi/aseprite-mcp) (MIT). License preserved in `LICENSE`. This fork diverges to fit the Colony art workflow: dark fantasy palettes, Bevy-friendly sprite-sheet exports, batch ops on `.aseprite` sources stored under `/mnt/Jeux/Project/`.

## Status

Active. Upstream tools intact. Colony-specific additions live alongside in `aseprite_mcp/tools/`.

## Colony additions

| Tool | Purpose |
|------|---------|
| `extract_palette_from_image` | Quantize a reference image (Bloodborne/Stalker/grimdark screenshot, etc.) into a coherent palette. Outputs hex list + optional `.gpl` (Aseprite-compatible) and can apply directly to a target sprite. Alpha-aware: transparent pixels do not pollute the palette. |

## Requirements

- Aseprite (any install: Steam, AUR, source). Set `ASEPRITE_PATH` if not on `PATH`.
- Python 3.13+
- `uv`

## Local install

```bash
uv sync
ASEPRITE_PATH=/mnt/Jeux/SteamLibrary/steamapps/common/Aseprite/aseprite \
  uv run -m aseprite_mcp
```

## MCP client config

Drop into your Claude Code MCP config:

```json
{
  "mcpServers": {
    "aseprite": {
      "command": "/usr/bin/uv",
      "args": [
        "--directory",
        "/home/mothersphere/Documents/Repositories/aseprite-mcp-colony",
        "run",
        "-m",
        "aseprite_mcp"
      ],
      "env": {
        "ASEPRITE_PATH": "/mnt/Jeux/SteamLibrary/steamapps/common/Aseprite/aseprite"
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
