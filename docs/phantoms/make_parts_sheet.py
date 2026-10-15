"""Part-size reference: which printed part is which, and what each one measures.

Writes parts_sheet.pdf, four US Letter landscape pages:

  1-2. a picture of every part, all at one scale, with its sizes beside it in
     mm and cm - the pictures are renders/<id>.png, drawn from the STEP files
     by render_parts.py;
  3. every part - its STEP file, how to recognise it on the bench (for prints
     whose labels are missing as well as new ones), and its wound's opening,
     depth, area, perimeter and volume;
  4. P10 and its lids - the lid-seated truths, the undermining extent at each
     clock position and how to orient the lid - plus the scale references on
     every block and the formulas behind the numbers.

Every number is computed from the closed forms in make_phantoms_step.py and
rounded once, exactly as the parts are engraved; the script stops if any value
disagrees with truth_step.json, or if a depth, area or volume it prints is not
the text engraved on that part, so the sheet, the engravings and the STEP files
cannot drift apart. (truth_step.json stores values already rounded to 0.001,
and rounding those again would put P2's area at 1963.49 against its engraved
1963.50.) Perimeters are not engraved or in truth_step.json; they are
integrated here, to far better than the 0.01 mm shown. Every size is given in
cm as well, written by moving the mm figure's decimal point (cm(), below), so
the cm figures are exactly as precise as the mm ones and never rounded again.
"""
import io
import json
from decimal import Decimal
import math
import os
import numpy as np
from PIL import Image as PILImage, ImageOps
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)
import make_phantoms_step as M

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "parts_sheet.pdf")
RENDERS = os.path.join(HERE, "renders")
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

POW = {1: "", 2: "²", 3: "³"}

def cm(s, k=1):
    """The mm figure s (a string, as printed) in cm (k=1), cm² (k=2) or cm³
    (k=3): its decimal point moved k places, so nothing is rounded twice."""
    return format(Decimal(s).scaleb(-k), "f")

def both(s, k=1, pre=""):
    """ "706.86 mm² · 7.0686 cm²"; pre goes before each figure, e.g. "Ø" """
    return f"{pre}{s} mm{POW[k]} · {pre}{cm(s, k)} cm{POW[k]}"

def g(x):
    return f"{x:g}"

def grey(text):
    return f"<font color='#555555'>{text}</font>"

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

def opening(p, unit="mm", units=False, words=True):
    """The opening's size in mm or cm; units adds the unit, words the shape."""
    f = (lambda x: cm(length(x))) if unit == "cm" else length
    u = f" {unit}" if units else ""
    k = p["kind"]
    if k in ("hemisphere", "cone"): return f"Ø{f(2*p['R'])}{u}"
    if k == "paraboloid":
        return (f"{f(2*p['a'])} × {f(2*p['b'])}{u}" + (" oval" if words else "")
                + (" (plan)" if p.get("cyl") and words else ""))
    if k == "lobed":
        lo, hi = lobed_radii(p)
        return f"R {f(lo)}–{f(hi)}{u}" + (", lobed" if words else "")
    if k == "stadium":
        return f"{f(p['seg'] + 2*p['R'])} × {f(2*p['R'])}{u}" + (" slot" if words else "")
    if k == "cylwell":
        return f"Ø{f(2*M.LIDS[0]['hole_r'])}{u}" + (" lid hole" if words else "")
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
def grid(rows, widths, head_rows=1, extra=(), pad=3.2):
    t = Table(rows, colWidths=widths, repeatRows=head_rows)
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "DV", 7.9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, head_rows - 1), HEAD),
        ("LINEBELOW", (0, head_rows - 1), (-1, head_rows - 1), 0.8, INK),
        ("LINEBELOW", (0, head_rows), (-1, -1), 0.3, RULE),
        ("TOPPADDING", (0, 0), (-1, -1), pad), ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        *extra]))
    return t

def P(text, s=CELL):
    return Paragraph(text, s)

def sizes(p, r, lid):
    """A block's numbers as printed, each checked against its engraving."""
    dep, ar, vol = truths(p, lid)
    per = 2*math.pi*lid["hole_r"] if p["kind"] == "cylwell" else perimeter(p)
    d = dict(depth=depth(dep), area=area(ar), per="—" if per is None else f"{per:.2f}",
             volume=volume(vol))
    engraved(r, f"DEPTH {d['depth']} MM", f"{'PLAN' if p.get('cyl') else 'AREA'} {d['area']} MM2",
             f"VOL {d['volume']} MM3")
    if p.get("cyl"):
        d["skin"] = area(M.skin_area(p))
        engraved(r, f"SKIN {d['skin']} MM2")
    return d

def pictures(ids):
    """The renders, all cropped to one box so they keep their common scale."""
    ims = {i: PILImage.open(os.path.join(RENDERS, f"{i}.png")).convert("L") for i in ids}
    boxes = [ImageOps.invert(im).point(lambda v: 255 if v > 6 else 0).getbbox()
             for im in ims.values()]
    w, h = next(iter(ims.values())).size
    pad = 10
    box = (max(0, min(b[0] for b in boxes) - pad), max(0, min(b[1] for b in boxes) - pad),
           min(w, max(b[2] for b in boxes) + pad), min(h, max(b[3] for b in boxes) + pad))
    return {i: im.crop(box) for i, im in ims.items()}

def picture_cards(rows, lids, width=2.3*inch):
    """Twelve cards, two across and three down on each of two pages: the
    picture, and beside it the part's sizes in mm and cm."""
    ids = [p["id"] for p in M.PHANTOMS] + [l["id"] for l in lids]
    pics = pictures(ids)
    p10 = next(p for p in M.PHANTOMS if p["kind"] == "cylwell")
    tw = 5.0*inch - width - 12                       # the text column
    small, body, head = style(6.6, color=MUTED), style(7.7), style(10.5, lead=1.15)
    cards = []
    for p in M.PHANTOMS + lids:
        r = rows[p["id"]]
        im = pics[p["id"]]
        buf = io.BytesIO(); im.save(buf, "PNG"); buf.seek(0)
        if p in lids:
            e = M.extents(p10, p)
            hole = length(2*p["hole_r"])
            text = [P(f"<b>{p['id']}</b>  Lid for P10", head), P(r["file"], small), Spacer(1, 3),
                    P(f"Hole Ø{hole} mm · Ø{cm(hole)} cm, " + ("centred" if not p["hole_cx"] else
                      f"its centre {both(length(p['hole_cx']))} off-centre, on the notch side"), body),
                    P(f"Disc Ø{g(2*p['R_out'])} × {g(p['thick'])} mm · Ø{cm(g(2*p['R_out']))} × "
                      f"{cm(g(p['thick']))} cm", body)]
            if max(e) - min(e) < 1e-9:
                vals = [("Undermining, all round", length(min(e)), 1)]
            else:
                vals = [("Least undermining, at 3 o’clock", length(min(e)), 1),
                        ("Most undermining, at 9 o’clock", length(max(e)), 1)]
            foot = "Notch to P10’s groove. Every clock position: page 4."
        else:
            d = sizes(p, r, lids[0])
            text = [P(f"<b>{p['id']}</b>  {M.SHAPE[p['kind']].capitalize()}", head),
                    P(r["file"], small), Spacer(1, 3)]
            if p["kind"] == "cylwell":
                text += [P("<b>With a lid seated:</b>", body)]
            if p["kind"] == "flat":
                text += [P("No cavity", body)]
            else:
                text += [P(f"Opening {opening(p, units=True).replace(' (plan)', '')}", body),
                         P(grey(f"Opening {opening(p, 'cm', units=True, words=False)}"), body)]
            if p.get("cyl"):
                text += [P(f"On a curved top, R {g(p['cyl'])} mm · {cm(g(p['cyl']))} cm", body)]
            text += [P(f"Block {g(M.L)} × {g(M.L)} × {g(p['height'])} mm · {cm(g(M.L))} × "
                       f"{cm(g(M.L))} × {cm(g(p['height']))} cm", body)]
            vals = [("Depth", d["depth"], 1)]
            vals += ([("Plan area", d["area"], 2), ("Skin area", d["skin"], 2)] if "skin" in d
                     else [("Area", d["area"], 2)])
            vals += [("Volume", d["volume"], 3)]
            if p["kind"] == "cylwell":
                a = M.assembled(p, lids[0])
                vals += [("Hidden volume", volume(a["hidden"]), 3),
                         ("Undermined area", area(a["undermined_area"]), 2)]
            if d["per"] != "—":
                vals += [("Plan perimeter" if p.get("cyl") else "Perimeter", d["per"], 1)]
            foot = "P10’s lids and undermining: page 4." if p["kind"] == "cylwell" else ""
        mini = Table([[P(lab, body), P(f"{v} mm{POW[k]}", body), P(f"{cm(v, k)} cm{POW[k]}", body)]
                      for lab, v, k in vals], colWidths=[tw - 2*0.84*inch, 0.84*inch, 0.84*inch])
        mini.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                  ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                  ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                                  ("TOPPADDING", (0, 0), (-1, -1), 1.2),
                                  ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2),
                                  ("LINEABOVE", (0, 0), (-1, 0), 0.4, RULE),
                                  ("LINEBELOW", (0, 0), (-1, -1), 0.25, RULE)]))
        text += [Spacer(1, 3), mini]
        if foot:
            text += [Spacer(1, 2), P(foot, small)]
        card = Table([[Image(buf, width=width, height=width*im.height/im.width), text]],
                     colWidths=[width + 8, tw + 4])
        card.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                  ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                  ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                  ("TOPPADDING", (0, 0), (-1, -1), 0),
                                  ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
        cards.append(card)
    pages = []
    for half in (cards[:6], cards[6:]):
        t = Table([half[i:i + 2] for i in range(0, len(half), 2)], colWidths=[5.0*inch]*2)
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                               ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                               ("LINEBELOW", (0, 0), (-1, -2), 0.3, RULE)]))
        pages.append(t)
    return pages

def parts_table(rows, lids):
    head = [P(h, HDR) for h in ("Part", "STEP file", "How to recognise it", "Wound shape (mm)",
                                "Opening<br/>mm<br/>" + grey("cm"), "Max depth<br/>mm<br/>" + grey("cm"),
                                "Opening area<br/>mm²<br/>" + grey("cm²"),
                                "Perimeter<br/>mm<br/>" + grey("cm"),
                                "Volume<br/>mm³<br/>" + grey("cm³ = mL"))]
    body, spans = [head], []
    for p in M.PHANTOMS:
        r = rows[p["id"]]
        d = sizes(p, r, lids[0])
        num = [f"{v}<br/>{grey(cm(v, k))}" if v != "—" else v
               for v, k in ((d["depth"], 1), (d["area"], 2), (d["per"], 1), (d["volume"], 3))]
        if "skin" in d:
            num[1] += f"<br/>skin {d['skin']}<br/>{grey(cm(d['skin'], 2))}"
        if p["kind"] == "cylwell":
            num[0] += "<br/>with a lid"
        op = opening(p) if p["kind"] == "flat" else f"{opening(p)}<br/>{grey(opening(p, 'cm', words=False))}"
        body.append([P(p["id"], CELLB), P(r["file"]), P(recognise(p)), P(wound(p)),
                     P(op)] + [P(x) for x in num])
    for l in lids:
        r = rows[l["id"]]
        i = len(body)
        off = "centred" if not l["hole_cx"] else f"offset {length(l['hole_cx'])}"
        look = "centred" if not l["hole_cx"] else f"{l['hole_cx']:g} mm off-centre"
        body.append([P(l["id"], CELLB), P(r["file"]),
                     P(f"Disc Ø{r['outer_dia_mm']:g} × {r['thickness_mm']:g}, hole {look}"),
                     P(f"Lid for P10: hole Ø{length(r['hole_dia_mm'])}, {off}"),
                     P("Sets P10's opening and undermining; values on page 4", NOTE),
                     "", "", "", ""])
        spans.append(("SPAN", (4, i), (8, i)))
    w = [0.42, 1.86, 1.55, 1.80, 1.31, 0.62, 0.84, 0.74, 0.86]
    return grid(body, [x*inch for x in w], extra=spans, pad=2.3)

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
        return (f"{both(length(min(e)))}, all round" if max(e) - min(e) < 1e-9 else
                f"{both(length(min(e)))} at 3 o'clock, to {both(length(max(e)))} at 9 o'clock")
    body = [[P("", HDR)] + [P(f"P10 with {l['id']} seated  "
                              f"<font name='DV' size='7'>({rows[l['id']]['file']})</font>", HDR)
                            for l in lids],
            row("Lid hole", lambda l: f"{both(length(2*l['hole_r']), pre='Ø')}, "
                + ("centred" if not l["hole_cx"] else
                   f"centre {both(length(l['hole_cx']))} toward 3 o'clock")),
            row("Max depth", lambda l: both(depth(a[l["id"]]["depth"])) + "  (top skin to chamber floor)"),
            row("Opening area", lambda l: both(area(a[l["id"]]["area"]), 2)),
            row("Opening perimeter", lambda l: both(f"{2*math.pi*l['hole_r']:.2f}")),
            row("Total volume", lambda l: both(volume(a[l["id"]]["volume"]), 3)),
            row("Visible from above", lambda l: both(volume(a[l["id"]]["visible"]), 3)),
            row("Hidden under the lid", lambda l: both(volume(a[l["id"]]["hidden"]), 3)),
            row("Undermined area", lambda l: both(area(a[l["id"]]["undermined_area"]), 2)),
            row("Undermining extent", rng)]
    for l in lids:                  # P10's walls carry the lid-seated values
        x = a[l["id"]]
        engraved(rows["P10"], f"DEPTH {depth(x['depth'])} MM", f"AREA {area(x['area'])} MM2",
                 f"VOL {volume(x['volume'])} MM3", f"SEEN {volume(x['visible'])} MM3",
                 f"HIDDEN {volume(x['hidden'])} MM3", f"UM AREA {area(x['undermined_area'])} MM2")
    for l in lids:                  # and each lid its hole and offset
        engraved(rows[l["id"]], f"{l['id']} HOLE D{length(2*l['hole_r'])}",
                 f"OFFSET {length(l['hole_cx'])} MM")
    t = grid(body, [1.7*inch, 4.1*inch, 4.1*inch], pad=1.9)
    clock = [[P("Clock", HDR)] + [P(f"{12 if k == 0 else k}", HDR) for k in range(12)]]
    for l in lids:
        clock.append([P(f"{l['id']} (mm)", CELLB)] + [P(f"{x:.3f}") for x in ext[l["id"]]])
        clock.append([P(grey(f"{l['id']} (cm)"), CELLB)] + [P(grey(cm(f"{x:.3f}"))) for x in ext[l["id"]]])
    c = grid(clock, [0.8*inch] + [0.6*inch]*12, pad=1.9)
    return t, c

# --------------------------------------------------------------------- page ---
class Numbered(rl_canvas.Canvas):
    """Footer with "Page n of N", N known only once every page is laid out."""
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.pages = []
    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()
    def save(self):
        for st in self.pages:
            self.__dict__.update(st)
            self.saveState()
            self.setFont("DV", 7)
            self.setFillColor(MUTED)
            self.drawString(MARGIN, 0.3*inch, "StrataMetric wound phantoms, revision C  ·  part "
                            "sizes  ·  generated by make_parts_sheet.py from make_phantoms_step.py, "
                            "truth_step.json and renders/")
            self.drawRightString(PAGE[0] - MARGIN, 0.3*inch,
                                 f"Page {self._pageNumber} of {len(self.pages)}")
            self.restoreState()
            super().showPage()
        super().save()

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
    s.append(P("Wound phantoms: match the part to its picture", TITLE))
    s.append(Spacer(1, 4))
    s.append(P("Drawn from the STEP files at one scale, cavity up, key line nearest. Sizes in mm "
               "and cm (1 cm³ = 1 mL); the mm depth, area and volume are as engraved on the parts. "
               "Pages 3 and 4 have the full detail.", SUB))
    s.append(Spacer(1, 6))
    first, second = picture_cards(rows, lids)
    s.append(first)
    s.append(PageBreak())
    s.append(P("Match the part to its picture, continued", TITLE))
    s.append(Spacer(1, 6))
    s.append(second)
    s.append(Spacer(1, 6))
    s.append(P("<b>Revision B prints</b> have the same shapes and sizes but look different: most of "
               "their lettering is missing; the hollow blocks (all but P5 and P6) have round powder "
               "holes through their left and right walls, except P9, where the holes come out "
               "through its curved top as four open slots in place of the dots; P10 has no index "
               "groove beside its pocket; and the lids have no notch.", NOTE))
    s.append(PageBreak())
    s.append(P("Every part: file, shape and sizes", TITLE))
    s.append(Spacer(1, 4))
    s.append(P("Revision C. Each size in mm, with cm beneath it in grey; depth, area and volume in mm "
               "as engraved on the parts. Revision B prints read from this table too.", SUB))
    s.append(Spacer(1, 8))
    s.append(parts_table(rows, lids))
    s.append(Spacer(1, 7))
    s.append(P("<b>Blocks</b> are 80 × 80 mm; the height is in “How to recognise it”. "
               "<b>Max depth</b> is from the top surface to the lowest point of the wound "
               "(on P9, from the crown of its curved top). "
               "<b>Opening area</b> and <b>perimeter</b> are measured in plan, looking straight "
               "down; on P9, whose top is curved, the area measured on the curved surface itself "
               "is given as “skin”. <b>Perimeter</b> is not engraved on the parts. P10’s depth, "
               "area, perimeter and volume are with either lid seated (page 4). Each cm figure is the mm "
               "figure with its decimal point moved (1 cm = 10 mm, 1 cm² = 100 mm², 1 cm³ = 1000 mm³ "
               "= 1 mL), so it is exactly as precise.", NOTE))
    s.append(Spacer(1, 3))
    s.append(P("Measure the printed parts with calipers on arrival and use the measured values as "
               "truth: every print process shrinks a little, and the measured number is the one "
               "that matters.", NOTE))

    s.append(PageBreak())
    s.append(P("P10 undermining set", TITLE))
    s.append(Spacer(1, 4))
    ch = f"{length(2*p10['R'])} × {length(p10['h'])}"
    pk = f"{length(2*p10['pocket_r'])} × {length(p10['pocket_d'])}"
    ho = length(2*lids[0]["hole_r"])
    s.append(P(f"P10 is a Ø{ch} mm (Ø{cm(length(2*p10['R']))} × {cm(length(p10['h']))} cm) chamber "
               f"under a Ø{pk} mm (Ø{cm(length(2*p10['pocket_r']))} × {cm(length(p10['pocket_d']))} cm) "
               f"pocket. A lid drops into the pocket, flush with the top, and its Ø{ho} mm "
               f"(Ø{cm(ho)} cm) hole becomes the visible wound; the chamber beyond the hole’s edge is "
               "undermined. The two lids give the same depth, area and volume and differ only in "
               "where the undermining runs.", BODY))
    s.append(Spacer(1, 5))
    t, c = lid_table(p10, lids, rows)
    s.append(t)
    s.append(Spacer(1, 6))
    r10 = rows["P10"]
    cv, ca, cd = M.analytic(p10)
    s.append(P(f"Without a lid, the chamber alone, measured from the pocket floor "
               f"{both(length(p10['pocket_d']))} below the top: opening {both(length(2*p10['R']), pre='Ø')}, "
               f"area {both(area(ca), 2)}, depth {both(depth(cd))}, volume {both(volume(cv), 3)}.",
               BODY))
    s.append(Spacer(1, 5))
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
    s.append(Spacer(1, 5))
    s.append(KeepTogether([
        P("Scale references on every block’s top", H2), Spacer(1, 3),
        P(f"<b>Key line:</b> {both(length(M.KEY_LEN))} between the centres of its two end ticks. "
          f"<b>Fiducial dots:</b> four {both(length(2*M.DOT_R), pre='Ø')} dots at the corners of a "
          f"{both(length(2*M.DOT_XY))} square, centre to centre. "
          "Revision B P9 has no dots: its powder vents cut them away and left four open slots in "
          "its top near the corners, so use it for depth, area and volume only, not as a scale "
          "reference.", BODY)]))
    s.append(Spacer(1, 4))
    s.append(KeepTogether([
        P("Where the numbers come from", H2), Spacer(1, 3),
        P("Hemisphere: V = ⅔πR³, A = πR². Cone: V = ⅓πR²h, A = πR². Elliptic paraboloid: "
          "V = ½πabh, A = πab. Lobed paraboloid, r(θ) = R0(1 + Σ a cos(mθ + φ)), one term per "
          "set of m lobes with amplitude a and phase φ: "
          "V = ¼πhR0²(2 + Σa²), A = ½πR0²(2 + Σa²). Trough, channel length L: "
          "V = (4/3)hRL + ½πhR², A = 2RL + πR². P10 with a lid of hole radius r and "
          "thickness t: V = πr²t + πR²h, depth = t + h. Perimeters are integrated numerically "
          "from the same outlines.", style(7.9))]))
    doc.build(s, canvasmaker=Numbered)
    print("wrote", OUT)

if __name__ == "__main__":
    main()
