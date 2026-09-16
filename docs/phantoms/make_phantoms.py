#!/usr/bin/env python3
"""Wound-measurement calibration phantoms -> watertight binary STL (millimetres).

Each phantom is an 80 x 80 x 30 mm block.

TOP FACE    one cavity of closed-form volume, plus (all engraved 0.5 mm deep):
              - four fiducial dots, centres on a 64.000 mm square
              - the MEASUREMENT KEY LINE: a groove spanning exactly 50.000 mm,
                terminated by a tick centred on each end
              - "50.000" beneath the key line, and the phantom id above the cavity
BOTTOM FACE the spec plate: the phantom's exact nominal geometry, engraved 0.4 mm
            deep and mirrored so it reads correctly when the block is turned over.

Origin: block centre, bottom face at z = 0, +Z up.
"""
import json, os, struct, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT  = os.path.dirname(os.path.abspath(__file__))
L = 80.0                   # block side
H_DEFAULT = 30.0           # fallback block height
STEP = 0.32                # grid pitch target
ENG_TOP, ENG_BOT = 0.5, 0.4

# Hollow shell: a solid rim, a solid central pad carrying the spec plate, and an
# open-bottomed void ring between them.  Nothing is enclosed, so no resin is
# trapped and the part drains as it lifts out of the vat.
HOLLOW = True              # set False (or pass --solid) for solid blocks
RIM = 3.5                  # solid border width, full height
PAD = 34.0                 # solid central pad, carries the bottom spec plate
WALL = 3.5                 # ceiling thickness over the void ring
RIB = 3.0                  # stiffening ribs pad -> rim, full height, on both axes

DOT_R, DOT_XY = 1.25, 32.0          # fiducials: 64.000 mm square, 90.510 mm diagonal
KEY_LEN, KEY_Y = 50.0, -30.0        # key line: 50.000 mm, groove + end ticks
KEY_W, TICK_W, TICK_H = 0.8, 0.8, 6.0

MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

PHANTOMS = [
    dict(id="P1", name="hemisphere_r15",       kind="hemisphere", R=15.0, height=19.0),
    dict(id="P2", name="hemisphere_r25",       kind="hemisphere", R=25.0, height=29.0),
    dict(id="P3", name="cone_r20_d10",         kind="cone",       R=20.0, h=10.0, height=14.0),
    dict(id="P4", name="paraboloid_30x20_d12", kind="paraboloid", a=30.0, b=20.0, h=12.0, height=16.0),
    dict(id="P5", name="paraboloid_12x8_d4",   kind="paraboloid", a=12.0, b=8.0,  h=4.0, height=9.0),
    dict(id="P6", name="flat_plate",           kind="flat", height=9.0),
    # --- complex set -------------------------------------------------------
    dict(id="P7", name="lobed_r18_d9",         kind="lobed",   R0=18.0, h=9.0, height=13.0,
         lobes=[(3, 0.18, 0.0), (5, 0.10, 0.7)]),
    dict(id="P8", name="trough_L40_r9_d8",     kind="stadium", R=9.0, seg=40.0, h=8.0, height=12.0),
    dict(id="P9", name="paraboloid_on_cyl_r60", kind="paraboloid", a=25.0, b=18.0, h=10.0,
         cyl=60.0, key_axis="y", height=22.0),
    dict(id="P10", name="undermining_base",    kind="cylwell", R=20.0, h=12.0,
         pocket_r=28.2, pocket_d=3.0, height=19.0),
]

# Two-part undermining lids (discs that drop into P10's register pocket).
LIDS = [
    dict(id="L1", name="lid_concentric_r12", R_out=28.0, thick=3.0, hole_r=12.0, hole_cx=0.0),
    dict(id="L2", name="lid_offset6_r12",    R_out=28.0, thick=3.0, hole_r=12.0, hole_cx=6.0),
]

# ---------------------------------------------------------------- geometry ---
def analytic(p):
    k = p["kind"]
    if k == "hemisphere":
        R = p["R"]
        return dict(volume=2/3*np.pi*R**3, depth=R, area=np.pi*R**2,
                    opening=f"circle {2*R:.3f} mm dia", shape="hemisphere",
                    formula="V = 2/3 pi R^3", geom=[f"SPHERE R {R:.3f}"])
    if k == "cone":
        R, h = p["R"], p["h"]
        return dict(volume=np.pi*R**2*h/3, depth=h, area=np.pi*R**2,
                    opening=f"circle {2*R:.3f} mm dia", shape="cone",
                    formula="V = 1/3 pi R^2 h", geom=[f"CONE R {R:.3f}"])
    if k == "paraboloid":
        a, b, h = p["a"], p["b"], p["h"]
        return dict(volume=np.pi*a*b*h/2, depth=h, area=np.pi*a*b,
                    opening=f"ellipse {2*a:.3f} x {2*b:.3f} mm", shape="ell. paraboloid",
                    formula="V = pi a b h / 2",
                    geom=[f"a{a:.3f} b{b:.3f}"])
    if k == "lobed":
        R0, h, lb = p["R0"], p["h"], p["lobes"]
        s2 = sum(a*a for _, a, _ in lb)
        th = np.linspace(0, 2*np.pi, 2**16, endpoint=False)
        R = R0*(1 + sum(a*np.cos(m*th + ph) for m, a, ph in lb))
        dR = R0*sum(-a*m*np.sin(m*th + ph) for m, a, ph in lb)
        per = np.trapezoid(np.sqrt(R**2 + dR**2), th)
        return dict(volume=np.pi*h*R0**2/4*(2 + s2), depth=h,
                    area=np.pi*R0**2/2*(2 + s2), perimeter=per,
                    opening=f"lobed, R {R.min():.3f}-{R.max():.3f} mm", shape="lobed paraboloid",
                    formula="V = (pi h R0^2/4)(2 + sum a_k^2)",
                    geom=[f"R0 {R0:.3f} mm", "LOBES 3:.18 5:.10"])
    if k == "stadium":
        R, Ls, h = p["R"], p["seg"], p["h"]
        return dict(volume=4*h*R*Ls/3 + np.pi*h*R*R/2, depth=h,
                    area=2*R*Ls + np.pi*R*R, perimeter=2*Ls + 2*np.pi*R,
                    opening=f"stadium {Ls + 2*R:.3f} x {2*R:.3f} mm", shape="stadium trough",
                    formula="V = 4hR*Ls/3 + pi h R^2/2",
                    geom=[f"L{Ls:.3f} R{R:.3f}"])
    if k == "cylwell":
        R, h = p["R"], p["h"]
        return dict(volume=np.pi*R*R*h, depth=h, area=np.pi*R*R, perimeter=2*np.pi*R,
                    opening=f"circle {2*R:.3f} mm dia", shape="cyl. well + lid",
                    formula="V = pi R^2 h",
                    geom=[f"CHAMBER R {R:.3f}"])
    return dict(volume=0.0, depth=0.0, area=0.0, opening="none (flat reference)",
                shape="flat plate", formula="-", geom=["NO CAVITY"])

def cavity(p, X, Y):
    k = p["kind"]; r = np.hypot(X, Y)
    if k == "hemisphere":
        R = p["R"]; return np.where(r < R, np.sqrt(np.clip(R*R - r*r, 0, None)), 0.0)
    if k == "cone":
        R, h = p["R"], p["h"]; return np.where(r < R, h*(1 - r/R), 0.0)
    if k == "paraboloid":
        a, b, h = p["a"], p["b"], p["h"]; q = (X/a)**2 + (Y/b)**2
        return np.where(q < 1, h*(1 - q), 0.0)
    if k == "lobed":
        th = np.arctan2(Y, X)
        Rt = p["R0"]*(1 + sum(a*np.cos(m*th + ph) for m, a, ph in p["lobes"]))
        q = (r/Rt)**2
        return np.where(q < 1, p["h"]*(1 - q), 0.0)
    if k == "stadium":
        R, Ls, h = p["R"], p["seg"], p["h"]
        d = np.hypot(np.clip(np.abs(X) - Ls/2, 0, None), Y)
        return np.where(d < R, h*(1 - (d/R)**2), 0.0)
    if k == "cylwell":
        pocket = np.where(r < p["pocket_r"], p["pocket_d"], 0.0)
        return pocket + np.where(r < p["R"], p["h"], 0.0)
    return np.zeros_like(X)

def cavity_check(p, X, Y):
    """The part of the cavity whose integral must equal the analytic volume."""
    if p["kind"] == "cylwell":
        return np.where(np.hypot(X, Y) < p["R"], p["h"], 0.0)
    return cavity(p, X, Y)

def block_height(p):
    return float(p.get("height", H_DEFAULT))

def base_surface(p, X):
    """Top surface before the cavity: flat, or a cylinder of radius cyl about the y-axis."""
    H = block_height(p)
    Rc = p.get("cyl")
    if not Rc:
        return np.full_like(X, H)
    return H - Rc + np.sqrt(np.clip(Rc*Rc - X*X, 0.0, None))

def hollow_floor(p, X, Y, Ztop, spec_mask, hollow=True):
    """Bottom surface of the solid.

    Solid (z = 0) under the rim and under the central spec pad; elsewhere the
    solid stops at a ceiling one WALL below the top surface, leaving an
    open-bottomed void ring that drains freely.
    """
    Zbot = np.where(spec_mask, ENG_BOT, 0.0)
    if not hollow:
        return Zbot
    solid = (np.abs(X) >= L/2 - RIM) | (np.abs(Y) >= L/2 - RIM) \
            | ((np.abs(X) <= PAD/2) & (np.abs(Y) <= PAD/2)) \
            | (np.abs(X) <= RIB/2) | (np.abs(Y) <= RIB/2)
    ceiling = np.clip(Ztop - WALL, 0.0, None)
    return np.where(solid, Zbot, ceiling)

# ------------------------------------------------------------------- text ----
def text_mask(n, lines, cx, cy, cap_mm, pitch_mm, mirror_x, font_path):
    """Rasterise centred lines of text; return bool mask indexed [i(x), j(y)]."""
    ppm = (n - 1) / L
    img = Image.new("L", (n, n), 0); d = ImageDraw.Draw(img)
    f = ImageFont.truetype(font_path, max(6, int(round(cap_mm * ppm / 0.72))))
    y0 = cy + (len(lines) - 1) * pitch_mm / 2.0
    for k, line in enumerate(lines):
        ym = y0 - k * pitch_mm
        d.text(((cx + L/2) * ppm, (L/2 - ym) * ppm), line, fill=255, font=f, anchor="mm")
    a = np.array(img) > 127                      # [row(y down), col(x)]
    if mirror_x:
        a = a[:, ::-1]                           # mirror so it reads from below
    return a[::-1, :].T                          # -> [i(x), j(y)]

def top_engraving(n, xs, p, D):
    X, Y = np.meshgrid(xs, xs, indexing="ij")
    m = np.zeros((n, n), bool)
    for sx in (-1, 1):
        for sy in (-1, 1):
            m |= np.hypot(X - sx*DOT_XY, Y - sy*DOT_XY) <= DOT_R          # fiducials
    half = KEY_LEN / 2.0
    if p.get("key_axis", "x") == "y":            # run along y (constant height on a cylinder)
        A, B, ka, kb = Y, X, 0.0, KEY_Y          # groove along y at x = KEY_Y
    else:
        A, B, ka, kb = X, Y, 0.0, KEY_Y
    m |= (np.abs(A - ka) <= half) & (np.abs(B - kb) <= KEY_W/2)           # key groove
    for sx in (-1, 1):                                                    # end ticks
        m |= (np.abs(A - sx*half) <= TICK_W/2) & (np.abs(B - kb) <= TICK_H/2)
    m |= text_mask(n, ["50.000"], 0.0, -36.0, 3.2, 4.0, False, MONO)      # key value
    m |= text_mask(n, [p["id"]],  0.0,  33.0, 6.0, 7.0, False, SANS)      # phantom id
    assert not (m & (D > 1e-9)).any(), "top engraving overlaps the cavity"
    return m

def bottom_engraving(n, p, a):
    """Spec plate, sized to the central pad so the shell can be hollowed around it."""
    T = block_height(p)
    lines = [f"STRATAMETRIC {p['id']}", a["shape"].upper()]
    lines += [g.replace("  ", " ").strip() for g in a["geom"]]
    lines += [f"DEPTH  {a['depth']:8.3f} mm",
              f"AREA   {a['area']:8.2f} mm2",
              f"VOL  {a['volume']:10.2f} mm3",
              f"VOL  {a['volume']/1000:10.3f} cm3"]
    if p.get("cyl"):
        lines.append(f"CYL BASE R {p['cyl']:.1f} mm")
    if p["kind"] == "cylwell":
        lines.append("USE WITH LID L1/L2")
    lines += ["KEY LINE  50.000 mm",
              f"BLOCK 80x80x{T:.0f} mm",
              "CAD NOMINAL-VERIFY"]
    usable = PAD - 4.0
    widest = max(len(t) for t in lines)
    # DejaVu Sans Mono: advance ~0.60 em, cap height ~0.72 em
    em = min(usable / (0.60 * widest), usable / (1.09 * len(lines)), 5.3)
    cap, pitch = 0.72 * em, 1.09 * em
    assert cap >= 1.7, (
        f"{p['id']} spec plate would engrave at {cap:.2f} mm cap height "
        f"({len(lines)} lines, widest {widest} chars, in {usable:.0f} mm) - too fine to print")
    return text_mask(n, lines, 0.0, 0.0, cap, pitch, True, MONO), lines

# ------------------------------------------------------------------- mesh ----
def build_solid(Ztop, Zbot, xs):
    X, Y = np.meshgrid(xs, xs, indexing="ij")
    Vt = np.stack([X, Y, Ztop], -1); Vb = np.stack([X, Y, Zbot], -1)
    def quads(V, flip):
        a = V[:-1, :-1].reshape(-1, 3); b = V[1:, :-1].reshape(-1, 3)
        c = V[1:, 1:].reshape(-1, 3);   d = V[:-1, 1:].reshape(-1, 3)
        if flip:
            return np.concatenate([np.stack([a, c, b], 1), np.stack([a, d, c], 1)])
        return np.concatenate([np.stack([a, b, c], 1), np.stack([a, c, d], 1)])
    def loop(V):
        return np.concatenate([V[:-1, 0], V[-1, :-1], V[1:, -1][::-1], V[0, 1:][::-1]])
    P, B = loop(Vt), loop(Vb)
    Pn, Bn = np.roll(P, -1, axis=0), np.roll(B, -1, axis=0)
    walls = np.concatenate([np.stack([P, B, Bn], 1), np.stack([P, Bn, Pn], 1)])
    return np.concatenate([quads(Vt, False), quads(Vb, True), walls]).astype(np.float64)

def hf_integral(Z, cell):
    z00, z10 = Z[:-1, :-1], Z[1:, :-1]
    z11, z01 = Z[1:, 1:], Z[:-1, 1:]
    return (cell/6.0*(2*z00 + z10 + 2*z11 + z01)).sum()

def build_lid(R_out, thick, hole_r, hole_cx, N=1440):
    """Disc with a (possibly offset) through hole, from four 1:1 quad strips."""
    th = np.linspace(0, 2*np.pi, N, endpoint=False)
    c, sn = np.cos(th), np.sin(th)
    ring = lambda px, py, z: np.stack([px, py, np.full(N, z)], -1)
    OT, OB = ring(R_out*c, R_out*sn, thick), ring(R_out*c, R_out*sn, 0.0)
    IT = ring(hole_cx + hole_r*c, hole_r*sn, thick)
    IB = ring(hole_cx + hole_r*c, hole_r*sn, 0.0)
    def strip(A, B):
        An, Bn = np.roll(A, -1, 0), np.roll(B, -1, 0)
        return np.concatenate([np.stack([A, B, Bn], 1), np.stack([A, Bn, An], 1)])
    # no self-intersection: every top-annulus quad must have positive projected area
    a, b = IT[:, :2], OT[:, :2]
    an, bn = np.roll(a, -1, 0), np.roll(b, -1, 0)
    cr = lambda u, v: u[:, 0]*v[:, 1] - u[:, 1]*v[:, 0]
    assert (cr(b - a, bn - a) > 0).all() and (cr(bn - a, an - a) > 0).all(), "lid annulus self-intersects"
    return np.concatenate([strip(IT, OT), strip(OB, IB), strip(OT, OB), strip(IB, IT)]).astype(np.float64)

def manifold(T):
    q = np.round(T, 5); idx = {}
    ids = np.array([idx.setdefault(tuple(v), len(idx)) for tri in q for v in tri]).reshape(-1, 3)
    e = np.concatenate([ids[:, [0, 1]], ids[:, [1, 2]], ids[:, [2, 0]]])
    directed = set(map(tuple, e))
    unpaired = sum(1 for a, b in directed if (b, a) not in directed)
    _, cnt = np.unique(np.sort(e, axis=1), axis=0, return_counts=True)
    return int((cnt != 2).sum()), unpaired

def volume(T):
    return np.einsum("ij,ij->i", T[:, 0], np.cross(T[:, 1], T[:, 2])).sum() / 6.0

def write_stl(path, T, header):
    nrm = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
    rec = np.zeros(len(T), dtype=[("n", "<f4", (3,)), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"] = nrm; rec["v"] = T
    with open(path, "wb") as f:
        f.write(header.encode()[:80].ljust(80, b"\0")); f.write(struct.pack("<I", len(T))); f.write(rec.tobytes())

# ------------------------------------------------------------------- main ----
def undermining_truth(base, lid):
    """Exact truths for the assembled base+lid configuration."""
    R, dc, tl, rh, cx = base["R"], base["h"], lid["thick"], lid["hole_r"], lid["hole_cx"]
    hole = np.pi*rh**2*tl
    chamber = np.pi*R**2*dc
    hidden = np.pi*(R**2 - rh**2)*dc
    out = dict(lid=lid["id"], hole_offset_mm=cx,
               skin_to_floor_depth_mm=round(tl + dc, 3),
               opening_area_at_skin_mm2=round(np.pi*rh**2, 2),
               total_wound_volume_mm3=round(hole + chamber, 2),
               visible_volume_mm3=round(np.pi*rh**2*(tl + dc), 2),
               undermined_volume_mm3=round(hidden, 2),
               undermined_fraction_pct=round(hidden/(hole + chamber)*100, 1),
               shelf_depth_below_skin_mm=round(tl, 3))
    ext = {}
    for k in range(12):
        a = np.pi/2 - k*np.pi/6                      # 12 o'clock = +y
        pu = cx*np.cos(a) + rh                       # P.u  with P = (cx,0) + rh*u
        p2 = cx**2 + 2*cx*rh*np.cos(a) + rh**2       # |P|^2
        ext[str(k or 12)] = round(-pu + np.sqrt(pu*pu - p2 + R*R), 3)
    out["undermining_extent_mm_by_clock"] = ext
    return out

def main():
    global HOLLOW
    args = [a for a in sys.argv[1:]]
    if "--solid" in args:
        HOLLOW = False
        args.remove("--solid")
    want = set(args)
    n = int(round(L / STEP)) + 1
    xs = np.linspace(-L/2, L/2, n)
    X, Y = np.meshgrid(xs, xs, indexing="ij")
    cell = (xs[1] - xs[0]) ** 2
    truth = []
    material_total = []
    print(f"grid {n} x {n}  pitch {xs[1]-xs[0]:.4f} mm   hollow={HOLLOW}"
          f"  (rim {RIM:.0f} mm, pad {PAD:.0f} mm, wall {WALL:.0f} mm)\n")
    for p in PHANTOMS:
        if want and p["id"] not in want:
            continue
        a  = analytic(p)
        D  = cavity(p, X, Y)
        Et = top_engraving(n, xs, p, D)
        Eb, lines = bottom_engraving(n, p, a)
        T_mm = block_height(p)
        Ztop = base_surface(p, X) - D - np.where(Et, ENG_TOP, 0.0)
        if HOLLOW and Eb.any():
            outside = Eb & ((np.abs(X) > PAD/2) | (np.abs(Y) > PAD/2))
            assert not outside.any(), (
                f"{p['id']} spec text spills outside the {PAD:.0f} mm pad "
                f"({outside.sum()} cells) and would be lost to the void")
        Zbot = hollow_floor(p, X, Y, Ztop, Eb, hollow=HOLLOW)
        assert (Zbot <= Ztop - 0.4).all(), f"{p['id']} wall too thin somewhere"
        T = build_solid(Ztop, Zbot, xs)
        nm, up = manifold(T)
        vol, expect = volume(T), hf_integral(Ztop, cell) - hf_integral(Zbot, cell)
        solid_ref = L * L * 30.0 - cavity_check(p, X, Y).sum() * cell   # original solid block
        cav = cavity_check(p, X, Y).sum()*cell
        err = 0.0 if a["volume"] == 0 else abs(cav - a["volume"])/a["volume"]*100
        assert nm == 0 and up == 0, f"{p['id']} not watertight (nm={nm} up={up})"
        assert abs(vol - expect) < 1e-3*abs(expect) + 1.0, f"{p['id']} mesh volume mismatch"
        assert err < 0.5, f"{p['id']} cavity off by {err:.3f}%"
        fn = f"{p['id']}_{p['name']}.stl"
        write_stl(os.path.join(OUT, fn), T, f"StrataMetric wound phantom {p['id']} {p['name']} mm CAD nominal")
        print(f"{fn:32s} tri={len(T):7d} H={T_mm:4.0f}mm  V_true={a['volume']:9.2f}  err={err:.4f}%  "
              f"material {vol/1000:7.1f} cm3 ({100*vol/solid_ref:4.1f}% of solid)  watertight")
        material_total.append((vol, solid_ref))
        rec = dict(
            id=p["id"], file=fn, part="block", shape=a["shape"], formula=a["formula"],
            parameters={k: v for k, v in p.items() if k in ("R", "h", "a", "b", "R0", "seg", "lobes", "cyl", "pocket_r", "pocket_d")},
            opening=a["opening"], max_depth_mm=round(a["depth"], 3),
            opening_area_mm2=round(a["area"], 2),
            cavity_volume_mm3=round(a["volume"], 2), cavity_volume_cm3=round(a["volume"]/1000, 4),
            cavity_volume_mm3_from_mesh=round(cav, 2),
            key_line_mm=50.000, key_line_axis=p.get("key_axis", "x"),
            key_line_definition="end-tick centre to end-tick centre (= groove end to groove end)",
            fiducial_square_mm=64.000, fiducial_diagonal_mm=round(64*np.sqrt(2), 3),
            block_mm=[L, L, T_mm], material_volume_mm3=round(vol, 1),
            solid_equivalent_mm3=round(solid_ref, 1), hollow=HOLLOW, base_surface=("cylinder R %.3f mm" % p["cyl"]) if p.get("cyl") else "flat",
            engraving_depth_top_mm=ENG_TOP, engraving_depth_bottom_mm=ENG_BOT,
            bottom_plate_text=[t for t in lines if t], triangles=int(len(T)))
        if "perimeter" in a:
            rec["opening_perimeter_mm"] = round(a["perimeter"], 3)
        if p["kind"] == "cylwell":
            rec["assemblies"] = [undermining_truth(p, l) for l in LIDS]
            rec["note"] = ("register pocket D %.1f x %.1f mm deep receives lid L1/L2; "
                           "volumes above are the chamber alone" % (2*p["pocket_r"], p["pocket_d"]))
        truth.append(rec)

    for l in LIDS:
        if want and l["id"] not in want:
            continue
        T = build_lid(l["R_out"], l["thick"], l["hole_r"], l["hole_cx"])
        nm, up = manifold(T)
        vol = volume(T)
        expect = np.pi*(l["R_out"]**2 - l["hole_r"]**2)*l["thick"]
        assert nm == 0 and up == 0, f"{l['id']} not watertight"
        assert abs(vol - expect) < 0.002*expect, f"{l['id']} volume {vol:.2f} != {expect:.2f}"
        fn = f"{l['id']}_{l['name']}.stl"
        write_stl(os.path.join(OUT, fn), T, f"StrataMetric undermining lid {l['id']} {l['name']} mm")
        print(f"{fn:32s} tri={len(T):7d}  solid={vol:9.2f} mm3 (exact {expect:9.2f})  watertight")
        material_total.append((vol, vol))
        truth.append(dict(id=l["id"], file=fn, part="lid", shape="disc with through hole",
                          outer_dia_mm=2*l["R_out"], thickness_mm=l["thick"],
                          hole_dia_mm=2*l["hole_r"], hole_offset_mm=l["hole_cx"],
                          solid_volume_mm3=round(expect, 2),
                          pairs_with="P10", triangles=int(len(T))))

    if material_total:
        m = sum(v for v, _ in material_total) / 1000.0
        r = sum(s_ for _, s_ in material_total) / 1000.0
        print(f"\nmaterial for this set: {m:.0f} cm3   "
              f"(original solid 30 mm blocks: {r:.0f} cm3 -> {r/m:.1f}x less)")
    json.dump(truth, open(os.path.join(OUT, "truth.json"), "w"), indent=1)
    import csv
    with open(os.path.join(OUT, "truth.csv"), "w", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(["id", "file", "part", "shape", "opening", "max_depth_mm", "opening_area_mm2",
                    "perimeter_mm", "cavity_volume_mm3", "cavity_volume_cm3", "key_line_mm",
                    "fiducial_square_mm"])
        for t in truth:
            if t["part"] == "lid":
                w.writerow([t["id"], t["file"], "lid", t["shape"],
                            f"hole dia {t['hole_dia_mm']:.3f} offset {t['hole_offset_mm']:.3f}",
                            t["thickness_mm"], "", "", "", "", "", ""])
            else:
                w.writerow([t["id"], t["file"], "block", t["shape"], t["opening"],
                            t["max_depth_mm"], t["opening_area_mm2"],
                            t.get("opening_perimeter_mm", ""), t["cavity_volume_mm3"],
                            t["cavity_volume_cm3"], f"{t['key_line_mm']:.3f}",
                            f"{t['fiducial_square_mm']:.3f}"])

    blocks = [p for p in PHANTOMS if not want or p["id"] in want]
    if blocks:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        for face in ("top", "bottom"):
            cols = min(3, len(blocks)); rows = int(np.ceil(len(blocks)/cols))
            fig, axes = plt.subplots(rows, cols, figsize=(4.4*cols, 4.3*rows), squeeze=False)
            for ax, p in zip(axes.flat, blocks):
                a = analytic(p); D = cavity(p, X, Y)
                if face == "top":
                    Z = D + np.where(top_engraving(n, xs, p, D), ENG_TOP, 0.0)
                    ttl = f"{p['id']}  V = {a['volume']/1000:.3f} cm³, depth {a['depth']:.0f} mm"
                else:
                    Z = np.where(bottom_engraving(n, p, a)[0], 1.0, 0.0)[::-1, :]
                    ttl = f"{p['id']} spec plate (as seen from below)"
                ax.imshow(Z.T[::-1], extent=[-L/2, L/2, -L/2, L/2],
                          cmap="viridis" if face == "top" else "Greys")
                ax.set_title(ttl, fontsize=9); ax.set_xticks([]); ax.set_yticks([])
            for ax in axes.flat[len(blocks):]:
                ax.axis("off")
            fig.suptitle(f"Wound phantom set — {face} face")
            fig.tight_layout(); fig.savefig(os.path.join(OUT, f"preview_{face}.png"), dpi=105)
    print("\nwrote truth.json truth.csv preview_top.png preview_bottom.png")

if __name__ == "__main__":
    main()
