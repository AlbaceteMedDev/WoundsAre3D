"""Lifelike full-colour wound phantoms, W1-W8.

The P-series blocks are exact closed-form shapes in natural grey: the reference
for measuring geometry. These are the opposite: wounds that look like real
ones - irregular margins, uneven beds, granulation in raised granules, slough,
leathery cracked eschar, new epithelium at the edges and in islands, callus,
rolled edges, maceration, erythema and haemosiderin staining - printed in full
colour on six skin tones. They test what the P-series cannot: whether the
product finds the wound edge and classifies the tissue on something that
looks like a patient.

Each wound is designed as functions of position: an outline, a depth below
the skin, a tissue map and the periwound changes. Those are sampled on a fine
triangulation that follows the wound margin exactly, coloured per vertex, and
combined with the block, its engraved labels and (on W4) an undermining pocket
by mesh booleans that carry the colours through. Every number engraved on a
part is measured on the finished mesh - the geometry that is printed - except
the outline's area, perimeter and extents, which the mesh follows exactly, and
the tissue percentages, which come from the tissue map on a 0.05 mm grid.

Writes lifelike/<id>_<name>.3mf (colour per triangle corner, for Xometry and
HP Multi Jet Fusion colour), lifelike/<id>_<name>.wrl.zip (VRML with one colour
per vertex, for Stratasys PolyJet through GrabCAD Print and for Shapeways) and
truth_lifelike.json. render_lifelike.py draws the pictures.

    python make_lifelike.py            # all eight
    python make_lifelike.py W4         # just these
"""
import json
import math
import os
import sys
import zipfile
import numpy as np
import triangle
from manifold3d import Manifold, Mesh, CrossSection
import make_phantoms_step as M

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "lifelike")
L = M.L                                   # 80 mm block, as the P-series
ENG = M.ENG                               # 1.0 mm engravings
PATCH = (-29.0, 29.0, -26.0, 29.0)        # x0, x1, y0, y1: wound and periwound live here,
                                          # clear of the dots, key line and part number
CENTRE = (0.0, 1.5)
FRAME = L/2 + 1.0                         # the top's surface mesh runs 1 mm past the block's edges
AREA_WOUND, AREA_PERI = 0.011, 0.030      # mm^2 per triangle: edges about 0.16 / 0.26 mm
AREA_FRAME = 2.0                          # the plain top outside the patch
MAX_TRIANGLES = 950_000                   # Shapeways' colour upload limit is 1 million
ROOF = 2.0                                # undermining roof, skin to pocket ceiling

# ------------------------------------------------------------------- colour ---
def rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float)/255.0

# Skin: medians of 697 reflectance spectra measured on faces (the University of
# Oulu Physics-Based Face Database, Marszalec et al., J Electron Imaging 2000,
# and RIT's Lippmann2000 database) binned by individual typology angle, matched
# to Fitzpatrick type by the median ITA of each perceived type in 789 adults
# (Lipnick et al., Br J Dermatol 2026;194:135, doi:10.1093/bjd/ljaf397): very
# light, light, intermediate, tan, brown, dark. Measured skin is darker and
# redder than swatch scales such as Monk's, whose prints read too bright.
SKIN = {
    "I": rgb("#C6A494"), "II": rgb("#BF9785"), "III": rgb("#B88E79"),
    "IV": rgb("#A97D67"), "V": rgb("#8D6750"), "VI": rgb("#6E4F40"),
}
# per skin type: erythema, haemosiderin, maceration, callus, pallor - redness
# deepens and turns violaceous on darker skin rather than reading red; pallor
# is ashen, the skin lighter by 13.5 L* with its a* and b* about halved
PERI_COL = {
    "I":   dict(ery="#B07168", hae="#96674F", mac="#D3C4B6", cal="#D5B693", pal="#DECDC4"),
    "II":  dict(ery="#B07168", hae="#96674F", mac="#D3C4B6", cal="#D5B693", pal="#D4C0B6"),
    "III": dict(ery="#996453", hae="#845945", mac="#C9B9AB", cal="#C9AA88", pal="#CCB7AB"),
    "IV":  dict(ery="#996453", hae="#845945", mac="#BFAFA2", cal="#BDA07F", pal="#BCA699"),
    "V":   dict(ery="#7D544B", hae="#5B4136", mac="#A0948A", cal="#9A826D", pal="#A28E81"),
    "VI":  dict(ery="#5E3F3B", hae="#5B4136", mac="#A0948A", cal="#9A826D", pal="#84746B"),
}
BODY = rgb("#E3E1DD")                     # sides and underside: light neutral
INK_DARK, INK_LIGHT = rgb("#1C1C1C"), rgb("#F4F4F2")

# Wound bed. Granulation is within about 7 dE2000 of the median granulation in
# LUTSeg's tissue-labelled ulcer photographs (CC BY 4.0), and epithelium has
# LUTSeg's pink hue (a* 20-24) but lighter, more so on light skin. LUTSeg's
# photographs are of leprosy-related ulcers on uncalibrated smartphones, so
# slough and eschar follow the clinical descriptions instead (BWAT, NPIAP, BMJ
# ABC of Wound Healing): tan-yellow-cream slough, with LUTSeg's pinkish tan only
# where thin fibrin lies over red granulation, and dark brown-black eschar.
# Exposed bone (W4) is ivory to white. Each tissue has a range it is mottled
# across; verify_lifelike.py classes the printed colours against these same
# references.
TISSUE_REF = {
    "granulation": ["#933E41", "#B8484A", "#CB6563"],          # beefy red
    "granulation_pale": ["#A86E68", "#C6857E", "#D29A92"],     # poorly perfused
    "slough": ["#B68E68", "#D1AB6B", "#DCCAAE", "#97926D"],    # tan, yellow, cream, grey
    "necrotic": ["#2E2420", "#4A3A31", "#664333"],             # dark brown-black to brown
    "epithelial": ["#D0908E", "#DEA9A6"],                      # pink, pearly
    "epithelial_dark": ["#B88380", "#C49D9A"],                 # new skin on dark skin
    "bone": ["#E9E2D2", "#F2EDE3"],                            # exposed bone: ivory, white
}
TISSUE = {k: (rgb(v[0]), rgb(v[-1])) for k, v in TISSUE_REF.items()}
ORDER = ["bone", "epithelial", "necrotic", "slough", "granulation"]     # assignment priority
SHORT = {"granulation": "GRAN", "slough": "SLOUGH", "necrotic": "NECROTIC", "epithelial": "EPI",
         "bone": "BONE"}

def luminance(c):
    return float(0.2126*c[0] + 0.7152*c[1] + 0.0722*c[2])

def ink_on(c):
    return INK_DARK if luminance(c) > 0.47 else INK_LIGHT

def mix(a, b, t):
    t = np.clip(t, 0.0, 1.0)[..., None]
    return a*(1 - t) + b*t

def smoothstep(e0, e1, x):
    t = np.clip((x - e0)/(e1 - e0), 0.0, 1.0)
    return t*t*(3 - 2*t)

# -------------------------------------------------------------------- noise ---
def field(seed, x, y, scale, n=28, stretch=1.0, angle=0.0):
    """Smooth random field of roughly unit amplitude with features about `scale`
    mm across; stretch > 1 draws them out along `angle` (degrees), for fibrous
    and streaky textures."""
    rng = np.random.default_rng(seed)
    k = rng.normal(0.0, 1.0, (n, 2))
    k *= (2*math.pi/scale)/np.maximum(np.linalg.norm(k, axis=1, keepdims=True), 1e-9)
    k *= rng.uniform(0.6, 1.4, (n, 1))
    if stretch != 1.0:
        c, s_ = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        u = k[:, 0]*c + k[:, 1]*s_                 # along the streaks: long features
        v = -k[:, 0]*s_ + k[:, 1]*c
        u /= stretch
        k = np.c_[u*c - v*s_, u*s_ + v*c]
    ph = rng.uniform(0, 2*math.pi, n)
    a = rng.normal(0, 1, n)
    out = np.zeros_like(x)
    for i in range(n):
        out += a[i]*np.cos(k[i, 0]*x + k[i, 1]*y + ph[i])
    return out/math.sqrt(float(np.sum(a*a))/2)

def bumps(seed, x, y, spacing, radius, height):
    """Granules: domed bumps on a jittered lattice; returns 0-1 times `height`."""
    from scipy.spatial import cKDTree
    rng = np.random.default_rng(seed)
    x0, x1, y0, y1 = PATCH
    gy = np.arange(y0 - spacing, y1 + spacing, spacing*0.866)
    cs = []
    for j, yy in enumerate(gy):
        gx = np.arange(x0 - spacing, x1 + spacing, spacing) + (spacing/2 if j % 2 else 0.0)
        cs.append(np.c_[gx, np.full(len(gx), yy)])
    c = np.vstack(cs)
    c += rng.uniform(-0.35, 0.35, c.shape)*spacing
    r = radius*rng.uniform(0.7, 1.3, len(c))
    hg = rng.uniform(0.55, 1.2, len(c))
    tree = cKDTree(c)
    d, i = tree.query(np.c_[x, y], k=4)
    v = hg[i]*np.clip(1 - (d/r[i])**2, 0, None)**1.5
    return height*v.max(axis=1)

def smoother(x, y, radius):
    """Averaging over each point's neighbours within `radius` mm, as a sparse
    operator: softens tissue boundaries the way real tissue blends."""
    from scipy.spatial import cKDTree
    from scipy.sparse import csr_matrix
    n = len(x)
    pairs = cKDTree(np.c_[x, y]).query_pairs(radius, output_type="ndarray")
    i = np.r_[pairs[:, 0], pairs[:, 1], np.arange(n)]
    j = np.r_[pairs[:, 1], pairs[:, 0], np.arange(n)]
    A = csr_matrix((np.ones(len(i)), (i, j)), shape=(n, n))
    deg = np.asarray(A.sum(axis=1)).ravel()
    return lambda v: (A @ v)/(deg if np.ndim(v) == 1 else deg[:, None])

# ------------------------------------------------------------------ designs ---
def harmonics(seed, amp, mmax=14, rough=0.0):
    rng = np.random.default_rng(seed)
    hs = [(m, amp*rng.uniform(0.3, 1.0)/m**0.8, rng.uniform(0, 2*math.pi)) for m in range(2, mmax + 1)]
    if rough:
        hs += [(m, rough*rng.uniform(0.3, 1.0)/m**0.5, rng.uniform(0, 2*math.pi))
               for m in range(mmax + 1, 41)]
    return hs

# a and b are the semi-axes across (3-9 o'clock) and along (12-6 o'clock); every
# wound lies roughly along 12-6, so its labelled length is also its longer side.
# Angles in peri and undermine are degrees anticlockwise from 3 o'clock.
WOUNDS = [
    dict(id="W1", name="venous_leg_ulcer", title="VENOUS ULCER", long="VENOUS LEG ULCER",
         a=14.5, b=20.5, rot=-6, harm=harmonics(11, 0.16, 14, 0.010), D=2.4, k=2.2,
         tissue=dict(granulation=0.55, slough=0.25, epithelial=0.20, necrotic=0.0), islands=True,
         peri=dict(erythema=4.0, haemosiderin=6.5, maceration=(230, 300)),
         peri_names=["HAEMOSIDERIN", "ERYTHEMA", "MACERATION"],
         skin="II", seed=101),
    dict(id="W2", name="diabetic_foot_ulcer", title="DIABETIC FOOT", long="DIABETIC FOOT ULCER",
         a=7.0, b=8.0, rot=0, harm=harmonics(12, 0.05, 8, 0.004), D=4.5, k=10,
         tissue=dict(granulation=0.70, slough=0.20, necrotic=0.10, epithelial=0.0),
         peri=dict(callus=(5.0, 1.2), maceration_ring=1.2),
         peri_names=["CALLUS", "MACERATION", "BLOOD IN CALLUS"],
         skin="IV", seed=202),
    dict(id="W3", name="pressure_injury_stage3", title="PRESSURE ST3", long="PRESSURE INJURY S3",
         a=13.0, b=17.0, rot=10, harm=harmonics(13, 0.09, 12, 0.006), D=7.0, k=5,
         tissue=dict(granulation=0.65, slough=0.30, epithelial=0.05, necrotic=0.0),
         peri=dict(erythema=6.0, epibole=(200, 330, 0.8)),
         peri_names=["ROLLED EDGE", "ERYTHEMA"],
         skin="V", seed=303),
    dict(id="W4", name="pressure_injury_stage4", title="PRESSURE ST4", long="PRESSURE INJURY S4",
         a=12.0, b=15.0, rot=-5, harm=harmonics(14, 0.07, 10, 0.004), D=12.0, k=30,
         tissue=dict(granulation=0.38, slough=0.40, necrotic=0.19, bone=0.03, epithelial=0.0),
         bone=dict(at=(-2.0, -3.0), axes=(3.4, 2.6), rot=20.0),       # exposed bone in the base
         peri=dict(erythema=5.0, maceration=(200, 300)),
         undermine=dict(start=30.0, end=150.0, extent=10.0, height=5.0),
         peri_names=["ERYTHEMA", "MACERATION"],
         skin="III", seed=404),
    dict(id="W5", name="unstageable_eschar", title="UNSTAGEABLE", long="UNSTAGEABLE ESCHAR",
         a=12.5, b=16.0, rot=-5, harm=harmonics(15, 0.08, 10, 0.006), D=1.8, k=4,
         tissue=dict(necrotic=0.85, slough=0.15, granulation=0.0, epithelial=0.0),
         peri=dict(erythema=4.0),
         peri_names=["ERYTHEMA"],
         skin="I", seed=505),
    dict(id="W6", name="arterial_ulcer", title="ARTERIAL ULCER", long="ARTERIAL ULCER",
         a=6.0, b=7.0, rot=0, harm=harmonics(16, 0.03, 6, 0.002), D=4.0, k=14,
         tissue=dict(slough=0.50, necrotic=0.30, granulation=0.20, epithelial=0.0),
         pale=True, peri=dict(pallor=6.0),
         peri_names=["PALE SHINY"],
         skin="VI", seed=606),
    dict(id="W7", name="surgical_dehiscence", title="DEHISCENCE", long="SURGICAL DEHISCENCE",
         a=6.0, b=22.5, rot=0, harm=harmonics(17, 0.05, 12, 0.004), D=6.0, k=6,
         tissue=dict(granulation=0.75, slough=0.15, epithelial=0.10, necrotic=0.0),
         peri=dict(erythema=3.0, sutures=True),
         peri_names=["ERYTHEMA", "SUTURE MARKS"],
         skin="IV", seed=707),
    dict(id="W8", name="healing_wound", title="HEALING WOUND", long="HEALING WOUND",
         a=10.0, b=13.0, rot=15, harm=harmonics(18, 0.10, 12, 0.008), D=1.0, k=1.6,
         tissue=dict(epithelial=0.60, granulation=0.40, slough=0.0, necrotic=0.0), islands=True,
         peri=dict(),
         peri_names=["INTACT"],
         skin="II", seed=808),
]

# ------------------------------------------------------------------ outline ---
def r_of(w, th):
    """Distance from the wound centre to the margin along polar angle th (+y is
    12 o'clock): a rotated ellipse with harmonic and fine irregularity."""
    a, b, rot = w["a"], w["b"], math.radians(w["rot"])
    t = th - rot
    re = a*b/np.sqrt((b*np.cos(t))**2 + (a*np.sin(t))**2)
    pert = 1.0 + sum(A*np.cos(m*th + ph) for m, A, ph in w["harm"])
    return re*np.maximum(pert, 0.5)

def polar(x, y):
    dx, dy = x - CENTRE[0], y - CENTRE[1]
    return np.hypot(dx, dy), np.arctan2(dy, dx)

def outline(w, step=0.12):
    """Margin polygon, points spaced `step` mm along it, anticlockwise."""
    th = np.linspace(0, 2*math.pi, 40000, endpoint=False)
    r = r_of(w, th)
    px, py = CENTRE[0] + r*np.cos(th), CENTRE[1] + r*np.sin(th)
    seg = np.hypot(np.diff(np.r_[px, px[0]]), np.diff(np.r_[py, py[0]]))
    s = np.r_[0, np.cumsum(seg)]
    n = int(s[-1]/step)
    ti = np.interp(np.linspace(0, s[-1], n, endpoint=False), s, np.r_[th, 2*math.pi])
    ri = r_of(w, ti)
    return np.c_[CENTRE[0] + ri*np.cos(ti), CENTRE[1] + ri*np.sin(ti)], ti

def undermine_extent(w, th):
    u = w.get("undermine")
    if not u:
        return np.zeros_like(th)
    a0, a1 = math.radians(u["start"]), math.radians(u["end"])
    t = (np.mod(th - a0, 2*math.pi))/(a1 - a0)
    inside = (t >= 0) & (t <= 1)
    return np.where(inside, u["extent"]*np.sin(math.pi*np.clip(t, 0, 1))**1.2, 0.0)

def window(th, a0, a1):
    """0-1 over the arc from a0 to a1 degrees anticlockwise, peaking mid-arc."""
    t = np.mod(np.degrees(th) - a0, 360)/(a1 - a0)
    return np.where((t >= 0) & (t <= 1), np.sin(math.pi*np.clip(t, 0, 1)), 0.0)

def edge_taper(x, y, width=4.0):
    """1 well inside the patch, easing to 0 at its edge, so periwound changes
    never meet the plain skin of the rest of the top in a visible line."""
    x0, x1, y0, y1 = PATCH
    dmin = np.minimum.reduce([x - x0, x1 - x, y - y0, y1 - y])
    return smoothstep(0.5, width, dmin)

# ------------------------------------------------------------ surface model ---
class Design:
    """Everything about one wound as functions of position on the top."""
    def __init__(self, w):
        self.w, self.s = w, w["seed"]

    def f(self, k, x, y, scale, **kw):
        return field(self.s + k, x, y, scale, **kw)

    def frame(self, x, y):
        r, th = polar(x, y)
        R = r_of(self.w, th)
        return r/R, th, R

    # tissue map --------------------------------------------------------------
    def scores(self, x, y, rho, th, R):
        inward = (1 - rho)*R                                  # mm inside the margin
        epi = np.exp(-inward/2.0)*(1 + 0.35*self.f(1, x, y, 6.0))
        if self.w.get("islands"):                             # partial thickness only
            epi = epi + 0.6*np.clip(self.f(2, x, y, 3.5) - 1.0, 0, None)
        side = np.cos(th - math.radians(self.s % 360))                # clumps toward one side
        nec = 0.8*self.f(3, x, y, 9.0) + 0.4*self.f(5, x, y, 4.0) + 0.6*(1 - rho)
        slo = (self.f(4, x, y, 8.0, stretch=1.4, angle=self.s % 180) + 0.35*self.f(6, x, y, 3.0)
               + 0.5*side + 0.25*self.f(3, x, y, 9.0))
        return dict(bone=self.bone(x, y), epithelial=epi, necrotic=nec, slough=slo)

    def bone(self, x, y):
        """Exposed bone in the base of a stage 4 injury: highest inside a ragged
        ellipse, so the share fitted to it takes a compact patch."""
        b = self.w.get("bone")
        if not b:
            return np.zeros_like(x)
        c, s_ = math.cos(math.radians(b["rot"])), math.sin(math.radians(b["rot"]))
        dx, dy = x - CENTRE[0] - b["at"][0], y - CENTRE[1] - b["at"][1]
        u, v = (dx*c + dy*s_)/b["axes"][0], (-dx*s_ + dy*c)/b["axes"][1]
        return 1 - np.hypot(u, v) + 0.12*self.f(53, x, y, 2.0)

    def tissue(self, x, y, rho, th, R, thresholds):
        sc = self.scores(x, y, rho, th, R)
        out = np.full(x.shape, ORDER.index("granulation"))
        free = np.ones(x.shape, bool)
        for name in ORDER[:-1]:
            t = thresholds.get(name)
            if t is None:
                continue
            m = free & (sc[name] > t)
            out[m] = ORDER.index(name)
            free &= ~m
        return out

    def fit_thresholds(self, grid=0.1):
        """Thresholds that give each tissue its target share of the wound area."""
        x, y = np.meshgrid(np.arange(PATCH[0], PATCH[1], grid), np.arange(PATCH[2], PATCH[3], grid))
        x, y = x.ravel(), y.ravel()
        rho, th, R = self.frame(x, y)
        m = rho < 1
        x, y, rho, th, R = x[m], y[m], rho[m], th[m], R[m]
        sc = self.scores(x, y, rho, th, R)
        thr, free = {}, np.ones(x.shape, bool)
        for name in ORDER[:-1]:
            want = self.w["tissue"].get(name, 0.0)
            if want <= 0:
                thr[name] = None
                continue
            v = np.sort(sc[name][free])[::-1]
            n = min(max(int(round(want*len(x))), 1), len(v))
            thr[name] = float(v[n - 1])
            free &= ~(sc[name] > thr[name])
        return thr

    # the surface ---------------------------------------------------------------
    def surface(self, x, y, on_margin, thresholds):
        """Depth inside the wound, height outside it, tissue and colour, for each
        point. Depth and height are >= 0 except suture pits."""
        w = self.w
        rho, th, R = self.frame(x, y)
        rho = np.where(on_margin, 1.0, rho)
        ins = rho < 1
        n = len(x)
        tis = np.full(n, -1)
        dep, up = np.zeros(n), np.zeros(n)
        cols = self.periwound_colour(x, y, rho, th, R)
        up[~ins] = self.raise_(x[~ins], y[~ins], rho[~ins], th[~ins], R[~ins])
        xi, yi, ri, ti, Ri = x[ins], y[ins], rho[ins], th[ins], R[ins]
        tis[ins] = self.tissue(xi, yi, ri, ti, Ri, thresholds)
        avg = smoother(xi, yi, 0.4)
        soft = {nm: avg((tis[ins] == ORDER.index(nm)).astype(float)) for nm in ORDER}
        g = bumps(self.s + 12, xi, yi, 0.95, 0.70, 1.0)               # velvety granules, 0-1.2
        # eschar fissures: a sparse network where a broad field crosses zero
        crack = np.clip(1 - np.abs(self.f(13, xi, yi, 7.0))/0.045, 0, None)*np.clip(self.f(16, xi, yi, 9.0) + 0.6, 0, 1)
        dep[ins] = self.depth(xi, yi, ri, Ri, soft, g, crack)
        cols[ins] = self.bed_colour(xi, yi, ri, Ri, soft, g, crack)
        return dep, up, cols, tis

    def depth(self, x, y, rho, R, soft, g, crack):
        w = self.w
        base = w["D"]*np.clip(1 - rho**w["k"], 0, None)
        base *= (1 + 0.12*self.f(10, x, y, 30.0))*(1 + 0.05*self.f(11, x, y, 7.0))
        gh = 0.08 if w.get("pale") else 0.14
        relief = (soft["granulation"]*(gh*g + 0.08*self.f(17, x, y, 3.0))
                  + soft["slough"]*(0.12 + 0.03*self.f(14, x, y, 1.0, stretch=2.0, angle=self.s % 180))
                  + soft["necrotic"]*(0.40 + 0.06*self.f(15, x, y, 2.0) - 0.25*crack)
                  + soft["epithelial"]*0.03
                  + soft["bone"]*(0.9 + 0.05*self.f(54, x, y, 1.5)))      # a bony prominence stands proud
        ramp = smoothstep(0.0, 1.2, (1 - rho)*R)                     # relief fades out at the margin
        d = base - relief*ramp*np.minimum(1.0, base/0.6 + 0.2)
        return np.maximum(d, 0.08*smoothstep(0.0, 0.6, (1 - rho)*R))

    def bed_colour(self, x, y, rho, R, soft, g, crack):
        w = self.w
        f = lambda k, sc, **kw: self.f(k, x, y, sc, **kw)
        T = {k: [rgb(h) for h in v] for k, v in TISSUE_REF.items()}
        if w.get("pale"):                                          # poorly perfused: pale, blanched
            gran = mix(T["granulation_pale"][0], T["granulation_pale"][-1], 0.25 + 1.1*g + 0.1*f(44, 3.0))
        else:                                                      # beefy red, velvety
            gran = mix(T["granulation"][0], T["granulation"][-1],
                       0.30 + 0.9*g + 0.15*f(44, 2.0) + 0.10*f(49, 0.6))
        # slough: tan to yellow to cream, greyish in places, and the pinkish tan of
        # thin fibrin over a red bed where it meets granulation
        tan, yellow, cream, grey = T["slough"]
        slo = mix(tan, yellow, 0.5 + 0.35*f(45, 3.0))
        slo = mix(slo, cream, 0.45*np.clip(f(50, 2.0) + 0.3, 0, 1))
        slo = mix(slo, grey, 0.25*np.clip(f(46, 5.0) - 0.4, 0, 1))
        slo = mix(slo, rgb("#B3746B"), 0.3*np.clip((0.7 - soft["slough"])*2.5, 0, 1))
        slo = slo*(1 + 0.05*f(51, 0.8, stretch=2.0, angle=self.s % 180))[:, None]
        # eschar: hard dark brown-black, never pure black; browner where it lifts
        nec = mix(T["necrotic"][0], T["necrotic"][1], 0.5 + 0.35*f(47, 2.0))
        nec = mix(nec, T["necrotic"][2], 0.85*np.clip((0.9 - soft["necrotic"])*3, 0, 1))
        nec = nec*(1 - 0.30*crack)[:, None]
        e = T["epithelial_dark"] if luminance(SKIN[w["skin"]]) < 0.47 else T["epithelial"]
        epi = mix(e[0], e[1], 0.5 + 0.3*f(48, 2.0))                 # new skin stays pink on dark skin
        bone = mix(T["bone"][0], T["bone"][1], 0.5 + 0.35*f(52, 1.5))
        c = (soft["granulation"][:, None]*gran + soft["slough"][:, None]*slo
             + soft["necrotic"][:, None]*nec + soft["epithelial"][:, None]*epi
             + soft["bone"][:, None]*bone)
        return np.clip(c, 0, 1)

    # periwound -----------------------------------------------------------------
    def out(self, rho, R):
        return np.maximum((rho - 1)*R, 0.0)

    def maceration(self, rho, th, R):
        p, o = self.w["peri"], self.out(rho, R)
        m = np.zeros_like(rho)
        if "maceration" in p:
            m = np.maximum(m, window(th, *p["maceration"])*np.exp(-o/3.0))
        if "maceration_ring" in p:
            m = np.maximum(m, np.exp(-o/p["maceration_ring"]))
        return m*(rho >= 1)

    def callus(self, x, y, rho, R):
        wc, _ = self.w["peri"]["callus"]
        o = self.out(rho, R)
        edge = wc*(1 + 0.18*self.f(20, x, y, 8.0))
        return smoothstep(0.0, 0.8, o)*(1 - smoothstep(edge - 1.8, edge, o))*(rho >= 1)

    def sutures(self, x, y):
        """Suture punctures in pairs either side of the incision, every 7 mm, and
        the closed incision line beyond the wound."""
        cx, cy = CENTRE
        off = self.w["a"] + 2.2                     # just outside the opened edges
        pits, line = np.zeros_like(x), np.zeros_like(x)
        for yy in np.arange(PATCH[2] + 4, PATCH[3] - 3, 7.0):
            for sx in (-1, 1):
                d = np.hypot(x - (cx + sx*off), y - yy)
                pits = np.maximum(pits, np.clip(1 - (d/0.45)**2, 0, None))
        line = np.clip(1 - np.abs(x - cx)/0.8, 0, None)
        return pits, line

    def raise_(self, x, y, rho, th, R):
        p = self.w["peri"]
        o = self.out(rho, R)
        z = np.zeros_like(x)
        if "callus" in p:
            _, hc = p["callus"]
            z += hc*self.callus(x, y, rho, R)*(1 + 0.10*self.f(21, x, y, 3.0)) \
                 + 0.04*self.callus(x, y, rho, R)*self.f(23, x, y, 1.5)
        if "epibole" in p:
            a0, a1, he = p["epibole"]
            z += he*window(th, a0, a1)**0.7*np.exp(-((o - 0.9)/0.9)**2)*smoothstep(0.0, 0.25, o)
        z += 0.05*self.maceration(rho, th, R)*(1 + self.f(22, x, y, 0.7))*smoothstep(0.0, 0.3, o)
        z = np.maximum(z, 0.0)*edge_taper(x, y)
        if p.get("sutures"):
            pits, _ = self.sutures(x, y)
            z -= 0.25*pits
        return z

    def periwound_layers(self, x, y, rho, th, R):
        """Each periwound change as (name, weight 0-1 at each point, colour), in
        the order they are laid over the skin. periwound_colour mixes them, and
        the truth measures where each shows from the same weights."""
        w, p = self.w, self.w["peri"]
        skin = SKIN[w["skin"]]
        pc = PERI_COL[w["skin"]]
        tap = edge_taper(x, y)
        o = self.out(rho, R)
        layers = []
        if "haemosiderin" in p:
            hw = p["haemosiderin"]
            fade = 1 - smoothstep(2.0, hw + 3.0, o*(1 + 0.3*self.f(30, x, y, 10.0)))
            spk = np.clip((self.f(31, x, y, 1.2) - 1.2)*3, 0, 1)
            hz = fade*np.clip(0.45 + 0.5*self.f(32, x, y, 5.0), 0, 1) + 0.5*spk*fade
            layers.append(("haemosiderin", 0.75*np.clip(hz, 0, 1)*tap, rgb(pc["hae"])))
        if "erythema" in p:
            we = p["erythema"]*(1 + 0.25*self.f(33, x, y, 12.0))
            ez = np.exp(-o/we)*(1 - smoothstep(1.5*we, 3.0*we, o))
            layers.append(("erythema", 0.85*ez*tap, rgb(pc["ery"])))
        if "pallor" in p:                                           # ashen, shiny, hairless; uneven
            wp = p["pallor"]*np.maximum(1 + 0.35*self.f(36, x, y, 9.0), 0.3)
            pz = np.exp(-o/wp)*(0.8 + 0.2*self.f(37, x, y, 3.0))
            layers.append(("pale shiny skin", 0.75*pz*(rho >= 1)*tap, rgb(pc["pal"])))
        if "callus" in p:
            cz = self.callus(x, y, rho, R)*(0.88 + 0.12*self.f(34, x, y, 3.5))*tap
            layers.append(("callus", 0.85*cz, rgb(pc["cal"])))
            bleed = np.clip((self.f(35, x, y, 4.0) - 1.7)*2.0, 0, 1)*self.callus(x, y, rho, R)
            layers.append(("blood in callus", 0.75*bleed*tap, rgb("#74433B")))
        if "epibole" in p:
            a0, a1, _ = p["epibole"]
            ridge = window(th, a0, a1)**0.7*np.exp(-((o - 0.9)/0.9)**2)*(rho >= 1)
            layers.append(("rolled edge", 0.6*ridge*tap, np.clip(skin*0.5 + rgb("#EAC9BE")*0.5, 0, 1)))
        if "maceration" in p or "maceration_ring" in p:
            layers.append(("maceration", 0.85*self.maceration(rho, th, R)*tap, rgb(pc["mac"])))
        if p.get("sutures"):
            pits, line = self.sutures(x, y)
            scar = rgb("#B8746C") if luminance(skin) > 0.55 else rgb("#8A5248")
            layers.append(("incision line", 0.85*line*(rho >= 1)*tap, scar))
            layers.append(("suture marks", 0.85*pits*tap, rgb("#6A3530")))
        return layers

    def periwound_colour(self, x, y, rho, th, R):
        c = np.tile(SKIN[self.w["skin"]], (len(x), 1))
        for _, wt, col in self.periwound_layers(x, y, rho, th, R):
            c = mix(c, col, wt)
        return np.clip(c, 0, 1)

# ---------------------------------------------------------------- meshing ---
def patch_mesh(w):
    """Triangulation of the whole top, running past the block's edges, with the
    patch rectangle and the wound margin as fixed edges: finest inside the
    wound, fine over the periwound patch, coarse beyond it. Returns the index of
    the margin's first vertex too."""
    x0, x1, y0, y1 = PATCH
    o, th = outline(w)
    outer = np.array([[-FRAME, -FRAME], [FRAME, -FRAME], [FRAME, FRAME], [-FRAME, FRAME]])
    rect = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])
    sq = np.array([[0, 1], [1, 2], [2, 3], [3, 0]])
    n0 = 8
    segs = [sq, sq + 4, np.c_[np.arange(len(o)), (np.arange(len(o)) + 1) % len(o)] + n0]
    regions = [[CENTRE[0], CENTRE[1], 1, AREA_WOUND], [x0 + 0.5, y0 + 0.5, 2, AREA_PERI],
               [-FRAME + 0.5, -FRAME + 0.5, 3, AREA_FRAME]]
    T = triangle.triangulate(dict(vertices=np.vstack([outer, rect, o]), segments=np.vstack(segs),
                                  regions=regions), "pq28Aa")
    return T["vertices"], T["triangles"], o, th, T["vertex_markers"].ravel(), n0

def mesh_from(vp, tris):
    m = Mesh(vert_properties=np.ascontiguousarray(vp, np.float32),
             tri_verts=np.ascontiguousarray(tris, np.uint32))
    m.merge()
    man = Manifold(m)
    if man.status().name != "NoError":
        raise RuntimeError(f"mesh is not a valid solid: {man.status()}")
    return man

def box(x0, x1, y0, y1, z0, z1, top, side, bottom):
    """A box whose faces carry their own colours."""
    c = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]])
    faces = [([0, 3, 2, 1], bottom), ([4, 5, 6, 7], top), ([0, 1, 5, 4], side),
             ([1, 2, 6, 5], side), ([2, 3, 7, 6], side), ([3, 0, 4, 7], side)]
    vp, tr = [], []
    for idx, col in faces:
        b = len(vp)
        vp += [np.r_[c[i], col] for i in idx]
        tr += [[b, b + 1, b + 2], [b, b + 2, b + 3]]
    return mesh_from(np.array(vp), np.array(tr))

def cut_tool(V, T, h, cols, Htop):
    """The region above the designed top surface: bottom = the surface (facing
    down), top = a flat lid at Htop, vertical sides on the mesh's outer edge.
    The surface runs past the block's edges, so the cut meets each side wall
    along a clean line at the skin plane and leaves no seam on the top."""
    n = len(V)
    bottom = np.c_[V, h, cols]
    # boundary loop, anticlockwise, from edges used by one triangle
    e = np.sort(np.vstack([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), axis=1)
    u, cnt = np.unique(e, axis=0, return_counts=True)
    bnd = u[cnt == 1]
    nxt = {}
    for a, b in bnd:
        nxt.setdefault(a, []).append(b); nxt.setdefault(b, []).append(a)
    loop = [bnd[0, 0]]
    prev = None
    while True:
        cands = [v for v in nxt[loop[-1]] if v != prev]
        prev = loop[-1]
        if cands[0] == loop[0]:
            break
        loop.append(cands[0])
    loop = np.array(loop)
    # anticlockwise in xy
    lx, ly = V[loop, 0], V[loop, 1]
    if np.sum(lx*np.roll(ly, -1) - np.roll(lx, -1)*ly) < 0:
        loop = loop[::-1]
    top_i = n + np.arange(len(loop))
    top = np.c_[V[loop], np.full(len(loop), Htop), np.tile(cols[0], (len(loop), 1))]
    ctr = n + len(loop)
    cxy = np.array([[lx.mean(), ly.mean(), Htop, *cols[0]]])
    vp = np.vstack([bottom, top, cxy])
    tris = [T[:, [0, 2, 1]]]                                     # surface faces down
    k = len(loop)
    j = np.arange(k); jn = (j + 1) % k
    tris.append(np.c_[np.full(k, ctr), top_i[j], top_i[jn]])     # lid faces up
    tris.append(np.c_[loop[j], loop[jn], top_i[jn]])             # sides face out
    tris.append(np.c_[loop[j], top_i[jn], top_i[j]])
    return mesh_from(vp, np.vstack(tris))

def pocket_height(w, th):
    """Height of the undermining pocket along polar angle th: its design height,
    or less where the pocket is too short for a full rounded end."""
    return np.minimum(w["undermine"]["height"], 2*undermine_extent(w, th))

def pocket_tool(w, H, col):
    """Undermining: a pocket under the margin, its roof ROOF mm below the skin,
    opening into the wound wall. In section it is a slot of constant height with
    a half-round end, so a probe with a ball tip up to that height across slides
    in to the full extent - as on a patient - and support material washes out.
    Its two ends, where the extent falls below 0.2 mm, are closed flat."""
    u = w["undermine"]
    a0, a1 = math.radians(u["start"]), math.radians(u["end"])
    th = np.linspace(a0, a1, 241)
    th = th[undermine_extent(w, th) >= 0.2]
    R, E, hgt = r_of(w, th), undermine_extent(w, th), pocket_height(w, th)
    zc = H - ROOF
    nr, nc = 20, 15                       # points along roof and floor; inside the rounded end
    s = np.linspace(0, 1, nr)
    phi = np.linspace(math.pi/2, -math.pi/2, nc + 2)[1:-1]
    rin = 0.94*R                          # from just inside the margin, in the wound's air
    rc = R + E - hgt/2                    # centre of the rounded end
    rho = np.hstack([rin[:, None] + (rc - rin)[:, None]*s,                       # roof, outward
                     rc[:, None] + (hgt/2)[:, None]*np.cos(phi),                   # round the end
                     rc[:, None] + (rin - rc)[:, None]*s])                         # floor, inward
    z = np.hstack([np.tile(zc, (len(th), nr)),
                   (zc - hgt/2)[:, None] + (hgt/2)[:, None]*np.sin(phi),
                   (zc - hgt)[:, None]*np.ones(nr)])
    nt, k = rho.shape
    X = CENTRE[0] + rho*np.cos(th)[:, None]; Y = CENTRE[1] + rho*np.sin(th)[:, None]
    vp = np.c_[X.ravel(), Y.ravel(), z.ravel(), np.tile(col, (nt*k, 1))]
    i, j = np.meshgrid(np.arange(nt - 1), np.arange(k), indexing="ij")
    a, b = (i*k + j).ravel(), (i*k + (j + 1) % k).ravel()
    c, d = a + k, b + k
    # the section runs clockwise as seen from the start end, so these all face
    # inward; the volume check below turns them out
    tris = [np.c_[a, c, d], np.c_[a, d, b]]                         # the slot's surface
    for row, flip in ((0, False), (nt - 1, True)):                  # flat ends: fans
        f = np.c_[np.zeros(k - 2, int), np.arange(1, k - 1), np.arange(2, k)] + row*k
        tris.append(f[:, ::-1] if flip else f)
    tris = np.vstack(tris)
    for attempt in range(2):
        man = mesh_from(vp, tris)
        if man.volume() > 0:
            return man
        tris = tris[:, ::-1]                       # built inside out: turn every face
    raise RuntimeError("pocket has no positive volume")

def text_tool(rows, col):
    """Engraving tools for label rows, as one coloured mesh solid. Glyph curves
    are kept within 0.01 mm: finer than any printer resolves, and a quarter of
    the triangles a 0.004 mm tolerance costs."""
    import cadquery as cq
    parts = []
    for r in rows:
        comp = M.text_on(r["text"], r["cap"], r["at"], r["xdir"], r["normal"])
        for s in (comp.Solids() or [comp]):
            v, t = s.tessellate(0.01, 0.1)
            v = np.array([[p.x, p.y, p.z] for p in v]); t = np.array(t)
            parts.append(mesh_from(np.c_[v, np.tile(col, (len(v), 1))], t))
    return Manifold.batch_boolean(parts, _op("Add")) if len(parts) > 1 else parts[0]

def _op(name):
    from manifold3d import OpType
    return getattr(OpType, name)

def top_marks(H, ink):
    """Fiducial dots, key line and its end ticks, cut 1 mm into the top."""
    tools = []
    z0 = H - ENG
    def prism(x0, x1, y0, y1):
        return box(x0, x1, y0, y1, z0, H + 1, ink, ink, ink)
    for sx in (-1, 1):
        for sy in (-1, 1):
            c = Manifold.cylinder(ENG + 1, M.DOT_R, M.DOT_R, 48).translate((sx*M.DOT_XY, sy*M.DOT_XY, z0))
            tools.append(c.set_properties(3, lambda p, old: ink))
    half = M.KEY_LEN/2
    tools.append(prism(-half, half, M.KEY_Y - M.KEY_W/2, M.KEY_Y + M.KEY_W/2))
    for sx in (-1, 1):
        tools.append(prism(sx*half - M.TICK_W/2, sx*half + M.TICK_W/2,
                           M.KEY_Y - M.TICK_H/2, M.KEY_Y + M.TICK_H/2))
    return Manifold.batch_boolean(tools, _op("Add"))

# ------------------------------------------------------------------ labels ---
def pct(shares):
    """Whole percentages that add to 100 (largest remainder)."""
    names = [n for n in ORDER[::-1]]
    raw = {n: 100*shares[n] for n in names}
    fl = {n: int(math.floor(raw[n])) for n in names}
    left = 100 - sum(fl.values())
    for n in sorted(names, key=lambda n: raw[n] - fl[n], reverse=True)[:left]:
        fl[n] += 1
    return fl

def tissue_lines(pc, width=19):
    """Tissues present, largest share first, packed into lines; 'PCT' closes
    the last line: the figures are percent of the wound area."""
    items = ["PCT"] + [f"{SHORT[n]} {pc[n]}" for n in sorted(pc, key=lambda n: -pc[n]) if pc[n] > 0]
    lines, cur = [], ""
    for it in items:
        if cur and len(cur) + 1 + len(it) > width:
            lines.append(cur); cur = it
        else:
            cur = f"{cur} {it}".strip()
    return lines + [cur]

def peri_lines(w, width=19):
    """The periwound changes the part shows, packed into lines after 'PERI';
    a name never splits across lines."""
    lines, cur = [], "PERI"
    for n in w["peri_names"]:
        if len(cur) + 1 + len(n) > width:
            lines.append(cur); cur = n
        else:
            cur = f"{cur} {n}"
    return lines + [cur]

def side_lines(w, t):
    pc = t["tissue_pct"]
    und = ([f"UNDERMINED MAX {t['undermining']['max_extent_mm']:.1f}"] if "undermining" in t else [])
    lines = ([f"{w['id']} {w['title']}",
              f"L{t['length_mm']:.1f} W{t['width_mm']:.1f} D{t['max_depth_mm']:.2f}",
              f"AREA {t['area_mm2']:.1f} MM2", f"VOL {t['volume_mm3']:.1f} MM3"]
             + und + tissue_lines(pc) + peri_lines(w) + [f"SKIN TYPE {w['skin']}"])
    # a 14-20 mm wall takes two lines a side; the underside carries the rest,
    # so the skin type and then the periwound give way first
    room = 8 if w["H"] < 20.1 else 12
    if len(lines) > room:
        lines = [s_ for s_ in lines if not s_.startswith("SKIN TYPE")]
    if len(lines) > room:
        lines = [s_ for s_ in lines if s_ not in peri_lines(w)]
    return lines

def spec_lines(w, t):
    """Everything engraved about the part, in the underside's order."""
    lines = [f"{w['id']} {w['title']}",
             f"L{t['length_mm']:.1f} W{t['width_mm']:.1f} D{t['max_depth_mm']:.2f}",
             f"AREA {t['area_mm2']:.1f} MM2", f"PERIM {t['perimeter_mm']:.1f} MM",
             f"VOL {t['volume_mm3']:.1f} MM3"]
    if "undermining" in t:
        u = t["undermining"]
        lines += [f"UNDERMINED {u['from_clock']}-{u['to_clock']}",
                  f"MAX {u['max_extent_mm']:.1f} MM AT {u['max_at_clock']}",
                  f"HIDDEN {u['hidden_volume_mm3']:.1f} MM3"]
    return lines + tissue_lines(t["tissue_pct"]) + peri_lines(w) + [f"SKIN TYPE {w['skin']}"]

def bottom_lines(w, t):
    """The underside: the whole specification in twelve lines at most. Where it
    has no room, what the sides carry gives way - the skin type, then the
    periwound's later lines; build() checks every line is on one face or the
    other."""
    lines = spec_lines(w, t)
    if len(lines) > 12:
        lines = [s_ for s_ in lines if not s_.startswith("SKIN TYPE")]
    for s_ in peri_lines(w)[:0:-1]:
        if len(lines) > 12:
            lines.remove(s_)
    if len(lines) > 12:
        raise RuntimeError(f"{w['id']}: {len(lines)} lines for the underside")
    if len(lines) < 12 and w["long"] != w["title"]:
        lines.insert(1, w["long"])
    if len(lines) < 12:
        lines.insert(0, "STRATAMETRIC")
    for s_ in lines:
        if len(s_) > 19:
            raise RuntimeError(f"{w['id']}: label line too long: {s_}")
    return lines

def layout_bottom(lines, H):
    cap = M.CAP_MAX
    while cap >= M.CAP_MIN - 1e-9:
        pitch = M.PITCH*cap
        if cap + pitch*(len(lines) - 1) + 2*M.EDGE <= L and \
                max(M.text_len(s, cap) for s in lines)/2 <= L/2 - M.EDGE:
            return [dict(face="bottom", text=s, cap=round(cap, 2),
                         at=(0.0, -((len(lines) - 1)*pitch/2 - j*pitch), 0.0),
                         xdir=(1, 0, 0), normal=(0, 0, -1)) for j, s in enumerate(lines)]
        cap -= 0.05
    raise RuntimeError(f"bottom specification does not fit: {lines}")

def layout_sides(w, lines):
    p = dict(id=w["id"], height=w["H"])
    best = M._layout_sides(p, lines)
    if best is None:
        raise RuntimeError(f"{w['id']}: side labels do not fit at {M.CAP_MIN} mm on a {w['H']} mm wall")
    return M._place_sides(p, best)

def top_rows(w):
    H = w["H"]
    return [dict(face="top", text=w["id"], cap=6.0, at=(0.0, 33.0, H), xdir=(1, 0, 0), normal=(0, 0, 1)),
            dict(face="top", text=f"{M.KEY_LEN:.3f}", cap=4.5, at=(0.0, M.KEY_Y - 6.0, H),
                 xdir=(1, 0, 0), normal=(0, 0, 1))]

# ------------------------------------------------------------------- truth ---
def clock(th):
    """Polar angle (rad, +y = 12) to the nearest clock hour."""
    h = int(round((90 - math.degrees(th))/30)) % 12
    return 12 if h == 0 else h

def design_truth(w, o):
    x, y = o[:, 0], o[:, 1]
    area = 0.5*abs(np.sum(x*np.roll(y, -1) - np.roll(x, -1)*y))
    per = float(np.sum(np.hypot(np.diff(np.r_[x, x[0]]), np.diff(np.r_[y, y[0]]))))
    return dict(area_mm2=float(area), perimeter_mm=per,
                length_mm=float(y.max() - y.min()), width_mm=float(x.max() - x.min()))

def tissue_shares(design, thresholds, grid=0.05):
    """Shares of the wound's plan area - as seen from straight above."""
    x, y = np.meshgrid(np.arange(PATCH[0], PATCH[1], grid), np.arange(PATCH[2], PATCH[3], grid))
    x, y = x.ravel(), y.ravel()
    rho, th, R = design.frame(x, y)
    m = rho < 1
    tis = design.tissue(x[m], y[m], rho[m], th[m], R[m], thresholds)
    return {n: float(np.mean(tis == i)) for i, n in enumerate(ORDER)}

def surface_shares(design, thresholds, V, T, h):
    """Shares of the wound bed's surface area rather than its plan area, on the
    designed surface (W4: before its pocket is cut), and that area. Steep walls
    weigh more here than seen from above."""
    P = np.c_[V, h][T]
    cen = P.mean(axis=1)
    rho, th, R = design.frame(cen[:, 0], cen[:, 1])
    m = rho < 1
    a3 = 0.5*np.linalg.norm(np.cross(P[m, 1] - P[m, 0], P[m, 2] - P[m, 0]), axis=1)
    tis = design.tissue(cen[m, 0], cen[m, 1], rho[m], th[m], R[m], thresholds)
    return {n: float(a3[tis == i].sum()/a3.sum()) for i, n in enumerate(ORDER)}, float(a3.sum())

def periwound_truth(design, grid=0.1):
    """Where each periwound change shows, from the same weights the colours are
    mixed with: the area over which its weight is at least 0.3, the clock hours
    that area spans and how far from the margin it reaches."""
    x, y = np.meshgrid(np.arange(PATCH[0], PATCH[1], grid), np.arange(PATCH[2], PATCH[3], grid))
    x, y = x.ravel(), y.ravel()
    rho, th, R = design.frame(x, y)
    m = rho >= 1
    x, y, rho, th, R = x[m], y[m], rho[m], th[m], R[m]
    out = []
    for name, wt, _ in design.periwound_layers(x, y, rho, th, R):
        on = wt >= 0.3
        hours = sorted({12 if h == 0 else int(h) for h in np.round((90 - np.degrees(th[on]))/30) % 12})
        out.append(dict(name=name, area_mm2=round(float(on.sum())*grid*grid, 1),
                        clock="all round" if len(hours) == 12 else hours,
                        reaches_mm=round(float(((rho[on] - 1)*R[on]).max()), 1) if on.any() else 0.0))
    return out

def feret(o):
    """Longest diameter of the margin, its angle from the 12-6 line (degrees,
    positive toward 3 o'clock), and the width across it."""
    from scipy.spatial import ConvexHull
    hull = o[ConvexHull(o).vertices]
    d = np.linalg.norm(hull[:, None] - hull[None], axis=2)
    i, j = np.unravel_index(np.argmax(d), d.shape)
    v = (hull[j] - hull[i])/d[i, j]
    ang = (math.degrees(math.atan2(v[0], v[1])) + 90) % 180 - 90
    return float(d[i, j]), float(ang), float(np.ptp(hull @ np.array([-v[1], v[0]])))

# ------------------------------------------------------------------- build ---
def build(w):
    d = Design(w)
    thr = d.fit_thresholds()
    V, T, o, oth, mk, n0 = patch_mesh(w)
    x, y = V[:, 0], V[:, 1]
    rho, th, R = d.frame(x, y)
    on_margin = np.zeros(len(V), bool)
    on_margin[n0:n0 + len(o)] = True                     # the outline's own vertices
    on_margin |= (mk == 1) & (np.abs(rho - 1) < 0.01)    # points triangle added on it
    ox, oy = o[:, 0], o[:, 1]
    x0, x1, y0, y1 = PATCH
    room = min(ox.min() - x0, x1 - ox.max(), oy.min() - y0, y1 - oy.max())
    if room < 3.0:
        raise RuntimeError(f"{w['id']}: the wound reaches within {room:.1f} mm of the patch edge")
    dep, up, cols, tis = d.surface(x, y, on_margin, thr)
    edge = np.max(np.abs(V), axis=1) > L/2 - 0.5
    if np.any(dep[edge] != 0) or np.any(up[edge] != 0):
        raise RuntimeError(f"{w['id']}: the top is not flat at the block's edges")
    w["H"] = float(max(14, math.ceil(float(dep.max()) + 6)))    # at least 6 mm under the deepest point
    H = w["H"]
    h = H - dep + up
    skin = SKIN[w["skin"]]
    ink_top = ink_on(skin)

    # a block standing above everything the surface raises, cut down to the surface
    base = box(-L/2, L/2, -L/2, L/2, 0.0, H + up.max() + 0.5, skin, BODY, BODY)
    parts = base - cut_tool(V, T, h, cols, H + up.max() + 3)
    if "undermine" in w:
        lo = TISSUE["slough"][0]
        before = parts.volume()
        parts = parts - pocket_tool(w, H, lo)
        if not 0 < before - parts.volume() < 5000:
            raise RuntimeError(f"{w['id']}: undermining removed {before - parts.volume():.1f} mm3")
    if parts.status().name != "NoError" or len(parts.decompose()) != 1:
        raise RuntimeError(f"{w['id']}: the wound left the part invalid or in pieces")

    # truth on the mesh, before labels (labels never touch the wound)
    t = design_truth(w, o)
    t["longest_mm"], t["longest_angle_deg"], t["width_across_longest_mm"] = feret(o)
    cs = CrossSection([o.tolist()])
    prism = Manifold.extrude(cs, H)
    air = prism - parts
    t["volume_mm3"] = float(air.volume())
    mv = parts.to_mesh().vert_properties
    rr, tt = polar(mv[:, 0], mv[:, 1])
    ins = rr < r_of(w, tt) - 1e-6
    t["max_depth_mm"] = float(H - mv[ins, 2].min())
    t["skin_plane_z_mm"] = H
    sh = tissue_shares(d, thr)
    t["tissue_share"] = sh
    t["tissue_pct"] = pct(sh)
    t["tissue_share_surface"], t["bed_surface_area_mm2"] = surface_shares(d, thr, V, T, h)
    # the mean printed colour of each tissue, for the parts sheet's swatches
    t["tissue_colour"] = {n: "#%06X" % hexval(cols[tis == i].mean(axis=0))
                          for i, n in enumerate(ORDER) if (tis == i).any()}
    t["periwound_conditions"] = periwound_truth(d)
    if "undermine" in w:
        u = w["undermine"]
        tt_ = np.linspace(math.radians(u["start"]), math.radians(u["end"]), 3601)
        E = undermine_extent(w, tt_)
        thf = np.linspace(0, 2*math.pi, 20000, endpoint=False)
        Ef = undermine_extent(w, thf)
        rf = r_of(w, thf) + Ef
        big = np.c_[CENTRE[0] + rf*np.cos(thf), CENTRE[1] + rf*np.sin(thf)]
        ring = Manifold.extrude(CrossSection([big.tolist()]), H) - prism
        hidden = (ring - parts).volume()
        if hidden <= 0:
            raise RuntimeError(f"{w['id']}: hidden volume {hidden:.1f} mm3")
        bx, by = big[:, 0], big[:, 1]
        a_big = 0.5*abs(np.sum(bx*np.roll(by, -1) - np.roll(bx, -1)*by))
        imax = int(np.argmax(E))
        hours = [np.array([math.radians(90 - 30*hr)]) for hr in range(1, 13)]
        clocks = {str(hr): round(float(undermine_extent(w, a)[0]), 3) for hr, a in zip(range(1, 13), hours)}
        heights = {str(hr): round(float(pocket_height(w, a)[0]), 3) for hr, a in zip(range(1, 13), hours)
                   if undermine_extent(w, a)[0] >= 0.2}
        t["undermining"] = dict(
            max_extent_mm=float(E[imax]), max_at_clock=clock(tt_[imax]),
            from_clock=clock(math.radians(u["end"])), to_clock=clock(math.radians(u["start"])),
            extent_by_clock_mm=clocks, undermined_area_mm2=float(a_big - t["area_mm2"]),
            hidden_volume_mm3=float(hidden), roof_mm=ROOF, pocket_height_by_clock_mm=heights,
            note=(f"extent from the margin outward along a line from the wound centre; the pocket "
                  f"is a slot {u['height']:.1f} mm high under a {ROOF:.1f} mm roof with a half-round "
                  f"end, so a probe with a ball tip up to {u['height']:.1f} mm across reaches the "
                  f"full extent where the slot is that high"))
        t["total_volume_mm3"] = t["volume_mm3"] + float(hidden)

    # labels: every line on one face or another
    ink_body = INK_DARK
    sl, bl = side_lines(w, t), bottom_lines(w, t)
    missing = [s_ for s_ in spec_lines(w, t) if s_ not in sl + bl]
    if missing:
        raise RuntimeError(f"{w['id']}: no face carries {missing}")
    sides = layout_sides(w, sl)
    bottom = layout_bottom(bl, H)
    top = top_rows(w)
    tools = [text_tool(sides + bottom, ink_body), text_tool(top, ink_top), top_marks(H, ink_top)]
    part = parts - Manifold.batch_boolean(tools, _op("Add"))
    if part.status().name != "NoError" or len(part.decompose()) != 1:
        raise RuntimeError(f"{w['id']}: labels left the part invalid or in pieces")
    t["labels"] = [dict(face=r["face"], text=r["text"], cap_mm=r["cap"],
                        at=[round(float(a), 4) for a in r["at"]], xdir=list(r["xdir"]),
                        normal=list(r["normal"])) for r in sides + bottom + top]
    t["material_mm3"] = float(part.volume())
    return part, t, dict(V=V, T=T, tis=tis, h=h, cols=cols, outline=o, thresholds=thr)

# ------------------------------------------------------------------ export ---
def export(part, path_base, title):
    mesh = part.to_mesh()
    vp = np.asarray(mesh.vert_properties, float)
    tri = np.asarray(mesh.tri_verts, np.int64)
    # one position per geometric vertex; colours stay per triangle corner
    canon = np.arange(len(vp))
    mf, mt = np.asarray(mesh.merge_from_vert), np.asarray(mesh.merge_to_vert)
    if len(mf):
        canon[mf] = mt
    used = np.unique(canon[tri])
    remap = np.full(len(vp), -1); remap[used] = np.arange(len(used))
    pos = vp[used, :3]
    tv = remap[canon[tri]]
    rgb8 = np.clip(np.round(vp[:, 3:6]*255), 0, 255).astype(np.int64)
    key = rgb8[:, 0]*65536 + rgb8[:, 1]*256 + rgb8[:, 2]
    ucol, cidx = np.unique(key, return_inverse=True)
    tc = cidx[tri]
    if len(tv) > MAX_TRIANGLES:
        raise RuntimeError(f"{title}: {len(tv):,} triangles, over the {MAX_TRIANGLES:,} limit")
    write_3mf(path_base + ".3mf", pos, tv, ucol, tc, title)
    write_wrl(path_base + ".wrl.zip", pos, tv, ucol[point_colours(pos, tv, tc, ucol)], title)
    return len(pos), len(tv)

def hexval(c):
    r, g, b = np.clip(np.round(np.asarray(c)*255), 0, 255).astype(int)
    return int(r*65536 + g*256 + b)

def point_colours(pos, tv, tc, ucol):
    """One colour per vertex, for the VRML: some readers ignore colorIndex, so
    it gives each point a single colour. Where a vertex's corners differ - along
    label grooves, the top marks, the block's top edge and the pocket's mouth -
    any colour but the ink wins, so an engraving's walls fade into its groove
    rather than the ink spreading over the face; then the colour covering the
    most area around the vertex."""
    P = pos[tv]
    area = 0.5*np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1)
    ink = np.isin(ucol, [hexval(INK_DARK), hexval(INK_LIGHT)])
    v, c = tv.ravel(), tc.ravel()
    n = len(ucol)
    key, inv = np.unique(v*n + c, return_inverse=True)
    score = np.bincount(inv, weights=np.repeat(area, 3) + np.where(ink[c], 0.0, 1e6))
    kv, kc = key // n, key % n
    order = np.lexsort((score, kv))                  # by vertex, best last
    last = np.r_[kv[order][1:] != kv[order][:-1], True]
    best = np.full(len(pos), -1)
    best[kv[order][last]] = kc[order][last]
    if (best < 0).any():
        raise RuntimeError("a vertex is used by no triangle")
    return best

def write_3mf(path, pos, tv, ucol, tc, title):
    hexes = [f"#{c:06X}" for c in ucol]
    v = "\n".join(f'<vertex x="{a:.5f}" y="{b:.5f}" z="{c:.5f}"/>' for a, b, c in pos)
    t = "\n".join(f'<triangle v1="{a}" v2="{b}" v3="{c}" pid="2" p1="{p}" p2="{q}" p3="{r}"/>'
                  for (a, b, c), (p, q, r) in zip(tv, tc))
    col = "\n".join(f'<m:color color="{h}"/>' for h in hexes)
    model = (f'<?xml version="1.0" encoding="UTF-8"?>\n'
             f'<model unit="millimeter" xml:lang="en-US" '
             f'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
             f'xmlns:m="http://schemas.microsoft.com/3dmanufacturing/material/2015/02">\n'
             f'<metadata name="Title">{title}</metadata>\n'
             f'<metadata name="Designer">StrataMetric</metadata>\n'
             f'<resources>\n<m:colorgroup id="2">\n{col}\n</m:colorgroup>\n'
             f'<object id="1" type="model" pid="2" pindex="0"><mesh>\n<vertices>\n{v}\n</vertices>\n'
             f'<triangles>\n{t}\n</triangles>\n</mesh></object>\n</resources>\n'
             f'<build><item objectid="1"/></build>\n</model>\n')
    ct = ('<?xml version="1.0" encoding="UTF-8"?>\n'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
          '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)

def write_wrl(path, pos, tv, pcol, title):
    """VRML 2.0, one colour per point in point order (no colorIndex)."""
    cols = np.c_[(pcol >> 16) & 255, (pcol >> 8) & 255, pcol & 255]/255.0
    p = ",\n".join(f"{a:.5f} {b:.5f} {c:.5f}" for a, b, c in pos)
    ci = ",\n".join(f"{a},{b},{c},-1" for a, b, c in tv)
    cc = ",\n".join(f"{r:.4f} {g:.4f} {b:.4f}" for r, g, b in cols)
    wrl = (f"#VRML V2.0 utf8\n# {title}. Units: millimetres.\n"
           f"Shape {{ geometry IndexedFaceSet {{ solid TRUE colorPerVertex TRUE\n"
           f"coord Coordinate {{ point [\n{p}\n] }}\ncoordIndex [\n{ci}\n]\n"
           f"color Color {{ color [\n{cc}\n] }}\n}} }}\n")
    name = os.path.basename(path)[:-4]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr(name, wrl)

# -------------------------------------------------------------------- main ---
def main(ids):
    os.makedirs(OUT, exist_ok=True)
    tpath = os.path.join(HERE, "truth_lifelike.json")
    rows = {r["id"]: r for r in json.load(open(tpath))} if os.path.exists(tpath) else {}
    for w in WOUNDS:
        if ids and w["id"] not in ids:
            continue
        part, t, _ = build(w)
        base = os.path.join(OUT, f"{w['id']}_{w['name']}")
        nv, nt = export(part, base, f"StrataMetric {w['id']} {w['long'].title()}")
        rows[w["id"]] = dict(id=w["id"], name=w["name"], wound=w["long"].title(), skin_type=w["skin"],
                             periwound=", ".join(n.lower() for n in w["peri_names"]).capitalize(),
                             block_mm=[L, L, w["H"]],
                             files=[os.path.basename(base) + ".3mf", os.path.basename(base) + ".wrl.zip"],
                             vertices=nv, triangles=nt, **t)
        print(f"{w['id']}: {nv:,} vertices, {nt:,} triangles; area {t['area_mm2']:.1f} mm2, "
              f"depth {t['max_depth_mm']:.2f} mm, volume {t['volume_mm3']:.1f} mm3, "
              f"tissue {t['tissue_pct']}")
    json.dump([rows[k] for k in sorted(rows, key=lambda s: int(s[1:]))], open(tpath, "w"), indent=1)

if __name__ == "__main__":
    main(set(sys.argv[1:]))
