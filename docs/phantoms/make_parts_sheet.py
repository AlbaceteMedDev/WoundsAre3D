"""Part-size reference: which printed part is which, and what each one measures.

Writes parts_sheet.pdf, two US Letter landscape pages:

  1. every part - its STEP file, how to recognise it on the bench (for prints
     whose labels are missing as well as new ones), and its wound's opening,
     depth, area, perimeter and volume;
  2. P10 and its lids - the lid-seated truths, the undermining extent at each
     clock position and how to orient the lid - plus the scale references on
     every block and the formulas behind the numbers.

Every number is computed from the closed forms in make_phantoms_step.py and
rounded once, exactly as the parts are engraved; the script stops if any value
disagrees with truth_step.json, or if a depth, area or volume it prints is not
the text engraved on that part, so the sheet, the engravings and the STEP files
cannot drift apart. (truth_step.json stores values already rounded to 0.001,
and rounding those again would put P2's area at 1963.49 against its engraved
1963.50.) Perimeters are not engraved or in truth_step.json; they are
integrated here, to far better than the 0.01 mm shown.
"""
import json
import math
import os
import numpy as np
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)
import make_phantoms_step as M

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "parts_sheet.pdf")
PAGE = landscape(letter)
MARGIN = 0.5*inch
INK, MUTED, RULE, HEAD = (colors.HexColor(c) for c in ("#1a1a1a", "#555555", "#bbbbbb", "#e8ecef"))

# ------------------------------------------------------------------ fonts ---
def _font(name):
    """DejaVu Sans carries the glyphs the sheet needs (Ø, ×, ², ³, π, ⅔)."""
    import matplotlib
    for d in ("/usr/share/fonts/truetype/dejavu",
              os.path.join(matplotlib.get_data_path(), "fonts", "ttf")):
        f = os.path.join(d, name)
        if os.path.exists(f):
            return f
    raise RuntimeError(f"{name} not found: install fonts-dejavu-core or matplotlib")

pdfmetrics.registerFont(TTFont("DV", _font("DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DV-B", _font("DejaVuSans-Bold.ttf")))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-B")

def style(size, bold=False, color=INK, lead=1.25, **kw):
    return ParagraphStyle("s", fontName="DV-B" if bold else "DV", fontSize=size,
                          leading=size*lead, textColor=color, alignment=TA_LEFT, **kw)

TITLE, SUB, H2 = style(17, True), style(9.5, color=MUTED), style(11.5, True, spaceBefore=4)
BODY, CELL, CELLB, HDR = style(8.6), style(7.9), style(7.9, True), style(7.6, True)
NOTE = style(7.6, color=MUTED)

# ----------------------------------------------------------------- numbers ---
def depth(x):   return f"{x:.3f}"
def area(x):    return f"{x:.2f}"
def volume(x):  return f"{x:.2f}"
def length(x):  return f"{x:.3f}"

def perimeter(p):
    """Opening perimeter in plan. The integrands are smooth and periodic, so the
    trapezoid rule converges geometrically; 8192 points is exact to ~1e-12 mm."""
    k, n = p["kind"], 8192
    t = np.arange(n)*2*math.pi/n
    if k in ("hemisphere", "cone"):
        return 2*math.pi*p["R"]
    if k == "paraboloid":
        a, b = p["a"], p["b"]
        return float(np.sum(np.hypot(a*np.sin(t), b*np.cos(t)))*2*math.pi/n)
    if k == "lobed":
        r = p["R0"]*(1 + sum(A*np.cos(m*t + q) for m, A, q in p["lobes"]))
        dr = -p["R0"]*sum(A*m*np.sin(m*t + q) for m, A, q in p["lobes"])
        return float(np.sum(np.hypot(r, dr))*2*math.pi/n)
    if k == "stadium":
        return 2*p["seg"] + 2*math.pi*p["R"]
    return None

def lobed_radii(p, n=1 << 20):
    t = np.arange(n)*2*math.pi/n
    r = p["R0"]*(1 + sum(A*np.cos(m*t + q) for m, A, q in p["lobes"]))
    return float(r.min()), float(r.max())

def close(a, b, tol=5e-4):
    assert abs(a - b) <= tol, (a, b)

def truths(p, lid):
    """Unrounded (depth, area, volume) - for P10, with a lid seated."""
    if p["kind"] == "cylwell":
        a = M.assembled(p, lid)
        return a["depth"], a["area"], a["volume"]
    vol, ar, dep = M.analytic(p)
    return dep, ar, vol

def engraved(r, *texts):
    """Each text must be engraved on the part, word for word."""
    on = {l["text"] for l in r["labels"]}
    for t in texts:
        assert t in on, (r["id"], t)

# ------------------------------------------------------------- descriptions ---
def wound(p):
    k = p["kind"]
    if k == "hemisphere": return f"Hemisphere, R {length(p['R'])}"
    if k == "cone":       return f"Cone, R {length(p['R'])}, h {length(p['h'])}"
    if k == "paraboloid":
        s = f"Elliptic paraboloid, a {length(p['a'])}, b {length(p['b'])}, h {length(p['h'])}"
        return s + (f", on a cylinder R {length(p['cyl'])}" if p.get("cyl") else "")
    if k == "lobed":
        lb = ", ".join(f"{m}-lobe amplitude {A:.2f} R0" + (f" at phase {q:g} rad" if q else "")
                       for m, A, q in p["lobes"])
        return f"Lobed paraboloid, R0 {length(p['R0'])}, h {length(p['h'])}; {lb}"
    if k == "stadium":
        return (f"Trough: parabolic channel {length(p['seg'])} long, R {length(p['R'])}, "
                f"h {length(p['h'])}, half-paraboloid ends")
    if k == "cylwell":
        return (f"Undermined well: chamber Ø{length(2*p['R'])} × {length(p['h'])} "
                f"under a Ø24.000 lid opening")
    return "None: flat reference"

def opening(p):
    k = p["kind"]
    if k in ("hemisphere", "cone"): return f"Ø{length(2*p['R'])}"
    if k == "paraboloid":
        return f"{length(2*p['a'])} × {length(2*p['b'])} oval" + (" (plan)" if p.get("cyl") else "")
    if k == "lobed":
        lo, hi = lobed_radii(p)
        return f"Lobed, R {lo:.3f}–{hi:.3f}"
    if k == "stadium":
        return f"{length(p['seg'] + 2*p['R'])} × {length(2*p['R'])} slot"
    if k == "cylwell":
        return "Ø24.000 (the lid's hole)"
    return "—"

def recognise(p):
    """What tells the parts apart with the labels unreadable or missing."""
    h = f"{p['height']:g} mm tall"
    k = p["kind"]
    if k == "hemisphere":
        big = p["R"] == max(q.get("R", 0) for q in M.PHANTOMS if q["kind"] == "hemisphere")
        return (f"{h}{', the tallest block' if big else ''}; "
                f"{'large' if big else 'small'} round bowl, Ø{2*p['R']:g}")
    if k == "cone":       return f"{h}; round opening Ø{2*p['R']:g}, straight sides to a point"
    if k == "paraboloid" and p.get("cyl"):
        return f"{h}; top face curved; oval {2*p['a']:g} × {2*p['b']:g}"
    if k == "paraboloid":
        big = p["a"] > 20
        return f"{h}; {'large' if big else 'small, shallow'} oval {2*p['a']:g} × {2*p['b']:g}"
    if k == "lobed":      return f"{h}; flower-shaped opening, uneven lobes"
    if k == "stadium":    return f"{h}; long slot {p['seg'] + 2*p['R']:g} × {2*p['R']:g}, rounded ends"
    if k == "cylwell":    return f"{h}; stepped round pocket Ø{2*p['pocket_r']:g} that the lids drop into"
    return f"{h}; flat top, no cavity"

# ------------------------------------------------------------------- tables ---
def grid(rows, widths, head_rows=1, extra=()):
    t = Table(rows, colWidths=widths, repeatRows=head_rows)
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "DV", 7.9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, head_rows - 1), HEAD),
        ("LINEBELOW", (0, head_rows - 1), (-1, head_rows - 1), 0.8, INK),
        ("LINEBELOW", (0, head_rows), (-1, -1), 0.3, RULE),
        ("TOPPADDING", (0, 0), (-1, -1), 3.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        *extra]))
    return t

def P(text, s=CELL):
    return Paragraph(text, s)

def parts_table(rows, lids):
    head = [P(h, HDR) for h in ("Part", "STEP file", "How to recognise it", "Wound shape (mm)",
                                "Opening (mm)", "Max depth<br/>(mm)", "Opening area<br/>(mm²)",
                                "Perimeter<br/>(mm)", "Volume<br/>(mm³)")]
    body, spans = [head], []
    for p in M.PHANTOMS:
        r = rows[p["id"]]
        per = perimeter(p)
        if p["kind"] == "cylwell":
            per = 2*math.pi*lids[0]["hole_r"]
        dep, ar, vol = truths(p, lids[0])
        num = [depth(dep), area(ar), "—" if per is None else f"{per:.2f}", volume(vol)]
        engraved(r, f"DEPTH {num[0]} MM", f"{'PLAN' if p.get('cyl') else 'AREA'} {num[1]} MM2",
                 f"VOL {num[3]} MM3")
        if p.get("cyl"):
            skin = area(M.skin_area(p))
            engraved(r, f"SKIN {skin} MM2")
            num[1] += f"<br/><font color='#555555'>skin {skin}</font>"
        if p["kind"] == "cylwell":
            num[0] += "<br/><font color='#555555'>with a lid</font>"
        body.append([P(p["id"], CELLB), P(r["file"]), P(recognise(p)), P(wound(p)),
                     P(opening(p))] + [P(x) for x in num])
    for l in lids:
        r = rows[l["id"]]
        i = len(body)
        off = "centred" if not l["hole_cx"] else f"offset {length(l['hole_cx'])}"
        look = "centred" if not l["hole_cx"] else f"{l['hole_cx']:g} mm off-centre"
        body.append([P(l["id"], CELLB), P(r["file"]),
                     P(f"Disc Ø{r['outer_dia_mm']:g} × {r['thickness_mm']:g}, hole {look}"),
                     P(f"Lid for P10: hole Ø{length(r['hole_dia_mm'])}, {off}"),
                     P("Sets P10's opening and undermining; values on page 2", NOTE),
                     "", "", "", ""])
        spans.append(("SPAN", (4, i), (8, i)))
    w = [0.42, 1.95, 1.62, 1.92, 1.10, 0.62, 0.84, 0.74, 0.79]
    return grid(body, [x*inch for x in w], extra=spans)

def lid_table(p10, lids, rows):
    a = {l["id"]: M.assembled(p10, l) for l in lids}
    ext = {l["id"]: M.extents(p10, l) for l in lids}
    for l in lids:                  # the sheet and truth_step.json must agree
        wl = rows["P10"]["with_lid"][l["id"]]
        for k in ("depth", "area", "volume", "visible", "hidden", "undermined_area"):
            close(a[l["id"]][k], wl[k])
        for x, y in zip(ext[l["id"]], wl["extent_by_clock_mm"]):
            close(x, y)
    def row(name, f):
        return [P(name, CELLB)] + [P(f(l)) for l in lids]
    def rng(l):
        e = ext[l["id"]]
        return (f"{min(e):.3f} all round" if max(e) - min(e) < 1e-9 else
                f"{min(e):.3f} at 3 o'clock to {max(e):.3f} at 9 o'clock")
    body = [[P("", HDR)] + [P(f"P10 with {l['id']} seated", HDR) for l in lids],
            row("Lid file", lambda l: rows[l["id"]]["file"]),
            row("Lid hole", lambda l: f"Ø{length(2*l['hole_r'])}, "
                + ("centred" if not l["hole_cx"] else f"centre {length(l['hole_cx'])} toward 3 o'clock")),
            row("Max depth (mm)", lambda l: depth(a[l["id"]]["depth"]) + "  (top skin to chamber floor)"),
            row("Opening area (mm²)", lambda l: area(a[l["id"]]["area"])),
            row("Opening perimeter (mm)", lambda l: f"{2*math.pi*l['hole_r']:.2f}"),
            row("Total volume (mm³)", lambda l: volume(a[l["id"]]["volume"])),
            row("Visible from above (mm³)", lambda l: volume(a[l["id"]]["visible"])),
            row("Hidden under the lid (mm³)", lambda l: volume(a[l["id"]]["hidden"])),
            row("Undermined area (mm²)", lambda l: area(a[l["id"]]["undermined_area"])),
            row("Undermining extent (mm)", rng)]
    for l in lids:                  # P10's walls carry the lid-seated values
        x = a[l["id"]]
        engraved(rows["P10"], f"DEPTH {depth(x['depth'])} MM", f"AREA {area(x['area'])} MM2",
                 f"VOL {volume(x['volume'])} MM3", f"SEEN {volume(x['visible'])} MM3",
                 f"HIDDEN {volume(x['hidden'])} MM3", f"UM AREA {area(x['undermined_area'])} MM2")
    for l in lids:                  # and each lid its hole and offset
        engraved(rows[l["id"]], f"{l['id']} HOLE D{length(2*l['hole_r'])}",
                 f"OFFSET {length(l['hole_cx'])} MM")
    t = grid(body, [1.9*inch, 3.0*inch, 3.0*inch])
    clock = [[P("Clock", HDR)] + [P(f"{12 if k == 0 else k}", HDR) for k in range(12)]]
    for l in lids:
        clock.append([P(f"{l['id']} (mm)", CELLB)] + [P(f"{x:.3f}") for x in ext[l["id"]]])
    c = grid(clock, [0.8*inch] + [0.6*inch]*12)
    return t, c

# --------------------------------------------------------------------- page ---
def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("DV", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, 0.3*inch, "StrataMetric wound phantoms, revision C  ·  part sizes  ·  "
                      "generated by make_parts_sheet.py from make_phantoms_step.py and truth_step.json")
    canvas.drawRightString(PAGE[0] - MARGIN, 0.3*inch, f"Page {doc.page} of 2")
    canvas.restoreState()

def main():
    rows = {r["id"]: r for r in json.load(open(os.path.join(HERE, "truth_step.json")))}
    lids = M.LIDS
    p10 = next(p for p in M.PHANTOMS if p["kind"] == "cylwell")

    # every engraved truth must match its closed form before anything is drawn
    for p in M.PHANTOMS:
        r = rows[p["id"]]
        assert r["file"] == f"{p['id']}_{p['name']}.step", r["file"]
        assert r["height_mm"] == p["height"], p["id"]
        vol, ar, dep = M.analytic(p)
        if p["kind"] == "cylwell":
            close(vol, r["chamber_volume_mm3"]); close(ar, r["chamber_area_mm2"])
            close(dep, r["chamber_depth_mm"])
            a = M.assembled(p, lids[0])
            vol, ar, dep = a["volume"], a["area"], a["depth"]
        close(vol, r["cavity_volume_mm3"]); close(ar, r["opening_area_mm2"])
        close(dep, r["max_depth_mm"])
        if p.get("cyl"):
            close(M.skin_area(p), r["skin_area_mm2"], 1e-2)
    for l in lids:
        r = rows[l["id"]]
        assert r["file"] == f"{l['id']}_{l['name']}.step", r["file"]
        close(2*l["hole_r"], r["hole_dia_mm"]); close(l["hole_cx"], r["hole_offset_mm"])
        close(2*l["R_out"], r["outer_dia_mm"]); close(l["thick"], r["thickness_mm"])

    doc = SimpleDocTemplate(OUT, pagesize=PAGE, leftMargin=MARGIN, rightMargin=MARGIN,
                            topMargin=0.45*inch, bottomMargin=0.5*inch,
                            title="StrataMetric wound phantoms - part sizes",
                            author="StrataMetric", subject="Revision C part-size reference")
    s = []
    s.append(P("Wound phantoms: which part is which, and what it measures", TITLE))
    s.append(Spacer(1, 4))
    s.append(P("Revision C. All dimensions in millimetres. Depth, area and volume are the values "
               "engraved on each part, rounded the same way. Revision B prints have the same file "
               "names, block sizes and cavities, so they read from this table too; revision B "
               "P9 has no fiducial dots (page 2).", SUB))
    s.append(Spacer(1, 8))
    s.append(parts_table(rows, lids))
    s.append(Spacer(1, 7))
    s.append(P("<b>Blocks</b> are 80 × 80 mm; the height is in “How to recognise it”. "
               "<b>Max depth</b> is from the top surface to the lowest point of the wound "
               "(on P9, from the crown of its curved top). "
               "<b>Opening area</b> and <b>perimeter</b> are measured in plan, looking straight "
               "down; on P9, whose top is curved, the area measured on the curved surface itself "
               "is given as “skin”. <b>Perimeter</b> is not engraved on the parts. P10’s depth, "
               "area, perimeter and volume are with either lid seated (page 2).", NOTE))
    s.append(Spacer(1, 3))
    s.append(P("Measure the printed parts with calipers on arrival and use the measured values as "
               "truth: every print process shrinks a little, and the measured number is the one "
               "that matters.", NOTE))

    s.append(PageBreak())
    s.append(P("P10 undermining set", TITLE))
    s.append(Spacer(1, 4))
    s.append(P("P10 is a Ø40.000 × 12.000 chamber under a Ø56.400 × 3.000 pocket. A lid drops into "
               "the pocket, flush with the top, and its Ø24.000 hole becomes the visible wound; the "
               "chamber beyond the hole’s edge is undermined. The two lids give the same depth, "
               "area and volume and differ only in where the undermining runs.", BODY))
    s.append(Spacer(1, 7))
    t, c = lid_table(p10, lids, rows)
    s.append(t)
    s.append(Spacer(1, 6))
    r10 = rows["P10"]
    cv, ca, cd = M.analytic(p10)
    s.append(P(f"Without a lid, the chamber alone, measured from the pocket floor "
               f"{length(p10['pocket_d'])} mm below the top: opening Ø{length(2*p10['R'])}, area "
               f"{area(ca)} mm², depth {depth(cd)} mm, volume {volume(cv)} mm³.", BODY))
    s.append(Spacer(1, 10))
    s.append(KeepTogether([
        P("Undermining extent at each clock position", H2), Spacer(1, 3),
        P("From the edge of the lid’s hole outward to the chamber wall, along a line from the "
          "hole’s centre, as a probe would measure it.", BODY), Spacer(1, 4), c, Spacer(1, 5),
        P("<b>Orientation.</b> 12 o’clock is the edge of P10 nearest the “P10” engraved on its "
          "top; 6 o’clock is the side with the 50.000 key line. On revision C parts, seat the lid "
          "with the notch in its rim at the index groove on P10’s top, which is at 3 o’clock. "
          "Revision B parts have no groove, no notch and no legible “P10”: take 6 o’clock as the side "
          "with the key line, and seat L2 with its hole nearest 3 o’clock. L1 reads the "
          "same at every position.", BODY)]))
    s.append(Spacer(1, 10))
    s.append(KeepTogether([
        P("Scale references on every block’s top", H2), Spacer(1, 3),
        P(f"<b>Key line:</b> {M.KEY_LEN:.3f} mm between the centres of its two end ticks. "
          f"<b>Fiducial dots:</b> four Ø{2*M.DOT_R:.3f} dots at the corners of a "
          f"{2*M.DOT_XY:.3f} mm square, centre to centre. "
          "Revision B P9 has no dots: its powder vents cut them away and left four open slots in "
          "its top near the corners, so use it for depth, area and volume only, not as a scale "
          "reference.", BODY)]))
    s.append(Spacer(1, 10))
    s.append(KeepTogether([
        P("Where the numbers come from", H2), Spacer(1, 3),
        P("Hemisphere: V = ⅔πR³, A = πR². Cone: V = ⅓πR²h, A = πR². Elliptic paraboloid: "
          "V = ½πabh, A = πab. Lobed paraboloid, r(θ) = R0(1 + Σ a cos(mθ + φ)), one term per "
          "set of m lobes with amplitude a and phase φ: "
          "V = ¼πhR0²(2 + Σa²), A = ½πR0²(2 + Σa²). Trough, channel length L: "
          "V = (4/3)hRL + ½πhR², A = 2RL + πR². P10 with a lid of hole radius r and "
          "thickness t: V = πr²t + πR²h, depth = t + h. Perimeters are integrated numerically "
          "from the same outlines.", BODY)]))
    doc.build(s, onFirstPage=footer, onLaterPages=footer)
    print("wrote", OUT)

if __name__ == "__main__":
    main()
