"""Diagnostic tool exposing the live-bridge connection state."""

from ..core.live import bridge
from .. import mcp


@mcp.tool()
async def bridge_status() -> str:
    """Report the live-bridge state and the mode of the last script run.

    Returns a one-line summary describing whether an Aseprite editor is
    connected to the MCP, what mode the most recent tool call used, and
    the WebSocket port the bridge is listening on.

    Useful when you want to check if your edits are landing in the live
    editor (visible immediately) or in a headless batch invocation.
    """
    connected = "connected" if bridge.connected else "disconnected"
    last_mode = bridge.last_mode or "none yet"
    return (
        f"bridge: {connected} on ws://127.0.0.1:{bridge.port} | "
        f"last_call: {last_mode}"
    )
