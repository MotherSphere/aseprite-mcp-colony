import logging

from . import mcp
from .core.live import bridge
from .tools import *  # noqa: F401, F403


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    bridge.start_in_thread()
    mcp.run(transport='stdio')
