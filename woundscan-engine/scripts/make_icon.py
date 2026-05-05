"""Generate the WoundScan app icon.

Design:
  - 1024×1024 square that bleeds edge-to-edge (iOS rounds the corners
    itself; we don't need to round them or pad with white).
  - Dark navy gradient background to match albacetemeddev.com / the
    portal's dark theme — recognisable next to the brand.
  - Center mark: a stylised topographical "wound" — concentric bands
    that read as a 3-D depth scan, the product's defining capability.
    The bands graduate from cyan (shallow) to deep red-orange (deepest)
    so the icon communicates "wound depth measurement" at any size.
  - Subtle outer cyan halo ties it to the WoundScan logo's accent.
"""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFilter, ImageFont

S = 1024  # final size


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def background() -> Image.Image:
    """Deep navy gradient with a soft cyan halo behind the mark."""
    img = Image.new("RGB", (S, S), (5, 7, 12))
    px = img.load()
    top = (10, 26, 48)        # ink with a hint of blue
    bot = (3, 6, 13)          # near-black
    for y in range(S):
        t = y / (S - 1)
        col = lerp(top, bot, t)
        for x in range(S):
            px[x, y] = col

    # radial cyan glow behind the mark
    halo = Image.new("RGB", (S, S), (0, 0, 0))
    halo_px = halo.load()
    cx, cy = S // 2, int(S * 0.5)
    R = S * 0.55
    for y in range(S):
        for x in range(S):
            dx = x - cx
            dy = y - cy
            d = (dx * dx + dy * dy) ** 0.5
            if d > R:
                continue
            t = 1 - d / R
            t = t * t  # softer falloff
            col = lerp((0, 0, 0), (10, 80, 110), t)
            halo_px[x, y] = col
    halo = halo.filter(ImageFilter.GaussianBlur(40))

    return Image.eval(
        Image.merge("RGB", [
            ImageChops_add(img.split()[0], halo.split()[0]),
            ImageChops_add(img.split()[1], halo.split()[1]),
            ImageChops_add(img.split()[2], halo.split()[2]),
        ]),
        lambda v: min(255, v),
    )


def ImageChops_add(a, b):
    from PIL import ImageChops
    return ImageChops.add(a, b)


def topographic_mark(img: Image.Image) -> None:
    """Draw a stylised wound-depth topographical mark, centred."""
    draw = ImageDraw.Draw(img, "RGBA")
    cx, cy = S // 2, int(S * 0.50)

    # Concentric depth rings — outer = shallow (cyan), inner = deep (red-orange)
    rings = [
        # (rx, ry, color, alpha, width)
        (340, 220, (34, 211, 238),  120, 6),   # cyan-300
        (300, 192, (56, 189, 248),  140, 6),   # sky-400
        (256, 162, (125, 211, 252), 170, 7),   # sky-300 brighter
        (212, 132, (217, 119, 6),   210, 8),   # amber-600
        (168, 102, (220, 38, 38),   230, 9),   # red-600
        (124,  72, (185, 28, 28),   245, 10),  # red-700
        ( 80,  46, (127, 29, 29),   255, 12),  # red-900 / wound floor
    ]
    for rx, ry, rgb, alpha, w in rings:
        bbox = [cx - rx, cy - ry, cx + rx, cy + ry]
        draw.ellipse(bbox, outline=(*rgb, alpha), width=w)

    # Inner wound-floor fill (solid)
    draw.ellipse([cx - 70, cy - 38, cx + 70, cy + 38], fill=(127, 29, 29, 255))
    # Highlight on the floor
    draw.ellipse([cx - 50, cy - 30, cx + 30, cy - 5], fill=(170, 50, 50, 200))


def measurement_marks(img: Image.Image) -> None:
    """Tiny corner ticks to evoke a measurement frame, like the logo."""
    draw = ImageDraw.Draw(img, "RGBA")
    cyan = (34, 211, 238, 220)
    L = 70
    pad = 70
    w = 6
    # top-left corner bracket
    draw.line([(pad, pad), (pad + L, pad)], fill=cyan, width=w)
    draw.line([(pad, pad), (pad, pad + L)], fill=cyan, width=w)
    # top-right
    draw.line([(S - pad - L, pad), (S - pad, pad)], fill=cyan, width=w)
    draw.line([(S - pad, pad), (S - pad, pad + L)], fill=cyan, width=w)
    # bottom-left
    draw.line([(pad, S - pad - L), (pad, S - pad)], fill=cyan, width=w)
    draw.line([(pad, S - pad), (pad + L, S - pad)], fill=cyan, width=w)
    # bottom-right
    draw.line([(S - pad, S - pad - L), (S - pad, S - pad)], fill=cyan, width=w)
    draw.line([(S - pad - L, S - pad), (S - pad, S - pad)], fill=cyan, width=w)


def wordmark(img: Image.Image) -> None:
    """Tiny WoundScan wordmark at the bottom edge."""
    draw = ImageDraw.Draw(img, "RGBA")
    # Try to use a system font; fall back to default if unavailable.
    candidates = [
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Avenir.ttc",
        "/Library/Fonts/Arial Bold.ttf",
    ]
    font = None
    for path in candidates:
        try:
            font = ImageFont.truetype(path, 78)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()

    # Place at ~88% down, centered
    text_w = "Wound"
    text_s = "Scan"
    bbox_w = draw.textbbox((0, 0), text_w, font=font)
    bbox_s = draw.textbbox((0, 0), text_s, font=font)
    width_w = bbox_w[2] - bbox_w[0]
    width_s = bbox_s[2] - bbox_s[0]
    total = width_w + width_s
    y = int(S * 0.86)
    x = (S - total) // 2
    draw.text((x, y), text_w, fill=(245, 247, 250, 240), font=font)
    draw.text((x + width_w, y), text_s, fill=(34, 211, 238, 240), font=font)


def main(out: str) -> None:
    img = background().convert("RGBA")
    topographic_mark(img)
    measurement_marks(img)
    wordmark(img)
    img.convert("RGB").save(out, "PNG", optimize=True)


if __name__ == "__main__":
    import sys

    out_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/icon-1024.png"
    main(out_path)
    print(f"wrote {out_path}")
