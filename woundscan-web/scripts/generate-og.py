#!/usr/bin/env python3
"""Generate the OpenGraph link-share card (public/og.png).

Run:  python3 scripts/generate-og.py     (from woundscan-web/)

The card is what people see when the URL is texted, DM'd, or posted. It has to
answer "what is this?" at a glance on a phone, so the type is large and the copy
names the whole product, not just the measurement step. Regenerate this whenever
the brand art or the positioning line changes.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1200, 630
FONTS = str(Path(__file__).parent / "fonts")

# Brand palette (dark theme tokens from src/styles/globals.css)
INK = (245, 247, 250)
INK_SOFT = (176, 190, 208)
INK_MUTED = (128, 145, 168)
CYAN = (34, 211, 238)
GOLD = (230, 192, 107)
BG_TOP = (12, 26, 48)
BG_BOT = (4, 7, 13)

f_head = ImageFont.truetype(f"{FONTS}/Outfit-Bold.ttf", 60)
f_sub = ImageFont.truetype(f"{FONTS}/WorkSans-Regular.ttf", 23)
f_tag = ImageFont.truetype(f"{FONTS}/JetBrainsMono-Regular.ttf", 15)
f_plus = ImageFont.truetype(f"{FONTS}/Outfit-Bold.ttf", 19)
f_dom = ImageFont.truetype(f"{FONTS}/JetBrainsMono-Regular.ttf", 16)
f_small = ImageFont.truetype(f"{FONTS}/JetBrainsMono-Regular.ttf", 11)


def gradient(w, h, top, bot):
    col = Image.new("RGB", (1, h))
    px = col.load()
    for y in range(h):
        t = y / (h - 1)
        px[0, y] = tuple(int(top[i] * (1 - t) + bot[i] * t) for i in range(3))
    return col.resize((w, h))


def glow(color, cx, cy, rx, ry, strength, blur=110):
    layer = Image.new("L", (W, H), 0)
    ImageDraw.Draw(layer).ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)
    layer = layer.filter(ImageFilter.GaussianBlur(blur)).point(
        lambda v: int(v * strength)
    )
    tint = Image.new("RGBA", (W, H), color + (0,))
    tint.putalpha(layer)
    return tint


card = gradient(W, H, BG_TOP, BG_BOT).convert("RGBA")

# ── Faint technical grid, masked so it fades out toward the edges ──────────
grid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
gd = ImageDraw.Draw(grid)
for x in range(0, W, 48):
    gd.line([(x, 0), (x, H)], fill=(255, 255, 255, 12), width=1)
for y in range(0, H, 48):
    gd.line([(0, y), (W, y)], fill=(255, 255, 255, 12), width=1)
mask = Image.new("L", (W, H), 0)
ImageDraw.Draw(mask).ellipse([-260, -300, W + 260, H + 220], fill=190)
grid.putalpha(Image.composite(grid.getchannel("A"), Image.new("L", (W, H), 0), mask))
card = Image.alpha_composite(card, grid)

# ── Ambient light: cyan behind the headline, gold warmth under the visual ──
card = Image.alpha_composite(card, glow(CYAN, W * 0.30, H * 0.42, 300, 250, 0.30))
card = Image.alpha_composite(card, glow(GOLD, W * 0.86, H * 0.80, 260, 200, 0.13))

# ── LiDAR reconstruction mesh ─────────────────────────────────────────────
# Drawn the way ARKit renders a scene-reconstruction mesh: a triangulated
# wireframe deforming over the surface, brighter where the sensor is closest.
import math

topo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
td = ImageDraw.Draw(topo)
CX, CY = 1000, int(H * 0.40)
N = 15                       # grid resolution
ISO_X, ISO_Y = 62, 34        # isometric axes
DEPTH = 76                   # crater depth on screen
SIGMA = 0.55                 # crater width; larger reads shallower and broader


def surface(i, j):
    """Grid index -> screen point over a Gaussian depression, isometric view."""
    u = (i / (N - 1) - 0.5) * 2
    v = (j / (N - 1) - 0.5) * 2
    z = math.exp(-(u * u + v * v) / SIGMA)   # 1 at the deepest point, ~0 at the rim
    return (CX + (u - v) * ISO_X, CY + (u + v) * ISO_Y + z * DEPTH), z


pts = [[surface(i, j) for j in range(N)] for i in range(N)]


def shade(z):
    """Intact rim stays cyan; the excavated centre warms toward gold."""
    return tuple(round(CYAN[k] + (GOLD[k] - CYAN[k]) * z) for k in range(3))


for i in range(N):
    for j in range(N):
        (x0, y0), z0 = pts[i][j]
        for di, dj in ((1, 0), (0, 1), (1, 1)):   # rows, columns, one diagonal
            if i + di < N and j + dj < N:
                (x1, y1), z1 = pts[i + di][j + dj]
                z = (z0 + z1) / 2
                a = int(78 + 172 * z)
                if di and dj:
                    a = int(a * 0.34)             # diagonals sit behind the quads
                td.line([(x0, y0), (x1, y1)], fill=shade(z) + (a,), width=1)

# Vertex returns, the way a depth capture shows its samples.
for i in range(N):
    for j in range(N):
        (x, y), z = pts[i][j]
        if (i + j) % 2:
            continue
        r = 1.5 if z > 0.4 else 1.1
        td.ellipse([x - r, y - r, x + r, y + r], fill=shade(z) + (int(130 + 125 * z),))

card = Image.alpha_composite(card, topo)

dl = ImageDraw.Draw(card)
bot_y = CY + DEPTH + 12

formula = "V = ∫∫ d(x,y) dA"
dl.text((CX - dl.textlength(formula, font=f_tag) / 2, bot_y + 26), formula, font=f_tag, fill=GOLD + (240,))
sub = "OVER THE WOUND BED"
dl.text((CX - dl.textlength(sub, font=f_small) / 2, bot_y + 48), sub, font=f_small, fill=INK_MUTED)

# ── Brand lockup, top-left ────────────────────────────────────────────────
PAD = 74
sym = Image.open("public/symbol-dark.png").convert("RGBA")
sh = 46
sym = sym.resize((int(sym.width * sh / sym.height), sh), Image.LANCZOS)
card.alpha_composite(sym, (PAD, 60))

wm = Image.open("public/wordmark-dark.png").convert("RGBA")
wh = 30
wm = wm.resize((int(wm.width * wh / wm.height), wh), Image.LANCZOS)
card.alpha_composite(wm, (PAD + sym.width + 16, 60 + (sh - wh) // 2))

d = ImageDraw.Draw(card)

# ── Headline ──────────────────────────────────────────────────────────────
y = 186
for line in ["Measure true wound volume", "in 4 seconds, with an iPhone."]:
    d.text((PAD, y), line, font=f_head, fill=INK)
    y += 70

# ── Supporting line: names the WHOLE product, not just the scan ───────────
y += 26
for line in [
    "Wound beds are never uniform. Undermining, tunneling and uneven",
    "granulation all change the real volume. So the scan measures depth",
    "point by point across the whole bed and adds it up.",
]:
    d.text((PAD, y), line, font=f_sub, fill=INK_SOFT)
    y += 34

# ── Credential tags, matching the site's gold "+" instrument tags ─────────
y += 34
x = PAD
for label in ["VOLUME · AREA · DEPTH", "±0.3 MM @ 95% CI", "510(K)-READY ARCHITECTURE"]:
    d.text((x, y - 2), "+", font=f_plus, fill=GOLD)
    x += 17
    d.text((x, y), label, font=f_tag, fill=INK_MUTED)
    x += int(d.textlength(label, font=f_tag)) + 34

# ── Base rule + domain ────────────────────────────────────────────────────
d.line([(PAD, H - 74), (W - PAD, H - 74)], fill=(255, 255, 255, 26), width=1)
d.text((PAD, H - 56), "stratametricai.com", font=f_dom, fill=INK_MUTED)
byline = "by Albacete MedDev"
d.text(
    (W - PAD - d.textlength(byline, font=f_dom), H - 56),
    byline,
    font=f_dom,
    fill=INK_MUTED,
)

out = card.convert("RGB")
# Versioned name busts scraper caches; the legacy path keeps older embeds alive.
out.save("public/og-v2.png", "PNG")
out.save("public/og.png", "PNG")
print(f"wrote public/og-v2.png and public/og.png ({W}x{H})")
