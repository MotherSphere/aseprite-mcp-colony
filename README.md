# aseprite-mcp-colony

MCP server piloting Aseprite for the Colony / Project VN sprite pipeline.

Forked from [diivi/aseprite-mcp](https://github.com/diivi/aseprite-mcp) (MIT). License preserved in `LICENSE`. This fork diverges to fit the Colony art workflow: dark fantasy palettes, Bevy-friendly sprite-sheet exports, batch ops on `.aseprite` sources stored under `/mnt/Jeux/Project/`.

## Status

Bootstrap. Upstream features as-is for now; Colony-specific additions land in `aseprite_mcp/colony/` (planned).

## Requirements

- Aseprite (any install — Steam, AUR, source). Set `ASEPRITE_PATH` if not on `PATH`.
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
