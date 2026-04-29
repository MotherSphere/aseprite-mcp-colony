"""Palette extraction from reference images via Pillow median-cut quantization."""
import json
import os
from typing import Literal

from PIL import Image

from ..core.commands import AsepriteCommand
from .. import mcp


def _luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _hue(rgb: tuple[int, int, int]) -> float:
    r, g, b = (c / 255.0 for c in rgb)
    mx, mn = max(r, g, b), min(r, g, b)
    d = mx - mn
    if d == 0:
        return 0.0
    if mx == r:
        h = ((g - b) / d) % 6
    elif mx == g:
        h = (b - r) / d + 2
    else:
        h = (r - g) / d + 4
    return h * 60.0


def _quantize_palette(
    image_path: str,
    num_colors: int,
    alpha_threshold: int = 16,
) -> list[tuple[int, int, int]]:
    img = Image.open(image_path)

    max_dim = 512
    if max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim))

    if img.mode == "RGBA":
        rgba = img.convert("RGBA")
        pixels = [(r, g, b) for r, g, b, a in rgba.getdata() if a >= alpha_threshold]
        if not pixels:
            raise ValueError("Image has no opaque pixels above alpha threshold")
        flat = Image.new("RGB", (len(pixels), 1))
        flat.putdata(pixels)
        img = flat
    elif img.mode != "RGB":
        img = img.convert("RGB")

    quantized = img.quantize(
        colors=num_colors,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE,
    )
    palette_bytes = quantized.getpalette() or []

    colors: list[tuple[int, int, int]] = []
    actual_count = min(num_colors, len(palette_bytes) // 3)
    for i in range(actual_count):
        r, g, b = palette_bytes[i * 3 : i * 3 + 3]
        colors.append((int(r), int(g), int(b)))

    return colors


def _write_gpl(path: str, name: str, colors: list[tuple[int, int, int]]) -> None:
    lines = [
        "GIMP Palette",
        f"Name: {name}",
        "Columns: 4",
        "#",
    ]
    for r, g, b in colors:
        lines.append(f"{r:3d} {g:3d} {b:3d}\t#{r:02X}{g:02X}{b:02X}")

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


@mcp.tool()
async def extract_palette_from_image(
    image_path: str,
    num_colors: int = 16,
    output_gpl: str | None = None,
    palette_name: str = "extracted",
    sort_by: Literal["luminance", "hue", "none"] = "luminance",
    target_aseprite: str | None = None,
) -> str:
    """Extract a quantized palette from a reference image.

    Captures a coherent palette from a Bloodborne / Stalker / grimdark
    screenshot (or any reference) and optionally applies it to a sprite
    so generated art stays in the same color space.

    Args:
        image_path: Path to the source reference image (PNG/JPG/etc).
        num_colors: Palette size (2 to 256, default 16).
        output_gpl: Optional path to write a GIMP .gpl palette file
            (Aseprite-compatible, double-clickable to load).
        palette_name: Display name stored in the .gpl header.
        sort_by: 'luminance' (dark to light), 'hue', or 'none'.
        target_aseprite: Optional .aseprite file path. If provided,
            the palette is also applied to that sprite right away.

    Returns:
        JSON string with 'colors' (#RRGGBB list), 'gpl_path', and 'applied_to'.
    """
    if not os.path.exists(image_path):
        return f"Image {image_path} not found"
    if num_colors < 2 or num_colors > 256:
        return "num_colors must be between 2 and 256"

    try:
        colors = _quantize_palette(image_path, num_colors)
    except Exception as e:
        return f"Failed to quantize palette: {e}"

    if sort_by == "luminance":
        colors.sort(key=_luminance)
    elif sort_by == "hue":
        colors.sort(key=lambda c: (_hue(c), _luminance(c)))

    hex_list = [f"#{r:02X}{g:02X}{b:02X}" for r, g, b in colors]

    gpl_path = None
    if output_gpl:
        try:
            parent = os.path.dirname(os.path.abspath(output_gpl))
            if parent:
                os.makedirs(parent, exist_ok=True)
            _write_gpl(output_gpl, palette_name, colors)
            gpl_path = os.path.abspath(output_gpl)
        except Exception as e:
            return f"Quantized OK but failed to write GPL: {e}"

    applied_to = None
    if target_aseprite:
        if not os.path.exists(target_aseprite):
            return f"target_aseprite {target_aseprite} not found"
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
        success, output = AsepriteCommand.execute_lua_script(script, target_aseprite)
        if not success:
            return f"Quantized OK but failed to apply to {target_aseprite}: {output}"
        applied_to = target_aseprite

    return json.dumps(
        {
            "colors": hex_list,
            "gpl_path": gpl_path,
            "applied_to": applied_to,
        }
    )
