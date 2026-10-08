"""Stick-on labels for phantoms that were printed without legible engravings.

Writes label_sheet.pdf: one page, twelve 60 x 60 mm labels with cut marks, laid
out to fit both A4 and US Letter. Print at 100 % ("actual size", no fit-to-page)
on adhesive paper and stick each block's label on its underside. The lid labels
are for the bag or box the lids are kept in - anything stuck to a lid would
change how it seats, and with it the skin plane P10 measures from.

The text comes from the same functions that write the engraved labels, so the
sheet and the engravings cannot disagree.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import make_phantoms_step as M

HERE = os.path.dirname(os.path.abspath(__file__))
MM = 1/25.4
PAGE_W, PAGE_H = 210.0, 279.4          # fits inside both A4 and Letter
SIZE, COLS, ROWS = 60.0, 3, 4
X0 = (PAGE_W - COLS*SIZE)/2
Y0 = (PAGE_H - ROWS*SIZE)/2

def block_text(p):
    lines = M.bottom_lines(p)
    if p["kind"] == "cylwell":
        a = M.assembled(p, M.LIDS[0])
        lines += [f"SEEN {a['visible']:.2f} mm3", f"UM AREA {a['undermined_area']:.2f} mm2",
                  "12 O'CLOCK: AWAY FROM KEY"]
    return lines

def lid_text(l):
    p10 = next(p for p in M.PHANTOMS if p["kind"] == "cylwell")
    lo = p10["R"] - (l["hole_r"] + abs(l["hole_cx"]))      # undermining extent, wound
    hi = p10["R"] - (l["hole_r"] - abs(l["hole_cx"]))      # edge to chamber wall
    ext = f"EXTENT {lo:.3f} ALL ROUND" if abs(hi - lo) < 1e-9 else f"EXTENT {lo:.3f}-{hi:.3f}"
    turn = [] if not l["hole_cx"] else ["OFFSET AT 3 O'CLOCK"]
    return ["STRATAMETRIC " + l["id"], "LID FOR P10"] + M.lid_lines(l) + turn + \
           [ext, f"OD {2*l['R_out']:.3f}  T {l['thick']:.3f}",
            "KEEP WITH LID", "DO NOT STICK ON LID"]

def main():
    fig = plt.figure(figsize=(PAGE_W*MM, PAGE_H*MM))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, PAGE_W); ax.set_ylim(PAGE_H, 0); ax.axis("off")
    items = [(p["id"], block_text(p)) for p in M.PHANTOMS] + \
            [(l["id"], lid_text(l)) for l in M.LIDS]
    for i, (pid, lines) in enumerate(items):
        c, r = i % COLS, i // COLS
        x, y = X0 + c*SIZE, Y0 + r*SIZE
        ax.add_patch(Rectangle((x, y), SIZE, SIZE, fill=False, lw=0.3, ls=(0, (2, 2)),
                               ec="#888888"))
        n = len(lines)
        pitch = min(5.0, (SIZE - 8.0)/n)
        fs = pitch/0.3528*0.72                     # points, cap height ~ 0.72*pitch
        top = y + SIZE/2 - (n - 1)*pitch/2
        for k, s in enumerate(lines):
            ax.text(x + SIZE/2, top + k*pitch, s, ha="center", va="center",
                    family="DejaVu Sans Mono", weight="bold" if k == 0 else "normal",
                    fontsize=fs)
    # cut marks at the grid corners, outside the labels
    for c in range(COLS + 1):
        for r in range(ROWS + 1):
            x, y = X0 + c*SIZE, Y0 + r*SIZE
            if r in (0, ROWS):
                ax.plot([x, x], [y - 6 if r == 0 else y + 2, y - 2 if r == 0 else y + 6], lw=0.4, c="k")
            if c in (0, COLS):
                ax.plot([x - 6 if c == 0 else x + 2, x - 2 if c == 0 else x + 6], [y, y], lw=0.4, c="k")
    ax.text(PAGE_W/2, Y0 - 9, "StrataMetric phantoms - print at 100 % (actual size); "
            "each square is 60 x 60 mm", ha="center", va="center", fontsize=7)
    out = os.path.join(HERE, "label_sheet.pdf")
    fig.savefig(out)
    print("wrote", out)

if __name__ == "__main__":
    main()
