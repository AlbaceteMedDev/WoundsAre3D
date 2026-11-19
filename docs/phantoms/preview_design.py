"""Design-level preview of the lifelike phantoms W1-W8, with numpy, scipy and
matplotlib only - no meshing or CAD libraries - so it runs in a restricted
Python sandbox such as an AI assistant's code tool.

From the same functions make_lifelike.py builds the parts with, it recomputes
everything that does not need the printed mesh, and checks it against
truth_lifelike.json:

  design   area, perimeter, length, width, longest diameter, tissue shares
           and percentages, where each periwound change shows, and W4's
           undermining extents, clock hours, pocket heights and area: the
           build's own arithmetic, so they agree to rounding
  grid     maximum depth, block height, volume and each tissue's mean
           colour, sampled on a grid instead of the mesh: within the
           tolerances below
  neither  the hidden volume, the labels and anything else on the solid

and draws each wound from above: in colour with relief shading, as a tissue
map, and as depth contours with any undermining.

    python preview_design.py                  # all eight
    python preview_design.py W4 W6            # just these
    python preview_design.py --grid 0.1       # finer pictures (default 0.15 mm)
    python preview_design.py --truth path/to/truth_lifelike.json --out pictures

It checks against truth_lifelike.json beside it, or in the reproduction kit
against ../data/truth_lifelike.json.
"""
import argparse
import json
import math
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_lifelike as LL                         # noqa: E402  (needs only numpy and scipy here)
from check_reproduction import agree               # noqa: E402

# tolerances for the values sampled on a grid rather than measured on the mesh
TOL_DEPTH = 0.05                                   # mm
TOL_VOLUME = 0.02                                  # relative; W4's pocket adds 0.4 % inside the margin
TOL_COLOUR = 8                                     # per channel, 0-255

def grid(step, box):
    x0, x1, y0, y1 = box
    xs, ys = np.arange(x0 + step/2, x1, step), np.arange(y0 + step/2, y1, step)
    X, Y = np.meshgrid(xs, ys)
    return X, Y

def sample(w, d, thr, step):
    """Depth, raise, colour and tissue over the whole top, from the design."""
    X, Y = grid(step, (-LL.L/2, LL.L/2, -LL.L/2, LL.L/2))
    x, y = X.ravel(), Y.ravel()
    x0, x1, y0, y1 = LL.PATCH
    inp = (x > x0) & (x < x1) & (y > y0) & (y < y1)
    n = len(x)
    dep, up, tis = np.zeros(n), np.zeros(n), np.full(n, -1)
    cols = np.tile(LL.SKIN[w["skin"]], (n, 1))
    dp, upp, cp, tp = d.surface(x[inp], y[inp], np.zeros(inp.sum(), bool), thr)
    dep[inp], up[inp], cols[inp], tis[inp] = dp, upp, cp, tp
    sh = X.shape
    return X, Y, dep.reshape(sh), up.reshape(sh), cols.reshape(sh + (3,)), tis.reshape(sh)

def show(v):
    if isinstance(v, float):
        return f"{v:.3f}"
    if isinstance(v, list) and len(v) == 3 and all(isinstance(c, float) for c in v):     # a colour
        return "#%02X%02X%02X" % tuple(int(c) for c in v)
    if isinstance(v, dict) and set(v) <= set(LL.ORDER):           # tissue percentages
        return " ".join(f"{LL.SHORT[n]} {p}" for n, p in sorted(v.items(), key=lambda i: -i[1]) if p)
    if isinstance(v, dict) and "area_mm2" in v:                    # a periwound change
        return f"{v['area_mm2']} mm2, clock {v['clock']}, reaches {v['reaches_mm']} mm"
    if isinstance(v, dict):
        return " ".join(f"{k}:{show(x) if isinstance(x, float) else x}" for k, x in v.items())
    return str(v)

class Report:
    """'design' rows are recomputed by the same functions the build uses and
    agree to rounding; 'grid' rows are sampled on a grid instead of measured
    on the mesh, and agree within the tolerances above."""
    def __init__(self):
        self.rows, self.bad = [], 0

    def add(self, what, got, want, kind, **tol):
        ok = agree(got, want, **tol)
        self.rows.append((what, got, want, ok, kind))
        self.bad += 0 if ok else 1

    def show(self):
        for what, got, want, ok, kind in self.rows:
            note = f"   (truth {show(want)})" if kind == "grid" or not ok else ""
            print(f"  {'ok  ' if ok else 'DIFF'} {kind:6s} {what:36s} {show(got)}{note}")

def preview(w, truth, step, out):
    d = LL.Design(w)
    thr = d.fit_thresholds()
    o, _ = LL.outline(w)
    t = LL.design_truth(w, o)
    t["longest_mm"], t["longest_angle_deg"], t["width_across_longest_mm"] = LL.feret(o)
    t["tissue_share"] = LL.tissue_shares(d, thr)
    t["tissue_pct"] = LL.pct(t["tissue_share"])
    t["periwound_conditions"] = LL.periwound_truth(d)
    if "undermine" in w:
        u = w["undermine"]
        tt = np.linspace(math.radians(u["start"]), math.radians(u["end"]), 3601)
        E = LL.undermine_extent(w, tt)
        thf = np.linspace(0, 2*math.pi, 20000, endpoint=False)
        rf = LL.r_of(w, thf) + LL.undermine_extent(w, thf)
        bx, by = LL.CENTRE[0] + rf*np.cos(thf), LL.CENTRE[1] + rf*np.sin(thf)
        a_big = 0.5*abs(np.sum(bx*np.roll(by, -1) - np.roll(bx, -1)*by))
        hours = [np.array([math.radians(90 - 30*hr)]) for hr in range(1, 13)]
        imax = int(np.argmax(E))
        t["undermining"] = dict(
            max_extent_mm=float(E[imax]), max_at_clock=LL.clock(tt[imax]),
            from_clock=LL.clock(math.radians(u["end"])), to_clock=LL.clock(math.radians(u["start"])),
            extent_by_clock_mm={str(hr): round(float(LL.undermine_extent(w, a)[0]), 3)
                                for hr, a in zip(range(1, 13), hours)},
            pocket_height_by_clock_mm={str(hr): round(float(LL.pocket_height(w, a)[0]), 3)
                                       for hr, a in zip(range(1, 13), hours)
                                       if LL.undermine_extent(w, a)[0] >= 0.2},
            undermined_area_mm2=float(a_big - t["area_mm2"]))

    # sampled on a grid: depth, volume, block height and tissue colours
    X, Y, dep, up, cols, tis = sample(w, d, thr, step)
    rho, _, _ = d.frame(X.ravel(), Y.ravel())
    inside = (rho < 1).reshape(X.shape)
    tg = dict(max_depth_mm=float(dep[inside].max()), volume_mm3=float(dep[inside].sum()*step*step))
    tg["block_height_mm"] = max(14, math.ceil(tg["max_depth_mm"] + 6))
    tg["tissue_colour"] = {n: "#%06X" % LL.hexval(cols[tis == i].mean(axis=0))
                           for i, n in enumerate(LL.ORDER) if (tis == i).any()}

    r = Report()
    if truth is not None:
        for k in ("area_mm2", "perimeter_mm", "length_mm", "width_mm", "longest_mm",
                  "width_across_longest_mm"):
            r.add(k, t[k], truth[k], "design")
        r.add("longest_angle_deg", t["longest_angle_deg"], truth["longest_angle_deg"], "design", ab=1e-3)
        for n in LL.ORDER:
            r.add(f"tissue_share {n}", t["tissue_share"][n], truth["tissue_share"][n], "design", ab=1e-4)
        r.add("tissue_pct", t["tissue_pct"], truth["tissue_pct"], "design")
        got, want = t["periwound_conditions"], truth["periwound_conditions"]
        if len(got) != len(want):
            r.add("periwound changes", [g["name"] for g in got], [g["name"] for g in want], "design")
        for g, h in zip(got, want):
            r.add(f"periwound {g['name']}", g, h, "design", ab=0.15)
        if "undermining" in t:
            for k, v in t["undermining"].items():
                r.add(f"undermining {k}", v, truth["undermining"][k], "design", ab=1e-3)
        r.add("max_depth_mm", tg["max_depth_mm"], truth["max_depth_mm"], "grid", ab=TOL_DEPTH)
        r.add("block height H", tg["block_height_mm"], int(truth["skin_plane_z_mm"]), "grid")
        r.add("volume_mm3", tg["volume_mm3"], truth["volume_mm3"], "grid", rel=TOL_VOLUME)
        for n, hx in tg["tissue_colour"].items():
            r.add(f"tissue_colour {n}", hexrgb(hx), hexrgb(truth["tissue_colour"].get(n, "#FFFFFF")),
                  "grid", ab=TOL_COLOUR)
    if out:
        draw(w, d, t, X, Y, dep, up, cols, tis, inside, o, out)
    return t, tg, r

def hexrgb(h):
    return [float(int(h[i:i + 2], 16)) for i in (1, 3, 5)]

def shade(dep, up, step):
    """Lambert shading of the surface lit from the upper left."""
    z = up - dep
    gy, gx = np.gradient(z, step)
    n = np.dstack([-gx, -gy, np.ones_like(z)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    light = np.array([-0.5, 0.6, 0.85]); light /= np.linalg.norm(light)
    return np.clip(0.35 + 0.75*(n @ light), 0, 1.15)

def draw(w, d, t, X, Y, dep, up, cols, tis, inside, o, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch
    os.makedirs(out, exist_ok=True)
    step = X[0, 1] - X[0, 0]
    ext = (X.min() - step/2, X.max() + step/2, Y.min() - step/2, Y.max() + step/2)
    fig, ax = plt.subplots(1, 3, figsize=(15, 5.4))
    img = np.clip(cols*shade(dep, up, step)[..., None], 0, 1)
    ax[0].imshow(img, origin="lower", extent=ext, interpolation="bilinear")
    ax[0].set_title("colour, lit from upper left")
    # tissue map: the hard classes the shares are counted on
    names = LL.ORDER
    tc = [LL.rgb(LL.TISSUE_REF[n][len(LL.TISSUE_REF[n])//2]) for n in names]
    lab = np.where(inside, tis, -1).astype(float)
    lab[lab < 0] = np.nan
    ax[1].imshow(np.broadcast_to(LL.SKIN[w["skin"]], X.shape + (3,)), origin="lower", extent=ext)
    ax[1].imshow(lab, origin="lower", extent=ext, cmap=ListedColormap(tc), vmin=-0.5, vmax=len(names) - 0.5,
                 interpolation="nearest")
    ax[1].legend(handles=[Patch(color=c, label=f"{n} {t['tissue_pct'][n]}%") for n, c in zip(names, tc)
                          if t["tissue_pct"][n] > 0], loc="lower left", fontsize=8, framealpha=0.85)
    ax[1].set_title("tissue map (plan shares)")
    # depth: contours every 1 mm, outline, undermining extent dashed
    dm = np.where(inside, dep, np.nan)
    im = ax[2].imshow(dm, origin="lower", extent=ext, cmap="viridis_r")
    lv = np.arange(1, math.ceil(np.nanmax(dm)) + 1)
    if len(lv):
        ax[2].contour(X, Y, dm, levels=lv, colors="k", linewidths=0.4)
    fig.colorbar(im, ax=ax[2], fraction=0.046, pad=0.04, label="depth below skin, mm")
    if "undermine" in w:
        th = np.linspace(0, 2*math.pi, 4000)
        rr = LL.r_of(w, th) + LL.undermine_extent(w, th)
        ax[2].plot(LL.CENTRE[0] + rr*np.cos(th), LL.CENTRE[1] + rr*np.sin(th), "r--", lw=1,
                   label="undermining extent")
        ax[2].legend(loc="lower left", fontsize=8)
    ax[2].set_title(f"depth (max {np.nanmax(dm):.2f} mm on this grid)")
    for a in ax:
        if a is not ax[0]:                       # the colour view shows only what is printed
            a.plot(np.r_[o[:, 0], o[0, 0]], np.r_[o[:, 1], o[0, 1]], "k", lw=0.6)
        a.set_xlim(LL.PATCH[0] - 4, LL.PATCH[1] + 4); a.set_ylim(LL.PATCH[2] - 4, LL.PATCH[3] + 4)
        a.set_aspect("equal"); a.set_xlabel("x, mm (3 o'clock)"); a.set_ylabel("y, mm (12 o'clock)")
    fig.suptitle(f"{w['id']} {w['long'].title()}, skin type {w['skin']}: L {t['length_mm']:.1f} x "
                 f"W {t['width_mm']:.1f} mm, area {t['area_mm2']:.1f} mm2; periwound: "
                 + ", ".join(n.lower() for n in w["peri_names"]))
    fig.tight_layout()
    fig.savefig(os.path.join(out, f"{w['id']}_{w['name']}_design.png"), dpi=110)
    plt.close(fig)

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("ids", nargs="*", help="parts, e.g. W1 W4 (default all)")
    ap.add_argument("--truth", help="truth file (default: truth_lifelike.json here, else ../data's)")
    ap.add_argument("--out", default=os.path.join(HERE, "preview"), help="folder for pictures, '' for none")
    ap.add_argument("--grid", type=float, default=0.15, help="sampling step for pictures, depth, volume, mm")
    a = ap.parse_args()
    paths = [a.truth] if a.truth else [os.path.join(HERE, os.pardir, "data", "truth_lifelike.json"),
                                       os.path.join(HERE, "truth_lifelike.json")]
    truth = {}
    for p in paths:                                    # a rebuild's truth here overrides the kit's
        if os.path.exists(p):
            truth.update({r["id"]: r for r in json.load(open(p))})
    if not truth:
        print("no truth file found: computing without checking")
    bad, summary = 0, {}
    for w in LL.WOUNDS:
        if a.ids and w["id"] not in a.ids:
            continue
        t, tg, r = preview(w, truth.get(w["id"]), a.grid, a.out)
        print(f"{w['id']} {w['long'].title()}: L {t['length_mm']:.2f} W {t['width_mm']:.2f} mm, "
              f"area {t['area_mm2']:.1f} mm2, perimeter {t['perimeter_mm']:.1f} mm, "
              f"longest {t['longest_mm']:.2f} mm; depth ~{tg['max_depth_mm']:.2f} mm, "
              f"volume ~{tg['volume_mm3']:.0f} mm3; tissue % {show(t['tissue_pct'])}")
        if w["id"] in truth:
            r.show()
        else:
            print("  (no truth for this part to check against)")
        bad += r.bad
        summary[w["id"]] = dict(design=t, grid=tg)
    if a.out:                                          # runs on a few parts at a time add up
        path = os.path.join(a.out, "preview_truth.json")
        merged = {**(json.load(open(path)) if os.path.exists(path) else {}), **summary}
        with open(path, "w") as f:
            json.dump({k: merged[k] for k in sorted(merged, key=lambda s: int(s[1:]))}, f, indent=1)
    if truth:
        print("ALL MATCH" if bad == 0 else f"{bad} DIFFERENCES")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
