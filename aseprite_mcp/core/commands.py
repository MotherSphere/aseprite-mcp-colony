import subprocess
import tempfile
import os
import dotenv

from .live import bridge

_ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
dotenv.load_dotenv(dotenv_path=_ENV_PATH)


def lua_escape(s: str) -> str:
    """Escape a string for safe embedding inside a Lua double-quoted string literal."""
    return (
        s.replace("\\", "\\\\")
         .replace('"', '\\"')
         .replace("\n", "\\n")
         .replace("\r", "\\r")
         .replace("\0", "\\0")
    )


def reject_traversal(path: str) -> str | None:
    """Reject parent-directory traversal in a user-supplied path.

    Returns an error message string when the path contains a `..`
    component, or None when the path looks safe.

    The check works on normalized path components, so it does not
    false-positive on filenames like `foo..bar.aseprite` (the previous
    `'..' in path` substring check did). Absolute paths and tilde
    expansion are not rejected here: this function targets traversal
    only, not access scoping.
    """
    parts = os.path.normpath(path).replace("\\", "/").split("/")
    if ".." in parts:
        return "Invalid filename: parent directory traversal not allowed"
    return None


class AsepriteCommand:
    """Helper class for running Aseprite commands."""

    @staticmethod
    def run_command(args):
        """Run an Aseprite command with proper error handling."""
        try:
            cmd = [os.getenv('ASEPRITE_PATH', 'aseprite')] + args
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, e.stderr

    @staticmethod
    def execute_lua_script(script_content, filename=None):
        """Execute a Lua script in Aseprite.

        Tries the live bridge first (running editor) and falls back to a
        headless `aseprite --batch --script` invocation if no editor is
        connected or the live call fails.
        """
        live = bridge.execute_lua_sync(script_content, filename)
        if live is not None:
            bridge.last_mode = "live"
            return live

        with tempfile.NamedTemporaryFile(suffix='.lua', delete=False, mode='w') as tmp:
            tmp.write(script_content)
            script_path = tmp.name

        try:
            args = ["--batch"]
            if filename and os.path.exists(filename):
                args.append(filename)
            args.extend(["--script", script_path])

            success, output = AsepriteCommand.run_command(args)
            bridge.last_mode = "batch"
            return success, output
        finally:
            os.remove(script_path)
