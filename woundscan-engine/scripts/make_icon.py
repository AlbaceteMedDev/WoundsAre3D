"""Generate the WoundScan app icon from the project's wordmark logo.

The source `WoundScan Updated Logo.png` sits on a near-opaque white
background — dropping it onto an iOS rounded-rect canvas as-is leaves
a "rectangle in a circle" with a white border. To avoid that we:

  1. Load the wordmark.
  2. Use its luminance as an alpha mask so the wordmark + topographic
     wound mesh become a silhouette on transparent.
  3. Recolor the silhouette: dark / grey pixels → white (matches the
     "Wound" wordmark), cyan-leaning pixels → cyan (preserves "Scan"
     and the cyan accents from the original).
  4. Composite that silhouette onto a 1024×1024 dark navy gradient
     with a soft cyan halo behind the mark, bleeding edge-to-edge so
     iOS / favicon corner-rounding looks clean.

The result is the same logo, on the brand-correct dark background,
without any white padding. Re-run the script after editing the source
PNG to regenerate the icon.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageFilter

S = 1024
LOGO = Path("/Users/gabea/WoundsAre3D/WoundScan Updated Logo.png")


def lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (
        round(a[0] + (b[0] - a[0]) * t),
        round(a[1] + (b[1] - a[1]) * t),
        round(a[2] + (b[2] - a[2]) * t),
    )


def background() -> Image.Image:
    """Deep navy gradient + soft cyan halo, fully opaque, bleeds to edge."""
    bg = Image.new("RGB", (S, S))
    px = bg.load()
    top = (10, 26, 48)
    bot = (3, 6, 13)
    for y in range(S):
        t = y / (S - 1)
        col = lerp(top, bot, t)
        for x in range(S):
            px[x, y] = col

    halo = Image.new("RGB", (S, S), (0, 0, 0))
    hpx = halo.load()
    cx, cy = S // 2, S // 2
    R = S * 0.55
    for y in range(S):
        for x in range(S):
            dx, dy = x - cx, y - cy
            d = (dx * dx + dy * dy) ** 0.5
            if d > R:
                continue
            t = (1 - d / R) ** 2
            hpx[x, y] = lerp((0, 0, 0), (10, 90, 120), t)
    halo = halo.filter(ImageFilter.GaussianBlur(45))
    return ImageChops.add(bg, halo)


def silhouette_from_logo(path: Path) -> Image.Image:
    """Convert the wordmark into a white/cyan silhouette on transparent.

    Darkness is used as opacity: the near-white background of the source
    becomes transparent, the black "Wound" wordmark and the topographic
    mesh become opaque white. Cyan-leaning pixels (the "Scan" wordmark
    and the corner accents) are preserved as cyan.
    """
    src = Image.open(path).convert("RGBA")
    sw, sh = src.size
    out = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    src_px = src.load()
    out_px = out.load()
    for y in range(sh):
        for x in range(sw):
            r, g, b, a = src_px[x, y]
            if a == 0:
                continue
            min_rgb = min(r, g, b)
            alpha = 255 - min_rgb
            if alpha < 8:
                continue
            is_cyan = b > r + 25 and b >= g and (g - r) >= -10
            color = (34, 211, 238) if is_cyan else (245, 247, 250)
            out_px[x, y] = (color[0], color[1], color[2], alpha)
    return out


def build_icon(out_path: Path) -> None:
    bg = background().convert("RGBA")

    sil = silhouette_from_logo(LOGO)
    sw, sh = sil.size
    target_w = int(S * 0.84)
    target_h = round(sh * target_w / sw)
    sil = sil.resize((target_w, target_h), Image.LANCZOS)

    px = (S - target_w) // 2
    py = (S - target_h) // 2
    bg.alpha_composite(sil, dest=(px, py))

    bg.convert("RGB").save(out_path, "PNG", optimize=True)


if __name__ == "__main__":
    import sys

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/icon-1024.png")
    build_icon(out)
    print(f"wrote {out}")
