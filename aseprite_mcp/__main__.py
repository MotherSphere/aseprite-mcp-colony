import logging

from . import mcp
from .tools import *  # noqa: F401, F403
from .core.live import bridge as live_bridge


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    live_bridge.start_in_thread()
    mcp.run(transport='stdio')
