"""Diagram generation: top-view SVG and cross-section PNG (Pillow only)."""

import io
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageDraw, ImageFont

WOUND_FILL = "#C0392B"
RING_FILL = "#F5C26B"
INK = "#1F2933"
MUTED = "#6B7785"
FOOTER = "Objective measurements only. Not a diagnosis."


def _path(points, sx, sy):
    if len(points) < 3:
        return ""
    cmds = [f"M{sx(points[0][0]):.1f},{sy(points[0][1]):.1f}"]
    cmds += [f"L{sx(x):.1f},{sy(y):.1f}" for x, y in points[1:]]
    return " ".join(cmds) + " Z"


def _simplify(points, max_points=400):
    pts = np.asarray(points)
    if len(pts) > max_points:
        pts = pts[np.linspace(0, len(pts) - 1, max_points).astype(int)]
    return pts


def top_view_svg(geom, m, size=480):
    outline = _simplify(geom["outline_uv"])
    ring = _simplify(geom["ring_outline_uv"])
    allpts = np.vstack([outline, ring]) if len(ring) else outline
    span = float(np.max(np.abs(allpts))) if allpts.size else 30.0
    span = max(span, 10.0) * 1.08
    top, bottom = 56, 92
    plot = size - 2 * 24
    scale = min(plot, size - top - bottom) / (2 * span)
    cx, cy = size / 2, top + (size - top - bottom) / 2

    def sx(u):
        return cx + u * scale

    def sy(v):
        return cy + v * scale

    (lu0, _), (lu1, _) = geom["length_uv"]
    (_, wv0), (_, wv1) = geom["width_uv"]
    bar_mm = 10 if span < 60 else 20
    bar_px = bar_mm * scale

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}" font-family="Helvetica, Arial, sans-serif">',
        f'<rect width="{size}" height="{size}" fill="#FFFFFF"/>',
        f'<text x="{size/2}" y="28" text-anchor="middle" font-size="17" font-weight="bold" fill="{INK}">Top view</text>',
        f'<text x="{size/2}" y="46" text-anchor="middle" font-size="11" fill="{MUTED}">Wound outline on the fitted skin plane, length axis horizontal</text>',
    ]
    if len(ring) >= 3:
        out.append(f'<path d="{_path(ring, sx, sy)}" fill="{RING_FILL}" fill-opacity="0.45" stroke="{RING_FILL}" stroke-width="1.5"/>')
    out.append(f'<path d="{_path(outline, sx, sy)}" fill="{WOUND_FILL}" fill-opacity="0.55" stroke="{WOUND_FILL}" stroke-width="2"/>')
    # length axis
    out.append(f'<line x1="{sx(lu0):.1f}" y1="{sy(0):.1f}" x2="{sx(lu1):.1f}" y2="{sy(0):.1f}" stroke="{INK}" stroke-width="1.6" stroke-dasharray="6 4"/>')
    for u in (lu0, lu1):
        out.append(f'<line x1="{sx(u):.1f}" y1="{sy(0)-6:.1f}" x2="{sx(u):.1f}" y2="{sy(0)+6:.1f}" stroke="{INK}" stroke-width="1.6"/>')
    out.append(f'<text x="{sx(lu1)+6:.1f}" y="{sy(0)+4:.1f}" font-size="12" fill="{INK}">L {m["length_mm"]:.1f} mm</text>')
    # width axis
    out.append(f'<line x1="{sx(0):.1f}" y1="{sy(wv0):.1f}" x2="{sx(0):.1f}" y2="{sy(wv1):.1f}" stroke="{INK}" stroke-width="1.6" stroke-dasharray="2 3"/>')
    for v in (wv0, wv1):
        out.append(f'<line x1="{sx(0)-6:.1f}" y1="{sy(v):.1f}" x2="{sx(0)+6:.1f}" y2="{sy(v):.1f}" stroke="{INK}" stroke-width="1.6"/>')
    out.append(f'<text x="{sx(0)+6:.1f}" y="{sy(wv0)-6:.1f}" font-size="12" fill="{INK}">W {m["width_mm"]:.1f} mm</text>')
    # scale bar
    by = size - 64
    out.append(f'<line x1="24" y1="{by}" x2="{24+bar_px:.1f}" y2="{by}" stroke="{INK}" stroke-width="3"/>')
    out.append(f'<line x1="24" y1="{by-5}" x2="24" y2="{by+5}" stroke="{INK}" stroke-width="1.5"/>')
    out.append(f'<line x1="{24+bar_px:.1f}" y1="{by-5}" x2="{24+bar_px:.1f}" y2="{by+5}" stroke="{INK}" stroke-width="1.5"/>')
    out.append(f'<text x="24" y="{by+18}" font-size="11" fill="{INK}">{bar_mm} mm</text>')
    # legend
    lx = size - 208
    out.append(f'<rect x="{lx}" y="{by-14}" width="12" height="12" fill="{WOUND_FILL}" fill-opacity="0.55"/>')
    out.append(f'<text x="{lx+18}" y="{by-4}" font-size="11" fill="{INK}">Wound bed {m["bed_area_cm2"]:.2f} cm²</text>')
    out.append(f'<rect x="{lx}" y="{by+4}" width="12" height="12" fill="{RING_FILL}" fill-opacity="0.6"/>')
    out.append(f'<text x="{lx+18}" y="{by+14}" font-size="11" fill="{INK}">Peri-wound 20 mm {m["peri_wound_area_cm2"]:.2f} cm²</text>')
    out.append(f'<text x="{size/2}" y="{size-14}" text-anchor="middle" font-size="10" fill="{MUTED}">{escape(FOOTER)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def _font(px):
    try:
        return ImageFont.load_default(size=px)
    except TypeError:  # Pillow < 10.1
        return ImageFont.load_default()


def _nice_step(span, target=6):
    raw = span / target
    mag = 10 ** np.floor(np.log10(raw)) if raw > 0 else 1
    for f in (1, 2, 2.5, 5, 10):
        if raw <= f * mag:
            return f * mag
    return 10 * mag


def cross_section_png(geom, m, width=900, height=440, ss=2):
    u = np.asarray(geom["profile_u"], dtype=float)
    hgt = np.asarray(geom["profile_h"], dtype=float)
    depth = float(m["depth_mm"])
    wu0, wu1 = [float(x) for x in geom["wound_u_range"]]
    deepest_u = float(geom["deepest_u"])
    if u.size < 2:
        u = np.array([wu0 - 20, wu1 + 20])
        hgt = np.zeros(2)

    W, H = width * ss, height * ss
    img = Image.new("RGB", (W, H), "white")
    dr = ImageDraw.Draw(img)
    f_title, f_lab, f_small = _font(19 * ss), _font(13 * ss), _font(11 * ss)
    L, R, T, B = 78 * ss, 30 * ss, 64 * ss, 70 * ss

    x_lo, x_hi = float(u.min()), float(u.max())
    y_lo = min(float(hgt.min()), -depth, -1.0) - 1.5
    y_hi = max(float(hgt.max()), 1.0) + 1.5

    def X(v):
        return L + (v - x_lo) / (x_hi - x_lo) * (W - L - R)

    def Y(v):
        return T + (y_hi - v) / (y_hi - y_lo) * (H - T - B)

    dr.text((W / 2, 16 * ss), "Cross-section along the length axis", fill=INK, font=f_title, anchor="mt")
    dr.text((W / 2, 42 * ss), "Height relative to the fitted skin plane (vertical axis exaggerated)", fill=MUTED, font=f_small, anchor="mt")

    # grid + ticks
    xs = _nice_step(x_hi - x_lo)
    for t in np.arange(np.ceil(x_lo / xs) * xs, x_hi + 1e-9, xs):
        dr.line([(X(t), T), (X(t), H - B)], fill="#ECEFF3", width=ss)
        dr.text((X(t), H - B + 6 * ss), f"{t:g}", fill=MUTED, font=f_small, anchor="mt")
    ys = _nice_step(y_hi - y_lo, 5)
    for t in np.arange(np.ceil(y_lo / ys) * ys, y_hi + 1e-9, ys):
        dr.line([(L, Y(t)), (W - R, Y(t))], fill="#ECEFF3", width=ss)
        dr.text((L - 8 * ss, Y(t)), f"{t:g}", fill=MUTED, font=f_small, anchor="rm")
    dr.text(((L + W - R) / 2, H - B + 26 * ss), "Position along length axis (mm)", fill=INK, font=f_lab, anchor="mt")
    dr.text((14 * ss, (T + H - B) / 2), "mm", fill=INK, font=f_lab, anchor="lm")
    dr.rectangle([L, T, W - R, H - B], outline="#C9D0D8", width=ss)

    # wound region fill between plane and profile
    inw = (u >= wu0) & (u <= wu1)
    if inw.sum() >= 2:
        uu, hh = u[inw], np.minimum(hgt[inw], 0)
        poly = [(X(a), Y(0)) for a in uu] + [(X(a), Y(b)) for a, b in zip(uu[::-1], hh[::-1])]
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(overlay).polygon(poly, fill=(192, 57, 43, 90))
        img.paste(overlay, (0, 0), overlay)
        dr = ImageDraw.Draw(img)

    # reference plane
    x = L
    while x < W - R:
        dr.line([(x, Y(0)), (min(x + 10 * ss, W - R), Y(0))], fill="#3E7CB1", width=2 * ss)
        x += 16 * ss
    dr.text((W - R - 6 * ss, Y(0) - 6 * ss), "Reference skin plane", fill="#3E7CB1", font=f_small, anchor="rb")

    # profile
    dr.line([(X(a), Y(b)) for a, b in zip(u, hgt)], fill=INK, width=3 * ss, joint="curve")

    # wound edges
    for e in (wu0, wu1):
        dr.line([(X(e), T + 4 * ss), (X(e), H - B)], fill=WOUND_FILL, width=ss)
    dr.text((X((wu0 + wu1) / 2), T + 6 * ss), f"Wound length {m['length_mm']:.1f} mm", fill=WOUND_FILL, font=f_small, anchor="mt")

    # depth arrow
    if depth > 0:
        xa = X(deepest_u)
        y0, y1 = Y(0), Y(-depth)
        dr.line([(xa, y0), (xa, y1)], fill=WOUND_FILL, width=2 * ss)
        a = 6 * ss
        dr.polygon([(xa, y1), (xa - a, y1 - a * 1.6), (xa + a, y1 - a * 1.6)], fill=WOUND_FILL)
        dr.text((xa + 10 * ss, (y0 + y1) / 2), f"Depth {depth:.1f} mm", fill=WOUND_FILL, font=f_lab, anchor="lm")

    dr.text((W / 2, H - 14 * ss), FOOTER, fill=MUTED, font=f_small, anchor="mb")
    img = img.resize((width, height), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
