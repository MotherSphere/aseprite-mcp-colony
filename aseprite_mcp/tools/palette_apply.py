"""Apply external palettes (.gpl) and snap arbitrary images onto a target palette."""
import json
import os
import re
from typing import Literal

from PIL import Image

from ..core.commands import AsepriteCommand
from .. import mcp


_HEX_RE = re.compile(r"#?([0-9a-fA-F]{6})")
_RGB_LINE = re.compile(r"^\s*(\d{1,3})\s+(\d{1,3})\s+(\d{1,3})(?:\s+|\t|$)")


def _parse_gpl(path: str) -> list[tuple[int, int, int]]:
    colors: list[tuple[int, int, int]] = []
    with open(path) as f:
        first = f.readline().strip()
        if not first.startswith("GIMP Palette"):
            raise ValueError("Not a GIMP Palette (.gpl) file")
        for line in f:
            line = line.split("#", 1)[0]
            line = line.rstrip("\n")
            if not line.strip():
                continue
            if line.lstrip().startswith(("Name:", "Columns:")):
                continue
            m = _RGB_LINE.match(line)
            if not m:
                continue
            r, g, b = (int(x) for x in m.groups())
            if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255:
                colors.append((r, g, b))
    if not colors:
        raise ValueError("No colors parsed from .gpl")
    return colors


def _parse_hex_list(values: list[str]) -> list[tuple[int, int, int]]:
    out: list[tuple[int, int, int]] = []
    for v in values:
        m = _HEX_RE.fullmatch(v.strip())
        if not m:
            raise ValueError(f"Bad hex color: {v}")
        h = m.group(1)
        out.append((int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)))
    return out


def _apply_palette_lua(filename: str, colors: list[tuple[int, int, int]]) -> tuple[bool, str]:
    palette_entries = "\n".join(
        f"    pal:setColor({i}, Color({r}, {g}, {b}))"
        for i, (r, g, b) in enumerate(colors)
    )
    script = f"""
    local spr = app.activeSprite
    if not spr then return "No active sprite" end
    local pal = Palette({len(colors)})
{palette_entries}
    spr:setPalette(pal)
    spr:saveAs(spr.filename)
    return "Palette set"
    """
    return AsepriteCommand.execute_lua_script(script, filename)


@mcp.tool()
async def apply_gpl_palette(gpl_path: str, target_aseprite: str) -> str:
    """Apply a GIMP .gpl palette file to an .aseprite sprite.

    Args:
        gpl_path: Path to a .gpl palette file (e.g. produced by extract_palette_from_image).
        target_aseprite: Path to the .aseprite file to modify in place.

    Returns:
        JSON with applied color count and target path.
    """
    if not os.path.exists(gpl_path):
        return f"GPL file {gpl_path} not found"
    if not os.path.exists(target_aseprite):
        return f"target_aseprite {target_aseprite} not found"
    try:
        colors = _parse_gpl(gpl_path)
    except Exception as e:
        return f"Failed to parse GPL: {e}"

    success, output = _apply_palette_lua(target_aseprite, colors)
    if not success:
        return f"Failed to apply palette: {output}"
    return json.dumps({"applied_to": target_aseprite, "color_count": len(colors)})


@mcp.tool()
async def quantize_image_to_palette(
    image_path: str,
    output_path: str,
    palette: list[str] | None = None,
    gpl_path: str | None = None,
    dither: Literal["none", "floyd_steinberg"] = "none",
) -> str:
    """Snap an arbitrary image (PNG/JPG, e.g. SpriteCook output) onto a fixed palette.

    Each pixel is replaced by its nearest color in the supplied palette.
    Useful for forcing externally-generated art (AI, screenshots, brushes)
    to obey a project palette so it stays visually coherent.

    Args:
        image_path: Source image (PNG/JPG/etc).
        output_path: Output path (PNG recommended).
        palette: List of #RRGGBB hex strings. Mutually exclusive with gpl_path.
        gpl_path: Path to a .gpl palette file. Mutually exclusive with palette.
        dither: 'none' for crisp pixel-art look, 'floyd_steinberg' for smoother gradients.

    Returns:
        JSON with output path, palette size, and pixel count converted.
    """
    if not os.path.exists(image_path):
        return f"Image {image_path} not found"
    if (palette is None) == (gpl_path is None):
        return "Provide exactly one of: palette (hex list) or gpl_path"

    try:
        if palette is not None:
            colors = _parse_hex_list(palette)
        else:
            assert gpl_path is not None
            if not os.path.exists(gpl_path):
                return f"GPL file {gpl_path} not found"
            colors = _parse_gpl(gpl_path)
    except Exception as e:
        return f"Failed to load palette: {e}"

    if not colors:
        return "Palette is empty"
    if len(colors) > 256:
        return "PIL palette mode supports at most 256 colors"

    src = Image.open(image_path)
    has_alpha = src.mode in ("RGBA", "LA") or "transparency" in src.info
    rgba = src.convert("RGBA") if has_alpha else None

    rgb_src = src.convert("RGB")

    palette_image = Image.new("P", (1, 1))
    flat = []
    for r, g, b in colors:
        flat.extend([r, g, b])
    flat.extend([0] * (768 - len(flat)))
    palette_image.putpalette(flat)

    dither_mode = (
        Image.Dither.FLOYDSTEINBERG if dither == "floyd_steinberg" else Image.Dither.NONE
    )
    quantized = rgb_src.quantize(palette=palette_image, dither=dither_mode)
    out = quantized.convert("RGB")

    if rgba is not None:
        alpha = rgba.split()[-1]
        out = out.convert("RGBA")
        out.putalpha(alpha)

    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    out.save(output_path)

    return json.dumps(
        {
            "output_path": os.path.abspath(output_path),
            "palette_size": len(colors),
            "size": list(out.size),
            "alpha_preserved": has_alpha,
        }
    )
