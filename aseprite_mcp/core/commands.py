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
            return success, output
        finally:
            os.remove(script_path)
