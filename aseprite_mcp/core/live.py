"""Live bridge to Aseprite GUI via WebSocket.

The MCP process hosts a WebSocket server in a dedicated thread (own
asyncio loop) so synchronous tool code can dispatch Lua scripts via
`run_coroutine_threadsafe`. The Aseprite Lua extension connects as a
client when the editor opens. While that connection is alive, every
Lua script that would otherwise run via `aseprite --batch --script`
is sent over the socket and executed inside the live editor instead.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
from typing import Any

try:
    from websockets.asyncio.server import serve
    from websockets.exceptions import ConnectionClosed
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

logger = logging.getLogger("aseprite_mcp.live")

DEFAULT_PORT = int(os.getenv("ASEPRITE_MCP_PORT", "12700"))
DEFAULT_TIMEOUT = float(os.getenv("ASEPRITE_MCP_WS_TIMEOUT", "10.0"))


class LiveBridge:
    """WebSocket bridge to a single connected Aseprite editor."""

    def __init__(self, port: int = DEFAULT_PORT) -> None:
        self.port = port
        self._connection: Any = None
        self._lock: asyncio.Lock | None = None
        self._next_id = 1
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()

    @property
    def connected(self) -> bool:
        return self._connection is not None

    def start_in_thread(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        if not HAS_WEBSOCKETS:
            logger.warning("websockets package missing, live bridge disabled")
            return
        self._thread = threading.Thread(
            target=self._thread_main, name="aseprite-mcp-bridge", daemon=True
        )
        self._thread.start()
        self._ready.wait(timeout=2.0)

    def _thread_main(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._lock = asyncio.Lock()
        self._ready.set()
        try:
            loop.run_until_complete(self._serve())
        except Exception as e:
            logger.warning("live bridge stopped: %s", e)
        finally:
            loop.close()

    async def _serve(self) -> None:
        try:
            async with serve(self._handle_client, "127.0.0.1", self.port):
                logger.info("live bridge listening on ws://127.0.0.1:%d", self.port)
                await asyncio.Future()
        except OSError as e:
            logger.warning("could not bind live bridge port %d: %s", self.port, e)

    async def _handle_client(self, websocket: Any) -> None:
        if self._connection is not None:
            try:
                await websocket.close(reason="another editor already connected")
            except Exception:
                pass
            return

        self._connection = websocket
        peer = getattr(websocket, "remote_address", "unknown")
        logger.info("aseprite extension connected from %s", peer)
        try:
            async for _msg in websocket:
                pass
        except ConnectionClosed:
            pass
        finally:
            if self._connection is websocket:
                self._connection = None
            logger.info("aseprite extension disconnected (%s)", peer)

    async def _call(
        self,
        method: str,
        params: dict[str, Any],
        timeout: float,
    ) -> tuple[bool, Any]:
        ws = self._connection
        if ws is None or self._lock is None:
            return False, "no live connection"

        async with self._lock:
            req_id = self._next_id
            self._next_id += 1
            request = json.dumps(
                {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
            )
            try:
                await ws.send(request)
                raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
            except (ConnectionClosed, asyncio.TimeoutError, OSError) as e:
                if self._connection is ws:
                    self._connection = None
                return False, f"live transport error: {e}"

            try:
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                return False, f"live response parse error: {e}"

            if "error" in data:
                err = data["error"]
                msg = (
                    err.get("message", "unknown error") if isinstance(err, dict) else str(err)
                )
                return False, f"live error: {msg}"
            return True, data.get("result")

    def execute_lua_sync(
        self,
        code: str,
        filename: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> tuple[bool, str] | None:
        """Run a Lua script in the live editor from a synchronous caller.

        Returns (True, output) on success, (False, message) when the live
        editor is connected but the call failed, or None if no editor is
        connected (caller should fall back to batch).
        """
        if self._loop is None or not self.connected:
            return None
        future = asyncio.run_coroutine_threadsafe(
            self._call(
                "execute_lua",
                {"code": code, "filename": filename},
                timeout,
            ),
            self._loop,
        )
        try:
            ok, result = future.result(timeout=timeout + 5.0)
        except Exception as e:
            return False, f"live call failed: {e}"

        if not ok:
            return False, str(result)
        if isinstance(result, dict):
            return True, str(result.get("output", ""))
        return True, str(result or "")


bridge = LiveBridge()
