"""Generate shading ramps from a base color (HSL stepping with hue/saturation drift)."""
import colorsys
import json
import os

from .. import mcp
from .palette_extract import _write_gpl


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"Bad hex: {h}")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"


@mcp.tool()
async def generate_palette_ramp(
    base_hex: str,
    steps: int = 5,
    base_position: int = 2,
    lightness_step: float = 0.12,
    hue_shift: float = 4.0,
    saturation_drop: float = 0.0,
    output_gpl: str | None = None,
    palette_name: str = "ramp",
) -> str:
    """Generate a shading ramp from a base color (HLS stepping + hue/saturation drift).

    Pixel-art convention: shadows skew cooler (hue rotates negative),
    highlights skew warmer (hue rotates positive). Saturation usually
    drops slightly at the extremes (cinematic lighting feel).

    Args:
        base_hex: Mid-tone of the ramp, #RRGGBB.
        steps: Total ramp size (1 to 32).
        base_position: 0-indexed slot of the base. E.g. steps=5 base=2
            yields [shadow2, shadow1, BASE, highlight1, highlight2].
        lightness_step: Lightness delta between adjacent steps (0.0 to 0.3).
        hue_shift: Hue degrees shifted per step. Positive = warmer toward
            highlights, cooler toward shadows.
        saturation_drop: Per-step saturation reduction at the extremes
            (0.0 to 0.1). Recommended 0.02 to 0.05.
        output_gpl: Optional .gpl output path.
        palette_name: Header name for the .gpl file.

    Returns:
        JSON with 'colors' (dark to light) and 'gpl_path'.
    """
    if not 1 <= steps <= 32:
        return "steps must be between 1 and 32"
    if not 0 <= base_position < steps:
        return f"base_position must be in [0, {steps})"

    try:
        r, g, b = _hex_to_rgb(base_hex)
    except Exception as e:
        return f"Bad base_hex: {e}"

    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)

    colors: list[tuple[int, int, int]] = []
    for i in range(steps):
        offset = i - base_position
        new_l = max(0.0, min(1.0, l + offset * lightness_step))
        new_h = (h + offset * (hue_shift / 360.0)) % 1.0
        new_s = max(0.0, min(1.0, s - abs(offset) * saturation_drop))
        nr, ng, nb = colorsys.hls_to_rgb(new_h, new_l, new_s)
        colors.append((round(nr * 255), round(ng * 255), round(nb * 255)))

    hex_list = [_rgb_to_hex(*c) for c in colors]

    gpl_path = None
    if output_gpl:
        try:
            parent = os.path.dirname(os.path.abspath(output_gpl))
            if parent:
                os.makedirs(parent, exist_ok=True)
            _write_gpl(output_gpl, palette_name, colors)
            gpl_path = os.path.abspath(output_gpl)
        except Exception as e:
            return f"Ramp generated but failed to write GPL: {e}"

    return json.dumps({"colors": hex_list, "gpl_path": gpl_path})
